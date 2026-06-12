"""Data-only runtime buffer lifetime analysis."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from math import prod
from typing import NamedTuple

from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, TensorRef
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.partitioning import Assignment, PartitionPlan

RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_buffer_lifetime_report.v0"
)
RUNTIME_BUFFER_LIFETIME_CONTRACT = "runtime_buffer_lifetime.data_only.v0"
MAX_RUNTIME_BUFFER_LIFETIMES = 8192
MAX_RUNTIME_BUFFER_REUSE_GROUPS = 8192
MAX_RUNTIME_BUFFER_LIFETIME_ISSUES = 64
MAX_RUNTIME_BUFFER_LIFETIME_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_BUFFER_LIFETIME_FIELD_BYTES = 512

_BUFFER_LIFETIME_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_BUFFER_LIFETIME_TEXT = frozenset(
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
class RuntimeBufferLifetime:
    """Lifetime facts for one produced tensor buffer."""

    tensor_name: str
    producer_operation: str
    producer_index: int
    first_live_index: int
    last_use_index: int
    last_consumer_operation: str
    lifetime_kind: str
    bytes_allocated: int
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    shape: tuple[int, ...]
    reuse_group_id: str
    reusable: bool

    def __post_init__(self) -> None:
        _validate_text(self.tensor_name, "tensor_name")
        _validate_text(self.producer_operation, "producer_operation")
        _require_non_negative_int(self.producer_index, "producer_index")
        _require_non_negative_int(self.first_live_index, "first_live_index")
        _require_non_negative_int(self.last_use_index, "last_use_index")
        if self.last_use_index < self.first_live_index:
            raise ValueError("buffer lifetime last_use_index precedes first_live_index")
        _validate_text(self.last_consumer_operation, "last_consumer_operation")
        if self.lifetime_kind not in {"intermediate", "graph_output"}:
            raise ValueError("buffer lifetime kind is unsupported")
        _require_positive_int(self.bytes_allocated, "bytes_allocated")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("buffer lifetime memory_domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("buffer lifetime layout must be LayoutKind")
        _validate_dtype(self.dtype)
        _validate_shape(self.shape)
        _validate_text(self.reuse_group_id, "reuse_group_id")
        if not isinstance(self.reusable, bool):
            raise TypeError("buffer lifetime reusable must be bool")


@dataclass(frozen=True)
class RuntimeBufferReuseGroup:
    """Conservative same-shape reuse group for non-overlapping lifetimes."""

    group_id: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    shape: tuple[int, ...]
    tensor_names: tuple[str, ...]
    bytes_per_buffer: int
    total_tensor_bytes: int
    reuse_savings_upper_bound_bytes: int
    non_overlapping: bool

    def __post_init__(self) -> None:
        _validate_text(self.group_id, "group_id")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("reuse group memory_domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("reuse group layout must be LayoutKind")
        _validate_dtype(self.dtype)
        _validate_shape(self.shape)
        if type(self.tensor_names) is not tuple:
            raise TypeError("reuse group tensor_names must be a tuple")
        if not self.tensor_names:
            raise ValueError("reuse group tensor_names must not be empty")
        for tensor_name in self.tensor_names:
            _validate_text(tensor_name, "reuse group tensor_name")
        _require_positive_int(self.bytes_per_buffer, "bytes_per_buffer")
        _require_positive_int(self.total_tensor_bytes, "total_tensor_bytes")
        _require_non_negative_int(
            self.reuse_savings_upper_bound_bytes,
            "reuse_savings_upper_bound_bytes",
        )
        if self.total_tensor_bytes != self.bytes_per_buffer * len(self.tensor_names):
            raise ValueError("reuse group total bytes must match tensor count")
        expected_savings = self.total_tensor_bytes - self.bytes_per_buffer
        if self.reuse_savings_upper_bound_bytes != expected_savings:
            raise ValueError("reuse group savings must be derived")
        if not isinstance(self.non_overlapping, bool):
            raise TypeError("reuse group non_overlapping must be bool")

    @property
    def tensor_count(self) -> int:
        """Return the number of tensor lifetimes in this group."""

        return len(self.tensor_names)


@dataclass(frozen=True)
class RuntimeBufferLifetimeIssue:
    """One derived runtime buffer lifetime issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "issue subject")
        _validate_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeBufferLifetimeReport:
    """Deterministic buffer lifetime report for a runtime plan."""

    graph_name: str
    operation_count: int
    lifetimes: tuple[RuntimeBufferLifetime, ...]
    reuse_groups: tuple[RuntimeBufferReuseGroup, ...]
    issues: tuple[RuntimeBufferLifetimeIssue, ...]
    lifetime_contract: str = RUNTIME_BUFFER_LIFETIME_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        if self.lifetime_contract != RUNTIME_BUFFER_LIFETIME_CONTRACT:
            raise ValueError("runtime buffer lifetime contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime buffer lifetime blocked surfaces changed")
        if type(self.lifetimes) is not tuple:
            raise TypeError("runtime buffer lifetimes must be a tuple")
        if len(self.lifetimes) > MAX_RUNTIME_BUFFER_LIFETIMES:
            raise ValueError("runtime buffer lifetime count exceeds limit")
        for lifetime in self.lifetimes:
            if not isinstance(lifetime, RuntimeBufferLifetime):
                raise TypeError("runtime buffer lifetimes must be lifetime objects")
        if type(self.reuse_groups) is not tuple:
            raise TypeError("runtime buffer reuse groups must be a tuple")
        if len(self.reuse_groups) > MAX_RUNTIME_BUFFER_REUSE_GROUPS:
            raise ValueError("runtime buffer reuse group count exceeds limit")
        for group in self.reuse_groups:
            if not isinstance(group, RuntimeBufferReuseGroup):
                raise TypeError("runtime buffer reuse groups must be group objects")
        if type(self.issues) is not tuple:
            raise TypeError("runtime buffer lifetime issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_BUFFER_LIFETIME_ISSUES:
            raise ValueError("runtime buffer lifetime issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeBufferLifetimeIssue):
                raise TypeError("runtime buffer lifetime issues must be issue objects")
        expected_issues = _derive_lifetime_issues(self.lifetimes, self.reuse_groups)
        if self.issues != expected_issues:
            raise ValueError("runtime buffer lifetime issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether buffer lifetime analysis passed."""

        return not self.issues

    @property
    def tensor_lifetime_count(self) -> int:
        """Return produced tensor lifetime count."""

        return len(self.lifetimes)

    @property
    def reuse_group_count(self) -> int:
        """Return reuse group count."""

        return len(self.reuse_groups)

    @property
    def total_tensor_bytes(self) -> int:
        """Return total bytes across produced tensor lifetimes."""

        return sum(lifetime.bytes_allocated for lifetime in self.lifetimes)

    @property
    def reuse_savings_upper_bound_bytes(self) -> int:
        """Return conservative upper-bound bytes saved by exact buffer reuse."""

        return sum(group.reuse_savings_upper_bound_bytes for group in self.reuse_groups)

    @property
    def lifetime_metadata_digest(self) -> str:
        """Return a digest over buffer-lifetime metadata only."""

        payload = {
            "graph_name": self.graph_name,
            "issues": [
                {
                    "issue_code": issue.issue_code,
                    "subject": issue.subject,
                }
                for issue in self.issues
            ],
            "lifetime_contract": self.lifetime_contract,
            "lifetimes": [
                {
                    "bytes_allocated": lifetime.bytes_allocated,
                    "dtype": lifetime.dtype,
                    "first_live_index": lifetime.first_live_index,
                    "last_consumer_operation": lifetime.last_consumer_operation,
                    "last_use_index": lifetime.last_use_index,
                    "layout": lifetime.layout.value,
                    "lifetime_kind": lifetime.lifetime_kind,
                    "memory_domain": lifetime.memory_domain.value,
                    "producer_index": lifetime.producer_index,
                    "producer_operation": lifetime.producer_operation,
                    "reusable": lifetime.reusable,
                    "reuse_group_id": lifetime.reuse_group_id,
                    "shape": list(lifetime.shape),
                    "tensor_name": lifetime.tensor_name,
                }
                for lifetime in self.lifetimes
            ],
            "operation_count": self.operation_count,
            "reuse_groups": [
                {
                    "bytes_per_buffer": group.bytes_per_buffer,
                    "dtype": group.dtype,
                    "group_id": group.group_id,
                    "layout": group.layout.value,
                    "memory_domain": group.memory_domain.value,
                    "non_overlapping": group.non_overlapping,
                    "reuse_savings_upper_bound_bytes": (
                        group.reuse_savings_upper_bound_bytes
                    ),
                    "shape": list(group.shape),
                    "tensor_names": list(group.tensor_names),
                    "total_tensor_bytes": group.total_tensor_bytes,
                }
                for group in self.reuse_groups
            ],
        }
        return _metadata_digest(payload)

    @property
    def peak_live_bytes(self) -> int:
        """Return conservative peak live bytes across operation boundaries."""

        peak = 0
        for point in range(self.operation_count + 1):
            live_bytes = sum(
                lifetime.bytes_allocated
                for lifetime in self.lifetimes
                if lifetime.first_live_index <= point <= lifetime.last_use_index
            )
            peak = max(peak, live_bytes)
        return peak


class RuntimeBufferLifetimeError(AssertionError):
    """Raised when runtime buffer lifetime evidence fails."""


def build_runtime_buffer_lifetime_report(
    graph: ComputeGraph,
    plan: PartitionPlan,
) -> RuntimeBufferLifetimeReport:
    """Build a bounded buffer lifetime report from a graph and runtime plan."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("graph must be ComputeGraph")
    if not isinstance(plan, PartitionPlan):
        raise TypeError("plan must be PartitionPlan")
    if graph.name != plan.graph_name:
        raise ValueError("runtime buffer lifetime graph and plan names must match")

    assignments = _assignments_by_operation(graph, plan)
    drafts = _lifetime_drafts(graph, assignments)
    lifetimes, reuse_groups = _assign_reuse_groups(drafts)
    issues = _derive_lifetime_issues(lifetimes, reuse_groups)
    return RuntimeBufferLifetimeReport(
        graph_name=graph.name,
        operation_count=len(graph.operations),
        lifetimes=lifetimes,
        reuse_groups=reuse_groups,
        issues=issues,
    )


def assert_runtime_buffer_lifetime(
    report: RuntimeBufferLifetimeReport,
) -> RuntimeBufferLifetimeReport:
    """Return the report or raise when runtime buffer lifetime evidence fails."""

    if not isinstance(report, RuntimeBufferLifetimeReport):
        raise TypeError("runtime buffer lifetime report must be report object")
    if report.issues:
        lines = [f"runtime buffer lifetime failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeBufferLifetimeError("\n".join(lines))
    return report


def runtime_buffer_lifetime_report_to_dict(
    report: RuntimeBufferLifetimeReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible buffer lifetime report."""

    if not isinstance(report, RuntimeBufferLifetimeReport):
        raise TypeError("runtime buffer lifetime report must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "lifetime_contract": report.lifetime_contract,
        "lifetime_metadata_digest": report.lifetime_metadata_digest,
        "lifetimes": [
            {
                "bytes_allocated": lifetime.bytes_allocated,
                "dtype": lifetime.dtype,
                "first_live_index": lifetime.first_live_index,
                "last_consumer_operation": lifetime.last_consumer_operation,
                "last_use_index": lifetime.last_use_index,
                "layout": lifetime.layout.value,
                "lifetime_kind": lifetime.lifetime_kind,
                "memory_domain": lifetime.memory_domain.value,
                "producer_index": lifetime.producer_index,
                "producer_operation": lifetime.producer_operation,
                "reusable": lifetime.reusable,
                "reuse_group_id": lifetime.reuse_group_id,
                "shape": list(lifetime.shape),
                "tensor_name": lifetime.tensor_name,
            }
            for lifetime in report.lifetimes
        ],
        "operation_count": report.operation_count,
        "passed": report.passed,
        "peak_live_bytes": report.peak_live_bytes,
        "reuse_group_count": report.reuse_group_count,
        "reuse_groups": [
            {
                "bytes_per_buffer": group.bytes_per_buffer,
                "dtype": group.dtype,
                "group_id": group.group_id,
                "layout": group.layout.value,
                "memory_domain": group.memory_domain.value,
                "non_overlapping": group.non_overlapping,
                "reuse_savings_upper_bound_bytes": (
                    group.reuse_savings_upper_bound_bytes
                ),
                "shape": list(group.shape),
                "tensor_count": group.tensor_count,
                "tensor_names": list(group.tensor_names),
                "total_tensor_bytes": group.total_tensor_bytes,
            }
            for group in report.reuse_groups
        ],
        "reuse_savings_upper_bound_bytes": report.reuse_savings_upper_bound_bytes,
        "schema_version": RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION,
        "tensor_lifetime_count": report.tensor_lifetime_count,
        "total_tensor_bytes": report.total_tensor_bytes,
    }


def dump_runtime_buffer_lifetime_report(report: RuntimeBufferLifetimeReport) -> str:
    """Render a stable runtime buffer lifetime report."""

    text = json.dumps(
        runtime_buffer_lifetime_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_BUFFER_LIFETIME_REPORT_BYTES:
        raise ValueError("runtime buffer lifetime report exceeds byte limit")
    return text + "\n"


def _assignments_by_operation(
    graph: ComputeGraph,
    plan: PartitionPlan,
) -> dict[str, Assignment]:
    operation_names = graph.operation_names()
    assignment_names = tuple(assignment.operation_name for assignment in plan.assignments)
    if assignment_names != operation_names:
        raise ValueError("runtime buffer lifetime plan assignments must match graph order")
    return {assignment.operation_name: assignment for assignment in plan.assignments}


def _lifetime_drafts(
    graph: ComputeGraph,
    assignments: dict[str, Assignment],
) -> tuple[LifetimeDraft, ...]:
    consumer_indices: dict[str, list[int]] = {}
    for operation_index, operation in enumerate(graph.operations):
        for tensor in operation.inputs:
            consumer_indices.setdefault(tensor.name, []).append(operation_index)

    drafts: list[LifetimeDraft] = []
    produced_tensors: set[str] = set()
    for operation_index, operation in enumerate(graph.operations):
        assignment = assignments[operation.name]
        for tensor in operation.outputs:
            if tensor.name in produced_tensors:
                raise ValueError("runtime buffer lifetime tensor producer is not unique")
            produced_tensors.add(tensor.name)
            consumers = tuple(consumer_indices.get(tensor.name, ()))
            if consumers:
                last_use_index = max(consumers)
                last_consumer = graph.operations[last_use_index].name
                lifetime_kind = "intermediate"
            else:
                last_use_index = len(graph.operations)
                last_consumer = "graph_output"
                lifetime_kind = "graph_output"
            drafts.append(
                LifetimeDraft(
                    tensor=tensor,
                    producer_operation=operation.name,
                    producer_index=operation_index,
                    first_live_index=operation_index,
                    last_use_index=last_use_index,
                    last_consumer_operation=last_consumer,
                    lifetime_kind=lifetime_kind,
                    bytes_allocated=_tensor_nbytes(tensor),
                    memory_domain=assignment.memory_domain,
                    layout=assignment.produced_layout,
                )
            )
    if len(drafts) > MAX_RUNTIME_BUFFER_LIFETIMES:
        raise ValueError("runtime buffer lifetime draft count exceeds limit")
    return tuple(drafts)


def _assign_reuse_groups(
    drafts: tuple[LifetimeDraft, ...],
) -> tuple[tuple[RuntimeBufferLifetime, ...], tuple[RuntimeBufferReuseGroup, ...]]:
    states: list[ReuseGroupState] = []
    for draft in sorted(drafts, key=_draft_sort_key):
        state = _find_reuse_group(states, draft)
        if state is None:
            state = ReuseGroupState(
                group_id=f"reuse_group_{len(states) + 1:03d}",
                key=draft.reuse_key,
            )
            states.append(state)
        state.drafts.append(draft)
        state.last_use_index = draft.last_use_index

    group_sizes = {state.group_id: len(state.drafts) for state in states}
    lifetime_by_tensor: dict[str, RuntimeBufferLifetime] = {}
    for state in states:
        for draft in state.drafts:
            lifetime_by_tensor[draft.tensor.name] = RuntimeBufferLifetime(
                tensor_name=draft.tensor.name,
                producer_operation=draft.producer_operation,
                producer_index=draft.producer_index,
                first_live_index=draft.first_live_index,
                last_use_index=draft.last_use_index,
                last_consumer_operation=draft.last_consumer_operation,
                lifetime_kind=draft.lifetime_kind,
                bytes_allocated=draft.bytes_allocated,
                memory_domain=draft.memory_domain,
                layout=draft.layout,
                dtype=draft.tensor.dtype,
                shape=draft.tensor.shape,
                reuse_group_id=state.group_id,
                reusable=group_sizes[state.group_id] > 1,
            )

    lifetimes = tuple(
        lifetime_by_tensor[draft.tensor.name]
        for draft in sorted(drafts, key=lambda item: item.producer_index)
    )
    groups = tuple(_reuse_group_from_state(state) for state in states)
    return lifetimes, groups


def _find_reuse_group(
    states: list[ReuseGroupState],
    draft: LifetimeDraft,
) -> ReuseGroupState | None:
    for state in states:
        if state.key == draft.reuse_key and state.last_use_index < draft.producer_index:
            return state
    return None


def _reuse_group_from_state(state: ReuseGroupState) -> RuntimeBufferReuseGroup:
    first = state.drafts[0]
    tensor_names = tuple(draft.tensor.name for draft in state.drafts)
    total_tensor_bytes = first.bytes_allocated * len(state.drafts)
    return RuntimeBufferReuseGroup(
        group_id=state.group_id,
        memory_domain=first.memory_domain,
        layout=first.layout,
        dtype=first.tensor.dtype,
        shape=first.tensor.shape,
        tensor_names=tensor_names,
        bytes_per_buffer=first.bytes_allocated,
        total_tensor_bytes=total_tensor_bytes,
        reuse_savings_upper_bound_bytes=total_tensor_bytes - first.bytes_allocated,
        non_overlapping=_group_non_overlapping(tuple(state.drafts)),
    )


def _group_non_overlapping(drafts: tuple[LifetimeDraft, ...]) -> bool:
    ordered = sorted(drafts, key=lambda draft: draft.producer_index)
    previous_last_use = -1
    for draft in ordered:
        if previous_last_use >= draft.producer_index:
            return False
        previous_last_use = draft.last_use_index
    return True


def _derive_lifetime_issues(
    lifetimes: tuple[RuntimeBufferLifetime, ...],
    reuse_groups: tuple[RuntimeBufferReuseGroup, ...],
) -> tuple[RuntimeBufferLifetimeIssue, ...]:
    issues: list[RuntimeBufferLifetimeIssue] = []
    if not lifetimes:
        issues.append(
            RuntimeBufferLifetimeIssue(
                subject="graph",
                issue_code="produced_tensor_lifetimes_missing",
            )
        )
    group_ids = {group.group_id for group in reuse_groups}
    for lifetime in lifetimes:
        if lifetime.reuse_group_id not in group_ids:
            issues.append(
                RuntimeBufferLifetimeIssue(
                    subject=lifetime.tensor_name,
                    issue_code="reuse_group_missing",
                )
            )
    for group in reuse_groups:
        if not group.non_overlapping:
            issues.append(
                RuntimeBufferLifetimeIssue(
                    subject=group.group_id,
                    issue_code="reuse_group_lifetimes_overlap",
                )
            )
    return tuple(issues)


def _draft_sort_key(
    draft: LifetimeDraft,
) -> tuple[str, str, str, tuple[int, ...], int, int, str]:
    return (
        draft.memory_domain.value,
        draft.layout.value,
        draft.tensor.dtype,
        draft.tensor.shape,
        draft.bytes_allocated,
        draft.producer_index,
        draft.tensor.name,
    )


def _tensor_nbytes(tensor: TensorRef) -> int:
    return prod(tensor.shape) * dtype_size_bytes(tensor.dtype)


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _BUFFER_LIFETIME_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime buffer lifetime identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_BUFFER_LIFETIME_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime buffer lifetime field limit")
    if value in _FORBIDDEN_BUFFER_LIFETIME_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_dtype(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"^[A-Za-z][A-Za-z0-9_]*$", value):
        raise ValueError("buffer lifetime dtype must be a safe dtype identifier")


def _validate_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise TypeError("buffer lifetime shape must be a non-empty tuple")
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


class LifetimeDraft(NamedTuple):
    """Internal lifetime data before reuse groups are assigned."""

    tensor: TensorRef
    producer_operation: str
    producer_index: int
    first_live_index: int
    last_use_index: int
    last_consumer_operation: str
    lifetime_kind: str
    bytes_allocated: int
    memory_domain: MemoryDomainKind
    layout: LayoutKind

    @property
    def reuse_key(self) -> tuple[MemoryDomainKind, LayoutKind, str, tuple[int, ...], int]:
        """Return exact-match key required for safe reuse candidates."""

        return (
            self.memory_domain,
            self.layout,
            self.tensor.dtype,
            self.tensor.shape,
            self.bytes_allocated,
        )


@dataclass
class ReuseGroupState:
    """Mutable internal greedy allocation state."""

    group_id: str
    key: tuple[MemoryDomainKind, LayoutKind, str, tuple[int, ...], int]
    drafts: list[LifetimeDraft]
    last_use_index: int = -1

    def __init__(
        self,
        *,
        group_id: str,
        key: tuple[MemoryDomainKind, LayoutKind, str, tuple[int, ...], int],
    ) -> None:
        self.group_id = group_id
        self.key = key
        self.drafts = []
        self.last_use_index = -1


__all__ = [
    "MAX_RUNTIME_BUFFER_LIFETIMES",
    "MAX_RUNTIME_BUFFER_LIFETIME_FIELD_BYTES",
    "MAX_RUNTIME_BUFFER_LIFETIME_ISSUES",
    "MAX_RUNTIME_BUFFER_LIFETIME_REPORT_BYTES",
    "MAX_RUNTIME_BUFFER_REUSE_GROUPS",
    "RUNTIME_BUFFER_LIFETIME_CONTRACT",
    "RUNTIME_BUFFER_LIFETIME_REPORT_SCHEMA_VERSION",
    "RuntimeBufferLifetime",
    "RuntimeBufferLifetimeError",
    "RuntimeBufferLifetimeIssue",
    "RuntimeBufferLifetimeReport",
    "RuntimeBufferReuseGroup",
    "assert_runtime_buffer_lifetime",
    "build_runtime_buffer_lifetime_report",
    "dump_runtime_buffer_lifetime_report",
    "runtime_buffer_lifetime_report_to_dict",
]
