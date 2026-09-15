"""Pure, two-profile reduction lowering and odd-shape observation verification."""

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
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_reduction_c11 import ROOT, _read_bounded_file, load_observation
from examples.bounded_reduction_cuda import BLOCKED_CLAIMS
from examples.source_to_intent_research_kernel_ingress import (
    REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE as SOURCE,
)
from tuc.frontend import ingest_triton_module_source_to_source_intent, source_intent_from_mapping

CONTEXT = ROOT / "docker/reduction-shapes"
PROFILES = {"baseline": (4, 8, 2), "odd": (33, 7, 5)}
INTENT_DIGESTS = {
    "baseline": "sha256:8089f3a64aca72e2ee7d71a3f4eb10c7454d3c67f04cffa4db300734176cc614",
    "odd": "sha256:54415a7218b284a9e0e8927ffc2a9d5eef0ff5cb9d5ccd8669b64d0f2a4c44a1",
}
TARGETS = ("c11", "cuda")
MUTATIONS = ("missing-sum", "wrong-stride", "incomplete-coverage")


def dimensions(profile: str) -> tuple[int, int, int]:
    if type(profile) is not str or profile not in PROFILES:
        raise BoundedCompilerEmissionError("shape profile rejected")
    return PROFILES[profile]


def parse_source(profile: str) -> dict:
    rows, inner, columns = dimensions(profile)
    result = ingest_triton_module_source_to_source_intent(
        SOURCE, source_name="research_matmul_reduction", kernel_name="matmul_reduction",
        tensor_shapes={"a": (rows, inner), "b": (inner, columns), "y": (rows,)},
    )
    return result.parser_result.source_intent_payload


def emit(payload: object, profile: str) -> dict[str, str]:
    dimensions(profile)
    _assert_plain_json(payload)
    if _digest_payload(payload) != INTENT_DIGESTS[profile]:
        raise BoundedCompilerEmissionError("shape Source Intent rejected")
    module = source_intent_from_mapping(payload)
    tensors = {t.name: t for t in module.tensors}
    matmul, reduction = module.operations
    rows, inner = tensors[matmul.inputs[0]].shape
    other_inner, columns = tensors[matmul.inputs[1]].shape
    if (
        (rows, inner, columns) != dimensions(profile) or inner != other_inner
        or (matmul.family, reduction.family) != ("matmul", "reduction")
        or dict(reduction.attributes) != {"axis": 1}
        or reduction.inputs != matmul.outputs
        or tensors[reduction.outputs[0]].shape != (rows,)
        or any(t.dtype != "float32" for t in module.tensors)
    ):
        raise BoundedCompilerEmissionError("shape typed semantics rejected")
    header = """#ifndef TUC_REDUCTION_GENERATED_H
#define TUC_REDUCTION_GENERATED_H
void tuc_projection(const float *a, const float *b, float *projection);
void tuc_sum_axis1(const float *projection, float *output);
#endif
"""
    source = f"""#include "generated.h"
#include <stddef.h>

void tuc_projection(const float *a, const float *b, float *projection) {{
  for (size_t row = 0; row < {rows}U; ++row) {{
    for (size_t column = 0; column < {columns}U; ++column) {{
      float value = 0.0F;
      for (size_t inner = 0; inner < {inner}U; ++inner) {{
        value += a[row * {inner}U + inner] * b[inner * {columns}U + column];
      }}
      projection[row * {columns}U + column] = value;
    }}
  }}
}}

void tuc_sum_axis1(const float *projection, float *output) {{
  for (size_t row = 0; row < {rows}U; ++row) {{
    float value = 0.0F;
    for (size_t column = 0; column < {columns}U; ++column) {{
      value += projection[row * {columns}U + column];
    }}
    output[row] = value;
  }}
}}
"""
    kernels = f"""#ifndef TUC_REDUCTION_KERNELS_CUH
#define TUC_REDUCTION_KERNELS_CUH
__global__ void tuc_projection(const float *a, const float *b, float *projection) {{
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < {rows * columns}U) {{
    const unsigned int row = index / {columns}U;
    const unsigned int column = index % {columns}U;
    float value = 0.0F;
    for (unsigned int inner = 0; inner < {inner}U; ++inner) {{
      value += a[row * {inner}U + inner] * b[inner * {columns}U + column];
    }}
    projection[index] = value;
  }}
}}

__global__ void tuc_sum_axis1(const float *projection, float *output) {{
  const unsigned int row = blockIdx.x * blockDim.x + threadIdx.x;
  if (row < {rows}U) {{
    float value = 0.0F;
    for (unsigned int column = 0; column < {columns}U; ++column) {{
      value += projection[row * {columns}U + column];
    }}
    output[row] = value;
  }}
}}
#endif
"""
    return {"generated.c": source, "generated.h": header, "kernels.cuh": kernels}


