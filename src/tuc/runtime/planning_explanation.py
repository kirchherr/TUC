"""Data-only explanation reports for runtime partition plans."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.partitioning import CandidateScore, PartitionPlan

RUNTIME_PLANNING_EXPLANATION_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_planning_explanation_report.v0"
)
RUNTIME_PLANNING_EXPLANATION_CONTRACT = "runtime_planning_explanation.data_only.v0"
RUNTIME_PLANNING_EXPLANATION_STATUSES = frozenset({"passed", "failed"})
RUNTIME_PLANNING_EXPLANATION_CANDIDATE_SCORE_MODES = frozenset(
    {"not_recorded", "recorded"}
)
RUNTIME_PLANNING_EXPLANATION_SELECTION_KINDS = frozenset(
    {
        "fallback",
        "manual_override_prefer",
        "manual_override_require",
        "preferred_for",
        "supported",
        "unknown",
    }
)
MAX_RUNTIME_PLANNING_EXPLANATION_STEPS = 256
MAX_RUNTIME_PLANNING_EXPLANATION_ISSUES = 128
MAX_RUNTIME_PLANNING_EXPLANATION_FIELD_BYTES = 512
MAX_RUNTIME_PLANNING_EXPLANATION_REASON_BYTES = 2048
MAX_RUNTIME_PLANNING_EXPLANATION_REPORT_BYTES = 64 * 1024

_EXPLANATION_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_EXPLANATION_REASON_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:=;,-]*$")
_FORBIDDEN_EXPLANATION_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimePlanningExplanationStep:
    """One explainable runtime placement step."""

    operation_name: str
    backend_name: str
    selection_kind: str
    reason: str
    memory_domain: MemoryDomainKind
    produced_layout: LayoutKind
    transfer_bytes: int
    layout_conversion_bytes: int
    candidate_score_count: int
    selected_candidate_score_count: int
    rejected_candidate_score_count: int

    def __post_init__(self) -> None:
        _validate_explanation_text(self.operation_name, "operation_name")
        _validate_explanation_text(self.backend_name, "backend_name")
        if self.selection_kind not in RUNTIME_PLANNING_EXPLANATION_SELECTION_KINDS:
            raise ValueError("runtime planning explanation selection kind is unsupported")
        _validate_reason(self.reason, "reason")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("runtime planning explanation memory_domain must be MemoryDomainKind")
        if not isinstance(self.produced_layout, LayoutKind):
            raise TypeError("runtime planning explanation produced_layout must be LayoutKind")
        _validate_non_negative_int(self.transfer_bytes, "transfer_bytes")
        _validate_non_negative_int(
            self.layout_conversion_bytes,
            "layout_conversion_bytes",
        )
        _validate_non_negative_int(self.candidate_score_count, "candidate_score_count")
        _validate_non_negative_int(
            self.selected_candidate_score_count,
            "selected_candidate_score_count",
        )
        _validate_non_negative_int(
            self.rejected_candidate_score_count,
            "rejected_candidate_score_count",
        )
        if self.candidate_score_count != (
            self.selected_candidate_score_count + self.rejected_candidate_score_count
        ):
            raise ValueError("runtime planning explanation candidate counts mismatch")

    @property
    def movement_bytes(self) -> int:
        """Return total explicit movement bytes for this operation."""

        return self.transfer_bytes + self.layout_conversion_bytes


@dataclass(frozen=True)
class RuntimePlanningExplanationIssue:
    """One derived runtime planning explanation issue."""

    operation_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_explanation_text(self.operation_name, "issue operation_name")
        _validate_explanation_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimePlanningExplanationReport:
    """Deterministic explanation summary for one runtime partition plan."""

    graph_name: str
    steps: tuple[RuntimePlanningExplanationStep, ...]
    transfer_edge_count: int
    layout_conversion_count: int
    total_transfer_bytes: int
    total_layout_conversion_bytes: int
    total_data_movement_bytes: int
    candidate_score_mode: str
    issues: tuple[RuntimePlanningExplanationIssue, ...]
    explanation_contract: str = RUNTIME_PLANNING_EXPLANATION_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_explanation_text(self.graph_name, "graph_name")
        if self.explanation_contract != RUNTIME_PLANNING_EXPLANATION_CONTRACT:
            raise ValueError("runtime planning explanation contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime planning explanation blocked surfaces changed")
        if type(self.steps) is not tuple:
            raise TypeError("runtime planning explanation steps must be a tuple")
        if len(self.steps) > MAX_RUNTIME_PLANNING_EXPLANATION_STEPS:
            raise ValueError("runtime planning explanation step count exceeds limit")
        for step in self.steps:
            if not isinstance(step, RuntimePlanningExplanationStep):
                raise TypeError("runtime planning explanation steps must be step objects")
        _validate_non_negative_int(self.transfer_edge_count, "transfer_edge_count")
        _validate_non_negative_int(
            self.layout_conversion_count,
            "layout_conversion_count",
        )
        _validate_non_negative_int(self.total_transfer_bytes, "total_transfer_bytes")
        _validate_non_negative_int(
            self.total_layout_conversion_bytes,
            "total_layout_conversion_bytes",
        )
        _validate_non_negative_int(
            self.total_data_movement_bytes,
            "total_data_movement_bytes",
        )
        if self.total_data_movement_bytes != (
            self.total_transfer_bytes + self.total_layout_conversion_bytes
        ):
            raise ValueError("runtime planning explanation movement totals mismatch")
        if self.candidate_score_mode not in (
            RUNTIME_PLANNING_EXPLANATION_CANDIDATE_SCORE_MODES
        ):
            raise ValueError("runtime planning explanation candidate score mode unsupported")
        if type(self.issues) is not tuple:
            raise TypeError("runtime planning explanation issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_PLANNING_EXPLANATION_ISSUES:
            raise ValueError("runtime planning explanation issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimePlanningExplanationIssue):
                raise TypeError("runtime planning explanation issues must be issue objects")
        if self.issues != _derive_explanation_issues(self.steps):
            raise ValueError("runtime planning explanation issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether every placement step has a known explanation."""

        return not self.issues

    @property
    def explanation_status(self) -> str:
        """Return the report-level explanation status."""

        return "passed" if self.passed else "failed"

    @property
    def operation_count(self) -> int:
        """Return the number of explained operations."""

        return len(self.steps)

    @property
    def backend_sequence(self) -> tuple[str, ...]:
        """Return the backend sequence in operation order."""

        return tuple(step.backend_name for step in self.steps)

    @property
    def selection_kinds(self) -> tuple[str, ...]:
        """Return observed selection kinds in deterministic order."""

        return tuple(sorted({step.selection_kind for step in self.steps}))

    @property
    def fallback_count(self) -> int:
        """Return the number of fallback assignments."""

        return sum(1 for step in self.steps if step.selection_kind == "fallback")

    @property
    def candidate_score_count(self) -> int:
        """Return the total number of candidate score records."""

        return sum(step.candidate_score_count for step in self.steps)


