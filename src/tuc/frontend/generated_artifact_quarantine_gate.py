"""Data-only quarantine gate for future generated artifacts.

The gate documents the quarantine requirements needed before TUC can ever
consider generated artifacts executable or loadable. It deliberately keeps
artifact emission, artifact writes, artifact loads, executable permissions,
backend binary emission, generated artifact execution, device access, kernel
launch, subprocesses, and dynamic libraries blocked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.generated_artifact_quarantine_gate_report.v0"
)
GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT = (
    "generated_artifact_quarantine_gate.data_only.v0"
)
GENERATED_ARTIFACT_QUARANTINE_GATE_ARTIFACT_STATUS = "review_gate"
GENERATED_ARTIFACT_QUARANTINE_GATE_ID = "generated_artifact_quarantine_gate"
GENERATED_ARTIFACT_QUARANTINE_SURFACE_ID = "generated_artifact_execution"
GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS = "quarantine_requirements_only"
GENERATED_ARTIFACT_QUARANTINE_ADMISSION_EFFECT = (
    "does_not_admit_generated_artifact_execution"
)
GENERATED_ARTIFACT_QUARANTINE_EVIDENCE_POLICY = "digest_only"
GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE = (
    "real_triton_integration_admission_gate",
    "triton_jit_execution_sandbox_gate",
    "device_access_sandbox_gate",
    "generated_artifact_quarantine_model",
)
GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS = (
    "artifact_cache_access_blocked",
    "artifact_emission_blocked",
    "artifact_load_blocked",
    "artifact_provenance_required",
    "artifact_writes_blocked",
    "backend_binary_emission_blocked",
    "device_access_blocked",
    "digest_only_evidence",
    "dynamic_library_loading_blocked",
    "executable_permissions_blocked",
    "fail_closed_on_violation",
    "file_system_access_blocked",
    "generated_artifact_execution_blocked",
    "kernel_launch_blocked",
    "no_backend_binary_emission",
    "no_generated_artifact_execution",
    "no_kernel_cache_access",
    "no_subprocess_execution",
    "quarantine_metadata_only",
    "sanitized_diagnostics_only",
)
GENERATED_ARTIFACT_QUARANTINE_BLOCKED_EXECUTION_SURFACES = (
    "artifact_cache_access",
    "artifact_load",
    "artifact_write",
    "backend_binary_emission",
    "device_access",
    "dynamic_library_loading",
    "file_system_access",
    "generated_artifact_execution",
    "kernel_launch",
    "subprocess_execution",
    "triton_jit_execution",
)
GENERATED_ARTIFACT_QUARANTINE_BLOCKED_OUTPUTS = (
    "backend_binary_record",
    "compiled_kernel_record",
    "executable_artifact",
    "generated_artifact_record",
    "kernel_cache_record",
    "loadable_module",
)
MAX_GENERATED_ARTIFACT_QUARANTINE_EVIDENCE = 16
MAX_GENERATED_ARTIFACT_QUARANTINE_FIELD_BYTES = 512
MAX_GENERATED_ARTIFACT_QUARANTINE_REPORT_BYTES = 96 * 1024

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
class GeneratedArtifactQuarantineEvidence:
    """Digest-only prerequisite evidence for generated-artifact quarantine."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE:
            raise ValueError("generated artifact quarantine evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("generated artifact quarantine required flag must be bool")
        if not self.required:
            raise ValueError("generated artifact quarantine evidence cannot be optional")


@dataclass(frozen=True)
class GeneratedArtifactQuarantineReport:
    """Fail-closed report for the generated-artifact quarantine boundary."""

    evidence: tuple[GeneratedArtifactQuarantineEvidence, ...]
    gate_contract: str = GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT
    artifact_status: str = GENERATED_ARTIFACT_QUARANTINE_GATE_ARTIFACT_STATUS
    gate_id: str = GENERATED_ARTIFACT_QUARANTINE_GATE_ID
    surface_id: str = GENERATED_ARTIFACT_QUARANTINE_SURFACE_ID
    evidence_policy: str = GENERATED_ARTIFACT_QUARANTINE_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = (
        GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE
    )
    required_controls: tuple[str, ...] = (
        GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        GENERATED_ARTIFACT_QUARANTINE_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = GENERATED_ARTIFACT_QUARANTINE_BLOCKED_OUTPUTS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT:
            raise ValueError("generated artifact quarantine contract mismatch")
        if (
            self.artifact_status
            != GENERATED_ARTIFACT_QUARANTINE_GATE_ARTIFACT_STATUS
        ):
            raise ValueError("generated artifact quarantine artifact status mismatch")
        if self.gate_id != GENERATED_ARTIFACT_QUARANTINE_GATE_ID:
            raise ValueError("generated artifact quarantine gate id mismatch")
        if self.surface_id != GENERATED_ARTIFACT_QUARANTINE_SURFACE_ID:
            raise ValueError("generated artifact quarantine surface id mismatch")
        if self.evidence_policy != GENERATED_ARTIFACT_QUARANTINE_EVIDENCE_POLICY:
            raise ValueError("generated artifact quarantine evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            GENERATED_ARTIFACT_QUARANTINE_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            GENERATED_ARTIFACT_QUARANTINE_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return GENERATED_ARTIFACT_QUARANTINE_ADMISSION_EFFECT

    @property
    def quarantine_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def generated_artifact_execution(self) -> bool:
        return False

    @property
    def generated_artifact_emission(self) -> bool:
        return False

    @property
    def artifact_write(self) -> bool:
        return False

    @property
    def artifact_load(self) -> bool:
        return False

    @property
    def artifact_cache_access(self) -> bool:
        return False

    @property
    def artifact_provenance_verified(self) -> bool:
        return False

    @property
    def executable_permission_granted(self) -> bool:
        return False

    @property
    def backend_binary_emitted(self) -> bool:
        return False

    @property
    def compiled_kernel_emitted(self) -> bool:
        return False

    @property
    def file_system_access(self) -> bool:
        return False

    @property
    def device_access(self) -> bool:
        return False

    @property
    def kernel_launch(self) -> bool:
        return False

    @property
    def triton_jit_execution(self) -> bool:
        return False

    @property
    def subprocess_execution(self) -> bool:
        return False

    @property
    def dynamic_library_loading(self) -> bool:
        return False


def build_generated_artifact_quarantine_report(
    evidence: Iterable[GeneratedArtifactQuarantineEvidence],
) -> GeneratedArtifactQuarantineReport:
    """Build the generated-artifact quarantine report from digest-only evidence."""

    return GeneratedArtifactQuarantineReport(evidence=tuple(evidence))


def generated_artifact_quarantine_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> GeneratedArtifactQuarantineEvidence:
    """Create digest-only generated-artifact quarantine evidence."""

    if not isinstance(payload, Mapping):
        raise TypeError("generated artifact quarantine payload must be mapping")
    return GeneratedArtifactQuarantineEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def generated_artifact_quarantine_report_to_dict(
    report: GeneratedArtifactQuarantineReport,
) -> dict[str, object]:
    """Return stable JSON-ready generated-artifact quarantine evidence."""

    if not isinstance(report, GeneratedArtifactQuarantineReport):
        raise TypeError("generated artifact quarantine report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_cache_access": report.artifact_cache_access,
        "artifact_load": report.artifact_load,
        "artifact_provenance_verified": report.artifact_provenance_verified,
        "artifact_status": report.artifact_status,
        "artifact_write": report.artifact_write,
        "backend_binary_emitted": report.backend_binary_emitted,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "compiled_kernel_emitted": report.compiled_kernel_emitted,
        "device_access": report.device_access,
        "dynamic_library_loading": report.dynamic_library_loading,
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
        "executable_permission_granted": report.executable_permission_granted,
        "file_system_access": report.file_system_access,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "generated_artifact_emission": report.generated_artifact_emission,
        "generated_artifact_execution": report.generated_artifact_execution,
        "kernel_launch": report.kernel_launch,
        "quarantine_boundary_established": report.quarantine_boundary_established,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "schema_version": GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION,
        "subprocess_execution": report.subprocess_execution,
        "surface_id": report.surface_id,
        "triton_jit_execution": report.triton_jit_execution,
    }


def dump_generated_artifact_quarantine_report(
    report: GeneratedArtifactQuarantineReport,
) -> str:
    """Render stable JSON generated-artifact quarantine evidence."""

    text = json.dumps(
        generated_artifact_quarantine_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_GENERATED_ARTIFACT_QUARANTINE_REPORT_BYTES:
        raise ValueError("generated artifact quarantine report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(
    evidence: tuple[GeneratedArtifactQuarantineEvidence, ...],
) -> None:
    if type(evidence) is not tuple:
        raise TypeError("generated artifact quarantine evidence must be a tuple")
    if len(evidence) > MAX_GENERATED_ARTIFACT_QUARANTINE_EVIDENCE:
        raise ValueError("generated artifact quarantine evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, GeneratedArtifactQuarantineEvidence):
            raise TypeError("generated artifact quarantine evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE:
        raise ValueError("generated artifact quarantine required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError(
            "generated artifact quarantine evidence digests must be unique"
        )


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"generated artifact quarantine {label} must be tuple")
    if values != expected:
        raise ValueError(f"generated artifact quarantine {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"generated artifact quarantine {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"generated artifact quarantine {label} must be report-safe text"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(
            f"generated artifact quarantine {label} must be report-safe text"
        )
    if len(value.encode("utf-8")) > MAX_GENERATED_ARTIFACT_QUARANTINE_FIELD_BYTES:
        raise ValueError(f"generated artifact quarantine {label} exceeds field limit")


__all__ = [
    "GENERATED_ARTIFACT_QUARANTINE_ADMISSION_EFFECT",
    "GENERATED_ARTIFACT_QUARANTINE_BLOCKED_EXECUTION_SURFACES",
    "GENERATED_ARTIFACT_QUARANTINE_BLOCKED_OUTPUTS",
    "GENERATED_ARTIFACT_QUARANTINE_EVIDENCE_POLICY",
    "GENERATED_ARTIFACT_QUARANTINE_GATE_ARTIFACT_STATUS",
    "GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT",
    "GENERATED_ARTIFACT_QUARANTINE_GATE_ID",
    "GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION",
    "GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS",
    "GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS",
    "GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE",
    "GENERATED_ARTIFACT_QUARANTINE_SURFACE_ID",
    "GeneratedArtifactQuarantineEvidence",
    "GeneratedArtifactQuarantineReport",
    "MAX_GENERATED_ARTIFACT_QUARANTINE_EVIDENCE",
    "MAX_GENERATED_ARTIFACT_QUARANTINE_FIELD_BYTES",
    "MAX_GENERATED_ARTIFACT_QUARANTINE_REPORT_BYTES",
    "build_generated_artifact_quarantine_report",
    "dump_generated_artifact_quarantine_report",
    "generated_artifact_quarantine_evidence_from_payload",
    "generated_artifact_quarantine_report_to_dict",
]
