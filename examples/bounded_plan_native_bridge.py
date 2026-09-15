"""Bounded core-plan-to-native dispatch; no normal-runtime native admission."""

from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path

from examples import bounded_composed_chain as chain
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.frontend import source_intent_from_mapping, source_intent_to_triton_metadata
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.ir.modules import IRStage

CONTEXT = ROOT / "docker/plan-native-bridge"
TARGETS = chain.TARGETS
PLAN_MUTATIONS = ("unknown-opcode", "wrong-order", "input-overwrite",
                  "missing-step", "wrong-target")
MUTATIONS = (*chain.MUTATIONS, *PLAN_MUTATIONS)


def _bounded_metadata(value: object) -> None:
    _assert_plain_json(value)
    pending = [value]
    characters = 0
    while pending:
        item = pending.pop()
        if type(item) is str:
            characters += len(item)
            if len(item) > 16384 or characters > 65536:
                raise BoundedCompilerEmissionError("bridge text budget exceeded")
        elif type(item) is int and item.bit_length() > 63:
            raise BoundedCompilerEmissionError("bridge integer budget exceeded")
        elif type(item) is list:
            pending.extend(item)
        elif type(item) is dict:
            pending.extend(item.keys())
            pending.extend(item.values())
    if len(_canonical_json(value).encode()) > 65536:
        raise BoundedCompilerEmissionError("bridge metadata byte budget exceeded")


def capability(target: str) -> BackendCapability:
    if type(target) is not str or target not in TARGETS:
        raise BoundedCompilerEmissionError("bridge target rejected")
    return BackendCapability(
        name=f"bounded-{target}",
        supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                                 OperationKind.REDUCTION}),
        memory_domain=MemoryDomainKind.HOST_RAM if target == "c11" else MemoryDomainKind.UNKNOWN,
    )


def compile_chain(target: str):
    cap = capability(target)
    payload = chain.parse_source()
    chain.emit(payload)
    graph = source_intent_to_triton_metadata(source_intent_from_mapping(payload)).to_compute_graph()
    return compile_graph(graph, [cap])


def snapshot(compiled, target: str) -> dict:
    """Serialize internally produced core objects, never parse an IR text dump."""
    cap = capability(target)
    return {
        "schema_version": "tuc.bounded_native_core_snapshot.v0", "target": target,
        "backend": cap.name, "memory_domain": cap.memory_domain.value,
        "source_intent_digest": chain.INTENT_DIGEST,
        "numeric_contract_digest": _digest_payload(chain.CONTRACT),
        "hac_ir": compiled.dump(IRStage.HAC_IR), "hs_ir": compiled.dump(IRStage.HS_IR),
        "runtime_plan": compiled.dump_runtime_plan(),
        "decision_report": compiled.dump_decision_report(),
        "operations": [{"name": op.name, "kind": op.kind.value,
                        "inputs": [t.name for t in op.inputs],
                        "outputs": [t.name for t in op.outputs]}
                       for op in compiled.hac_ir.graph.operations],
        "assignments": [{"operation": a.operation_name, "backend": a.backend_name,
                         "domain": a.memory_domain.value, "layout": a.produced_layout.value}
                        for a in compiled.partition_plan.assignments],
        "io_policy": "operator_owned_input_upload_and_terminal_download",
        "slot_policy": "projection_2_activation_3" if target == "c11" else
                       "projection_3_activation_2",
        "external_io_in_core_transfer_plan": False, "normal_runtime_admission": False,
    }


