"""Emit one reviewed C11 target from one exact Source Intent slice."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from examples.bounded_compiler_emission import (
    COMPILER_EMISSION_SOURCE_INTENT_DIGEST,
    COMPILER_EMISSION_WORKLOAD_CONTRACT,
    COMPILER_EMISSION_WORKLOAD_DIGEST,
    MAX_EMITTED_HEADER_BYTES,
    BoundedCompilerEmissionError,
    _digest_payload,
    _digest_text,
    _load_json,
    _matrix,
    _read_text,
    assert_compiler_emission_source_intent,
    assert_compiler_emission_workload,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
C11_CONTEXT_PATH = REPOSITORY_ROOT / "docker/c11-observation"
C11_SOURCE_INTENT_PATH = C11_CONTEXT_PATH / "compiler_emitted_source_intent.v0.json"
C11_WORKLOAD_MANIFEST_PATH = C11_CONTEXT_PATH / "compiler_emitted_workload.v0.json"
C11_WORKLOAD_HEADER_PATH = C11_CONTEXT_PATH / "compiler_emitted_c11_workload.h"
C11_GENERATED_HEADER_PATH = (
    C11_CONTEXT_PATH / "generated_compiler_emitted_c11_functions.h"
)
C11_GENERATED_SOURCE_PATH = (
    C11_CONTEXT_PATH / "generated_compiler_emitted_c11_functions.c"
)
C11_EMISSION_PLAN_PATH = C11_CONTEXT_PATH / "compiler_emission_plan.v0.json"

C11_EMISSION_SCHEMA_VERSION = "tuc.bounded_compiler_emitted_c11_plan.v0"
C11_EMISSION_CONTRACT = "bounded_c11_emission.exact_source_intent_x86_64.v0"
C11_TARGET_PROFILE = "linux-x86_64-static-c11-compiler-emitted"
C11_BLOCKED_CLAIMS = (
    "arbitrary_source_intent",
    "cross_isa_portability",
    "dynamic_shapes_or_inputs",
    "free_form_c",
    "general_cpu_backend",
    "native_performance_parity",
    "production_runtime_admission",
    "runtime_code_generation",
    "source_text_execution",
)

MAX_C11_GENERATED_SOURCE_BYTES = 16 * 1024
MAX_C11_PLAN_BYTES = 32 * 1024


@dataclass(frozen=True)
class C11CompilerEmissionArtifacts:
    """Deterministic C11 artifacts for the single admitted program."""

    generated_header: str
    generated_source: str
    plan: dict[str, object]
    workload_header: str


def _plan_core(source_intent: object, workload: object) -> dict[str, object]:
    source = assert_compiler_emission_source_intent(source_intent)
    vector = assert_compiler_emission_workload(workload)
    return {
        "blocked_claims": list(C11_BLOCKED_CLAIMS),
        "code_generation_phase": "trusted_review_time_before_container_build",
        "emission_contract": C11_EMISSION_CONTRACT,
        "identifier_policy": "fixed_symbols_no_source_identifier_interpolation",
        "operations": [
            {
                "family": "matmul",
                "function_call_count": 1,
                "function_symbol": "tuc_projection_matmul_4x8x2_f32",
                "input_shapes": [[4, 8], [8, 2]],
                "operation": "projection",
                "output_shape": [4, 2],
            },
            {
                "attributes": {"elementwise_kind": "relu"},
                "family": "elementwise",
                "function_call_count": 1,
                "function_symbol": "tuc_activated_relu_4x2_f32",
                "input_shapes": [[4, 2]],
                "operation": "activated",
                "output_shape": [4, 2],
            },
        ],
        "schema_version": C11_EMISSION_SCHEMA_VERSION,
        "source_intent_digest": _digest_payload(source),
        "source_intent_schema_version": source["schema_version"],
        "target": {
            "architecture": "x86_64",
            "binary_format": "elf64",
            "compiler_contract": "gcc-14.2.0",
            "cuda_dependency": False,
            "execution_model": "bounded_sequential_host_functions",
            "linkage": "static",
            "source_language": "c11",
            "target_profile": C11_TARGET_PROFILE,
        },
        "workload_contract": vector["workload_contract"],
        "workload_digest": _digest_payload(vector),
    }


def _render_generated_header(core: dict[str, object]) -> str:
    operations = cast(list[dict[str, object]], core["operations"])
    if [item["family"] for item in operations] != ["matmul", "elementwise"]:
        raise BoundedCompilerEmissionError("C11 emission operation sequence rejected")
    return """#ifndef TUC_GENERATED_COMPILER_EMITTED_C11_FUNCTIONS_H
