"""Data-only resource budgets for future executable backend plugins."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.artifact_provenance import (
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
    build_backend_plugin_artifact_provenance_report,
)
from tuc.backends.sandbox_model import BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_SCHEMA_VERSION = (
    "tuc.backend_plugin_resource_budget_report.v0"
)
BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT = "backend_plugin_resource_budget.data_only.v0"
BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY = "resource_budget.static_bounds.no_execution.v0"
BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS = "accepted_data_only_budget"
BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION = "not_granted"
BACKEND_PLUGIN_RESOURCE_BUDGET_RECORD_STATUSES = frozenset({"reviewed_static_bounds"})
BACKEND_PLUGIN_RESOURCE_BUDGET_SCOPES = frozenset({"generated_artifact_execution"})
BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS = (
    "sandbox_model",
    "artifact_provenance",
    "content_digest",
    "cpu_budget",
    "memory_budget",
    "io_budget",
)
BACKEND_PLUGIN_RESOURCE_BUDGET_ISSUE_CODES = frozenset(
    {
        "artifact_provenance_binding_mismatch",
        "budget_execution_permission_granted",
        "budget_limit_exceeds_policy",
        "budget_limit_not_positive",
        "budget_missing_required_binding",
        "budget_scope_invalid",
        "budget_status_invalid",
        "duplicate_budget_id",
        "invalid_artifact_digest",
        "sandbox_binding_mismatch",
    }
)
MAX_BACKEND_PLUGIN_RESOURCE_BUDGETS = 16
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ISSUES = 64
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_BYTES = 64 * 1024
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_FIELD_BYTES = 512
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CPU_TIME_MS = 60_000
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES = 512 * 1024 * 1024
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_OUTPUT_BYTES = 1024 * 1024
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CACHE_ENTRIES = 64
MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_DIAGNOSTICS_BYTES = 64 * 1024

_BUDGET_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_BUDGET_TEXT = frozenset(
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
class BackendPluginResourceBudgetRecord:
    """One static resource budget for a future backend plugin artifact."""

    budget_id: str
    artifact_id: str
    artifact_digest: str
    budget_scope: str
    sandbox_model_contract: str
    provenance_contract: str
    cpu_time_limit_ms: int
    memory_limit_bytes: int
    output_limit_bytes: int
    artifact_size_limit_bytes: int
    cache_entry_limit: int
    diagnostics_limit_bytes: int
    budget_status: str

    def __post_init__(self) -> None:
        _validate_budget_text(self.budget_id, "budget_id")
        _validate_budget_text(self.artifact_id, "artifact_id")
        _validate_digest(self.artifact_digest)
        _validate_budget_text(self.budget_scope, "budget_scope")
        _validate_budget_text(
            self.sandbox_model_contract,
            "sandbox_model_contract",
        )
        _validate_budget_text(self.provenance_contract, "provenance_contract")
        _validate_budget_text(self.budget_status, "budget_status")
        if self.budget_scope not in BACKEND_PLUGIN_RESOURCE_BUDGET_SCOPES:
            raise ValueError("backend plugin resource budget scope unsupported")
        if (
            self.budget_status
            not in BACKEND_PLUGIN_RESOURCE_BUDGET_RECORD_STATUSES
        ):
            raise ValueError("backend plugin resource budget status unsupported")
        _validate_limit(
            self.cpu_time_limit_ms,
            MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CPU_TIME_MS,
            "cpu_time_limit_ms",
        )
        _validate_limit(
            self.memory_limit_bytes,
            MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES,
            "memory_limit_bytes",
        )
        _validate_limit(
            self.output_limit_bytes,
            MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_OUTPUT_BYTES,
            "output_limit_bytes",
        )
        _validate_limit(
            self.artifact_size_limit_bytes,
            MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ARTIFACT_BYTES,
            "artifact_size_limit_bytes",
        )
        _validate_limit(
            self.cache_entry_limit,
            MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CACHE_ENTRIES,
            "cache_entry_limit",
        )
        _validate_limit(
            self.diagnostics_limit_bytes,
            MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_DIAGNOSTICS_BYTES,
            "diagnostics_limit_bytes",
        )


@dataclass(frozen=True)
class BackendPluginResourceBudgetIssue:
    """One derived resource budget issue."""

    budget_id: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_budget_text(self.budget_id, "budget issue budget_id")
        _validate_budget_text(self.issue_code, "budget issue_code")
        if self.issue_code not in BACKEND_PLUGIN_RESOURCE_BUDGET_ISSUE_CODES:
            raise ValueError("backend plugin resource budget issue unsupported")


@dataclass(frozen=True)
class BackendPluginResourceBudgetReport:
    """Current data-only resource budget evidence."""

    budgets: tuple[BackendPluginResourceBudgetRecord, ...]
    issues: tuple[BackendPluginResourceBudgetIssue, ...]
    resource_budget_contract: str = BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    budget_policy: str = BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY
    budget_status: str = BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS
    execution_permission: str = BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION
    required_bindings: tuple[str, ...] = BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.resource_budget_contract != BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT:
            raise ValueError("backend plugin resource budget contract mismatch")
        if self.budget_policy != BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY:
            raise ValueError("backend plugin resource budget policy mismatch")
        if self.budget_status != BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS:
            raise ValueError("backend plugin resource budget status mismatch")
        if (
            self.execution_permission
            != BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION
        ):
            raise ValueError("backend plugin resource budget permission mismatch")
        if self.required_bindings != BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS:
            raise ValueError("backend plugin resource budget required bindings changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin resource budget blocked surfaces changed")
        if type(self.budgets) is not tuple:
            raise TypeError("backend plugin resource budgets must be a tuple")
        if len(self.budgets) > MAX_BACKEND_PLUGIN_RESOURCE_BUDGETS:
            raise ValueError("backend plugin resource budget count exceeds limit")
        for budget in self.budgets:
            if not isinstance(budget, BackendPluginResourceBudgetRecord):
                raise TypeError("backend plugin resource budgets must be records")
        if type(self.issues) is not tuple:
            raise TypeError("backend plugin resource budget issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ISSUES:
            raise ValueError("backend plugin resource budget issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPluginResourceBudgetIssue):
                raise TypeError("backend plugin resource budget issues must be objects")
        expected_issues = _derive_budget_issues(self)
        if self.issues != expected_issues:
            raise ValueError("backend plugin resource budget issues must be derived")

    @property
    def budget_count(self) -> int:
        """Return the number of reviewed budget records."""

        return len(self.budgets)

    @property
    def budget_ready(self) -> bool:
        """Return whether resource budget evidence is internally complete."""

        return bool(self.budgets) and not self.issues

    @property
    def execution_allowed(self) -> bool:
        """Return whether this budget evidence grants execution permission."""

        return False


class BackendPluginResourceBudgetError(ValueError):
    """Raised when backend plugin resource budget evidence fails."""


def build_backend_plugin_resource_budget_report(
    budgets: tuple[BackendPluginResourceBudgetRecord, ...] | None = None,
) -> BackendPluginResourceBudgetReport:
    """Build the current data-only backend plugin resource budget report."""

    normalized_budgets = _current_budget_records() if budgets is None else budgets
    report = BackendPluginResourceBudgetReport(
        budgets=normalized_budgets,
        issues=(),
    )
    return BackendPluginResourceBudgetReport(
        budgets=normalized_budgets,
        issues=_derive_budget_issues(report),
    )


def assert_backend_plugin_resource_budget(
    report: BackendPluginResourceBudgetReport,
) -> BackendPluginResourceBudgetReport:
    """Return the report or raise when resource budget evidence is incomplete."""

    if not isinstance(report, BackendPluginResourceBudgetReport):
        raise TypeError("backend plugin resource budget must be report object")
    if not report.budget_ready:
        lines = ["backend plugin resource budget failed:"]
        for issue in report.issues:
            lines.append(f"- {issue.budget_id}: {issue.issue_code}")
        raise BackendPluginResourceBudgetError("\n".join(lines))
    return report


def backend_plugin_resource_budget_report_to_dict(
    report: BackendPluginResourceBudgetReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible resource budget report."""

    if not isinstance(report, BackendPluginResourceBudgetReport):
        raise TypeError("backend plugin resource budget must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "budget_count": report.budget_count,
        "budget_policy": report.budget_policy,
        "budget_ready": report.budget_ready,
        "budget_status": report.budget_status,
        "budgets": [
            {
                "artifact_digest": budget.artifact_digest,
                "artifact_id": budget.artifact_id,
                "artifact_size_limit_bytes": budget.artifact_size_limit_bytes,
                "budget_id": budget.budget_id,
                "budget_scope": budget.budget_scope,
                "budget_status": budget.budget_status,
                "cache_entry_limit": budget.cache_entry_limit,
                "cpu_time_limit_ms": budget.cpu_time_limit_ms,
                "diagnostics_limit_bytes": budget.diagnostics_limit_bytes,
                "memory_limit_bytes": budget.memory_limit_bytes,
                "output_limit_bytes": budget.output_limit_bytes,
                "provenance_contract": budget.provenance_contract,
                "sandbox_model_contract": budget.sandbox_model_contract,
            }
            for budget in report.budgets
        ],
        "execution_allowed": report.execution_allowed,
        "execution_permission": report.execution_permission,
        "issues": [
            {
                "budget_id": issue.budget_id,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "required_bindings": list(report.required_bindings),
        "resource_budget_contract": report.resource_budget_contract,
        "schema_version": BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_SCHEMA_VERSION,
    }


def dump_backend_plugin_resource_budget_report(
    report: BackendPluginResourceBudgetReport,
) -> str:
    """Render a stable backend plugin resource budget report."""

    text = json.dumps(
        backend_plugin_resource_budget_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_BYTES:
        raise ValueError("backend plugin resource budget report exceeds byte limit")
    return text + "\n"


def _current_budget_records() -> tuple[BackendPluginResourceBudgetRecord, ...]:
    artifact = build_backend_plugin_artifact_provenance_report().artifacts[0]
    return (
        BackendPluginResourceBudgetRecord(
            budget_id="external_vector_lowering_resource_budget",
            artifact_id=artifact.artifact_id,
            artifact_digest=artifact.artifact_digest,
            budget_scope="generated_artifact_execution",
            sandbox_model_contract=BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
            provenance_contract=BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
            cpu_time_limit_ms=1000,
            memory_limit_bytes=64 * 1024 * 1024,
            output_limit_bytes=256 * 1024,
            artifact_size_limit_bytes=1024 * 1024,
            cache_entry_limit=4,
            diagnostics_limit_bytes=32 * 1024,
            budget_status="reviewed_static_bounds",
        ),
    )


def _derive_budget_issues(
    report: BackendPluginResourceBudgetReport,
) -> tuple[BackendPluginResourceBudgetIssue, ...]:
    issues: list[BackendPluginResourceBudgetIssue] = []
    budget_ids = tuple(budget.budget_id for budget in report.budgets)
    duplicate_ids = {
        budget_id for budget_id in budget_ids if budget_ids.count(budget_id) > 1
    }
    for budget_id in sorted(duplicate_ids):
        issues.append(
            BackendPluginResourceBudgetIssue(
                budget_id=budget_id,
                issue_code="duplicate_budget_id",
            )
        )
    provenance_artifacts = {
        artifact.artifact_id: artifact.artifact_digest
        for artifact in build_backend_plugin_artifact_provenance_report().artifacts
    }
    for budget in report.budgets:
        if not _SHA256_RE.fullmatch(budget.artifact_digest):
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="invalid_artifact_digest",
                )
            )
        if budget.budget_scope not in BACKEND_PLUGIN_RESOURCE_BUDGET_SCOPES:
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="budget_scope_invalid",
                )
            )
        if (
            budget.budget_status
            not in BACKEND_PLUGIN_RESOURCE_BUDGET_RECORD_STATUSES
        ):
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="budget_status_invalid",
                )
            )
        if budget.sandbox_model_contract != BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT:
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="sandbox_binding_mismatch",
                )
            )
        if budget.provenance_contract != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT:
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="artifact_provenance_binding_mismatch",
                )
            )
        if provenance_artifacts.get(budget.artifact_id) != budget.artifact_digest:
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="artifact_provenance_binding_mismatch",
                )
            )
        for binding in BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS:
            if not _budget_has_binding(budget, binding):
                issues.append(
                    BackendPluginResourceBudgetIssue(
                        budget_id=budget.budget_id,
                        issue_code="budget_missing_required_binding",
                    )
                )
    if report.execution_permission != BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION:
        for budget in report.budgets:
            issues.append(
                BackendPluginResourceBudgetIssue(
                    budget_id=budget.budget_id,
                    issue_code="budget_execution_permission_granted",
                )
            )
    return tuple(issues)


