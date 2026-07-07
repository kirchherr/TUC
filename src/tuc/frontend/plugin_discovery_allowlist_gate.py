"""Data-only allowlist gate for future frontend plugin discovery.

The gate documents the allowlist requirements needed before TUC can ever
consider discovering frontend plugins. It deliberately keeps plugin discovery,
entrypoint discovery, registry scans, filesystem scans, package import, Python
import, plugin code execution, network access, subprocesses, dynamic libraries,
and device access blocked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.plugin_discovery_allowlist_gate_report.v0"
)
PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT = (
    "plugin_discovery_allowlist_gate.data_only.v0"
)
PLUGIN_DISCOVERY_ALLOWLIST_GATE_ARTIFACT_STATUS = "review_gate"
PLUGIN_DISCOVERY_ALLOWLIST_GATE_ID = "plugin_discovery_allowlist_gate"
PLUGIN_DISCOVERY_ALLOWLIST_SURFACE_ID = "plugin_discovery"
PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS = "allowlist_requirements_only"
PLUGIN_DISCOVERY_ALLOWLIST_ADMISSION_EFFECT = "does_not_admit_plugin_discovery"
PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE_POLICY = "digest_only"
PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE = (
    "external_frontend_package_conformance",
    "package_import_sandbox_gate",
    "plugin_discovery_allowlist_model",
    "real_triton_integration_admission_gate",
)
PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS = (
    "allowlist_entries_are_manifest_ids",
    "capability_claims_are_data_only",
    "digest_only_evidence",
    "entrypoints_not_discovered",
    "fail_closed_on_violation",
    "no_device_access",
    "no_dynamic_library_loading",
    "no_entrypoint_discovery",
    "no_filesystem_scan",
    "no_frontend_package_import",
    "no_network_access",
    "no_plugin_code_execution",
    "no_plugin_discovery",
    "no_python_import",
    "no_registry_scan",
    "no_subprocess_execution",
    "plugin_treated_as_untrusted",
    "sanitized_diagnostics_only",
)
PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_EXECUTION_SURFACES = (
    "device_access",
    "dynamic_library_loading",
    "entrypoint_discovery",
    "file_system_access",
    "frontend_package_import",
    "network_access",
    "plugin_code_execution",
    "plugin_discovery",
    "python_import",
    "registry_scan",
    "subprocess_execution",
)
PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_OUTPUTS = (
    "discovered_plugin",
    "entrypoint_record",
    "imported_module",
    "plugin_capability_from_code",
    "plugin_handle",
    "plugin_registry_record",
)
MAX_PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE = 16
MAX_PLUGIN_DISCOVERY_ALLOWLIST_FIELD_BYTES = 512
MAX_PLUGIN_DISCOVERY_ALLOWLIST_REPORT_BYTES = 96 * 1024

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
class PluginDiscoveryAllowlistEvidence:
    """Digest-only prerequisite evidence for plugin-discovery allowlist review."""

    evidence_id: str
    evidence_digest: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        if self.evidence_id not in PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE:
            raise ValueError("plugin discovery allowlist evidence is not accepted")
        _validate_sha256(self.evidence_digest, "evidence_digest")
        if type(self.required) is not bool:
            raise TypeError("plugin discovery allowlist required flag must be bool")
        if not self.required:
            raise ValueError("plugin discovery allowlist evidence cannot be optional")


@dataclass(frozen=True)
class PluginDiscoveryAllowlistReport:
    """Fail-closed report for the frontend plugin-discovery allowlist boundary."""

    evidence: tuple[PluginDiscoveryAllowlistEvidence, ...]
    gate_contract: str = PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT
    artifact_status: str = PLUGIN_DISCOVERY_ALLOWLIST_GATE_ARTIFACT_STATUS
    gate_id: str = PLUGIN_DISCOVERY_ALLOWLIST_GATE_ID
    surface_id: str = PLUGIN_DISCOVERY_ALLOWLIST_SURFACE_ID
    evidence_policy: str = PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE_POLICY
    required_evidence_ids: tuple[str, ...] = PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE
    required_controls: tuple[str, ...] = PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS
    blocked_execution_surfaces: tuple[str, ...] = (
        PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_EXECUTION_SURFACES
    )
    blocked_outputs: tuple[str, ...] = PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_OUTPUTS

    def __post_init__(self) -> None:
        _validate_evidence(self.evidence)
        if self.gate_contract != PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT:
            raise ValueError("plugin discovery allowlist contract mismatch")
        if self.artifact_status != PLUGIN_DISCOVERY_ALLOWLIST_GATE_ARTIFACT_STATUS:
            raise ValueError("plugin discovery allowlist artifact status mismatch")
        if self.gate_id != PLUGIN_DISCOVERY_ALLOWLIST_GATE_ID:
            raise ValueError("plugin discovery allowlist gate id mismatch")
        if self.surface_id != PLUGIN_DISCOVERY_ALLOWLIST_SURFACE_ID:
            raise ValueError("plugin discovery allowlist surface id mismatch")
        if self.evidence_policy != PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE_POLICY:
            raise ValueError("plugin discovery allowlist evidence policy mismatch")
        _validate_exact_tuple(
            self.required_evidence_ids,
            PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE,
            "required_evidence_ids",
        )
        _validate_exact_tuple(
            self.required_controls,
            PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.blocked_outputs,
            PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )

    @property
    def gate_status(self) -> str:
        return PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS

    @property
    def admission_effect(self) -> str:
        return PLUGIN_DISCOVERY_ALLOWLIST_ADMISSION_EFFECT

    @property
    def allowlist_boundary_established(self) -> bool:
        return True

    @property
    def all_required_evidence_present(self) -> bool:
        return tuple(item.evidence_id for item in self.evidence) == (
            PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def required_control_count(self) -> int:
        return len(self.required_controls)

    @property
    def plugin_discovery(self) -> bool:
        return False

    @property
    def entrypoint_discovery(self) -> bool:
        return False

    @property
    def registry_scan(self) -> bool:
        return False

    @property
    def filesystem_scan(self) -> bool:
        return False

    @property
    def frontend_package_import(self) -> bool:
        return False

    @property
    def python_import(self) -> bool:
        return False

    @property
    def plugin_code_execution(self) -> bool:
        return False

    @property
    def plugin_loaded(self) -> bool:
        return False

    @property
    def capability_claims_from_code(self) -> bool:
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

    @property
    def device_access(self) -> bool:
        return False


def build_plugin_discovery_allowlist_report(
    evidence: Iterable[PluginDiscoveryAllowlistEvidence],
) -> PluginDiscoveryAllowlistReport:
    """Build the plugin-discovery allowlist report from digest-only evidence."""

    return PluginDiscoveryAllowlistReport(evidence=tuple(evidence))


def plugin_discovery_allowlist_evidence_from_payload(
    evidence_id: str,
    payload: Mapping[str, object],
) -> PluginDiscoveryAllowlistEvidence:
    """Create digest-only plugin-discovery allowlist evidence."""

    if not isinstance(payload, Mapping):
        raise TypeError("plugin discovery allowlist evidence payload must be mapping")
    return PluginDiscoveryAllowlistEvidence(
        evidence_id=evidence_id,
        evidence_digest=_digest_payload(dict(payload)),
    )


def plugin_discovery_allowlist_report_to_dict(
    report: PluginDiscoveryAllowlistReport,
) -> dict[str, object]:
    """Return stable JSON-ready plugin-discovery allowlist evidence."""

    if not isinstance(report, PluginDiscoveryAllowlistReport):
        raise TypeError("plugin discovery allowlist report must be report")
    return {
        "admission_effect": report.admission_effect,
        "all_required_evidence_present": report.all_required_evidence_present,
        "allowlist_boundary_established": report.allowlist_boundary_established,
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "capability_claims_from_code": report.capability_claims_from_code,
        "device_access": report.device_access,
        "dynamic_library_loading": report.dynamic_library_loading,
        "entrypoint_discovery": report.entrypoint_discovery,
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
        "filesystem_scan": report.filesystem_scan,
        "frontend_package_import": report.frontend_package_import,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_status": report.gate_status,
        "network_access": report.network_access,
        "plugin_code_execution": report.plugin_code_execution,
        "plugin_discovery": report.plugin_discovery,
        "plugin_loaded": report.plugin_loaded,
        "python_import": report.python_import,
        "registry_scan": report.registry_scan,
        "required_control_count": report.required_control_count,
        "required_controls": list(report.required_controls),
        "required_evidence_ids": list(report.required_evidence_ids),
        "schema_version": PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION,
        "subprocess_execution": report.subprocess_execution,
        "surface_id": report.surface_id,
    }


def dump_plugin_discovery_allowlist_report(
    report: PluginDiscoveryAllowlistReport,
) -> str:
    """Render stable JSON plugin-discovery allowlist evidence."""

    text = json.dumps(
        plugin_discovery_allowlist_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_PLUGIN_DISCOVERY_ALLOWLIST_REPORT_BYTES:
        raise ValueError("plugin discovery allowlist report exceeds byte limit")
    return f"{text}\n"


def _validate_evidence(
    evidence: tuple[PluginDiscoveryAllowlistEvidence, ...],
) -> None:
    if type(evidence) is not tuple:
        raise TypeError("plugin discovery allowlist evidence must be a tuple")
    if len(evidence) > MAX_PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE:
        raise ValueError("plugin discovery allowlist evidence count exceeds limit")
    for item in evidence:
        if not isinstance(item, PluginDiscoveryAllowlistEvidence):
            raise TypeError("plugin discovery allowlist evidence must be evidence")
    evidence_ids = tuple(item.evidence_id for item in evidence)
    if evidence_ids != PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE:
        raise ValueError("plugin discovery allowlist required evidence mismatch")
    evidence_digests = tuple(item.evidence_digest for item in evidence)
    if len(evidence_digests) != len(set(evidence_digests)):
        raise ValueError("plugin discovery allowlist evidence digests must be unique")


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"plugin discovery allowlist {label} must be tuple")
    if values != expected:
        raise ValueError(f"plugin discovery allowlist {label} mismatch")
    for value in values:
        _validate_report_text(value, label)


def _digest_payload(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"plugin discovery allowlist {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"plugin discovery allowlist {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"plugin discovery allowlist {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_PLUGIN_DISCOVERY_ALLOWLIST_FIELD_BYTES:
        raise ValueError(f"plugin discovery allowlist {label} exceeds field limit")


__all__ = [
    "MAX_PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE",
    "MAX_PLUGIN_DISCOVERY_ALLOWLIST_FIELD_BYTES",
    "MAX_PLUGIN_DISCOVERY_ALLOWLIST_REPORT_BYTES",
    "PLUGIN_DISCOVERY_ALLOWLIST_ADMISSION_EFFECT",
    "PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_EXECUTION_SURFACES",
    "PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_OUTPUTS",
    "PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE_POLICY",
    "PLUGIN_DISCOVERY_ALLOWLIST_GATE_ARTIFACT_STATUS",
    "PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT",
    "PLUGIN_DISCOVERY_ALLOWLIST_GATE_ID",
    "PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION",
    "PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS",
    "PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS",
    "PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE",
    "PLUGIN_DISCOVERY_ALLOWLIST_SURFACE_ID",
    "PluginDiscoveryAllowlistEvidence",
    "PluginDiscoveryAllowlistReport",
    "build_plugin_discovery_allowlist_report",
    "dump_plugin_discovery_allowlist_report",
    "plugin_discovery_allowlist_evidence_from_payload",
    "plugin_discovery_allowlist_report_to_dict",
]
