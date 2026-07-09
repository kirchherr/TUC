"""Fail-closed maintainer approval status for source ingestion.

This module records that the external maintainer approval artifact is absent.
It never grants approval and never admits source ingestion into compiler
artifacts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT = (
    "source_ingestion_maintainer_approval_artifact.absent.v0"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_ID = (
    "source_ingestion_maintainer_approval_artifact"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS = "external_approval_not_supplied"
SOURCE_INGESTION_MAINTAINER_APPROVAL_APPROVAL_STATUS = "not_approved"
SOURCE_INGESTION_MAINTAINER_APPROVAL_DECISION = "deny_until_external_approval"
SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SURFACE = "direct_source_ingestion"
SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_POLICY = "digest_only_source_free"
SOURCE_INGESTION_MAINTAINER_APPROVAL_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_ID = (
    "source_ingestion_maintainer_security_review_packet"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_CONTRACT = (
    "source_ingestion_maintainer_security_review_packet.review.v0"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_STATUS = (
    "ready_for_maintainer_review"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS = (
    "maintainer_review_packet_bound",
    "approval_criteria_bound_by_review_packet",
    "external_approval_artifact_required",
    "external_approval_artifact_absent",
    "no_source_text_serialization",
    "no_source_intent_payload_serialization",
    "no_runtime_handle_serialization",
    "no_generated_artifacts",
    "approval_not_granted",
    "fail_closed_until_approval",
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_BLOCKED_EXECUTION_SURFACES = (
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

MAX_SOURCE_INGESTION_MAINTAINER_APPROVAL_FIELD_BYTES = 512
MAX_SOURCE_INGESTION_MAINTAINER_APPROVAL_REPORT_BYTES = 128 * 1024

_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
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


class SourceIngestionMaintainerApprovalError(ValueError):
    """Raised when source-ingestion maintainer approval evidence drifts."""


@dataclass(frozen=True)
class SourceIngestionMaintainerApprovalEvidence:
    """Review packet evidence bound by the approval-status artifact."""

    evidence_id: str
    contract: str
    status: str
    digest: str
    source_free: bool = True
    criteria_bound: bool = True
    reviewable: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        _validate_report_text(self.contract, "contract")
        _validate_report_text(self.status, "status")
        _validate_digest(self.digest, "digest")
        if self.source_free is not True:
            raise SourceIngestionMaintainerApprovalError(
                "approval evidence must be source-free"
            )
        if self.criteria_bound is not True:
            raise SourceIngestionMaintainerApprovalError(
                "approval evidence must bind approval criteria"
            )
        if self.reviewable is not True:
            raise SourceIngestionMaintainerApprovalError(
                "approval evidence must be reviewable"
            )


@dataclass(frozen=True)
class SourceIngestionMaintainerApprovalReport:
    """Fail-closed report for missing external maintainer approval."""

    maintainer_review_packet: SourceIngestionMaintainerApprovalEvidence
    contract: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT
    evidence_id: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_ID
    status: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS
    approval_status: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_APPROVAL_STATUS
    approval_decision: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_DECISION
    target_surface: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SURFACE
    target_slice: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SLICE
    artifact_policy: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_POLICY
    admission_effect: str = SOURCE_INGESTION_MAINTAINER_APPROVAL_ADMISSION_EFFECT
    required_external_evidence: tuple[str, ...] = (
        SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE
    )
    required_controls: tuple[str, ...] = (
        SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_INGESTION_MAINTAINER_APPROVAL_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.maintainer_review_packet,
            SourceIngestionMaintainerApprovalEvidence,
        ):
            raise TypeError("maintainer approval evidence must be evidence")
        if self.contract != SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT:
            raise SourceIngestionMaintainerApprovalError("approval contract drift")
        if self.evidence_id != SOURCE_INGESTION_MAINTAINER_APPROVAL_ID:
            raise SourceIngestionMaintainerApprovalError("approval id drift")
        if self.status != SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS:
            raise SourceIngestionMaintainerApprovalError("approval status drift")
        if self.approval_status != SOURCE_INGESTION_MAINTAINER_APPROVAL_APPROVAL_STATUS:
            raise SourceIngestionMaintainerApprovalError(
                "approval approval status drift"
            )
        if self.approval_decision != SOURCE_INGESTION_MAINTAINER_APPROVAL_DECISION:
            raise SourceIngestionMaintainerApprovalError("approval decision drift")
        if self.target_surface != SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SURFACE:
            raise SourceIngestionMaintainerApprovalError("approval surface drift")
        if self.target_slice != SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SLICE:
            raise SourceIngestionMaintainerApprovalError("approval slice drift")
        if self.artifact_policy != SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_POLICY:
            raise SourceIngestionMaintainerApprovalError(
                "approval artifact policy drift"
            )
        if self.admission_effect != SOURCE_INGESTION_MAINTAINER_APPROVAL_ADMISSION_EFFECT:
            raise SourceIngestionMaintainerApprovalError(
                "approval admission effect drift"
            )
        _validate_exact_tuple(
            self.required_external_evidence,
            SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE,
            "required_external_evidence",
        )
        _validate_exact_tuple(
            self.required_controls,
            SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_INGESTION_MAINTAINER_APPROVAL_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )

    @property
    def approval_required(self) -> bool:
        """Return whether external maintainer approval is still required."""

        return True


def build_source_ingestion_maintainer_approval_report(
    maintainer_review_packet: SourceIngestionMaintainerApprovalEvidence,
) -> SourceIngestionMaintainerApprovalReport:
    """Build fail-closed maintainer approval status evidence."""

    return SourceIngestionMaintainerApprovalReport(maintainer_review_packet)


def source_ingestion_maintainer_approval_report_to_dict(
    report: SourceIngestionMaintainerApprovalReport,
) -> dict[str, object]:
    """Return stable JSON-ready maintainer approval status evidence."""

    if not isinstance(report, SourceIngestionMaintainerApprovalReport):
        raise TypeError("maintainer approval report must be report")
    evidence = report.maintainer_review_packet
    return {
        "admission_effect": report.admission_effect,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_decision": report.approval_decision,
        "approval_required": report.approval_required,
        "approval_status": report.approval_status,
        "artifact_policy": report.artifact_policy,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "contract": report.contract,
        "criteria_bound_by_review_packet": evidence.criteria_bound,
        "direct_source_ingestion": False,
        "evidence_id": report.evidence_id,
        "execution_permission": "not_granted",
        "external_approval_artifact_present": False,
        "maintainer_review_packet": {
            "contract": evidence.contract,
            "criteria_bound": evidence.criteria_bound,
            "digest": evidence.digest,
            "evidence_id": evidence.evidence_id,
            "reviewable": evidence.reviewable,
            "source_free": evidence.source_free,
            "status": evidence.status,
        },
        "remaining_external_evidence": list(report.required_external_evidence),
        "required_external_evidence": list(report.required_external_evidence),
        "remaining_external_evidence_count": len(report.required_external_evidence),
        "required_control_count": len(report.required_controls),
        "required_controls": list(report.required_controls),
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "status": report.status,
        "target_slice": report.target_slice,
        "target_surface": report.target_surface,
    }


def source_ingestion_maintainer_approval_evidence_from_review_packet_payload(
    payload: Mapping[str, object],
) -> SourceIngestionMaintainerApprovalEvidence:
    """Build approval evidence from a source-free maintainer-review packet."""

    _validate_review_packet_payload(payload)
    return SourceIngestionMaintainerApprovalEvidence(
        evidence_id=SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_ID,
        contract=SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_CONTRACT,
        status=SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_STATUS,
        digest=digest_json_payload(payload),
    )


def digest_json_payload(payload: Mapping[str, object]) -> str:
    """Return canonical digest for JSON-compatible payloads."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def dump_source_ingestion_maintainer_approval_report(
    report: SourceIngestionMaintainerApprovalReport,
) -> str:
    """Render stable maintainer approval status evidence."""

    payload = source_ingestion_maintainer_approval_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if (
        len(text.encode("utf-8"))
        > MAX_SOURCE_INGESTION_MAINTAINER_APPROVAL_REPORT_BYTES
    ):
        raise SourceIngestionMaintainerApprovalError(
            "maintainer approval report exceeds byte limit"
        )
    return text + "\n"


