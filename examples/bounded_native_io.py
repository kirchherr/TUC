"""Execute explicit boundary I/O around the closed RFC 0312 core plan."""

from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from math import prod
from pathlib import Path

from examples import bounded_plan_native_bridge as bridge
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _canonical_json,
    _digest_payload,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation
from tuc.ir.memory import dtype_size_bytes

CONTEXT = ROOT / "docker/native-io"
TARGETS = bridge.TARGETS
IO_MUTATIONS = ("io-count", "io-direction", "io-size", "io-slot", "io-early-output",
                "io-duplicate-input", "io-short-output")
MUTATIONS = (*bridge.MUTATIONS, *IO_MUTATIONS, "io-skip-output")


def io_plan(target: str) -> dict:
    compiled = bridge.compile_chain(target)
    core = bridge.snapshot(compiled, target)
    bridge.lower_snapshot(core, target)
    graph = compiled.hac_ir.graph
    produced = {t.name: t for op in graph.operations for t in op.outputs}
    consumed = {t.name for op in graph.operations for t in op.inputs}
    inputs = {t.name: t for op in graph.operations for t in op.inputs if t.name not in produced}
    outputs = {name: t for name, t in produced.items() if name not in consumed}
    if set(inputs) != {"a", "b"} or set(outputs) != {"row_sum"}:
        raise BoundedCompilerEmissionError("unreviewed native I/O boundary")
    slots = {"a": 0, "b": 1, "row_sum": 4}
    rows = []
    for phase, tensors in (("before_compute", inputs), ("after_compute", outputs)):
        for name, tensor in sorted(tensors.items()):
            inbound = phase == "before_compute"
            mode = "host_binding" if target == "c11" else "upload" if inbound else "download"
            rows.append({"phase": phase, "mode": mode, "tensor": name, "slot": slots[name],
                         "shape": list(tensor.shape), "dtype": tensor.dtype,
                         "bytes": prod(tensor.shape) * dtype_size_bytes(tensor.dtype),
                         "source_space": "host" if inbound else "execution",
                         "target_space": "execution" if inbound else "host",
                         "layout": "row_major"})
    sizes = [0] * 5
    all_tensors = {**inputs, **produced}
    for name, slot in {**slots, "projection": 2 if target == "c11" else 3,
                       "activated": 3 if target == "c11" else 2}.items():
        tensor = all_tensors[name]
        sizes[slot] = prod(tensor.shape) * dtype_size_bytes(tensor.dtype)
    return {"schema_version": "tuc.bounded_native_io_plan.v0", "target": target,
            "core_snapshot_digest": _digest_payload(core),
            "compute_dispatch_digest": bridge._digest_text(bridge.lower_snapshot(core, target)),
            "memory_spaces": {
                "host": {"address_space": "host_process", "physical_kind": "host_ram"},
                "execution": {"address_space": "host_process" if target == "c11" else
                              "device_global", "physical_kind": core["memory_domain"]}},
            "steps": rows, "buffer_bytes": sizes,
            "cross_space_bytes_per_run": sum(r["bytes"] for r in rows) if target == "cuda" else 0,
            "latency_ns": None, "energy_pj": None, "cost_status": "not_measured",
            "scope": "closed_operator_boundary_not_core_partition_transfers",
            "normal_runtime_admission": False}


def lower_io(value: object, target: str) -> str:
    bridge._bounded_metadata(value)
    expected = io_plan(target)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("native I/O plan rejected")
    lines = ["#ifndef TUC_IO_PLAN_H", "#define TUC_IO_PLAN_H",
             f'#define TUC_IO_DIGEST "{_digest_payload(expected)}"',
             "#define TUC_IO_COUNT 3U",
             "static const unsigned int TUC_BUFFER_BYTES[5] = {" +
             ", ".join(f"{n}U" for n in expected["buffer_bytes"]) + "};",
             "static const struct tuc_io_step TUC_IO_STEPS[] = {"]
    for row in expected["steps"]:
        phase = 1 if row["phase"] == "before_compute" else 2
        mode = {"host_binding": 0, "upload": 1, "download": 2}[row["mode"]]
        src = 0 if row["source_space"] == "host" or target == "c11" else 1
        dst = 0 if row["target_space"] == "host" or target == "c11" else 1
        lines.append(f"  {{{phase}U, {mode}U, {row['slot']}U, {row['bytes']}U, {src}U, {dst}U}},")
    return "\n".join([*lines, "};", "#endif", ""])