def exact_reference(a: object, b: object) -> list[float]:
    _assert_plain_json({"a": a, "b": b})
    for matrix, rows, columns in ((a, 33, 7), (b, 7, 5)):
        if type(matrix) is not list or len(matrix) != rows:
            raise BoundedCompilerEmissionError("shape vector rejected")
        for row in matrix:
            if type(row) is not list or len(row) != columns:
                raise BoundedCompilerEmissionError("shape vector row rejected")
            for x in row:
                if type(x) is not float or not -4 <= x <= 4 or x * 4 % 1:
                    raise BoundedCompilerEmissionError("shape numeric domain rejected")
    sums = [sum((Fraction(x) for x in row), Fraction()) for row in b]
    return [float(sum((Fraction(x) * y for x, y in zip(row, sums, strict=True)), Fraction()))
            for row in a]


def corpus() -> list[dict]:
    a = [[((r * 3 + k * 2) % 13 - 6) / 4 for k in range(7)] for r in range(33)]
    b = [[((k * 5 + c * 3) % 11 - 5) / 4 for c in range(5)] for k in range(7)]
    cases = []

    def add(name, left, right):
        cases.append({"name": name, "a": left, "b": right,
                      "expected": exact_reference(left, right)})

    add("baseline", a, b)
    add("zero_a", [[0.0] * 7 for _ in range(33)], b)
    add("negated_a", [[-x for x in row] for row in a], b)
    add("reversed_a_rows", list(reversed(a)), b)
    add("rotated_b_columns", a, [row[1:] + row[:1] for row in b])
    add("zero_b", a, [[0.0] * 5 for _ in range(7)])
    add("last_row_only", [[0.0] * 7 for _ in range(32)] + [a[-1]], b)
    for k in range(7):
        add(f"basis_{k}", [[1.0 if i == k else 0.0 for i in range(7)] for _ in range(33)], b)
    rng = random.Random(308)
    for index in range(6):
        add(f"mixed_{index}", [[rng.randint(-8, 8) / 4 for _ in range(7)] for _ in range(33)],
            [[rng.randint(-8, 8) / 4 for _ in range(5)] for _ in range(7)])
    return cases


