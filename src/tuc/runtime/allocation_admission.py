"""Data-only allocation admission evidence for future allocator behavior."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.ir.memory import MemoryDomainKind
from tuc.runtime.allocation_request_manifest import (
    RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY,
    RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT,
    RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_REQUEST_STATUS,
    RuntimeAllocationRequestManifestReport,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.memory_budget import (
    RUNTIME_MEMORY_BUDGET_CONTRACT,
    RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
    RuntimeMemoryBudgetReport,
)

RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_allocation_admission_report.v0"
)
RUNTIME_ALLOCATION_ADMISSION_CONTRACT = "runtime_allocation_admission.data_only.v0"
RUNTIME_ALLOCATION_ADMISSION_STATUS = "admitted_by_budget_evidence"
RUNTIME_ALLOCATION_ADMISSION_BLOCKED_STATUS = "blocked_by_budget_evidence"
RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY = RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
MAX_RUNTIME_ALLOCATION_ADMISSIONS = 8192
MAX_RUNTIME_ALLOCATION_ADMISSION_ISSUES = 64
MAX_RUNTIME_ALLOCATION_ADMISSION_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_ALLOCATION_ADMISSION_FIELD_BYTES = 512

_ADMISSION_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_ADMISSION_TEXT = frozenset(
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
        "runtime_handle",
        "subprocess",
        "url",
    }
)
_ADMISSION_STATUSES = frozenset(
    {
        RUNTIME_ALLOCATION_ADMISSION_STATUS,
        RUNTIME_ALLOCATION_ADMISSION_BLOCKED_STATUS,
    }
)
_MISSING_BUDGET_ID = "missing_budget"


@dataclass(frozen=True)
class RuntimeAllocationAdmission:
    """One data-only allocator-admission decision for a request."""

    request_id: str
    slot_id: str
    memory_domain: MemoryDomainKind
    budget_id: str
    bytes_reserved: int
    domain_total_reserved_bytes: int
    domain_max_reserved_bytes: int
    admission_status: str
    handle_policy: str = RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY

    def __post_init__(self) -> None:
        _validate_text(self.request_id, "allocation admission request_id")
        _validate_text(self.slot_id, "allocation admission slot_id")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("allocation admission memory_domain must be MemoryDomainKind")
        _validate_text(self.budget_id, "allocation admission budget_id")
        _require_positive_int(self.bytes_reserved, "bytes_reserved")
        _require_non_negative_int(
            self.domain_total_reserved_bytes,
            "domain_total_reserved_bytes",
        )
        _require_non_negative_int(
            self.domain_max_reserved_bytes,
            "domain_max_reserved_bytes",
        )
        if self.admission_status not in _ADMISSION_STATUSES:
            raise ValueError("allocation admission status is unsupported")
        if self.handle_policy != RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY:
            raise ValueError("allocation admission must not expose runtime handles")


@dataclass(frozen=True)
class RuntimeAllocationAdmissionIssue:
    """One derived allocation-admission issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "allocation admission issue subject")
        _validate_text(self.issue_code, "allocation admission issue_code")