class RuntimePlanningExplanationError(AssertionError):
    """Raised when runtime planning explanations fail."""


def build_runtime_planning_explanation_report(
    partition_plan: PartitionPlan,
) -> RuntimePlanningExplanationReport:
    """Build a data-only explanation summary from a partition plan."""

    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("partition_plan must be PartitionPlan")

    scores_by_operation = _candidate_scores_by_operation(partition_plan.candidate_scores)
    steps = tuple(
        RuntimePlanningExplanationStep(
            operation_name=assignment.operation_name,
            backend_name=assignment.backend_name,
            selection_kind=_selection_kind(assignment.reason),
            reason=assignment.reason,
            memory_domain=assignment.memory_domain,
            produced_layout=assignment.produced_layout,
            transfer_bytes=assignment.transfer_bytes,
            layout_conversion_bytes=assignment.layout_conversion_bytes,
            candidate_score_count=len(scores_by_operation.get(assignment.operation_name, ())),
            selected_candidate_score_count=sum(
                1
                for score in scores_by_operation.get(assignment.operation_name, ())
                if score.selected
            ),
            rejected_candidate_score_count=sum(
                1
                for score in scores_by_operation.get(assignment.operation_name, ())
                if not score.selected
            ),
        )
        for assignment in partition_plan.assignments
    )
    return RuntimePlanningExplanationReport(
        graph_name=partition_plan.graph_name,
        steps=steps,
        transfer_edge_count=len(partition_plan.transfer_edges),
        layout_conversion_count=len(partition_plan.layout_conversions),
        total_transfer_bytes=partition_plan.total_transfer_bytes(),
        total_layout_conversion_bytes=partition_plan.total_layout_conversion_bytes(),
        total_data_movement_bytes=partition_plan.total_data_movement_bytes(),
        candidate_score_mode=(
            "recorded" if partition_plan.candidate_scores else "not_recorded"
        ),
        issues=_derive_explanation_issues(steps),
    )


