"""Portfolio-level data-only evidence for trusted backend equivalence slices."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.backend_equivalence import RuntimeBackendEquivalenceReport
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_backend_equivalence_portfolio_report.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT = (
    "runtime_backend_equivalence_portfolio.data_only.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS = "review_evidence"
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_SLICES = 16
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ISSUES = 128
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_FIELD_BYTES = 512

_PORTFOLIO_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_PORTFOLIO_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "command_line",
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
        "output_value",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "reference_value",
        "runtime_handle",
        "source_text",
        "subprocess",
        "tensor_value",
        "tensor_values",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeBackendEquivalencePortfolioSlice:
    """One backend-equivalence report summarized for portfolio review."""

    slice_id: str
    graph_name: str
    baseline_run_id: str
    candidate_run_id: str
    baseline_backend_sequence: tuple[str, ...]
    candidate_backend_sequence: tuple[str, ...]
    comparison_count: int
    comparison_metadata_digest: str
    passed: bool
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_portfolio_text(self.slice_id, "slice_id")
        _validate_portfolio_text(self.graph_name, "graph_name")
        _validate_portfolio_text(self.baseline_run_id, "baseline_run_id")
        _validate_portfolio_text(self.candidate_run_id, "candidate_run_id")
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError("runtime backend equivalence portfolio run IDs must differ")
        _validate_text_sequence(
            self.baseline_backend_sequence,
            "baseline_backend_sequence",
        )
        _validate_text_sequence(
            self.candidate_backend_sequence,
            "candidate_backend_sequence",
        )
        _validate_positive_count(self.comparison_count, "comparison_count")
        _validate_digest(self.comparison_metadata_digest, "comparison_metadata_digest")
        if not isinstance(self.passed, bool):
            raise TypeError("runtime backend equivalence portfolio passed must be bool")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError(
                "runtime backend equivalence portfolio must omit raw values"
            )


@dataclass(frozen=True)
class RuntimeBackendEquivalencePortfolioIssue:
    """One derived portfolio-level issue."""

    slice_id: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_portfolio_text(self.slice_id, "issue slice_id")
        _validate_portfolio_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeBackendEquivalencePortfolioReport:
    """Aggregate backend-equivalence evidence across backend families."""

    portfolio_id: str
    slices: tuple[RuntimeBackendEquivalencePortfolioSlice, ...]
    issues: tuple[RuntimeBackendEquivalencePortfolioIssue, ...]
    portfolio_contract: str = RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    artifact_status: str = RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_portfolio_text(self.portfolio_id, "portfolio_id")
        if (
            self.portfolio_contract
            != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT
        ):
            raise ValueError(
                "runtime backend equivalence portfolio contract mismatch"
            )
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError(
                "runtime backend equivalence portfolio executor contract mismatch"
            )
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError(
                "runtime backend equivalence portfolio trusted registry mismatch"
            )
        if (
            self.artifact_status
            != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS
        ):
            raise ValueError(
                "runtime backend equivalence portfolio artifact status mismatch"
            )
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError(
                "runtime backend equivalence portfolio must omit raw values"
            )
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError(
                "runtime backend equivalence portfolio blocked surfaces changed"
            )
        _validate_slices(self.slices)
        if type(self.issues) is not tuple:
            raise TypeError("runtime backend equivalence portfolio issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ISSUES:
            raise ValueError(
                "runtime backend equivalence portfolio issue count exceeds limit"
            )
        for issue in self.issues:
            if not isinstance(issue, RuntimeBackendEquivalencePortfolioIssue):
                raise TypeError(
                    "runtime backend equivalence portfolio issues must be issues"
                )
        expected_issues = _derive_issues(self.slices)
        if self.issues != expected_issues:
            raise ValueError(
                "runtime backend equivalence portfolio issues must be derived"
            )

    @property
    def passed(self) -> bool:
        """Return whether all portfolio slices passed."""

        return not self.issues

    @property
    def slice_count(self) -> int:
        """Return the number of backend-equivalence slices."""

        return len(self.slices)

    @property
    def candidate_backend_families(self) -> tuple[str, ...]:
        """Return non-reference backend families covered by candidate slices."""

        return tuple(
            sorted(
                {
                    backend
                    for slice_ in self.slices
                    for backend in slice_.candidate_backend_sequence
                    if backend != "reference-cpu"
                }
            )
        )

    @property
    def portfolio_metadata_digest(self) -> str:
        """Return a digest over portfolio metadata only, never tensor values."""

        payload = [
            {
                "baseline_backend_sequence": list(
                    slice_.baseline_backend_sequence
                ),
                "baseline_run_id": slice_.baseline_run_id,
                "candidate_backend_sequence": list(
                    slice_.candidate_backend_sequence
                ),
                "candidate_run_id": slice_.candidate_run_id,
                "comparison_count": slice_.comparison_count,
                "comparison_metadata_digest": (
                    slice_.comparison_metadata_digest
                ),
                "graph_name": slice_.graph_name,
                "passed": slice_.passed,
                "raw_value_policy": slice_.raw_value_policy,
                "slice_id": slice_.slice_id,
            }
            for slice_ in self.slices
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeBackendEquivalencePortfolioError(AssertionError):
    """Raised when backend-equivalence portfolio evidence does not pass."""


def build_runtime_backend_equivalence_portfolio_report(
    portfolio_id: str,
    reports: Iterable[RuntimeBackendEquivalenceReport],
) -> RuntimeBackendEquivalencePortfolioReport:
    """Build an aggregate data-only portfolio from equivalence reports."""

    _validate_portfolio_text(portfolio_id, "portfolio_id")
    report_tuple = tuple(reports)
    if not report_tuple:
        raise ValueError(
            "runtime backend equivalence portfolio requires at least one report"
        )
    slices = tuple(_slice_from_report(report) for report in report_tuple)
    return RuntimeBackendEquivalencePortfolioReport(
        portfolio_id=portfolio_id,
        slices=slices,
        issues=_derive_issues(slices),
    )


def assert_runtime_backend_equivalence_portfolio(
    report: RuntimeBackendEquivalencePortfolioReport,
) -> RuntimeBackendEquivalencePortfolioReport:
    """Return the report or raise when portfolio evidence fails."""

    if not isinstance(report, RuntimeBackendEquivalencePortfolioReport):
        raise TypeError(
            "runtime backend equivalence portfolio report must be report object"
        )
    if report.issues:
        lines = [
            "runtime backend equivalence portfolio failed "
            f"for {report.portfolio_id!r}:"
        ]
        lines.extend(f"- {issue.slice_id}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeBackendEquivalencePortfolioError("\n".join(lines))
    return report


def runtime_backend_equivalence_portfolio_report_to_dict(
    report: RuntimeBackendEquivalencePortfolioReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible backend-equivalence portfolio."""

    if not isinstance(report, RuntimeBackendEquivalencePortfolioReport):
        raise TypeError(
            "runtime backend equivalence portfolio report must be report object"
        )
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_backend_families": list(report.candidate_backend_families),
        "executor_contract": report.executor_contract,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "slice_id": issue.slice_id,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "portfolio_contract": report.portfolio_contract,
        "portfolio_id": report.portfolio_id,
        "portfolio_metadata_digest": report.portfolio_metadata_digest,
        "raw_value_policy": report.raw_value_policy,
        "schema_version": RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_SCHEMA_VERSION,
        "slice_count": report.slice_count,
        "slices": [
            {
                "baseline_backend_sequence": list(
                    slice_.baseline_backend_sequence
                ),
                "baseline_run_id": slice_.baseline_run_id,
                "candidate_backend_sequence": list(
                    slice_.candidate_backend_sequence
                ),
                "candidate_run_id": slice_.candidate_run_id,
                "comparison_count": slice_.comparison_count,
                "comparison_metadata_digest": (
                    slice_.comparison_metadata_digest
                ),
                "graph_name": slice_.graph_name,
                "passed": slice_.passed,
                "raw_value_policy": slice_.raw_value_policy,
                "slice_id": slice_.slice_id,
            }
            for slice_ in report.slices
        ],
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_backend_equivalence_portfolio_report(
    report: RuntimeBackendEquivalencePortfolioReport,
) -> str:
    """Render stable data-only backend-equivalence portfolio evidence."""

    text = json.dumps(
        runtime_backend_equivalence_portfolio_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_BYTES
    ):
        raise ValueError("runtime backend equivalence portfolio report exceeds limit")
    return text + "\n"


