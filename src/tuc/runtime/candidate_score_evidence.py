"""Data-only evidence report for runtime candidate score diagnostics."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.partitioning import CandidateScore, PartitionPlan

RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_candidate_score_evidence_report.v0"
)
RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT = (
    "runtime_candidate_score_evidence.data_only.v0"
)
MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_SCORES = 128
MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_ISSUES = 64
MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_FIELD_BYTES = 512

_EVIDENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_EVIDENCE_TEXT = frozenset(
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
class RuntimeCandidateScoreEvidenceIssue:
    """One derived issue in candidate score evidence."""

    operation_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_evidence_text(self.operation_name, "issue operation_name")
        _validate_evidence_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeCandidateScoreEvidenceReport:
    """Deterministic report proving candidate score diagnostics remain inspectable."""

    graph_name: str
    operation_count: int
    default_plan_candidate_score_count: int
    compiler_decision_candidate_score_count: int
    compiler_decision_candidate_score_digest: str
    candidate_scores: tuple[CandidateScore, ...]
    issues: tuple[RuntimeCandidateScoreEvidenceIssue, ...]
    evidence_contract: str = RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_evidence_text(self.graph_name, "graph_name")
        if self.evidence_contract != RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT:
            raise ValueError("runtime candidate score evidence contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError(
                "runtime candidate score evidence blocked execution surfaces changed"
            )
        _require_non_negative_int(self.operation_count, "operation_count")
        _require_non_negative_int(
            self.default_plan_candidate_score_count,
            "default_plan_candidate_score_count",
        )
        _require_non_negative_int(
            self.compiler_decision_candidate_score_count,
            "compiler_decision_candidate_score_count",
        )
        _validate_digest(
            self.compiler_decision_candidate_score_digest,
            "compiler_decision_candidate_score_digest",
        )
        if type(self.candidate_scores) is not tuple:
            raise TypeError("runtime candidate score evidence scores must be a tuple")
        if (
            len(self.candidate_scores)
            > MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_SCORES
        ):
            raise ValueError("runtime candidate score evidence score count exceeds limit")
        for score in self.candidate_scores:
            if not isinstance(score, CandidateScore):
                raise TypeError(
                    "runtime candidate score evidence scores must be CandidateScore"
                )
        if type(self.issues) is not tuple:
            raise TypeError("runtime candidate score evidence issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_ISSUES:
            raise ValueError("runtime candidate score evidence issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeCandidateScoreEvidenceIssue):
                raise TypeError(
                    "runtime candidate score evidence issues must be issue objects"
                )

        expected_issues = _derive_candidate_score_evidence_issues(
            operation_count=self.operation_count,
            default_plan_candidate_score_count=self.default_plan_candidate_score_count,
            compiler_decision_candidate_score_count=(
                self.compiler_decision_candidate_score_count
            ),
            compiler_decision_candidate_score_digest=(
                self.compiler_decision_candidate_score_digest
            ),
            candidate_scores=self.candidate_scores,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime candidate score evidence issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether candidate score evidence passed."""

        return not self.issues

    @property
    def selected_candidate_count(self) -> int:
        """Return selected score count."""

        return sum(1 for score in self.candidate_scores if score.selected)

    @property
    def rejected_candidate_count(self) -> int:
        """Return rejected score count."""

        return sum(1 for score in self.candidate_scores if not score.selected)

    @property
    def candidate_score_digest(self) -> str:
        """Return the deterministic digest of runtime candidate scores."""

        return _candidate_score_digest(self.candidate_scores)

    @property
    def score_units(self) -> tuple[str, ...]:
        """Return score units present in deterministic order."""

        return tuple(sorted({score.transfer_score_unit for score in self.candidate_scores}))

    @property
    def selection_stages(self) -> tuple[str, ...]:
        """Return selection stages present in deterministic order."""

        return tuple(sorted({score.selection_stage for score in self.candidate_scores}))


class RuntimeCandidateScoreEvidenceError(AssertionError):
    """Raised when runtime candidate score evidence does not pass."""


