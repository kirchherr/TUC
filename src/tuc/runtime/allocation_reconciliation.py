"""Data-only allocation reconciliation evidence for future allocators."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import MemoryDomainKind
from tuc.runtime.allocation_admission import (
    RUNTIME_ALLOCATION_ADMISSION_CONTRACT,
    RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY,
    RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
    RuntimeAllocationAdmission,
    RuntimeAllocationAdmissionReport,
)
from tuc.runtime.allocation_receipt import (
    RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE,
    RUNTIME_ALLOCATION_RECEIPT_CONTRACT,
    RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION,
    RuntimeAllocationReceipt,
    RuntimeAllocationReceiptReport,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

RUNTIME_ALLOCATION_RECONCILIATION_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_allocation_reconciliation_report.v0"
)
RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT = (
    "runtime_allocation_reconciliation.data_only.v0"
)
RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID = (
    "allocation_reconciliation.no_handles.no_pointers.contiguous_offsets.v0"
)
RUNTIME_ALLOCATION_RECONCILIATION_STATUS = "reconciled_by_policy"
RUNTIME_ALLOCATION_RECONCILIATION_ROW_STATUS = "reconciled"
RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY = (
    RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
)
MAX_RUNTIME_ALLOCATION_RECONCILIATION_ROWS = 8192
MAX_RUNTIME_ALLOCATION_RECONCILIATION_ISSUES = 96
MAX_RUNTIME_ALLOCATION_RECONCILIATION_REPORT_BYTES = 160 * 1024
MAX_RUNTIME_ALLOCATION_RECONCILIATION_FIELD_BYTES = 512

_RECONCILIATION_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_RECONCILIATION_TEXT = frozenset(
    {
        "allocator_handle",
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "device_pointer",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "memory_address",
        "memory_handle",
        "module",
        "network",
        "plugin_entrypoint",
        "pointer",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "runtime_handle",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeAllocationReconciliationRow:
    """One admission-to-receipt row reconciled without runtime handles."""

    row_id: str
    admission_request_id: str
    receipt_request_id: str
    admission_slot_id: str
    receipt_slot_id: str
    receipt_id: str
    admission_memory_domain: MemoryDomainKind
    receipt_memory_domain: MemoryDomainKind
    admission_budget_id: str
    receipt_budget_id: str
    admitted_bytes: int
    receipted_bytes: int
    domain_offset_bytes: int
    domain_end_bytes: int
    domain_total_reserved_bytes: int
    domain_max_reserved_bytes: int
    row_status: str = RUNTIME_ALLOCATION_RECONCILIATION_ROW_STATUS

    def __post_init__(self) -> None:
        _validate_text(self.row_id, "allocation reconciliation row_id")
        _validate_text(
            self.admission_request_id,
            "allocation reconciliation admission_request_id",
        )
        _validate_text(
            self.receipt_request_id,
            "allocation reconciliation receipt_request_id",
        )
        _validate_text(
            self.admission_slot_id,
            "allocation reconciliation admission_slot_id",
        )
        _validate_text(
            self.receipt_slot_id,
            "allocation reconciliation receipt_slot_id",
        )
        _validate_text(self.receipt_id, "allocation reconciliation receipt_id")
        if not isinstance(self.admission_memory_domain, MemoryDomainKind):
            raise TypeError("admission memory domain must be MemoryDomainKind")
        if not isinstance(self.receipt_memory_domain, MemoryDomainKind):
            raise TypeError("receipt memory domain must be MemoryDomainKind")
        _validate_text(
            self.admission_budget_id,
            "allocation reconciliation admission_budget_id",
        )
        _validate_text(
            self.receipt_budget_id,
            "allocation reconciliation receipt_budget_id",
        )
        _require_positive_int(self.admitted_bytes, "admitted_bytes")
        _require_positive_int(self.receipted_bytes, "receipted_bytes")
        _require_non_negative_int(self.domain_offset_bytes, "domain_offset_bytes")
        _require_non_negative_int(self.domain_end_bytes, "domain_end_bytes")
        _require_non_negative_int(
            self.domain_total_reserved_bytes,
            "domain_total_reserved_bytes",
        )
        _require_non_negative_int(
            self.domain_max_reserved_bytes,
            "domain_max_reserved_bytes",
        )
        if self.domain_offset_bytes + self.receipted_bytes != self.domain_end_bytes:
            raise ValueError("allocation reconciliation row span mismatch")
        if self.domain_end_bytes > self.domain_total_reserved_bytes:
            raise ValueError("allocation reconciliation row exceeds domain total")
        if self.domain_total_reserved_bytes > self.domain_max_reserved_bytes:
            raise ValueError("allocation reconciliation row exceeds domain budget")
        if self.row_status != RUNTIME_ALLOCATION_RECONCILIATION_ROW_STATUS:
            raise ValueError("allocation reconciliation row status is unsupported")


@dataclass(frozen=True)
class RuntimeAllocationReconciliationIssue:
    """One derived allocation reconciliation issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "allocation reconciliation issue subject")
        _validate_text(self.issue_code, "allocation reconciliation issue_code")


