"""Restricted source -> matmul -> ReLU -> sum; pure native-proof verification."""

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
from tuc.frontend import ingest_triton_module_source_to_source_intent, source_intent_from_mapping

CONTEXT = ROOT / "docker/composed-chain"
TARGETS = ("c11", "cuda")
MUTATIONS = ("bypass-relu", "late-relu", "missing-sum", "wrong-stride",
             "incomplete-coverage", "over-budget", "nonfinite")
SOURCE = """import triton
import triton.language as tl

@triton.jit
def matmul_relu_reduction(a, b, y):
    projection = tl.dot(a, b)
    activated = tl.where(projection > 0, projection, 0)
    row_sum = tl.sum(activated, axis=1)
    tl.store(y, row_sum)
"""
INTENT_DIGEST = "sha256:e4572c28acc1c6e2f0ff774461208cadcb13ddf957ec79744ee474bd47f12af5"
CONTRACT = {
    "schema_version": "tuc.bounded_chain_numeric_contract.v0",
    "reference": "sum_c(max(sum_k(a[row,k]*b[k,c]),0))_over_exact_binary32_inputs",
    "rounding": "nearest_ties_even", "fma_contraction": False, "reassociation": False,
    "operation_order": ["sequential_matmul", "relu", "sequential_sum_axis1"],
    "underflow_overflow": "excluded_from_fixed_corpus",
    "unit_roundoff": "2^-24", "rounding_depth_bound": 13,
    "absolute_error_bound": "gamma_13 * sum_k_c(abs(a[row,k]*b[k,c]))",
    "relu_error_propagation": "1_Lipschitz",
    "interval_encoding": "binary64_endpoints_rounded_inward",
    "signed_zero": "numerical_equality_only", "admission": "fixed_ten_case_corpus_only",
}


def parse_source() -> dict:
    return ingest_triton_module_source_to_source_intent(
        SOURCE, source_name="research_composed_chain", kernel_name="matmul_relu_reduction",
        tensor_shapes={"a": (33, 7), "b": (7, 5), "y": (33,)},
    ).parser_result.source_intent_payload


def emit(payload: object) -> dict[str, str]:
    _assert_plain_json(payload)
    if _digest_payload(payload) != INTENT_DIGEST:
        raise BoundedCompilerEmissionError("chain Source Intent rejected")
    module = source_intent_from_mapping(payload)
    tensors = {t.name: t for t in module.tensors}
    matmul, relu, reduction = module.operations
    if (tuple(op.family for op in module.operations) != ("matmul", "elementwise", "reduction")
            or dict(relu.attributes) != {"elementwise_kind": "relu"}
            or dict(reduction.attributes) != {"axis": 1}
            or relu.inputs != matmul.outputs or reduction.inputs != relu.outputs
            or tuple(tensors[n].shape for n in matmul.inputs) != ((33, 7), (7, 5))
            or tensors[relu.outputs[0]].shape != (33, 5)
            or tensors[reduction.outputs[0]].shape != (33,)
            or any(t.dtype != "float32" for t in module.tensors)):
        raise BoundedCompilerEmissionError("chain typed semantics rejected")
    # Reuse frozen, reviewed primitive lowering only after checking the new chain.
    primitives = fp.shapes.emit(fp.shapes.parse_source("odd"), "odd")
    header = primitives["generated.h"].replace("#endif", (
        "void tuc_relu(const float *projection, float *activated);\n#endif"))
    body = """    const float value = projection[index];
    activated[index] = value < 0.0F ? 0.0F : value;
"""
    # NaN poison propagates through ReLU; admitted source inputs are finite only.
    host_relu = """
void tuc_relu(const float *projection, float *activated) {
  for (size_t index = 0; index < 165U; ++index) {
""" + body + "  }\n}\n"
    gpu_relu = """
__global__ void tuc_relu(const float *projection, float *activated) {
  const unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < 165U) {
""" + body + "  }\n}\n"
    return {"generated.h": header, "generated.c": primitives["generated.c"] + host_relu,
            "kernels.cuh": primitives["kernels.cuh"].replace("#endif", gpu_relu + "#endif")}


def corpus() -> list[dict]:
    cases = fp.corpus()
    # Cancellation supplies a first-run witness against moving ReLU after the sum.
    return [cases[3], *cases[:3], *cases[4:]]


def reference(case: dict) -> list[tuple[Fraction, Fraction]]:
    validated = fp.reference(case["a"], case["b"])
    result = []
    for row, (_, budget) in zip(case["a"], validated, strict=True):
        columns = [sum((Fraction(row[k]) * Fraction(case["b"][k][c])
                        for k in range(7)), Fraction()) for c in range(5)]
        result.append((sum((max(x, Fraction()) for x in columns), Fraction()), budget))
    return result


