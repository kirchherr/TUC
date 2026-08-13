"""Data-only backend capability coverage reports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.base import BackendCapability
from tuc.backends.conformance import (
    MVP_CONFORMANCE_OPERATION_KINDS,
    build_conformance_graph,
)
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_CAPABILITY_COVERAGE_REPORT_SCHEMA_VERSION = (
    "tuc.backend_capability_coverage_report.v0"
)
BACKEND_CAPABILITY_COVERAGE_CONTRACT = "backend_capability_coverage.data_only.v0"
BACKEND_CAPABILITY_COVERAGE_STATUSES = frozenset({"complete", "partial"})
BACKEND_CAPABILITY_COVERAGE_ROW_STATUSES = frozenset({"covered", "missing"})
MAX_BACKEND_CAPABILITY_COVERAGE_BACKENDS = 32
MAX_BACKEND_CAPABILITY_COVERAGE_OPERATIONS = 16
MAX_BACKEND_CAPABILITY_COVERAGE_ISSUES = 64
MAX_BACKEND_CAPABILITY_COVERAGE_FIELD_BYTES = 512
MAX_BACKEND_CAPABILITY_COVERAGE_REPORT_BYTES = 64 * 1024

_COVERAGE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_COVERAGE_TEXT = frozenset(
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
class BackendCapabilityCoverageRow:
    """Coverage result for one neutral operation family."""

    operation_kind: OperationKind
    accepting_backends: tuple[str, ...]
    preferred_backends: tuple[str, ...]
    memory_domains: tuple[MemoryDomainKind, ...]
    produced_layouts: tuple[LayoutKind, ...]
    status: str

    def __post_init__(self) -> None:
        if not isinstance(self.operation_kind, OperationKind):
            raise TypeError("coverage operation_kind must be OperationKind")
        _validate_name_tuple(self.accepting_backends, "accepting_backends")
        _validate_name_tuple(self.preferred_backends, "preferred_backends")
        _validate_memory_domain_tuple(self.memory_domains, "memory_domains")
        _validate_layout_tuple(self.produced_layouts, "produced_layouts")
        if self.status not in BACKEND_CAPABILITY_COVERAGE_ROW_STATUSES:
            raise ValueError("coverage row status is unsupported")
        if self.status == "covered" and not self.accepting_backends:
            raise ValueError("covered operation must have accepting backends")
        if self.status == "missing" and (
            self.accepting_backends
            or self.preferred_backends
            or self.memory_domains
            or self.produced_layouts
        ):
            raise ValueError("missing operation must not report accepted coverage")


@dataclass(frozen=True)
class BackendCapabilityCoverageIssue:
    """One capability coverage issue."""

    operation_kind: OperationKind
    issue_code: str

    def __post_init__(self) -> None:
        if not isinstance(self.operation_kind, OperationKind):
            raise TypeError("coverage issue operation_kind must be OperationKind")
        _validate_coverage_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class BackendCapabilityCoverageReport:
    """Deterministic pure-data capability coverage matrix."""

    backend_names: tuple[str, ...]
    required_operation_kinds: tuple[OperationKind, ...]
    rows: tuple[BackendCapabilityCoverageRow, ...]
    issues: tuple[BackendCapabilityCoverageIssue, ...]
    coverage_contract: str = BACKEND_CAPABILITY_COVERAGE_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.coverage_contract != BACKEND_CAPABILITY_COVERAGE_CONTRACT:
            raise ValueError("backend capability coverage contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend capability coverage blocked surfaces changed")
        _validate_name_tuple(self.backend_names, "backend_names")
        if not self.backend_names:
            raise ValueError("backend capability coverage requires at least one backend")
        if len(self.backend_names) > MAX_BACKEND_CAPABILITY_COVERAGE_BACKENDS:
            raise ValueError("backend capability coverage backend count exceeds limit")
        if len(self.backend_names) != len(set(self.backend_names)):
            raise ValueError("backend capability coverage backend names must be unique")
        _validate_operation_tuple(
            self.required_operation_kinds,
            "required_operation_kinds",
        )
        if not self.required_operation_kinds:
            raise ValueError("backend capability coverage requires operation kinds")
        if len(self.required_operation_kinds) > MAX_BACKEND_CAPABILITY_COVERAGE_OPERATIONS:
            raise ValueError("backend capability coverage operation count exceeds limit")
        if len(self.required_operation_kinds) != len(set(self.required_operation_kinds)):
            raise ValueError("backend capability coverage operation kinds must be unique")
        if type(self.rows) is not tuple:
            raise TypeError("backend capability coverage rows must be a tuple")
        if tuple(row.operation_kind for row in self.rows) != self.required_operation_kinds:
            raise ValueError("backend capability coverage rows must match operation order")
        for row in self.rows:
            if not isinstance(row, BackendCapabilityCoverageRow):
                raise TypeError("backend capability coverage rows must be row objects")
            for backend_name in row.accepting_backends + row.preferred_backends:
                if backend_name not in self.backend_names:
                    raise ValueError("coverage row references unknown backend")
        if type(self.issues) is not tuple:
            raise TypeError("backend capability coverage issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_CAPABILITY_COVERAGE_ISSUES:
            raise ValueError("backend capability coverage issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendCapabilityCoverageIssue):
                raise TypeError("backend capability coverage issues must be issue objects")
        if self.issues != _derive_coverage_issues(self.rows):
            raise ValueError("backend capability coverage issues must be derived")

    @property
    def complete(self) -> bool:
        """Return whether every required operation family is covered."""

        return not self.issues

    @property
    def coverage_status(self) -> str:
        """Return the report-level coverage status."""

        return "complete" if self.complete else "partial"


class BackendCapabilityCoverageError(AssertionError):
    """Raised when a capability coverage report is incomplete."""


def build_backend_capability_coverage_report(
    capabilities: tuple[BackendCapability, ...],
    *,
    operation_kinds: tuple[
        OperationKind, ...
    ] = MVP_CONFORMANCE_OPERATION_KINDS,
) -> BackendCapabilityCoverageReport:
    """Build a pure-data coverage matrix from backend capabilities."""

    _validate_capability_tuple(capabilities)
    _validate_operation_tuple(operation_kinds, "operation_kinds")
    backend_names = tuple(sorted(capability.name for capability in capabilities))
    capabilities_by_name = {
        capability.name: capability
        for capability in sorted(capabilities, key=lambda item: item.name)
    }
    rows = tuple(
        _coverage_row(operation_kind, capabilities_by_name)
        for operation_kind in operation_kinds
    )
    return BackendCapabilityCoverageReport(
        backend_names=backend_names,
        required_operation_kinds=operation_kinds,
        rows=rows,
        issues=_derive_coverage_issues(rows),
    )


def assert_backend_capability_coverage(
    report: BackendCapabilityCoverageReport,
) -> BackendCapabilityCoverageReport:
    """Return the report or raise when required operation coverage is missing."""

    if not isinstance(report, BackendCapabilityCoverageReport):
        raise TypeError("backend capability coverage report must be report object")
    if report.issues:
        lines = ["backend capability coverage is incomplete:"]
        lines.extend(
            f"- {issue.operation_kind.value}:{issue.issue_code}"
            for issue in report.issues
        )
        raise BackendCapabilityCoverageError("\n".join(lines))
    return report


def backend_capability_coverage_report_to_dict(
    report: BackendCapabilityCoverageReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible capability coverage report."""

    if not isinstance(report, BackendCapabilityCoverageReport):
        raise TypeError("backend capability coverage report must be report object")
    return {
        "backend_count": len(report.backend_names),
        "backend_names": list(report.backend_names),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "complete": report.complete,
        "coverage_contract": report.coverage_contract,
        "coverage_status": report.coverage_status,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "operation_kind": issue.operation_kind.value,
            }
            for issue in report.issues
        ],
        "operation_count": len(report.required_operation_kinds),
        "required_operation_kinds": [
            operation.value for operation in report.required_operation_kinds
        ],
        "rows": [
            {
                "accepting_backends": list(row.accepting_backends),
                "memory_domains": [domain.value for domain in row.memory_domains],
                "operation_kind": row.operation_kind.value,
                "preferred_backends": list(row.preferred_backends),
                "produced_layouts": [layout.value for layout in row.produced_layouts],
                "status": row.status,
            }
            for row in report.rows
        ],
        "schema_version": BACKEND_CAPABILITY_COVERAGE_REPORT_SCHEMA_VERSION,
    }


