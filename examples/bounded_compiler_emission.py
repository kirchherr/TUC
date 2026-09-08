"""Emit one reviewed CUDA kernel header from one exact Source Intent slice."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

from tuc.frontend import source_intent_from_mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GPU_CONTEXT_PATH = REPOSITORY_ROOT / "docker/gpu-observation"
SOURCE_INTENT_PATH = GPU_CONTEXT_PATH / "compiler_emitted_source_intent.v0.json"
WORKLOAD_MANIFEST_PATH = GPU_CONTEXT_PATH / "compiler_emitted_workload.v0.json"
WORKLOAD_HEADER_PATH = GPU_CONTEXT_PATH / "compiler_emitted_workload.hpp"
EMITTED_KERNEL_PATH = GPU_CONTEXT_PATH / "generated_compiler_emitted_sm86_kernels.cuh"
EMISSION_PLAN_PATH = GPU_CONTEXT_PATH / "compiler_emission_plan.v0.json"

COMPILER_EMISSION_SCHEMA_VERSION = "tuc.bounded_compiler_emission_plan.v0"
COMPILER_EMISSION_CONTRACT = "bounded_cuda_emission.exact_source_intent_sm86.v0"
COMPILER_EMISSION_SOURCE_INTENT_DIGEST = (
    "sha256:79f0fbd3fad9baf3a77df0eea5a1250234c24cdb7d5d6dd703e595816550daaa"
)
COMPILER_EMISSION_WORKLOAD_DIGEST = (
    "sha256:7aec3a02cdfe8fa687b6531d2a37849418bc056989b1cbdc397730b6dfebaadd"
)
COMPILER_EMISSION_WORKLOAD_CONTRACT = "research_triton_matmul_relu_4x8x2_f32.v0"
COMPILER_EMISSION_TARGET_PROFILE = "nvidia-sm86-compiler-emitted"
COMPILER_EMISSION_BLOCKED_CLAIMS = (
    "arbitrary_source_intent",
    "dynamic_shapes",
    "free_form_cuda",
    "general_cuda_backend",
    "runtime_code_generation",
    "source_text_execution",
)

MAX_INPUT_BYTES = 64 * 1024
MAX_PLAN_BYTES = 32 * 1024
MAX_EMITTED_HEADER_BYTES = 16 * 1024
MAX_JSON_DEPTH = 16
MAX_JSON_ITEMS = 512


class BoundedCompilerEmissionError(ValueError):
    """Raised when the fixed Source Intent emission boundary is violated."""


@dataclass(frozen=True)
class CompilerEmissionArtifacts:
    """Deterministic data and source artifacts for the one admitted slice."""

    plan: dict[str, object]
    kernel_header: str
    workload_header: str


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError, RecursionError) as exc:
        raise BoundedCompilerEmissionError("compiler emission JSON rejected") from exc


def _digest_payload(value: object) -> str:
    return f"sha256:{sha256(_canonical_json(value).encode('utf-8')).hexdigest()}"


def _digest_text(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


def _load_json(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise BoundedCompilerEmissionError("compiler emission symbolic link rejected")
    try:
        before = path.stat()
        if not path.is_file() or not 0 < before.st_size <= MAX_INPUT_BYTES:
            raise BoundedCompilerEmissionError("compiler emission input boundary rejected")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise BoundedCompilerEmissionError("compiler emission input unavailable") from exc
    if len(raw) != before.st_size or before.st_size != after.st_size:
        raise BoundedCompilerEmissionError("compiler emission input changed while reading")
    try:
        payload = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_non_finite,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise BoundedCompilerEmissionError("compiler emission JSON rejected") from exc
    if type(payload) is not dict:
        raise BoundedCompilerEmissionError("compiler emission input must be an object")
    _assert_plain_json(payload)
    return cast(dict[str, object], payload)


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BoundedCompilerEmissionError("compiler emission duplicate key rejected")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    del value
    raise BoundedCompilerEmissionError("compiler emission non-finite value rejected")


def _assert_plain_json(value: object) -> None:
    remaining = MAX_JSON_ITEMS

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > MAX_JSON_DEPTH:
            raise BoundedCompilerEmissionError("compiler emission structure exceeds limit")
        if item is None or type(item) in (bool, int, float, str):
            if type(item) is float and not math.isfinite(cast(float, item)):
                raise BoundedCompilerEmissionError("compiler emission non-finite value rejected")
            return
        if type(item) is list:
            for child in cast(list[object], item):
                visit(child, depth + 1)
            return
        if type(item) is dict:
            for key, child in cast(dict[object, object], item).items():
                if type(key) is not str:
                    raise BoundedCompilerEmissionError("compiler emission key rejected")
                visit(child, depth + 1)
            return
        raise BoundedCompilerEmissionError("compiler emission value type rejected")

    visit(value, 0)


def assert_compiler_emission_source_intent(value: object) -> dict[str, object]:
    """Accept only the reviewed parser output with explicit ReLU semantics."""

    if type(value) is not dict:
        raise BoundedCompilerEmissionError("compiler emission Source Intent rejected")
    typed = cast(dict[str, object], value)
    _assert_plain_json(typed)
    if _digest_payload(typed) != COMPILER_EMISSION_SOURCE_INTENT_DIGEST:
        raise BoundedCompilerEmissionError("compiler emission Source Intent digest drift")
    try:
        module = source_intent_from_mapping(typed)
    except (TypeError, ValueError) as exc:
        raise BoundedCompilerEmissionError("compiler emission Source Intent invalid") from exc
    if (
        module.name != "research_matmul_elementwise"
        or tuple(operation.family for operation in module.operations)
        != ("matmul", "elementwise")
        or module.operations[1].attributes.get("elementwise_kind") != "relu"
    ):
        raise BoundedCompilerEmissionError("compiler emission Source Intent semantics drift")
    return typed


def _matrix(value: object, rows: int, columns: int) -> list[list[float]]:
    if type(value) is not list or len(value) != rows:
        raise BoundedCompilerEmissionError("compiler emission workload shape drift")
    result: list[list[float]] = []
    for row in cast(list[object], value):
        if type(row) is not list or len(row) != columns:
            raise BoundedCompilerEmissionError("compiler emission workload shape drift")
        converted: list[float] = []
        for item in cast(list[object], row):
            if type(item) not in (int, float) or not math.isfinite(float(item)):
                raise BoundedCompilerEmissionError("compiler emission workload value rejected")
            converted.append(float(item))
        result.append(converted)
    return result


def assert_compiler_emission_workload(value: object) -> dict[str, object]:
    """Accept only the fixed public 4x8x2 FP32 ReLU conformance vector."""

    if type(value) is not dict:
        raise BoundedCompilerEmissionError("compiler emission workload rejected")
    typed = cast(dict[str, object], value)
    _assert_plain_json(typed)
    if _digest_payload(typed) != COMPILER_EMISSION_WORKLOAD_DIGEST:
        raise BoundedCompilerEmissionError("compiler emission workload digest drift")
    inputs = typed.get("inputs")
    if type(inputs) is not dict:
        raise BoundedCompilerEmissionError("compiler emission workload inputs rejected")
    input_map = cast(dict[str, object], inputs)
    a = _matrix(input_map.get("a"), 4, 8)
    b = _matrix(input_map.get("b"), 8, 2)
    expected = _matrix(typed.get("expected_output"), 4, 2)
    observed = [
        [
            max(
                0.0,
                sum(a[row][inner] * b[inner][column] for inner in range(8)),
            )
            for column in range(2)
        ]
        for row in range(4)
    ]
    if observed != expected:
        raise BoundedCompilerEmissionError("compiler emission workload reference mismatch")
    return typed


def _plan_core(source_intent: object, workload: object) -> dict[str, object]:
    source = assert_compiler_emission_source_intent(source_intent)
    vector = assert_compiler_emission_workload(workload)
    return {
        "blocked_claims": list(COMPILER_EMISSION_BLOCKED_CLAIMS),
        "code_generation_phase": "trusted_review_time_before_container_build",
        "emission_contract": COMPILER_EMISSION_CONTRACT,
        "identifier_policy": "fixed_symbols_no_source_identifier_interpolation",
        "operations": [
            {
                "family": "matmul",
                "input_shapes": [[4, 8], [8, 2]],
                "kernel_symbol": "tuc_projection_matmul_4x8x2_f32",
                "launch": {"blocks": 1, "threads_per_block": 32},
                "operation": "projection",
                "output_shape": [4, 2],
            },
            {
                "attributes": {"elementwise_kind": "relu"},
                "family": "elementwise",
                "input_shapes": [[4, 2]],
                "kernel_symbol": "tuc_activated_relu_4x2_f32",
                "launch": {"blocks": 1, "threads_per_block": 32},
                "operation": "activated",
                "output_shape": [4, 2],
            },
        ],
        "schema_version": COMPILER_EMISSION_SCHEMA_VERSION,
        "source_intent_digest": _digest_payload(source),
        "source_intent_schema_version": source["schema_version"],
        "target": {
            "accelerator_class": "nvidia_cuda_sm86",
            "compute_target": "compute_86",
            "ptx_emission": False,
            "sass_target": "sm_86",
            "target_profile": COMPILER_EMISSION_TARGET_PROFILE,
        },
        "workload_contract": vector["workload_contract"],
        "workload_digest": _digest_payload(vector),
    }


def _render_kernel_header_from_core(core: dict[str, object]) -> str:
    operations = cast(list[dict[str, object]], core["operations"])
    if [item["family"] for item in operations] != ["matmul", "elementwise"]:
        raise BoundedCompilerEmissionError("compiler emission operation sequence rejected")
    if cast(dict[str, object], operations[1])["attributes"] != {
        "elementwise_kind": "relu"
    }:
        raise BoundedCompilerEmissionError("compiler emission elementwise semantics rejected")
    return """#pragma once