def ordered_reference(case: dict) -> list[float]:
    reference(case)
    result = []
    for row in case["a"]:
        columns = []
        for c in range(5):
            value = 0.0
            for k in range(7):
                product = fp.round_f32(Fraction(row[k]) * Fraction(case["b"][k][c]))
                value = fp.round_f32(Fraction(value) + Fraction(product))
            columns.append(max(value, 0.0))
        value = 0.0
        for x in columns:
            value = fp.round_f32(Fraction(value) + Fraction(x))
        result.append(value)
    return result


def artifact_files() -> dict[str, str]:
    payload = parse_source()
    files = emit(payload)
    cases = corpus()
    refs = [reference(c) for c in cases]
    ordered = [ordered_reference(c) for c in cases]
    rounded = 0
    for i in (*range(10), 0):
        for value, (exact, budget) in zip(ordered[i], refs[i], strict=True):
            if abs(Fraction(value) - exact) > budget:
                raise BoundedCompilerEmissionError("chain corpus exceeds contract")
            rounded += value != float(exact)
    for wrong, (exact, budget) in zip(fp.ordered_reference(cases[0]), refs[0], strict=True):
        if abs(Fraction(wrong) - exact) <= budget or abs(Fraction(max(wrong, 0)) - exact) <= budget:
            raise BoundedCompilerEmissionError("ReLU placement witness missing")
    plan = {"schema_version": "tuc.bounded_chain_plan.v0",
            "source_module_digest": _digest_text(SOURCE), "source_intent_digest": INTENT_DIGEST,
            "c11_code_digest": _digest_text(files["generated.c"]),
            "cuda_code_digest": _digest_text(files["kernels.cuh"]),
            "corpus_digest": _digest_payload(cases), "contract_digest": _digest_payload(CONTRACT),
            "operation_order": ["matmul", "relu", "sum_axis1"],
            "input_shapes": [[33, 7], [7, 5]], "intermediate_shapes": [[33, 5], [33, 5]],
            "output_shape": [33], "case_count": 10, "runs": 11, "tensor_bytes": 2516,
            "expected_rounded_outputs": rounded, "generated_calls_per_run": 3,
            "runtime_admission": False,
            "blocked_claims": [*fp.shapes.BLOCKED_CLAIMS, "arbitrary_fp32_inputs",
                               "dynamic_shapes", "bitwise_backend_equivalence",
                               "relative_error_guarantee", "general_chain_lowering"]}
    inputs = ["#ifndef TUC_CHAIN_INPUTS_H", "#define TUC_CHAIN_INPUTS_H"]
    for name, value in (("ROWS", 33), ("INNER", 7), ("COLUMNS", 5), ("CASES", 10),
                        ("RUNS", 11), ("PROJECTION_BLOCKS", 6), ("OUTPUT_BLOCKS", 2),
                        ("TENSOR_BYTES", 2516)):
        inputs.append(f"#define TUC_{name} {value}U")
    for name, key in (("INTENT", "source_intent_digest"), ("C11_CODE", "c11_code_digest"),
                      ("CUDA_CODE", "cuda_code_digest"), ("CORPUS", "corpus_digest"),
                      ("CONTRACT", "contract_digest")):
        inputs.append(f'#define TUC_{name}_DIGEST "{plan[key]}"')
    for key, width in (("a", 231), ("b", 35)):
        inputs.append(f"static const float TUC_{key.upper()}[10][{width}] = {{")
        for case in cases:
            values = (fp._hex(x) + "F" for row in case[key] for x in row)
            inputs.append("  {" + ", ".join(values) + "},")
        inputs.append("};")
    oracle = ["#ifndef TUC_CHAIN_ORACLE_H", "#define TUC_CHAIN_ORACLE_H"]
    for name in ("LOWER", "UPPER", "REFERENCE64", "ORDERED"):
        oracle.append(f"static const double TUC_{name}[10][33] = {{")
        for i, bounds in enumerate(refs):
            values = ordered[i] if name == "ORDERED" else [
                float(x) if name == "REFERENCE64" else fp.interval(x, e)[name == "UPPER"]
                for x, e in bounds]
            oracle.append("  {" + ", ".join(map(fp._hex, values)) + "},")
        oracle.append("};")
    files.update({"inputs.h": "\n".join([*inputs, "#endif", ""]),
                  "oracle.h": "\n".join([*oracle, "#endif", ""])})
    for name, value in (("source_intent", payload), ("numeric_contract", CONTRACT),
                        ("emission_plan", plan)):
        files[name + ".json"] = json.dumps(value, indent=2, sort_keys=True) + "\n"
    return files