def _slice_from_report(
    report: RuntimeBackendEquivalenceReport,
) -> RuntimeBackendEquivalencePortfolioSlice:
    if not isinstance(report, RuntimeBackendEquivalenceReport):
        raise TypeError(
            "runtime backend equivalence portfolio inputs must be reports"
        )
    runs = {run.run_id: run for run in report.runs}
    baseline = runs[report.baseline_run_id]
    candidate = runs[report.candidate_run_id]
    comparisons_matched = all(
        comparison.comparison_status == "matched"
        for comparison in report.comparisons
    )
    return RuntimeBackendEquivalencePortfolioSlice(
        slice_id=report.graph_name,
        graph_name=report.graph_name,
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        baseline_backend_sequence=baseline.planned_backend_sequence,
        candidate_backend_sequence=candidate.planned_backend_sequence,
        comparison_count=len(report.comparisons),
        comparison_metadata_digest=report.comparison_metadata_digest,
        passed=report.passed and comparisons_matched,
        raw_value_policy=report.raw_value_policy,
    )


def _derive_issues(
    slices: tuple[RuntimeBackendEquivalencePortfolioSlice, ...],
) -> tuple[RuntimeBackendEquivalencePortfolioIssue, ...]:
    issues: list[RuntimeBackendEquivalencePortfolioIssue] = []
    seen_slice_ids: set[str] = set()
    for slice_ in slices:
        if slice_.slice_id in seen_slice_ids:
            issues.append(
                RuntimeBackendEquivalencePortfolioIssue(
                    slice_id=slice_.slice_id,
                    issue_code="slice_id_duplicate",
                )
            )
        seen_slice_ids.add(slice_.slice_id)
        if not slice_.passed:
            issues.append(
                RuntimeBackendEquivalencePortfolioIssue(
                    slice_id=slice_.slice_id,
                    issue_code="equivalence_report_failed",
                )
            )
    if not {
        backend
        for slice_ in slices
        for backend in slice_.candidate_backend_sequence
        if backend != "reference-cpu"
    }:
        issues.append(
            RuntimeBackendEquivalencePortfolioIssue(
                slice_id="portfolio",
                issue_code="candidate_backend_family_missing",
            )
        )
    return tuple(issues)


