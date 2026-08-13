"""Approval criteria for the first direct source-ingestion slice.

This module defines review criteria only. It does not approve source ingestion
and does not admit source text into compiler artifacts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT = (
    "source_ingestion_approval_criteria.data_only.v0"
)
SOURCE_INGESTION_APPROVAL_CRITERIA_ID = "source_ingestion_approval_criteria"
SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS = "criteria_defined_not_approved"
SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS = "not_approved"
SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE = "direct_source_ingestion"
SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
SOURCE_INGESTION_APPROVAL_CRITERIA_ARTIFACT_POLICY = "criteria_only_source_free"
SOURCE_INGESTION_APPROVAL_CRITERIA_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)
SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA = (
    "bounded_source_buffer_reviewed",
    "sandbox_boundary_reviewed",
    "negative_corpus_reviewed",
    "source_free_diagnostics_reviewed",
    "plain_data_golden_reviewed",
    "ci_replay_reviewed",
    "first_slice_plan_reviewed",
    "no_raw_source_serialization",
    "no_source_intent_payload_serialization",
    "no_runtime_handle_serialization",
    "no_host_path_serialization",
    "no_command_serialization",
    "no_compute_graph_output",
    "no_hac_ir_output",
    "no_runtime_plan_output",
    "direct_source_ingestion_remains_blocked",
    "maintainer_approval_required",
)
SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS = (
    "parser_approval",
    "source_execution",
    "source_to_compute_graph",
    "source_to_hac_ir",
    "source_to_runtime_plan",
    "native_backend_execution",
    "production_compiler_claim",
)
SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES = (
    "frontend_package_import",
    "plugin_discovery",
    "triton_jit_execution",
    "device_access",
    "generated_artifact_execution",
    "native_backend_execution",
    "python_import",
    "network_access",
    "subprocess_execution",
    "dynamic_library_loading",
)

MAX_SOURCE_INGESTION_APPROVAL_CRITERIA_FIELD_BYTES = 512
MAX_SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_BYTES = 96 * 1024

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
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
_FORBIDDEN_TEXT_FRAGMENTS = (
    "@triton.jit",
    "import os",
    "import triton",
    "tl.dot",
    "tl.store",
    '"backend_artifact":',
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
)


class SourceIngestionApprovalCriteriaError(ValueError):
    """Raised when source-ingestion approval criteria drift."""


@dataclass(frozen=True)
class SourceIngestionApprovalCriteriaReport:
    """Data-only criteria for a future maintainer approval decision."""

    criteria_contract: str = SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT
    criteria_id: str = SOURCE_INGESTION_APPROVAL_CRITERIA_ID
    criteria_status: str = SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS
    approval_status: str = SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS
    target_surface: str = SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE
    target_slice: str = SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE
    artifact_policy: str = SOURCE_INGESTION_APPROVAL_CRITERIA_ARTIFACT_POLICY
    admission_effect: str = SOURCE_INGESTION_APPROVAL_CRITERIA_ADMISSION_EFFECT
    required_criteria: tuple[str, ...] = (
        SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA
    )
    blocked_claims: tuple[str, ...] = (
        SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES
    )
    remaining_external_evidence: tuple[str, ...] = (
        SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE
    )

    def __post_init__(self) -> None:
        if self.criteria_contract != SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria contract drift"
            )
        if self.criteria_id != SOURCE_INGESTION_APPROVAL_CRITERIA_ID:
            raise SourceIngestionApprovalCriteriaError("approval criteria id drift")
        if self.criteria_status != SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria status drift"
            )
        if self.approval_status != SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria approval status drift"
            )
        if self.target_surface != SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria target surface drift"
            )
        if self.target_slice != SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria target slice drift"
            )
        if self.artifact_policy != SOURCE_INGESTION_APPROVAL_CRITERIA_ARTIFACT_POLICY:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria artifact policy drift"
            )
        if self.admission_effect != SOURCE_INGESTION_APPROVAL_CRITERIA_ADMISSION_EFFECT:
            raise SourceIngestionApprovalCriteriaError(
                "approval criteria admission effect drift"
            )
        _validate_exact_tuple(
            self.required_criteria,
            SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA,
            "required_criteria",
        )
        _validate_exact_tuple(
            self.blocked_claims,
            SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS,
            "blocked_claims",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.remaining_external_evidence,
            SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE,
            "remaining_external_evidence",
        )

    @property
    def approval_required(self) -> bool:
        """Return whether real maintainer approval is still required."""

        return True

    @property
    def criteria_ready(self) -> bool:
        """Return whether criteria are ready for maintainer review."""

        return True


def build_source_ingestion_approval_criteria_report() -> SourceIngestionApprovalCriteriaReport:
    """Build source-ingestion approval criteria evidence."""

    return SourceIngestionApprovalCriteriaReport()


def source_ingestion_approval_criteria_report_to_dict(
    report: SourceIngestionApprovalCriteriaReport,
) -> dict[str, object]:
    """Return stable JSON-ready approval criteria evidence."""

    if not isinstance(report, SourceIngestionApprovalCriteriaReport):
        raise TypeError("source-ingestion approval criteria report must be report")
    return {
        "admission_effect": report.admission_effect,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_required": report.approval_required,
        "approval_status": report.approval_status,
        "artifact_policy": report.artifact_policy,
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "criteria_contract": report.criteria_contract,
        "criteria_id": report.criteria_id,
        "criteria_ready": report.criteria_ready,
        "criteria_status": report.criteria_status,
        "direct_source_ingestion": False,
        "evidence_id": report.criteria_id,
        "execution_permission": "not_granted",
        "remaining_external_evidence": list(report.remaining_external_evidence),
        "remaining_external_evidence_count": len(report.remaining_external_evidence),
        "required_criteria": list(report.required_criteria),
        "required_criteria_count": len(report.required_criteria),
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "target_slice": report.target_slice,
        "target_surface": report.target_surface,
    }


def digest_json_payload(payload: Mapping[str, object]) -> str:
    """Return canonical digest for JSON-compatible payloads."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def dump_source_ingestion_approval_criteria_report(
    report: SourceIngestionApprovalCriteriaReport,
) -> str:
    """Render stable source-ingestion approval criteria evidence."""

    payload = source_ingestion_approval_criteria_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_BYTES:
        raise SourceIngestionApprovalCriteriaError(
            "source-ingestion approval criteria report exceeds byte limit"
        )
    return text + "\n"


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"approval criteria {label} must be tuple")
    if values != expected:
        raise SourceIngestionApprovalCriteriaError(
            f"approval criteria {label} drift"
        )
    for value in values:
        _validate_report_text(value, label)


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceIngestionApprovalCriteriaError(
            f"approval criteria {label} must be report-safe"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceIngestionApprovalCriteriaError(
            f"approval criteria {label} must be report-safe"
        )
    if len(value.encode("utf-8")) > MAX_SOURCE_INGESTION_APPROVAL_CRITERIA_FIELD_BYTES:
        raise SourceIngestionApprovalCriteriaError(
            f"approval criteria {label} exceeds limit"
        )


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionApprovalCriteriaError(
                f"approval criteria contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_SOURCE_INGESTION_APPROVAL_CRITERIA_FIELD_BYTES",
    "MAX_SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_BYTES",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_ADMISSION_EFFECT",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_ARTIFACT_POLICY",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_ID",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE",
    "SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE",
    "SourceIngestionApprovalCriteriaError",
    "SourceIngestionApprovalCriteriaReport",
    "build_source_ingestion_approval_criteria_report",
    "digest_json_payload",
    "dump_source_ingestion_approval_criteria_report",
    "source_ingestion_approval_criteria_report_to_dict",
]
