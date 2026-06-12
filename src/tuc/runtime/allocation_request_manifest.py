"""Data-only allocation request manifest for future allocator admission."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.allocation import (
    RUNTIME_ALLOCATION_PLAN_CONTRACT,
    RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
    RuntimeAllocationPlanReport,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.memory_budget import (
    RUNTIME_MEMORY_BUDGET_CONTRACT,
    RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
    RuntimeMemoryBudgetReport,
)

RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_allocation_request_manifest_report.v0"
)
RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT = (
    "runtime_allocation_request_manifest.data_only.v0"
)
RUNTIME_ALLOCATION_REQUEST_STATUS = "admitted"
RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY = "no_runtime_handles"
MAX_RUNTIME_ALLOCATION_REQUESTS = 8192
MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_ISSUES = 64
MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_FIELD_BYTES = 512

_REQUEST_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_REQUEST_TEXT = frozenset(
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


@dataclass(frozen=True)
class RuntimeAllocationRequest:
    """One bounded future allocator request derived from an allocation slot."""

    request_id: str
    slot_id: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    shape: tuple[int, ...]
    bytes_reserved: int
    tensor_names: tuple[str, ...]
    allocation_kind: str
    request_status: str = RUNTIME_ALLOCATION_REQUEST_STATUS
    handle_policy: str = RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY

    def __post_init__(self) -> None:
        _validate_text(self.request_id, "allocation request request_id")
        _validate_text(self.slot_id, "allocation request slot_id")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("allocation request memory_domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("allocation request layout must be LayoutKind")
        _validate_dtype(self.dtype)
        _validate_shape(self.shape)
        _require_positive_int(self.bytes_reserved, "bytes_reserved")
        if type(self.tensor_names) is not tuple:
            raise TypeError("allocation request tensor_names must be a tuple")
        if not self.tensor_names:
            raise ValueError("allocation request tensor_names must not be empty")
        for tensor_name in self.tensor_names:
            _validate_text(tensor_name, "allocation request tensor_name")
        if self.allocation_kind not in {"exclusive", "reused"}:
            raise ValueError("allocation request kind is unsupported")
        if self.request_status != RUNTIME_ALLOCATION_REQUEST_STATUS:
            raise ValueError("allocation request status must be admitted")
        if self.handle_policy != RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY:
            raise ValueError("allocation request must not expose runtime handles")

    @property
    def tensor_count(self) -> int:
        """Return tensor count associated with the request."""

        return len(self.tensor_names)


@dataclass(frozen=True)
class RuntimeAllocationRequestManifestIssue:
    """One derived allocation request manifest issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "allocation request manifest issue subject")
        _validate_text(self.issue_code, "allocation request manifest issue_code")