def lower_snapshot(value: object, target: str) -> str:
    _bounded_metadata(value)
    expected = snapshot(compile_chain(target), target)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("core snapshot rejected")
    compiled = compile_chain(target)
    plan = compiled.partition_plan
    if (plan.transfer_edges or plan.layout_conversions or plan.override_effects
            or any(a.backend_name != expected["backend"] for a in plan.assignments)):
        raise BoundedCompilerEmissionError("native placement outside reviewed slice")
    slots = {"a": 0, "b": 1, "projection": 2, "activated": 3, "row_sum": 4}
    if target == "cuda":
        slots.update(projection=3, activated=2)
    opcodes = {"matmul": 1, "elementwise": 2, "reduction": 3}
    lines = ["#ifndef TUC_NATIVE_DISPATCH_H", "#define TUC_NATIVE_DISPATCH_H",
             f"#define TUC_PLAN_TARGET {TARGETS.index(target) + 1}U",
             f"#define TUC_STEP_COUNT {len(expected['assignments'])}U",
             "static const struct tuc_step TUC_STEPS[] = {"]
    by_name = {op["name"]: op for op in expected["operations"]}
    for assignment in expected["assignments"]:
        op = by_name[assignment["operation"]]
        a = slots[op["inputs"][0]]
        b = slots[op["inputs"][1]] if len(op["inputs"]) == 2 else 5
        out = slots[op["outputs"][0]]
        lines.append(f"  {{{opcodes[op['kind']]}U, {a}U, {b}U, {out}U}},")
    return "\n".join([*lines, "};", "#endif", ""])


def _replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise BoundedCompilerEmissionError("bridge template drift")
    return text.replace(old, new)


def artifact_files() -> dict[str, str]:
    chain.verify_artifacts()
    previous = chain.artifact_files()
    files = {name: previous[name] for name in
             ("generated.c", "generated.h", "kernels.cuh", "inputs.h", "oracle.h")}
    for target in TARGETS:
        core = snapshot(compile_chain(target), target)
        files[f"{target}_plan.json"] = json.dumps(core, indent=2, sort_keys=True) + "\n"
        files[f"{target}_dispatch.h"] = lower_snapshot(core, target)
    for name in ("common.h", "build-c11.sh", "build-cuda.sh",
                 "Dockerfile", "Dockerfile.dockerignore"):
        files[name] = _read_bounded_file(chain.CONTEXT / name).decode()
    for target in TARGETS:
        key = f"build-{target}.sh"
        commands = []
        for index, mutation in enumerate(PLAN_MUTATIONS, 1):
            source = "generated.c " if target == "c11" else ""
            commands.append(f"compile {source}/out/{mutation} -DTUC_PLAN_FAULT={index}")
        files[key] = _replace_once(files[key], "compile " + (
            "generated.c " if target == "c11" else "") + "/out/proof\n",
            "compile " + ("generated.c " if target == "c11" else "") + "/out/proof\n"
            + "\n".join(commands) + "\n")
    dockerfile = files["Dockerfile"].replace("docker/composed-chain/", "docker/plan-native-bridge/")
    for target in TARGETS:
        prefix = "docker/plan-native-bridge/"
        dockerfile = _replace_once(dockerfile, f"RUN --network=none sh build-{target}.sh", (
            f"COPY {prefix}dispatch_contract.h {prefix}{target}_dispatch.h ./\n"
            f"RUN --network=none sh build-{target}.sh"))
    files["Dockerfile"] = dockerfile.replace("/out/nonfinite /opt/tuc/", (
        "/out/nonfinite " + " ".join(f"/out/{m}" for m in PLAN_MUTATIONS) + " /opt/tuc/"))
    files["Dockerfile.dockerignore"] = files["Dockerfile.dockerignore"].replace(
        "composed-chain", "plan-native-bridge") + "".join(
            f"!docker/plan-native-bridge/{n}\n" for n in
            ("dispatch_contract.h", "c11_dispatch.h", "cuda_dispatch.h"))
    operator = _read_bounded_file(ROOT / "scripts/run_bounded_composed_chain.sh").decode()
    operator = operator.replace("bounded_composed_chain", "bounded_plan_native_bridge")
    operator = operator.replace("composed-chain", "plan-native-bridge")
    operator = operator.replace("tuc-chain-", "tuc-plan-")
    operator = _replace_once(operator, 'cd "$(dirname "$0")/.."',
                             'cd "$(dirname "$0")/../.."')
    operator = _replace_once(operator, "over-budget nonfinite; do", (
        "over-budget nonfinite " + " ".join(PLAN_MUTATIONS) + "; do"))
    files["operator.sh"] = operator.replace("Composed chain", "Plan-driven chain").replace(
        "seven negative probes", "twelve negative probes")
    return files


