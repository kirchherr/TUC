"""Paired separate/FMA reduction experiment with unchanged RFC 0309 error bounds."""

from __future__ import annotations

import argparse
import json
import re
import sys
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from examples import reduction_fp32_contract as fp
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation

CONTEXT = ROOT / "docker/reduction-fma"
TARGETS = fp.TARGETS
MUTATIONS = (*fp.MUTATIONS, "separate-as-fma")
POLICY = {
    "schema_version": "tuc.bounded_fma_execution_policy.v0",
    "baseline": "separate_binary32_multiply_then_add",
    "candidate": "explicit_binary32_fused_multiply_add",
    "candidate_c11": "fmaf", "candidate_cuda": "__fmaf_rn",
    "automatic_contraction": False, "reassociation": False,
    "rounding": "nearest_ties_even", "output_reduction": "sequential_binary32_sum",
    "admission": "fixed_rfc0309_corpus_only",
    "baseline_policy_is_unchanged": True,
}


def fused_reference(case: dict) -> list[float]:
    fp.reference(case["a"], case["b"])
    result = []
    for row in case["a"]:
        projection = []
        for c in range(5):
            value = 0.0
            for k in range(7):
                value = fp.round_f32(Fraction(row[k]) * Fraction(case["b"][k][c])
                                     + Fraction(value))
            projection.append(value)
        value = 0.0
        for x in projection:
            value = fp.round_f32(Fraction(value) + Fraction(x))
        result.append(value)
    return result


def emit(payload: object, target: str) -> dict[str, str]:
    if type(target) is not str or target not in TARGETS:
        raise BoundedCompilerEmissionError("FMA target rejected")
    separate = fp.shapes.emit(payload, "odd")
    name = "generated.c" if target == "c11" else "kernels.cuh"
    intrinsic = "fmaf" if target == "c11" else "__fmaf_rn"
    statement = "value += a[row * 7U + inner] * b[inner * 5U + column];"
    if separate[name].count(statement) != 1:
        raise BoundedCompilerEmissionError("FMA lowering template drift")
    source = separate[name].replace(statement,
        f"value = {intrinsic}(a[row * 7U + inner], b[inner * 5U + column], value);")
    source = source.replace("tuc_projection", "tuc_projection_fma")
    source = source.replace("tuc_sum_axis1", "tuc_sum_axis1_fma")
    if target == "cuda":
        return {"fma.cuh": source.replace("TUC_REDUCTION_KERNELS_CUH", "TUC_FMA_KERNELS_CUH")}
    header = separate["generated.h"].replace("TUC_REDUCTION_GENERATED_H", "TUC_FMA_GENERATED_H")
    header = header.replace("tuc_projection", "tuc_projection_fma")
    header = header.replace("tuc_sum_axis1", "tuc_sum_axis1_fma")
    return {"fma.c": source.replace('#include "generated.h"',
                                   '#include "fma.h"\n#include <math.h>'), "fma.h": header}


def artifact_files() -> dict[str, str]:
    payload = fp.shapes.parse_source("odd")
    files = {**emit(payload, "c11"), **emit(payload, "cuda")}
    previous = fp.artifact_files()
    old_plan = json.loads(previous["emission_plan.json"])
    cases = fp.corpus()
    separate = [fp.ordered_reference(c) for c in cases]
    fused = [fused_reference(c) for c in cases]
    counts = {"baseline_rounding_outputs": 0, "fma_rounding_outputs": 0, "different_outputs": 0}
    for i in (*range(10), 0):
        bounds = fp.reference(cases[i]["a"], cases[i]["b"])
        for baseline, candidate, (exact, budget) in zip(separate[i], fused[i], bounds, strict=True):
            if abs(Fraction(candidate) - exact) > budget:
                raise BoundedCompilerEmissionError("FMA exceeds unchanged error budget")
            counts["baseline_rounding_outputs"] += baseline != float(exact)
            counts["fma_rounding_outputs"] += candidate != float(exact)
            counts["different_outputs"] += baseline != candidate
    if not counts["different_outputs"] or separate[0] == fused[0]:
        raise BoundedCompilerEmissionError("FMA difference witness missing")
    plan = {"schema_version": "tuc.bounded_fma_plan.v0",
            "source_intent_digest": old_plan["source_intent_digest"],
            "corpus_digest": old_plan["corpus_digest"],
            "baseline_contract_digest": old_plan["contract_digest"],
            "acceptance_intervals_digest": _digest_text(previous["oracle.h"]),
            "execution_policy_digest": _digest_payload(POLICY),
            "baseline_c11_code_digest": old_plan["c11_code_digest"],
            "baseline_cuda_code_digest": old_plan["cuda_code_digest"],
            "fma_c11_code_digest": _digest_text(files["fma.c"]),
            "fma_cuda_code_digest": _digest_text(files["fma.cuh"]),
            "input_shapes": [[33, 7], [7, 5]], "output_shape": [33],
            "case_count": 10, "runs": 11, "tensor_bytes": 1856,
            "expected_counts": counts, "runtime_admission": False,
            "blocked_claims": old_plan["blocked_claims"]}
    lines = ["#ifndef TUC_FMA_POLICY_H", "#define TUC_FMA_POLICY_H"]
    for name, key in (("FMA_C11_CODE", "fma_c11_code_digest"),
                      ("FMA_CUDA_CODE", "fma_cuda_code_digest"),
                      ("INTERVALS", "acceptance_intervals_digest"),
                      ("EXECUTION_POLICY", "execution_policy_digest")):
        lines.append(f'#define TUC_{name}_DIGEST "{plan[key]}"')
    for name, rows in (("SEPARATE", separate), ("FMA", fused)):
        lines.append(f"static const float TUC_{name}_EXPECTED[10][33] = {{")
        for row in rows:
            lines.append("  {" + ", ".join(fp._hex(x) + "F" for x in row) + "},")
        lines.append("};")
    files["policy.h"] = "\n".join([*lines, "#endif", ""])
    files["execution_policy.json"] = json.dumps(POLICY, indent=2, sort_keys=True) + "\n"
    files["emission_plan.json"] = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return files