def _budget_has_binding(
    budget: BackendPluginResourceBudgetRecord,
    binding: str,
) -> bool:
    if binding == "sandbox_model":
        return budget.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    if binding == "artifact_provenance":
        return (
            budget.provenance_contract == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
        )
    if binding == "content_digest":
        return bool(_SHA256_RE.fullmatch(budget.artifact_digest))
    if binding == "cpu_budget":
        return 0 < budget.cpu_time_limit_ms <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CPU_TIME_MS
    if binding == "memory_budget":
        return 0 < budget.memory_limit_bytes <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES
    if binding == "io_budget":
        return (
            0
            < budget.output_limit_bytes
            <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_OUTPUT_BYTES
            and 0
            < budget.artifact_size_limit_bytes
            <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ARTIFACT_BYTES
            and 0
            < budget.cache_entry_limit
            <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CACHE_ENTRIES
            and 0
            < budget.diagnostics_limit_bytes
            <= MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_DIAGNOSTICS_BYTES
        )
    return False


def _validate_budget_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _BUDGET_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend budget identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend budget field limit")
    if value in _FORBIDDEN_BUDGET_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_digest(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("backend resource budget artifact digest must be a string")
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("backend resource budget artifact digest must be sha256")


def _validate_limit(value: int, maximum: int, label: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{label} must be an integer")
    if value <= 0:
        raise ValueError(f"{label} must be positive")
    if value > maximum:
        raise ValueError(f"{label} exceeds backend resource budget policy")


__all__ = [
    "BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_EXECUTION_PERMISSION",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_ISSUE_CODES",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_POLICY",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_RECORD_STATUSES",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_SCHEMA_VERSION",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_REQUIRED_BINDINGS",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_SCOPES",
    "BACKEND_PLUGIN_RESOURCE_BUDGET_STATUS",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ARTIFACT_BYTES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CACHE_ENTRIES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_CPU_TIME_MS",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_DIAGNOSTICS_BYTES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_FIELD_BYTES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_ISSUES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_MEMORY_BYTES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_OUTPUT_BYTES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGET_REPORT_BYTES",
    "MAX_BACKEND_PLUGIN_RESOURCE_BUDGETS",
    "BackendPluginResourceBudgetError",
    "BackendPluginResourceBudgetIssue",
    "BackendPluginResourceBudgetRecord",
    "BackendPluginResourceBudgetReport",
    "assert_backend_plugin_resource_budget",
    "backend_plugin_resource_budget_report_to_dict",
    "build_backend_plugin_resource_budget_report",
    "dump_backend_plugin_resource_budget_report",
]
