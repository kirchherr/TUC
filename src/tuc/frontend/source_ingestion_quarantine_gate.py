"""Data-only quarantine gate for future source ingestion.

This gate is the first dedicated surface gate behind Real Triton Integration
Admission. It establishes a quarantine boundary for source buffers without
admitting direct source ingestion into compiler artifacts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_quarantine_gate_report.v0"
)
SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT = (
    "source_ingestion_quarantine_gate.data_only.v0"
)
SOURCE_INGESTION_QUARANTINE_GATE_ARTIFACT_STATUS = "review_gate"
SOURCE_INGESTION_QUARANTINE_GATE_ID = "source_ingestion_quarantine_gate"
SOURCE_INGESTION_QUARANTINE_SURFACE_ID = "direct_source_ingestion"
SOURCE_INGESTION_QUARANTINE_GATE_STATUS = "quarantine_only"
SOURCE_INGESTION_QUARANTINE_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
SOURCE_INGESTION_QUARANTINE_EVIDENCE_POLICY = "digest_only"
SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE = (
    "real_triton_integration_admission_gate",
    "source_to_intent_parser_gate",
    "triton_source_preflight",
    "triton_source_threat_model",
)
SOURCE_INGESTION_QUARANTINE_REQUIRED_CONTROLS = (
    "bounded_source_buffer",
    "decode_only_before_preflight",
    "digest_only_evidence",
    "execution_free_ast_preflight",
    "fail_closed_on_violation",
    "input_treated_as_untrusted",
    "no_compute_graph_from_source",
    "no_device_access",
    "no_generated_artifacts",
    "no_hac_ir_from_source",
    "no_python_import",
    "no_raw_source_serialization",
    "no_triton_jit",
    "sanitized_diagnostics_only",
)
SOURCE_INGESTION_QUARANTINE_BLOCKED_EXECUTION_SURFACES = (
    "device_access",
    "direct_source_ingestion",
    "frontend_package_import",
    "generated_artifact_execution",
    "plugin_discovery",
    "python_function_object_inspection",
    "python_import",
    "triton_jit_execution",
)
SOURCE_INGESTION_QUARANTINE_BLOCKED_OUTPUTS = (
    "compute_graph",
    "generated_artifact",
    "hac_ir",
    "hs_ir",
    "python_function_object",
    "runtime_plan",
    "tlir",
)
MAX_SOURCE_INGESTION_QUARANTINE_EVIDENCE = 16
MAX_SOURCE_INGESTION_QUARANTINE_FIELD_BYTES = 512
MAX_SOURCE_INGESTION_QUARANTINE_REPORT_BYTES = 96 * 1024

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
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
        "raw_source_text",
        "raw_timing_samples",
        "runtime_handle",
        "source_text",
        "url",
    }
)


@dataclass(frozen=True)
class SourceIngestionQuarantineEvidence:
    """Digest-only prerequisite evidence for source-ingestion quarantine."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE:
            raise ValueError("source ingestion quarantine evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("source ingestion quarantine required flag must be bool")
        if not self.required:
            raise ValueError("source ingestion quarantine evidence cannot be optional")


@dataclass(frozen=True)
class SourceIngestionQuarantineReport:
    """Fail-closed report for the source-ingestion quarantine boundary."""

    evidence: tuple[SourceIngestionQuarantineEvidence, ...]
    gate_contract: str = SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT
    artifact_status: str = SOURCE_INGESTION_QUARANTINE_GATE_ARTIFACT_STATUS
    gate_id: str = SOURCE_INGESTION_QUARANTINE_GATE_ID
    surface_id: str = SOURCE_INGESTION_QUARANTINE_SURFACE_ID
    evidence_policy: str = SOURCE_INGESTION_QUARANTINE_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE
    required_controls: tuple[str, ...] = SOURCE_INGESTION_QUARANTINE_REQUIRED_CONTROLS
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_INGESTION_QUARANTINE_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = SOURCE_INGESTION_QUARANTINE_BLOCKED_OUTPUTS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT:
            raise ValueError("source ingestion quarantine contract mismatch")
        if self.artifact_status != SOURCE_INGESTION_QUARANTINE_GATE_ARTIFACT_STATUS:
            raise ValueError("source ingestion quarantine artifact status mismatch")
        if self.gate_id != SOURCE_INGESTION_QUARANTINE_GATE_ID:
            raise ValueError("source ingestion quarantine gate id mismatch")
        if self.surface_id != SOURCE_INGESTION_QUARANTINE_SURFACE_ID:
            raise ValueError("source ingestion quarantine surface id mismatch")
        if self.evidence_policy != SOURCE_INGESTION_QUARANTINE_EVIDENCE_POLICY:
            raise ValueError("source ingestion quarantine evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            SOURCE_INGESTION_QUARANTINE_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_INGESTION_QUARANTINE_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            SOURCE_INGESTION_QUARANTINE_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return SOURCE_INGESTION_QUARANTINE_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return SOURCE_INGESTION_QUARANTINE_ADMISSION_EFFECT

    @property
    def quarantine_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def direct_source_ingestion(self) -> bool:
        return False

    @property
    def source_to_compute_graph(self) -> bool:
        return False

    @property
    def source_to_hac_ir(self) -> bool:
        return False

    @property
    def source_to_runtime_plan(self) -> bool:
        return False

    @property
    def triton_jit_execution(self) -> bool:
        return False

    @property
    def python_import(self) -> bool:
        return False

    @property
    def function_object_inspection(self) -> bool:
        return False

    @property
    def raw_source_serialization(self) -> bool:
        return False

    @property
    def generated_artifact_execution(self) -> bool:
        return False


def build_source_ingestion_quarantine_report(
    evidence: Iterable[SourceIngestionQuarantineEvidence],
) -> SourceIngestionQuarantineReport:
    """Build the source-ingestion quarantine report from digest-only evidence."""

    return SourceIngestionQuarantineReport(evidence=tuple(evidence))


def source_ingestion_quarantine_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> SourceIngestionQuarantineEvidence:
    """Create digest-only quarantine evidence from a data-only payload."""

    if not isinstance(payload, Mapping):
        raise TypeError("source ingestion quarantine evidence payload must be mapping")
    return SourceIngestionQuarantineEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def source_ingestion_quarantine_report_to_dict(
    report: SourceIngestionQuarantineReport,
) -> dict[str, object]:
    """Return stable JSON-ready source-ingestion quarantine evidence."""

    if not isinstance(report, SourceIngestionQuarantineReport):
        raise TypeError("source ingestion quarantine report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "direct_source_ingestion": report.direct_source_ingestion,
        "evidence": [
            {
                "evidence_digest": item.evidence_digest,
                "evidence_id": item.evidence_id,
                "required": item.required,
            }
            for item in report.evidence
        ],
        "evidence_count": report.evidence_count,
        "evidence_policy": report.evidence_policy,
        "function_object_inspection": report.function_object_inspection,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "generated_artifact_execution": report.generated_artifact_execution,
        "python_import": report.python_import,
        "quarantine_boundary_established": report.quarantine_boundary_established,
        "raw_source_serialization": report.raw_source_serialization,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "schema_version": SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": report.source_to_compute_graph,
        "source_to_hac_ir": report.source_to_hac_ir,
        "source_to_runtime_plan": report.source_to_runtime_plan,
        "surface_id": report.surface_id,
        "triton_jit_execution": report.triton_jit_execution,
    }


def dump_source_ingestion_quarantine_report(
    report: SourceIngestionQuarantineReport,
) -> str:
    """Render stable JSON source-ingestion quarantine evidence."""

    text = json.dumps(
        source_ingestion_quarantine_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_INGESTION_QUARANTINE_REPORT_BYTES:
        raise ValueError("source ingestion quarantine report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(
    evidence: tuple[SourceIngestionQuarantineEvidence, ...],
) -> None:
    if type(evidence) is not tuple:
        raise TypeError("source ingestion quarantine evidence must be a tuple")
    if len(evidence) > MAX_SOURCE_INGESTION_QUARANTINE_EVIDENCE:
        raise ValueError("source ingestion quarantine evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, SourceIngestionQuarantineEvidence):
            raise TypeError("source ingestion quarantine evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE:
        raise ValueError("source ingestion quarantine required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError("source ingestion quarantine evidence digests must be unique")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"source ingestion quarantine {label} must be tuple")
    if values != expected:
        raise ValueError(f"source ingestion quarantine {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"source ingestion quarantine {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"source ingestion quarantine {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"source ingestion quarantine {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_SOURCE_INGESTION_QUARANTINE_FIELD_BYTES:
        raise ValueError(f"source ingestion quarantine {label} exceeds field limit")


__all__ = [
    "MAX_SOURCE_INGESTION_QUARANTINE_EVIDENCE",
    "MAX_SOURCE_INGESTION_QUARANTINE_FIELD_BYTES",
    "MAX_SOURCE_INGESTION_QUARANTINE_REPORT_BYTES",
    "SOURCE_INGESTION_QUARANTINE_ADMISSION_EFFECT",
    "SOURCE_INGESTION_QUARANTINE_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_INGESTION_QUARANTINE_BLOCKED_OUTPUTS",
    "SOURCE_INGESTION_QUARANTINE_EVIDENCE_POLICY",
    "SOURCE_INGESTION_QUARANTINE_GATE_ARTIFACT_STATUS",
    "SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT",
    "SOURCE_INGESTION_QUARANTINE_GATE_ID",
    "SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION",
    "SOURCE_INGESTION_QUARANTINE_GATE_STATUS",
    "SOURCE_INGESTION_QUARANTINE_REQUIRED_CONTROLS",
    "SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE",
    "SOURCE_INGESTION_QUARANTINE_SURFACE_ID",
    "SourceIngestionQuarantineEvidence",
    "SourceIngestionQuarantineReport",
    "build_source_ingestion_quarantine_report",
    "dump_source_ingestion_quarantine_report",
    "source_ingestion_quarantine_evidence_from_payload",
    "source_ingestion_quarantine_report_to_dict",
]
