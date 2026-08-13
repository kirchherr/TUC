"""Data-only admission gate for future real Triton integration.

The gate binds the data-only Triton Integration Readiness evidence to a threat
model for real integration surfaces. It deliberately does not open source
ingestion, package import, plugin discovery, Triton JIT, device access,
generated artifact execution, or native backend execution.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION = (
    "tuc.real_triton_integration_admission_gate_report.v0"
)
REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT = (
    "real_triton_integration_admission.data_only.v0"
)
REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS = "review_gate"
REAL_TRITON_INTEGRATION_ADMISSION_SCOPE = "real_triton_integration_phase_zeta"
REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED = "blocked"
REAL_TRITON_INTEGRATION_ADMISSION_DECISION = (
    "blocked_until_surface_gates_exist"
)
REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE_POLICY = "digest_only"
REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE = (
    "external_frontend_package_conformance",
    "real_triton_integration_threat_model",
    "triton_integration_readiness",
)
REAL_TRITON_INTEGRATION_BLOCKED_SURFACES = (
    "device_access",
    "direct_source_ingestion",
    "dynamic_library_loading",
    "frontend_package_import",
    "generated_artifact_execution",
    "native_backend_execution",
    "network_access",
    "plugin_discovery",
    "python_function_object_inspection",
    "python_import",
    "subprocess_execution",
    "triton_jit_execution",
)
REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES = (
    "device_access_sandbox_gate",
    "generated_artifact_quarantine_gate",
    "native_backend_execution_security_gate",
    "package_import_sandbox_gate",
    "plugin_discovery_allowlist_gate",
    "source_ingestion_quarantine_gate",
    "triton_jit_execution_sandbox_gate",
)
REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS = (
    "accepts_arbitrary_triton_source",
    "executes_generated_artifacts",
    "executes_native_backends",
    "imports_external_frontend_packages",
    "runs_triton_jit",
    "uses_real_devices",
)
MAX_REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE = 16
MAX_REAL_TRITON_INTEGRATION_ADMISSION_SURFACES = 32
MAX_REAL_TRITON_INTEGRATION_ADMISSION_FIELD_BYTES = 512
MAX_REAL_TRITON_INTEGRATION_ADMISSION_REPORT_BYTES = 96 * 1024

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
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
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_SURFACE_REQUIRED_GATE = {
    "device_access": "device_access_sandbox_gate",
    "direct_source_ingestion": "source_ingestion_quarantine_gate",
    "dynamic_library_loading": "native_backend_execution_security_gate",
    "frontend_package_import": "package_import_sandbox_gate",
    "generated_artifact_execution": "generated_artifact_quarantine_gate",
    "native_backend_execution": "native_backend_execution_security_gate",
    "network_access": "package_import_sandbox_gate",
    "plugin_discovery": "plugin_discovery_allowlist_gate",
    "python_function_object_inspection": "source_ingestion_quarantine_gate",
    "python_import": "package_import_sandbox_gate",
    "subprocess_execution": "generated_artifact_quarantine_gate",
    "triton_jit_execution": "triton_jit_execution_sandbox_gate",
}


@dataclass(frozen=True)
class RealTritonIntegrationEvidence:
    """Digest-only input evidence for real Triton integration admission."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE:
            raise ValueError("real Triton integration evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("real Triton integration evidence required flag must be bool")
        if not self.required:
            raise ValueError("real Triton integration required evidence cannot be optional")


@dataclass(frozen=True)
class RealTritonIntegrationSurface:
    """One blocked real integration surface and its future gate."""

    surface_id: str
    status: str
    required_gate: str

    def __post_init__(self) -> None:
        _validate_report_text(self.surface_id, "surface_id")
        _validate_report_text(self.status, "status")
        _validate_report_text(self.required_gate, "required_gate")
        if self.surface_id not in REAL_TRITON_INTEGRATION_BLOCKED_SURFACES:
            raise ValueError("real Triton integration surface is not accepted")
        if self.status != REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED:
            raise ValueError("real Triton integration surface must remain blocked")
        if self.required_gate not in REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES:
            raise ValueError("real Triton integration required gate is not accepted")
        if self.required_gate != _SURFACE_REQUIRED_GATE[self.surface_id]:
            raise ValueError("real Triton integration surface gate mismatch")


@dataclass(frozen=True)
class RealTritonIntegrationAdmissionReport:
    """Fail-closed admission report for real Triton integration."""

    evidence: tuple[RealTritonIntegrationEvidence, ...]
    surfaces: tuple[RealTritonIntegrationSurface, ...]
    admission_contract: str = REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT
    artifact_status: str = REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS
    integration_scope: str = REAL_TRITON_INTEGRATION_ADMISSION_SCOPE
    evidence_policy: str = REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE
    required_surface_gates: tuple[str, ...] = REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES
    blocked_claims: tuple[str, ...] = REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        _validate_surfaces(self.surfaces)
        if self.admission_contract != REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT:
            raise ValueError("real Triton integration admission contract mismatch")
        if self.artifact_status != REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS:
            raise ValueError("real Triton integration artifact status mismatch")
        if self.integration_scope != REAL_TRITON_INTEGRATION_ADMISSION_SCOPE:
            raise ValueError("real Triton integration scope mismatch")
        if self.evidence_policy != REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE_POLICY:
            raise ValueError("real Triton integration evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_surface_gates,
            REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES,
            "required_surface_gates",
        )
        _validate_exact_tuple(
            self.blocked_claims,
            REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS,
            "blocked_claims",
        )

    @property
    def admission_status(self) -> str:
        return REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED

    @property
    def admission_decision(self) -> str:
        return REAL_TRITON_INTEGRATION_ADMISSION_DECISION

    @property
    def admitted(self) -> bool:
        return False

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def blocked_surface_count(self) -> int:
        return len(self.surfaces)

    @property
    def direct_source_ingestion(self) -> bool:
        return False

    @property
    def frontend_package_import(self) -> bool:
        return False

    @property
    def plugin_discovery(self) -> bool:
        return False

    @property
    def triton_jit_execution(self) -> bool:
        return False

    @property
    def device_access(self) -> bool:
        return False

    @property
    def generated_artifact_execution(self) -> bool:
        return False

    @property
    def native_backend_execution(self) -> bool:
        return False


def build_real_triton_integration_admission_report(
    evidence: Iterable[RealTritonIntegrationEvidence],
    surfaces: Iterable[RealTritonIntegrationSurface] = (),
) -> RealTritonIntegrationAdmissionReport:
    """Build the fail-closed admission report from digest-only evidence."""

    normalized_surfaces = tuple(surfaces) or default_real_triton_integration_surfaces()
    return RealTritonIntegrationAdmissionReport(
        evidence=tuple(evidence),
        surfaces=normalized_surfaces,
    )


def default_real_triton_integration_surfaces() -> tuple[RealTritonIntegrationSurface, ...]:
    """Return all currently blocked real Triton integration surfaces."""

    return tuple(
        RealTritonIntegrationSurface(
            surface_id=surface_id,
            status=REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED,
            required_gate=_SURFACE_REQUIRED_GATE[surface_id],
        )
        for surface_id in REAL_TRITON_INTEGRATION_BLOCKED_SURFACES
    )


def real_triton_integration_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> RealTritonIntegrationEvidence:
    """Create digest-only evidence from an already materialized data payload."""

    if not isinstance(payload, Mapping):
        raise TypeError("real Triton integration evidence payload must be mapping")
    return RealTritonIntegrationEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def real_triton_integration_admission_report_to_dict(
    report: RealTritonIntegrationAdmissionReport,
) -> dict[str, object]:
    """Return stable JSON-ready real Triton integration admission evidence."""

    if not isinstance(report, RealTritonIntegrationAdmissionReport):
        raise TypeError("real Triton integration admission report must be report")
    return {
        "admission_contract": report.admission_contract,
        "admission_decision": report.admission_decision,
        "admission_status": report.admission_status,
        "admitted": report.admitted,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_status": report.artifact_status,
        "blocked_claims": list(report.blocked_claims),
        "blocked_surface_count": report.blocked_surface_count,
        "device_access": report.device_access,
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
        "frontend_package_import": report.frontend_package_import,
        "generated_artifact_execution": report.generated_artifact_execution,
        "integration_scope": report.integration_scope,
        "native_backend_execution": report.native_backend_execution,
        "plugin_discovery": report.plugin_discovery,
        "required_evidence_ids": list(report.required_evidence_ids),
        "required_surface_gates": list(report.required_surface_gates),
        "schema_version": REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION,
        "surfaces": [
            {
                "required_gate": item.required_gate,
                "status": item.status,
                "surface_id": item.surface_id,
            }
            for item in report.surfaces
        ],
        "triton_jit_execution": report.triton_jit_execution,
    }


def dump_real_triton_integration_admission_report(
    report: RealTritonIntegrationAdmissionReport,
) -> str:
    """Render stable JSON real Triton integration admission evidence."""

    text = json.dumps(
        real_triton_integration_admission_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_REAL_TRITON_INTEGRATION_ADMISSION_REPORT_BYTES:
        raise ValueError("real Triton integration admission report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(evidence: tuple[RealTritonIntegrationEvidence, ...]) -> None:
    if type(evidence) is not tuple:
        raise TypeError("real Triton integration evidence must be a tuple")
    if len(evidence) > MAX_REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE:
        raise ValueError("real Triton integration evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, RealTritonIntegrationEvidence):
            raise TypeError("real Triton integration evidence must be evidence objects")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE:
        raise ValueError("real Triton integration required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError("real Triton integration evidence digests must be unique")


def _validate_surfaces(surfaces: tuple[RealTritonIntegrationSurface, ...]) -> None:
    if type(surfaces) is not tuple:
        raise TypeError("real Triton integration surfaces must be a tuple")
    if len(surfaces) > MAX_REAL_TRITON_INTEGRATION_ADMISSION_SURFACES:
        raise ValueError("real Triton integration surface count exceeds limit")
    for item in surfaces:
        if not isinstance(item, RealTritonIntegrationSurface):
            raise TypeError("real Triton integration surfaces must be surface objects")
    surface_ids = tuple(item.surface_id for item in surfaces)
    if surface_ids != REAL_TRITON_INTEGRATION_BLOCKED_SURFACES:
        raise ValueError("real Triton integration blocked surfaces mismatch")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"real Triton integration {label} must be a tuple")
    if values != expected:
        raise ValueError(f"real Triton integration {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"real Triton integration {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"real Triton integration {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"real Triton integration {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_REAL_TRITON_INTEGRATION_ADMISSION_FIELD_BYTES:
        raise ValueError(f"real Triton integration {label} exceeds field limit")


__all__ = [
    "MAX_REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE",
    "MAX_REAL_TRITON_INTEGRATION_ADMISSION_FIELD_BYTES",
    "MAX_REAL_TRITON_INTEGRATION_ADMISSION_REPORT_BYTES",
    "MAX_REAL_TRITON_INTEGRATION_ADMISSION_SURFACES",
    "REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS",
    "REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT",
    "REAL_TRITON_INTEGRATION_ADMISSION_DECISION",
    "REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE_POLICY",
    "REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION",
    "REAL_TRITON_INTEGRATION_ADMISSION_SCOPE",
    "REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED",
    "REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS",
    "REAL_TRITON_INTEGRATION_BLOCKED_SURFACES",
    "REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE",
    "REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES",
    "RealTritonIntegrationAdmissionReport",
    "RealTritonIntegrationEvidence",
    "RealTritonIntegrationSurface",
    "build_real_triton_integration_admission_report",
    "default_real_triton_integration_surfaces",
    "dump_real_triton_integration_admission_report",
    "real_triton_integration_admission_report_to_dict",
    "real_triton_integration_evidence_from_payload",
]
