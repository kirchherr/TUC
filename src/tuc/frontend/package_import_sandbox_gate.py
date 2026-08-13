"""Data-only sandbox gate for future frontend package imports.

The gate documents the package-import sandbox requirements needed before TUC
can ever consider importing external frontend packages. It deliberately keeps
frontend package import, Python import, entrypoint discovery, network access,
filesystem access, subprocesses, dynamic libraries, and package code execution
blocked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.package_import_sandbox_gate_report.v0"
)
PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT = "package_import_sandbox_gate.data_only.v0"
PACKAGE_IMPORT_SANDBOX_GATE_ARTIFACT_STATUS = "review_gate"
PACKAGE_IMPORT_SANDBOX_GATE_ID = "package_import_sandbox_gate"
PACKAGE_IMPORT_SANDBOX_SURFACE_ID = "frontend_package_import"
PACKAGE_IMPORT_SANDBOX_GATE_STATUS = "sandbox_requirements_only"
PACKAGE_IMPORT_SANDBOX_ADMISSION_EFFECT = "does_not_admit_frontend_package_import"
PACKAGE_IMPORT_SANDBOX_EVIDENCE_POLICY = "digest_only"
PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE = (
    "external_frontend_package_conformance",
    "package_import_sandbox_model",
    "real_triton_integration_admission_gate",
    "source_ingestion_quarantine_gate",
)
PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS = (
    "deterministic_manifest_only",
    "digest_only_evidence",
    "entrypoints_not_discovered",
    "fail_closed_on_violation",
    "import_side_effects_blocked",
    "network_access_blocked",
    "no_dynamic_library_loading",
    "no_environment_access",
    "no_filesystem_access",
    "no_frontend_package_import",
    "no_plugin_discovery",
    "no_python_import",
    "no_subprocess_execution",
    "package_treated_as_untrusted",
    "sanitized_diagnostics_only",
    "source_intent_fixtures_only",
)
PACKAGE_IMPORT_SANDBOX_BLOCKED_EXECUTION_SURFACES = (
    "device_access",
    "dynamic_library_loading",
    "environment_access",
    "file_system_access",
    "frontend_package_import",
    "network_access",
    "plugin_discovery",
    "python_import",
    "subprocess_execution",
)
PACKAGE_IMPORT_SANDBOX_BLOCKED_OUTPUTS = (
    "import_side_effect",
    "imported_module",
    "package_entrypoint",
    "python_function_object",
    "source_intent_from_import",
)
MAX_PACKAGE_IMPORT_SANDBOX_EVIDENCE = 16
MAX_PACKAGE_IMPORT_SANDBOX_FIELD_BYTES = 512
MAX_PACKAGE_IMPORT_SANDBOX_REPORT_BYTES = 96 * 1024

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
class PackageImportSandboxEvidence:
    """Digest-only prerequisite evidence for package-import sandbox review."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE:
            raise ValueError("package import sandbox evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("package import sandbox required flag must be bool")
        if not self.required:
            raise ValueError("package import sandbox evidence cannot be optional")


@dataclass(frozen=True)
class PackageImportSandboxReport:
    """Fail-closed report for the frontend package-import sandbox boundary."""

    evidence: tuple[PackageImportSandboxEvidence, ...]
    gate_contract: str = PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT
    artifact_status: str = PACKAGE_IMPORT_SANDBOX_GATE_ARTIFACT_STATUS
    gate_id: str = PACKAGE_IMPORT_SANDBOX_GATE_ID
    surface_id: str = PACKAGE_IMPORT_SANDBOX_SURFACE_ID
    evidence_policy: str = PACKAGE_IMPORT_SANDBOX_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE
    required_controls: tuple[str, ...] = PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS
    blocked_execution_surfaces: tuple[str, ...] = (
        PACKAGE_IMPORT_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = PACKAGE_IMPORT_SANDBOX_BLOCKED_OUTPUTS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT:
            raise ValueError("package import sandbox contract mismatch")
        if self.artifact_status != PACKAGE_IMPORT_SANDBOX_GATE_ARTIFACT_STATUS:
            raise ValueError("package import sandbox artifact status mismatch")
        if self.gate_id != PACKAGE_IMPORT_SANDBOX_GATE_ID:
            raise ValueError("package import sandbox gate id mismatch")
        if self.surface_id != PACKAGE_IMPORT_SANDBOX_SURFACE_ID:
            raise ValueError("package import sandbox surface id mismatch")
        if self.evidence_policy != PACKAGE_IMPORT_SANDBOX_EVIDENCE_POLICY:
            raise ValueError("package import sandbox evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            PACKAGE_IMPORT_SANDBOX_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            PACKAGE_IMPORT_SANDBOX_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return PACKAGE_IMPORT_SANDBOX_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return PACKAGE_IMPORT_SANDBOX_ADMISSION_EFFECT

    @property
    def sandbox_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def frontend_package_import(self) -> bool:
        return False

    @property
    def python_import(self) -> bool:
        return False

    @property
    def package_code_execution(self) -> bool:
        return False

    @property
    def external_package_loaded(self) -> bool:
        return False

    @property
    def entrypoint_discovery(self) -> bool:
        return False

    @property
    def plugin_discovery(self) -> bool:
        return False

    @property
    def network_access(self) -> bool:
        return False

    @property
    def filesystem_access(self) -> bool:
        return False

    @property
    def environment_access(self) -> bool:
        return False

    @property
    def subprocess_execution(self) -> bool:
        return False

    @property
    def dynamic_library_loading(self) -> bool:
        return False

    @property
    def source_intent_from_import(self) -> bool:
        return False


def build_package_import_sandbox_report(
    evidence: Iterable[PackageImportSandboxEvidence],
) -> PackageImportSandboxReport:
    """Build the package-import sandbox report from digest-only evidence."""

    return PackageImportSandboxReport(evidence=tuple(evidence))


def package_import_sandbox_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> PackageImportSandboxEvidence:
    """Create digest-only package-import sandbox evidence."""

    if not isinstance(payload, Mapping):
        raise TypeError("package import sandbox evidence payload must be mapping")
    return PackageImportSandboxEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def package_import_sandbox_report_to_dict(
    report: PackageImportSandboxReport,
) -> dict[str, object]:
    """Return stable JSON-ready package-import sandbox evidence."""

    if not isinstance(report, PackageImportSandboxReport):
        raise TypeError("package import sandbox report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "dynamic_library_loading": report.dynamic_library_loading,
        "entrypoint_discovery": report.entrypoint_discovery,
        "environment_access": report.environment_access,
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
        "external_package_loaded": report.external_package_loaded,
        "filesystem_access": report.filesystem_access,
        "frontend_package_import": report.frontend_package_import,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "network_access": report.network_access,
        "package_code_execution": report.package_code_execution,
        "plugin_discovery": report.plugin_discovery,
        "python_import": report.python_import,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "sandbox_boundary_established": report.sandbox_boundary_established,
        "schema_version": PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION,
        "source_intent_from_import": report.source_intent_from_import,
        "subprocess_execution": report.subprocess_execution,
        "surface_id": report.surface_id,
    }


def dump_package_import_sandbox_report(report: PackageImportSandboxReport) -> str:
    """Render stable JSON package-import sandbox evidence."""

    text = json.dumps(
        package_import_sandbox_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_PACKAGE_IMPORT_SANDBOX_REPORT_BYTES:
        raise ValueError("package import sandbox report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(evidence: tuple[PackageImportSandboxEvidence, ...]) -> None:
    if type(evidence) is not tuple:
        raise TypeError("package import sandbox evidence must be a tuple")
    if len(evidence) > MAX_PACKAGE_IMPORT_SANDBOX_EVIDENCE:
        raise ValueError("package import sandbox evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, PackageImportSandboxEvidence):
            raise TypeError("package import sandbox evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE:
        raise ValueError("package import sandbox required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError("package import sandbox evidence digests must be unique")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"package import sandbox {label} must be tuple")
    if values != expected:
        raise ValueError(f"package import sandbox {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"package import sandbox {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"package import sandbox {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"package import sandbox {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_PACKAGE_IMPORT_SANDBOX_FIELD_BYTES:
        raise ValueError(f"package import sandbox {label} exceeds field limit")


__all__ = [
    "MAX_PACKAGE_IMPORT_SANDBOX_EVIDENCE",
    "MAX_PACKAGE_IMPORT_SANDBOX_FIELD_BYTES",
    "MAX_PACKAGE_IMPORT_SANDBOX_REPORT_BYTES",
    "PACKAGE_IMPORT_SANDBOX_ADMISSION_EFFECT",
    "PACKAGE_IMPORT_SANDBOX_BLOCKED_EXECUTION_SURFACES",
    "PACKAGE_IMPORT_SANDBOX_BLOCKED_OUTPUTS",
    "PACKAGE_IMPORT_SANDBOX_EVIDENCE_POLICY",
    "PACKAGE_IMPORT_SANDBOX_GATE_ARTIFACT_STATUS",
    "PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT",
    "PACKAGE_IMPORT_SANDBOX_GATE_ID",
    "PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION",
    "PACKAGE_IMPORT_SANDBOX_GATE_STATUS",
    "PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS",
    "PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE",
    "PACKAGE_IMPORT_SANDBOX_SURFACE_ID",
    "PackageImportSandboxEvidence",
    "PackageImportSandboxReport",
    "build_package_import_sandbox_report",
    "dump_package_import_sandbox_report",
    "package_import_sandbox_evidence_from_payload",
    "package_import_sandbox_report_to_dict",
]