@dataclass(frozen=True)
class RuntimeAllocationReconciliationReport:
    """Policy evidence that Admission and Receipt describe the same ledger."""

    graph_name: str
    operation_count: int
    source_admission_contract: str
    source_admission_schema_version: str
    source_admission_issue_count: int
    source_admission_metadata_digest: str
    source_admission_count: int
    source_admission_total_admitted_bytes: int
    source_receipt_contract: str
    source_receipt_schema_version: str
    source_receipt_issue_count: int
    source_receipt_metadata_digest: str
    source_receipt_source_admission_metadata_digest: str
    source_receipt_count: int
    source_receipt_total_receipted_bytes: int
    rows: tuple[RuntimeAllocationReconciliationRow, ...]
    issues: tuple[RuntimeAllocationReconciliationIssue, ...]
    reconciliation_contract: str = RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT
    reconciliation_policy_id: str = RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID
    reconciliation_status: str = RUNTIME_ALLOCATION_RECONCILIATION_STATUS
    allocation_mode: str = RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    handle_policy: str = RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "allocation reconciliation graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.source_admission_contract != RUNTIME_ALLOCATION_ADMISSION_CONTRACT:
            raise ValueError("allocation reconciliation admission contract mismatch")
        if (
            self.source_admission_schema_version
            != RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("allocation reconciliation admission schema mismatch")
        _require_non_negative_int(
            self.source_admission_issue_count,
            "source_admission_issue_count",
        )
        _validate_digest(
            self.source_admission_metadata_digest,
            "source_admission_metadata_digest",
        )
        _require_non_negative_int(self.source_admission_count, "source_admission_count")
        _require_non_negative_int(
            self.source_admission_total_admitted_bytes,
            "source_admission_total_admitted_bytes",
        )
        if self.source_receipt_contract != RUNTIME_ALLOCATION_RECEIPT_CONTRACT:
            raise ValueError("allocation reconciliation receipt contract mismatch")
        if (
            self.source_receipt_schema_version
            != RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("allocation reconciliation receipt schema mismatch")
        _require_non_negative_int(
            self.source_receipt_issue_count,
            "source_receipt_issue_count",
        )
        _validate_digest(
            self.source_receipt_metadata_digest,
            "source_receipt_metadata_digest",
        )
        _validate_digest(
            self.source_receipt_source_admission_metadata_digest,
            "source_receipt_source_admission_metadata_digest",
        )
        _require_non_negative_int(self.source_receipt_count, "source_receipt_count")
        _require_non_negative_int(
            self.source_receipt_total_receipted_bytes,
            "source_receipt_total_receipted_bytes",
        )
        if self.reconciliation_contract != RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT:
            raise ValueError("runtime allocation reconciliation contract mismatch")
        if self.reconciliation_policy_id != RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID:
            raise ValueError("runtime allocation reconciliation policy mismatch")
        if self.reconciliation_status != RUNTIME_ALLOCATION_RECONCILIATION_STATUS:
            raise ValueError("runtime allocation reconciliation status mismatch")
        if self.allocation_mode != RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE:
            raise ValueError("runtime allocation reconciliation must remain dry-run only")
        if self.handle_policy != RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY:
            raise ValueError("runtime allocation reconciliation must not use handles")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime allocation reconciliation blocked surfaces changed")
        if type(self.rows) is not tuple:
            raise TypeError("runtime allocation reconciliation rows must be a tuple")
        if len(self.rows) > MAX_RUNTIME_ALLOCATION_RECONCILIATION_ROWS:
            raise ValueError("runtime allocation reconciliation row count exceeds limit")
        for row in self.rows:
            if not isinstance(row, RuntimeAllocationReconciliationRow):
                raise TypeError("runtime allocation reconciliation rows must be rows")
        if type(self.issues) is not tuple:
            raise TypeError("runtime allocation reconciliation issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_ALLOCATION_RECONCILIATION_ISSUES:
            raise ValueError("runtime allocation reconciliation issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeAllocationReconciliationIssue):
                raise TypeError(
                    "runtime allocation reconciliation issues must be issue objects"
                )
        expected_issues = _derive_reconciliation_issues(
            source_admission_issue_count=self.source_admission_issue_count,
            source_receipt_issue_count=self.source_receipt_issue_count,
            source_admission_metadata_digest=self.source_admission_metadata_digest,
            source_receipt_source_admission_metadata_digest=(
                self.source_receipt_source_admission_metadata_digest
            ),
            source_admission_count=self.source_admission_count,
            source_receipt_count=self.source_receipt_count,
            source_admission_total_admitted_bytes=(
                self.source_admission_total_admitted_bytes
            ),
            source_receipt_total_receipted_bytes=(
                self.source_receipt_total_receipted_bytes
            ),
            rows=self.rows,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime allocation reconciliation issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether allocation reconciliation evidence passed."""

        return not self.issues

    @property
    def row_count(self) -> int:
        """Return reconciliation row count."""

        return len(self.rows)

    @property
    def total_reconciled_bytes(self) -> int:
        """Return bytes reconciled across Admission and Receipt."""

        return sum(row.receipted_bytes for row in self.rows)

    @property
    def reconciliation_metadata_digest(self) -> str:
        """Return a digest over reconciliation metadata only."""

        payload = {
            "graph_name": self.graph_name,
            "reconciliation_policy_id": self.reconciliation_policy_id,
            "rows": [
                {
                    "admission_budget_id": row.admission_budget_id,
                    "admission_memory_domain": row.admission_memory_domain.value,
                    "admission_request_id": row.admission_request_id,
                    "admission_slot_id": row.admission_slot_id,
                    "admitted_bytes": row.admitted_bytes,
                    "domain_end_bytes": row.domain_end_bytes,
                    "domain_max_reserved_bytes": row.domain_max_reserved_bytes,
                    "domain_offset_bytes": row.domain_offset_bytes,
                    "domain_total_reserved_bytes": row.domain_total_reserved_bytes,
                    "receipt_budget_id": row.receipt_budget_id,
                    "receipt_id": row.receipt_id,
                    "receipt_memory_domain": row.receipt_memory_domain.value,
                    "receipt_request_id": row.receipt_request_id,
                    "receipt_slot_id": row.receipt_slot_id,
                    "receipted_bytes": row.receipted_bytes,
                    "row_id": row.row_id,
                    "row_status": row.row_status,
                }
                for row in self.rows
            ],
            "source_admission_metadata_digest": self.source_admission_metadata_digest,
            "source_receipt_metadata_digest": self.source_receipt_metadata_digest,
        }
        return _metadata_digest(payload)


class RuntimeAllocationReconciliationError(AssertionError):
    """Raised when runtime allocation reconciliation evidence fails."""


def build_runtime_allocation_reconciliation_report(
    admission_report: RuntimeAllocationAdmissionReport,
    receipt_report: RuntimeAllocationReceiptReport,
) -> RuntimeAllocationReconciliationReport:
    """Build a data-only reconciliation ledger from Admission and Receipt."""

    if not isinstance(admission_report, RuntimeAllocationAdmissionReport):
        raise TypeError("allocation reconciliation source must be admission report")
    if not isinstance(receipt_report, RuntimeAllocationReceiptReport):
        raise TypeError("allocation reconciliation source must be receipt report")
    rows = (
        _build_reconciliation_rows(admission_report.admissions, receipt_report.receipts)
        if admission_report.passed and receipt_report.passed
        else ()
    )
    return RuntimeAllocationReconciliationReport(
        graph_name=admission_report.graph_name,
        operation_count=admission_report.operation_count,
        source_admission_contract=admission_report.admission_contract,
        source_admission_schema_version=RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
        source_admission_issue_count=len(admission_report.issues),
        source_admission_metadata_digest=admission_report.admission_metadata_digest,
        source_admission_count=admission_report.admission_count,
        source_admission_total_admitted_bytes=admission_report.total_admitted_bytes,
        source_receipt_contract=receipt_report.receipt_contract,
        source_receipt_schema_version=RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION,
        source_receipt_issue_count=len(receipt_report.issues),
        source_receipt_metadata_digest=receipt_report.receipt_metadata_digest,
        source_receipt_source_admission_metadata_digest=(
            receipt_report.source_admission_metadata_digest
        ),
        source_receipt_count=receipt_report.receipt_count,
        source_receipt_total_receipted_bytes=receipt_report.total_receipted_bytes,
        rows=rows,
        issues=_derive_reconciliation_issues(
            source_admission_issue_count=len(admission_report.issues),
            source_receipt_issue_count=len(receipt_report.issues),
            source_admission_metadata_digest=admission_report.admission_metadata_digest,
            source_receipt_source_admission_metadata_digest=(
                receipt_report.source_admission_metadata_digest
            ),
            source_admission_count=admission_report.admission_count,
            source_receipt_count=receipt_report.receipt_count,
            source_admission_total_admitted_bytes=admission_report.total_admitted_bytes,
            source_receipt_total_receipted_bytes=receipt_report.total_receipted_bytes,
            rows=rows,
        ),
    )


def assert_runtime_allocation_reconciliation(
    report: RuntimeAllocationReconciliationReport,
) -> RuntimeAllocationReconciliationReport:
    """Return the report or raise when reconciliation evidence fails."""

    if not isinstance(report, RuntimeAllocationReconciliationReport):
        raise TypeError("runtime allocation reconciliation must be report object")
    if report.issues:
        lines = [
            f"runtime allocation reconciliation failed for {report.graph_name!r}:"
        ]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeAllocationReconciliationError("\n".join(lines))
    return report


def runtime_allocation_reconciliation_report_to_dict(
    report: RuntimeAllocationReconciliationReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible reconciliation report."""

    if not isinstance(report, RuntimeAllocationReconciliationReport):
        raise TypeError("runtime allocation reconciliation must be report object")
    return {
        "allocation_mode": report.allocation_mode,
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
        "reconciliation_contract": report.reconciliation_contract,
        "reconciliation_metadata_digest": report.reconciliation_metadata_digest,
        "reconciliation_policy_id": report.reconciliation_policy_id,
        "reconciliation_status": report.reconciliation_status,
        "row_count": report.row_count,
        "rows": [
            {
                "admission_budget_id": row.admission_budget_id,
                "admission_memory_domain": row.admission_memory_domain.value,
                "admission_request_id": row.admission_request_id,
                "admission_slot_id": row.admission_slot_id,
                "admitted_bytes": row.admitted_bytes,
                "domain_end_bytes": row.domain_end_bytes,
                "domain_max_reserved_bytes": row.domain_max_reserved_bytes,
                "domain_offset_bytes": row.domain_offset_bytes,
                "domain_total_reserved_bytes": row.domain_total_reserved_bytes,
                "receipt_budget_id": row.receipt_budget_id,
                "receipt_id": row.receipt_id,
                "receipt_memory_domain": row.receipt_memory_domain.value,
                "receipt_request_id": row.receipt_request_id,
                "receipt_slot_id": row.receipt_slot_id,
                "receipted_bytes": row.receipted_bytes,
                "row_id": row.row_id,
                "row_status": row.row_status,
            }
            for row in report.rows
        ],
        "schema_version": RUNTIME_ALLOCATION_RECONCILIATION_REPORT_SCHEMA_VERSION,
        "source_admission_contract": report.source_admission_contract,
        "source_admission_count": report.source_admission_count,
        "source_admission_issue_count": report.source_admission_issue_count,
        "source_admission_metadata_digest": report.source_admission_metadata_digest,
        "source_admission_schema_version": report.source_admission_schema_version,
        "source_admission_total_admitted_bytes": (
            report.source_admission_total_admitted_bytes
        ),
        "source_receipt_contract": report.source_receipt_contract,
        "source_receipt_count": report.source_receipt_count,
        "source_receipt_issue_count": report.source_receipt_issue_count,
        "source_receipt_metadata_digest": report.source_receipt_metadata_digest,
        "source_receipt_schema_version": report.source_receipt_schema_version,
        "source_receipt_source_admission_metadata_digest": (
            report.source_receipt_source_admission_metadata_digest
        ),
        "source_receipt_total_receipted_bytes": (
            report.source_receipt_total_receipted_bytes
        ),
        "total_reconciled_bytes": report.total_reconciled_bytes,
    }


def dump_runtime_allocation_reconciliation_report(
    report: RuntimeAllocationReconciliationReport,
) -> str:
    """Render stable data-only allocation reconciliation evidence."""

    text = json.dumps(
        runtime_allocation_reconciliation_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_RECONCILIATION_REPORT_BYTES:
        raise ValueError("runtime allocation reconciliation report exceeds byte limit")
    return text + "\n"


def _build_reconciliation_rows(
    admissions: tuple[RuntimeAllocationAdmission, ...],
    receipts: tuple[RuntimeAllocationReceipt, ...],
) -> tuple[RuntimeAllocationReconciliationRow, ...]:
    rows: list[RuntimeAllocationReconciliationRow] = []
    for index, (admission, receipt) in enumerate(zip(admissions, receipts, strict=False), start=1):
        rows.append(
            RuntimeAllocationReconciliationRow(
                row_id=f"allocation_reconciliation_{index:03d}",
                admission_request_id=admission.request_id,
                receipt_request_id=receipt.request_id,
                admission_slot_id=admission.slot_id,
                receipt_slot_id=receipt.slot_id,
                receipt_id=receipt.receipt_id,
                admission_memory_domain=admission.memory_domain,
                receipt_memory_domain=receipt.memory_domain,
                admission_budget_id=admission.budget_id,
                receipt_budget_id=receipt.budget_id,
                admitted_bytes=admission.bytes_reserved,
                receipted_bytes=receipt.bytes_reserved,
                domain_offset_bytes=receipt.domain_offset_bytes,
                domain_end_bytes=receipt.domain_offset_bytes + receipt.bytes_reserved,
                domain_total_reserved_bytes=receipt.domain_total_reserved_bytes,
                domain_max_reserved_bytes=receipt.domain_max_reserved_bytes,
            )
        )
    return tuple(rows)


def _derive_reconciliation_issues(
    *,
    source_admission_issue_count: int,
    source_receipt_issue_count: int,
    source_admission_metadata_digest: str,
    source_receipt_source_admission_metadata_digest: str,
    source_admission_count: int,
    source_receipt_count: int,
    source_admission_total_admitted_bytes: int,
    source_receipt_total_receipted_bytes: int,
    rows: tuple[RuntimeAllocationReconciliationRow, ...],
) -> tuple[RuntimeAllocationReconciliationIssue, ...]:
    issues: list[RuntimeAllocationReconciliationIssue] = []
    if source_admission_issue_count > 0:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="source_allocation_admission",
                issue_code="source_allocation_admission_failed",
            )
        )
    if source_receipt_issue_count > 0:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="source_allocation_receipt",
                issue_code="source_allocation_receipt_failed",
            )
        )
    if source_receipt_source_admission_metadata_digest != source_admission_metadata_digest:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="source_binding",
                issue_code="source_receipt_admission_digest_mismatch",
            )
        )
    if source_admission_count != source_receipt_count:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="source_counts",
                issue_code="source_admission_receipt_count_mismatch",
            )
        )
    if source_admission_count != len(rows) or source_receipt_count != len(rows):
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="rows",
                issue_code="allocation_reconciliation_row_count_mismatch",
            )
        )
    if not rows:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="rows",
                issue_code="allocation_reconciliation_rows_missing",
            )
        )
    if source_admission_total_admitted_bytes != source_receipt_total_receipted_bytes:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="source_bytes",
                issue_code="source_admission_receipt_bytes_mismatch",
            )
        )
    if sum(row.admitted_bytes for row in rows) != source_admission_total_admitted_bytes:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="rows",
                issue_code="allocation_reconciliation_admitted_bytes_mismatch",
            )
        )
    if sum(row.receipted_bytes for row in rows) != source_receipt_total_receipted_bytes:
        issues.append(
            RuntimeAllocationReconciliationIssue(
                subject="rows",
                issue_code="allocation_reconciliation_receipted_bytes_mismatch",
            )
        )
    issues.extend(_derive_row_binding_issues(rows))
    issues.extend(_derive_domain_offset_issues(rows))
    return tuple(issues)


