"""Execution-free source-ingestion sandbox boundary.

The sandbox wraps the bounded source-buffer API and emits source-free evidence
records only. It does not admit direct source ingestion, produce Source Intent,
construct graphs, lower IR, import packages, evaluate decorators, execute JIT
code, access devices, or serialize raw source text.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.bounded_source_buffer import (
    BOUNDED_SOURCE_BUFFER_API_CONTRACT,
    BOUNDED_SOURCE_BUFFER_API_STATUS,
    BoundedSourceBufferError,
    bound_source_buffer,
    bounded_source_buffer_record_to_dict,
)

SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT = (
    "source_ingestion_sandbox_implementation.execution_free.v0"
)
SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS = "implemented_non_admitting"
SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY = "bounded_source_buffer_record_only"
SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY = "omitted_by_policy"
SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY = "source_free_reason_codes_only"
SOURCE_INGESTION_SANDBOX_ACCEPTED_OUTCOME = "accepted_metadata_only"
SOURCE_INGESTION_SANDBOX_REJECTED_OUTCOME = "rejected"
SOURCE_INGESTION_SANDBOX_ACCEPTED_REASON = "accepted_metadata_only"
SOURCE_INGESTION_SANDBOX_REJECTION_REASONS = (
    "empty_source",
    "byte_budget",
    "line_budget",
    "syntax_error",
    "shape_profile",
    "report_safe",
    "type_error",
    "other_rejected",
)
SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS = (
    "backend_artifact",
    "compute_graph",
    "generated_artifact",
    "hac_ir",
    "hs_ir",
    "python_function_object",
    "runtime_plan",
    "source_intent_plain_data",
    "tlir",
)
SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES = (
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "frontend_package_import",
    "generated_artifact_execution",
    "native_backend_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "subprocess_execution",
    "triton_jit_execution",
)
SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS = (
    "bounded_source_buffer_api",
    "decode_only_before_validation",
    "fail_closed_before_lowering",
    "source_free_diagnostics",
    "source_digest_only",
    "no_python_import",
    "no_triton_jit",
    "no_decorator_evaluation",
    "no_device_access",
    "no_generated_artifacts",
    "no_native_backend_execution",
    "no_source_to_intent_output",
    "no_source_to_compute_graph",
    "no_source_to_hac_ir",
    "no_source_to_runtime_plan",
)
MAX_SOURCE_INGESTION_SANDBOX_RESULT_BYTES = 16 * 1024

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact_path",
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


class SourceIngestionSandboxError(ValueError):
    """Raised when source-ingestion sandbox evidence drifts."""


@dataclass(frozen=True)
class SourceIngestionSandboxResult:
    """Source-free result for one source-ingestion sandbox attempt."""

    source_name: str
    source_digest: str
    outcome: str
    reason_code: str
    record: Mapping[str, object] | None = None
    sandbox_contract: str = SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT
    sandbox_status: str = SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS
    admission_effect: str = SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT
    output_policy: str = SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY
    raw_source_policy: str = SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY
    diagnostic_policy: str = SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY
    blocked_outputs: tuple[str, ...] = SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_report_text(self.source_name, "source_name")
        _validate_digest(self.source_digest, "source_digest")
        if self.sandbox_contract != SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT:
            raise SourceIngestionSandboxError("source sandbox contract drift")
        if self.sandbox_status != SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS:
            raise SourceIngestionSandboxError("source sandbox status drift")
        if self.admission_effect != SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT:
            raise SourceIngestionSandboxError("source sandbox admission effect drift")
        if self.output_policy != SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY:
            raise SourceIngestionSandboxError("source sandbox output policy drift")
        if self.raw_source_policy != SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY:
            raise SourceIngestionSandboxError("source sandbox raw source policy drift")
        if self.diagnostic_policy != SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY:
            raise SourceIngestionSandboxError("source sandbox diagnostic policy drift")
        _validate_exact_tuple(
            self.blocked_outputs,
            SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        if self.outcome == SOURCE_INGESTION_SANDBOX_ACCEPTED_OUTCOME:
            if self.reason_code != SOURCE_INGESTION_SANDBOX_ACCEPTED_REASON:
                raise SourceIngestionSandboxError("source sandbox accepted reason drift")
            if self.record is None:
                raise SourceIngestionSandboxError("source sandbox accepted record missing")
            _assert_bounded_source_record(self.record)
            return
        if self.outcome != SOURCE_INGESTION_SANDBOX_REJECTED_OUTCOME:
            raise SourceIngestionSandboxError("source sandbox outcome drift")
        if self.reason_code not in SOURCE_INGESTION_SANDBOX_REJECTION_REASONS:
            raise SourceIngestionSandboxError("source sandbox rejection reason drift")
        if self.record is not None:
            raise SourceIngestionSandboxError("source sandbox rejection record drift")


def run_source_ingestion_sandbox(
    source: str,
    *,
    source_name: str,
    declared_shape_profile: Mapping[str, Sequence[int]],
) -> SourceIngestionSandboxResult:
    """Validate source through the sandbox and return source-free metadata only."""

    safe_source_name = _safe_source_name(source_name)
    source_digest = _source_digest(source)
    try:
        record = bound_source_buffer(
            source,
            source_name=source_name,
            declared_shape_profile=declared_shape_profile,
        )
    except (BoundedSourceBufferError, TypeError) as exc:
        return SourceIngestionSandboxResult(
            source_name=safe_source_name,
            source_digest=source_digest,
            outcome=SOURCE_INGESTION_SANDBOX_REJECTED_OUTCOME,
            reason_code=_reason_code_from_exception(exc),
        )
    payload = bounded_source_buffer_record_to_dict(record)
    return SourceIngestionSandboxResult(
        source_name=safe_source_name,
        source_digest=str(payload["source_digest"]),
        outcome=SOURCE_INGESTION_SANDBOX_ACCEPTED_OUTCOME,
        reason_code=SOURCE_INGESTION_SANDBOX_ACCEPTED_REASON,
        record=payload,
    )


def source_ingestion_sandbox_result_to_dict(
    result: SourceIngestionSandboxResult,
) -> dict[str, object]:
    """Return a JSON-compatible source-free sandbox result."""

    if not isinstance(result, SourceIngestionSandboxResult):
        raise TypeError("source-ingestion sandbox result must be result")
    base: dict[str, object] = {
        "admission_effect": result.admission_effect,
        "blocked_execution_surfaces": list(result.blocked_execution_surfaces),
        "blocked_outputs": list(result.blocked_outputs),
        "diagnostic_policy": result.diagnostic_policy,
        "direct_source_ingestion": False,
        "outcome": result.outcome,
        "output_policy": result.output_policy,
        "raw_source_policy": result.raw_source_policy,
        "reason_code": result.reason_code,
        "sandbox_contract": result.sandbox_contract,
        "sandbox_status": result.sandbox_status,
        "source_digest": result.source_digest,
        "source_name": result.source_name,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
    }
    if result.record is None:
        base["source_free"] = True
        _assert_result_size(base)
        return base
    record = dict(result.record)
    base.update(
        {
            "ast_depth": record["ast_depth"],
            "ast_node_count": record["ast_node_count"],
            "bounded_source_buffer_api_contract": BOUNDED_SOURCE_BUFFER_API_CONTRACT,
            "bounded_source_buffer_api_status": BOUNDED_SOURCE_BUFFER_API_STATUS,
            "bounded_source_buffer_record_digest": _digest_payload(record),
            "line_count": record["line_count"],
            "shape_profile_digest": record["shape_profile_digest"],
            "shape_profile_entry_count": record["shape_profile_entry_count"],
            "shape_profile_max_rank": record["shape_profile_max_rank"],
            "source_bytes": record["source_bytes"],
        }
    )
    _assert_result_size(base)
    return base


def _assert_bounded_source_record(record: Mapping[str, object]) -> None:
    if record.get("api_contract") != BOUNDED_SOURCE_BUFFER_API_CONTRACT:
        raise SourceIngestionSandboxError("source sandbox bounded API contract drift")
    if record.get("api_status") != BOUNDED_SOURCE_BUFFER_API_STATUS:
        raise SourceIngestionSandboxError("source sandbox bounded API status drift")
    if record.get("source_digest") is None:
        raise SourceIngestionSandboxError("source sandbox source digest missing")
    _validate_digest(str(record["source_digest"]), "record source_digest")
    _assert_text_is_source_free(_canonical_json(record))


def _reason_code_from_exception(exc: BaseException) -> str:
    message = str(exc).lower()
    if "must not be empty" in message:
        return "empty_source"
    if "byte budget" in message:
        return "byte_budget"
    if "line budget" in message:
        return "line_budget"
    if "syntax" in message:
        return "syntax_error"
    if "shape" in message or "dimension" in message or "rank" in message:
        return "shape_profile"
    if "report-safe" in message or "identifier" in message:
        return "report_safe"
    if isinstance(exc, TypeError):
        return "type_error"
    return "other_rejected"


def _safe_source_name(value: object) -> str:
    if (
        isinstance(value, str)
        and _REPORT_TEXT_RE.fullmatch(value)
        and value not in _FORBIDDEN_REPORT_TEXT
    ):
        return value
    return "rejected_source_name"


def _source_digest(source: object) -> str:
    if isinstance(source, str):
        return _digest_text(source)
    return _digest_text("non_text_source_input")


def _assert_result_size(payload: Mapping[str, object]) -> None:
    text = _canonical_json(payload)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_SOURCE_INGESTION_SANDBOX_RESULT_BYTES:
        raise SourceIngestionSandboxError("source sandbox result exceeds byte limit")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceIngestionSandboxError(f"source sandbox {label} must be report-safe")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceIngestionSandboxError(f"source sandbox {label} must be report-safe")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceIngestionSandboxError(f"source sandbox {label} must be sha256")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"source sandbox {label} must be tuple")
    if values != expected:
        raise SourceIngestionSandboxError(f"source sandbox {label} drift")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    text = _canonical_json(payload)
    _assert_text_is_source_free(text)
    return _digest_text(text)


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in (
        "@triton.jit",
        "import triton",
        "tl.dot",
        '"backend_artifact_path":',
        '"command_line":',
        '"device_id":',
        '"file_path":',
        '"generated_code":',
        '"host_path":',
        '"plugin_entrypoint":',
        '"python_source":',
        '"raw_source":',
        '"raw_source_text":',
        '"raw_tensor_value":',
        '"runtime_handle":',
        '"source_intent_payload":',
        '"source_text":',
    ):
        if fragment in lowered:
            raise SourceIngestionSandboxError(
                f"source sandbox contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_SOURCE_INGESTION_SANDBOX_RESULT_BYTES",
    "SOURCE_INGESTION_SANDBOX_ACCEPTED_OUTCOME",
    "SOURCE_INGESTION_SANDBOX_ACCEPTED_REASON",
    "SOURCE_INGESTION_SANDBOX_ADMISSION_EFFECT",
    "SOURCE_INGESTION_SANDBOX_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_INGESTION_SANDBOX_BLOCKED_OUTPUTS",
    "SOURCE_INGESTION_SANDBOX_DIAGNOSTIC_POLICY",
    "SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT",
    "SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS",
    "SOURCE_INGESTION_SANDBOX_OUTPUT_POLICY",
    "SOURCE_INGESTION_SANDBOX_RAW_SOURCE_POLICY",
    "SOURCE_INGESTION_SANDBOX_REJECTED_OUTCOME",
    "SOURCE_INGESTION_SANDBOX_REJECTION_REASONS",
    "SOURCE_INGESTION_SANDBOX_REQUIRED_CONTROLS",
    "SourceIngestionSandboxError",
    "SourceIngestionSandboxResult",
    "run_source_ingestion_sandbox",
    "source_ingestion_sandbox_result_to_dict",
]
