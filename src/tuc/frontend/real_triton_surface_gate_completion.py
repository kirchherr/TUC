"""Data-only completion report for Real Triton surface gates.

The report binds Real Triton Integration Admission and all dedicated surface
gates by digest. It proves the surface-gate set is complete while keeping Real
Triton integration non-admitting.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.real_triton_integration_admission import (
    REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED,
    REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS,
    REAL_TRITON_INTEGRATION_BLOCKED_SURFACES,
)

REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION = (
    "tuc.real_triton_surface_gate_completion_report.v0"
)
REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT = (
    "real_triton_surface_gate_completion.data_only.v0"
)
REAL_TRITON_SURFACE_GATE_COMPLETION_ARTIFACT_STATUS = "review_gate"
REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS = "complete"
REAL_TRITON_SURFACE_GATE_COMPLETION_ADMISSION_EFFECT = (
    "does_not_admit_real_triton_integration"
)
REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE_POLICY = "digest_only"
REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES = (
    "source_ingestion_quarantine_gate",
    "package_import_sandbox_gate",
    "plugin_discovery_allowlist_gate",
    "triton_jit_execution_sandbox_gate",
    "device_access_sandbox_gate",
    "generated_artifact_quarantine_gate",
    "native_backend_execution_security_gate",
)
MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE = 16
MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_FIELD_BYTES = 512
MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_BYTES = 96 * 1024

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
class RealTritonSurfaceGateExpectation:
    """Static expectation for one dedicated Real Triton surface gate."""

    gate_id: str
    surface_id: str
    gate_status: str
    admission_effect: str

    def __post_init__(self) -> None:
        _validate_report_text(self.gate_id, "gate_id")
        _validate_report_text(self.surface_id, "surface_id")
        _validate_report_text(self.gate_status, "gate_status")
        _validate_report_text(self.admission_effect, "admission_effect")


@dataclass(frozen=True)
class RealTritonSurfaceGateEvidence:
    """Digest-only evidence for one dedicated Real Triton surface gate."""

    gate_id: str
    surface_id: str
    gate_status: str
    admission_effect: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.gate_id, "gate_id")
        _validate_report_text(self.surface_id, "surface_id")
        _validate_report_text(self.gate_status, "gate_status")
        _validate_report_text(self.admission_effect, "admission_effect")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("surface gate completion required flag must be bool")
        if not self.required:
            raise ValueError("surface gate completion evidence cannot be optional")
        expectation = _EXPECTATIONS_BY_GATE_ID.get(self.gate_id)
        if expectation is None:
            raise ValueError("surface gate completion evidence gate is not accepted")
        if self.surface_id != expectation.surface_id:
            raise ValueError("surface gate completion surface mismatch")
        if self.gate_status != expectation.gate_status:
            raise ValueError("surface gate completion gate status mismatch")
        if self.admission_effect != expectation.admission_effect:
            raise ValueError("surface gate completion admission effect mismatch")


@dataclass(frozen=True)
class RealTritonSurfaceGateCompletionReport:
    """Fail-closed completion report for Real Triton surface-gate coverage."""

    admission_gate_digest: str
    surface_gate_evidence: tuple[RealTritonSurfaceGateEvidence, ...]
    completion_contract: str = REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT
    artifact_status: str = REAL_TRITON_SURFACE_GATE_COMPLETION_ARTIFACT_STATUS
    evidence_policy: str = REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE_POLICY
    required_surface_gate_ids: tuple[str, ...] = (
        REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES
    )
    blocked_execution_surfaces: tuple[str, ...] = REAL_TRITON_INTEGRATION_BLOCKED_SURFACES
    blocked_claims: tuple[str, ...] = REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS

    def __post_init__(self) -> None:
        _validate_sha256(self.admission_gate_digest, "admission_gate_digest")
        if self.completion_contract != REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT:
            raise ValueError("surface gate completion contract mismatch")
        if self.artifact_status != REAL_TRITON_SURFACE_GATE_COMPLETION_ARTIFACT_STATUS:
            raise ValueError("surface gate completion artifact status mismatch")
        if self.evidence_policy != REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE_POLICY:
            raise ValueError("surface gate completion evidence policy mismatch")
        _validate_exact_tuple(
            self.required_surface_gate_ids,
            REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES,
            "required_surface_gate_ids",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            REAL_TRITON_INTEGRATION_BLOCKED_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_claims,
            REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS,
            "blocked_claims",
        )
        _validate_surface_gate_evidence(self.surface_gate_evidence)

    @property
    def completion_status(self) -> str:
        return REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS

    @property
    def admission_status(self) -> str:
        return REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED

    @property
    def admission_effect(self) -> str:
        return REAL_TRITON_SURFACE_GATE_COMPLETION_ADMISSION_EFFECT

    @property
    def admitted(self) -> bool:
        return False

    @property
    def security_boundary_established(self) -> bool:
        return True

    @property
    def expected_surface_gate_count(self) -> int:
        return len(self.required_surface_gate_ids)

    @property
    def surface_gate_count(self) -> int:
        return len(self.surface_gate_evidence)

    @property
    def blocked_surface_count(self) -> int:
        return len(self.blocked_execution_surfaces)

    @property
    def blocked_claim_count(self) -> int:
        return len(self.blocked_claims)

    @property
    def all_required_surface_gates_present(self) -> bool:
        return tuple(item.gate_id for item in self.surface_gate_evidence) == (
            self.required_surface_gate_ids
        )

    @property
    def all_surface_gates_non_admitting(self) -> bool:
        return all(
            item.admission_effect.startswith("does_not_admit_")
            for item in self.surface_gate_evidence
        )

    @property
    def missing_surface_gate_ids(self) -> tuple[str, ...]:
        observed = {item.gate_id for item in self.surface_gate_evidence}
        return tuple(
            gate_id
            for gate_id in self.required_surface_gate_ids
            if gate_id not in observed
        )


def build_real_triton_surface_gate_completion_report(
    admission_gate_digest: str,
    surface_gate_evidence: Iterable[RealTritonSurfaceGateEvidence],
) -> RealTritonSurfaceGateCompletionReport:
    """Build a data-only completion report for Real Triton surface gates."""

    return RealTritonSurfaceGateCompletionReport(
        admission_gate_digest=admission_gate_digest,
        surface_gate_evidence=tuple(surface_gate_evidence),
    )


def real_triton_surface_gate_completion_digest_payload(
    payload: Mapping[str, object],
) -> str:
    """Return the stable digest for a prerequisite report payload."""

    if not isinstance(payload, Mapping):
        raise TypeError("surface gate completion payload must be mapping")
    return _digest_payload(dict(payload))


def real_triton_surface_gate_evidence_from_payload(
    gate_id: str,
    payload: Mapping[str, object],
) -> RealTritonSurfaceGateEvidence:
    """Create digest-only surface-gate evidence from a gate report payload."""

    if not isinstance(payload, Mapping):
        raise TypeError("surface gate completion payload must be mapping")
    expectation = _EXPECTATIONS_BY_GATE_ID.get(gate_id)
    if expectation is None:
        raise ValueError("surface gate completion evidence gate is not accepted")
    for key, expected in (
        ("gate_id", expectation.gate_id),
        ("surface_id", expectation.surface_id),
        ("gate_status", expectation.gate_status),
        ("admission_effect", expectation.admission_effect),
    ):
        if payload.get(key) != expected:
            raise ValueError(f"surface gate completion {key} mismatch")
    return RealTritonSurfaceGateEvidence(
        gate_id=expectation.gate_id,
        surface_id=expectation.surface_id,
        gate_status=expectation.gate_status,
        admission_effect=expectation.admission_effect,
        evidence_digest=_digest_payload(dict(payload)),
    )


def real_triton_surface_gate_completion_report_to_dict(
    report: RealTritonSurfaceGateCompletionReport,
) -> dict[str, object]:
    """Return stable JSON-ready Real Triton surface-gate completion evidence."""

    if not isinstance(report, RealTritonSurfaceGateCompletionReport):
        raise TypeError("surface gate completion report must be report")
    return {
        "admission_effect": report.admission_effect,
        "admission_gate_digest": report.admission_gate_digest,
        "admission_status": report.admission_status,
        "admitted": report.admitted,
        "all_required_surface_gates_present": (
            report.all_required_surface_gates_present
        ),
        "all_surface_gates_non_admitting": report.all_surface_gates_non_admitting,
        "artifact_status": report.artifact_status,
        "blocked_claim_count": report.blocked_claim_count,
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_surface_count": report.blocked_surface_count,
        "completion_contract": report.completion_contract,
        "completion_status": report.completion_status,
        "evidence_policy": report.evidence_policy,
        "expected_surface_gate_count": report.expected_surface_gate_count,
        "missing_surface_gate_ids": list(report.missing_surface_gate_ids),
        "required_surface_gate_ids": list(report.required_surface_gate_ids),
        "schema_version": REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION,
        "security_boundary_established": report.security_boundary_established,
        "surface_gate_count": report.surface_gate_count,
        "surface_gates": [
            {
                "admission_effect": item.admission_effect,
                "evidence_digest": item.evidence_digest,
                "gate_id": item.gate_id,
                "gate_status": item.gate_status,
                "required": item.required,
                "surface_id": item.surface_id,
            }
            for item in report.surface_gate_evidence
        ],
    }


def dump_real_triton_surface_gate_completion_report(
    report: RealTritonSurfaceGateCompletionReport,
) -> str:
    """Render stable JSON Real Triton surface-gate completion evidence."""

    text = json.dumps(
        real_triton_surface_gate_completion_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_BYTES:
        raise ValueError("surface gate completion report exceeds byte limit")
    return f"{text}\n"


def _validate_surface_gate_evidence(
    evidence: tuple[RealTritonSurfaceGateEvidence, ...],
) -> None:
    if type(evidence) is not tuple:
        raise TypeError("surface gate completion evidence must be a tuple")
    if len(evidence) > MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE:
        raise ValueError("surface gate completion evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, RealTritonSurfaceGateEvidence):
            raise TypeError("surface gate completion evidence must be evidence")
    evidence_ids = tuple(item.gate_id for item in evidence)
    if evidence_ids != REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES:
        raise ValueError("surface gate completion required surface gate mismatch")
    evidence_digests = (item.evidence_digest for item in evidence)
    if len(tuple(evidence_digests)) != len({item.evidence_digest for item in evidence}):
        raise ValueError("surface gate completion evidence digests must be unique")


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"surface gate completion {label} must be tuple")
    if values != expected:
        raise ValueError(f"surface gate completion {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"surface gate completion {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"surface gate completion {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"surface gate completion {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_FIELD_BYTES:
        raise ValueError(f"surface gate completion {label} exceeds field limit")


REAL_TRITON_SURFACE_GATE_COMPLETION_EXPECTATIONS = (
    RealTritonSurfaceGateExpectation(
        gate_id="source_ingestion_quarantine_gate",
        surface_id="direct_source_ingestion",
        gate_status="quarantine_only",
        admission_effect="does_not_admit_direct_source_ingestion",
    ),
    RealTritonSurfaceGateExpectation(
        gate_id="package_import_sandbox_gate",
        surface_id="frontend_package_import",
        gate_status="sandbox_requirements_only",
        admission_effect="does_not_admit_frontend_package_import",
    ),
    RealTritonSurfaceGateExpectation(
        gate_id="plugin_discovery_allowlist_gate",
        surface_id="plugin_discovery",
        gate_status="allowlist_requirements_only",
        admission_effect="does_not_admit_plugin_discovery",
    ),
    RealTritonSurfaceGateExpectation(
        gate_id="triton_jit_execution_sandbox_gate",
        surface_id="triton_jit_execution",
        gate_status="sandbox_requirements_only",
        admission_effect="does_not_admit_triton_jit_execution",
    ),
    RealTritonSurfaceGateExpectation(
        gate_id="device_access_sandbox_gate",
        surface_id="device_access",
        gate_status="sandbox_requirements_only",
        admission_effect="does_not_admit_device_access",
    ),
    RealTritonSurfaceGateExpectation(
        gate_id="generated_artifact_quarantine_gate",
        surface_id="generated_artifact_execution",
        gate_status="quarantine_requirements_only",
        admission_effect="does_not_admit_generated_artifact_execution",
    ),
    RealTritonSurfaceGateExpectation(
        gate_id="native_backend_execution_security_gate",
        surface_id="native_backend_execution",
        gate_status="security_requirements_only",
        admission_effect="does_not_admit_native_backend_execution",
    ),
)
_EXPECTATIONS_BY_GATE_ID = {
    expectation.gate_id: expectation
    for expectation in REAL_TRITON_SURFACE_GATE_COMPLETION_EXPECTATIONS
}

__all__ = [
    "MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE",
    "MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_FIELD_BYTES",
    "MAX_REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_BYTES",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_ADMISSION_EFFECT",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_ARTIFACT_STATUS",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE_POLICY",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_EXPECTATIONS",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES",
    "REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS",
    "RealTritonSurfaceGateCompletionReport",
    "RealTritonSurfaceGateEvidence",
    "RealTritonSurfaceGateExpectation",
    "build_real_triton_surface_gate_completion_report",
    "dump_real_triton_surface_gate_completion_report",
    "real_triton_surface_gate_completion_digest_payload",
    "real_triton_surface_gate_completion_report_to_dict",
    "real_triton_surface_gate_evidence_from_payload",
]