def _derive_row_binding_issues(
    rows: tuple[RuntimeAllocationReconciliationRow, ...],
) -> tuple[RuntimeAllocationReconciliationIssue, ...]:
    issues: list[RuntimeAllocationReconciliationIssue] = []
    if _has_duplicates(row.row_id for row in rows):
        issues.append(_issue("rows", "duplicate_reconciliation_row_id"))
    if _has_duplicates(row.receipt_id for row in rows):
        issues.append(_issue("rows", "duplicate_reconciliation_receipt_id"))
    if _has_duplicates(row.admission_request_id for row in rows):
        issues.append(_issue("rows", "duplicate_admission_request_id"))
    if _has_duplicates(row.receipt_request_id for row in rows):
        issues.append(_issue("rows", "duplicate_receipt_request_id"))
    if _has_duplicates(row.admission_slot_id for row in rows):
        issues.append(_issue("rows", "duplicate_admission_slot_id"))
    if _has_duplicates(row.receipt_slot_id for row in rows):
        issues.append(_issue("rows", "duplicate_receipt_slot_id"))
    for row in rows:
        if row.admission_request_id != row.receipt_request_id:
            issues.append(_issue(row.row_id, "allocation_request_binding_mismatch"))
        if row.admission_slot_id != row.receipt_slot_id:
            issues.append(_issue(row.row_id, "allocation_slot_binding_mismatch"))
        if row.admission_memory_domain != row.receipt_memory_domain:
            issues.append(_issue(row.row_id, "allocation_memory_domain_mismatch"))
        if row.admission_budget_id != row.receipt_budget_id:
            issues.append(_issue(row.row_id, "allocation_budget_binding_mismatch"))
        if row.admitted_bytes != row.receipted_bytes:
            issues.append(_issue(row.row_id, "allocation_byte_binding_mismatch"))
    return tuple(issues)