def build_runtime_candidate_score_evidence_report(
    *,
    default_plan: PartitionPlan,
    scored_plan: PartitionPlan,
    compiler_decision_candidate_scores: tuple[CandidateScore, ...],
) -> RuntimeCandidateScoreEvidenceReport:
    """Build a bounded evidence report from explicit runtime planning artifacts."""

    if not isinstance(default_plan, PartitionPlan):
        raise TypeError("default_plan must be PartitionPlan")
    if not isinstance(scored_plan, PartitionPlan):
        raise TypeError("scored_plan must be PartitionPlan")
    if default_plan.graph_name != scored_plan.graph_name:
        raise ValueError("candidate score evidence plans must use the same graph")
    if type(compiler_decision_candidate_scores) is not tuple:
        raise TypeError("compiler_decision_candidate_scores must be a tuple")
    for score in compiler_decision_candidate_scores:
        if not isinstance(score, CandidateScore):
            raise TypeError("compiler_decision_candidate_scores must contain CandidateScore")

    candidate_scores = scored_plan.candidate_scores
    issues = _derive_candidate_score_evidence_issues(
        operation_count=len(scored_plan.assignments),
        default_plan_candidate_score_count=len(default_plan.candidate_scores),
        compiler_decision_candidate_score_count=len(compiler_decision_candidate_scores),
        compiler_decision_candidate_score_digest=_candidate_score_digest(
            compiler_decision_candidate_scores
        ),
        candidate_scores=candidate_scores,
    )
    return RuntimeCandidateScoreEvidenceReport(
        graph_name=scored_plan.graph_name,
        operation_count=len(scored_plan.assignments),
        default_plan_candidate_score_count=len(default_plan.candidate_scores),
        compiler_decision_candidate_score_count=len(compiler_decision_candidate_scores),
        compiler_decision_candidate_score_digest=_candidate_score_digest(
            compiler_decision_candidate_scores
        ),
        candidate_scores=candidate_scores,
        issues=issues,
    )