def _validate_slices(
    slices: tuple[RuntimeBackendEquivalencePortfolioSlice, ...],
) -> None:
    if type(slices) is not tuple or not slices:
        raise ValueError(
            "runtime backend equivalence portfolio slices must be non-empty tuple"
        )
    if len(slices) > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_SLICES:
        raise ValueError(
            "runtime backend equivalence portfolio slice count exceeds limit"
        )
    for slice_ in slices:
        if not isinstance(slice_, RuntimeBackendEquivalencePortfolioSlice):
            raise TypeError(
                "runtime backend equivalence portfolio slices must be slice objects"
            )


def _validate_text_sequence(value: tuple[str, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(
            f"runtime backend equivalence portfolio {label} must be non-empty tuple"
        )
    for item in value:
        _validate_portfolio_text(item, label)


def _validate_positive_count(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(
            f"runtime backend equivalence portfolio {label} must be positive"
        )


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(
            f"runtime backend equivalence portfolio {label} must be sha256 digest"
        )


def _validate_portfolio_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PORTFOLIO_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe runtime backend equivalence portfolio identifier"
        )
    if len(value.encode("utf-8")) > MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_FIELD_BYTES:
        raise ValueError(
            f"{label} exceeds runtime backend equivalence portfolio field limit"
        )
    if value in _FORBIDDEN_PORTFOLIO_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_FIELD_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ISSUES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_SLICES",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT",
    "RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_SCHEMA_VERSION",
    "RuntimeBackendEquivalencePortfolioError",
    "RuntimeBackendEquivalencePortfolioIssue",
    "RuntimeBackendEquivalencePortfolioReport",
    "RuntimeBackendEquivalencePortfolioSlice",
    "assert_runtime_backend_equivalence_portfolio",
    "build_runtime_backend_equivalence_portfolio_report",
    "dump_runtime_backend_equivalence_portfolio_report",
    "runtime_backend_equivalence_portfolio_report_to_dict",
]
