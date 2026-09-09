"""Emit and verify the fixed Matmul -> axis-1 Sum C11 research program."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import cast

from examples.bounded_compiler_emission import (
    WORKLOAD_MANIFEST_PATH,
    BoundedCompilerEmissionError,
    _assert_plain_json,
    _canonical_json,
    _digest_payload,
    _digest_text,
    _load_json,
    _object_without_duplicates,
    _reject_non_finite,
    assert_compiler_emission_workload,
)
from examples.bounded_compiler_emitted_c11_emission import _render_array
from examples.source_to_intent_research_kernel_ingress import (
    REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
)
from tuc.frontend import (
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
)

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "docker/reduction-c11"
SOURCE_INTENT_DIGEST = (
    "sha256:8089f3a64aca72e2ee7d71a3f4eb10c7454d3c67f04cffa4db300734176cc614"
)
CONTRACT = "bounded_reduction_c11.matmul_sum_axis1.v0"
BLOCKED_CLAIMS = [
    "arbitrary_programs", "cross_target_reduction_equivalence",
    "general_source_ingestion", "independent_reproduction",
    "native_performance", "production_runtime_admission", "universal_hardware",
]
EXPECTED_OUTPUT = (-5.875, 2.625, 5.125, 4.75)
MAX_FILE_BYTES = 64 * 1024


@dataclass(frozen=True)
class ReductionArtifacts:
    """Review-time artifacts; construction never compiles or executes code."""

    source_intent: dict[str, object]
    source: str
    header: str
    inputs: str
    plan: dict[str, object]


def parse_fixed_source() -> dict[str, object]:
    """Parse only the reviewed inert module, without executing its imports."""
    result = ingest_triton_module_source_to_source_intent(
        REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
        source_name="research_matmul_reduction",
        kernel_name="matmul_reduction",
        tensor_shapes={"a": (4, 8), "b": (8, 2), "y": (4,)},
    )
    return cast(dict[str, object], result.parser_result.source_intent_payload)


def build_artifacts(payload: object) -> ReductionArtifacts:
    """Lower one exact typed program, with fixed symbols and bounded loops."""
    _assert_plain_json(payload)
    if _digest_payload(payload) != SOURCE_INTENT_DIGEST:
        raise BoundedCompilerEmissionError("reduction Source Intent drift")
    module = source_intent_from_mapping(payload)
    tensors = {tensor.name: tensor for tensor in module.tensors}
    matmul, reduction = module.operations
    if (
        (matmul.family, reduction.family) != ("matmul", "reduction")
        or dict(reduction.attributes) != {"axis": 1}
        or reduction.inputs != matmul.outputs
        or any(tensor.dtype != "float32" for tensor in module.tensors)
    ):
        raise BoundedCompilerEmissionError("reduction semantics drift")
    rows, inner = tensors[matmul.inputs[0]].shape
    _, columns = tensors[matmul.inputs[1]].shape
    if (rows, inner, columns) != (4, 8, 2):
        raise BoundedCompilerEmissionError("reduction shape budget rejected")
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
    workload = assert_compiler_emission_workload(_load_json(WORKLOAD_MANIFEST_PATH))
    inputs = cast(dict[str, list[list[float]]], workload["inputs"])
    # An exact rational oracle contracts B first, unlike the emitted matmul.
    b_sums = [sum((Fraction(x) for x in row), Fraction(0)) for row in inputs["b"]]
    oracle = [
        sum((Fraction(x) * y for x, y in zip(row, b_sums, strict=True)), Fraction(0))
        for row in inputs["a"]
    ]
    if oracle != [Fraction(x) for x in EXPECTED_OUTPUT]:
        raise BoundedCompilerEmissionError("reduction rational reference drift")
    vector_digest = _digest_payload({"inputs": inputs, "expected_output": EXPECTED_OUTPUT})
    input_lines = ["#ifndef TUC_REDUCTION_INPUTS_H", "#define TUC_REDUCTION_INPUTS_H"]
    for name in ("a", "b"):
        input_lines.extend(
            _render_array("TUC_" + name.upper(), [x for row in inputs[name] for x in row])
        )
    input_lines.extend([
        f'#define TUC_SOURCE_INTENT_DIGEST "{SOURCE_INTENT_DIGEST}"',
        f'#define TUC_GENERATED_SOURCE_DIGEST "{_digest_text(source)}"',
        f'#define TUC_VECTOR_DIGEST "{vector_digest}"',
        "#endif", "",
    ])
    plan: dict[str, object] = {
        "schema_version": "tuc.bounded_reduction_c11_emission.v0",
        "contract": CONTRACT,
        "source_module_digest": _digest_text(REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE),
        "source_intent_digest": SOURCE_INTENT_DIGEST,
        "generated_source_digest": _digest_text(source),
        "vector_digest": vector_digest,
        "operation_families": ["matmul", "reduction"],
        "reduction_axis": 1,
        "input_shapes": [[rows, inner], [inner, columns]],
        "output_shape": [rows],
        "working_set_bytes": (rows * inner + inner * columns + rows * columns + rows) * 4,
        "source_execution": False,
        "runtime_admission": False,
        "blocked_claims": BLOCKED_CLAIMS,
    }
    return ReductionArtifacts(
        cast(dict[str, object], payload), source, header, "\n".join(input_lines), plan
    )


def artifact_files(artifacts: ReductionArtifacts) -> dict[str, str]:
    return {
        "generated.c": artifacts.source,
        "generated.h": artifacts.header,
        "inputs.h": artifacts.inputs,
        "source_intent.json": json.dumps(artifacts.source_intent, indent=2, sort_keys=True) + "\n",
        "emission_plan.json": json.dumps(artifacts.plan, indent=2, sort_keys=True) + "\n",
    }


def verify_artifacts() -> ReductionArtifacts:
    artifacts = build_artifacts(parse_fixed_source())
    for name, expected in artifact_files(artifacts).items():
        path = CONTEXT / name
        if _read_bounded_file(path) != expected.encode("utf-8"):
            raise BoundedCompilerEmissionError("reduction generated artifact drift")
    return artifacts


def _read_bounded_file(path: Path) -> bytes:
    def identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns

    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_FILE_BYTES:
            raise BoundedCompilerEmissionError("reduction file boundary rejected")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), "rb") as handle:
            opened = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
                raise BoundedCompilerEmissionError("reduction file changed")
            raw = handle.read(MAX_FILE_BYTES + 1)
            after = os.fstat(handle.fileno())
        if (
            len(raw) != before.st_size or identity(after) != identity(before)
            or identity(path.lstat()) != identity(before)
        ):
            raise BoundedCompilerEmissionError("reduction file changed")
        return raw
    except OSError as exc:
        raise BoundedCompilerEmissionError("reduction file unavailable") from exc


def load_observation(path: Path) -> object:
    try:
        value = json.loads(
            _read_bounded_file(path).decode("utf-8", errors="strict"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_non_finite,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise BoundedCompilerEmissionError("reduction observation JSON rejected") from exc
    _assert_plain_json(value)
    return value


def expected_observation(mode: str, plan: dict[str, object]) -> dict[str, object]:
    if mode not in {"preflight", "execute"}:
        raise BoundedCompilerEmissionError("reduction mode rejected")
    return {
        "schema_version": "tuc.bounded_reduction_c11_observation.v0",
        "status": "PASS",
        "mode": mode,
        "reason_code": "none",
        "source_intent_digest": SOURCE_INTENT_DIGEST,
        "generated_source_digest": plan["generated_source_digest"],
        "vector_digest": plan["vector_digest"],
        "generated_function_calls": 2 if mode == "execute" else 0,
        "reference_correctness": mode == "execute",
        "security_boundary_passed": True,
        "output_shape": [4],
        "working_set_bytes": 240 if mode == "execute" else 0,
        "raw_values_serialized": False,
    }


def validate_observation(value: object, mode: str = "execute") -> dict[str, object]:
    _assert_plain_json(value)
    artifacts = verify_artifacts()
    expected = expected_observation(mode, artifacts.plan)
    # Canonical JSON comparison preserves bool/int distinctions in public evidence.
    if _canonical_json(value) != _canonical_json(expected):
        raise BoundedCompilerEmissionError("reduction observation rejected")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-observation", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    try:
        if args.validate_observation:
            report = validate_observation(
                load_observation(args.validate_observation),
                "preflight" if args.preflight else "execute",
            )
        else:
            report = verify_artifacts().plan
        print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        del exc
        print("bounded reduction C11 verification rejected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