@dataclass(frozen=True)
class RuntimeAllocationRequestManifestReport:
    """Deterministic allocation request manifest for future allocator admission."""

    graph_name: str
    operation_count: int
    source_allocation_contract: str
    source_allocation_schema_version: str
    source_allocation_metadata_digest: str
    source_memory_budget_contract: str
    source_memory_budget_schema_version: str
    source_memory_budget_allocation_digest: str
    requests: tuple[RuntimeAllocationRequest, ...]
    issues: tuple[RuntimeAllocationRequestManifestIssue, ...]
    manifest_contract: str = RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT
    handle_policy: str = RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "allocation request manifest graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.source_allocation_contract != RUNTIME_ALLOCATION_PLAN_CONTRACT:
            raise ValueError("allocation request source allocation contract mismatch")
        if (
            self.source_allocation_schema_version
            != RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("allocation request source allocation schema mismatch")
        _validate_digest(
            self.source_allocation_metadata_digest,
            "source_allocation_metadata_digest",
        )
        if self.source_memory_budget_contract != RUNTIME_MEMORY_BUDGET_CONTRACT:
            raise ValueError("allocation request source memory budget contract mismatch")
        if (
            self.source_memory_budget_schema_version
            != RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("allocation request source memory budget schema mismatch")
        _validate_digest(
            self.source_memory_budget_allocation_digest,
            "source_memory_budget_allocation_digest",
        )
        if self.manifest_contract != RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT:
            raise ValueError("runtime allocation request manifest contract mismatch")
        if self.handle_policy != RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY:
            raise ValueError("runtime allocation request manifest must not use handles")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError(
                "runtime allocation request manifest blocked surfaces changed"
            )
        if type(self.requests) is not tuple:
            raise TypeError("runtime allocation requests must be a tuple")
        if len(self.requests) > MAX_RUNTIME_ALLOCATION_REQUESTS:
            raise ValueError("runtime allocation request count exceeds limit")
        for request in self.requests:
            if not isinstance(request, RuntimeAllocationRequest):
                raise TypeError("runtime allocation requests must be request objects")
        if type(self.issues) is not tuple:
            raise TypeError("runtime allocation request issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_ISSUES:
            raise ValueError("runtime allocation request issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeAllocationRequestManifestIssue):
                raise TypeError(
                    "runtime allocation request issues must be issue objects"
                )
        expected_issues = _derive_request_manifest_issues(
            self.source_allocation_metadata_digest,
            self.source_memory_budget_allocation_digest,
            self.requests,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime allocation request issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether allocation request manifest evidence passed."""

        return not self.issues

    @property
    def request_count(self) -> int:
        """Return allocation request count."""

        return len(self.requests)

    @property
    def total_reserved_bytes(self) -> int:
        """Return total reserved bytes requested across slots."""

        return sum(request.bytes_reserved for request in self.requests)

    @property
    def manifest_metadata_digest(self) -> str:
        """Return a digest over request manifest metadata only."""

        payload = {
            "graph_name": self.graph_name,
            "handle_policy": self.handle_policy,
            "manifest_contract": self.manifest_contract,
            "operation_count": self.operation_count,
            "requests": [
                {
                    "allocation_kind": request.allocation_kind,
                    "bytes_reserved": request.bytes_reserved,
                    "dtype": request.dtype,
                    "handle_policy": request.handle_policy,
                    "layout": request.layout.value,
                    "memory_domain": request.memory_domain.value,
                    "request_id": request.request_id,
                    "request_status": request.request_status,
                    "shape": list(request.shape),
                    "slot_id": request.slot_id,
                    "tensor_names": list(request.tensor_names),
                }
                for request in self.requests
            ],
            "source_allocation_metadata_digest": self.source_allocation_metadata_digest,
            "source_memory_budget_allocation_digest": (
                self.source_memory_budget_allocation_digest
            ),
        }
        return _metadata_digest(payload)


class RuntimeAllocationRequestManifestError(AssertionError):
    """Raised when runtime allocation request manifest evidence fails."""


def build_runtime_allocation_request_manifest_report(
    allocation_report: RuntimeAllocationPlanReport,
    memory_budget_report: RuntimeMemoryBudgetReport,
) -> RuntimeAllocationRequestManifestReport:
    """Build data-only future allocator request metadata from memory evidence."""

    if not isinstance(allocation_report, RuntimeAllocationPlanReport):
        raise TypeError("allocation request source must be allocation report")
    if not isinstance(memory_budget_report, RuntimeMemoryBudgetReport):
        raise TypeError("allocation request budget source must be memory budget report")
    requests = tuple(
        RuntimeAllocationRequest(
            request_id=f"alloc_request_{index + 1:03d}",
            slot_id=slot.slot_id,
            memory_domain=slot.memory_domain,
            layout=slot.layout,
            dtype=slot.dtype,
            shape=slot.shape,
            bytes_reserved=slot.bytes_reserved,
            tensor_names=slot.tensor_names,
            allocation_kind=slot.allocation_kind,
        )
        for index, slot in enumerate(allocation_report.slots)
    )
    return RuntimeAllocationRequestManifestReport(
        graph_name=allocation_report.graph_name,
        operation_count=allocation_report.operation_count,
        source_allocation_contract=allocation_report.allocation_contract,
        source_allocation_schema_version=RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
        source_allocation_metadata_digest=allocation_report.allocation_metadata_digest,
        source_memory_budget_contract=memory_budget_report.budget_contract,
        source_memory_budget_schema_version=RUNTIME_MEMORY_BUDGET_REPORT_SCHEMA_VERSION,
        source_memory_budget_allocation_digest=(
            memory_budget_report.source_allocation_metadata_digest
        ),
        requests=requests,
        issues=_derive_request_manifest_issues(
            allocation_report.allocation_metadata_digest,
            memory_budget_report.source_allocation_metadata_digest,
            requests,
        ),
    )


def assert_runtime_allocation_request_manifest(
    report: RuntimeAllocationRequestManifestReport,
) -> RuntimeAllocationRequestManifestReport:
    """Return the report or raise when allocation request evidence fails."""

    if not isinstance(report, RuntimeAllocationRequestManifestReport):
        raise TypeError("runtime allocation request manifest must be report object")
    if report.issues:
        lines = [f"runtime allocation request manifest failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeAllocationRequestManifestError("\n".join(lines))
    return report


def runtime_allocation_request_manifest_report_to_dict(
    report: RuntimeAllocationRequestManifestReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible allocation request manifest."""

    if not isinstance(report, RuntimeAllocationRequestManifestReport):
        raise TypeError("runtime allocation request manifest must be report object")
    return {
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
        "manifest_contract": report.manifest_contract,
        "manifest_metadata_digest": report.manifest_metadata_digest,
        "operation_count": report.operation_count,
        "passed": report.passed,
        "request_count": report.request_count,
        "requests": [
            {
                "allocation_kind": request.allocation_kind,
                "bytes_reserved": request.bytes_reserved,
                "dtype": request.dtype,
                "handle_policy": request.handle_policy,
                "layout": request.layout.value,
                "memory_domain": request.memory_domain.value,
                "request_id": request.request_id,
                "request_status": request.request_status,
                "shape": list(request.shape),
                "slot_id": request.slot_id,
                "tensor_count": request.tensor_count,
                "tensor_names": list(request.tensor_names),
            }
            for request in report.requests
        ],
        "schema_version": RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION,
        "source_allocation_contract": report.source_allocation_contract,
        "source_allocation_metadata_digest": (
            report.source_allocation_metadata_digest
        ),
        "source_allocation_schema_version": (
            report.source_allocation_schema_version
        ),
        "source_memory_budget_allocation_digest": (
            report.source_memory_budget_allocation_digest
        ),
        "source_memory_budget_contract": report.source_memory_budget_contract,
        "source_memory_budget_schema_version": (
            report.source_memory_budget_schema_version
        ),
        "total_reserved_bytes": report.total_reserved_bytes,
    }


def dump_runtime_allocation_request_manifest_report(
    report: RuntimeAllocationRequestManifestReport,
) -> str:
    """Render stable data-only allocation request manifest evidence."""

    text = json.dumps(
        runtime_allocation_request_manifest_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_BYTES:
        raise ValueError("runtime allocation request manifest exceeds byte limit")
    return text + "\n"


def _derive_request_manifest_issues(
    source_allocation_digest: str,
    source_memory_budget_allocation_digest: str,
    requests: tuple[RuntimeAllocationRequest, ...],
) -> tuple[RuntimeAllocationRequestManifestIssue, ...]:
    issues: list[RuntimeAllocationRequestManifestIssue] = []
    if source_allocation_digest != source_memory_budget_allocation_digest:
        issues.append(
            RuntimeAllocationRequestManifestIssue(
                subject="source_allocation",
                issue_code="source_allocation_digest_mismatch",
            )
        )
    if not requests:
        issues.append(
            RuntimeAllocationRequestManifestIssue(
                subject="requests",
                issue_code="allocation_requests_missing",
            )
        )
    request_ids = {request.request_id for request in requests}
    if len(request_ids) != len(requests):
        issues.append(
            RuntimeAllocationRequestManifestIssue(
                subject="requests",
                issue_code="duplicate_request_id",
            )
        )
    slot_ids = {request.slot_id for request in requests}
    if len(slot_ids) != len(requests):
        issues.append(
            RuntimeAllocationRequestManifestIssue(
                subject="requests",
                issue_code="duplicate_slot_id",
            )
        )
    return tuple(issues)


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REQUEST_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe allocation request identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_FIELD_BYTES:
        raise ValueError(f"{label} exceeds allocation request field limit")
    if value in _FORBIDDEN_REQUEST_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be a sha256 metadata digest")


def _validate_dtype(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"^[A-Za-z][A-Za-z0-9_]*$", value):
        raise ValueError("allocation request dtype must be a safe dtype identifier")


def _validate_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise TypeError("allocation request shape must be a non-empty tuple")
    for dimension in value:
        _require_positive_int(dimension, "shape dimension")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_ALLOCATION_REQUESTS",
    "MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_FIELD_BYTES",
    "MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_ISSUES",
    "MAX_RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_BYTES",
    "RUNTIME_ALLOCATION_REQUEST_HANDLE_POLICY",
    "RUNTIME_ALLOCATION_REQUEST_MANIFEST_CONTRACT",
    "RUNTIME_ALLOCATION_REQUEST_MANIFEST_REPORT_SCHEMA_VERSION",
    "RUNTIME_ALLOCATION_REQUEST_STATUS",
    "RuntimeAllocationRequest",
    "RuntimeAllocationRequestManifestError",
    "RuntimeAllocationRequestManifestIssue",
    "RuntimeAllocationRequestManifestReport",
    "assert_runtime_allocation_request_manifest",
    "build_runtime_allocation_request_manifest_report",
    "dump_runtime_allocation_request_manifest_report",
    "runtime_allocation_request_manifest_report_to_dict",
]
