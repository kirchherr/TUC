"""Bounded source-buffer admission API.

This module validates caller-provided source text as untrusted data and emits a
metadata-only record. It does not parse source into Source Intent, construct
graphs, lower IR, import modules, evaluate decorators, execute JIT code, or
serialize raw source text.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent import (
    MAX_SOURCE_INTENT_DIMENSION,
    MAX_SOURCE_INTENT_RANK,
)
from tuc.frontend.triton_source import (
    MAX_TRITON_SOURCE_AST_DEPTH,
    MAX_TRITON_SOURCE_AST_NODES,
    MAX_TRITON_SOURCE_BYTES,
    MAX_TRITON_SOURCE_LINES,
)

BOUNDED_SOURCE_BUFFER_API_CONTRACT = "bounded_source_buffer_api.execution_free.v0"
BOUNDED_SOURCE_BUFFER_API_STATUS = "implemented_non_admitting"
BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY = "metadata_record_only"
BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY = "omitted_by_policy"
BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY = "source_free_reason_codes_only"
BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT = "does_not_admit_direct_source_ingestion"
BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS = (
    "compute_graph",
    "generated_artifact",
    "hac_ir",
    "hs_ir",
    "python_function_object",
    "runtime_plan",
    "source_intent_plain_data",
    "tlir",
)
BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES = (
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "frontend_package_import",
    "generated_artifact_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "subprocess_execution",
    "triton_jit_execution",
)
MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES = 64
MAX_BOUNDED_SOURCE_BUFFER_RECORD_BYTES = 32 * 1024

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
        "environment",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
        "url",
    }
)


class BoundedSourceBufferError(ValueError):
    """Raised when source-buffer admission fails closed."""


@dataclass(frozen=True)
class BoundedSourceBufferRecord:
    """Metadata-only record for one bounded source buffer."""

    source_name: str
    source_digest: str
    source_bytes: int
    line_count: int
    ast_node_count: int
    ast_depth: int
    shape_profile_digest: str
    shape_profile_entry_count: int
    shape_profile_max_rank: int
    api_contract: str = BOUNDED_SOURCE_BUFFER_API_CONTRACT
    api_status: str = BOUNDED_SOURCE_BUFFER_API_STATUS
    output_policy: str = BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY
    raw_source_policy: str = BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY
    diagnostic_policy: str = BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY
    admission_effect: str = BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT
    blocked_outputs: tuple[str, ...] = BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS
    blocked_execution_surfaces: tuple[str, ...] = (
        BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_report_text(self.source_name, "source_name")
        _validate_digest(self.source_digest, "source_digest")
        _validate_digest(self.shape_profile_digest, "shape_profile_digest")
        for label, value in (
            ("source_bytes", self.source_bytes),
            ("line_count", self.line_count),
            ("ast_node_count", self.ast_node_count),
            ("ast_depth", self.ast_depth),
            ("shape_profile_entry_count", self.shape_profile_entry_count),
            ("shape_profile_max_rank", self.shape_profile_max_rank),
        ):
            _validate_positive_int(value, label)
        if self.source_bytes > MAX_TRITON_SOURCE_BYTES:
            raise BoundedSourceBufferError("bounded source byte budget drift")
        if self.line_count > MAX_TRITON_SOURCE_LINES:
            raise BoundedSourceBufferError("bounded source line budget drift")
        if self.ast_node_count > MAX_TRITON_SOURCE_AST_NODES:
            raise BoundedSourceBufferError("bounded source AST node budget drift")
        if self.ast_depth > MAX_TRITON_SOURCE_AST_DEPTH:
            raise BoundedSourceBufferError("bounded source AST depth budget drift")
        if self.shape_profile_entry_count > MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES:
            raise BoundedSourceBufferError("bounded shape profile entry budget drift")
        if self.shape_profile_max_rank > MAX_SOURCE_INTENT_RANK:
            raise BoundedSourceBufferError("bounded shape profile rank budget drift")
        if self.api_contract != BOUNDED_SOURCE_BUFFER_API_CONTRACT:
            raise BoundedSourceBufferError("bounded source API contract drift")
        if self.api_status != BOUNDED_SOURCE_BUFFER_API_STATUS:
            raise BoundedSourceBufferError("bounded source API status drift")
        if self.output_policy != BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY:
            raise BoundedSourceBufferError("bounded source output policy drift")
        if self.raw_source_policy != BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY:
            raise BoundedSourceBufferError("bounded source raw policy drift")
        if self.diagnostic_policy != BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY:
            raise BoundedSourceBufferError("bounded source diagnostic policy drift")
        if self.admission_effect != BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT:
            raise BoundedSourceBufferError("bounded source admission effect drift")
        _validate_exact_tuple(
            self.blocked_outputs,
            BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )


def bound_source_buffer(
    source: str,
    *,
    source_name: str,
    declared_shape_profile: Mapping[str, Sequence[int]],
) -> BoundedSourceBufferRecord:
    """Validate source text as bounded data and return metadata only."""

    if not isinstance(source, str):
        raise TypeError("bounded source buffer input must be source text")
    _validate_report_text(source_name, "source_name")
    shape_profile = _shape_profile_from_mapping(declared_shape_profile)
    source_bytes = _source_bytes(source)
    line_count = len(source.splitlines())
    if source_bytes == 0:
        raise BoundedSourceBufferError("source buffer must not be empty")
    if source_bytes > MAX_TRITON_SOURCE_BYTES:
        raise BoundedSourceBufferError("source buffer byte budget exceeded")
    if line_count > MAX_TRITON_SOURCE_LINES:
        raise BoundedSourceBufferError("source buffer line budget exceeded")
    tree = _parse_source(source)
    ast_node_count, ast_depth = _measure_ast(tree)
    shape_profile_digest = _digest(_canonical_json(shape_profile))
    return BoundedSourceBufferRecord(
        source_name=source_name,
        source_digest=_digest(source),
        source_bytes=source_bytes,
        line_count=line_count,
        ast_node_count=ast_node_count,
        ast_depth=ast_depth,
        shape_profile_digest=shape_profile_digest,
        shape_profile_entry_count=len(shape_profile),
        shape_profile_max_rank=max(len(shape) for shape in shape_profile.values()),
    )


def bounded_source_buffer_record_to_dict(
    record: BoundedSourceBufferRecord,
) -> dict[str, object]:
    """Return a JSON-compatible metadata-only source-buffer record."""

    if not isinstance(record, BoundedSourceBufferRecord):
        raise TypeError("bounded source buffer record must be record")
    payload: dict[str, object] = {
        "admission_effect": record.admission_effect,
        "api_contract": record.api_contract,
        "api_status": record.api_status,
        "ast_depth": record.ast_depth,
        "ast_node_count": record.ast_node_count,
        "blocked_execution_surfaces": list(record.blocked_execution_surfaces),
        "blocked_outputs": list(record.blocked_outputs),
        "diagnostic_policy": record.diagnostic_policy,
        "line_count": record.line_count,
        "output_policy": record.output_policy,
        "raw_source_policy": record.raw_source_policy,
        "shape_profile_digest": record.shape_profile_digest,
        "shape_profile_entry_count": record.shape_profile_entry_count,
        "shape_profile_max_rank": record.shape_profile_max_rank,
        "source_bytes": record.source_bytes,
        "source_digest": record.source_digest,
        "source_name": record.source_name,
    }
    text = _canonical_json(payload)
    if len(text.encode("utf-8")) > MAX_BOUNDED_SOURCE_BUFFER_RECORD_BYTES:
        raise BoundedSourceBufferError("bounded source record exceeds byte limit")
    return payload


def _shape_profile_from_mapping(
    declared_shape_profile: Mapping[str, Sequence[int]],
) -> dict[str, list[int]]:
    if not isinstance(declared_shape_profile, Mapping):
        raise TypeError("declared shape profile must be a mapping")
    if not declared_shape_profile:
        raise BoundedSourceBufferError("declared shape profile must not be empty")
    if len(declared_shape_profile) > MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES:
        raise BoundedSourceBufferError("declared shape profile entry budget exceeded")
    profile: dict[str, list[int]] = {}
    for name, shape in declared_shape_profile.items():
        _validate_identifier(name, "shape profile tensor name")
        if name in profile:
            raise BoundedSourceBufferError("declared shape profile names must be unique")
        profile[name] = list(_shape_from_sequence(shape))
    return dict(sorted(profile.items()))


def _shape_from_sequence(shape: Sequence[int]) -> tuple[int, ...]:
    if isinstance(shape, str | bytes):
        raise TypeError("declared shape must be a sequence of integers")
    dimensions = tuple(shape)
    if not dimensions:
        raise BoundedSourceBufferError("declared shape must not be empty")
    if len(dimensions) > MAX_SOURCE_INTENT_RANK:
        raise BoundedSourceBufferError("declared shape rank exceeds limit")
    for dimension in dimensions:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_SOURCE_INTENT_DIMENSION
        ):
            raise BoundedSourceBufferError(
                "declared shape dimensions must be positive bounded integers"
            )
    return dimensions


def _parse_source(source: str) -> ast.Module:
    try:
        parsed = ast.parse(source, filename="<tuc-bounded-source-buffer>", mode="exec")
    except SyntaxError as exc:
        raise BoundedSourceBufferError("source buffer syntax is invalid") from exc
    except RecursionError as exc:
        raise BoundedSourceBufferError("source buffer parser recursion exceeded") from exc
    if not isinstance(parsed, ast.Module):
        raise BoundedSourceBufferError("source buffer parser returned non-module AST")
    return parsed


def _measure_ast(tree: ast.AST) -> tuple[int, int]:
    node_count = 0
    max_depth = 0
    stack: list[tuple[ast.AST, int]] = [(tree, 1)]
    while stack:
        node, depth = stack.pop()
        node_count += 1
        max_depth = max(max_depth, depth)
        if node_count > MAX_TRITON_SOURCE_AST_NODES:
            raise BoundedSourceBufferError("source buffer AST node budget exceeded")
        if max_depth > MAX_TRITON_SOURCE_AST_DEPTH:
            raise BoundedSourceBufferError("source buffer AST depth budget exceeded")
        for child in ast.iter_child_nodes(node):
            stack.append((child, depth + 1))
    return node_count, max_depth


def _source_bytes(source: str) -> int:
    try:
        return len(source.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise BoundedSourceBufferError("source buffer must be valid UTF-8 text") from exc


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise BoundedSourceBufferError(f"bounded source {label} must be identifier")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise BoundedSourceBufferError(f"bounded source {label} must be report-safe")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise BoundedSourceBufferError(f"bounded source {label} must be report-safe")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise BoundedSourceBufferError(f"bounded source {label} must be sha256")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise BoundedSourceBufferError(f"bounded source {label} must be positive integer")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"bounded source {label} must be tuple")
    if values != expected:
        raise BoundedSourceBufferError(f"bounded source {label} drift")
    for value in values:
        _validate_report_text(value, label)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "BOUNDED_SOURCE_BUFFER_ADMISSION_EFFECT",
    "BOUNDED_SOURCE_BUFFER_API_CONTRACT",
    "BOUNDED_SOURCE_BUFFER_API_STATUS",
    "BOUNDED_SOURCE_BUFFER_BLOCKED_EXECUTION_SURFACES",
    "BOUNDED_SOURCE_BUFFER_BLOCKED_OUTPUTS",
    "BOUNDED_SOURCE_BUFFER_DIAGNOSTIC_POLICY",
    "BOUNDED_SOURCE_BUFFER_OUTPUT_POLICY",
    "BOUNDED_SOURCE_BUFFER_RAW_SOURCE_POLICY",
    "BoundedSourceBufferError",
    "BoundedSourceBufferRecord",
    "MAX_BOUNDED_SOURCE_BUFFER_RECORD_BYTES",
    "MAX_BOUNDED_SOURCE_BUFFER_SHAPE_PROFILE_ENTRIES",
    "bound_source_buffer",
    "bounded_source_buffer_record_to_dict",
]
