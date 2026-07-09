"""Fail-closed admission gate for direct source ingestion.

The gate binds the maintainer-review packet and keeps direct source ingestion
blocked until an external maintainer approval exists.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

SOURCE_INGESTION_ADMISSION_GATE_CONTRACT = (
    "source_ingestion_admission_gate.fail_closed.v0"
)
SOURCE_INGESTION_ADMISSION_GATE_ID = "source_ingestion_admission_gate"
SOURCE_INGESTION_ADMISSION_GATE_STATUS = (
    "blocked_missing_maintainer_security_review_approval"
)
SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS = "blocked"
SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS = "not_approved"
SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE = "direct_source_ingestion"
SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY = "digest_only_source_free"
SOURCE_INGESTION_ADMISSION_GATE_DECISION = "deny_until_external_approval"
SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)
SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS = (
    "maintainer_review_packet_bound",
    "approval_criteria_bound_by_review_packet",
    "external_approval_artifact_required",
    "external_approval_artifact_absent",
    "direct_source_ingestion_false",
    "source_to_compute_graph_false",
    "source_to_hac_ir_false",
    "source_to_runtime_plan_false",
    "no_source_text_serialization",
    "no_source_intent_payload_serialization",
    "no_runtime_handle_serialization",
    "no_generated_artifacts",
    "fail_closed_until_approval",
)
SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES = (
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

MAX_SOURCE_INGESTION_ADMISSION_GATE_FIELD_BYTES = 512
MAX_SOURCE_INGESTION_ADMISSION_GATE_REPORT_BYTES = 96 * 1024

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


class SourceIngestionAdmissionGateError(ValueError):
    """Raised when source-ingestion admission-gate evidence drifts."""


@dataclass(frozen=True)
class SourceIngestionAdmissionGateEvidence:
    """One source-free evidence artifact bound by the gate."""

    evidence_id: str
    contract: str
    status: str
    digest: str
    source_free: bool = True
    supports_gate: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        _validate_report_text(self.contract, "contract")
        _validate_report_text(self.status, "status")
        _validate_digest(self.digest, "digest")
        if self.source_free is not True:
            raise SourceIngestionAdmissionGateError(
                "source-ingestion admission evidence must be source-free"
            )
        if self.supports_gate is not True:
            raise SourceIngestionAdmissionGateError(
                "source-ingestion admission evidence must support the gate"
            )


@dataclass(frozen=True)
class SourceIngestionAdmissionGateReport:
    """Fail-closed source-ingestion admission gate report."""

    maintainer_review_packet: SourceIngestionAdmissionGateEvidence
    gate_contract: str = SOURCE_INGESTION_ADMISSION_GATE_CONTRACT
    gate_id: str = SOURCE_INGESTION_ADMISSION_GATE_ID
    gate_status: str = SOURCE_INGESTION_ADMISSION_GATE_STATUS
    admission_status: str = SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS
    approval_status: str = SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS
    target_surface: str = SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE
    target_slice: str = SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE
    evidence_policy: str = SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY
    decision: str = SOURCE_INGESTION_ADMISSION_GATE_DECISION
    required_external_evidence: tuple[str, ...] = (
        SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE
    )
    required_controls: tuple[str, ...] = (
        SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.maintainer_review_packet,
            SourceIngestionAdmissionGateEvidence,
        ):
            raise TypeError(
                "source-ingestion admission gate evidence must be evidence"
            )
        if self.gate_contract != SOURCE_INGESTION_ADMISSION_GATE_CONTRACT:
            raise SourceIngestionAdmissionGateError("admission gate contract drift")
        if self.gate_id != SOURCE_INGESTION_ADMISSION_GATE_ID:
            raise SourceIngestionAdmissionGateError("admission gate id drift")
        if self.gate_status != SOURCE_INGESTION_ADMISSION_GATE_STATUS:
            raise SourceIngestionAdmissionGateError("admission gate status drift")
        if self.admission_status != SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS:
            raise SourceIngestionAdmissionGateError(
                "admission gate admission status drift"
            )
        if self.approval_status != SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS:
            raise SourceIngestionAdmissionGateError(
                "admission gate approval status drift"
            )
        if self.target_surface != SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE:
            raise SourceIngestionAdmissionGateError("admission gate surface drift")
        if self.target_slice != SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE:
            raise SourceIngestionAdmissionGateError("admission gate slice drift")
        if self.evidence_policy != SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY:
            raise SourceIngestionAdmissionGateError(
                "admission gate evidence policy drift"
            )
        if self.decision != SOURCE_INGESTION_ADMISSION_GATE_DECISION:
            raise SourceIngestionAdmissionGateError("admission gate decision drift")
        _validate_exact_tuple(
            self.required_external_evidence,
            SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE,
            "required_external_evidence",
        )
        _validate_exact_tuple(
            self.required_controls,
            SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )


def build_source_ingestion_admission_gate_report(
    maintainer_review_packet: SourceIngestionAdmissionGateEvidence,
) -> SourceIngestionAdmissionGateReport:
    """Build a fail-closed source-ingestion admission gate report."""

    return SourceIngestionAdmissionGateReport(maintainer_review_packet)


def source_ingestion_admission_gate_report_to_dict(
    report: SourceIngestionAdmissionGateReport,
) -> dict[str, object]:
    """Return stable JSON-ready admission-gate evidence."""

    if not isinstance(report, SourceIngestionAdmissionGateReport):
        raise TypeError("source-ingestion admission gate report must be report")
    evidence = report.maintainer_review_packet
    return {
        "admission_status": report.admission_status,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_required": True,
        "approval_status": report.approval_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "decision": report.decision,
        "direct_source_ingestion": False,
        "evidence_policy": report.evidence_policy,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "maintainer_review_packet": {
            "contract": evidence.contract,
            "digest": evidence.digest,
            "evidence_id": evidence.evidence_id,
            "source_free": evidence.source_free,
            "status": evidence.status,
            "supports_gate": evidence.supports_gate,
        },
        "required_control_count": len(report.required_controls),
        "required_controls": list(report.required_controls),
        "required_external_evidence": list(report.required_external_evidence),
        "required_external_evidence_count": len(report.required_external_evidence),
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "target_slice": report.target_slice,
        "target_surface": report.target_surface,
    }


def source_ingestion_admission_gate_evidence_from_payload(
    payload: Mapping[str, object],
) -> SourceIngestionAdmissionGateEvidence:
    """Build admission-gate evidence from a source-free review-packet payload."""

    _assert_text_is_source_free(json.dumps(payload, sort_keys=True))
    evidence_id = payload.get("evidence_id")
    contract = payload.get("contract")
    status = payload.get("status")
    if not isinstance(evidence_id, str):
        raise SourceIngestionAdmissionGateError("admission evidence id missing")
    if not isinstance(contract, str):
        raise SourceIngestionAdmissionGateError("admission evidence contract missing")
    if not isinstance(status, str):
        raise SourceIngestionAdmissionGateError("admission evidence status missing")
    if payload.get("approval_status") != "not_approved":
        raise SourceIngestionAdmissionGateError("admission evidence approval drift")
    if payload.get("source_ingestion_admission_ready") is not False:
        raise SourceIngestionAdmissionGateError("admission evidence readiness drift")
    if payload.get("direct_source_ingestion") is not False:
        raise SourceIngestionAdmissionGateError("admission evidence source drift")
    return SourceIngestionAdmissionGateEvidence(
        evidence_id=evidence_id,
        contract=contract,
        status=status,
        digest=digest_json_payload(payload),
    )


def digest_json_payload(payload: Mapping[str, object]) -> str:
    """Return canonical digest for JSON-compatible payloads."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def dump_source_ingestion_admission_gate_report(
    report: SourceIngestionAdmissionGateReport,
) -> str:
    """Render stable source-ingestion admission-gate evidence."""

    payload = source_ingestion_admission_gate_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_SOURCE_INGESTION_ADMISSION_GATE_REPORT_BYTES:
        raise SourceIngestionAdmissionGateError(
            "source-ingestion admission gate report exceeds byte limit"
        )
    return text + "\n"


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"source-ingestion admission gate {label} must be tuple")
    if values != expected:
        raise SourceIngestionAdmissionGateError(
            f"source-ingestion admission gate {label} drift"
        )
    for value in values:
        _validate_report_text(value, label)


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceIngestionAdmissionGateError(
            f"source-ingestion admission gate {label} must be report-safe"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceIngestionAdmissionGateError(
            f"source-ingestion admission gate {label} must be report-safe"
        )
    if len(value.encode("utf-8")) > MAX_SOURCE_INGESTION_ADMISSION_GATE_FIELD_BYTES:
        raise SourceIngestionAdmissionGateError(
            f"source-ingestion admission gate {label} exceeds limit"
        )


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceIngestionAdmissionGateError(
            f"source-ingestion admission gate {label} must be sha256"
        )


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionAdmissionGateError(
                f"source-ingestion admission gate contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_SOURCE_INGESTION_ADMISSION_GATE_FIELD_BYTES",
    "MAX_SOURCE_INGESTION_ADMISSION_GATE_REPORT_BYTES",
    "SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS",
    "SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS",
    "SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_INGESTION_ADMISSION_GATE_CONTRACT",
    "SOURCE_INGESTION_ADMISSION_GATE_DECISION",
    "SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY",
    "SOURCE_INGESTION_ADMISSION_GATE_ID",
    "SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS",
    "SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE",
    "SOURCE_INGESTION_ADMISSION_GATE_STATUS",
    "SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE",
    "SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE",
    "SourceIngestionAdmissionGateError",
    "SourceIngestionAdmissionGateEvidence",
    "SourceIngestionAdmissionGateReport",
    "build_source_ingestion_admission_gate_report",
    "digest_json_payload",
    "dump_source_ingestion_admission_gate_report",
    "source_ingestion_admission_gate_evidence_from_payload",
    "source_ingestion_admission_gate_report_to_dict",
]