def artifact_files() -> dict[str, str]:
    payload = parse_source("odd")
    files = emit(payload, "odd")
    rows, inner, columns = dimensions("odd")
    cases = corpus()
    plan = {
        "schema_version": "tuc.bounded_reduction_shape_emission.v0", "profile": "odd",
        "source_module_digest": _digest_text(SOURCE),
        "source_intent_digest": _digest_payload(payload),
        "c11_code_digest": _digest_text(files["generated.c"]),
        "cuda_code_digest": _digest_text(files["kernels.cuh"]),
        "corpus_digest": _digest_payload(cases), "case_count": len(cases), "runs": len(cases) + 1,
        "input_shapes": [[rows, inner], [inner, columns]], "output_shape": [rows],
        "projection_shape": [rows, columns], "reduction_axis": 1, "dtype": "float32",
        "cuda_launches": [{"blocks": (count + 31) // 32, "threads": 32, "logical_items": count}
                          for count in (rows * columns, rows)],
        "tensor_bytes": (rows * inner + inner * columns + rows * columns + rows) * 4,
        "numeric_domain": "quarter_integers_abs_le_4", "runtime_admission": False,
        "blocked_claims": [*BLOCKED_CLAIMS, "arbitrary_fp32_inputs", "dynamic_shapes"],
    }
    lines = ["#ifndef TUC_SHAPE_INPUTS_H", "#define TUC_SHAPE_INPUTS_H"]
    for name, value in (("ROWS", rows), ("INNER", inner), ("COLUMNS", columns),
                        ("CASES", len(cases)), ("RUNS", len(cases) + 1),
                        ("PROJECTION_BLOCKS", (rows * columns + 31) // 32),
                        ("OUTPUT_BLOCKS", (rows + 31) // 32),
                        ("TENSOR_BYTES", plan["tensor_bytes"])):
        lines.append(f"#define TUC_{name} {value}U")
    for name, key in (("INTENT", "source_intent_digest"), ("C11_CODE", "c11_code_digest"),
                      ("CUDA_CODE", "cuda_code_digest"), ("CORPUS", "corpus_digest")):
        lines.append(f'#define TUC_{name}_DIGEST "{plan[key]}"')
    for key, width in (("a", rows * inner), ("b", inner * columns), ("expected", rows)):
        lines.append(f"static const float TUC_{key.upper()}[{len(cases)}][{width}] = {{")
        for case in cases:
            values = case[key] if key == "expected" else [x for row in case[key] for x in row]
            lines.append("  {" + ", ".join(f"{x!r}F" for x in values) + "},")
        lines.append("};")
    files["inputs.h"] = "\n".join([*lines, "#endif", ""])
    files["source_intent.json"] = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    files["emission_plan.json"] = json.dumps(plan, indent=2, sort_keys=True) + "\n"
    return files


def verify_artifacts() -> dict:
    files = artifact_files()
    for name, value in files.items():
        if _read_bounded_file(CONTEXT / name) != value.encode():
            raise BoundedCompilerEmissionError("shape artifact drift")
    return json.loads(files["emission_plan.json"])


def expected_observation(target: str, preflight: bool = False) -> dict:
    if type(target) is not str or target not in TARGETS or type(preflight) is not bool:
        raise BoundedCompilerEmissionError("shape mode rejected")
    plan = verify_artifacts()
    return {
        "schema_version": "tuc.bounded_reduction_shape_observation.v0", "target": target,
        "mode": "preflight" if preflight else "execute", "status": "PASS", "reason_code": "none",
        "source_intent_digest": plan["source_intent_digest"],
        "code_digest": plan[f"{target}_code_digest"],
        "corpus_digest": plan["corpus_digest"], "output_shape": [33], "case_count": 20,
        "cases_passed": 0 if preflight else 21, "generated_function_calls": 0 if preflight else 42,
        "failed_run_index": -1, "tensor_bytes": 0 if preflight else 1856,
        "security_boundary_passed": True, "reference_correctness": not preflight,
        "repeated_baseline_passed": not preflight, "raw_values_serialized": False,
    }


def validate_observation(value: object, target: str, preflight: bool = False) -> dict:
    _assert_plain_json(value)
    expected = expected_observation(target, preflight)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("shape observation rejected")
    return expected


def validate_negative(value: object, target: str, mutation: str) -> None:
    if mutation not in MUTATIONS:
        raise BoundedCompilerEmissionError("shape mutation rejected")
    _assert_plain_json(value)
    expected = expected_observation(target)
    expected.update(status="ERROR", reason_code="reference_mismatch", cases_passed=0,
                    failed_run_index=0, generated_function_calls=2,
                    reference_correctness=False, repeated_baseline_passed=False)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("shape negative observation rejected")


def program_digest() -> str:
    names = [*artifact_files(), "common.h", "host.c", "device.cu", "Dockerfile",
             "Dockerfile.dockerignore", "build-c11.sh", "build-cuda.sh"]
    files = {name: CONTEXT / name for name in names}
    for name in ("examples/bounded_reduction_shapes.py", "scripts/run_bounded_reduction_shapes.sh"):
        files[name] = ROOT / name
    return _digest_payload({name: "sha256:" + sha256(_read_bounded_file(path)).hexdigest()
                            for name, path in files.items()})


def build_record(value: object, target: str, image_id: str) -> dict:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("shape image rejected")
    return {"schema_version": "tuc.bounded_reduction_shape_record.v0",
            "observation": validate_observation(value, target), "operator_image_id": image_id,
            "program_files_digest": program_digest(), "provenance": "same_maintainer_operator"}


def compare_records(cpu: object, gpu: object) -> dict:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        _assert_plain_json(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("shape record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("shape record binding rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_reduction_shape_equivalence.v0", "status": "PASS",
            "source_intent_digest": plan["source_intent_digest"],
            "input_shapes": plan["input_shapes"],
            "output_shape": [33], "targets": list(TARGETS), "case_count": 20, "runs_per_target": 21,
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "comparison": "all_cases_exactly_match_same_reference", "raw_values_serialized": False,
            "blocked_claims": plan["blocked_claims"]}


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
                report = {"negative_probe": args.negative, "rejected_by_reference": True}
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
        print("bounded reduction shape verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