def _validate_review_packet_payload(payload: Mapping[str, object]) -> None:
    _assert_text_is_source_free(json.dumps(payload, sort_keys=True))
    expected = {
        "evidence_id": SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_ID,
        "contract": SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_CONTRACT,
        "status": SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_STATUS,
        "approval_status": "not_approved",
        "direct_source_ingestion": False,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
    }
    for key, expected_value in expected.items():
        if payload.get(key) != expected_value:
            raise SourceIngestionMaintainerApprovalError(
                f"maintainer approval review packet {key} drift"
            )
    review_evidence = payload.get("review_evidence")
    if not isinstance(review_evidence, list):
        raise SourceIngestionMaintainerApprovalError(
            "maintainer approval review evidence missing"
        )
    evidence_ids = {
        item.get("evidence_id")
        for item in review_evidence
        if isinstance(item, Mapping)
    }
    if "source_ingestion_approval_criteria" not in evidence_ids:
        raise SourceIngestionMaintainerApprovalError(
            "maintainer approval criteria evidence missing"
        )


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"maintainer approval {label} must be tuple")
    if values != expected:
        raise SourceIngestionMaintainerApprovalError(
            f"maintainer approval {label} drift"
        )
    for value in values:
        _validate_report_text(value, label)


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceIngestionMaintainerApprovalError(
            f"maintainer approval {label} must be report-safe"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceIngestionMaintainerApprovalError(
            f"maintainer approval {label} must be report-safe"
        )
    if (
        len(value.encode("utf-8"))
        > MAX_SOURCE_INGESTION_MAINTAINER_APPROVAL_FIELD_BYTES
    ):
        raise SourceIngestionMaintainerApprovalError(
            f"maintainer approval {label} exceeds limit"
        )


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceIngestionMaintainerApprovalError(
            f"maintainer approval {label} must be sha256"
        )


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionMaintainerApprovalError(
                f"maintainer approval contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_SOURCE_INGESTION_MAINTAINER_APPROVAL_FIELD_BYTES",
    "MAX_SOURCE_INGESTION_MAINTAINER_APPROVAL_REPORT_BYTES",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_ADMISSION_EFFECT",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_APPROVAL_STATUS",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_POLICY",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_DECISION",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_ID",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_CONTRACT",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_ID",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_STATUS",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SLICE",
    "SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SURFACE",
    "SourceIngestionMaintainerApprovalError",
    "SourceIngestionMaintainerApprovalEvidence",
    "SourceIngestionMaintainerApprovalReport",
    "build_source_ingestion_maintainer_approval_report",
    "digest_json_payload",
    "dump_source_ingestion_maintainer_approval_report",
    "source_ingestion_maintainer_approval_evidence_from_review_packet_payload",
    "source_ingestion_maintainer_approval_report_to_dict",
]
