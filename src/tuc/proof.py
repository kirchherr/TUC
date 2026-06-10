"""Deterministic proof-report metadata for TUC validation artifacts."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

from tuc.runtime import Assignment, PartitionPlan

PROOF_REPORT_SCHEMA_VERSION = "proof-report.v0"
PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.performance_proof_readiness_report.v0"
)
PERFORMANCE_PROOF_BOUNDARY_CONTRACT = "performance_proof_boundary.blocking.v0"
PERFORMANCE_PROOF_REQUIRED_EVIDENCE = (
    "performance_proof_rfc",
    "benchmark_methodology",
    "native_baseline_provenance",
    "versioned_toolchain_environment",
    "workload_scope",
    "correctness_goldens",
    "native_baseline_comparison",
    "leaky_abstraction_report",
    "planner_overhead_report",
    "break_even_workload_size",
    "runtime_plan_goldens",
    "compiler_decision_report_goldens",
    "benchmark_report_schema",
    "benchmark_report_artifacts",
    "executable_backend_security_review",
)
PERFORMANCE_PROOF_BLOCKED_CLAIMS = (
    "native_performance_parity",
    "hundred_percent_native_performance",
    "fixed_vendor_performance_percentage",
    "near_native_without_threshold",
    "planner_overhead_hidden_in_execution_time",
    "transfer_estimates_as_measured_hardware_performance",
    "hardware_specific_hac_ir_knobs",
)
MAX_PROOF_METADATA_STRING_BYTES = 128
MAX_PROOF_BACKENDS = 16
MAX_PERFORMANCE_PROOF_READINESS_REPORT_BYTES = 64 * 1024
MAX_PERFORMANCE_PROOF_READINESS_FIELD_BYTES = 512
MAX_PERFORMANCE_PROOF_READINESS_ISSUES = 128

_PROOF_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_BACKEND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


@dataclass(frozen=True)
class ProofReportMetadata:
    """Stable metadata printed in proof reports before compiler artifacts."""

    proof_id: str
    proof_version: str
    graph_family: str
    backend_set: tuple[str, ...]
    report_schema: str = PROOF_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_proof_identifier(self.report_schema, "report_schema")
        _validate_proof_identifier(self.proof_id, "proof_id")
        _validate_proof_identifier(self.proof_version, "proof_version")
        _validate_proof_identifier(self.graph_family, "graph_family")
        normalized_backends = _normalize_backend_set(self.backend_set)
        object.__setattr__(self, "backend_set", normalized_backends)

    def render_lines(self) -> tuple[str, ...]:
        """Return deterministic text lines for proof report rendering."""

        return (
            f"report_schema: {self.report_schema}",
            f"proof_id: {self.proof_id}",
            f"proof_version: {self.proof_version}",
            f"graph_family: {self.graph_family}",
            f"backend_set: {', '.join(self.backend_set)}",
        )


@dataclass(frozen=True)
class PerformanceProofReadinessEvidence:
    """One explicit evidence flag for native performance proof readiness."""

    evidence_id: str
    present: bool


@dataclass(frozen=True)
class PerformanceProofReadinessIssue:
    """One missing or invalid performance-proof evidence item."""

    evidence_id: str
    message: str


@dataclass(frozen=True)
class PerformanceProofReadinessReport:
    """Review report for future native performance proof claims."""

    proposal_name: str
    boundary_contract: str
    checked_evidence: tuple[PerformanceProofReadinessEvidence, ...]
    blocked_claims: tuple[str, ...]
    issues: tuple[PerformanceProofReadinessIssue, ...]

    @property
    def ready(self) -> bool:
        return not self.issues


class PerformanceProofReadinessError(AssertionError):
    """Raised when a performance proof proposal is not ready."""


def proof_metadata_from_partition_plan(
    *,
    proof_id: str,
    proof_version: str,
    graph_family: str,
    partition_plan: PartitionPlan,
) -> ProofReportMetadata:
    """Build proof metadata from an already validated partition plan."""

    return ProofReportMetadata(
        proof_id=proof_id,
        proof_version=proof_version,
        graph_family=graph_family,
        backend_set=_backend_set_from_assignments(partition_plan.assignments),
    )


def build_performance_proof_readiness_report(
    proposal_name: str,
    evidence: Iterable[PerformanceProofReadinessEvidence],
) -> PerformanceProofReadinessReport:
    """Build a bounded report for future performance-proof readiness."""

    _validate_performance_report_text(proposal_name, "proposal_name")
    evidence_by_id = _normalize_performance_evidence(evidence)
    checked_evidence = tuple(
        PerformanceProofReadinessEvidence(
            evidence_id=evidence_id,
            present=evidence_by_id.get(evidence_id, False),
        )
        for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
    )
    issues = tuple(
        PerformanceProofReadinessIssue(
            evidence_id=item.evidence_id,
            message="required performance proof boundary evidence is missing",
        )
        for item in checked_evidence
        if not item.present
    )
    return PerformanceProofReadinessReport(
        proposal_name=proposal_name,
        boundary_contract=PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        checked_evidence=checked_evidence,
        blocked_claims=PERFORMANCE_PROOF_BLOCKED_CLAIMS,
        issues=issues,
    )


def assert_performance_proof_readiness(
    proposal_name: str,
    evidence: Iterable[PerformanceProofReadinessEvidence],
) -> PerformanceProofReadinessReport:
    """Raise unless a performance proof proposal satisfies every evidence item."""

    report = build_performance_proof_readiness_report(proposal_name, evidence)
    if report.issues:
        lines = [f"performance proof proposal {proposal_name!r} is blocked:"]
        lines.extend(f"- {issue.evidence_id}: {issue.message}" for issue in report.issues)
        raise PerformanceProofReadinessError("\n".join(lines))
    return report


def performance_proof_readiness_report_to_dict(
    report: PerformanceProofReadinessReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible performance readiness report."""

    _validate_performance_readiness_report(report)
    return {
        "blocked_claims": list(report.blocked_claims),
        "boundary_contract": report.boundary_contract,
        "checked_evidence": [
            {
                "evidence_id": item.evidence_id,
                "present": item.present,
            }
            for item in report.checked_evidence
        ],
        "issues": [
            {
                "evidence_id": issue.evidence_id,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "proposal_name": report.proposal_name,
        "ready": report.ready,
        "schema_version": PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION,
    }


def dump_performance_proof_readiness_report(
    report: PerformanceProofReadinessReport,
) -> str:
    """Render a stable review artifact for performance-proof readiness."""

    text = json.dumps(
        performance_proof_readiness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_PERFORMANCE_PROOF_READINESS_REPORT_BYTES:
        raise ValueError("performance proof readiness report exceeds byte limit")
    return text + "\n"


def _backend_set_from_assignments(
    assignments: Iterable[Assignment],
) -> tuple[str, ...]:
    return tuple(sorted({assignment.backend_name for assignment in assignments}))


def _normalize_backend_set(backends: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(backends, tuple):
        raise TypeError("backend_set must be a tuple")
    if not backends:
        raise ValueError("backend_set must not be empty")
    if len(backends) > MAX_PROOF_BACKENDS:
        raise ValueError("backend_set exceeds proof metadata backend limit")
    if len(set(backends)) != len(backends):
        raise ValueError("backend_set must not contain duplicate names")

    normalized: list[str] = []
    for backend in backends:
        if not isinstance(backend, str) or not _BACKEND_NAME_RE.fullmatch(backend):
            raise ValueError("backend_set entries must be safe backend identifiers")
        _validate_string_budget(backend, "backend_set entry")
        normalized.append(backend)
    return tuple(sorted(normalized))


def _normalize_performance_evidence(
    evidence: Iterable[PerformanceProofReadinessEvidence],
) -> dict[str, bool]:
    evidence_by_id: dict[str, bool] = {}
    allowed_ids = frozenset(PERFORMANCE_PROOF_REQUIRED_EVIDENCE)
    for item in tuple(evidence):
        if not isinstance(item, PerformanceProofReadinessEvidence):
            raise TypeError(
                "performance proof readiness evidence must be "
                "PerformanceProofReadinessEvidence"
            )
        _validate_performance_report_text(item.evidence_id, "evidence_id")
        if item.evidence_id not in allowed_ids:
            raise ValueError(f"unsupported performance proof evidence id: {item.evidence_id}")
        if item.evidence_id in evidence_by_id:
            raise ValueError(f"duplicate performance proof evidence id: {item.evidence_id}")
        if type(item.present) is not bool:
            raise TypeError("performance proof evidence present must be bool")
        evidence_by_id[item.evidence_id] = item.present
    return evidence_by_id


def _validate_performance_readiness_report(
    report: PerformanceProofReadinessReport,
) -> None:
    if not isinstance(report, PerformanceProofReadinessReport):
        raise TypeError("performance proof readiness report must be report object")
    _validate_performance_report_text(report.proposal_name, "proposal_name")
    if report.boundary_contract != PERFORMANCE_PROOF_BOUNDARY_CONTRACT:
        raise ValueError(
            "performance proof readiness boundary contract must be "
            f"{PERFORMANCE_PROOF_BOUNDARY_CONTRACT!r}"
        )
    expected_evidence = PERFORMANCE_PROOF_REQUIRED_EVIDENCE
    if tuple(item.evidence_id for item in report.checked_evidence) != expected_evidence:
        raise ValueError("performance proof readiness evidence order must match boundary")
    for item in report.checked_evidence:
        if not isinstance(item, PerformanceProofReadinessEvidence):
            raise TypeError("performance proof checked evidence must be evidence objects")
        if type(item.present) is not bool:
            raise TypeError("performance proof checked evidence present must be bool")
    if tuple(report.blocked_claims) != PERFORMANCE_PROOF_BLOCKED_CLAIMS:
        raise ValueError("performance proof blocked claims must match boundary")
    if len(report.issues) > MAX_PERFORMANCE_PROOF_READINESS_ISSUES:
        raise ValueError("performance proof readiness report exceeds issue limit")
    for issue in report.issues:
        if not isinstance(issue, PerformanceProofReadinessIssue):
            raise TypeError("performance proof readiness issues must be issue objects")
        _validate_performance_report_text(issue.evidence_id, "issue evidence_id")
        _validate_performance_report_text(issue.message, "issue message")


def _validate_proof_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe proof identifier")
    _validate_string_budget(value, label)


def _validate_string_budget(value: str, label: str) -> None:
    if len(value.encode("utf-8")) > MAX_PROOF_METADATA_STRING_BYTES:
        raise ValueError(f"{label} exceeds proof metadata string limit")


def _validate_performance_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_PERFORMANCE_PROOF_READINESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds performance proof readiness field limit")


__all__ = [
    "MAX_PERFORMANCE_PROOF_READINESS_ISSUES",
    "MAX_PROOF_BACKENDS",
    "MAX_PROOF_METADATA_STRING_BYTES",
    "PERFORMANCE_PROOF_BLOCKED_CLAIMS",
    "PERFORMANCE_PROOF_BOUNDARY_CONTRACT",
    "PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION",
    "PERFORMANCE_PROOF_REQUIRED_EVIDENCE",
    "PerformanceProofReadinessError",
    "PerformanceProofReadinessEvidence",
    "PerformanceProofReadinessIssue",
    "PerformanceProofReadinessReport",
    "PROOF_REPORT_SCHEMA_VERSION",
    "ProofReportMetadata",
    "assert_performance_proof_readiness",
    "build_performance_proof_readiness_report",
    "dump_performance_proof_readiness_report",
    "performance_proof_readiness_report_to_dict",
    "proof_metadata_from_partition_plan",
]