def verify_artifacts() -> dict:
    files = artifact_files()
    for name, value in files.items():
        if _read_bounded_file(CONTEXT / name) != value.encode():
            raise BoundedCompilerEmissionError("chain artifact drift")
    return json.loads(files["emission_plan.json"])


def expected_observation(target: str, preflight: bool = False) -> dict:
    if type(target) is not str or target not in TARGETS or type(preflight) is not bool:
        raise BoundedCompilerEmissionError("chain mode rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_chain_observation.v0", "target": target,
            "mode": "preflight" if preflight else "execute",
            "status": "PASS", "reason_code": "none",
            **{key: plan[key] for key in
               ("source_intent_digest", "corpus_digest", "contract_digest")},
            "code_digest": plan[f"{target}_code_digest"],
            "operation_order": plan["operation_order"],
            "output_shape": [33], "case_count": 10, "cases_passed": 0 if preflight else 11,
            "generated_function_calls": 0 if preflight else 33, "failed_run_index": -1,
            "tensor_bytes": 0 if preflight else 2516, "scalar_checks": 0 if preflight else 363,
            "outputs_differing_from_reference64": (
                0 if preflight else plan["expected_rounded_outputs"]),
            "security_boundary_passed": True, "numeric_contract_passed": not preflight,
            "execution_policy_passed": not preflight, "repeated_baseline_passed": not preflight,
            "raw_values_serialized": False}


def validate_observation(value: object, target: str, preflight: bool = False) -> dict:
    _assert_plain_json(value)
    expected = expected_observation(target, preflight)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("chain observation rejected")
    return expected


def validate_negative(value: object, target: str, mutation: str) -> None:
    if type(mutation) is not str or mutation not in MUTATIONS:
        raise BoundedCompilerEmissionError("chain mutation rejected")
    _assert_plain_json(value)
    expected = expected_observation(target)
    expected.update(status="ERROR", reason_code="numeric_contract_mismatch", cases_passed=0,
                    failed_run_index=0, generated_function_calls=3, scalar_checks=0,
                    outputs_differing_from_reference64=0, numeric_contract_passed=False,
                    execution_policy_passed=False, repeated_baseline_passed=False)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("chain negative observation rejected")


def program_digest() -> str:
    paths = [CONTEXT / name for name in (*artifact_files(), "host.c", "device.cu", "common.h",
             "Dockerfile", "Dockerfile.dockerignore", "build-c11.sh", "build-cuda.sh")]
    paths += [ROOT / name for name in ("examples/bounded_composed_chain.py",
              "examples/reduction_fp32_contract.py", "examples/bounded_reduction_shapes.py",
              "scripts/run_bounded_composed_chain.sh")]
    return _digest_payload({p.relative_to(ROOT).as_posix():
                            "sha256:" + sha256(_read_bounded_file(p)).hexdigest() for p in paths})


def build_record(value: object, target: str, image_id: str) -> dict:
    if type(image_id) is not str or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("chain image rejected")
    return {"schema_version": "tuc.bounded_chain_record.v0",
            "observation": validate_observation(value, target), "operator_image_id": image_id,
            "program_files_digest": program_digest(), "provenance": "same_maintainer_operator"}


def compare_records(cpu: object, gpu: object) -> dict:
    for target, record in zip(TARGETS, (cpu, gpu), strict=True):
        _assert_plain_json(record)
        if type(record) is not dict:
            raise BoundedCompilerEmissionError("chain record rejected")
        expected = build_record(record.get("observation"), target, record.get("operator_image_id"))
        if _canonical_json(record) != _canonical_json(expected):
            raise BoundedCompilerEmissionError("chain record binding rejected")
    plan = verify_artifacts()
    return {"schema_version": "tuc.bounded_chain_comparison.v0", "status": "PASS",
            **{key: plan[key] for key in
               ("source_intent_digest", "corpus_digest", "contract_digest",
                "operation_order", "blocked_claims")},
            "targets": list(TARGETS), "runs_per_target": 11, "scalar_checks_per_target": 363,
            "c11_record_digest": _digest_payload(cpu), "cuda_record_digest": _digest_payload(gpu),
            "comparison": "both_targets_satisfy_same_nonlinear_reference_contract_and_order",
            "pairwise_absolute_error_bound": "twice_per_row_contract_budget",
            "raw_values_serialized": False}


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
        print("bounded chain verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
