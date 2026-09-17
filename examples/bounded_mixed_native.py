"""Shared residency schedule consumed by a closed C11 / mixed CPU-GPU worker."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from examples import bounded_native_io as previous
from examples import bounded_plan_native_bridge as bridge
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
from tuc.runtime.residency import ResidencySpace, plan_residency

CONTEXT = ROOT / "docker/mixed-native"
TARGETS = ("c11", "mixed")
STATIC_FAULTS = (
    "schedule-count",
    "schedule-slot",
    "schedule-space",
    "schedule-order",
    "schedule-size",
    "schedule-duplicate",
)
MUTATIONS = (*bridge.chain.MUTATIONS, *STATIC_FAULTS, "skip-publish")


def compile_case(target):
    if type(target) is not str or target not in TARGETS:
        raise BoundedCompilerEmissionError("mixed target rejected")
    payload = bridge.chain.parse_source()
    bridge.chain.emit(payload)
    graph = source_intent_to_triton_metadata(source_intent_from_mapping(payload)).to_compute_graph()
    host = ResidencySpace("host", MemoryDomainKind.HOST_RAM)
    if target == "c11":
        capabilities = [bridge.capability("c11")]
        spaces = {"bounded-c11": host}
    else:
        capabilities = [
            BackendCapability(
                "bounded-c11",
                frozenset({OperationKind.ELEMENTWISE}),
                memory_domain=MemoryDomainKind.HOST_RAM,
            ),
            BackendCapability(
                "bounded-cuda",
                frozenset({OperationKind.MATMUL, OperationKind.REDUCTION}),
                memory_domain=MemoryDomainKind.UNKNOWN,
            ),
        ]
        spaces = {
            "bounded-c11": host,
            "bounded-cuda": ResidencySpace("accelerator", MemoryDomainKind.UNKNOWN),
        }
    compiled = compile_graph(graph, capabilities)
    return compiled, plan_residency(compiled.hac_ir.graph, compiled.partition_plan, spaces, host)


def snapshot(target):
    compiled, residency = compile_case(target)
    return {
        "schema_version": "tuc.bounded_mixed_native_plan.v0",
        "target": target,
        "hac_ir": compiled.dump(IRStage.HAC_IR),
        "hs_ir": compiled.dump(IRStage.HS_IR),
        "partition": compiled.dump_runtime_plan(),
        "decisions": compiled.dump_decision_report(),
        "residency": json.loads(json.dumps(asdict(residency))),
        "copy_bytes": residency.copy_bytes,
        "latency_ns": None,
        "energy_pj": None,
        "normal_runtime_admission": False,
    }


def lower(value, target):
    bridge._bounded_metadata(value)
    expected = snapshot(target)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("mixed residency plan rejected")
    _, plan = compile_case(target)
    tensors = {"a": 0, "b": 1, "projection": 2, "activated": 3, "row_sum": 4}
    # Names are resolved from the checked source graph rather than an IR dump.
    compiled, _ = compile_case(target)
    operations = {op.name: i for i, op in enumerate(compiled.hac_ir.graph.operations, 1)}
    lines = [
        "#ifndef TUC_RESIDENCY_PLAN_H",
        "#define TUC_RESIDENCY_PLAN_H",
        f"#define TUC_MIXED {int(target == 'mixed')}",
        f"#define TUC_RESIDENCY_BYTES {sum(b.bytes for b in plan.buffers)}U",
        '#define TUC_MIXED_CODE_DIGEST "'
        + _digest_payload(
            {t: bridge.chain.expected_observation(t)["code_digest"] for t in bridge.chain.TARGETS}
        )
        + '"',
        f'#define TUC_RESIDENCY_DIGEST "{_digest_payload(expected)}"',
        f"#define TUC_BUFFER_COUNT {len(plan.buffers)}U",
        f"#define TUC_RESIDENCY_COUNT {len(plan.steps)}U",
        "static const struct tuc_buffer TUC_BUFFERS[] = {",
    ]
    for b in plan.buffers:
        lines.append(f"  {{{tensors[b.tensor]}U, {int(b.space.name != 'host')}U, {b.bytes}U}},")
    lines += ["};", "static const struct tuc_event TUC_EVENTS[] = {"]
    for s in plan.steps:
        kind = {"bind_input": 0, "copy": 1, "execute": 2, "publish_output": 3}[s.kind]
        op = operations[s.operation] if s.operation else 0
        space = int(s.backend == "bounded-cuda")
        a, b = (*s.inputs, 255, 255)[:2]
        out = s.outputs[0] if s.outputs else 255
        lines.append(f"  {{{kind}U, {op}U, {space}U, {a}U, {b}U, {out}U}},")
    return "\n".join([*lines, "};", "#endif", ""])


def artifact_files():
    bridge.chain.verify_artifacts()
    files = {
        n: _read_bounded_file(bridge.chain.CONTEXT / n).decode()
        for n in ("generated.c", "generated.h", "kernels.cuh", "inputs.h", "oracle.h", "common.h")
    }
    for target in TARGETS:
        plan = snapshot(target)
        files[f"{target}_plan.json"] = json.dumps(plan, indent=2, sort_keys=True) + "\n"
        files[f"{target}_plan.h"] = lower(plan, target)
    files["common.h"] = bridge._replace_once(
        files["common.h"], '  printf("{', '  residency_emit();\n  printf("{'
    )
    files["common.h"] = bridge._replace_once(files["common.h"], r'false}\n",', r'false}}\n",')
    files["common.h"] = bridge._replace_once(
        files["common.h"],
        "tuc.bounded_chain_observation.v0",
        "tuc.bounded_mixed_numeric_observation.v0",
    )
    # Toolchain hardening and numerical mutation recipes are inherited unchanged.
    for target in ("c11", "cuda"):
        key = f"build-{target}.sh"
        text = _read_bounded_file(bridge.chain.CONTEXT / key).decode()
        prefix = "compile generated.c " if target == "c11" else "compile "
        added = [
            f"{prefix}/out/{name} -DTUC_SCHEDULE_FAULT={i}"
            for i, name in enumerate(STATIC_FAULTS, 1)
        ]
        added += [f"{prefix}/out/skip-publish -DTUC_SKIP_PUBLISH=1"]
        if target == "cuda":
            added += ["compile /out/skip-transfer -DTUC_SKIP_TRANSFER=1"]
            text = text.replace(
                '"$@" device.cu -o "$output"', '"$@" device.cu host-kernels.o -o "$output"'
            )
            host_compile = (
                "gcc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math "
                "-ffp-contract=off -fexcess-precision=standard -fstack-protector-strong -fPIE "
                "-D_FORTIFY_SOURCE=3 -Dtuc_projection=tuc_host_projection "
                "-Dtuc_relu=tuc_host_relu -Dtuc_sum_axis1=tuc_host_sum_axis1 "
                "-c generated.c -o host-kernels.o\n"
            )
            text = bridge._replace_once(
                text, "compile /out/proof\n", host_compile + "compile /out/proof\n"
            )
            # ReLU runs in C11 in the mixed placement, including wrong-code controls.
            text = bridge._replace_once(
                text,
                "compile /out/bypass-relu\n",
                "cp generated.c reviewed.c\n"
                "sed 's/value < 0.0F ? 0.0F : value/value/' reviewed.c > generated.c\n"
                + host_compile
                + "compile /out/bypass-relu\n",
            )
            text = bridge._replace_once(
                text,
                "compile /out/late-relu\n",
                "compile /out/late-relu\ncp reviewed.c generated.c\n" + host_compile,
            )
        files[key] = bridge._replace_once(
            text, prefix + "/out/proof\n", prefix + "/out/proof\n" + "\n".join(added) + "\n"
        )
    docker = _read_bounded_file(bridge.chain.CONTEXT / "Dockerfile").decode()
    docker = docker.replace("composed-chain", "mixed-native")
    for target in ("c11", "cuda"):
        header = "c11" if target == "c11" else "mixed"
        copy = (
            f"COPY docker/mixed-native/{header}_plan.h docker/mixed-native/worker.h "
            "docker/mixed-native/contract.h ./\n"
        )
        if target == "cuda":
            copy += "COPY docker/mixed-native/generated.c docker/mixed-native/generated.h ./\n"
        docker = bridge._replace_once(
            docker,
            f"RUN --network=none sh build-{target}.sh",
            copy + f"RUN --network=none sh build-{target}.sh",
        )
    docker = docker.replace(
        "/out/nonfinite /opt/tuc/",
        "/out/nonfinite "
        + " ".join(f"/out/{m}" for m in (*STATIC_FAULTS, "skip-publish"))
        + " /opt/tuc/",
    )
    cuda_copy = "COPY --from=cuda-build --chmod=0555 /out/proof"
    docker = bridge._replace_once(docker, cuda_copy, cuda_copy + " /out/skip-transfer")
    files["Dockerfile"] = docker
    files["Dockerfile.dockerignore"] = "**\n!docker/\n!docker/mixed-native/\n" + "".join(
        f"!docker/mixed-native/{n}\n"
        for n in (*files, "host.c", "device.cu", "worker.h", "contract.h")
        if not n.endswith(".json") and n != "Dockerfile"
    )
    operator = _read_bounded_file(
        bridge.chain.ROOT / "scripts/run_bounded_composed_chain.sh"
    ).decode()
    operator = (
        operator.replace("bounded_composed_chain", "bounded_mixed_native")
        .replace("composed-chain", "mixed-native")
        .replace("tuc-chain-", "tuc-mixed-")
    )
    operator = bridge._replace_once(
        operator, 'cd "$(dirname "$0")/.."', 'cd "$(dirname "$0")/../.."'
    )
    operator = operator.replace("--cuda-reviewed) target=cuda", "--cuda-reviewed) target=mixed")
    operator = operator.replace('"$target" = cuda', '"$target" = mixed')
    operator = operator.replace('--target "$target-runtime"', '--target "$build_target-runtime"')
    operator = operator.replace(
        "export PYTHONPATH=.:src",
        'build_target=c11\nif [ "$target" = mixed ]; then build_target=cuda; fi\n'
        'extra=""\nif [ "$target" = mixed ]; then extra=skip-transfer; fi\nexport PYTHONPATH=.:src',
    )
    operator = bridge._replace_once(
        operator,
        "over-budget nonfinite; do",
        "over-budget nonfinite " + " ".join((*STATIC_FAULTS, "skip-publish")) + " $extra; do",
    )
    files["operator.sh"] = operator.replace("Composed chain", "Shared residency").replace(
        "seven negative probes", "all negative probes"
    )
    return files


def verify_artifacts():
    for name, text in artifact_files().items():
        if _read_bounded_file(CONTEXT / name) != text.encode():
            raise BoundedCompilerEmissionError("mixed native artifact drift")
    return {
        "schema_version": "tuc.bounded_mixed_native_verification.v0",
        "status": "PASS",
        "normal_runtime_admission": False,
    }


def program_digest():
    paths = [
        CONTEXT / n for n in (*artifact_files(), "host.c", "device.cu", "worker.h", "contract.h")
    ]
    paths += [ROOT / "examples/bounded_mixed_native.py", ROOT / "src/tuc/runtime/residency.py"]
    return _digest_payload(
        {
            p.relative_to(ROOT).as_posix(): "sha256:" + sha256(_read_bounded_file(p)).hexdigest()
            for p in paths
        }
    )


def counters(target, runs):
    _, plan = compile_case(target)
    result = {
        "completed_steps": len(plan.steps),
        "cpu_calls": 0,
        "gpu_calls": 0,
        "upload_calls": 0,
        "download_calls": 0,
        "upload_bytes": 0,
        "download_bytes": 0,
    }
    for step in plan.steps:
        if step.kind == "execute":
            result["gpu_calls" if step.backend == "bounded-cuda" else "cpu_calls"] += 1
        elif step.kind == "copy":
            dst = plan.buffers[step.outputs[0]]
            prefix = "download" if dst.space.name == "host" else "upload"
            result[prefix + "_calls"] += 1
            result[prefix + "_bytes"] += dst.bytes
    return {k: v * runs for k, v in result.items()}


def expected_numeric(target, preflight=False):
    if type(preflight) is not bool:
        raise BoundedCompilerEmissionError("mixed preflight mode rejected")
    original = "c11" if target == "c11" else "cuda"
    value = bridge.chain.expected_observation(original, preflight)
    value["schema_version"] = "tuc.bounded_mixed_numeric_observation.v0"
    if target == "mixed":
        value["target"] = "mixed"
        value["code_digest"] = _digest_payload(
            {t: bridge.chain.expected_observation(t)["code_digest"] for t in bridge.chain.TARGETS}
        )
    value["tensor_bytes"] = (
        0 if preflight else sum(b.bytes for b in compile_case(target)[1].buffers)
    )
    return value


def validate_observation(value, target, preflight=False, mutation=None):
    bridge._bounded_metadata(value)
    if mutation is not None and (type(mutation) is not str or not mutation):
        raise BoundedCompilerEmissionError("mixed mutation mode rejected")
    expected = expected_numeric(target, preflight)
    count = counters(target, 0 if preflight else 11)
    if mutation:
        if preflight or mutation not in (
            *MUTATIONS,
            *(("skip-transfer",) if target == "mixed" else ()),
        ):
            raise BoundedCompilerEmissionError("mixed mutation rejected")
        expected.update(
            status="ERROR",
            cases_passed=0,
            failed_run_index=0,
            scalar_checks=0,
            outputs_differing_from_reference64=0,
            numeric_contract_passed=False,
            execution_policy_passed=False,
            repeated_baseline_passed=False,
        )
        if mutation in STATIC_FAULTS:
            expected.update(
                reason_code="target_not_ready",
                failed_run_index=-1,
                generated_function_calls=0,
                tensor_bytes=0,
            )
            count = counters(target, 0)
        elif mutation in ("skip-transfer", "skip-publish"):
            expected["reason_code"] = "execution_failed"
            expected["generated_function_calls"] = 1 if mutation == "skip-transfer" else 3
            count = counters(target, 1)
            if mutation == "skip-publish":
                count["completed_steps"] -= 1
            else:
                count.update(
                    completed_steps=5,
                    cpu_calls=0,
                    gpu_calls=1,
                    upload_calls=2,
                    upload_bytes=1064,
                    download_calls=0,
                    download_bytes=0,
                )
        else:
            expected.update(reason_code="numeric_contract_mismatch", generated_function_calls=3)
            count = counters(target, 1)
    report = {
        "schema_version": "tuc.bounded_mixed_native_observation.v0",
        "plan_digest": _digest_payload(snapshot(target)),
        "residency": count,
        "numeric_observation": expected,
    }
    if _canonical_json(value) != _canonical_json(report):
        raise BoundedCompilerEmissionError("mixed native observation rejected")
    return report


def build_record(value, target, image_id):
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("mixed image rejected")
    observation = validate_observation(value, target)
    verify_artifacts()
    return {
        "schema_version": "tuc.bounded_mixed_native_record.v0",
        "observation": observation,
        "program_files_digest": program_digest(),
        "operator_image_id": image_id,
        "previous_io_program_digest": previous.program_digest(),
        "provenance": "same_maintainer_operator",
        "normal_runtime_admission": False,
    }


def compare_records(cpu, mixed):
    for target, value in zip(TARGETS, (cpu, mixed), strict=True):
        bridge._bounded_metadata(value)
        if type(value) is not dict or _canonical_json(value) != _canonical_json(
            build_record(value.get("observation"), target, value.get("operator_image_id"))
        ):
            raise BoundedCompilerEmissionError("mixed record binding rejected")
    if snapshot("c11")["hac_ir"] != snapshot("mixed")["hac_ir"]:
        raise BoundedCompilerEmissionError("mixed HAC-IR drift")
    return {
        "schema_version": "tuc.bounded_mixed_native_comparison.v0",
        "status": "PASS",
        "c11_record_digest": _digest_payload(cpu),
        "mixed_record_digest": _digest_payload(mixed),
        "source_intent_digest": bridge.chain.INTENT_DIGEST,
        "placement": ["bounded-cuda", "bounded-c11", "bounded-cuda"],
        "scalar_checks_per_target": 363,
        "copy_bytes_per_mixed_run": 2516,
        "core_residency_schedule": True,
        "normal_runtime_admission": False,
        "latency_ns": None,
        "energy_pj": None,
        "blocked_claims": [
            "general_native_runtime",
            "arbitrary_inputs",
            "dynamic_shapes",
            "performance",
            "independent_reproduction",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--image-id")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--negative", choices=(*MUTATIONS, "skip-transfer"))
    parser.add_argument("--compare", nargs=2, type=Path)
    args = parser.parse_args()
    try:
        if args.compare and not any(
            (args.target, args.validate, args.image_id, args.preflight, args.negative)
        ):
            report = compare_records(*(load_observation(p) for p in args.compare))
        elif args.target and args.validate and not args.compare:
            value = load_observation(args.validate)
            if args.image_id and not args.preflight and not args.negative:
                report = build_record(value, args.target, args.image_id)
            elif not args.image_id:
                report = validate_observation(value, args.target, args.preflight, args.negative)
            else:
                raise BoundedCompilerEmissionError("conflicting mixed modes")
        elif not any(
            (args.target, args.validate, args.image_id, args.preflight, args.negative, args.compare)
        ):
            report = verify_artifacts()
        else:
            raise BoundedCompilerEmissionError("mixed invocation rejected")
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError):
        print("bounded mixed native verification rejected", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
