"""Data-only security gate for future native backend execution.

The gate documents the security requirements needed before TUC can ever
consider native backend execution. It deliberately keeps native backend
execution, native plugin ABI loading, backend plugin execution, symbol
resolution, FFI calls, unsafe memory access, generated artifact execution,
device access, kernel launch, subprocesses, and dynamic libraries blocked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.native_backend_execution_security_gate_report.v0"
)
NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT = (
    "native_backend_execution_security_gate.data_only.v0"
)
NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ARTIFACT_STATUS = "review_gate"
NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ID = "native_backend_execution_security_gate"
NATIVE_BACKEND_EXECUTION_SECURITY_SURFACE_ID = "native_backend_execution"
NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS = "security_requirements_only"
NATIVE_BACKEND_EXECUTION_SECURITY_ADMISSION_EFFECT = (
    "does_not_admit_native_backend_execution"
)
NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE_POLICY = "digest_only"
NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE = (
    "real_triton_integration_admission_gate",
    "generated_artifact_quarantine_gate",
    "device_access_sandbox_gate",
    "backend_plugin_lifecycle_policy",
    "native_backend_execution_security_model",
)
NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS = (
    "abi_loading_blocked",
    "artifact_execution_blocked",
    "backend_plugin_execution_blocked",
    "capability_checks_are_data_only",
    "device_access_blocked",
    "digest_only_evidence",
    "dynamic_library_loading_blocked",
    "executable_permissions_blocked",
    "fail_closed_on_violation",
    "ffi_call_blocked",
    "generated_artifact_execution_blocked",
    "maintainer_approval_required",
    "native_backend_execution_blocked",
    "native_plugin_abi_blocked",
    "no_dynamic_library_loading",
    "no_native_backend_execution",
    "no_subprocess_execution",
    "sandbox_required",
    "sanitized_diagnostics_only",
    "symbol_resolution_blocked",
)
NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_EXECUTION_SURFACES = (
    "backend_plugin_execution",
    "device_access",
    "dynamic_library_loading",
    "ffi_call",
    "generated_artifact_execution",
    "kernel_launch",
    "native_backend_execution",
    "native_plugin_abi_loading",
    "subprocess_execution",
    "symbol_resolution",
    "unsafe_memory_access",
)
NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_OUTPUTS = (
    "driver_context",
    "ffi_callable",
    "loaded_symbol",
    "native_backend_handle",
    "native_execution_receipt",
    "native_plugin_handle",
)
MAX_NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE = 16
MAX_NATIVE_BACKEND_EXECUTION_SECURITY_FIELD_BYTES = 512
MAX_NATIVE_BACKEND_EXECUTION_SECURITY_REPORT_BYTES = 96 * 1024

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
class NativeBackendExecutionSecurityEvidence:
    """Digest-only prerequisite evidence for native-backend security review."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE:
            raise ValueError("native backend execution security evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("native backend execution security required flag must be bool")
        if not self.required:
            raise ValueError("native backend execution security evidence cannot be optional")


@dataclass(frozen=True)
class NativeBackendExecutionSecurityReport:
    """Fail-closed report for the native-backend execution security boundary."""

    evidence: tuple[NativeBackendExecutionSecurityEvidence, ...]
    gate_contract: str = NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT
    artifact_status: str = NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ARTIFACT_STATUS
    gate_id: str = NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ID
    surface_id: str = NATIVE_BACKEND_EXECUTION_SECURITY_SURFACE_ID
    evidence_policy: str = NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = (
        NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE
    )
    required_controls: tuple[str, ...] = (
        NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = (
        NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_OUTPUTS
    )

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT:
            raise ValueError("native backend execution security contract mismatch")
        if (
            self.artifact_status
            != NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ARTIFACT_STATUS
        ):
            raise ValueError("native backend execution security artifact status mismatch")
        if self.gate_id != NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ID:
            raise ValueError("native backend execution security gate id mismatch")
        if self.surface_id != NATIVE_BACKEND_EXECUTION_SECURITY_SURFACE_ID:
            raise ValueError("native backend execution security surface id mismatch")
        if self.evidence_policy != NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE_POLICY:
            raise ValueError("native backend execution security evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return NATIVE_BACKEND_EXECUTION_SECURITY_ADMISSION_EFFECT

    @property
    def security_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def native_backend_execution(self) -> bool:
        return False

    @property
    def native_backend_loaded(self) -> bool:
        return False

    @property
    def native_plugin_abi_loading(self) -> bool:
        return False

    @property
    def backend_plugin_execution(self) -> bool:
        return False

    @property
    def native_backend_handle_emitted(self) -> bool:
        return False

    @property
    def symbol_resolution(self) -> bool:
        return False

    @property
    def ffi_call(self) -> bool:
        return False

    @property
    def unsafe_memory_access(self) -> bool:
        return False

    @property
    def dynamic_library_loading(self) -> bool:
        return False

    @property
    def generated_artifact_execution(self) -> bool:
        return False

    @property
    def executable_permission_granted(self) -> bool:
        return False

    @property
    def device_access(self) -> bool:
        return False

    @property
    def kernel_launch(self) -> bool:
        return False

    @property
    def subprocess_execution(self) -> bool:
        return False

    @property
    def capability_claims_from_native_code(self) -> bool:
        return False


def build_native_backend_execution_security_report(
    evidence: Iterable[NativeBackendExecutionSecurityEvidence],
) -> NativeBackendExecutionSecurityReport:
    """Build the native-backend execution security report from digest evidence."""

    return NativeBackendExecutionSecurityReport(evidence=tuple(evidence))


def native_backend_execution_security_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> NativeBackendExecutionSecurityEvidence:
    """Create digest-only native-backend execution security evidence."""

    if not isinstance(payload, Mapping):
        raise TypeError("native backend execution security payload must be mapping")
    return NativeBackendExecutionSecurityEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def native_backend_execution_security_report_to_dict(
    report: NativeBackendExecutionSecurityReport,
) -> dict[str, object]:
    """Return stable JSON-ready native-backend execution security evidence."""

    if not isinstance(report, NativeBackendExecutionSecurityReport):
        raise TypeError("native backend execution security report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_status": report.artifact_status,
        "backend_plugin_execution": report.backend_plugin_execution,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "capability_claims_from_native_code": (
            report.capability_claims_from_native_code
        ),
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
        "ffi_call": report.ffi_call,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "generated_artifact_execution": report.generated_artifact_execution,
        "kernel_launch": report.kernel_launch,
        "native_backend_execution": report.native_backend_execution,
        "native_backend_handle_emitted": report.native_backend_handle_emitted,
        "native_backend_loaded": report.native_backend_loaded,
        "native_plugin_abi_loading": report.native_plugin_abi_loading,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "schema_version": NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION,
        "security_boundary_established": report.security_boundary_established,
        "subprocess_execution": report.subprocess_execution,
        "surface_id": report.surface_id,
        "symbol_resolution": report.symbol_resolution,
        "unsafe_memory_access": report.unsafe_memory_access,
    }


def dump_native_backend_execution_security_report(
    report: NativeBackendExecutionSecurityReport,
) -> str:
    """Render stable JSON native-backend execution security evidence."""

    text = json.dumps(
        native_backend_execution_security_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_NATIVE_BACKEND_EXECUTION_SECURITY_REPORT_BYTES:
        raise ValueError("native backend execution security report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(
    evidence: tuple[NativeBackendExecutionSecurityEvidence, ...],
) -> None:
    if type(evidence) is not tuple:
        raise TypeError("native backend execution security evidence must be a tuple")
    if len(evidence) > MAX_NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE:
        raise ValueError(
            "native backend execution security evidence count exceeds limit"
        )
    for item in evidence:
        if not isinstance(item, NativeBackendExecutionSecurityEvidence):
            raise TypeError("native backend execution security evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE:
        raise ValueError("native backend execution security required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError(
            "native backend execution security evidence digests must be unique"
        )


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"native backend execution security {label} must be tuple")
    if values != expected:
        raise ValueError(f"native backend execution security {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"native backend execution security {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"native backend execution security {label} must be report-safe text"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(
            f"native backend execution security {label} must be report-safe text"
        )
    if len(value.encode("utf-8")) > MAX_NATIVE_BACKEND_EXECUTION_SECURITY_FIELD_BYTES:
        raise ValueError(
            f"native backend execution security {label} exceeds field limit"
        )


__all__ = [
    "MAX_NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE",
    "MAX_NATIVE_BACKEND_EXECUTION_SECURITY_FIELD_BYTES",
    "MAX_NATIVE_BACKEND_EXECUTION_SECURITY_REPORT_BYTES",
    "NATIVE_BACKEND_EXECUTION_SECURITY_ADMISSION_EFFECT",
    "NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_EXECUTION_SURFACES",
    "NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_OUTPUTS",
    "NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE_POLICY",
    "NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ARTIFACT_STATUS",
    "NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT",
    "NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ID",
    "NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION",
    "NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS",
    "NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS",
    "NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE",
    "NATIVE_BACKEND_EXECUTION_SECURITY_SURFACE_ID",
    "NativeBackendExecutionSecurityEvidence",
    "NativeBackendExecutionSecurityReport",
    "build_native_backend_execution_security_report",
    "dump_native_backend_execution_security_report",
    "native_backend_execution_security_evidence_from_payload",
    "native_backend_execution_security_report_to_dict",
]
