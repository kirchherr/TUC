"""Data-only backend author readiness reports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_AUTHOR_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.backend_author_readiness_report.v0"
)
BACKEND_AUTHOR_READINESS_CONTRACT = "backend_author_readiness.data_only.v0"
BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS = (
    "manifest_claim_review",
    "manifest_registry",
    "compiler_assignment",
    "backend_conformance",
    "assigned_subgraph_lowering",
)
BACKEND_AUTHOR_READINESS_STATUSES = frozenset({"passed", "failed"})
MAX_BACKEND_AUTHOR_READINESS_CHECKS = 16
MAX_BACKEND_AUTHOR_READINESS_ISSUES = 64
MAX_BACKEND_AUTHOR_READINESS_REPORT_BYTES = 64 * 1024
MAX_BACKEND_AUTHOR_READINESS_FIELD_BYTES = 512

_READINESS_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_READINESS_TEXT = frozenset(
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
class BackendAuthorReadinessCheck:
    """One required backend-author onboarding check."""

    check_name: str
    status: str
    evidence_id: str
    detail: str

    def __post_init__(self) -> None:
        _validate_readiness_text(self.check_name, "check_name")
        if self.status not in BACKEND_AUTHOR_READINESS_STATUSES:
            raise ValueError("backend author readiness status is unsupported")
        _validate_readiness_text(self.evidence_id, "evidence_id")
        _validate_readiness_text(self.detail, "detail")


@dataclass(frozen=True)
class BackendAuthorReadinessIssue:
    """One derived backend-author readiness issue."""

    check_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_readiness_text(self.check_name, "issue check_name")
        _validate_readiness_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class BackendAuthorReadinessReport:
    """Deterministic readiness report for an external backend author path."""

    backend_name: str
    manifest_id: str
    checks: tuple[BackendAuthorReadinessCheck, ...]
    issues: tuple[BackendAuthorReadinessIssue, ...]
    readiness_contract: str = BACKEND_AUTHOR_READINESS_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_readiness_text(self.backend_name, "backend_name")
        _validate_readiness_text(self.manifest_id, "manifest_id")
        if self.readiness_contract != BACKEND_AUTHOR_READINESS_CONTRACT:
            raise ValueError("backend author readiness contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend author readiness blocked execution surfaces changed")
        if type(self.checks) is not tuple:
            raise TypeError("backend author readiness checks must be a tuple")
        if len(self.checks) > MAX_BACKEND_AUTHOR_READINESS_CHECKS:
            raise ValueError("backend author readiness check count exceeds limit")
        check_names: list[str] = []
        for check in self.checks:
            if not isinstance(check, BackendAuthorReadinessCheck):
                raise TypeError("backend author readiness checks must be check objects")
            check_names.append(check.check_name)
        if tuple(check_names) != BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS:
            raise ValueError("backend author readiness checks must match required order")
        if type(self.issues) is not tuple:
            raise TypeError("backend author readiness issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_AUTHOR_READINESS_ISSUES:
            raise ValueError("backend author readiness issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendAuthorReadinessIssue):
                raise TypeError("backend author readiness issues must be issue objects")
        expected_issues = _derive_readiness_issues(self.checks)
        if self.issues != expected_issues:
            raise ValueError("backend author readiness issues must be derived")

    @property
    def ready(self) -> bool:
        """Return whether every required author-readiness check passed."""

        return not self.issues


class BackendAuthorReadinessError(AssertionError):
    """Raised when a backend author readiness report is not ready."""


def build_backend_author_readiness_report(
    *,
    backend_name: str,
    manifest_id: str,
    checks: tuple[BackendAuthorReadinessCheck, ...],
) -> BackendAuthorReadinessReport:
    """Build a bounded backend author readiness report from explicit checks."""

    return BackendAuthorReadinessReport(
        backend_name=backend_name,
        manifest_id=manifest_id,
        checks=checks,
        issues=_derive_readiness_issues(checks),
    )


def assert_backend_author_readiness(
    report: BackendAuthorReadinessReport,
) -> BackendAuthorReadinessReport:
    """Return the report or raise when any required check failed."""

    if not isinstance(report, BackendAuthorReadinessReport):
        raise TypeError("backend author readiness report must be report object")
    if report.issues:
        lines = [f"backend author {report.backend_name!r} is not ready:"]
        lines.extend(f"- {issue.check_name}:{issue.issue_code}" for issue in report.issues)
        raise BackendAuthorReadinessError("\n".join(lines))
    return report


def backend_author_readiness_report_to_dict(
    report: BackendAuthorReadinessReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible backend author readiness report."""

    if not isinstance(report, BackendAuthorReadinessReport):
        raise TypeError("backend author readiness report must be report object")
    return {
        "backend_name": report.backend_name,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "check_count": len(report.checks),
        "checks": [
            {
                "check_name": check.check_name,
                "detail": check.detail,
                "evidence_id": check.evidence_id,
                "status": check.status,
            }
            for check in report.checks
        ],
        "issues": [
            {
                "check_name": issue.check_name,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "manifest_id": report.manifest_id,
        "readiness_contract": report.readiness_contract,
        "ready": report.ready,
        "required_checks": list(BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS),
        "schema_version": BACKEND_AUTHOR_READINESS_REPORT_SCHEMA_VERSION,
    }


def dump_backend_author_readiness_report(
    report: BackendAuthorReadinessReport,
) -> str:
    """Render a stable backend author readiness report."""

    text = json.dumps(
        backend_author_readiness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_AUTHOR_READINESS_REPORT_BYTES:
        raise ValueError("backend author readiness report exceeds byte limit")
    return text + "\n"


def _derive_readiness_issues(
    checks: tuple[BackendAuthorReadinessCheck, ...],
) -> tuple[BackendAuthorReadinessIssue, ...]:
    issues: list[BackendAuthorReadinessIssue] = []
    for check in checks:
        if check.status != "passed":
            issues.append(
                BackendAuthorReadinessIssue(
                    check_name=check.check_name,
                    issue_code=f"{check.check_name}_not_passed",
                )
            )
    return tuple(issues)


def _validate_readiness_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _READINESS_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend author readiness identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_AUTHOR_READINESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend author readiness field limit")
    if value in _FORBIDDEN_READINESS_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "BACKEND_AUTHOR_READINESS_CONTRACT",
    "BACKEND_AUTHOR_READINESS_REPORT_SCHEMA_VERSION",
    "BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS",
    "BACKEND_AUTHOR_READINESS_STATUSES",
    "MAX_BACKEND_AUTHOR_READINESS_CHECKS",
    "MAX_BACKEND_AUTHOR_READINESS_FIELD_BYTES",
    "MAX_BACKEND_AUTHOR_READINESS_ISSUES",
    "MAX_BACKEND_AUTHOR_READINESS_REPORT_BYTES",
    "BackendAuthorReadinessCheck",
    "BackendAuthorReadinessError",
    "BackendAuthorReadinessIssue",
    "BackendAuthorReadinessReport",
    "assert_backend_author_readiness",
    "backend_author_readiness_report_to_dict",
    "build_backend_author_readiness_report",
    "dump_backend_author_readiness_report",
]
