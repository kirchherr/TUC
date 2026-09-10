"""Pure emission and evidence validation for one fixed sm86 reduction program."""

from __future__ import annotations

import argparse
import json
import re
import sys
from hashlib import sha256
from pathlib import Path

from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _digest_text,
)
from examples.bounded_reduction_c11 import (
    ROOT,
    _read_bounded_file,
    load_observation,
    parse_fixed_source,
)
from examples.bounded_reduction_c11 import (
    build_artifacts as build_c11,
)
from examples.bounded_reduction_c11 import (
    expected_observation as expected_c11,
)
from examples.bounded_reduction_c11 import (
    validate_observation as validate_c11,
)
from examples.bounded_reduction_c11 import (
    verify_artifacts as verify_c11,
)

CONTEXT = ROOT / "docker/reduction-cuda"
SCHEMA = "tuc.bounded_reduction_cuda_observation.v0"
BLOCKED_CLAIMS = [
    "arbitrary_programs", "cross_vendor_execution", "general_cuda_backend",
    "independent_reproduction", "native_performance", "production_runtime_admission",
    "universal_hardware",
]


def artifact_files(payload: object) -> dict[str, str]:
    c11 = build_c11(payload)
    (rows, inner), (_, columns) = c11.plan["input_shapes"]
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
    plan = {
        **c11.plan,
        "schema_version": "tuc.bounded_reduction_cuda_emission.v0",
        "contract": "bounded_reduction_cuda.matmul_sum_axis1_sm86.v0",
        "c11_source_digest": c11.plan["generated_source_digest"],
        "generated_source_digest": _digest_text(kernels),
        "target": "nvidia_cuda_sm86", "ptx_jit": False,
        "kernel_launches": 2, "blocks_per_launch": 1, "threads_per_block": 32,
        "blocked_claims": BLOCKED_CLAIMS,
    }
    return {
        "kernels.cuh": kernels,
        "inputs.h": c11.inputs,
        "source_intent.json": json.dumps(c11.source_intent, indent=2, sort_keys=True) + "\n",
        "emission_plan.json": json.dumps(plan, indent=2, sort_keys=True) + "\n",
        "cuda_digest.h": f'#define TUC_CUDA_KERNEL_DIGEST "{_digest_text(kernels)}"\n',
    }


def verify_artifacts() -> dict[str, object]:
    verify_c11()
    files = artifact_files(parse_fixed_source())
    for name, expected in files.items():
        if _read_bounded_file(CONTEXT / name) != expected.encode("utf-8"):
            raise BoundedCompilerEmissionError("CUDA reduction artifact drift")
    return json.loads(files["emission_plan.json"])


def expected_observation(mode: str) -> dict[str, object]:
    plan = verify_artifacts()
    report = expected_c11(mode, plan)
    report.update(
        schema_version=SCHEMA, target="nvidia_cuda_sm86", visible_device_count=1,
        c11_source_digest=plan["c11_source_digest"],
    )
    return report


def validate_observation(value: object, mode: str = "execute") -> dict[str, object]:
    _assert_plain_json(value)
    expected = expected_observation(mode)
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("CUDA reduction observation rejected")
    return expected


def program_files_digest() -> str:
    names = (*artifact_files(parse_fixed_source()), "harness.cu", "Dockerfile",
             "Dockerfile.dockerignore", "build.sh")
    digests = {
        name: "sha256:" + sha256(_read_bounded_file(CONTEXT / name)).hexdigest()
        for name in names
    }
    for name in (
        "examples/bounded_reduction_cuda.py", "scripts/run_bounded_reduction_cuda_proof.sh"
    ):
        digests[name] = "sha256:" + sha256(_read_bounded_file(ROOT / name)).hexdigest()
    return _digest_payload(digests)


def build_record(observation: object, image_id: str) -> dict[str, object]:
    if re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise BoundedCompilerEmissionError("CUDA image identity rejected")
    return {
        "schema_version": "tuc.bounded_reduction_cuda_record.v0",
        "observation": validate_observation(observation),
        "operator_image_id": image_id,
        "program_files_digest": program_files_digest(),
        "provenance": "same_maintainer_explicit_operator",
    }


def build_equivalence(cpu: object, record: object) -> dict[str, object]:
    baseline = validate_c11(cpu)
    _assert_plain_json(record)
    if type(record) is not dict or type(record.get("operator_image_id")) is not str:
        raise BoundedCompilerEmissionError("CUDA record rejected")
    expected = build_record(record.get("observation"), record["operator_image_id"])
    if _canonical_json(record) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("CUDA record binding rejected")
    candidate = expected["observation"]
    for key in ("source_intent_digest", "vector_digest", "output_shape", "working_set_bytes"):
        if baseline[key] != candidate[key]:
            raise BoundedCompilerEmissionError("reduction target semantics differ")
    return {
        "schema_version": "tuc.bounded_reduction_target_equivalence.v0",
        "status": "PASS", "targets": ["c11_x86_64", "nvidia_cuda_sm86"],
        "source_intent_digest": baseline["source_intent_digest"],
        "vector_digest": baseline["vector_digest"], "output_shape": [4],
        "comparison": "both_exactly_match_same_fixed_reference",
        "c11_observation_digest": _digest_payload(baseline),
        "cuda_record_digest": _digest_payload(expected),
        "raw_values_serialized": False, "blocked_claims": BLOCKED_CLAIMS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-observation", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--record-image-id")
    parser.add_argument("--compare-record", type=Path)
    args = parser.parse_args()
    try:
        if args.compare_record:
            if args.validate_observation or args.preflight or args.record_image_id:
                raise BoundedCompilerEmissionError("conflicting modes")
            baseline_path = ROOT / "tests/golden/proofs/bounded_reduction_c11_observation.json"
            report = build_equivalence(
                load_observation(baseline_path),
                load_observation(args.compare_record),
            )
        elif args.validate_observation:
            report = validate_observation(
                load_observation(args.validate_observation),
                "preflight" if args.preflight else "execute",
            )
            if args.record_image_id:
                report = build_record(report, args.record_image_id)
        elif args.preflight or args.record_image_id:
            raise BoundedCompilerEmissionError("observation required")
        else:
            report = verify_artifacts()
        print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, ValueError):
        print("bounded CUDA reduction verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