def _derive_domain_offset_issues(
    rows: tuple[RuntimeAllocationReconciliationRow, ...],
) -> tuple[RuntimeAllocationReconciliationIssue, ...]:
    issues: list[RuntimeAllocationReconciliationIssue] = []
    domains = sorted({row.receipt_memory_domain for row in rows}, key=lambda item: item.value)
    for domain in domains:
        domain_rows = sorted(
            (row for row in rows if row.receipt_memory_domain == domain),
            key=lambda row: (row.domain_offset_bytes, row.row_id),
        )
        expected_offset = 0
        domain_total = sum(row.receipted_bytes for row in domain_rows)
        for row in domain_rows:
            if row.domain_offset_bytes != expected_offset:
                issues.append(_issue(row.row_id, "domain_offset_not_contiguous"))
            if row.domain_total_reserved_bytes != domain_total:
                issues.append(_issue(row.row_id, "domain_total_bytes_mismatch"))
            if row.domain_end_bytes > row.domain_max_reserved_bytes:
                issues.append(_issue(row.row_id, "domain_budget_exceeded"))
            expected_offset = row.domain_end_bytes
    return tuple(issues)


def _issue(subject: str, issue_code: str) -> RuntimeAllocationReconciliationIssue:
    return RuntimeAllocationReconciliationIssue(subject=subject, issue_code=issue_code)


