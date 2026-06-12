"""Data-only runtime allocation plan evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.buffer_lifetime import (
    RUNTIME_BUFFER_LIFETIME_CONTRACT,
    RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION,
    RuntimeBufferLifetime,
    RuntimeBufferLifetimeReport,
    RuntimeBufferReuseGroup,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_allocation_plan_report.v0"
)
RUNTIME_ALLOCATION_PLAN_CONTRACT = "runtime_allocation_plan.data_only.v0"
MAX_RUNTIME_ALLOCATION_BINDINGS = 8192
MAX_RUNTIME_ALLOCATION_SLOTS = 8192
MAX_RUNTIME_ALLOCATION_ISSUES = 64
MAX_RUNTIME_ALLOCATION_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_ALLOCATION_FIELD_BYTES = 512

_ALLOCATION_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_ALLOCATION_TEXT = frozenset(
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
class RuntimeAllocationBinding:
    """Binding from one produced tensor lifetime to one allocation slot."""

    tensor_name: str
    slot_id: str
    producer_operation: str
    producer_index: int
    first_live_index: int
    last_use_index: int
    lifetime_kind: str
    bytes_required: int
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    shape: tuple[int, ...]

    def __post_init__(self) -> None:
        _validate_text(self.tensor_name, "tensor_name")
        _validate_text(self.slot_id, "slot_id")
        _validate_text(self.producer_operation, "producer_operation")
        _require_non_negative_int(self.producer_index, "producer_index")
        _require_non_negative_int(self.first_live_index, "first_live_index")
        _require_non_negative_int(self.last_use_index, "last_use_index")
        if self.last_use_index < self.first_live_index:
            raise ValueError("allocation binding last_use_index precedes first_live_index")
        if self.lifetime_kind not in {"intermediate", "graph_output"}:
            raise ValueError("allocation binding lifetime kind is unsupported")
        _require_positive_int(self.bytes_required, "bytes_required")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("allocation binding memory_domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("allocation binding layout must be LayoutKind")
        _validate_dtype(self.dtype)
        _validate_shape(self.shape)


@dataclass(frozen=True)
class RuntimeAllocationSlot:
    """One planned allocation slot derived from a reuse group."""

    slot_id: str
    source_reuse_group_id: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    shape: tuple[int, ...]
    bytes_reserved: int
    tensor_names: tuple[str, ...]
    allocation_kind: str
    live_ranges_non_overlapping: bool

    def __post_init__(self) -> None:
        _validate_text(self.slot_id, "slot_id")
        _validate_text(self.source_reuse_group_id, "source_reuse_group_id")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("allocation slot memory_domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("allocation slot layout must be LayoutKind")
        _validate_dtype(self.dtype)
        _validate_shape(self.shape)
        _require_positive_int(self.bytes_reserved, "bytes_reserved")
        if type(self.tensor_names) is not tuple:
            raise TypeError("allocation slot tensor_names must be a tuple")
        if not self.tensor_names:
            raise ValueError("allocation slot tensor_names must not be empty")
        for tensor_name in self.tensor_names:
            _validate_text(tensor_name, "allocation slot tensor_name")
        if self.allocation_kind not in {"exclusive", "reused"}:
            raise ValueError("allocation slot kind is unsupported")
        expected_kind = "reused" if len(self.tensor_names) > 1 else "exclusive"
        if self.allocation_kind != expected_kind:
            raise ValueError("allocation slot kind must be derived from tensor count")
        if not isinstance(self.live_ranges_non_overlapping, bool):
            raise TypeError("allocation slot live range status must be bool")

    @property
    def tensor_count(self) -> int:
        """Return tensor binding count for the slot."""

        return len(self.tensor_names)


@dataclass(frozen=True)
class RuntimeAllocationIssue:
    """One derived runtime allocation issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "issue subject")
        _validate_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeAllocationPlanReport:
    """Deterministic allocation-plan report for runtime buffer slots."""

    graph_name: str
    operation_count: int
    source_lifetime_contract: str
    source_lifetime_schema_version: str
    source_lifetime_issue_count: int
    bindings: tuple[RuntimeAllocationBinding, ...]
    slots: tuple[RuntimeAllocationSlot, ...]
    issues: tuple[RuntimeAllocationIssue, ...]
    allocation_contract: str = RUNTIME_ALLOCATION_PLAN_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.source_lifetime_contract != RUNTIME_BUFFER_LIFETIME_CONTRACT:
            raise ValueError("allocation plan source lifetime contract mismatch")
        if self.source_lifetime_schema_version != RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION:
            raise ValueError("allocation plan source lifetime schema mismatch")
        _require_non_negative_int(
            self.source_lifetime_issue_count,
            "source_lifetime_issue_count",
        )
        if self.allocation_contract != RUNTIME_ALLOCATION_PLAN_CONTRACT:
            raise ValueError("runtime allocation plan contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime allocation plan blocked surfaces changed")
        if type(self.bindings) is not tuple:
            raise TypeError("runtime allocation bindings must be a tuple")
        if len(self.bindings) > MAX_RUNTIME_ALLOCATION_BINDINGS:
            raise ValueError("runtime allocation binding count exceeds limit")
        for binding in self.bindings:
            if not isinstance(binding, RuntimeAllocationBinding):
                raise TypeError("runtime allocation bindings must be binding objects")
        if type(self.slots) is not tuple:
            raise TypeError("runtime allocation slots must be a tuple")
        if len(self.slots) > MAX_RUNTIME_ALLOCATION_SLOTS:
            raise ValueError("runtime allocation slot count exceeds limit")
        for slot in self.slots:
            if not isinstance(slot, RuntimeAllocationSlot):
                raise TypeError("runtime allocation slots must be slot objects")
        if type(self.issues) is not tuple:
            raise TypeError("runtime allocation issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_ALLOCATION_ISSUES:
            raise ValueError("runtime allocation issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeAllocationIssue):
                raise TypeError("runtime allocation issues must be issue objects")
        expected_issues = _derive_allocation_issues(
            self.source_lifetime_issue_count,
            self.bindings,
            self.slots,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime allocation issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether allocation-plan evidence passed."""

        return not self.issues

    @property
    def tensor_binding_count(self) -> int:
        """Return the number of produced tensor bindings."""

        return len(self.bindings)

    @property
    def slot_count(self) -> int:
        """Return the number of planned allocation slots."""

        return len(self.slots)

    @property
    def reuse_slot_count(self) -> int:
        """Return the number of slots assigned to multiple lifetimes."""

        return sum(1 for slot in self.slots if slot.allocation_kind == "reused")

    @property
    def total_tensor_bytes(self) -> int:
        """Return total bytes required by produced tensor lifetimes."""

        return sum(binding.bytes_required for binding in self.bindings)

    @property
    def total_reserved_bytes(self) -> int:
        """Return bytes reserved by planned allocation slots."""

        return sum(slot.bytes_reserved for slot in self.slots)

    @property
    def committed_reuse_savings_bytes(self) -> int:
        """Return bytes saved by assigning exact non-overlapping lifetimes to slots."""

        return max(0, self.total_tensor_bytes - self.total_reserved_bytes)

    @property
    def allocation_metadata_digest(self) -> str:
        """Return a digest over allocation-plan metadata only."""

        payload = {
            "allocation_contract": self.allocation_contract,
            "bindings": [
                {
                    "bytes_required": binding.bytes_required,
                    "dtype": binding.dtype,
                    "first_live_index": binding.first_live_index,
                    "last_use_index": binding.last_use_index,
                    "layout": binding.layout.value,
                    "lifetime_kind": binding.lifetime_kind,
                    "memory_domain": binding.memory_domain.value,
                    "producer_index": binding.producer_index,
                    "producer_operation": binding.producer_operation,
                    "shape": list(binding.shape),
                    "slot_id": binding.slot_id,
                    "tensor_name": binding.tensor_name,
                }
                for binding in self.bindings
            ],
            "graph_name": self.graph_name,
            "issues": [
                {
                    "issue_code": issue.issue_code,
                    "subject": issue.subject,
                }
                for issue in self.issues
            ],
            "operation_count": self.operation_count,
            "source_lifetime_contract": self.source_lifetime_contract,
            "source_lifetime_issue_count": self.source_lifetime_issue_count,
            "source_lifetime_schema_version": self.source_lifetime_schema_version,
            "slots": [
                {
                    "allocation_kind": slot.allocation_kind,
                    "bytes_reserved": slot.bytes_reserved,
                    "dtype": slot.dtype,
                    "layout": slot.layout.value,
                    "live_ranges_non_overlapping": slot.live_ranges_non_overlapping,
                    "memory_domain": slot.memory_domain.value,
                    "shape": list(slot.shape),
                    "slot_id": slot.slot_id,
                    "source_reuse_group_id": slot.source_reuse_group_id,
                    "tensor_names": list(slot.tensor_names),
                }
                for slot in self.slots
            ],
        }
        return _metadata_digest(payload)

    @property
    def peak_live_bytes(self) -> int:
        """Return conservative peak live bytes across operation boundaries."""

        peak = 0
        for point in range(self.operation_count + 1):
            live_bytes = sum(
                binding.bytes_required
                for binding in self.bindings
                if binding.first_live_index <= point <= binding.last_use_index
            )
            peak = max(peak, live_bytes)
        return peak


class RuntimeAllocationPlanError(AssertionError):
    """Raised when runtime allocation-plan evidence fails."""


def build_runtime_allocation_plan_report(
    lifetime_report: RuntimeBufferLifetimeReport,
) -> RuntimeAllocationPlanReport:
    """Build a bounded allocation-plan report from buffer lifetime evidence."""

    if not isinstance(lifetime_report, RuntimeBufferLifetimeReport):
        raise TypeError("runtime allocation source must be lifetime report")

    slot_id_by_group = {
        group.group_id: f"slot_{index + 1:03d}"
        for index, group in enumerate(lifetime_report.reuse_groups)
    }
    slots = tuple(
        _slot_from_reuse_group(group, slot_id_by_group[group.group_id])
        for group in lifetime_report.reuse_groups
    )
    bindings = tuple(
        _binding_from_lifetime(
            lifetime,
            slot_id_by_group.get(lifetime.reuse_group_id, "missing_slot"),
        )
        for lifetime in lifetime_report.lifetimes
    )
    issues = _derive_allocation_issues(
        len(lifetime_report.issues),
        bindings,
        slots,
    )
    return RuntimeAllocationPlanReport(
        graph_name=lifetime_report.graph_name,
        operation_count=lifetime_report.operation_count,
        source_lifetime_contract=lifetime_report.lifetime_contract,
        source_lifetime_schema_version=RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION,
        source_lifetime_issue_count=len(lifetime_report.issues),
        bindings=bindings,
        slots=slots,
        issues=issues,
    )


def assert_runtime_allocation_plan(
    report: RuntimeAllocationPlanReport,
) -> RuntimeAllocationPlanReport:
    """Return the report or raise when runtime allocation-plan evidence fails."""

    if not isinstance(report, RuntimeAllocationPlanReport):
        raise TypeError("runtime allocation plan report must be report object")
    if report.issues:
        lines = [f"runtime allocation plan failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeAllocationPlanError("\n".join(lines))
    return report


def runtime_allocation_plan_report_to_dict(
    report: RuntimeAllocationPlanReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible runtime allocation plan report."""

    if not isinstance(report, RuntimeAllocationPlanReport):
        raise TypeError("runtime allocation plan report must be report object")
    return {
        "allocation_contract": report.allocation_contract,
        "allocation_metadata_digest": report.allocation_metadata_digest,
        "bindings": [
            {
                "bytes_required": binding.bytes_required,
                "dtype": binding.dtype,
                "first_live_index": binding.first_live_index,
                "last_use_index": binding.last_use_index,
                "layout": binding.layout.value,
                "lifetime_kind": binding.lifetime_kind,
                "memory_domain": binding.memory_domain.value,
                "producer_index": binding.producer_index,
                "producer_operation": binding.producer_operation,
                "shape": list(binding.shape),
                "slot_id": binding.slot_id,
                "tensor_name": binding.tensor_name,
            }
            for binding in report.bindings
        ],
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "committed_reuse_savings_bytes": report.committed_reuse_savings_bytes,
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
        "peak_live_bytes": report.peak_live_bytes,
        "reuse_slot_count": report.reuse_slot_count,
        "schema_version": RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION,
        "slot_count": report.slot_count,
        "slots": [
            {
                "allocation_kind": slot.allocation_kind,
                "bytes_reserved": slot.bytes_reserved,
                "dtype": slot.dtype,
                "layout": slot.layout.value,
                "live_ranges_non_overlapping": slot.live_ranges_non_overlapping,
                "memory_domain": slot.memory_domain.value,
                "shape": list(slot.shape),
                "slot_id": slot.slot_id,
                "source_reuse_group_id": slot.source_reuse_group_id,
                "tensor_count": slot.tensor_count,
                "tensor_names": list(slot.tensor_names),
            }
            for slot in report.slots
        ],
        "source_lifetime_contract": report.source_lifetime_contract,
        "source_lifetime_issue_count": report.source_lifetime_issue_count,
        "source_lifetime_schema_version": report.source_lifetime_schema_version,
        "tensor_binding_count": report.tensor_binding_count,
        "total_reserved_bytes": report.total_reserved_bytes,
        "total_tensor_bytes": report.total_tensor_bytes,
    }


def dump_runtime_allocation_plan_report(report: RuntimeAllocationPlanReport) -> str:
    """Render a stable runtime allocation plan report."""

    text = json.dumps(
        runtime_allocation_plan_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_REPORT_BYTES:
        raise ValueError("runtime allocation plan report exceeds byte limit")
    return text + "\n"


def _slot_from_reuse_group(
    group: RuntimeBufferReuseGroup,
    slot_id: str,
) -> RuntimeAllocationSlot:
    return RuntimeAllocationSlot(
        slot_id=slot_id,
        source_reuse_group_id=group.group_id,
        memory_domain=group.memory_domain,
        layout=group.layout,
        dtype=group.dtype,
        shape=group.shape,
        bytes_reserved=group.bytes_per_buffer,
        tensor_names=group.tensor_names,
        allocation_kind="reused" if group.tensor_count > 1 else "exclusive",
        live_ranges_non_overlapping=group.non_overlapping,
    )


def _binding_from_lifetime(
    lifetime: RuntimeBufferLifetime,
    slot_id: str,
) -> RuntimeAllocationBinding:
    return RuntimeAllocationBinding(
        tensor_name=lifetime.tensor_name,
        slot_id=slot_id,
        producer_operation=lifetime.producer_operation,
        producer_index=lifetime.producer_index,
        first_live_index=lifetime.first_live_index,
        last_use_index=lifetime.last_use_index,
        lifetime_kind=lifetime.lifetime_kind,
        bytes_required=lifetime.bytes_allocated,
        memory_domain=lifetime.memory_domain,
        layout=lifetime.layout,
        dtype=lifetime.dtype,
        shape=lifetime.shape,
    )


def _derive_allocation_issues(
    source_lifetime_issue_count: int,
    bindings: tuple[RuntimeAllocationBinding, ...],
    slots: tuple[RuntimeAllocationSlot, ...],
) -> tuple[RuntimeAllocationIssue, ...]:
    issues: list[RuntimeAllocationIssue] = []
    if source_lifetime_issue_count > 0:
        issues.append(
            RuntimeAllocationIssue(
                subject="source_lifetime_report",
                issue_code="source_lifetime_report_failed",
            )
        )
    if not bindings:
        issues.append(
            RuntimeAllocationIssue(
                subject="graph",
                issue_code="produced_tensor_bindings_missing",
            )
        )
    slot_ids = {slot.slot_id for slot in slots}
    if len(slot_ids) != len(slots):
        issues.append(
            RuntimeAllocationIssue(
                subject="slots",
                issue_code="duplicate_slot_id",
            )
        )
    binding_tensor_names: set[str] = set()
    for binding in bindings:
        if binding.tensor_name in binding_tensor_names:
            issues.append(
                RuntimeAllocationIssue(
                    subject=binding.tensor_name,
                    issue_code="duplicate_tensor_binding",
                )
            )
        binding_tensor_names.add(binding.tensor_name)
        if binding.slot_id not in slot_ids:
            issues.append(
                RuntimeAllocationIssue(
                    subject=binding.tensor_name,
                    issue_code="allocation_slot_missing",
                )
            )
    bindings_by_slot = {
        slot.slot_id: tuple(binding for binding in bindings if binding.slot_id == slot.slot_id)
        for slot in slots
    }
    for slot in slots:
        slot_bindings = bindings_by_slot[slot.slot_id]
        if not slot_bindings:
            issues.append(
                RuntimeAllocationIssue(
                    subject=slot.slot_id,
                    issue_code="allocation_slot_unused",
                )
            )
            continue
        if tuple(binding.tensor_name for binding in slot_bindings) != slot.tensor_names:
            issues.append(
                RuntimeAllocationIssue(
                    subject=slot.slot_id,
                    issue_code="allocation_slot_tensor_mismatch",
                )
            )
        if not slot.live_ranges_non_overlapping:
            issues.append(
                RuntimeAllocationIssue(
                    subject=slot.slot_id,
                    issue_code="allocation_slot_lifetimes_overlap",
                )
            )
        for binding in slot_bindings:
            if binding.bytes_required > slot.bytes_reserved:
                issues.append(
                    RuntimeAllocationIssue(
                        subject=binding.tensor_name,
                        issue_code="allocation_slot_bytes_too_small",
                    )
                )
            if (
                binding.memory_domain != slot.memory_domain
                or binding.layout != slot.layout
                or binding.dtype != slot.dtype
                or binding.shape != slot.shape
            ):
                issues.append(
                    RuntimeAllocationIssue(
                        subject=binding.tensor_name,
                        issue_code="allocation_slot_contract_mismatch",
                    )
                )
        if _slot_bindings_overlap(slot_bindings):
            issues.append(
                RuntimeAllocationIssue(
                    subject=slot.slot_id,
                    issue_code="allocation_slot_binding_overlap",
                )
            )
    total_tensor_bytes = sum(binding.bytes_required for binding in bindings)
    total_reserved_bytes = sum(slot.bytes_reserved for slot in slots)
    if total_reserved_bytes > total_tensor_bytes:
        issues.append(
            RuntimeAllocationIssue(
                subject="plan",
                issue_code="reserved_bytes_exceed_tensor_bytes",
            )
        )
    return tuple(issues)


def _slot_bindings_overlap(bindings: tuple[RuntimeAllocationBinding, ...]) -> bool:
    ordered = sorted(bindings, key=lambda binding: binding.producer_index)
    previous_last_use = -1
    for binding in ordered:
        if previous_last_use >= binding.producer_index:
            return True
        previous_last_use = binding.last_use_index
    return False


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ALLOCATION_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime allocation identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_ALLOCATION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime allocation field limit")
    if value in _FORBIDDEN_ALLOCATION_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_dtype(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"^[A-Za-z][A-Za-z0-9_]*$", value):
        raise ValueError("allocation dtype must be a safe dtype identifier")


def _validate_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise TypeError("allocation shape must be a non-empty tuple")
    for dimension in value:
        _require_positive_int(dimension, "shape dimension")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_ALLOCATION_BINDINGS",
    "MAX_RUNTIME_ALLOCATION_FIELD_BYTES",
    "MAX_RUNTIME_ALLOCATION_ISSUES",
    "MAX_RUNTIME_ALLOCATION_REPORT_BYTES",
    "MAX_RUNTIME_ALLOCATION_SLOTS",
    "RUNTIME_ALLOCATION_PLAN_CONTRACT",
    "RUNTIME_ALLOCATION_PLAN_REPORT_SCHEMA_VERSION",
    "RuntimeAllocationBinding",
    "RuntimeAllocationIssue",
    "RuntimeAllocationPlanError",
    "RuntimeAllocationPlanReport",
    "RuntimeAllocationSlot",
    "assert_runtime_allocation_plan",
    "build_runtime_allocation_plan_report",
    "dump_runtime_allocation_plan_report",
    "runtime_allocation_plan_report_to_dict",
]