def verify_artifacts() -> dict:
    files = artifact_files()
    for name, text in files.items():
        if _read_bounded_file(CONTEXT / name) != text.encode():
            raise BoundedCompilerEmissionError("bridge artifact drift")
    return {"schema_version": "tuc.bounded_plan_native_bridge.v0",
            "status": "PASS", "targets": list(TARGETS),
            "source_intent_digest": chain.INTENT_DIGEST,
            "dispatch": "checked_core_assignments_to_static_native_opcode_table",
            "normal_runtime_admission": False}


def program_digest() -> str:
    paths = [CONTEXT / n for n in (*artifact_files(), "host.c", "device.cu", "dispatch_contract.h")]
    paths += [ROOT / "examples/bounded_plan_native_bridge.py"]
    return _digest_payload({p.relative_to(ROOT).as_posix():
                            "sha256:" + sha256(_read_bounded_file(p)).hexdigest() for p in paths})


def validate_negative(value: object, target: str, mutation: str) -> None:
    if type(mutation) is not str or mutation not in MUTATIONS:
        raise BoundedCompilerEmissionError("bridge mutation rejected")
    _bounded_metadata(value)
    if mutation in chain.MUTATIONS:
        chain.validate_negative(value, target, mutation)
        return
    expected = chain.expected_observation(target)
    expected.update(status="ERROR", reason_code="target_not_ready", cases_passed=0,
                    generated_function_calls=0, tensor_bytes=0, scalar_checks=0,
                    outputs_differing_from_reference64=0, numeric_contract_passed=False,
                    execution_policy_passed=False, repeated_baseline_passed=False)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("native schedule rejection mismatch")


def build_record(value: object, target: str, image_id: str) -> dict:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("bridge image rejected")
    _bounded_metadata(value)
    observation = chain.validate_observation(value, target)
    verify_artifacts()
    core = snapshot(compile_chain(target), target)
    return {"schema_version": "tuc.bounded_plan_native_record.v0", "observation": observation,
            "operator_image_id": image_id, "program_files_digest": program_digest(),
            "core_snapshot_digest": _digest_payload(core),
            "hac_ir_digest": _digest_text(core["hac_ir"]),
            "dispatch_header_digest": _digest_text(lower_snapshot(core, target)),
            "previous_chain_program_digest": chain.program_digest(),
            "provenance": "same_maintainer_operator", "normal_runtime_admission": False,
            "io_policy": core["io_policy"]}


def compare_records(cpu: object, gpu: object) -> dict:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        _bounded_metadata(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("bridge record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("bridge record binding rejected")
    if cpu["hac_ir_digest"] != gpu["hac_ir_digest"]:
        raise BoundedCompilerEmissionError("target-dependent HAC-IR rejected")
    return {"schema_version": "tuc.bounded_plan_native_comparison.v0", "status": "PASS",
            "hac_ir_digest": cpu["hac_ir_digest"], "source_intent_digest": chain.INTENT_DIGEST,
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "dispatch": "core_plan_driven", "scalar_checks_per_target": 363,
            "normal_runtime_admission": False, "external_io_in_core_transfer_plan": False,
            "blocked_claims": [*chain.verify_artifacts()["blocked_claims"],
                               "general_native_plan_execution", "planned_external_io_costs"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--negative", choices=MUTATIONS)
    parser.add_argument("--image-id")
    parser.add_argument("--compare", type=Path, nargs=2)
    args = parser.parse_args()
    try:
        if args.compare:
            if any((args.validate, args.target, args.preflight, args.negative, args.image_id)):
                raise BoundedCompilerEmissionError("conflicting modes")
            report = compare_records(*(load_observation(p) for p in args.compare))
        elif args.validate and args.target:
            value = load_observation(args.validate)
            if args.negative:
                if args.preflight or args.image_id:
                    raise BoundedCompilerEmissionError("conflicting modes")
                validate_negative(value, args.target, args.negative)
                report = {"negative_probe": args.negative, "rejected": True}
            elif args.image_id:
                if args.preflight:
                    raise BoundedCompilerEmissionError("preflight is not execution")
                report = build_record(value, args.target, args.image_id)
            else:
                report = chain.validate_observation(value, args.target, args.preflight)
        elif any((args.validate, args.target, args.preflight, args.negative, args.image_id)):
            raise BoundedCompilerEmissionError("observation and target required")
        else:
            report = verify_artifacts()
        print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, ValueError):
        print("bounded native plan verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