def verify_artifacts() -> dict:
    fp.verify_artifacts()
    files = artifact_files()
    for name, value in files.items():
        if _read_bounded_file(CONTEXT / name) != value.encode():
            raise BoundedCompilerEmissionError("FMA artifact drift")
    return json.loads(files["emission_plan.json"])


def expected_observation(target: str, preflight: bool = False) -> dict:
    if type(target) is not str or target not in TARGETS or type(preflight) is not bool:
        raise BoundedCompilerEmissionError("FMA mode rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_fma_observation.v0", "target": target,
            "mode": "preflight" if preflight else "execute",
            "status": "PASS", "reason_code": "none",
            **{k: plan[k] for k in ("source_intent_digest", "corpus_digest",
                "baseline_contract_digest", "acceptance_intervals_digest",
                "execution_policy_digest")},
            "baseline_code_digest": plan[f"baseline_{target}_code_digest"],
            "fma_code_digest": plan[f"fma_{target}_code_digest"],
            "output_shape": [33], "case_count": 10, "runs_passed": 0 if preflight else 11,
            "generated_function_calls": 0 if preflight else 44, "failed_run_index": -1,
            "scalar_checks": 0 if preflight else 726, "tensor_bytes": 0 if preflight else 1856,
            **{k: 0 if preflight else v for k, v in plan["expected_counts"].items()},
            "security_boundary_passed": True, "numeric_contract_passed": not preflight,
            "execution_policy_passed": not preflight, "repeated_baseline_passed": not preflight,
            "raw_values_serialized": False}


def validate_observation(value: object, target: str, preflight: bool = False) -> dict:
    _assert_plain_json(value)
    expected = expected_observation(target, preflight)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("FMA observation rejected")
    return expected


def validate_negative(value: object, target: str, mutation: str) -> None:
    if type(mutation) is not str or mutation not in MUTATIONS:
        raise BoundedCompilerEmissionError("FMA mutation rejected")
    _assert_plain_json(value)
    expected = expected_observation(target)
    expected.update(status="ERROR", reason_code="execution_policy_mismatch" if
                    mutation == "separate-as-fma" else "numeric_contract_mismatch",
                    runs_passed=0, failed_run_index=0, generated_function_calls=4, scalar_checks=0,
                    baseline_rounding_outputs=0, fma_rounding_outputs=0, different_outputs=0,
                    numeric_contract_passed=False, execution_policy_passed=False,
                    repeated_baseline_passed=False)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("FMA negative observation rejected")


def program_digest() -> str:
    files = {f"docker/reduction-fma/{name}": CONTEXT / name for name in
             (*artifact_files(), "host.c", "device.cu", "common.h", "build-c11.sh", "build-cuda.sh",
              "Dockerfile", "Dockerfile.dockerignore")}
    for folder, names in (("reduction-shapes", ("generated.c", "generated.h", "kernels.cuh")),
                          ("reduction-fp32", ("inputs.h", "oracle.h", "numeric_contract.json"))):
        for name in names:
            files[f"docker/{folder}/{name}"] = ROOT / "docker" / folder / name
    for name in ("examples/reduction_fma_variant.py", "examples/reduction_fp32_contract.py",
                 "examples/bounded_reduction_shapes.py", "scripts/run_reduction_fma_variant.sh"):
        files[name] = ROOT / name
    return _digest_payload({name: "sha256:" + sha256(_read_bounded_file(path)).hexdigest()
                            for name, path in files.items()})


def build_record(value: object, target: str, image_id: str) -> dict:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("FMA image rejected")
    return {"schema_version": "tuc.bounded_fma_record.v0",
            "observation": validate_observation(value, target), "operator_image_id": image_id,
            "program_files_digest": program_digest(), "provenance": "same_maintainer_operator"}


def compare_records(cpu: object, gpu: object) -> dict:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        _assert_plain_json(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("FMA record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("FMA record binding rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_fma_comparison.v0", "status": "PASS",
            **{k: plan[k] for k in ("source_intent_digest", "corpus_digest",
                "baseline_contract_digest", "acceptance_intervals_digest",
                "execution_policy_digest")},
            "targets": list(TARGETS), "variants": ["separate", "explicit_fma"],
            "runs_per_target": 11, "scalar_checks_per_target": 726,
            "different_outputs_per_target": plan["expected_counts"]["different_outputs"],
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "comparison": "different_results_within_unchanged_reference_intervals",
            "raw_values_serialized": False, "blocked_claims": plan["blocked_claims"]}


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
                report = validate_observation(value, args.target, args.preflight)
        elif any((args.validate, args.target, args.preflight, args.negative, args.image_id)):
            raise BoundedCompilerEmissionError("observation and target required")
        else:
            report = verify_artifacts()
        print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, ValueError):
        print("bounded FMA verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
