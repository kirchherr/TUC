"""Data-only runtime memory budget evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.ir.memory import MemoryDomainKind
from tuc.runtime.allocation import (
    RUNTIME_ALLOCATION_PLAN_CONTRACT,
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RuntimeAllocationBinding,
    RuntimeAllocationPlanReport,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION = "tuc.runtime_memory_budget_report.v0"
RUNTIME_MEMORY_BUDGET_CONTRACT = "runtime_memory_budget.data_only.v0"
MAX_RUNTIME_MEMORY_BUDGETS = 32
MAX_RUNTIME_MEMORY_BUDGET_USAGES = 32
MAX_RUNTIME_MEMORY_BUDGET_ISSUES = 64
MAX_RUNTIME_MEMORY_BUDGET_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_MEMORY_BUDGET_FIELD_BYTES = 512

_MEMORY_BUDGET_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_MEMORY_BUDGET_TEXT = frozenset(
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
_MISSING_BUDGET_ID = "missing_budget"
_MEMORY_BUDGET_STATUSES = frozenset(
    {
        "within_budget",
        "missing_budget",
        "reserved_exceeded",
        "peak_exceeded",
        "reserved_and_peak_exceeded",
    }
)


@dataclass(frozen=True)
class RuntimeMemoryDomainBudget:
    """Explicit memory budget for one runtime memory domain."""

    budget_id: str
    memory_domain: MemoryDomainKind
    max_reserved_bytes: int
    max_peak_live_bytes: int

    def __post_init__(self) -> None:
        _validate_text(self.budget_id, "budget_id")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("memory budget memory_domain must be MemoryDomainKind")
        _require_positive_int(self.max_reserved_bytes, "max_reserved_bytes")
        _require_positive_int(self.max_peak_live_bytes, "max_peak_live_bytes")


@dataclass(frozen=True)
class RuntimeMemoryDomainUsage:
    """Derived memory usage for one memory domain."""

    memory_domain: MemoryDomainKind
    budget_id: str
    total_reserved_bytes: int
    peak_live_bytes: int
    max_reserved_bytes: int
    max_peak_live_bytes: int
    status: str

    def __post_init__(self) -> None:
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("memory usage memory_domain must be MemoryDomainKind")
        _validate_text(self.budget_id, "budget_id")
        _require_non_negative_int(self.total_reserved_bytes, "total_reserved_bytes")
        _require_non_negative_int(self.peak_live_bytes, "peak_live_bytes")
        _require_non_negative_int(self.max_reserved_bytes, "max_reserved_bytes")
        _require_non_negative_int(self.max_peak_live_bytes, "max_peak_live_bytes")
        if self.status not in _MEMORY_BUDGET_STATUSES:
            raise ValueError("memory usage status is unsupported")
        if self.status != _derive_usage_status(
            self.total_reserved_bytes,
            self.peak_live_bytes,
            self.max_reserved_bytes,
            self.max_peak_live_bytes,
        ):
            raise ValueError("memory usage status must be derived")


@dataclass(frozen=True)
class RuntimeMemoryBudgetIssue:
    """One derived runtime memory budget issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "issue subject")
        _validate_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeMemoryBudgetReport:
    """Deterministic memory budget report for a runtime allocation plan."""

    graph_name: str
    operation_count: int
    source_allocation_contract: str
    source_allocation_schema_version: str
    source_allocation_issue_count: int
    source_allocation_metadata_digest: str
    budgets: tuple[RuntimeMemoryDomainBudget, ...]
    usages: tuple[RuntimeMemoryDomainUsage, ...]
    issues: tuple[RuntimeMemoryBudgetIssue, ...]
    budget_contract: str = RUNTIME_MEMORY_BUDGET_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.source_allocation_contract != RUNTIME_ALLOCATION_PLAN_CONTRACT:
            raise ValueError("memory budget source allocation contract mismatch")
        if self.source_allocation_schema_version != RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION:
            raise ValueError("memory budget source allocation schema mismatch")
        _require_non_negative_int(
            self.source_allocation_issue_count,
            "source_allocation_issue_count",
        )
        _validate_digest(
            self.source_allocation_metadata_digest,
            "source_allocation_metadata_digest",
        )
        if self.budget_contract != RUNTIME_MEMORY_BUDGET_CONTRACT:
            raise ValueError("runtime memory budget contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime memory budget blocked surfaces changed")
        if type(self.budgets) is not tuple:
            raise TypeError("runtime memory budgets must be a tuple")
        if len(self.budgets) > MAX_RUNTIME_MEMORY_BUDGETS:
            raise ValueError("runtime memory budget count exceeds limit")
        for budget in self.budgets:
            if not isinstance(budget, RuntimeMemoryDomainBudget):
                raise TypeError("runtime memory budgets must be budget objects")
        if type(self.usages) is not tuple:
            raise TypeError("runtime memory usages must be a tuple")
        if len(self.usages) > MAX_RUNTIME_MEMORY_BUDGET_USAGES:
            raise ValueError("runtime memory usage count exceeds limit")
        for usage in self.usages:
            if not isinstance(usage, RuntimeMemoryDomainUsage):
                raise TypeError("runtime memory usages must be usage objects")
        if type(self.issues) is not tuple:
            raise TypeError("runtime memory budget issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_MEMORY_BUDGET_ISSUES:
            raise ValueError("runtime memory budget issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeMemoryBudgetIssue):
                raise TypeError("runtime memory budget issues must be issue objects")
        expected_issues = _derive_memory_budget_issues(
            self.source_allocation_issue_count,
            self.budgets,
            self.usages,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime memory budget issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether memory budget evidence passed."""

        return not self.issues

    @property
    def budget_count(self) -> int:
        """Return explicit memory-domain budget count."""

        return len(self.budgets)

    @property
    def usage_count(self) -> int:
        """Return used memory-domain count."""

        return len(self.usages)

    @property
    def total_reserved_bytes(self) -> int:
        """Return total reserved bytes across used memory domains."""

        return sum(usage.total_reserved_bytes for usage in self.usages)

    @property
    def total_peak_live_bytes(self) -> int:
        """Return conservative sum of per-domain peak live bytes."""

        return sum(usage.peak_live_bytes for usage in self.usages)


class RuntimeMemoryBudgetError(AssertionError):
    """Raised when runtime memory budget evidence fails."""


def build_runtime_memory_budget_report(
    allocation_report: RuntimeAllocationPlanReport,
    budgets: tuple[RuntimeMemoryDomainBudget, ...],
) -> RuntimeMemoryBudgetReport:
    """Build a bounded memory budget report from allocation-plan evidence."""

    if not isinstance(allocation_report, RuntimeAllocationPlanReport):
        raise TypeError("runtime memory budget source must be allocation report")
    if type(budgets) is not tuple:
        raise TypeError("runtime memory budgets must be a tuple")
    budget_by_domain = _first_budget_by_domain(budgets)
    usages = tuple(
        _usage_for_domain(allocation_report, budget_by_domain, domain)
        for domain in _used_domains(allocation_report)
    )
    issues = _derive_memory_budget_issues(
        len(allocation_report.issues),
        budgets,
        usages,
    )
    return RuntimeMemoryBudgetReport(
        graph_name=allocation_report.graph_name,
        operation_count=allocation_report.operation_count,
        source_allocation_contract=allocation_report.allocation_contract,
        source_allocation_schema_version=RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
        source_allocation_issue_count=len(allocation_report.issues),
        source_allocation_metadata_digest=allocation_report.allocation_metadata_digest,
        budgets=budgets,
        usages=usages,
        issues=issues,
    )


def assert_runtime_memory_budget(
    report: RuntimeMemoryBudgetReport,
) -> RuntimeMemoryBudgetReport:
    """Return the report or raise when runtime memory budget evidence fails."""

    if not isinstance(report, RuntimeMemoryBudgetReport):
        raise TypeError("runtime memory budget report must be report object")
    if report.issues:
        lines = [f"runtime memory budget failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeMemoryBudgetError("\n".join(lines))
    return report


def runtime_memory_budget_report_to_dict(
    report: RuntimeMemoryBudgetReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible runtime memory budget report."""

    if not isinstance(report, RuntimeMemoryBudgetReport):
        raise TypeError("runtime memory budget report must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "budget_contract": report.budget_contract,
        "budget_count": report.budget_count,
        "budgets": [
            {
                "budget_id": budget.budget_id,
                "max_peak_live_bytes": budget.max_peak_live_bytes,
                "max_reserved_bytes": budget.max_reserved_bytes,
                "memory_domain": budget.memory_domain.value,
            }
            for budget in report.budgets
        ],
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "operation_count": report.operation_count,
        "passed": report.passed,
        "schema_version": RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
        "source_allocation_contract": report.source_allocation_contract,
        "source_allocation_issue_count": report.source_allocation_issue_count,
        "source_allocation_metadata_digest": report.source_allocation_metadata_digest,
        "source_allocation_schema_version": report.source_allocation_schema_version,
        "total_peak_live_bytes": report.total_peak_live_bytes,
        "total_reserved_bytes": report.total_reserved_bytes,
        "usage_count": report.usage_count,
        "usages": [
            {
                "budget_id": usage.budget_id,
                "max_peak_live_bytes": usage.max_peak_live_bytes,
                "max_reserved_bytes": usage.max_reserved_bytes,
                "memory_domain": usage.memory_domain.value,
                "peak_live_bytes": usage.peak_live_bytes,
                "status": usage.status,
                "total_reserved_bytes": usage.total_reserved_bytes,
            }
            for usage in report.usages
        ],
    }


def dump_runtime_memory_budget_report(report: RuntimeMemoryBudgetReport) -> str:
    """Render a stable runtime memory budget report."""

    text = json.dumps(
        runtime_memory_budget_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_MEMORY_BUDGET_REPORT_BYTES:
        raise ValueError("runtime memory budget report exceeds byte limit")
    return text + "\n"


def _first_budget_by_domain(
    budgets: tuple[RuntimeMemoryDomainBudget, ...],
) -> dict[MemoryDomainKind, RuntimeMemoryDomainBudget]:
    result: dict[MemoryDomainKind, RuntimeMemoryDomainBudget] = {}
    for budget in budgets:
        if not isinstance(budget, RuntimeMemoryDomainBudget):
            raise TypeError("runtime memory budgets must be budget objects")
        result.setdefault(budget.memory_domain, budget)
    return result


def _used_domains(report: RuntimeAllocationPlanReport) -> tuple[MemoryDomainKind, ...]:
    domains = {binding.memory_domain for binding in report.bindings}
    domains.update(slot.memory_domain for slot in report.slots)
    return tuple(sorted(domains, key=lambda domain: domain.value))


def _usage_for_domain(
    report: RuntimeAllocationPlanReport,
    budget_by_domain: dict[MemoryDomainKind, RuntimeMemoryDomainBudget],
    domain: MemoryDomainKind,
) -> RuntimeMemoryDomainUsage:
    total_reserved_bytes = sum(
        slot.bytes_reserved for slot in report.slots if slot.memory_domain == domain
    )
    peak_live_bytes = _peak_live_bytes_for_domain(report.bindings, report.operation_count, domain)
    budget = budget_by_domain.get(domain)
    if budget is None:
        max_reserved_bytes = 0
        max_peak_live_bytes = 0
        budget_id = _MISSING_BUDGET_ID
    else:
        max_reserved_bytes = budget.max_reserved_bytes
        max_peak_live_bytes = budget.max_peak_live_bytes
        budget_id = budget.budget_id
    return RuntimeMemoryDomainUsage(
        memory_domain=domain,
        budget_id=budget_id,
        total_reserved_bytes=total_reserved_bytes,
        peak_live_bytes=peak_live_bytes,
        max_reserved_bytes=max_reserved_bytes,
        max_peak_live_bytes=max_peak_live_bytes,
        status=_derive_usage_status(
            total_reserved_bytes,
            peak_live_bytes,
            max_reserved_bytes,
            max_peak_live_bytes,
        ),
    )


def _peak_live_bytes_for_domain(
    bindings: tuple[RuntimeAllocationBinding, ...],
    operation_count: int,
    domain: MemoryDomainKind,
) -> int:
    peak = 0
    for point in range(operation_count + 1):
        live_bytes = sum(
            binding.bytes_required
            for binding in bindings
            if binding.memory_domain == domain
            and binding.first_live_index <= point <= binding.last_use_index
        )
        peak = max(peak, live_bytes)
    return peak


def _derive_usage_status(
    total_reserved_bytes: int,
    peak_live_bytes: int,
    max_reserved_bytes: int,
    max_peak_live_bytes: int,
) -> str:
    if max_reserved_bytes == 0 and max_peak_live_bytes == 0:
        return "missing_budget"
    reserved_exceeded = total_reserved_bytes > max_reserved_bytes
    peak_exceeded = peak_live_bytes > max_peak_live_bytes
    if reserved_exceeded and peak_exceeded:
        return "reserved_and_peak_exceeded"
    if reserved_exceeded:
        return "reserved_exceeded"
    if peak_exceeded:
        return "peak_exceeded"
    return "within_budget"


def _derive_memory_budget_issues(
    source_allocation_issue_count: int,
    budgets: tuple[RuntimeMemoryDomainBudget, ...],
    usages: tuple[RuntimeMemoryDomainUsage, ...],
) -> tuple[RuntimeMemoryBudgetIssue, ...]:
    issues: list[RuntimeMemoryBudgetIssue] = []
    if source_allocation_issue_count > 0:
        issues.append(
            RuntimeMemoryBudgetIssue(
                subject="source_allocation_report",
                issue_code="source_allocation_report_failed",
            )
        )
    if not budgets:
        issues.append(
            RuntimeMemoryBudgetIssue(
                subject="budgets",
                issue_code="memory_budgets_missing",
            )
        )
    if not usages:
        issues.append(
            RuntimeMemoryBudgetIssue(
                subject="usages",
                issue_code="memory_usages_missing",
            )
        )
    seen_domains: set[MemoryDomainKind] = set()
    duplicate_domains: set[MemoryDomainKind] = set()
    for budget in budgets:
        if budget.memory_domain in seen_domains:
            duplicate_domains.add(budget.memory_domain)
        seen_domains.add(budget.memory_domain)
    for domain in sorted(duplicate_domains, key=lambda item: item.value):
        issues.append(
            RuntimeMemoryBudgetIssue(
                subject=domain.value,
                issue_code="duplicate_memory_domain_budget",
            )
        )
    for usage in usages:
        issue_code = _issue_code_for_usage_status(usage.status)
        if issue_code is not None:
            issues.append(
                RuntimeMemoryBudgetIssue(
                    subject=usage.memory_domain.value,
                    issue_code=issue_code,
                )
            )
    return tuple(issues)


def _issue_code_for_usage_status(status: str) -> str | None:
    if status == "within_budget":
        return None
    if status == "missing_budget":
        return "memory_domain_budget_missing"
    if status == "reserved_exceeded":
        return "reserved_bytes_exceed_budget"
    if status == "peak_exceeded":
        return "peak_live_bytes_exceed_budget"
    if status == "reserved_and_peak_exceeded":
        return "reserved_and_peak_bytes_exceed_budget"
    raise ValueError("memory usage status is unsupported")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _MEMORY_BUDGET_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime memory budget identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_MEMORY_BUDGET_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime memory budget field limit")
    if value in _FORBIDDEN_MEMORY_BUDGET_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be a sha256 metadata digest")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


__all__ = [
    "MAX_RUNTIME_MEMORY_BUDGETS",
    "MAX_RUNTIME_MEMORY_BUDGET_FIELD_BYTES",
    "MAX_RUNTIME_MEMORY_BUDGET_ISSUES",
    "MAX_RUNTIME_MEMORY_BUDGET_REPORT_BYTES",
    "MAX_RUNTIME_MEMORY_BUDGET_USAGES",
    "RUNTIME_MEMORY_BUDGET_CONTRACT",
    "RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION",
    "RuntimeMemoryBudgetError",
    "RuntimeMemoryBudgetIssue",
    "RuntimeMemoryBudgetReport",
    "RuntimeMemoryDomainBudget",
    "RuntimeMemoryDomainUsage",
    "assert_runtime_memory_budget",
    "build_runtime_memory_budget_report",
    "dump_runtime_memory_budget_report",
    "runtime_memory_budget_report_to_dict",
]
