"""Fixed native fanout with one immutable projection and two published outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from examples import bounded_native_placements as previous
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.frontend import (
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.ir.modules import IRStage
from tuc.runtime.overrides import RuntimeOverrideAction, RuntimeOverrideRule, RuntimeOverrideSet
from tuc.runtime.residency import ResidencySpace, plan_residency

CHAIN = previous.CHAIN
FP = CHAIN.fp
CONTEXT = ROOT / "docker/native-fanout"
PROFILES = ("cccc", "gccc", "gggg")
STATIC_FAULTS = (*previous.STATIC_FAULTS, "schedule-fanout", "schedule-output")
MUTATIONS = (
    *CHAIN.MUTATIONS,
    *STATIC_FAULTS,
    "skip-publish",
    "skip-second-publish",
    "invalidate-shared",
    "clobber-shared",
)
SOURCE = """import triton
import triton.language as tl

@triton.jit
def matmul_fanout(a, b, raw, positive):
    projection = tl.dot(a, b)
    activated = tl.where(projection > 0, projection, 0)
    row_raw = tl.sum(projection, axis=1)
    row_positive = tl.sum(activated, axis=1)
    tl.store(raw, row_raw)
    tl.store(positive, row_positive)
"""
INTENT_DIGEST = "sha256:011c97afb0e42b0e08067123572db253fb82eddd122c02e1eff71def47636e20"
CONTRACT = {
    **CHAIN.CONTRACT,
    "schema_version": "tuc.bounded_fanout_numeric_contract.v0",
    "reference": "[sum_c(sum_k(a*b)), sum_c(max(sum_k(a*b),0))]_over_exact_binary32_inputs",
    "operation_order": ["sequential_matmul", "relu", "raw_sum_axis1", "positive_sum_axis1"],
    "output_order": ["row_raw", "row_positive"],
    "shared_projection": "immutable",
}


def parse_source():
    return ingest_triton_module_source_to_source_intent(
        SOURCE,
        source_name="research_native_fanout",
        kernel_name="matmul_fanout",
        tensor_shapes={"a": (33, 7), "b": (7, 5), "raw": (33,), "positive": (33,)},
    ).parser_result.source_intent_payload


def checked_intent(payload):
    previous.BRIDGE._bounded_metadata(payload)
    if _digest_payload(payload) != INTENT_DIGEST:
        raise BoundedCompilerEmissionError("fanout Source Intent rejected")
    module = source_intent_from_mapping(payload)
    if tuple(op.family for op in module.operations) != (
        "matmul",
        "elementwise",
        "reduction",
        "reduction",
    ):
        raise BoundedCompilerEmissionError("fanout operation family rejected")
    matmul, relu, raw, positive = module.operations
    tensors = {t.name: t for t in module.tensors}
    if (
        relu.inputs != matmul.outputs
        or raw.inputs != matmul.outputs
        or positive.inputs != relu.outputs
        or dict(relu.attributes) != {"elementwise_kind": "relu"}
        or dict(raw.attributes) != {"axis": 1}
        or dict(positive.attributes) != {"axis": 1}
        or tuple(tensors[n].shape for n in matmul.inputs) != ((33, 7), (7, 5))
        or any(t.dtype != "float32" for t in module.tensors)
    ):
        raise BoundedCompilerEmissionError("fanout typed semantics rejected")
    return module


def compile_case(profile):
    if type(profile) is not str or profile not in PROFILES:
        raise BoundedCompilerEmissionError("fanout profile rejected")
    graph = source_intent_to_triton_metadata(checked_intent(parse_source())).to_compute_graph()
    supported = frozenset(
        {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
    )
    caps = [
        BackendCapability("bounded-c11", supported, memory_domain=MemoryDomainKind.HOST_RAM),
        BackendCapability("bounded-cuda", supported, memory_domain=MemoryDomainKind.UNKNOWN),
    ]
    overrides = RuntimeOverrideSet(
        tuple(
            RuntimeOverrideRule(
                op.name,
                RuntimeOverrideAction.REQUIRE_BACKEND,
                "bounded-c11" if p == "c" else "bounded-cuda",
            )
            for op, p in zip(graph.operations, profile, strict=True)
        )
    )
    compiled = compile_graph(graph, caps, runtime_overrides=overrides)
    host = ResidencySpace("host", MemoryDomainKind.HOST_RAM)
    spaces = {
        "bounded-c11": host,
        "bounded-cuda": ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN),
    }
    used = {a.backend_name: spaces[a.backend_name] for a in compiled.partition_plan.assignments}
    return compiled, plan_residency(compiled.hac_ir.graph, compiled.partition_plan, used, host)


def snapshot(profile):
    compiled, plan = compile_case(profile)
    return {
        "schema_version": "tuc.bounded_fanout_plan.v0",
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
    previous.BRIDGE._bounded_metadata(value)
    if _canonical_json(value) != _canonical_json(snapshot(profile)):
        raise BoundedCompilerEmissionError("fanout snapshot rejected")
    compiled, plan = compile_case(profile)
    tensors = {
        n: i for i, n in enumerate(("a", "b", "projection", "activated", "row_raw", "row_positive"))
    }
    ops = {op.name: i for i, op in enumerate(compiled.hac_ir.graph.operations, 1)}
    lines = [f"static const struct tuc_buffer buffers_{profile}[] = {{"]
    for b in plan.buffers:
        lines.append(f"  {{{tensors[b.tensor]}U, {int(b.space.name != 'host')}U, {b.bytes}U}},")
    lines += ["};", f"static const struct tuc_event events_{profile}[] = {{"]
    for s in plan.steps:
        kind = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}[s.kind]
        opcode = ops[s.operation] if s.operation else 0
        a, b = (*s.inputs, 255, 255)[:2]
        out = s.outputs[0] if s.outputs else 255
        lines.append(
            f"  {{{kind}U, {opcode}U, {int(s.backend == 'bounded-cuda')}U, {a}U, {b}U, {out}U}},"
        )
    return "\n".join([*lines, "};", ""])


def numeric_files():
    payload = parse_source()
    checked_intent(payload)
    files = {
        n: _read_bounded_file(CHAIN.CONTEXT / n).decode()
        for n in ("generated.c", "generated.h", "kernels.cuh", "inputs.h")
    }
    cases = CHAIN.corpus()
    refs = [FP.reference(c["a"], c["b"]) + CHAIN.reference(c) for c in cases]
    ordered = [FP.ordered_reference(c) + CHAIN.ordered_reference(c) for c in cases]
    rounded = 0
    for i in (*range(10), 0):
        for value, (exact, budget) in zip(ordered[i], refs[i], strict=True):
            if abs(Fraction(value) - exact) > budget:
                raise BoundedCompilerEmissionError("fanout corpus exceeds contract")
            rounded += value != float(exact)
    plan = {
        "schema_version": "tuc.bounded_fanout_emission.v0",
        "source_module_digest": _digest_text(SOURCE),
        "source_intent_digest": INTENT_DIGEST,
        "c11_code_digest": _digest_text(files["generated.c"]),
        "cuda_code_digest": _digest_text(files["kernels.cuh"]),
        "corpus_digest": _digest_payload(cases),
        "contract_digest": _digest_payload(CONTRACT),
        "operation_order": ["matmul", "relu", "raw_sum_axis1", "positive_sum_axis1"],
        "output_names": ["row_raw", "row_positive"],
        "output_shapes": [[33], [33]],
        "case_count": 10,
        "runs": 11,
        "scalar_checks": 726,
        "expected_rounded_outputs": rounded,
        "normal_runtime_admission": False,
    }
    for macro, key in (("INTENT", "source_intent_digest"), ("CONTRACT", "contract_digest")):
        files["inputs.h"] = re.sub(
            rf'#define TUC_{macro}_DIGEST "[^"]+"',
            f'#define TUC_{macro}_DIGEST "{plan[key]}"',
            files["inputs.h"],
        )
    files["inputs.h"] = files["inputs.h"].replace(
        "#define TUC_TENSOR_BYTES 2516U",
        "#define TUC_TENSOR_BYTES 2648U\n#define TUC_OUTPUT_VALUES 66U",
    )
    oracle = ["#ifndef TUC_FANOUT_ORACLE_H", "#define TUC_FANOUT_ORACLE_H"]
    for name in ("LOWER", "UPPER", "REFERENCE64", "ORDERED"):
        oracle.append(f"static const double TUC_{name}[10][66] = {{")
        for i, bounds in enumerate(refs):
            values = (
                ordered[i]
                if name == "ORDERED"
                else [
                    float(x) if name == "REFERENCE64" else FP.interval(x, e)[name == "UPPER"]
                    for x, e in bounds
                ]
            )
            oracle.append("  {" + ", ".join(map(FP._hex, values)) + "},")
        oracle.append("};")
    files["oracle.h"] = "\n".join([*oracle, "#endif", ""])
    for name, value in (
        ("emission_plan", plan),
        ("numeric_contract", CONTRACT),
        ("source_intent", payload),
    ):
        files[name + ".json"] = json.dumps(value, indent=2, sort_keys=True) + "\n"
    return files


def artifact_files():
    previous.verify_artifacts()
    files = numeric_files()
    for name in (
        "host.c",
        "device.cu",
        "common.h",
        "build-c11.sh",
        "build-cuda.sh",
        "Dockerfile",
        "contract_test.c",
    ):
        files[name] = _read_bounded_file(previous.CONTEXT / name).decode()
    rows, tables = [], []
    for profile in PROFILES:
        value = snapshot(profile)
        files[f"{profile}_plan.json"] = json.dumps(value, indent=2, sort_keys=True) + "\n"
        tables.append(lower(value, profile))
        plan = value["residency"]
        mask = int(profile.replace("c", "0").replace("g", "1"), 2)
        rows.append(
            f'  {{"{profile}", "{_digest_payload(value)}", {mask}U, '
            f"{len(plan['buffers'])}U, {len(plan['steps'])}U, "
            f"{sum(b['bytes'] for b in plan['buffers'])}U, buffers_{profile}, events_{profile}}},"
        )
    emission = json.loads(files["emission_plan.json"])
    code = _digest_payload({t: emission[f"{t}_code_digest"] for t in CHAIN.TARGETS})
    files["plans.h"] = "\n".join(
        [
            "#ifndef TUC_FANOUT_PLANS_H",
            "#define TUC_FANOUT_PLANS_H",
            f'#define TUC_MATRIX_CODE_DIGEST "{code}"',
            *tables,
            "static const struct tuc_profile profiles[] = {",
            *rows,
            "};",
            "#endif",
            "",
        ]
    )
    files["device.cu"] = files["device.cu"].replace("opcode == 3U", "opcode >= 3U && opcode <= 4U")
    common = files["common.h"].replace(
        "tuc.bounded_placement_numeric.v0", "tuc.bounded_fanout_numeric.v0"
    )
    common = common.replace("TUC_ROWS", "TUC_OUTPUT_VALUES")
    common = common.replace(
        r"\"operation_order\":[\"matmul\",\"relu\",\"sum_axis1\"]",
        r"\"operation_order\":[\"matmul\",\"relu\",\"raw_sum_axis1\",\"positive_sum_axis1\"]",
    )
    common = common.replace(
        r"\"output_shape\":[%u]",
        r"\"output_names\":[\"row_raw\",\"row_positive\"],\"output_shapes\":[[33],[33]],\"output_values\":%u",
    )
    files["common.h"] = common
    for name in ("build-c11.sh", "build-cuda.sh"):
        prefix = "compile generated.c" if name == "build-c11.sh" else "compile"
        extra = [
            f"{prefix} /out/schedule-fanout -DTUC_SCHEDULE_FAULT=8",
            f"{prefix} /out/schedule-output -DTUC_SCHEDULE_FAULT=9",
            f"{prefix} /out/skip-second-publish -DTUC_SKIP_SECOND_PUBLISH=1",
            f"{prefix} /out/invalidate-shared -DTUC_INVALIDATE_SHARED=1",
            f"{prefix} /out/clobber-shared -DTUC_CLOBBER_SHARED=1",
        ]
        files[name] = previous.BRIDGE._replace_once(
            files[name],
            f"{prefix} /out/proof\n",
            f"{prefix} /out/proof\n" + "\n".join(extra) + "\n",
        )
    files["Dockerfile"] = files["Dockerfile"].replace("native-placements", "native-fanout")
    files["Dockerfile"] = files["Dockerfile"].replace(
        "/out/proof /out/",
        "/out/proof /out/schedule-fanout /out/schedule-output /out/skip-second-publish "
        "/out/invalidate-shared /out/clobber-shared /out/",
    )
    files["Dockerfile"] = files["Dockerfile"].replace('"ccc"', '"cccc"')
    files["contract_test.c"] = (
        files["contract_test.c"]
        .replace("p < 8U", "p < 3U")
        .replace(r"\"profiles_checked\":8", r"\"profiles_checked\":3")
    )
    files["contract_test.c"] = files["contract_test.c"].replace(
        "tuc.placement_contract_sanitizer.v0", "tuc.fanout_contract_sanitizer.v0"
    )
    files["Dockerfile.dockerignore"] = "**\n!docker/\n!docker/native-fanout/\n" + "".join(
        f"!docker/native-fanout/{n}\n"
        for n in (*files, "contract.h", "worker.h")
        if not n.endswith(".json")
    )
    return files


def verify_artifacts():
    for name, text in artifact_files().items():
        if _read_bounded_file(CONTEXT / name) != text.encode():
            raise BoundedCompilerEmissionError("fanout artifact drift")
    return {
        "schema_version": "tuc.bounded_fanout_verification.v0",
        "status": "PASS",
        "profiles": list(PROFILES),
        "normal_runtime_admission": False,
    }


def program_digest():
    paths = [CONTEXT / n for n in (*artifact_files(), "contract.h", "worker.h", "operator.sh")]
    paths += [
        ROOT / "examples/bounded_native_fanout.py",
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
        raise BoundedCompilerEmissionError("fanout worker rejected")
    return ("cccc",) if worker == "c11" else PROFILES


def counts(plan, steps, repeats):
    result = previous.counts(plan, steps, repeats)
    result.update(
        {k: 0 for k in ("projection_copy_calls", "shared_consumer_calls", "published_outputs")}
    )
    for s in steps:
        if s.kind == "copy" and plan.buffers[s.outputs[0]].tensor == "projection":
            result["projection_copy_calls"] += repeats
        if s.kind == "execute" and plan.buffers[s.inputs[0]].tensor == "projection":
            result["shared_consumer_calls"] += repeats
        if s.kind == "publish_output":
            result["published_outputs"] += repeats
    return result


def expected_observation(profile, worker, preflight=False, mutation=None):
    if (
        type(profile) is not str
        or profile not in profiles_for(worker)
        or type(preflight) is not bool
    ):
        raise BoundedCompilerEmissionError("fanout mode rejected")
    allowed = (*MUTATIONS, *(("skip-transfer",) if profile != "cccc" else ()), "unknown-profile")
    if mutation is not None and (type(mutation) is not str or mutation not in allowed or preflight):
        raise BoundedCompilerEmissionError("fanout mutation rejected")
    _, plan = compile_case(profile)
    emission = json.loads(numeric_files()["emission_plan.json"])
    code = (
        emission["c11_code_digest"]
        if worker == "c11"
        else _digest_payload({t: emission[f"{t}_code_digest"] for t in CHAIN.TARGETS})
    )
    numeric = {
        "schema_version": "tuc.bounded_fanout_numeric.v0",
        "target": profile,
        "mode": "preflight" if preflight else "execute",
        "status": "PASS",
        "reason_code": "none",
        **{
            k: emission[k]
            for k in (
                "source_intent_digest",
                "corpus_digest",
                "contract_digest",
                "operation_order",
                "output_names",
                "output_shapes",
            )
        },
        "code_digest": code,
        "output_values": 66,
        "case_count": 10,
        "cases_passed": 0 if preflight else 11,
        "failed_run_index": -1,
        "generated_function_calls": 0 if preflight else 44,
        "scalar_checks": 0 if preflight else 726,
        "tensor_bytes": 0 if preflight else sum(b.bytes for b in plan.buffers),
        "outputs_differing_from_reference64": 0
        if preflight
        else emission["expected_rounded_outputs"],
        "security_boundary_passed": True,
        "numeric_contract_passed": not preflight,
        "execution_policy_passed": not preflight,
        "repeated_baseline_passed": not preflight,
        "raw_values_serialized": False,
    }
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
            if mutation in ("skip-publish", "skip-second-publish"):
                steps = tuple(
                    s
                    for s in steps
                    if s.kind != "publish_output"
                    or (
                        mutation == "skip-second-publish"
                        and plan.buffers[s.inputs[0]].tensor == "row_raw"
                    )
                )
                reason = "execution_failed"
            elif mutation in ("skip-transfer", "invalidate-shared"):
                index = next(
                    i
                    for i, s in enumerate(steps)
                    if (
                        mutation == "skip-transfer"
                        and s.kind == "copy"
                        and plan.buffers[s.inputs[0]].tensor not in ("a", "b")
                    )
                    or (
                        mutation == "invalidate-shared"
                        and s.kind == "execute"
                        and plan.buffers[s.outputs[0]].tensor == "row_raw"
                    )
                )
                steps = steps[:index]
                reason = "execution_failed"
            counter = counts(plan, steps, 1)
            numeric.update(
                reason_code=reason,
                generated_function_calls=counter["cpu_calls"] + counter["gpu_calls"],
            )
    return {
        "schema_version": "tuc.bounded_fanout_observation.v0",
        "worker": worker,
        "profile": profile,
        "plan_digest": _digest_payload(snapshot(profile)),
        "residency": counter,
        "numeric_observation": numeric,
    }


def validate_observation(value, profile, worker, preflight=False, mutation=None):
    previous.BRIDGE._bounded_metadata(value)
    expected = expected_observation(profile, worker, preflight, mutation)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("fanout observation rejected")
    return expected


def build_record(observations, worker, image_id):
    previous.BRIDGE._bounded_metadata(observations)
    profiles = profiles_for(worker)
    if type(observations) is not list or len(observations) != len(profiles):
        raise BoundedCompilerEmissionError("fanout coverage rejected")
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("fanout image rejected")
    for profile, value in zip(profiles, observations, strict=True):
        validate_observation(value, profile, worker)
    verify_artifacts()
    return {
        "schema_version": "tuc.bounded_fanout_record.v0",
        "worker": worker,
        "observations": observations,
        "operator_image_id": image_id,
        "program_files_digest": program_digest(),
        "previous_placements_program_digest": previous.program_digest(),
        "provenance": "same_maintainer_operator",
        "normal_runtime_admission": False,
    }


def accept_directory(directory, worker, image_id):
    observations = []
    for profile in profiles_for(worker):
        validate_observation(
            load_observation(directory / f"{profile}-preflight.json"), profile, worker, True
        )
        observations.append(load_observation(directory / f"{profile}-execution.json"))
        for mutation in (*MUTATIONS, *(("skip-transfer",) if profile != "cccc" else ())):
            validate_observation(
                load_observation(directory / f"{profile}-{mutation}.json"),
                profile,
                worker,
                mutation=mutation,
            )
    validate_observation(
        load_observation(directory / "unknown-profile.json"),
        "cccc",
        worker,
        mutation="unknown-profile",
    )
    if worker == "c11":
        validate_observation(load_observation(directory / "sanitized.json"), "cccc", worker)
        if load_observation(directory / "contract-sanitized.json") != {
            "schema_version": "tuc.fanout_contract_sanitizer.v0",
            "status": "PASS",
            "profiles_checked": 3,
            "invalid_selectors": 4,
            "bitflip_rejections": 8736,
        }:
            raise BoundedCompilerEmissionError("fanout contract sanitizer rejected")
    return build_record(observations, worker, image_id)


def compare_records(cpu, matrix):
    for value, worker in ((cpu, "c11"), (matrix, "matrix")):
        previous.BRIDGE._bounded_metadata(value)
        if type(value) is not dict or _canonical_json(value) != _canonical_json(
            build_record(value.get("observations"), worker, value.get("operator_image_id"))
        ):
            raise BoundedCompilerEmissionError("fanout record rejected")
    if len({snapshot(p)["hac_ir"] for p in PROFILES}) != 1:
        raise BoundedCompilerEmissionError("fanout-dependent HAC-IR rejected")
    return {
        "schema_version": "tuc.bounded_fanout_comparison.v0",
        "status": "PASS",
        "source_intent_digest": INTENT_DIGEST,
        "matrix_scalar_checks": 2178,
        "one_matrix_image": True,
        "placements": [{"profile": o["profile"], **o["residency"]} for o in matrix["observations"]],
        "c11_record_digest": _digest_payload(cpu),
        "matrix_record_digest": _digest_payload(matrix),
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
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
            raise BoundedCompilerEmissionError("fanout invocation rejected")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError):
        print("bounded fanout verification rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