#define TUC_GENERATED_COMPILER_EMITTED_C11_FUNCTIONS_H

void tuc_projection_matmul_4x8x2_f32(const float *a, const float *b,
                                     float *projection);
void tuc_activated_relu_4x2_f32(const float *projection, float *activated);

#endif
"""


def _render_generated_source(core: dict[str, object]) -> str:
    operations = cast(list[dict[str, object]], core["operations"])
    if cast(dict[str, object], operations[1])["attributes"] != {
        "elementwise_kind": "relu"
    }:
        raise BoundedCompilerEmissionError("C11 emission elementwise semantics rejected")
    return """#include "generated_compiler_emitted_c11_functions.h"

#include <stddef.h>

void tuc_projection_matmul_4x8x2_f32(const float *a, const float *b,
                                     float *projection) {
  for (size_t row = 0; row < 4U; ++row) {
    for (size_t column = 0; column < 2U; ++column) {
      float value = 0.0F;
      for (size_t inner = 0; inner < 8U; ++inner) {
        value += a[(row * 8U) + inner] * b[(inner * 2U) + column];
      }
      projection[(row * 2U) + column] = value;
    }
  }
}

void tuc_activated_relu_4x2_f32(const float *projection, float *activated) {
  for (size_t index = 0; index < 8U; ++index) {
    const float value = projection[index];
    activated[index] = value > 0.0F ? value : 0.0F;
  }
}
"""


def _float_literal(value: float) -> str:
    rendered = repr(float(value))
    if rendered == "-0.0":
        rendered = "0.0"
    return f"{rendered}F"


def _render_array(name: str, values: list[float]) -> list[str]:
    lines = [f"static const float {name}[{len(values)}] = {{"]
    lines.extend(f"    {_float_literal(value)}," for value in values)
    lines.append("};")
    return lines


def _render_workload_header(workload: dict[str, object]) -> str:
    inputs = cast(dict[str, object], workload["inputs"])
    a = [item for row in _matrix(inputs["a"], 4, 8) for item in row]
    b = [item for row in _matrix(inputs["b"], 8, 2) for item in row]
    output = [
        item for row in _matrix(workload["expected_output"], 4, 2) for item in row
    ]
    lines = [
        "#ifndef TUC_COMPILER_EMITTED_C11_WORKLOAD_H",
        "#define TUC_COMPILER_EMITTED_C11_WORKLOAD_H",
        "",
        f'#define TUC_C11_WORKLOAD_CONTRACT "{COMPILER_EMISSION_WORKLOAD_CONTRACT}"',
        "#define TUC_C11_ROWS 4U",
        "#define TUC_C11_INNER 8U",
        "#define TUC_C11_COLUMNS 2U",
        "#define TUC_C11_A_COUNT 32U",
        "#define TUC_C11_B_COUNT 16U",
        "#define TUC_C11_OUTPUT_COUNT 8U",
        "",
    ]
    lines.extend(_render_array("TUC_C11_A", a))
    lines.extend(_render_array("TUC_C11_B", b))
    lines.extend(_render_array("TUC_C11_EXPECTED_OUTPUT", output))
    lines.extend(("", "#endif", ""))
    return "\n".join(lines)


def build_c11_compiler_emission_artifacts(
    source_intent: object,
    workload: object,
) -> C11CompilerEmissionArtifacts:
    """Build the fixed C11 plan and sources without side effects."""

    core = _plan_core(source_intent, workload)
    generated_header = _render_generated_header(core)
    generated_source = _render_generated_source(core)
    workload_header = _render_workload_header(
        assert_compiler_emission_workload(workload)
    )
    for label, rendered in (
        ("header", generated_header),
        ("source", generated_source),
        ("workload", workload_header),
    ):
        if len(rendered.encode("utf-8")) > MAX_C11_GENERATED_SOURCE_BYTES:
            raise BoundedCompilerEmissionError(f"compiler-emitted C11 {label} exceeds limit")
    plan = dict(core)
    plan.update(
        {
            "generated_function_count": 2,
            "generated_header_digest": _digest_text(generated_header),
            "generated_source_digest": _digest_text(generated_source),
            "runtime_generated_code": False,
            "workload_header_digest": _digest_text(workload_header),
        }
    )
    plan["plan_digest"] = _digest_payload(plan)
    return C11CompilerEmissionArtifacts(
        generated_header=generated_header,
        generated_source=generated_source,
        plan=assert_c11_compiler_emission_plan(plan, source_intent, workload),
        workload_header=workload_header,
    )


def assert_c11_compiler_emission_plan(
    plan: object,
    source_intent: object,
    workload: object,
) -> dict[str, object]:
    """Fail closed unless the C11 plan equals fresh deterministic emission."""

    if type(plan) is not dict:
        raise BoundedCompilerEmissionError("C11 emission plan rejected")
    typed = cast(dict[str, object], plan)
    digest_source = dict(typed)
    digest = digest_source.pop("plan_digest", None)
    if digest != _digest_payload(digest_source):
        raise BoundedCompilerEmissionError("C11 emission plan digest mismatch")
    core = _plan_core(source_intent, workload)
    generated_header = _render_generated_header(core)
    generated_source = _render_generated_source(core)
    workload_header = _render_workload_header(
        assert_compiler_emission_workload(workload)
    )
    expected = dict(core)
    expected.update(
        {
            "generated_function_count": 2,
            "generated_header_digest": _digest_text(generated_header),
            "generated_source_digest": _digest_text(generated_source),
            "runtime_generated_code": False,
            "workload_header_digest": _digest_text(workload_header),
        }
    )
    expected["plan_digest"] = _digest_payload(expected)
    if typed != expected:
        raise BoundedCompilerEmissionError("C11 emission plan drift")
    return typed


def dump_c11_compiler_emission_plan(
    plan: object,
    source_intent: object,
    workload: object,
) -> str:
    """Render deterministic metadata-only C11 lowering evidence."""

    typed = assert_c11_compiler_emission_plan(plan, source_intent, workload)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > MAX_C11_PLAN_BYTES:
        raise BoundedCompilerEmissionError("C11 emission plan exceeds limit")
    for forbidden in (
        '"command"',
        '"host_path"',
        '"raw_tensor_values"',
        '"source_text"',
    ):
        if forbidden in rendered:
            raise BoundedCompilerEmissionError("C11 emission plan leaks forbidden data")
    return rendered


def validate_checked_in_c11_compiler_emission() -> C11CompilerEmissionArtifacts:
    """Require all checked-in C11 artifacts to match fresh emission exactly."""

    source = _load_json(C11_SOURCE_INTENT_PATH)
    workload = _load_json(C11_WORKLOAD_MANIFEST_PATH)
    if _digest_payload(source) != COMPILER_EMISSION_SOURCE_INTENT_DIGEST:
        raise BoundedCompilerEmissionError("C11 Source Intent digest drift")
    if _digest_payload(workload) != COMPILER_EMISSION_WORKLOAD_DIGEST:
        raise BoundedCompilerEmissionError("C11 workload digest drift")
    artifacts = build_c11_compiler_emission_artifacts(source, workload)
    if _load_json(C11_EMISSION_PLAN_PATH) != artifacts.plan:
        raise BoundedCompilerEmissionError("checked-in C11 emission plan drift")
    checked = (
        (C11_GENERATED_HEADER_PATH, artifacts.generated_header),
        (C11_GENERATED_SOURCE_PATH, artifacts.generated_source),
        (C11_WORKLOAD_HEADER_PATH, artifacts.workload_header),
    )
    if any(
        _read_text(path, MAX_EMITTED_HEADER_BYTES) != expected
        for path, expected in checked
    ):
        raise BoundedCompilerEmissionError("checked-in compiler-emitted C11 source drift")
    return artifacts


def main() -> int:
    try:
        source = _load_json(C11_SOURCE_INTENT_PATH)
        workload = _load_json(C11_WORKLOAD_MANIFEST_PATH)
        artifacts = build_c11_compiler_emission_artifacts(source, workload)
        sys.stdout.write(dump_c11_compiler_emission_plan(artifacts.plan, source, workload))
    except BoundedCompilerEmissionError as exc:
        print(f"bounded compiler-emitted C11 emission rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