#include <cuda_runtime.h>

namespace tuc::compiler_emitted_gpu {

inline constexpr int kThreadsPerBlock = 32;

__global__ void tuc_projection_matmul_4x8x2_f32(const float* a, const float* b,
                                                float* projection) {
  const int index = static_cast<int>(threadIdx.x);
  if (index >= static_cast<int>(kOutputElementCount)) {
    return;
  }
  const int row = index / static_cast<int>(kColumns);
  const int column = index % static_cast<int>(kColumns);
  float value = 0.0F;
  for (int inner = 0; inner < static_cast<int>(kInner); ++inner) {
    value += a[row * static_cast<int>(kInner) + inner] *
             b[inner * static_cast<int>(kColumns) + column];
  }
  projection[index] = value;
}

__global__ void tuc_activated_relu_4x2_f32(const float* projection,
                                            float* activated) {
  const int index = static_cast<int>(threadIdx.x);
  if (index >= static_cast<int>(kOutputElementCount)) {
    return;
  }
  const float value = projection[index];
  activated[index] = value > 0.0F ? value : 0.0F;
}

}  // namespace tuc::compiler_emitted_gpu
"""


def _float_literal(value: float) -> str:
    rendered = repr(float(value))
    if rendered == "-0.0":
        rendered = "0.0"
    return f"{rendered}F"


def _render_array(name: str, values: list[float]) -> list[str]:
    lines = [f"inline constexpr std::array<float, {len(values)}> {name} = {{"]
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
        "#pragma once",
        "",
        "#include <array>",
        "#include <cstddef>",
        "",
        "namespace tuc::compiler_emitted_gpu {",
        "",
        "inline constexpr char kWorkloadContract[] =",
        f'    "{COMPILER_EMISSION_WORKLOAD_CONTRACT}";',
        "inline constexpr std::size_t kRows = 4;",
        "inline constexpr std::size_t kInner = 8;",
        "inline constexpr std::size_t kColumns = 2;",
        "inline constexpr std::size_t kAElementCount = kRows * kInner;",
        "inline constexpr std::size_t kBElementCount = kInner * kColumns;",
        "inline constexpr std::size_t kOutputElementCount = kRows * kColumns;",
    ]
    lines.extend(_render_array("kA", a))
    lines.extend(_render_array("kB", b))
    lines.extend(_render_array("kExpectedOutput", output))
    lines.extend(("", "}  // namespace tuc::compiler_emitted_gpu", ""))
    return "\n".join(lines)


def build_compiler_emission_artifacts(
    source_intent: object,
    workload: object,
) -> CompilerEmissionArtifacts:
    """Build the exact lowering plan and generated headers without side effects."""

    core = _plan_core(source_intent, workload)
    kernel_header = _render_kernel_header_from_core(core)
    workload_typed = assert_compiler_emission_workload(workload)
    workload_header = _render_workload_header(workload_typed)
    if len(kernel_header.encode("utf-8")) > MAX_EMITTED_HEADER_BYTES:
        raise BoundedCompilerEmissionError("compiler-emitted kernel exceeds limit")
    plan = dict(core)
    plan["emitted_kernel_digest"] = _digest_text(kernel_header)
    plan["generated_kernel_count"] = 2
    plan["runtime_generated_code"] = False
    plan["workload_header_digest"] = _digest_text(workload_header)
    plan["plan_digest"] = _digest_payload(plan)
    return CompilerEmissionArtifacts(
        plan=assert_compiler_emission_plan(plan, source_intent, workload),
        kernel_header=kernel_header,
        workload_header=workload_header,
    )


def assert_compiler_emission_plan(
    plan: object,
    source_intent: object,
    workload: object,
) -> dict[str, object]:
    """Fail closed unless the plan exactly matches fresh deterministic emission."""

    if type(plan) is not dict:
        raise BoundedCompilerEmissionError("compiler emission plan rejected")
    typed = cast(dict[str, object], plan)
    _assert_plain_json(typed)
    digest = typed.get("plan_digest")
    digest_source = dict(typed)
    digest_source.pop("plan_digest", None)
    if digest != _digest_payload(digest_source):
        raise BoundedCompilerEmissionError("compiler emission plan digest mismatch")
    core = _plan_core(source_intent, workload)
    kernel_header = _render_kernel_header_from_core(core)
    workload_header = _render_workload_header(
        assert_compiler_emission_workload(workload)
    )
    expected = dict(core)
    expected["emitted_kernel_digest"] = _digest_text(kernel_header)
    expected["generated_kernel_count"] = 2
    expected["runtime_generated_code"] = False
    expected["workload_header_digest"] = _digest_text(workload_header)
    expected["plan_digest"] = _digest_payload(expected)
    if typed != expected:
        raise BoundedCompilerEmissionError("compiler emission plan drift")
    return typed


def dump_compiler_emission_plan(
    plan: object,
    source_intent: object,
    workload: object,
) -> str:
    """Return deterministic metadata-only lowering evidence."""

    typed = assert_compiler_emission_plan(plan, source_intent, workload)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > MAX_PLAN_BYTES:
        raise BoundedCompilerEmissionError("compiler emission plan exceeds limit")
    for forbidden in ('"source_text"', '"command"', '"host_path"', '"raw_tensor_values"'):
        if forbidden in rendered:
            raise BoundedCompilerEmissionError("compiler emission plan leaks forbidden data")
    return rendered


def _read_text(path: Path, maximum_bytes: int) -> str:
    if path.is_symlink():
        raise BoundedCompilerEmissionError("compiler emission symbolic link rejected")
    try:
        before = path.stat()
        if not path.is_file() or not 0 < before.st_size <= maximum_bytes:
            raise BoundedCompilerEmissionError("compiler emission artifact boundary rejected")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise BoundedCompilerEmissionError("compiler emission artifact unavailable") from exc
    if len(raw) != before.st_size or before.st_size != after.st_size:
        raise BoundedCompilerEmissionError("compiler emission artifact changed while reading")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise BoundedCompilerEmissionError("compiler emission artifact encoding rejected") from exc


def validate_checked_in_compiler_emission() -> CompilerEmissionArtifacts:
    """Require checked-in artifacts to equal a fresh emission byte for byte."""

    source = _load_json(SOURCE_INTENT_PATH)
    workload = _load_json(WORKLOAD_MANIFEST_PATH)
    artifacts = build_compiler_emission_artifacts(source, workload)
    checked_plan = _load_json(EMISSION_PLAN_PATH)
    if checked_plan != artifacts.plan:
        raise BoundedCompilerEmissionError("checked-in compiler emission plan drift")
    kernel_header = _read_text(EMITTED_KERNEL_PATH, MAX_EMITTED_HEADER_BYTES)
    workload_header = _read_text(WORKLOAD_HEADER_PATH, MAX_EMITTED_HEADER_BYTES)
    if kernel_header != artifacts.kernel_header or workload_header != artifacts.workload_header:
        raise BoundedCompilerEmissionError("checked-in compiler-emitted source drift")
    return artifacts


def main() -> int:
    try:
        source = _load_json(SOURCE_INTENT_PATH)
        workload = _load_json(WORKLOAD_MANIFEST_PATH)
        artifacts = build_compiler_emission_artifacts(source, workload)
        sys.stdout.write(dump_compiler_emission_plan(artifacts.plan, source, workload))
    except BoundedCompilerEmissionError as exc:
        print(f"bounded compiler emission rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