def _has_duplicates(values: Iterable[object]) -> bool:
    seen: set[object] = set()
    for value in values:
        if value in seen:
            return True
        seen.add(value)
    return False


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _RECONCILIATION_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe allocation reconciliation identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_RECONCILIATION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds allocation reconciliation field limit")
    if value in _FORBIDDEN_RECONCILIATION_TEXT:
        raise ValueError(f"{label} names a forbidden allocation or execution surface")


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
    "MAX_RUNTIME_ALLOCATION_RECONCILIATION_FIELD_BYTES",
    "MAX_RUNTIME_ALLOCATION_RECONCILIATION_ISSUES",
    "MAX_RUNTIME_ALLOCATION_RECONCILIATION_REPORT_BYTES",
    "MAX_RUNTIME_ALLOCATION_RECONCILIATION_ROWS",
    "RUNTIME_ALLOCATION_RECONCILIATION_CONTRACT",
    "RUNTIME_ALLOCATION_RECONCILIATION_HANDLE_POLICY",
    "RUNTIME_ALLOCATION_RECONCILIATION_POLICY_ID",
    "RUNTIME_ALLOCATION_RECONCILIATION_REPORT_SCHEMA_VERSION",
    "RUNTIME_ALLOCATION_RECONCILIATION_ROW_STATUS",
    "RUNTIME_ALLOCATION_RECONCILIATION_STATUS",
    "RuntimeAllocationReconciliationError",
    "RuntimeAllocationReconciliationIssue",
    "RuntimeAllocationReconciliationReport",
    "RuntimeAllocationReconciliationRow",
    "assert_runtime_allocation_reconciliation",
    "build_runtime_allocation_reconciliation_report",
    "dump_runtime_allocation_reconciliation_report",
    "runtime_allocation_reconciliation_report_to_dict",
]
