"""Data-only allocation receipt evidence for future allocator dry runs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import MemoryDomainKind
from tuc.runtime.allocation_admission import (
    RUNTIME_ALLOCATION_ADMISSION_CONTRACT,
    RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY,
    RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION,
    RUNTIME_ALLOCATION_ADMISSION_STATUS,
    RuntimeAllocationAdmission,
    RuntimeAllocationAdmissionReport,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_allocation_receipt_report.v0"
)
RUNTIME_ALLOCATION_RECEIPT_CONTRACT = "runtime_allocation_receipt.data_only.v0"
RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE = "dry_run_only"
RUNTIME_ALLOCATION_RECEIPT_STATUS = "dry_run_recorded"
RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY = RUNTIME_ALLOCATION_ADMISSION_HANDLE_POLICY
MAX_RUNTIME_ALLOCATION_RECEIPTS = 8192
MAX_RUNTIME_ALLOCATION_RECEIPT_ISSUES = 64
MAX_RUNTIME_ALLOCATION_RECEIPT_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_ALLOCATION_RECEIPT_FIELD_BYTES = 512

_RECEIPT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_RECEIPT_TEXT = frozenset(
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
class RuntimeAllocationReceipt:
    """One deterministic dry-run receipt for an admitted allocation request."""

    receipt_id: str
    request_id: str
    slot_id: str
    memory_domain: MemoryDomainKind
    budget_id: str
    bytes_reserved: int
    domain_offset_bytes: int
    domain_total_reserved_bytes: int
    domain_max_reserved_bytes: int
    allocation_status: str = RUNTIME_ALLOCATION_RECEIPT_STATUS
    allocation_mode: str = RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    handle_policy: str = RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY

    def __post_init__(self) -> None:
        _validate_text(self.receipt_id, "allocation receipt receipt_id")
        _validate_text(self.request_id, "allocation receipt request_id")
        _validate_text(self.slot_id, "allocation receipt slot_id")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("allocation receipt memory_domain must be MemoryDomainKind")
        _validate_text(self.budget_id, "allocation receipt budget_id")
        _require_positive_int(self.bytes_reserved, "bytes_reserved")
        _require_non_negative_int(self.domain_offset_bytes, "domain_offset_bytes")
        _require_non_negative_int(
            self.domain_total_reserved_bytes,
            "domain_total_reserved_bytes",
        )
        _require_non_negative_int(
            self.domain_max_reserved_bytes,
            "domain_max_reserved_bytes",
        )
        if self.domain_offset_bytes + self.bytes_reserved > self.domain_total_reserved_bytes:
            raise ValueError("allocation receipt exceeds domain reserved bytes")
        if self.domain_total_reserved_bytes > self.domain_max_reserved_bytes:
            raise ValueError("allocation receipt exceeds domain budget")
        if self.allocation_status != RUNTIME_ALLOCATION_RECEIPT_STATUS:
            raise ValueError("allocation receipt status is unsupported")
        if self.allocation_mode != RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE:
            raise ValueError("allocation receipt must remain dry-run only")
        if self.handle_policy != RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY:
            raise ValueError("allocation receipt must not expose runtime handles")


@dataclass(frozen=True)
class RuntimeAllocationReceiptIssue:
    """One derived allocation-receipt issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "allocation receipt issue subject")
        _validate_text(self.issue_code, "allocation receipt issue_code")


