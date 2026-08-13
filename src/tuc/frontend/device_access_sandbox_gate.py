"""Data-only sandbox gate for future device access.

The gate documents the sandbox requirements needed before TUC can ever
consider touching real devices. It deliberately keeps device access,
discovery, enumeration, driver calls, device memory allocation, memory mapping,
direct memory access, kernel launch, generated artifact execution,
subprocesses, and dynamic libraries blocked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.device_access_sandbox_gate_report.v0"
)
DEVICE_ACCESS_SANDBOX_GATE_CONTRACT = "device_access_sandbox_gate.data_only.v0"
DEVICE_ACCESS_SANDBOX_GATE_ARTIFACT_STATUS = "review_gate"
DEVICE_ACCESS_SANDBOX_GATE_ID = "device_access_sandbox_gate"
DEVICE_ACCESS_SANDBOX_SURFACE_ID = "device_access"
DEVICE_ACCESS_SANDBOX_GATE_STATUS = "sandbox_requirements_only"
DEVICE_ACCESS_SANDBOX_ADMISSION_EFFECT = "does_not_admit_device_access"
DEVICE_ACCESS_SANDBOX_EVIDENCE_POLICY = "digest_only"
DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE = (
    "real_triton_integration_admission_gate",
    "triton_jit_execution_sandbox_gate",
    "device_access_sandbox_model",
)
DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS = (
    "device_access_blocked",
    "device_discovery_blocked",
    "device_enumeration_blocked",
    "device_handles_blocked",
    "device_memory_allocation_blocked",
    "device_memory_mapping_blocked",
    "digest_only_evidence",
    "direct_memory_access_blocked",
    "driver_calls_blocked",
    "fail_closed_on_violation",
    "hardware_fingerprints_blocked",
    "kernel_launch_blocked",
    "no_device_access",
    "no_device_discovery",
    "no_device_memory_allocation",
    "no_dynamic_library_loading",
    "no_generated_artifact_execution",
    "no_kernel_launch",
    "no_subprocess_execution",
    "sanitized_diagnostics_only",
)
DEVICE_ACCESS_SANDBOX_BLOCKED_EXECUTION_SURFACES = (
    "device_access",
    "device_discovery",
    "device_memory_allocation",
    "device_memory_mapping",
    "direct_memory_access",
    "driver_api_call",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "kernel_launch",
    "subprocess_execution",
    "triton_jit_execution",
)
DEVICE_ACCESS_SANDBOX_BLOCKED_OUTPUTS = (
    "device_allocation",
    "device_capability_record",
    "device_handle",
    "device_memory_mapping",
    "driver_context",
    "kernel_launch_receipt",
)
MAX_DEVICE_ACCESS_SANDBOX_EVIDENCE = 16
MAX_DEVICE_ACCESS_SANDBOX_FIELD_BYTES = 512
MAX_DEVICE_ACCESS_SANDBOX_REPORT_BYTES = 96 * 1024

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
class DeviceAccessSandboxEvidence:
    """Digest-only prerequisite evidence for device-access sandbox review."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE:
            raise ValueError("device access sandbox evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("device access sandbox required flag must be bool")
        if not self.required:
            raise ValueError("device access sandbox evidence cannot be optional")


@dataclass(frozen=True)
class DeviceAccessSandboxReport:
    """Fail-closed report for the device-access sandbox boundary."""

    evidence: tuple[DeviceAccessSandboxEvidence, ...]
    gate_contract: str = DEVICE_ACCESS_SANDBOX_GATE_CONTRACT
    artifact_status: str = DEVICE_ACCESS_SANDBOX_GATE_ARTIFACT_STATUS
    gate_id: str = DEVICE_ACCESS_SANDBOX_GATE_ID
    surface_id: str = DEVICE_ACCESS_SANDBOX_SURFACE_ID
    evidence_policy: str = DEVICE_ACCESS_SANDBOX_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE
    required_controls: tuple[str, ...] = DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS
    blocked_execution_surfaces: tuple[str, ...] = (
        DEVICE_ACCESS_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = DEVICE_ACCESS_SANDBOX_BLOCKED_OUTPUTS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != DEVICE_ACCESS_SANDBOX_GATE_CONTRACT:
            raise ValueError("device access sandbox contract mismatch")
        if self.artifact_status != DEVICE_ACCESS_SANDBOX_GATE_ARTIFACT_STATUS:
            raise ValueError("device access sandbox artifact status mismatch")
        if self.gate_id != DEVICE_ACCESS_SANDBOX_GATE_ID:
            raise ValueError("device access sandbox gate id mismatch")
        if self.surface_id != DEVICE_ACCESS_SANDBOX_SURFACE_ID:
            raise ValueError("device access sandbox surface id mismatch")
        if self.evidence_policy != DEVICE_ACCESS_SANDBOX_EVIDENCE_POLICY:
            raise ValueError("device access sandbox evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            DEVICE_ACCESS_SANDBOX_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            DEVICE_ACCESS_SANDBOX_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return DEVICE_ACCESS_SANDBOX_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return DEVICE_ACCESS_SANDBOX_ADMISSION_EFFECT

    @property
    def sandbox_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def device_access(self) -> bool:
        return False

    @property
    def device_discovery(self) -> bool:
        return False

    @property
    def device_enumeration(self) -> bool:
        return False

    @property
    def device_handle_emitted(self) -> bool:
        return False

    @property
    def device_memory_allocation(self) -> bool:
        return False

    @property
    def device_memory_mapping(self) -> bool:
        return False

    @property
    def direct_memory_access(self) -> bool:
        return False

    @property
    def driver_api_call(self) -> bool:
        return False

    @property
    def hardware_fingerprint_serialized(self) -> bool:
        return False

    @property
    def kernel_launch(self) -> bool:
        return False

    @property
    def generated_artifact_execution(self) -> bool:
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


def build_device_access_sandbox_report(
    evidence: Iterable[DeviceAccessSandboxEvidence],
) -> DeviceAccessSandboxReport:
    """Build the device-access sandbox report from digest-only evidence."""

    return DeviceAccessSandboxReport(evidence=tuple(evidence))


def device_access_sandbox_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> DeviceAccessSandboxEvidence:
    """Create digest-only device-access sandbox evidence."""

    if not isinstance(payload, Mapping):
        raise TypeError("device access sandbox payload must be mapping")
    return DeviceAccessSandboxEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def device_access_sandbox_report_to_dict(
    report: DeviceAccessSandboxReport,
) -> dict[str, object]:
    """Return stable JSON-ready device-access sandbox evidence."""

    if not isinstance(report, DeviceAccessSandboxReport):
        raise TypeError("device access sandbox report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "device_access": report.device_access,
        "device_discovery": report.device_discovery,
        "device_enumeration": report.device_enumeration,
        "device_handle_emitted": report.device_handle_emitted,
        "device_memory_allocation": report.device_memory_allocation,
        "device_memory_mapping": report.device_memory_mapping,
        "direct_memory_access": report.direct_memory_access,
        "driver_api_call": report.driver_api_call,
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
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "generated_artifact_execution": report.generated_artifact_execution,
        "hardware_fingerprint_serialized": report.hardware_fingerprint_serialized,
        "kernel_launch": report.kernel_launch,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "sandbox_boundary_established": report.sandbox_boundary_established,
        "schema_version": DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION,
        "subprocess_execution": report.subprocess_execution,
        "surface_id": report.surface_id,
        "triton_jit_execution": report.triton_jit_execution,
    }


def dump_device_access_sandbox_report(report: DeviceAccessSandboxReport) -> str:
    """Render stable JSON device-access sandbox evidence."""

    text = json.dumps(
        device_access_sandbox_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_DEVICE_ACCESS_SANDBOX_REPORT_BYTES:
        raise ValueError("device access sandbox report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(evidence: tuple[DeviceAccessSandboxEvidence, ...]) -> None:
    if type(evidence) is not tuple:
        raise TypeError("device access sandbox evidence must be a tuple")
    if len(evidence) > MAX_DEVICE_ACCESS_SANDBOX_EVIDENCE:
        raise ValueError("device access sandbox evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, DeviceAccessSandboxEvidence):
            raise TypeError("device access sandbox evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE:
        raise ValueError("device access sandbox required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError("device access sandbox evidence digests must be unique")


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"device access sandbox {label} must be tuple")
    if values != expected:
        raise ValueError(f"device access sandbox {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"device access sandbox {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"device access sandbox {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"device access sandbox {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_DEVICE_ACCESS_SANDBOX_FIELD_BYTES:
        raise ValueError(f"device access sandbox {label} exceeds field limit")


__all__ = [
    "DEVICE_ACCESS_SANDBOX_ADMISSION_EFFECT",
    "DEVICE_ACCESS_SANDBOX_BLOCKED_EXECUTION_SURFACES",
    "DEVICE_ACCESS_SANDBOX_BLOCKED_OUTPUTS",
    "DEVICE_ACCESS_SANDBOX_EVIDENCE_POLICY",
    "DEVICE_ACCESS_SANDBOX_GATE_ARTIFACT_STATUS",
    "DEVICE_ACCESS_SANDBOX_GATE_CONTRACT",
    "DEVICE_ACCESS_SANDBOX_GATE_ID",
    "DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION",
    "DEVICE_ACCESS_SANDBOX_GATE_STATUS",
    "DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS",
    "DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE",
    "DEVICE_ACCESS_SANDBOX_SURFACE_ID",
    "DeviceAccessSandboxEvidence",
    "DeviceAccessSandboxReport",
    "MAX_DEVICE_ACCESS_SANDBOX_EVIDENCE",
    "MAX_DEVICE_ACCESS_SANDBOX_FIELD_BYTES",
    "MAX_DEVICE_ACCESS_SANDBOX_REPORT_BYTES",
    "build_device_access_sandbox_report",
    "device_access_sandbox_evidence_from_payload",
    "device_access_sandbox_report_to_dict",
    "dump_device_access_sandbox_report",
]
