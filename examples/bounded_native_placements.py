"""Eight reviewed placements of one source graph in one fixed native worker."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from hashlib import sha256
from itertools import product
from pathlib import Path

from examples import bounded_mixed_native as previous
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _canonical_json,
    _digest_payload,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.frontend import source_intent_from_mapping, source_intent_to_triton_metadata
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.ir.modules import IRStage
from tuc.runtime.overrides import RuntimeOverrideAction, RuntimeOverrideRule, RuntimeOverrideSet
from tuc.runtime.residency import ResidencySpace, plan_residency

CONTEXT = ROOT / "docker/native-placements"
PROFILES = tuple("".join(p) for p in product("cg", repeat=3))
STATIC_FAULTS = (*previous.STATIC_FAULTS, "schedule-placement")
MUTATIONS = (*previous.bridge.chain.MUTATIONS, *STATIC_FAULTS, "skip-publish")
BRIDGE = previous.bridge
CHAIN = BRIDGE.chain


def compile_case(profile):
    if type(profile) is not str or profile not in PROFILES:
        raise BoundedCompilerEmissionError("placement profile rejected")
    payload = CHAIN.parse_source()
    CHAIN.emit(payload)
    graph = source_intent_to_triton_metadata(source_intent_from_mapping(payload)).to_compute_graph()
    supported = frozenset(
        {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
    )
    caps = [
        BackendCapability("bounded-c11", supported, memory_domain=MemoryDomainKind.HOST_RAM),
        BackendCapability("bounded-cuda", supported, memory_domain=MemoryDomainKind.UNKNOWN),
    ]
    names = {"c": "bounded-c11", "g": "bounded-cuda"}
    overrides = RuntimeOverrideSet(
        tuple(
            RuntimeOverrideRule(op.name, RuntimeOverrideAction.REQUIRE_BACKEND, names[p])
            for op, p in zip(graph.operations, profile, strict=True)
        )
    )
    compiled = compile_graph(graph, caps, runtime_overrides=overrides)
    host = ResidencySpace("host", MemoryDomainKind.HOST_RAM)
    available = {
        "bounded-c11": host,
        "bounded-cuda": ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN),
    }
    spaces = {
        a.backend_name: available[a.backend_name] for a in compiled.partition_plan.assignments
    }
    return compiled, plan_residency(compiled.hac_ir.graph, compiled.partition_plan, spaces, host)


def snapshot(profile):
    compiled, plan = compile_case(profile)
    return {
        "schema_version": "tuc.bounded_placement_plan.v0",
        "profile": profile,
        "hac_ir": compiled.dump(IRStage.HAC_IR),
        "hs_ir": compiled.dump(IRStage.HS_IR),
        "partition": compiled.dump_runtime_plan(),
        "decisions": compiled.dump_decision_report(),
        "overrides": json.loads(
            json.dumps([asdict(e) for e in compiled.partition_plan.override_effects])
        ),
        "residency": json.loads(json.dumps(asdict(plan))),
        "copy_bytes": plan.copy_bytes,
        "latency_ns": None,
        "energy_pj": None,
        "normal_runtime_admission": False,
    }


def lower(value, profile):
    BRIDGE._bounded_metadata(value)
    expected = snapshot(profile)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("placement snapshot rejected")
    compiled, plan = compile_case(profile)
    tensors = {"a": 0, "b": 1, "projection": 2, "activated": 3, "row_sum": 4}
    ops = {op.name: i for i, op in enumerate(compiled.hac_ir.graph.operations, 1)}
    lines = [f"static const struct tuc_buffer buffers_{profile}[] = {{"]
    for b in plan.buffers:
        lines.append(f"  {{{tensors[b.tensor]}U, {int(b.space.name != 'host')}U, {b.bytes}U}},")
    lines += ["};", f"static const struct tuc_event events_{profile}[] = {{"]
    for step in plan.steps:
        kind = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}[step.kind]
        opcode = ops[step.operation] if step.operation else 0
        space = int(step.backend == "bounded-cuda")
        a, b = (*step.inputs, 255, 255)[:2]
        out = step.outputs[0] if step.outputs else 255
        lines.append(f"  {{{kind}U, {opcode}U, {space}U, {a}U, {b}U, {out}U}},")
    return "\n".join([*lines, "};", ""])


def artifact_files():
    previous.verify_artifacts()
    files = {
        n: _read_bounded_file(previous.CONTEXT / n).decode()
        for n in (
            "generated.c",
            "generated.h",
            "kernels.cuh",
            "inputs.h",
            "oracle.h",
            "common.h",
            "worker.h",
            "host.c",
            "device.cu",
            "build-c11.sh",
            "Dockerfile",
        )
    }
    tables = []
    rows = []
    for profile in PROFILES:
        value = snapshot(profile)
        files[f"{profile}_plan.json"] = json.dumps(value, indent=2, sort_keys=True) + "\n"
        tables.append(lower(value, profile))
        plan = value["residency"]
        rows.append(
            f'  {{"{profile}", "{_digest_payload(value)}", {PROFILES.index(profile)}U, '
            f"{len(plan['buffers'])}U, {len(plan['steps'])}U, "
            f"{sum(b['bytes'] for b in plan['buffers'])}U, buffers_{profile}, events_{profile}}},"
        )
    code = _digest_payload({t: CHAIN.expected_observation(t)["code_digest"] for t in CHAIN.TARGETS})
    files["plans.h"] = "\n".join(
        [
            "#ifndef TUC_PLACEMENT_PLANS_H",
            "#define TUC_PLACEMENT_PLANS_H",
            f'#define TUC_MATRIX_CODE_DIGEST "{code}"',
            *tables,
            "static const struct tuc_profile profiles[] = {",
            *rows,
            "};",
            "#endif",
            "",
        ]
    )
    files["common.h"] = files["common.h"].replace(
        "tuc.bounded_mixed_numeric_observation.v0", "tuc.bounded_placement_numeric.v0"
    )
    files["common.h"] = BRIDGE._replace_once(
        files["common.h"],
        "  alarm(15U);",
        (
            "  alarm(15U);\n  if (argc != 3 || !select_profile(argv[1]))\n"
            '    return emit("invalid", "invalid_invocation", false, 0, -1, 0, 0, 0);'
        ),
    )
    files["common.h"] = (
        files["common.h"]
        .replace("argc == 2", "argc == 3")
        .replace("strcmp(argv[1],", "strcmp(argv[2],")
    )
    for array in ("read_slots", "write_slots", "owned", "available"):
        files["worker.h"] = files["worker.h"].replace(
            f"{array}[TUC_BUFFER_COUNT]", f"{array}[TUC_MAX_BUFFERS]"
        )
    files["worker.h"] = files["worker.h"].replace(
        "buffer_at(s.a).tensor == 2U", "buffer_at(s.a).tensor >= 2U"
    )
    for key, worker in (("host.c", "c11"), ("device.cu", "matrix")):
        text = files[key]
        text = re.sub(r'#define TUC_TARGET "\w+"', "#define TUC_TARGET active->name", text)
        text = re.sub(r'#define TUC_PLAN_HEADER "[\w.]+"', f'#define TUC_WORKER "{worker}"', text)
        text = text.replace("TUC_MIXED_CODE_DIGEST", "TUC_MATRIX_CODE_DIGEST")
        if key == "host.c":
            text = text.replace(
                "return schedule_valid() &&", "return active->mask == 0U && schedule_valid() &&"
            )
        else:
            text = BRIDGE._replace_once(
                text, "  int count = 0;", "  if (active->mask == 0U) return true;\n  int count = 0;"
            )
            text = text.replace("opcode == 1U ? 6U : 2U", "opcode == 3U ? 2U : 6U")
            text = BRIDGE._replace_once(
                text,
                "  else if (opcode == 3U)",
                "  else if (opcode == 2U) tuc_relu<<<blocks, 32>>>(a, out);\n"
                "  else if (opcode == 3U)",
            )
        files[key] = text
    files["build-c11.sh"] = BRIDGE._replace_once(
        files["build-c11.sh"],
        "compile generated.c /out/proof\n",
        "compile generated.c /out/proof\n"
        "compile generated.c /out/schedule-placement -DTUC_SCHEDULE_FAULT=7\n",
    )
    files["build-c11.sh"] += (
        "gcc -std=c11 -O1 -g1 -Wall -Wextra -Werror "
        "-fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer "
        "contract_test.c -o /out/contract-sanitized\n"
    )
    original = _read_bounded_file(previous.CONTEXT / "build-cuda.sh").decode()
    prefix = original.split("gcc -std=c11 -O2", 1)[0]
    host_compile = (
        "    gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off "
        "-fexcess-precision=standard -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=3 "
        "-Dtuc_projection=tuc_host_projection -Dtuc_relu=tuc_host_relu "
        '-Dtuc_sum_axis1=tuc_host_sum_axis1 "$@" -c generated.c -o host-kernels.o\n'
    )
    prefix = BRIDGE._replace_once(prefix, "    nvcc ", host_compile + "    nvcc ")
    commands = ["compile /out/proof", "cp generated.c reviewed.c", "cp kernels.cuh reviewed.cuh"]
    commands += [
        f"compile /out/{m} -DTUC_SCHEDULE_FAULT={i}" for i, m in enumerate(STATIC_FAULTS, 1)
    ]
    commands += [
        "compile /out/skip-publish -DTUC_SKIP_PUBLISH=1",
        "compile /out/skip-transfer -DTUC_SKIP_TRANSFER=1",
        "compile /out/over-budget -DTUC_OVER_BUDGET=1",
        "compile /out/nonfinite -DTUC_NONFINITE=1",
        "cuobjdump --dump-sass /out/proof > /out/sass.txt",
        "awk '/Function :/ {inside = ($0 ~ /tuc_projection/); if (inside) found=1} "
        "inside && /FFMA/ {bad=1} END {exit (!found || bad)}' /out/sass.txt",
    ]
    mutations = {
        "bypass-relu": "s/value < 0.0F ? 0.0F : value/value/",
        "late-relu": "s/value < 0.0F ? 0.0F : value/value/;"
        "s/output\\[row\\] = value;/output[row] = value < 0.0F ? 0.0F : value;/",
        "missing-sum": "s/value += projection\\[row \\* 5U + column\\];/"
        "value = projection[row * 5U + column];/",
        "wrong-stride": "s/b\\[inner \\* 5U + column\\]/b[inner + column]/",
        "incomplete-coverage": "s/index < 165U/index < 164U/",
    }
    for name, expr in mutations.items():
        commands += [
            f"sed '{expr}' reviewed.c > generated.c",
            f"sed '{expr}' reviewed.cuh > kernels.cuh",
            f"compile /out/{name}",
        ]
    files["build-cuda.sh"] = prefix + "\n".join(commands) + "\n"
    docker = files["Dockerfile"].replace("mixed-native", "native-placements")
    docker = docker.replace("c11_plan.h", "plans.h").replace("mixed_plan.h", "plans.h")
    docker = BRIDGE._replace_once(
        docker,
        "RUN --network=none sh build-c11.sh",
        "COPY docker/native-placements/contract_test.c ./\nRUN --network=none sh build-c11.sh",
    )
    docker = docker.replace("/out/proof /out/", "/out/proof /out/schedule-placement /out/")
    files["Dockerfile"] = docker.replace('CMD ["--preflight"]', 'CMD ["ccc", "--preflight"]')
    files["Dockerfile.dockerignore"] = "**\n!docker/\n!docker/native-placements/\n" + "".join(
        f"!docker/native-placements/{n}\n"
        for n in (*files, "contract.h", "contract_test.c")
        if not n.endswith(".json")
    )
    return files


def verify_artifacts():
    for name, text in artifact_files().items():
        if _read_bounded_file(CONTEXT / name) != text.encode():
            raise BoundedCompilerEmissionError("placement artifact drift")
    return {
        "schema_version": "tuc.bounded_placement_verification.v0",
        "status": "PASS",
        "profiles": list(PROFILES),
        "normal_runtime_admission": False,
    }


def program_digest():
    paths = [
        CONTEXT / n for n in (*artifact_files(), "contract.h", "contract_test.c", "operator.sh")
    ]
    paths += [
        ROOT / "examples/bounded_native_placements.py",
        ROOT / "src/tuc/runtime/residency.py",
        ROOT / "src/tuc/runtime/overrides.py",
    ]
    return _digest_payload(
        {
            p.relative_to(ROOT).as_posix(): "sha256:" + sha256(_read_bounded_file(p)).hexdigest()
            for p in paths
        }
    )


def profiles_for(worker):
    if type(worker) is not str or worker not in ("c11", "matrix"):
        raise BoundedCompilerEmissionError("placement worker rejected")
    return ("ccc",) if worker == "c11" else PROFILES


def counts(plan, steps, repeats):
    count = {
        "completed_steps": len(steps),
        "cpu_calls": 0,
        "gpu_calls": 0,
        "upload_calls": 0,
        "download_calls": 0,
        "upload_bytes": 0,
        "download_bytes": 0,
    }
    for step in steps:
        if step.kind == "execute":
            count["gpu_calls" if step.backend == "bounded-cuda" else "cpu_calls"] += 1
        elif step.kind == "copy":
            b = plan.buffers[step.outputs[0]]
            direction = "download" if b.space.name == "host" else "upload"
            count[direction + "_calls"] += 1
            count[direction + "_bytes"] += b.bytes
    return {k: v * repeats for k, v in count.items()}


def expected_observation(profile, worker, preflight=False, mutation=None):
    if (
        type(profile) is not str
        or profile not in profiles_for(worker)
        or type(preflight) is not bool
    ):
        raise BoundedCompilerEmissionError("placement mode rejected")
    allowed = (*MUTATIONS, *(("skip-transfer",) if profile != "ccc" else ()), "unknown-profile")
    if mutation is not None and (type(mutation) is not str or mutation not in allowed or preflight):
        raise BoundedCompilerEmissionError("placement mutation rejected")
    _, plan = compile_case(profile)
    numeric = CHAIN.expected_observation("c11" if worker == "c11" else "cuda", preflight)
    numeric.update(
        schema_version="tuc.bounded_placement_numeric.v0",
        target=profile,
        tensor_bytes=0 if preflight else sum(b.bytes for b in plan.buffers),
    )
    if worker == "matrix":
        numeric["code_digest"] = _digest_payload(
            {t: CHAIN.expected_observation(t)["code_digest"] for t in CHAIN.TARGETS}
        )
    counter = counts(plan, plan.steps, 0 if preflight else 11)
    if mutation:
        numeric.update(
            status="ERROR",
            cases_passed=0,
            failed_run_index=0,
            scalar_checks=0,
            outputs_differing_from_reference64=0,
            numeric_contract_passed=False,
            execution_policy_passed=False,
            repeated_baseline_passed=False,
        )
        if mutation in STATIC_FAULTS or mutation == "unknown-profile":
            counter = counts(plan, (), 0)
            numeric.update(
                reason_code="target_not_ready",
                generated_function_calls=0,
                tensor_bytes=0,
                failed_run_index=-1,
            )
            if mutation == "unknown-profile":
                numeric.update(
                    reason_code="invalid_invocation", mode="invalid", security_boundary_passed=False
                )
        else:
            steps = plan.steps
            reason = "numeric_contract_mismatch"
            if mutation == "skip-publish":
                steps = steps[:-1]
                reason = "execution_failed"
            elif mutation == "skip-transfer":
                index = next(
                    i
                    for i, s in enumerate(steps)
                    if s.kind == "copy" and plan.buffers[s.inputs[0]].tensor not in ("a", "b")
                )
                steps = steps[:index]
                reason = "execution_failed"
            counter = counts(plan, steps, 1)
            numeric.update(
                reason_code=reason,
                generated_function_calls=counter["cpu_calls"] + counter["gpu_calls"],
            )
    return {
        "schema_version": "tuc.bounded_placement_observation.v0",
        "worker": worker,
        "profile": profile,
        "plan_digest": _digest_payload(snapshot(profile)),
        "residency": counter,
        "numeric_observation": numeric,
    }


def validate_observation(value, profile, worker, preflight=False, mutation=None):
    BRIDGE._bounded_metadata(value)
    expected = expected_observation(profile, worker, preflight, mutation)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("placement observation rejected")
    return expected


def build_record(observations, worker, image_id):
    BRIDGE._bounded_metadata(observations)
    profiles = profiles_for(worker)
    if type(observations) is not list or len(observations) != len(profiles):
        raise BoundedCompilerEmissionError("placement coverage rejected")
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("placement image rejected")
    for profile, value in zip(profiles, observations, strict=True):
        validate_observation(value, profile, worker)
    verify_artifacts()
    return {
        "schema_version": "tuc.bounded_placement_record.v0",
        "worker": worker,
        "observations": observations,
        "operator_image_id": image_id,
        "program_files_digest": program_digest(),
        "previous_mixed_program_digest": previous.program_digest(),
        "provenance": "same_maintainer_operator",
        "normal_runtime_admission": False,
    }


def accept_directory(directory, worker, image_id):
    profiles = profiles_for(worker)
    observations = []
    for profile in profiles:
        validate_observation(
            load_observation(directory / f"{profile}-preflight.json"), profile, worker, True
        )
        observations.append(load_observation(directory / f"{profile}-execution.json"))
        for mutation in (*MUTATIONS, *(("skip-transfer",) if profile != "ccc" else ())):
            validate_observation(
                load_observation(directory / f"{profile}-{mutation}.json"),
                profile,
                worker,
                mutation=mutation,
            )
    validate_observation(
        load_observation(directory / "unknown-profile.json"),
        "ccc",
        worker,
        mutation="unknown-profile",
    )
    if worker == "c11":
        validate_observation(load_observation(directory / "sanitized.json"), "ccc", worker)
        contract = load_observation(directory / "contract-sanitized.json")
        if _canonical_json(contract) != _canonical_json(
            {
                "schema_version": "tuc.placement_contract_sanitizer.v0",
                "status": "PASS",
                "profiles_checked": 8,
                "invalid_selectors": 4,
                "bitflip_rejections": 19840,
            }
        ):
            raise BoundedCompilerEmissionError("placement contract sanitizer rejected")
    return build_record(observations, worker, image_id)


def compare_records(cpu, matrix):
    for value, worker in ((cpu, "c11"), (matrix, "matrix")):
        BRIDGE._bounded_metadata(value)
        if type(value) is not dict or _canonical_json(value) != _canonical_json(
            build_record(value.get("observations"), worker, value.get("operator_image_id"))
        ):
            raise BoundedCompilerEmissionError("placement record rejected")
    if len({snapshot(p)["hac_ir"] for p in PROFILES}) != 1:
        raise BoundedCompilerEmissionError("placement-dependent HAC-IR rejected")
    rows = [{"profile": o["profile"], **o["residency"]} for o in matrix["observations"]]
    return {
        "schema_version": "tuc.bounded_placement_comparison.v0",
        "status": "PASS",
        "source_intent_digest": CHAIN.INTENT_DIGEST,
        "matrix_scalar_checks": 8 * 363,
        "one_matrix_image": True,
        "placements": rows,
        "c11_record_digest": _digest_payload(cpu),
        "matrix_record_digest": _digest_payload(matrix),
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
        "optimal_placement_claim": False,
        "blocked_claims": [
            "arbitrary_inputs",
            "dynamic_shapes",
            "general_native_runtime",
            "performance",
            "independent_reproduction",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("c11", "matrix"))
    parser.add_argument("--accept", type=Path)
    parser.add_argument("--image-id")
    parser.add_argument("--compare", type=Path, nargs=2)
    args = parser.parse_args()
    try:
        if args.compare and not any((args.worker, args.accept, args.image_id)):
            report = compare_records(*(load_observation(p) for p in args.compare))
        elif args.accept and args.worker and args.image_id and not args.compare:
            report = accept_directory(args.accept, args.worker, args.image_id)
        elif not any((args.worker, args.accept, args.image_id, args.compare)):
            report = verify_artifacts()
        else:
            raise BoundedCompilerEmissionError("placement invocation rejected")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError):
        print("bounded placement verification rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