@dataclass(frozen=True)
class RuntimeAllocationReceiptReport:
    """Deterministic data-only receipt report for allocator dry-run evidence."""

    graph_name: str
    operation_count: int
    source_admission_contract: str
    source_admission_schema_version: str
    source_admission_issue_count: int
    source_admission_metadata_digest: str
    source_admission_total_admitted_bytes: int
    receipts: tuple[RuntimeAllocationReceipt, ...]
    issues: tuple[RuntimeAllocationReceiptIssue, ...]
    receipt_contract: str = RUNTIME_ALLOCATION_RECEIPT_CONTRACT
    allocation_mode: str = RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE
    handle_policy: str = RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "allocation receipt graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.source_admission_contract != RUNTIME_ALLOCATION_ADMISSION_CONTRACT:
            raise ValueError("allocation receipt source admission contract mismatch")
        if (
            self.source_admission_schema_version
            != RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("allocation receipt source admission schema mismatch")
        _require_non_negative_int(
            self.source_admission_issue_count,
            "source_admission_issue_count",
        )
        _validate_digest(
            self.source_admission_metadata_digest,
            "source_admission_metadata_digest",
        )
        _require_non_negative_int(
            self.source_admission_total_admitted_bytes,
            "source_admission_total_admitted_bytes",
        )
        if self.receipt_contract != RUNTIME_ALLOCATION_RECEIPT_CONTRACT:
            raise ValueError("runtime allocation receipt contract mismatch")
        if self.allocation_mode != RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE:
            raise ValueError("runtime allocation receipt must remain dry-run only")
        if self.handle_policy != RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY:
            raise ValueError("runtime allocation receipt must not use handles")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime allocation receipt blocked surfaces changed")
        if type(self.receipts) is not tuple:
            raise TypeError("runtime allocation receipts must be a tuple")
        if len(self.receipts) > MAX_RUNTIME_ALLOCATION_RECEIPTS:
            raise ValueError("runtime allocation receipt count exceeds limit")
        for receipt in self.receipts:
            if not isinstance(receipt, RuntimeAllocationReceipt):
                raise TypeError("runtime allocation receipts must be receipt objects")
        if type(self.issues) is not tuple:
            raise TypeError("runtime allocation receipt issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_ALLOCATION_RECEIPT_ISSUES:
            raise ValueError("runtime allocation receipt issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeAllocationReceiptIssue):
                raise TypeError("runtime allocation receipt issues must be issue objects")
        expected_issues = _derive_receipt_issues(
            self.source_admission_issue_count,
            self.source_admission_total_admitted_bytes,
            self.receipts,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime allocation receipt issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether allocation receipt evidence passed."""

        return not self.issues

    @property
    def receipt_count(self) -> int:
        """Return receipt count."""

        return len(self.receipts)

    @property
    def total_receipted_bytes(self) -> int:
        """Return bytes represented by dry-run allocation receipts."""

        return sum(receipt.bytes_reserved for receipt in self.receipts)

    @property
    def receipt_metadata_digest(self) -> str:
        """Return a digest over receipt metadata only."""

        payload = {
            "graph_name": self.graph_name,
            "receipts": [
                {
                    "allocation_mode": receipt.allocation_mode,
                    "allocation_status": receipt.allocation_status,
                    "budget_id": receipt.budget_id,
                    "bytes_reserved": receipt.bytes_reserved,
                    "domain_max_reserved_bytes": receipt.domain_max_reserved_bytes,
                    "domain_offset_bytes": receipt.domain_offset_bytes,
                    "domain_total_reserved_bytes": receipt.domain_total_reserved_bytes,
                    "handle_policy": receipt.handle_policy,
                    "memory_domain": receipt.memory_domain.value,
                    "receipt_id": receipt.receipt_id,
                    "request_id": receipt.request_id,
                    "slot_id": receipt.slot_id,
                }
                for receipt in self.receipts
            ],
            "source_admission_metadata_digest": (
                self.source_admission_metadata_digest
            ),
        }
        return _metadata_digest(payload)


class RuntimeAllocationReceiptError(AssertionError):
    """Raised when runtime allocation receipt evidence fails."""


def build_runtime_allocation_receipt_report(
    admission_report: RuntimeAllocationAdmissionReport,
) -> RuntimeAllocationReceiptReport:
    """Build data-only allocator dry-run receipts from admission evidence."""

    if not isinstance(admission_report, RuntimeAllocationAdmissionReport):
        raise TypeError("allocation receipt source must be admission report")
    receipts = (
        _build_receipts(admission_report.admissions)
        if admission_report.passed
        else ()
    )
    return RuntimeAllocationReceiptReport(
        graph_name=admission_report.graph_name,
        operation_count=admission_report.operation_count,
        source_admission_contract=admission_report.admission_contract,
        source_admission_schema_version=(
            RUNTIME_ALLOCATION_ADMISSION_REPORT_SCHEMA_VERSION
        ),
        source_admission_issue_count=len(admission_report.issues),
        source_admission_metadata_digest=admission_report.admission_metadata_digest,
        source_admission_total_admitted_bytes=admission_report.total_admitted_bytes,
        receipts=receipts,
        issues=_derive_receipt_issues(
            len(admission_report.issues),
            admission_report.total_admitted_bytes,
            receipts,
        ),
    )


def assert_runtime_allocation_receipt(
    report: RuntimeAllocationReceiptReport,
) -> RuntimeAllocationReceiptReport:
    """Return the report or raise when allocation receipt evidence fails."""

    if not isinstance(report, RuntimeAllocationReceiptReport):
        raise TypeError("runtime allocation receipt must be report object")
    if report.issues:
        lines = [f"runtime allocation receipt failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeAllocationReceiptError("\n".join(lines))
    return report


def runtime_allocation_receipt_report_to_dict(
    report: RuntimeAllocationReceiptReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible allocation receipt report."""

    if not isinstance(report, RuntimeAllocationReceiptReport):
        raise TypeError("runtime allocation receipt must be report object")
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
        "receipt_contract": report.receipt_contract,
        "receipt_count": report.receipt_count,
        "receipt_metadata_digest": report.receipt_metadata_digest,
        "receipts": [
            {
                "allocation_mode": receipt.allocation_mode,
                "allocation_status": receipt.allocation_status,
                "budget_id": receipt.budget_id,
                "bytes_reserved": receipt.bytes_reserved,
                "domain_max_reserved_bytes": receipt.domain_max_reserved_bytes,
                "domain_offset_bytes": receipt.domain_offset_bytes,
                "domain_total_reserved_bytes": receipt.domain_total_reserved_bytes,
                "handle_policy": receipt.handle_policy,
                "memory_domain": receipt.memory_domain.value,
                "receipt_id": receipt.receipt_id,
                "request_id": receipt.request_id,
                "slot_id": receipt.slot_id,
            }
            for receipt in report.receipts
        ],
        "schema_version": RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION,
        "source_admission_contract": report.source_admission_contract,
        "source_admission_issue_count": report.source_admission_issue_count,
        "source_admission_metadata_digest": (
            report.source_admission_metadata_digest
        ),
        "source_admission_schema_version": report.source_admission_schema_version,
        "source_admission_total_admitted_bytes": (
            report.source_admission_total_admitted_bytes
        ),
        "total_receipted_bytes": report.total_receipted_bytes,
    }


def dump_runtime_allocation_receipt_report(
    report: RuntimeAllocationReceiptReport,
) -> str:
    """Render stable data-only allocation receipt evidence."""

    text = json.dumps(
        runtime_allocation_receipt_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_RECEIPT_REPORT_BYTES:
        raise ValueError("runtime allocation receipt report exceeds byte limit")
    return text + "\n"


def _build_receipts(
    admissions: tuple[RuntimeAllocationAdmission, ...],
) -> tuple[RuntimeAllocationReceipt, ...]:
    offsets_by_domain: dict[MemoryDomainKind, int] = {}
    receipts: list[RuntimeAllocationReceipt] = []
    for index, admission in enumerate(admissions, start=1):
        if admission.admission_status != RUNTIME_ALLOCATION_ADMISSION_STATUS:
            continue
        offset = offsets_by_domain.get(admission.memory_domain, 0)
        receipts.append(
            RuntimeAllocationReceipt(
                receipt_id=f"allocation_receipt_{index:03d}",
                request_id=admission.request_id,
                slot_id=admission.slot_id,
                memory_domain=admission.memory_domain,
                budget_id=admission.budget_id,
                bytes_reserved=admission.bytes_reserved,
                domain_offset_bytes=offset,
                domain_total_reserved_bytes=admission.domain_total_reserved_bytes,
                domain_max_reserved_bytes=admission.domain_max_reserved_bytes,
            )
        )
        offsets_by_domain[admission.memory_domain] = offset + admission.bytes_reserved
    return tuple(receipts)


def _derive_receipt_issues(
    source_admission_issue_count: int,
    source_admission_total_admitted_bytes: int,
    receipts: tuple[RuntimeAllocationReceipt, ...],
) -> tuple[RuntimeAllocationReceiptIssue, ...]:
    issues: list[RuntimeAllocationReceiptIssue] = []
    if source_admission_issue_count > 0:
        issues.append(
            RuntimeAllocationReceiptIssue(
                subject="source_allocation_admission",
                issue_code="source_allocation_admission_failed",
            )
        )
    if not receipts:
        issues.append(
            RuntimeAllocationReceiptIssue(
                subject="receipts",
                issue_code="allocation_receipts_missing",
            )
        )
    receipt_ids = {receipt.receipt_id for receipt in receipts}
    if len(receipt_ids) != len(receipts):
        issues.append(
            RuntimeAllocationReceiptIssue(
                subject="receipts",
                issue_code="duplicate_receipt_id",
            )
        )
    request_ids = {receipt.request_id for receipt in receipts}
    if len(request_ids) != len(receipts):
        issues.append(
            RuntimeAllocationReceiptIssue(
                subject="receipts",
                issue_code="duplicate_request_id",
            )
        )
    slot_ids = {receipt.slot_id for receipt in receipts}
    if len(slot_ids) != len(receipts):
        issues.append(
            RuntimeAllocationReceiptIssue(
                subject="receipts",
                issue_code="duplicate_slot_id",
            )
        )
    if sum(receipt.bytes_reserved for receipt in receipts) != source_admission_total_admitted_bytes:
        issues.append(
            RuntimeAllocationReceiptIssue(
                subject="receipts",
                issue_code="allocation_receipt_bytes_mismatch",
            )
        )
    return tuple(issues)


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + sha256(encoded).hexdigest()


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _RECEIPT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe allocation receipt identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_RECEIPT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds allocation receipt field limit")
    if value in _FORBIDDEN_RECEIPT_TEXT:
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
    "MAX_RUNTIME_ALLOCATION_RECEIPT_FIELD_BYTES",
    "MAX_RUNTIME_ALLOCATION_RECEIPT_ISSUES",
    "MAX_RUNTIME_ALLOCATION_RECEIPT_REPORT_BYTES",
    "MAX_RUNTIME_ALLOCATION_RECEIPTS",
    "RUNTIME_ALLOCATION_RECEIPT_ALLOCATION_MODE",
    "RUNTIME_ALLOCATION_RECEIPT_CONTRACT",
    "RUNTIME_ALLOCATION_RECEIPT_HANDLE_POLICY",
    "RUNTIME_ALLOCATION_RECEIPT_REPORT_SCHEMA_VERSION",
    "RUNTIME_ALLOCATION_RECEIPT_STATUS",
    "RuntimeAllocationReceipt",
    "RuntimeAllocationReceiptError",
    "RuntimeAllocationReceiptIssue",
    "RuntimeAllocationReceiptReport",
    "assert_runtime_allocation_receipt",
    "build_runtime_allocation_receipt_report",
    "dump_runtime_allocation_receipt_report",
    "runtime_allocation_receipt_report_to_dict",
]
