"""Data-only sandbox gate for future Triton JIT execution.

The gate documents the sandbox requirements needed before TUC can ever
consider invoking Triton JIT execution. It deliberately keeps Triton JIT,
kernel launch, device access, generated artifact execution, kernel-cache
access, package import, Python import, plugin discovery, network access,
subprocesses, and dynamic libraries blocked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.triton_jit_execution_sandbox_gate_report.v0"
)
TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT = (
    "triton_jit_execution_sandbox_gate.data_only.v0"
)
TRITON_JIT_EXECUTION_SANDBOX_GATE_ARTIFACT_STATUS = "review_gate"
TRITON_JIT_EXECUTION_SANDBOX_GATE_ID = "triton_jit_execution_sandbox_gate"
TRITON_JIT_EXECUTION_SANDBOX_SURFACE_ID = "triton_jit_execution"
TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS = "sandbox_requirements_only"
TRITON_JIT_EXECUTION_SANDBOX_ADMISSION_EFFECT = (
    "does_not_admit_triton_jit_execution"
)
TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE_POLICY = "digest_only"
TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE = (
    "package_import_sandbox_gate",
    "plugin_discovery_allowlist_gate",
    "real_triton_integration_admission_gate",
    "source_ingestion_quarantine_gate",
    "triton_jit_execution_sandbox_model",
)
TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS = (
    "cache_writes_blocked",
    "compilation_outputs_are_metadata_only",
    "device_access_blocked",
    "digest_only_evidence",
    "entrypoints_not_discovered",
    "fail_closed_on_violation",
    "kernel_launch_blocked",
    "no_backend_binary_emission",
    "no_device_access",
    "no_dynamic_library_loading",
    "no_frontend_package_import",
    "no_generated_artifact_execution",
    "no_kernel_cache_access",
    "no_network_access",
    "no_plugin_discovery",
    "no_python_import",
    "no_subprocess_execution",
    "no_triton_jit_execution",
    "sanitized_diagnostics_only",
    "source_buffers_not_executed",
)
TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_EXECUTION_SURFACES = (
    "device_access",
    "dynamic_library_loading",
    "frontend_package_import",
    "generated_artifact_execution",
    "kernel_cache_access",
    "kernel_launch",
    "network_access",
    "plugin_discovery",
    "python_import",
    "subprocess_execution",
    "triton_jit_execution",
)
TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_OUTPUTS = (
    "compiled_kernel",
    "device_binary",
    "executable_kernel",
    "jit_artifact",
    "kernel_cache_entry",
    "kernel_launch_receipt",
)
MAX_TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE = 16
MAX_TRITON_JIT_EXECUTION_SANDBOX_FIELD_BYTES = 512
MAX_TRITON_JIT_EXECUTION_SANDBOX_REPORT_BYTES = 96 * 1024

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
class TritonJitExecutionSandboxEvidence:
    """Digest-only prerequisite evidence for Triton-JIT sandbox review."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE:
            raise ValueError("Triton JIT execution sandbox evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("Triton JIT execution sandbox required flag must be bool")
        if not self.required:
            raise ValueError("Triton JIT execution sandbox evidence cannot be optional")


@dataclass(frozen=True)
class TritonJitExecutionSandboxReport:
    """Fail-closed report for the Triton-JIT execution sandbox boundary."""

    evidence: tuple[TritonJitExecutionSandboxEvidence, ...]
    gate_contract: str = TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT
    artifact_status: str = TRITON_JIT_EXECUTION_SANDBOX_GATE_ARTIFACT_STATUS
    gate_id: str = TRITON_JIT_EXECUTION_SANDBOX_GATE_ID
    surface_id: str = TRITON_JIT_EXECUTION_SANDBOX_SURFACE_ID
    evidence_policy: str = TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = (
        TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE
    )
    required_controls: tuple[str, ...] = (
        TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_OUTPUTS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT:
            raise ValueError("Triton JIT execution sandbox contract mismatch")
        if self.artifact_status != TRITON_JIT_EXECUTION_SANDBOX_GATE_ARTIFACT_STATUS:
            raise ValueError("Triton JIT execution sandbox artifact status mismatch")
        if self.gate_id != TRITON_JIT_EXECUTION_SANDBOX_GATE_ID:
            raise ValueError("Triton JIT execution sandbox gate id mismatch")
        if self.surface_id != TRITON_JIT_EXECUTION_SANDBOX_SURFACE_ID:
            raise ValueError("Triton JIT execution sandbox surface id mismatch")
        if self.evidence_policy != TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE_POLICY:
            raise ValueError("Triton JIT execution sandbox evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return TRITON_JIT_EXECUTION_SANDBOX_ADMISSION_EFFECT

    @property
    def sandbox_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def triton_jit_execution(self) -> bool:
        return False

    @property
    def kernel_launch(self) -> bool:
        return False

    @property
    def generated_artifact_execution(self) -> bool:
        return False

    @property
    def device_access(self) -> bool:
        return False

    @property
    def kernel_cache_access(self) -> bool:
        return False

    @property
    def backend_binary_emitted(self) -> bool:
        return False

    @property
    def compiled_kernel_emitted(self) -> bool:
        return False

    @property
    def source_executed(self) -> bool:
        return False

    @property
    def frontend_package_import(self) -> bool:
        return False

    @property
    def python_import(self) -> bool:
        return False

    @property
    def plugin_discovery(self) -> bool:
        return False

    @property
    def network_access(self) -> bool:
        return False

    @property
    def subprocess_execution(self) -> bool:
        return False

    @property
    def dynamic_library_loading(self) -> bool:
        return False


def build_triton_jit_execution_sandbox_report(
    evidence: Iterable[TritonJitExecutionSandboxEvidence],
) -> TritonJitExecutionSandboxReport:
    """Build the Triton-JIT execution sandbox report from digest-only evidence."""

    return TritonJitExecutionSandboxReport(evidence=tuple(evidence))


def triton_jit_execution_sandbox_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> TritonJitExecutionSandboxEvidence:
    """Create digest-only Triton-JIT execution sandbox evidence."""

    if not isinstance(payload, Mapping):
        raise TypeError("Triton JIT execution sandbox payload must be mapping")
    return TritonJitExecutionSandboxEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def triton_jit_execution_sandbox_report_to_dict(
    report: TritonJitExecutionSandboxReport,
) -> dict[str, object]:
    """Return stable JSON-ready Triton-JIT execution sandbox evidence."""

    if not isinstance(report, TritonJitExecutionSandboxReport):
        raise TypeError("Triton JIT execution sandbox report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_status": report.artifact_status,
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
        "frontend_package_import": report.frontend_package_import,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "generated_artifact_execution": report.generated_artifact_execution,
        "kernel_cache_access": report.kernel_cache_access,
        "kernel_launch": report.kernel_launch,
        "network_access": report.network_access,
        "plugin_discovery": report.plugin_discovery,
        "python_import": report.python_import,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "sandbox_boundary_established": report.sandbox_boundary_established,
        "schema_version": TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION,
        "source_executed": report.source_executed,
        "subprocess_execution": report.subprocess_execution,
        "surface_id": report.surface_id,
        "triton_jit_execution": report.triton_jit_execution,
    }


def dump_triton_jit_execution_sandbox_report(
    report: TritonJitExecutionSandboxReport,
) -> str:
    """Render stable JSON Triton-JIT execution sandbox evidence."""

    text = json.dumps(
        triton_jit_execution_sandbox_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_TRITON_JIT_EXECUTION_SANDBOX_REPORT_BYTES:
        raise ValueError("Triton JIT execution sandbox report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(
    evidence: tuple[TritonJitExecutionSandboxEvidence, ...],
) -> None:
    if type(evidence) is not tuple:
        raise TypeError("Triton JIT execution sandbox evidence must be a tuple")
    if len(evidence) > MAX_TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE:
        raise ValueError("Triton JIT execution sandbox evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, TritonJitExecutionSandboxEvidence):
            raise TypeError("Triton JIT execution sandbox evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE:
        raise ValueError("Triton JIT execution sandbox required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError("Triton JIT execution sandbox evidence digests must be unique")


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"Triton JIT execution sandbox {label} must be tuple")
    if values != expected:
        raise ValueError(f"Triton JIT execution sandbox {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"Triton JIT execution sandbox {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"Triton JIT execution sandbox {label} must be report-safe text"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(
            f"Triton JIT execution sandbox {label} must be report-safe text"
        )
    if len(value.encode("utf-8")) > MAX_TRITON_JIT_EXECUTION_SANDBOX_FIELD_BYTES:
        raise ValueError(f"Triton JIT execution sandbox {label} exceeds field limit")


__all__ = [
    "MAX_TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE",
    "MAX_TRITON_JIT_EXECUTION_SANDBOX_FIELD_BYTES",
    "MAX_TRITON_JIT_EXECUTION_SANDBOX_REPORT_BYTES",
    "TRITON_JIT_EXECUTION_SANDBOX_ADMISSION_EFFECT",
    "TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_EXECUTION_SURFACES",
    "TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_OUTPUTS",
    "TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE_POLICY",
    "TRITON_JIT_EXECUTION_SANDBOX_GATE_ARTIFACT_STATUS",
    "TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT",
    "TRITON_JIT_EXECUTION_SANDBOX_GATE_ID",
    "TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION",
    "TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS",
    "TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS",
    "TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE",
    "TRITON_JIT_EXECUTION_SANDBOX_SURFACE_ID",
    "TritonJitExecutionSandboxEvidence",
    "TritonJitExecutionSandboxReport",
    "build_triton_jit_execution_sandbox_report",
    "dump_triton_jit_execution_sandbox_report",
    "triton_jit_execution_sandbox_evidence_from_payload",
    "triton_jit_execution_sandbox_report_to_dict",
]