def dump_backend_capability_coverage_report(
    report: BackendCapabilityCoverageReport,
) -> str:
    """Render a stable backend capability coverage matrix."""

    text = json.dumps(
        backend_capability_coverage_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_CAPABILITY_COVERAGE_REPORT_BYTES:
        raise ValueError("backend capability coverage report exceeds byte limit")
    return text + "\n"


def _coverage_row(
    operation_kind: OperationKind,
    capabilities_by_name: dict[str, BackendCapability],
) -> BackendCapabilityCoverageRow:
    operation = build_conformance_graph(operation_kind).operations[0]
    accepting: list[str] = []
    preferred: list[str] = []
    memory_domains: set[MemoryDomainKind] = set()
    produced_layouts: set[LayoutKind] = set()

    for backend_name, capability in capabilities_by_name.items():
        if not capability.supports(operation):
            continue
        accepting.append(backend_name)
        if operation_kind in capability.preferred_for:
            preferred.append(backend_name)
        memory_domains.add(capability.memory_domain)
        produced_layouts.add(capability.produced_layout_for(operation))

    return BackendCapabilityCoverageRow(
        operation_kind=operation_kind,
        accepting_backends=tuple(accepting),
        preferred_backends=tuple(preferred),
        memory_domains=tuple(sorted(memory_domains, key=lambda item: item.value)),
        produced_layouts=tuple(sorted(produced_layouts, key=lambda item: item.value)),
        status="covered" if accepting else "missing",
    )


def _derive_coverage_issues(
    rows: tuple[BackendCapabilityCoverageRow, ...],
) -> tuple[BackendCapabilityCoverageIssue, ...]:
    return tuple(
        BackendCapabilityCoverageIssue(
            operation_kind=row.operation_kind,
            issue_code="operation_kind_not_covered",
        )
        for row in rows
        if row.status == "missing"
    )


def _validate_capability_tuple(capabilities: tuple[BackendCapability, ...]) -> None:
    if type(capabilities) is not tuple:
        raise TypeError("backend capability coverage capabilities must be a tuple")
    if not capabilities:
        raise ValueError("backend capability coverage requires at least one capability")
    if len(capabilities) > MAX_BACKEND_CAPABILITY_COVERAGE_BACKENDS:
        raise ValueError("backend capability coverage capability count exceeds limit")
    names: list[str] = []
    for capability in capabilities:
        if not isinstance(capability, BackendCapability):
            raise TypeError("backend capability coverage inputs must be capabilities")
        _validate_coverage_text(capability.name, "backend_name")
        names.append(capability.name)
    if len(names) != len(set(names)):
        raise ValueError("backend capability coverage backend names must be unique")


def _validate_name_tuple(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    for value in values:
        _validate_coverage_text(value, label)


def _validate_operation_tuple(values: tuple[OperationKind, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    for value in values:
        if not isinstance(value, OperationKind):
            raise TypeError(f"{label} must contain OperationKind values")


def _validate_memory_domain_tuple(
    values: tuple[MemoryDomainKind, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    for value in values:
        if not isinstance(value, MemoryDomainKind):
            raise TypeError(f"{label} must contain MemoryDomainKind values")


def _validate_layout_tuple(values: tuple[LayoutKind, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    for value in values:
        if not isinstance(value, LayoutKind):
            raise TypeError(f"{label} must contain LayoutKind values")


def _validate_coverage_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _COVERAGE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend capability coverage identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_CAPABILITY_COVERAGE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend capability coverage field limit")
    if value in _FORBIDDEN_COVERAGE_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "BACKEND_CAPABILITY_COVERAGE_CONTRACT",
    "BACKEND_CAPABILITY_COVERAGE_REPORT_SCHEMA_VERSION",
    "BACKEND_CAPABILITY_COVERAGE_ROW_STATUSES",
    "BACKEND_CAPABILITY_COVERAGE_STATUSES",
    "MAX_BACKEND_CAPABILITY_COVERAGE_BACKENDS",
    "MAX_BACKEND_CAPABILITY_COVERAGE_FIELD_BYTES",
    "MAX_BACKEND_CAPABILITY_COVERAGE_ISSUES",
    "MAX_BACKEND_CAPABILITY_COVERAGE_OPERATIONS",
    "MAX_BACKEND_CAPABILITY_COVERAGE_REPORT_BYTES",
    "BackendCapabilityCoverageError",
    "BackendCapabilityCoverageIssue",
    "BackendCapabilityCoverageReport",
    "BackendCapabilityCoverageRow",
    "assert_backend_capability_coverage",
    "backend_capability_coverage_report_to_dict",
    "build_backend_capability_coverage_report",
    "dump_backend_capability_coverage_report",
]