@dataclass(frozen=True)
class RuntimeAllocationAdmissionReport:
    """Deterministic admission report for future allocator behavior."""

    graph_name: str
    operation_count: int
    source_request_manifest_contract: str
    source_request_manifest_schema_version: str
    source_request_manifest_issue_count: int
    source_request_manifest_metadata_digest: str
    source_request_manifest_budget_allocation_digest: str
    source_memory_budget_contract: str
    source_memory_budget_schema_version: str
    source_memory_budget_issue_count: int
    source_memory_budget_allocation_digest: str
    admissions: tuple[RuntimeAllocationAdmission, ...]
    issues: tuple[RuntimeAllocationAdmissionIssue, ...]
    admission_contract: str = RUNTIME_ALLOCATION_ADMISSION_CONTRACT
    handle_policy: str = RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "allocation admission graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.source_request_manifest_contract != RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT:
            raise ValueError("allocation admission request manifest contract mismatch")
        if (
            self.source_request_manifest_schema_version
            != RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("allocation admission request manifest schema mismatch")
        _require_non_negative_int(
            self.source_request_manifest_issue_count,
            "source_request_manifest_issue_count",
        )
        _validate_digest(
            self.source_request_manifest_metadata_digest,
            "source_request_manifest_metadata_digest",
        )
        _validate_digest(
            self.source_request_manifest_budget_allocation_digest,
            "source_request_manifest_budget_allocation_digest",
        )
        if self.source_memory_budget_contract != RUNTIME_MEMORY_BUDGET_CONTRACT:
            raise ValueError("allocation admission memory budget contract mismatch")
        if self.source_memory_budget_schema_version != RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION:
            raise ValueError("allocation admission memory budget schema mismatch")
        _require_non_negative_int(
            self.source_memory_budget_issue_count,
            "source_memory_budget_issue_count",
        )
        _validate_digest(
            self.source_memory_budget_allocation_digest,
            "source_memory_budget_allocation_digest",
        )
        if self.admission_contract != RUNTIME_ALLOCATION_ADMISSION_CONTRACT:
            raise ValueError("runtime allocation admission contract mismatch")
        if self.handle_policy != RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY:
            raise ValueError("runtime allocation admission must not use handles")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime allocation admission blocked surfaces changed")
        if type(self.admissions) is not tuple:
            raise TypeError("runtime allocation admissions must be a tuple")
        if len(self.admissions) > MAX_RUNTIME_ALLOCATION_ADMISSIONS:
            raise ValueError("runtime allocation admission count exceeds limit")
        for admission in self.admissions:
            if not isinstance(admission, RuntimeAllocationAdmission):
                raise TypeError("runtime allocation admissions must be admission objects")
        if type(self.issues) is not tuple:
            raise TypeError("runtime allocation admission issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_ALLOCATION_ADMISSION_ISSUES:
            raise ValueError("runtime allocation admission issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeAllocationAdmissionIssue):
                raise TypeError("runtime allocation admission issues must be issue objects")
        expected_issues = _derive_admission_issues(
            self.source_request_manifest_issue_count,
            self.source_memory_budget_issue_count,
            self.source_request_manifest_budget_allocation_digest,
            self.source_memory_budget_allocation_digest,
            self.admissions,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime allocation admission issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether allocation admission evidence passed."""

        return not self.issues

    @property
    def admission_count(self) -> int:
        """Return admission decision count."""

        return len(self.admissions)

    @property
    def blocked_admission_count(self) -> int:
        """Return the number of blocked admission decisions."""

        return sum(
            1
            for admission in self.admissions
            if admission.admission_status != RUNTIME_ALLOCATION_ADMISSION_STATUS
        )

    @property
    def total_admitted_bytes(self) -> int:
        """Return total bytes represented by admitted decisions."""

        return sum(
            admission.bytes_reserved
            for admission in self.admissions
            if admission.admission_status == RUNTIME_ALLOCATION_ADMISSION_STATUS
        )


class RuntimeAllocationAdmissionError(AssertionError):
    """Raised when runtime allocation admission evidence fails."""


def build_runtime_allocation_admission_report(
    request_manifest_report: RuntimeAllocationRequestManifestReport,
    memory_budget_report: RuntimeMemoryBudgetReport,
) -> RuntimeAllocationAdmissionReport:
    """Build data-only allocator-admission evidence from request and budget data."""

    if not isinstance(request_manifest_report, RuntimeAllocationRequestManifestReport):
        raise TypeError("allocation admission source must be request manifest report")
    if not isinstance(memory_budget_report, RuntimeMemoryBudgetReport):
        raise TypeError("allocation admission budget source must be memory budget report")
    usage_by_domain = {usage.memory_domain: usage for usage in memory_budget_report.usages}
    sources_passed = (
        request_manifest_report.passed
        and memory_budget_report.passed
        and request_manifest_report.source_memory_budget_allocation_digest
        == memory_budget_report.source_allocation_metadata_digest
    )
    admissions = tuple(
        _admission_from_request(request, usage_by_domain, sources_passed)
        for request in request_manifest_report.requests
    )
    return RuntimeAllocationAdmissionReport(
        graph_name=request_manifest_report.graph_name,
        operation_count=request_manifest_report.operation_count,
        source_request_manifest_contract=request_manifest_report.manifest_contract,
        source_request_manifest_schema_version=(
            RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION
        ),
        source_request_manifest_issue_count=len(request_manifest_report.issues),
        source_request_manifest_metadata_digest=(
            request_manifest_report.manifest_metadata_digest
        ),
        source_request_manifest_budget_allocation_digest=(
            request_manifest_report.source_memory_budget_allocation_digest
        ),
        source_memory_budget_contract=memory_budget_report.budget_contract,
        source_memory_budget_schema_version=RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
        source_memory_budget_issue_count=len(memory_budget_report.issues),
        source_memory_budget_allocation_digest=(
            memory_budget_report.source_allocation_metadata_digest
        ),
        admissions=admissions,
        issues=_derive_admission_issues(
            len(request_manifest_report.issues),
            len(memory_budget_report.issues),
            request_manifest_report.source_memory_budget_allocation_digest,
            memory_budget_report.source_allocation_metadata_digest,
            admissions,
        ),
    )


def assert_runtime_allocation_admission(
    report: RuntimeAllocationAdmissionReport,
) -> RuntimeAllocationAdmissionReport:
    """Return the report or raise when allocation admission evidence fails."""

    if not isinstance(report, RuntimeAllocationAdmissionReport):
        raise TypeError("runtime allocation admission must be report object")
    if report.issues:
        lines = [f"runtime allocation admission failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeAllocationAdmissionError("\n".join(lines))
    return report


def runtime_allocation_admission_report_to_dict(
    report: RuntimeAllocationAdmissionReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible allocation admission report."""

    if not isinstance(report, RuntimeAllocationAdmissionReport):
        raise TypeError("runtime allocation admission must be report object")
    return {
        "admission_contract": report.admission_contract,
        "admission_count": report.admission_count,
        "admissions": [
            {
                "admission_status": admission.admission_status,
                "budget_id": admission.budget_id,
                "bytes_reserved": admission.bytes_reserved,
                "domain_max_reserved_bytes": admission.domain_max_reserved_bytes,
                "domain_total_reserved_bytes": admission.domain_total_reserved_bytes,
                "handle_policy": admission.handle_policy,
                "memory_domain": admission.memory_domain.value,
                "request_id": admission.request_id,
                "slot_id": admission.slot_id,
            }
            for admission in report.admissions
        ],
        "blocked_admission_count": report.blocked_admission_count,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "graph_name": report.graph_name,
        "handle_policy": report.handle_policy,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "operation_count": report.operation_count,
        "passed": report.passed,
        "schema_version": RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
        "source_memory_budget_allocation_digest": (
            report.source_memory_budget_allocation_digest
        ),
        "source_memory_budget_contract": report.source_memory_budget_contract,
        "source_memory_budget_issue_count": report.source_memory_budget_issue_count,
        "source_memory_budget_schema_version": (
            report.source_memory_budget_schema_version
        ),
        "source_request_manifest_budget_allocation_digest": (
            report.source_request_manifest_budget_allocation_digest
        ),
        "source_request_manifest_contract": report.source_request_manifest_contract,
        "source_request_manifest_issue_count": (
            report.source_request_manifest_issue_count
        ),
        "source_request_manifest_metadata_digest": (
            report.source_request_manifest_metadata_digest
        ),
        "source_request_manifest_schema_version": (
            report.source_request_manifest_schema_version
        ),
        "total_admitted_bytes": report.total_admitted_bytes,
    }


def dump_runtime_allocation_admission_report(
    report: RuntimeAllocationAdmissionReport,
) -> str:
    """Render stable data-only allocation admission evidence."""

    text = json.dumps(
        runtime_allocation_admission_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_ADMISSION_REPORT_BYTES:
        raise ValueError("runtime allocation admission report exceeds byte limit")
    return text + "\n"


def _admission_from_request(
    request: object,
    usage_by_domain: object,
    sources_passed: bool,
) -> RuntimeAllocationAdmission:
    from tuc.runtime.allocation_request_manifest import RuntimeAllocationRequest

    if not isinstance(request, RuntimeAllocationRequest):
        raise TypeError("allocation admission request must be request object")
    if not isinstance(usage_by_domain, dict):
        raise TypeError("allocation admission usage lookup must be a dict")
    usage = usage_by_domain.get(request.memory_domain)
    if usage is None:
        budget_id = _MISSING_BUDGET_ID
        domain_total_reserved_bytes = 0
        domain_max_reserved_bytes = 0
        admitted = False
    else:
        budget_id = usage.budget_id
        domain_total_reserved_bytes = usage.total_reserved_bytes
        domain_max_reserved_bytes = usage.max_reserved_bytes
        admitted = usage.status == "within_budget"
    admitted = (
        admitted
        and sources_passed
        and request.request_status == RUNTIME_ALLOCATION_REQUEST_STATUS
        and request.handle_policy == RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
    )
    return RuntimeAllocationAdmission(
        request_id=request.request_id,
        slot_id=request.slot_id,
        memory_domain=request.memory_domain,
        budget_id=budget_id,
        bytes_reserved=request.bytes_reserved,
        domain_total_reserved_bytes=domain_total_reserved_bytes,
        domain_max_reserved_bytes=domain_max_reserved_bytes,
        admission_status=(
            RUNTIME_ALLOCATION_ADMISSION_STATUS
            if admitted
            else RUNTIME_ALLOCATION_ADMISSION_BLOCKED_STATUS
        ),
        handle_policy=request.handle_policy,
    )


def _derive_admission_issues(
    source_request_manifest_issue_count: int,
    source_memory_budget_issue_count: int,
    source_request_manifest_budget_allocation_digest: str,
    source_memory_budget_allocation_digest: str,
    admissions: tuple[RuntimeAllocationAdmission, ...],
) -> tuple[RuntimeAllocationAdmissionIssue, ...]:
    issues: list[RuntimeAllocationAdmissionIssue] = []
    if source_request_manifest_issue_count > 0:
        issues.append(
            RuntimeAllocationAdmissionIssue(
                subject="source_request_manifest",
                issue_code="source_request_manifest_failed",
            )
        )
    if source_memory_budget_issue_count > 0:
        issues.append(
            RuntimeAllocationAdmissionIssue(
                subject="source_memory_budget",
                issue_code="source_memory_budget_failed",
            )
        )
    if source_request_manifest_budget_allocation_digest != source_memory_budget_allocation_digest:
        issues.append(
            RuntimeAllocationAdmissionIssue(
                subject="source_memory_budget",
                issue_code="source_memory_budget_digest_mismatch",
            )
        )
    if not admissions:
        issues.append(
            RuntimeAllocationAdmissionIssue(
                subject="admissions",
                issue_code="allocation_admissions_missing",
            )
        )
    request_ids = {admission.request_id for admission in admissions}
    if len(request_ids) != len(admissions):
        issues.append(
            RuntimeAllocationAdmissionIssue(
                subject="admissions",
                issue_code="duplicate_request_id",
            )
        )
    slot_ids = {admission.slot_id for admission in admissions}
    if len(slot_ids) != len(admissions):
        issues.append(
            RuntimeAllocationAdmissionIssue(
                subject="admissions",
                issue_code="duplicate_slot_id",
            )
        )
    for admission in admissions:
        if admission.admission_status != RUNTIME_ALLOCATION_ADMISSION_STATUS:
            issues.append(
                RuntimeAllocationAdmissionIssue(
                    subject=admission.request_id,
                    issue_code="allocation_admission_blocked",
                )
            )
    return tuple(issues)


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ADMISSION_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe allocation admission identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_ADMISSION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds allocation admission field limit")
    if value in _FORBIDDEN_ADMISSION_TEXT:
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
    "MAX_RUNTIME_ALLOCATION_ADMISSION_FIELD_BYTES",
    "MAX_RUNTIME_ALLOCATION_ADMISSION_ISSUES",
    "MAX_RUNTIME_ALLOCATION_ADMISSION_REPORT_BYTES",
    "MAX_RUNTIME_ALLOCATION_ADMISSIONS",
    "RUNTIME_ALLOCATION_ADMISSION_BLOCKED_STATUS",
    "RUNTIME_ALLOCATION_ADMISSION_CONTRACT",
    "RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY",
    "RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION",
    "RUNTIME_ALLOCATION_ADMISSION_STATUS",
    "RuntimeAllocationAdmission",
    "RuntimeAllocationAdmissionError",
    "RuntimeAllocationAdmissionIssue",
    "RuntimeAllocationAdmissionReport",
    "assert_runtime_allocation_admission",
    "build_runtime_allocation_admission_report",
    "dump_runtime_allocation_admission_report",
    "runtime_allocation_admission_report_to_dict",
]
