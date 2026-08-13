"""Data-only readiness report for future real Triton integration.

The report prepares the next roadmap milestone without opening a Triton source
or execution surface. It records which review prerequisites exist and which are
still missing before broader Triton-facing integration can be considered.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.triton_integration_readiness_report.v0"
)
TRITON_INTEGRATION_READINESS_CONTRACT = (
    "triton_integration_readiness.data_only.v0"
)
TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS = "diagnostic_only"
TRITON_INTEGRATION_READINESS_TARGET = "real_triton_integration_phase_epsilon"
TRITON_INTEGRATION_READINESS_STATUS_READY = "ready"
TRITON_INTEGRATION_READINESS_STATUS_NOT_READY = "not_ready"
TRITON_INTEGRATION_READINESS_PREREQUISITE_STATUSES = (
    "blocked_by_policy",
    "missing",
    "satisfied",
)
TRITON_INTEGRATION_READINESS_BLOCKED_EXECUTION_SURFACES = (
    "bytecode_compilation",
    "decorator_evaluation",
    "device_access",
    "direct_compute_graph_from_source",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "python_function_object_inspection",
    "python_import",
    "subprocess_execution",
)
TRITON_INTEGRATION_READINESS_DEFAULT_ISSUES = (
    "triton_integration_prerequisites_incomplete",
    "direct_triton_source_ingestion_blocked",
    "triton_jit_execution_blocked",
)
MAX_TRITON_INTEGRATION_READINESS_PREREQUISITES = 128
MAX_TRITON_INTEGRATION_READINESS_FIELD_BYTES = 512
MAX_TRITON_INTEGRATION_READINESS_REPORT_BYTES = 64 * 1024

_REPORT_TEXT_RE = re.compile(r"^(not_supplied|[A-Za-z][A-Za-z0-9_.-]*)$")
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
        "url",
    }
)


@dataclass(frozen=True)
class TritonIntegrationReadinessPrerequisite:
    """One data-only prerequisite for future Triton-facing integration."""

    prerequisite_id: str
    status: str
    evidence_id: str
    required_for_readiness: bool = True


@dataclass(frozen=True)
class TritonIntegrationReadinessReport:
    """Readiness state for the next real Triton integration milestone."""

    proposal_name: str
    prerequisites: tuple[TritonIntegrationReadinessPrerequisite, ...]
    issues: tuple[str, ...]

    @property
    def readiness_ready(self) -> bool:
        return all(
            not item.required_for_readiness or item.status == "satisfied"
            for item in self.prerequisites
        )

    @property
    def integration_status(self) -> str:
        if self.readiness_ready:
            return TRITON_INTEGRATION_READINESS_STATUS_READY
        return TRITON_INTEGRATION_READINESS_STATUS_NOT_READY

    @property
    def satisfied_prerequisite_count(self) -> int:
        return sum(1 for item in self.prerequisites if item.status == "satisfied")

    @property
    def missing_prerequisite_count(self) -> int:
        return sum(1 for item in self.prerequisites if item.status == "missing")

    @property
    def blocked_prerequisite_count(self) -> int:
        return sum(1 for item in self.prerequisites if item.status == "blocked_by_policy")


def build_triton_integration_readiness_report(
    proposal_name: str,
    prerequisites: Iterable[TritonIntegrationReadinessPrerequisite],
) -> TritonIntegrationReadinessReport:
    """Build a bounded data-only Triton integration readiness report."""

    _validate_report_text(proposal_name, "proposal_name")
    normalized = _normalize_prerequisites(prerequisites)
    issues: list[str] = []
    if any(
        item.required_for_readiness and item.status != "satisfied"
        for item in normalized
    ):
        issues.append("triton_integration_prerequisites_incomplete")
    if any(
        item.prerequisite_id == "direct_triton_source_ingestion"
        and item.status == "blocked_by_policy"
        for item in normalized
    ):
        issues.append("direct_triton_source_ingestion_blocked")
    if any(
        item.prerequisite_id == "triton_jit_execution_permission"
        and item.status == "blocked_by_policy"
        for item in normalized
    ):
        issues.append("triton_jit_execution_blocked")
    return TritonIntegrationReadinessReport(
        proposal_name=proposal_name,
        prerequisites=normalized,
        issues=tuple(issues),
    )


def triton_integration_readiness_report_to_dict(
    report: TritonIntegrationReadinessReport,
) -> dict[str, object]:
    """Return a stable mapping for JSON serialization."""

    _validate_report(report)
    return {
        "artifact_status": TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS,
        "blocked_execution_surfaces": list(
            TRITON_INTEGRATION_READINESS_BLOCKED_EXECUTION_SURFACES
        ),
        "blocked_prerequisite_count": report.blocked_prerequisite_count,
        "direct_triton_source_ingestion": False,
        "integration_status": report.integration_status,
        "integration_target": TRITON_INTEGRATION_READINESS_TARGET,
        "issues": list(report.issues),
        "missing_prerequisite_count": report.missing_prerequisite_count,
        "prerequisites": [
            {
                "evidence_id": item.evidence_id,
                "prerequisite_id": item.prerequisite_id,
                "required_for_readiness": item.required_for_readiness,
                "status": item.status,
            }
            for item in report.prerequisites
        ],
        "proposal_name": report.proposal_name,
        "readiness_contract": TRITON_INTEGRATION_READINESS_CONTRACT,
        "readiness_ready": report.readiness_ready,
        "schema_version": TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION,
        "satisfied_prerequisite_count": report.satisfied_prerequisite_count,
        "triton_jit_execution": False,
    }


def dump_triton_integration_readiness_report(
    report: TritonIntegrationReadinessReport,
) -> str:
    """Render a stable JSON Triton integration readiness report."""

    text = json.dumps(
        triton_integration_readiness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_TRITON_INTEGRATION_READINESS_REPORT_BYTES:
        raise ValueError("triton integration readiness report exceeds byte limit")
    return f"{text}\n"


def _normalize_prerequisites(
    prerequisites: Iterable[TritonIntegrationReadinessPrerequisite],
) -> tuple[TritonIntegrationReadinessPrerequisite, ...]:
    normalized = tuple(prerequisites)
    if len(normalized) > MAX_TRITON_INTEGRATION_READINESS_PREREQUISITES:
        raise ValueError("triton integration readiness prerequisite count exceeds limit")
    seen: set[str] = set()
    for item in normalized:
        if not isinstance(item, TritonIntegrationReadinessPrerequisite):
            raise TypeError(
                "readiness prerequisites must be TritonIntegrationReadinessPrerequisite"
            )
        _validate_report_text(item.prerequisite_id, "prerequisite_id")
        if item.prerequisite_id in seen:
            raise ValueError("duplicate triton integration readiness prerequisite")
        seen.add(item.prerequisite_id)
        if item.status not in TRITON_INTEGRATION_READINESS_PREREQUISITE_STATUSES:
            raise ValueError("unsupported triton integration readiness status")
        _validate_report_text(item.evidence_id, "evidence_id")
        if not isinstance(item.required_for_readiness, bool):
            raise TypeError("required_for_readiness must be boolean")
    return normalized


def _validate_report(report: TritonIntegrationReadinessReport) -> None:
    if not isinstance(report, TritonIntegrationReadinessReport):
        raise TypeError("triton integration readiness report must be report object")
    _validate_report_text(report.proposal_name, "proposal_name")
    _normalize_prerequisites(report.prerequisites)
    for issue in report.issues:
        _validate_report_text(issue, "issue")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe triton integration identifier")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"{label} must be a safe triton integration identifier")
    if len(value.encode("utf-8")) > MAX_TRITON_INTEGRATION_READINESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds triton integration readiness limit")


__all__ = [
    "MAX_TRITON_INTEGRATION_READINESS_FIELD_BYTES",
    "MAX_TRITON_INTEGRATION_READINESS_PREREQUISITES",
    "MAX_TRITON_INTEGRATION_READINESS_REPORT_BYTES",
    "TRITON_INTEGRATION_READINESS_ARTIFACT_STATUS",
    "TRITON_INTEGRATION_READINESS_BLOCKED_EXECUTION_SURFACES",
    "TRITON_INTEGRATION_READINESS_CONTRACT",
    "TRITON_INTEGRATION_READINESS_DEFAULT_ISSUES",
    "TRITON_INTEGRATION_READINESS_PREREQUISITE_STATUSES",
    "TRITON_INTEGRATION_READINESS_REPORT_SCHEMA_VERSION",
    "TRITON_INTEGRATION_READINESS_STATUS_NOT_READY",
    "TRITON_INTEGRATION_READINESS_STATUS_READY",
    "TRITON_INTEGRATION_READINESS_TARGET",
    "TritonIntegrationReadinessPrerequisite",
    "TritonIntegrationReadinessReport",
    "build_triton_integration_readiness_report",
    "dump_triton_integration_readiness_report",
    "triton_integration_readiness_report_to_dict",
]