def assert_runtime_planning_explanation(
    report: RuntimePlanningExplanationReport,
) -> RuntimePlanningExplanationReport:
    """Return the report or raise when runtime planning is not explainable."""

    if not isinstance(report, RuntimePlanningExplanationReport):
        raise TypeError("runtime planning explanation report must be report object")
    if report.issues:
        lines = [f"runtime planning explanation failed for {report.graph_name!r}:"]
        lines.extend(
            f"- {issue.operation_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimePlanningExplanationError("\n".join(lines))
    return report


def runtime_planning_explanation_report_to_dict(
    report: RuntimePlanningExplanationReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible planning explanation report."""

    if not isinstance(report, RuntimePlanningExplanationReport):
        raise TypeError("runtime planning explanation report must be report object")
    return {
        "backend_sequence": list(report.backend_sequence),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_score_count": report.candidate_score_count,
        "candidate_score_mode": report.candidate_score_mode,
        "explanation_contract": report.explanation_contract,
        "explanation_status": report.explanation_status,
        "fallback_count": report.fallback_count,
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "operation_name": issue.operation_name,
            }
            for issue in report.issues
        ],
        "layout_conversion_count": report.layout_conversion_count,
        "operation_count": report.operation_count,
        "passed": report.passed,
        "schema_version": RUNTIME_PLANNING_EXPLANATION_REPORT_SCHEMA_VERSION,
        "selection_kinds": list(report.selection_kinds),
        "steps": [
            {
                "backend_name": step.backend_name,
                "candidate_score_count": step.candidate_score_count,
                "layout_conversion_bytes": step.layout_conversion_bytes,
                "memory_domain": step.memory_domain.value,
                "movement_bytes": step.movement_bytes,
                "operation_name": step.operation_name,
                "produced_layout": step.produced_layout.value,
                "reason": step.reason,
                "rejected_candidate_score_count": step.rejected_candidate_score_count,
                "selected_candidate_score_count": step.selected_candidate_score_count,
                "selection_kind": step.selection_kind,
                "transfer_bytes": step.transfer_bytes,
            }
            for step in report.steps
        ],
        "total_data_movement_bytes": report.total_data_movement_bytes,
        "total_layout_conversion_bytes": report.total_layout_conversion_bytes,
        "total_transfer_bytes": report.total_transfer_bytes,
        "transfer_edge_count": report.transfer_edge_count,
    }


def dump_runtime_planning_explanation_report(
    report: RuntimePlanningExplanationReport,
) -> str:
    """Render a stable runtime planning explanation report."""

    text = json.dumps(
        runtime_planning_explanation_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_PLANNING_EXPLANATION_REPORT_BYTES:
        raise ValueError("runtime planning explanation report exceeds byte limit")
    return text + "\n"


def _candidate_scores_by_operation(
    candidate_scores: tuple[CandidateScore, ...],
) -> dict[str, tuple[CandidateScore, ...]]:
    grouped: dict[str, list[CandidateScore]] = {}
    for score in candidate_scores:
        if not isinstance(score, CandidateScore):
            raise TypeError("runtime planning explanation scores must be CandidateScore")
        grouped.setdefault(score.operation_name, []).append(score)
    return {name: tuple(scores) for name, scores in grouped.items()}


def _derive_explanation_issues(
    steps: tuple[RuntimePlanningExplanationStep, ...],
) -> tuple[RuntimePlanningExplanationIssue, ...]:
    issues: list[RuntimePlanningExplanationIssue] = []
    if not steps:
        issues.append(
            RuntimePlanningExplanationIssue(
                operation_name="graph",
                issue_code="operation_assignments_missing",
            )
        )
    for step in steps:
        if step.selection_kind == "unknown":
            issues.append(
                RuntimePlanningExplanationIssue(
                    operation_name=step.operation_name,
                    issue_code="unknown_selection_reason",
                )
            )
        if not step.reason:
            issues.append(
                RuntimePlanningExplanationIssue(
                    operation_name=step.operation_name,
                    issue_code="assignment_reason_missing",
                )
            )
        if step.candidate_score_count and step.selected_candidate_score_count != 1:
            issues.append(
                RuntimePlanningExplanationIssue(
                    operation_name=step.operation_name,
                    issue_code="selected_candidate_score_count_invalid",
                )
            )
    return tuple(issues)


def _selection_kind(reason: str) -> str:
    if reason.startswith("manual_override:require_backend="):
        return "manual_override_require"
    if reason.startswith("manual_override:prefer_backend="):
        return "manual_override_prefer"
    if reason.startswith("preferred_for:"):
        return "preferred_for"
    if reason.startswith("supported:"):
        return "supported"
    if reason.startswith("fallback:"):
        return "fallback"
    return "unknown"


def _validate_explanation_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _EXPLANATION_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime planning explanation identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_PLANNING_EXPLANATION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime planning explanation field limit")
    if value in _FORBIDDEN_EXPLANATION_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_reason(value: str, label: str) -> None:
    if not isinstance(value, str) or not _EXPLANATION_REASON_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime planning explanation reason")
    if len(value.encode("utf-8")) > MAX_RUNTIME_PLANNING_EXPLANATION_REASON_BYTES:
        raise ValueError(f"{label} exceeds runtime planning explanation reason limit")
    for forbidden in _FORBIDDEN_EXPLANATION_TEXT:
        if forbidden in value:
            raise ValueError(f"{label} names a forbidden execution surface")


def _validate_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


__all__ = [
    "MAX_RUNTIME_PLANNING_EXPLANATION_FIELD_BYTES",
    "MAX_RUNTIME_PLANNING_EXPLANATION_ISSUES",
    "MAX_RUNTIME_PLANNING_EXPLANATION_REASON_BYTES",
    "MAX_RUNTIME_PLANNING_EXPLANATION_REPORT_BYTES",
    "MAX_RUNTIME_PLANNING_EXPLANATION_STEPS",
    "RUNTIME_PLANNING_EXPLANATION_CANDIDATE_SCORE_MODES",
    "RUNTIME_PLANNING_EXPLANATION_CONTRACT",
    "RUNTIME_PLANNING_EXPLANATION_REPORT_SCHEMA_VERSION",
    "RUNTIME_PLANNING_EXPLANATION_SELECTION_KINDS",
    "RUNTIME_PLANNING_EXPLANATION_STATUSES",
    "RuntimePlanningExplanationError",
    "RuntimePlanningExplanationIssue",
    "RuntimePlanningExplanationReport",
    "RuntimePlanningExplanationStep",
    "assert_runtime_planning_explanation",
    "build_runtime_planning_explanation_report",
    "dump_runtime_planning_explanation_report",
    "runtime_planning_explanation_report_to_dict",
]