def artifact_files() -> dict[str, str]:
    bridge.verify_artifacts()
    files = bridge.artifact_files()
    files["dispatch_contract.h"] = _read_bounded_file(
        bridge.CONTEXT / "dispatch_contract.h").decode()
    for target in TARGETS:
        plan = io_plan(target)
        files[f"{target}_io.json"] = json.dumps(plan, sort_keys=True, indent=2) + "\n"
        files[f"{target}_io.h"] = lower_io(plan, target)
        key = f"build-{target}.sh"
        prefix = "compile generated.c " if target == "c11" else "compile "
        commands = [f"{prefix}/out/{name} -DTUC_IO_FAULT={i}" for i, name in
                    enumerate(IO_MUTATIONS, 1)]
        commands.append(f"{prefix}/out/io-skip-output -DTUC_IO_SKIP_OUTPUT=1")
        files[key] = bridge._replace_once(files[key], prefix + "/out/proof\n",
                                          prefix + "/out/proof\n" + "\n".join(commands) + "\n")
    files["common.h"] = bridge._replace_once(files["common.h"], '  printf("{',
                                              '  io_emit_metadata();\n  printf("{')
    files["common.h"] = bridge._replace_once(files["common.h"],
                                              r'false}\n",', r'false}}\n",')
    files["Dockerfile"] = files["Dockerfile"].replace("plan-native-bridge", "native-io")
    for target in TARGETS:
        files["Dockerfile"] = bridge._replace_once(files["Dockerfile"],
            f"RUN --network=none sh build-{target}.sh",
            f"COPY docker/native-io/io_contract.h docker/native-io/{target}_io.h ./\n"
            f"RUN --network=none sh build-{target}.sh")
    extra = (*IO_MUTATIONS, "io-skip-output")
    files["Dockerfile"] = files["Dockerfile"].replace("/out/wrong-target /opt/tuc/",
        "/out/wrong-target " + " ".join(f"/out/{m}" for m in extra) + " /opt/tuc/")
    files["Dockerfile.dockerignore"] = files["Dockerfile.dockerignore"].replace(
        "plan-native-bridge", "native-io") + "".join(
            f"!docker/native-io/{n}\n" for n in ("io_contract.h", "c11_io.h", "cuda_io.h"))
    operator = files["operator.sh"].replace("bounded_plan_native_bridge", "bounded_native_io")
    operator = operator.replace("plan-native-bridge", "native-io").replace("tuc-plan-", "tuc-io-")
    operator = bridge._replace_once(operator, "missing-step wrong-target; do",
        "missing-step wrong-target " + " ".join(extra) + "; do")
    files["operator.sh"] = operator.replace("Plan-driven chain", "Plan-driven native I/O").replace(
        "twelve negative probes", "twenty negative probes")
    return files


def verify_artifacts() -> dict:
    for name, content in artifact_files().items():
        if _read_bounded_file(CONTEXT / name) != content.encode():
            raise BoundedCompilerEmissionError("native I/O artifact drift")
    return {"schema_version": "tuc.bounded_native_io_verification.v0", "status": "PASS",
            "normal_runtime_admission": False, "latency_ns": None,
            "cross_space_bytes_per_cuda_run": io_plan("cuda")["cross_space_bytes_per_run"]}


def program_digest() -> str:
    paths = [CONTEXT / n for n in (*artifact_files(), "host.c", "device.cu", "io_contract.h")]
    paths.append(ROOT / "examples/bounded_native_io.py")
    return _digest_payload({p.relative_to(ROOT).as_posix():
                            "sha256:" + sha256(_read_bounded_file(p)).hexdigest() for p in paths})


