"""Fixed-corpus FP32 error contract; pure verification, no native execution."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from examples import bounded_reduction_shapes as shapes
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation

CONTEXT = ROOT / "docker/reduction-fp32"
TARGETS = shapes.TARGETS
MUTATIONS = (*shapes.MUTATIONS, "over-budget", "nonfinite")
UNIT_ROUNDOFF = Fraction(1, 2**24)
ROUNDING_DEPTH = 1 + 7 + 5
GAMMA = ROUNDING_DEPTH * UNIT_ROUNDOFF / (1 - ROUNDING_DEPTH * UNIT_ROUNDOFF)
CONTRACT = {
    "schema_version": "tuc.bounded_fp32_numeric_contract.v0",
    "reference": "exact_real_sum_of_products_of_binary32_inputs",
    "rounding": "nearest_ties_even", "fma_contraction": False,
    "reassociation": False, "underflow_overflow": "excluded_from_fixed_corpus",
    "unit_roundoff": "2^-24", "rounding_depth_bound": ROUNDING_DEPTH,
    "absolute_error_bound": "gamma_13 * sum_k_c(abs(a[row,k]*b[k,c]))",
    "interval_encoding": "binary64_endpoints_rounded_inward",
    "signed_zero": "numerical_equality_only", "admission": "fixed_ten_case_corpus_only",
}


def round_f32(value: Fraction) -> float:
    """Integer ties-to-even rounding for this bounded normal-or-zero domain."""
    if not value:
        return 0.0
    magnitude = abs(value)
    if not Fraction(1, 2**100) <= magnitude <= 2**100:
        raise BoundedCompilerEmissionError("FP32 arithmetic domain rejected")
    exponent = magnitude.numerator.bit_length() - magnitude.denominator.bit_length()
    if magnitude < Fraction(2) ** exponent:
        exponent -= 1
    quantum = Fraction(2) ** (exponent - 23)
    return float(round(value / quantum) * quantum)


def reference(a: object, b: object) -> list[tuple[Fraction, Fraction]]:
    _assert_plain_json({"a": a, "b": b})
    for matrix, rows, columns in ((a, 33, 7), (b, 7, 5)):
        if type(matrix) is not list or len(matrix) != rows:
            raise BoundedCompilerEmissionError("FP32 shape rejected")
        for row in matrix:
            if type(row) is not list or len(row) != columns:
                raise BoundedCompilerEmissionError("FP32 row rejected")
            for x in row:
                if (type(x) is not float or not math.isfinite(x) or abs(x) > 2**16
                        or (x != 0 and abs(x) < 2**-24) or round_f32(Fraction(x)) != x):
                    raise BoundedCompilerEmissionError("FP32 input rejected")
    # Contract B first in exact rationals, not in the generated operation order.
    sums = [sum(map(Fraction, row), Fraction()) for row in b]
    magnitudes = [sum((abs(Fraction(x)) for x in row), Fraction()) for row in b]
    return [(sum((Fraction(x) * s for x, s in zip(row, sums, strict=True)), Fraction()),
             GAMMA * sum((abs(Fraction(x)) * s
                          for x, s in zip(row, magnitudes, strict=True)), Fraction()))
            for row in a]


def interval(exact: Fraction, budget: Fraction) -> tuple[float, float]:
    if budget < 0:
        raise BoundedCompilerEmissionError("negative error budget")
    lower, upper = exact - budget, exact + budget
    lo, hi = float(lower), float(upper)
    if Fraction(lo) < lower:
        lo = math.nextafter(lo, math.inf)
    if Fraction(hi) > upper:
        hi = math.nextafter(hi, -math.inf)
    return lo, hi


def corpus() -> list[dict]:
    a = [[Fraction((r * 3 + k * 7) % 19 + 1, 10) for k in range(7)] for r in range(33)]
    b = [[Fraction((k * 5 + c * 3) % 17 + 1, 10) for c in range(5)] for k in range(7)]
    cases = []

    def add(name, left, right):
        cases.append({"name": name,
                      "a": [[round_f32(x) for x in row] for row in left],
                      "b": [[round_f32(x) for x in row] for row in right]})

    add("decimal", a, b)
    add("negative", [[-x for x in row] for row in a], b)
    add("mixed_sign", [[x * (-1)**(r + k) for k, x in enumerate(row)]
                       for r, row in enumerate(a)], b)
    add("cancellation", a, [[row[0], -row[0], row[1], -row[1], Fraction(k + 1, 81920)]
                            for k, row in enumerate(b)])
    add("small", [[x / 1024 for x in row] for row in a],
        [[x / 1024 for x in row] for row in b])
    add("large", [[x * 1024 for x in row] for row in a],
        [[x * 1024 for x in row] for row in b])
    add("reciprocal_scale", [[x * 1024 for x in row] for row in a],
        [[x / 1024 for x in row] for row in b])
    add("mixed_magnitudes", [[x * Fraction(2)**(k * 4 - 12) for k, x in enumerate(row)]
                             for row in a], b)
    add("zero", [[Fraction()] * 7 for _ in range(33)], b)
    add("last_row", [[Fraction()] * 7 for _ in range(32)] + [a[-1]], b)
    return cases


def ordered_reference(case: dict) -> list[float]:
    """Test oracle also verifies every actual intermediate stays normal or zero."""
    reference(case["a"], case["b"])
    result = []
    for row in case["a"]:
        projection = []
        for c in range(5):
            value = 0.0
            for k in range(7):
                product = round_f32(Fraction(row[k]) * Fraction(case["b"][k][c]))
                value = round_f32(Fraction(value) + Fraction(product))
            projection.append(value)
        value = 0.0
        for x in projection:
            value = round_f32(Fraction(value) + Fraction(x))
        result.append(value)
    return result


def _hex(value: float) -> str:
    mantissa, exponent = value.hex().split("p")
    return mantissa.rstrip("0").rstrip(".") + "p" + exponent


def artifact_files() -> dict[str, str]:
    code = shapes.emit(shapes.parse_source("odd"), "odd")
    cases = corpus()
    refs = [reference(c["a"], c["b"]) for c in cases]
    for case, bounds in zip(cases, refs, strict=True):
        for value, (exact, budget) in zip(ordered_reference(case), bounds, strict=True):
            if abs(Fraction(value) - exact) > budget:
                raise BoundedCompilerEmissionError("reviewed corpus exceeds contract")
    plan = {"schema_version": "tuc.bounded_reduction_fp32_plan.v0",
            "source_intent_digest": shapes.INTENT_DIGESTS["odd"],
            "c11_code_digest": _digest_text(code["generated.c"]),
            "cuda_code_digest": _digest_text(code["kernels.cuh"]),
            "corpus_digest": _digest_payload(cases), "contract_digest": _digest_payload(CONTRACT),
            "case_count": len(cases), "runs": len(cases) + 1,
            "input_shapes": [[33, 7], [7, 5]], "output_shape": [33], "tensor_bytes": 1856,
            "runtime_admission": False,
            "blocked_claims": [*shapes.BLOCKED_CLAIMS, "arbitrary_fp32_inputs", "dynamic_shapes",
                               "bitwise_backend_equivalence", "relative_error_guarantee"]}
    lines = ["#ifndef TUC_FP32_INPUTS_H", "#define TUC_FP32_INPUTS_H"]
    for name, value in (("ROWS", 33), ("INNER", 7), ("COLUMNS", 5), ("CASES", len(cases)),
                        ("RUNS", len(cases) + 1), ("PROJECTION_BLOCKS", 6),
                        ("OUTPUT_BLOCKS", 2), ("TENSOR_BYTES", 1856)):
        lines.append(f"#define TUC_{name} {value}U")
    for name, key in (("INTENT", "source_intent_digest"), ("C11_CODE", "c11_code_digest"),
                      ("CUDA_CODE", "cuda_code_digest"), ("CORPUS", "corpus_digest"),
                      ("CONTRACT", "contract_digest")):
        lines.append(f'#define TUC_{name}_DIGEST "{plan[key]}"')
    for key, width in (("a", 231), ("b", 35)):
        lines.append(f"static const float TUC_{key.upper()}[{len(cases)}][{width}] = {{")
        for case in cases:
            lines.append("  {" + ", ".join(_hex(x) + "F" for row in case[key] for x in row) + "},")
        lines.append("};")
    oracle = ["#ifndef TUC_FP32_ORACLE_H", "#define TUC_FP32_ORACLE_H"]
    for name in ("LOWER", "UPPER", "REFERENCE64"):
        oracle.append(f"static const double TUC_{name}[{len(cases)}][33] = {{")
        for bounds in refs:
            values = [float(x) if name == "REFERENCE64" else interval(x, e)[name == "UPPER"]
                      for x, e in bounds]
            oracle.append("  {" + ", ".join(map(_hex, values)) + "},")
        oracle.append("};")
    return {"inputs.h": "\n".join([*lines, "#endif", ""]),
            "oracle.h": "\n".join([*oracle, "#endif", ""]),
            "numeric_contract.json": json.dumps(CONTRACT, indent=2, sort_keys=True) + "\n",
            "emission_plan.json": json.dumps(plan, indent=2, sort_keys=True) + "\n"}


def verify_artifacts() -> dict:
    shapes.verify_artifacts()
    files = artifact_files()
    for name, value in files.items():
        if _read_bounded_file(CONTEXT / name) != value.encode():
            raise BoundedCompilerEmissionError("FP32 artifact drift")
    return json.loads(files["emission_plan.json"])


def expected_observation(target: str, preflight: bool = False, rounded: int = 0) -> dict:
    if type(target) is not str or target not in TARGETS or type(preflight) is not bool:
        raise BoundedCompilerEmissionError("FP32 mode rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_reduction_fp32_observation.v0", "target": target,
            "mode": "preflight" if preflight else "execute",
            "status": "PASS", "reason_code": "none",
            "source_intent_digest": plan["source_intent_digest"],
            "code_digest": plan[f"{target}_code_digest"], "corpus_digest": plan["corpus_digest"],
            "contract_digest": plan["contract_digest"], "case_count": 10, "output_shape": [33],
            "cases_passed": 0 if preflight else 11,
            "generated_function_calls": 0 if preflight else 22,
            "failed_run_index": -1, "tensor_bytes": 0 if preflight else 1856,
            "outputs_differing_from_reference64": rounded,
            "security_boundary_passed": True, "numeric_contract_passed": not preflight,
            "repeated_baseline_passed": not preflight, "raw_values_serialized": False}


def validate_observation(value: object, target: str, preflight: bool = False) -> dict:
    _assert_plain_json(value)
    if type(value) is not dict:
        raise BoundedCompilerEmissionError("FP32 observation rejected")
    rounded = value.get("outputs_differing_from_reference64")
    if type(rounded) is not int or not (rounded == 0 if preflight else 1 <= rounded <= 363):
        raise BoundedCompilerEmissionError("FP32 rounding witness rejected")
    expected = expected_observation(target, preflight, rounded)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("FP32 observation rejected")
    return expected


def validate_negative(value: object, target: str, mutation: str) -> None:
    if type(mutation) is not str or mutation not in MUTATIONS:
        raise BoundedCompilerEmissionError("FP32 mutation rejected")
    _assert_plain_json(value)
    expected = expected_observation(target)
    expected.update(status="ERROR", reason_code="numeric_contract_mismatch", cases_passed=0,
                    failed_run_index=0, generated_function_calls=2,
                    numeric_contract_passed=False, repeated_baseline_passed=False)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("FP32 negative observation rejected")


def program_digest() -> str:
    files = {f"docker/reduction-fp32/{name}": CONTEXT / name for name in
             (*artifact_files(), "common.h", "build-c11.sh", "build-cuda.sh",
              "Dockerfile", "Dockerfile.dockerignore")}
    for name in ("generated.c", "generated.h", "kernels.cuh", "host.c", "device.cu"):
        files[f"docker/reduction-shapes/{name}"] = shapes.CONTEXT / name
    for name in ("examples/reduction_fp32_contract.py", "examples/bounded_reduction_shapes.py",
                 "scripts/run_reduction_fp32_contract.sh"):
        files[name] = ROOT / name
    return _digest_payload({name: "sha256:" + sha256(_read_bounded_file(path)).hexdigest()
                            for name, path in files.items()})


def build_record(value: object, target: str, image_id: str) -> dict:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("FP32 image rejected")
    return {"schema_version": "tuc.bounded_reduction_fp32_record.v0",
            "observation": validate_observation(value, target), "operator_image_id": image_id,
            "program_files_digest": program_digest(), "provenance": "same_maintainer_operator"}


def compare_records(cpu: object, gpu: object) -> dict:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        _assert_plain_json(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("FP32 record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("FP32 record binding rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_reduction_fp32_comparison.v0", "status": "PASS",
            "source_intent_digest": plan["source_intent_digest"],
            "contract_digest": plan["contract_digest"], "corpus_digest": plan["corpus_digest"],
            "output_shape": [33], "targets": list(TARGETS), "case_count": 10, "runs_per_target": 11,
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "comparison": "both_targets_satisfy_same_exact_reference_error_contract",
            "pairwise_absolute_error_bound": "twice_per_row_contract_budget",
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
                report = {"negative_probe": args.negative, "rejected_by_contract": True}
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
        print("bounded FP32 contract verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