def assert_runtime_candidate_score_evidence(
    report: RuntimeCandidateScoreEvidenceReport,
) -> RuntimeCandidateScoreEvidenceReport:
    """Return the report or raise when candidate score evidence fails."""

    if not isinstance(report, RuntimeCandidateScoreEvidenceReport):
        raise TypeError("runtime candidate score evidence report must be report object")
    if report.issues:
        lines = [f"runtime candidate score evidence failed for {report.graph_name!r}:"]
        lines.extend(
            f"- {issue.operation_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeCandidateScoreEvidenceError("\n".join(lines))
    return report


def runtime_candidate_score_evidence_report_to_dict(
    report: RuntimeCandidateScoreEvidenceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible candidate score evidence report."""

    if not isinstance(report, RuntimeCandidateScoreEvidenceReport):
        raise TypeError("runtime candidate score evidence report must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_score_count": len(report.candidate_scores),
        "candidate_score_digest": report.candidate_score_digest,
        "candidate_scores": [
            {
                "backend_name": score.backend_name,
                "layout_conversion_bytes": score.layout_conversion_bytes,
                "memory_domain": score.memory_domain.value,
                "operation_name": score.operation_name,
                "preferred_memory_domain_match": score.preferred_memory_domain_match,
                "produced_layout": score.produced_layout.value,
                "selected": score.selected,
                "selection_stage": score.selection_stage,
                "transfer_bytes": score.transfer_bytes,
                "transfer_score": score.transfer_score,
                "transfer_score_unit": score.transfer_score_unit,
            }
            for score in report.candidate_scores
        ],
        "compiler_decision_candidate_score_count": (
            report.compiler_decision_candidate_score_count
        ),
        "compiler_decision_candidate_score_digest": (
            report.compiler_decision_candidate_score_digest
        ),
        "default_plan_candidate_score_count": (
            report.default_plan_candidate_score_count
        ),
        "evidence_contract": report.evidence_contract,
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "operation_name": issue.operation_name,
            }
            for issue in report.issues
        ],
        "operation_count": report.operation_count,
        "passed": report.passed,
        "rejected_candidate_count": report.rejected_candidate_count,
        "schema_version": RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_SCHEMA_VERSION,
        "score_units": list(report.score_units),
        "selected_candidate_count": report.selected_candidate_count,
        "selection_stages": list(report.selection_stages),
    }


def dump_runtime_candidate_score_evidence_report(
    report: RuntimeCandidateScoreEvidenceReport,
) -> str:
    """Render a stable runtime candidate score evidence report."""

    text = json.dumps(
        runtime_candidate_score_evidence_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_BYTES:
        raise ValueError("runtime candidate score evidence report exceeds byte limit")
    return text + "\n"


def _derive_candidate_score_evidence_issues(
    *,
    operation_count: int,
    default_plan_candidate_score_count: int,
    compiler_decision_candidate_score_count: int,
    compiler_decision_candidate_score_digest: str,
    candidate_scores: tuple[CandidateScore, ...],
) -> tuple[RuntimeCandidateScoreEvidenceIssue, ...]:
    issues: list[RuntimeCandidateScoreEvidenceIssue] = []

    if operation_count <= 0:
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="operation_count_missing",
            )
        )
    if default_plan_candidate_score_count != 0:
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="default_plan_emitted_candidate_scores",
            )
        )
    if not candidate_scores:
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="opt_in_candidate_scores_missing",
            )
        )
    if compiler_decision_candidate_score_count != len(candidate_scores):
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="compiler_decision_score_count_mismatch",
            )
        )
    if compiler_decision_candidate_score_digest != _candidate_score_digest(
        candidate_scores
    ):
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="compiler_decision_score_digest_mismatch",
            )
        )
    if candidate_scores and all(score.selected for score in candidate_scores):
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="rejected_candidate_evidence_missing",
            )
        )

    scores_by_operation: dict[str, list[CandidateScore]] = {}
    for score in candidate_scores:
        scores_by_operation.setdefault(score.operation_name, []).append(score)

    if candidate_scores and operation_count != len(scores_by_operation):
        issues.append(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="candidate_score_operation_count_mismatch",
            )
        )

    for operation_name in sorted(scores_by_operation):
        operation_scores = scores_by_operation[operation_name]
        selected = tuple(score for score in operation_scores if score.selected)
        if len(selected) != 1:
            issues.append(
                RuntimeCandidateScoreEvidenceIssue(
                    operation_name=operation_name,
                    issue_code="selected_candidate_count_invalid",
                )
            )

    return tuple(issues)


def _validate_evidence_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _EVIDENCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime candidate score identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime candidate score field limit")
    if value in _FORBIDDEN_EVIDENCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"^[0-9a-f]{64}$", value):
        raise ValueError(f"{label} must be a sha256 hex digest")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _candidate_score_digest(candidate_scores: tuple[CandidateScore, ...]) -> str:
    payload = json.dumps(
        [
            {
                "backend_name": score.backend_name,
                "layout_conversion_bytes": score.layout_conversion_bytes,
                "memory_domain": score.memory_domain.value,
                "operation_name": score.operation_name,
                "preferred_memory_domain_match": score.preferred_memory_domain_match,
                "produced_layout": score.produced_layout.value,
                "selected": score.selected,
                "selection_stage": score.selection_stage,
                "transfer_bytes": score.transfer_bytes,
                "transfer_score": score.transfer_score,
                "transfer_score_unit": score.transfer_score_unit,
            }
            for score in candidate_scores
        ],
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_FIELD_BYTES",
    "MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_ISSUES",
    "MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_BYTES",
    "MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_SCORES",
    "RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT",
    "RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_SCHEMA_VERSION",
    "RuntimeCandidateScoreEvidenceError",
    "RuntimeCandidateScoreEvidenceIssue",
    "RuntimeCandidateScoreEvidenceReport",
    "assert_runtime_candidate_score_evidence",
    "build_runtime_candidate_score_evidence_report",
    "dump_runtime_candidate_score_evidence_report",
    "runtime_candidate_score_evidence_report_to_dict",
]
