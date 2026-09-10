"""A fixed input portfolio for the unchanged C11 and sm86 reduction programs."""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from examples.bounded_compiler_emission import (
    WORKLOAD_MANIFEST_PATH,
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _load_json,
    assert_compiler_emission_workload,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation
from examples.bounded_reduction_c11 import verify_artifacts as verify_c11
from examples.bounded_reduction_cuda import BLOCKED_CLAIMS
from examples.bounded_reduction_cuda import verify_artifacts as verify_cuda

CONTEXT = ROOT / "docker/reduction-portfolio"
TARGETS = ("c11", "cuda")
CASE_COUNT = 20
RUN_COUNT = CASE_COUNT + 1
SCHEMA = "tuc.reduction_input_portfolio_observation.v0"


def exact_reference(a: list[list[float]], b: list[list[float]]) -> list[float]:
    # Small quarter-integers keep every tested intermediate exactly FP32-representable.
    _assert_plain_json({"a": a, "b": b})
    if (type(a) is not list or len(a) != 4
            or any(type(row) is not list or len(row) != 8 for row in a)):
        raise BoundedCompilerEmissionError("portfolio A shape rejected")
    if (type(b) is not list or len(b) != 8
            or any(type(row) is not list or len(row) != 2 for row in b)):
        raise BoundedCompilerEmissionError("portfolio B shape rejected")
    for row in [*a, *b]:
        for value in row:
            if type(value) is not float or not -4 <= value <= 4 or value * 4 % 1:
                raise BoundedCompilerEmissionError("portfolio numeric domain rejected")
    sums = [sum((Fraction(x) for x in row), Fraction()) for row in b]
    return [float(sum((Fraction(x) * y for x, y in zip(row, sums, strict=True)), Fraction()))
            for row in a]


def corpus() -> list[dict[str, object]]:
    inputs = assert_compiler_emission_workload(_load_json(WORKLOAD_MANIFEST_PATH))["inputs"]
    a, b = inputs["a"], inputs["b"]
    cases: list[dict[str, object]] = []

    def add(name, left, right):
        cases.append({"name": name, "a": left, "b": right,
                      "expected": exact_reference(left, right)})

    add("baseline", a, b)
    add("zero_a", [[0.0] * 8 for _ in range(4)], b)
    add("negated_a", [[-x for x in row] for row in a], b)
    add("half_a", [[x / 2 for x in row] for row in a], b)
    add("swapped_b_columns", a, [list(reversed(row)) for row in b])
    add("reversed_a_rows", list(reversed(a)), b)
    add("cancelling_b_columns", a, [[row[0], -row[0]] for row in b])
    for inner in range(8):
        left = [[float(row + 1) if k == inner else 0.0 for k in range(8)] for row in range(4)]
        add(f"basis_{inner}", left, b)
    rng = random.Random(30607)
    for index in range(5):
        add(f"mixed_{index}", [[rng.randint(-8, 8) / 4 for _ in range(8)] for _ in range(4)],
            [[rng.randint(-8, 8) / 4 for _ in range(2)] for _ in range(8)])
    if len(cases) != CASE_COUNT:
        raise BoundedCompilerEmissionError("portfolio count drift")
    return cases


def artifact_files() -> dict[str, str]:
    cpu, gpu, cases = verify_c11(), verify_cuda(), corpus()
    lines = ["#ifndef TUC_PORTFOLIO_VECTORS_H", "#define TUC_PORTFOLIO_VECTORS_H",
             f"#define TUC_CASE_COUNT {CASE_COUNT}U", f"#define TUC_RUN_COUNT {RUN_COUNT}U"]
    for key, width in (("a", 32), ("b", 16), ("expected", 4)):
        lines.append(f"static const float TUC_{key.upper()}[{CASE_COUNT}][{width}] = {{")
        for case in cases:
            values = case[key] if key == "expected" else [x for row in case[key] for x in row]
            lines.append("  {" + ", ".join(f"{x!r}F" for x in values) + "},")
        lines.append("};")
    metadata = [{"name": case["name"], "vector_digest": _digest_payload(case)} for case in cases]
    plan = {
        "schema_version": "tuc.reduction_input_portfolio.v0",
        "source_intent_digest": cpu.plan["source_intent_digest"],
        "c11_code_digest": cpu.plan["generated_source_digest"],
        "cuda_code_digest": gpu["generated_source_digest"],
        "corpus_digest": _digest_payload(cases), "cases": metadata,
        "input_shapes": [[4, 8], [8, 2]], "output_shape": [4],
        "dtype": "float32", "domain": "quarter_integers_abs_le_4",
        "execution_order": [*range(CASE_COUNT), 0], "calls_per_case": 2,
        "case_tensor_bytes": 240, "recompile_between_cases": False,
        "blocked_claims": [*BLOCKED_CLAIMS, "arbitrary_fp32_inputs", "dynamic_shapes"],
    }
    for macro, key in (("INTENT", "source_intent_digest"), ("C11_CODE", "c11_code_digest"),
                       ("CUDA_CODE", "cuda_code_digest"), ("CORPUS", "corpus_digest")):
        lines.append(f'#define TUC_{macro}_DIGEST "{plan[key]}"')
    lines.extend(["#endif", ""])
    return {
        "vectors.h": "\n".join(lines),
        "portfolio.json": json.dumps(plan, indent=2, sort_keys=True) + "\n",
        "generated.c": cpu.source, "generated.h": cpu.header,
        "kernels.cuh": _read_bounded_file(ROOT / "docker/reduction-cuda/kernels.cuh").decode(),
    }


def verify_artifacts() -> dict[str, object]:
    files = artifact_files()
    for name, text in files.items():
        if _read_bounded_file(CONTEXT / name) != text.encode():
            raise BoundedCompilerEmissionError("portfolio artifact drift")
    return json.loads(files["portfolio.json"])


def expected_observation(target: str, mode: str = "execute") -> dict[str, object]:
    if target not in TARGETS or mode not in ("execute", "preflight"):
        raise BoundedCompilerEmissionError("portfolio mode rejected")
    plan = verify_artifacts()
    execute = mode == "execute"
    return {
        "schema_version": SCHEMA, "target": target, "mode": mode, "status": "PASS",
        "reason_code": "none", "source_intent_digest": plan["source_intent_digest"],
        "code_digest": plan[f"{target}_code_digest"], "corpus_digest": plan["corpus_digest"],
        "security_boundary_passed": True, "case_count": CASE_COUNT,
        "cases_passed": RUN_COUNT if execute else 0, "failed_run_index": -1,
        "generated_function_calls": RUN_COUNT * 2 if execute else 0,
        "case_tensor_bytes": 240 if execute else 0,
        "reference_correctness": execute, "repeated_baseline_passed": execute,
        "raw_values_serialized": False,
    }


def validate_observation(value: object, target: str, mode: str = "execute") -> dict[str, object]:
    _assert_plain_json(value)
    expected = expected_observation(target, mode)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("portfolio observation rejected")
    return expected


def validate_negative(value: object, target: str, mutation: str) -> None:
    if mutation not in ("missing-sum", "accidental-relu", "wrong-axis", "frozen-output"):
        raise BoundedCompilerEmissionError("portfolio mutation rejected")
    _assert_plain_json(value)
    index = 1 if mutation == "frozen-output" else 0
    expected = expected_observation(target)
    expected.update(status="ERROR", reason_code="reference_mismatch", cases_passed=index,
                    failed_run_index=index, generated_function_calls=(index + 1) * 2,
                    reference_correctness=False, repeated_baseline_passed=False)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("portfolio wrong-code check rejected")


def program_digest() -> str:
    names = [*artifact_files(), "common.h", "host.c", "device.cu", "Dockerfile",
             "Dockerfile.dockerignore", "build-c11.sh", "build-cuda.sh"]
    files = {name: CONTEXT / name for name in names}
    for name in (
        "examples/reduction_input_portfolio.py", "scripts/run_reduction_input_portfolio.sh"
    ):
        files[name] = ROOT / name
    return _digest_payload({name: "sha256:" + sha256(_read_bounded_file(path)).hexdigest()
                            for name, path in files.items()})


def build_record(value: object, target: str, image_id: str) -> dict[str, object]:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("portfolio image rejected")
    return {"schema_version": "tuc.reduction_input_portfolio_record.v0",
            "observation": validate_observation(value, target), "operator_image_id": image_id,
            "program_files_digest": program_digest(), "provenance": "same_maintainer_operator"}


def compare_records(cpu: object, gpu: object) -> dict[str, object]:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        _assert_plain_json(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("portfolio record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("portfolio record binding rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.reduction_input_portfolio_equivalence.v0", "status": "PASS",
            "targets": list(TARGETS), "case_count": CASE_COUNT, "runs_per_target": RUN_COUNT,
            "source_intent_digest": plan["source_intent_digest"],
            "corpus_digest": plan["corpus_digest"], "code_unchanged_from_single_vector": True,
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "comparison": "all_cases_exactly_match_same_reference", "raw_values_serialized": False,
            "blocked_claims": plan["blocked_claims"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--target", choices=TARGETS)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--negative", choices=("missing-sum", "accidental-relu",
                                              "wrong-axis", "frozen-output"))
    parser.add_argument("--image-id")
    parser.add_argument("--compare", nargs=2, type=Path)
    args = parser.parse_args()
    try:
        if args.compare:
            if args.validate or args.target or args.preflight or args.negative or args.image_id:
                raise BoundedCompilerEmissionError("conflicting modes")
            result = compare_records(*(load_observation(path) for path in args.compare))
        elif args.validate and args.target:
            value = load_observation(args.validate)
            if args.negative:
                if args.preflight or args.image_id:
                    raise BoundedCompilerEmissionError("conflicting modes")
                validate_negative(value, args.target, args.negative)
                result = {"negative_probe": args.negative, "rejected_by_reference": True}
            else:
                result = validate_observation(value, args.target,
                                              "preflight" if args.preflight else "execute")
                if args.image_id:
                    result = build_record(result, args.target, args.image_id)
        elif any((args.validate, args.target, args.preflight, args.negative, args.image_id)):
            raise BoundedCompilerEmissionError("observation and target required")
        else:
            result = verify_artifacts()
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError):
        print("reduction portfolio verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