def io_counters(target: str, runs: int, skip_output: bool = False) -> dict:
    bridge.capability(target)
    count = 2 if skip_output else 3
    return {"completed_steps": count * runs,
            "host_bindings": count * runs if target == "c11" else 0,
            "upload_calls": 2 * runs if target == "cuda" else 0,
            "upload_bytes": 1064 * runs if target == "cuda" else 0,
            "download_calls": runs if target == "cuda" and not skip_output else 0,
            "download_bytes": 132 * runs if target == "cuda" and not skip_output else 0}


def validate_observation(value: object, target: str, preflight: bool = False,
                         mutation: str | None = None) -> dict:
    bridge._bounded_metadata(value)
    if type(value) is not dict or set(value) != {"schema_version", "io_plan_digest", "io",
                                               "numeric_observation"}:
        raise BoundedCompilerEmissionError("native I/O observation rejected")
    if type(preflight) is not bool or (mutation is not None and (
            type(mutation) is not str or mutation not in MUTATIONS)):
        raise BoundedCompilerEmissionError("native I/O mutation rejected")
    if preflight and mutation:
        raise BoundedCompilerEmissionError("conflicting observation modes")
    numeric = value["numeric_observation"]
    runs = 0 if preflight else 11
    if mutation in (*bridge.PLAN_MUTATIONS, *IO_MUTATIONS):
        bridge.validate_negative(numeric, target, bridge.PLAN_MUTATIONS[0])
        runs = 0
    elif mutation == "io-skip-output":
        expected = bridge.chain.expected_observation(target)
        expected.update(status="ERROR", reason_code="execution_failed", cases_passed=0,
                        failed_run_index=0, generated_function_calls=3, scalar_checks=0,
                        outputs_differing_from_reference64=0, numeric_contract_passed=False,
                        execution_policy_passed=False, repeated_baseline_passed=False)
        if _canonical_json(numeric) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("missing output completion not rejected")
        runs = 1
    elif mutation:
        bridge.validate_negative(numeric, target, mutation)
        runs = 1
    else:
        bridge.chain.validate_observation(numeric, target, preflight)
    expected = {"schema_version": "tuc.bounded_native_io_observation.v0",
                "io_plan_digest": _digest_payload(io_plan(target)),
                "io": io_counters(target, runs, mutation == "io-skip-output"),
                "numeric_observation": numeric}
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("native I/O completion mismatch")
    return expected


def build_record(value: object, target: str, image_id: str) -> dict:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("native I/O image rejected")
    observation = validate_observation(value, target)
    verify_artifacts()
    return {"schema_version": "tuc.bounded_native_io_record.v0", "observation": observation,
            "operator_image_id": image_id, "program_files_digest": program_digest(),
            "previous_bridge_program_digest": bridge.program_digest(),
            "provenance": "same_maintainer_operator", "normal_runtime_admission": False}


def compare_records(cpu: object, gpu: object) -> dict:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        bridge._bounded_metadata(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("native I/O record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("native I/O binding rejected")
    return {"schema_version": "tuc.bounded_native_io_comparison.v0", "status": "PASS",
            "source_intent_digest": bridge.chain.INTENT_DIGEST,
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "scalar_checks_per_target": 363, "cuda_copy_calls": 33,
            "cuda_copy_bytes": 13156, "cpu_host_bindings": 33,
            "external_io_in_bounded_operator_plan": True,
            "external_io_in_core_partition_plan": False,
            "latency_ns": None, "energy_pj": None, "normal_runtime_admission": False,
            "blocked_claims": ["general_native_runtime", "arbitrary_programs_or_inputs",
                               "performance", "mixed_native_placement", "independent_reproduction"]}


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
                validate_observation(value, args.target, mutation=args.negative)
                report = {"negative_probe": args.negative, "rejected": True}
            elif args.image_id:
                if args.preflight:
                    raise BoundedCompilerEmissionError("preflight is not execution")
                report = build_record(value, args.target, args.image_id)
            else:
                report = validate_observation(value, args.target, args.preflight)
        elif any((args.validate, args.target, args.preflight, args.negative, args.image_id)):
            raise BoundedCompilerEmissionError("observation and target required")
        else:
            report = verify_artifacts()
        print(json.dumps(report, sort_keys=True, indent=2))
    except (OSError, ValueError):
        print("bounded native I/O verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
