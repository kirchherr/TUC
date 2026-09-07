"""Data-only heterogeneous runtime storage planning."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from hashlib import sha256
from math import prod
from typing import NamedTuple

from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, TensorRef
from tuc.runtime.buffer_lifetime import (
    assert_runtime_buffer_lifetime,
    build_runtime_buffer_lifetime_report,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.layout_conversion_evidence import (
    assert_runtime_layout_conversion_evidence,
    build_runtime_layout_conversion_evidence_report,
)
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.plan import LayoutConversionCost, RuntimeTransferEdge
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
from tuc.runtime.transfer_evidence import (
    assert_runtime_transfer_evidence,
    build_runtime_transfer_evidence_report,
)

RUNTIME_HETEROGENEOUS_STORAGE_PLAN_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_heterogeneous_storage_plan_report.v0"
)
RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT = (
    "runtime_heterogeneous_storage_plan.data_only.v0"
)
RUNTIME_HETEROGENEOUS_STORAGE_PLAN_SCOPE = (
    "produced_layout_and_transfer_staging_storage"
)
RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_POLICY = "does_not_allocate_or_execute"
RUNTIME_HETEROGENEOUS_STORAGE_LAYOUT_POLICY = "row_major_and_blocked_2x2_only"
RUNTIME_HETEROGENEOUS_STORAGE_REUSE_POLICY = (
    "same_role_domain_layout_dtype_physical_shape_non_overlapping"
)
RUNTIME_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM = (
    "planning_labels_not_physical_residency"
)
RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM = "not_measured"
RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS = "forbidden"
RUNTIME_HETEROGENEOUS_STORAGE_EVENT_PHASES = (
    "layout_conversion",
    "transfer",
    "consumer_execution",
    "output_produced",
)
RUNTIME_HETEROGENEOUS_STORAGE_ROLES = (
    "produced_value",
    "layout_staging",
    "transfer_target_staging",
)
RUNTIME_HETEROGENEOUS_STORAGE_BLOCKED_EXECUTION_SURFACES = (
    *RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    "allocator_plugin_discovery",
    "external_allocator_calls",
    "memory_mapping",
    "runtime_memory_allocation",
)
RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE = (2, 2)
MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES = 8192
MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS = 8192
MAX_RUNTIME_HETEROGENEOUS_STORAGE_ISSUES = 64
MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS = 2_000_000
MAX_RUNTIME_HETEROGENEOUS_STORAGE_RESERVED_BYTES = 128 * 1024 * 1024
MAX_RUNTIME_HETEROGENEOUS_STORAGE_REPORT_BYTES = 256 * 1024
MAX_RUNTIME_HETEROGENEOUS_STORAGE_FIELD_BYTES = 512

_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_TEXT = frozenset(
    {
        "address",
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "environment",
        "executable",
        "generated_code",
        "handle",
        "host_path",
        "import_module",
        "network",
        "plugin_entrypoint",
        "pointer",
        "python_source",
        "raw_tensor_value",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageLifetime:
    """One planned physical storage object's bounded lifetime."""

    storage_id: str
    tensor_name: str
    storage_role: str
    source_operation: str
    target_operation: str
    first_live_event: int
    first_live_phase: str
    last_use_event: int
    last_use_phase: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    logical_shape: tuple[int, ...]
    physical_shape: tuple[int, ...]
    tile_shape: tuple[int, ...]
    logical_element_count: int
    physical_element_count: int
    padding_element_count: int
    logical_bytes: int
    physical_bytes: int
    slot_id: str
    reusable: bool

    def __post_init__(self) -> None:
        for text_value, label in (
            (self.storage_id, "storage_id"),
            (self.tensor_name, "tensor_name"),
            (self.source_operation, "source_operation"),
            (self.target_operation, "target_operation"),
            (self.slot_id, "slot_id"),
        ):
            _validate_text(text_value, label)
        if self.storage_role not in RUNTIME_HETEROGENEOUS_STORAGE_ROLES:
            raise ValueError("heterogeneous storage role is unsupported")
        _require_non_negative_int(self.first_live_event, "first_live_event")
        _require_non_negative_int(self.last_use_event, "last_use_event")
        if self.last_use_event < self.first_live_event:
            raise ValueError("heterogeneous storage lifetime is reversed")
        if self.first_live_phase not in RUNTIME_HETEROGENEOUS_STORAGE_EVENT_PHASES:
            raise ValueError("heterogeneous storage first-live phase is unsupported")
        if self.last_use_phase not in (
            *RUNTIME_HETEROGENEOUS_STORAGE_EVENT_PHASES,
            "graph_end",
        ):
            raise ValueError("heterogeneous storage last-use phase is unsupported")
        _validate_role_phases(self)
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("heterogeneous storage domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("heterogeneous storage layout must be LayoutKind")
        _validate_shape(self.logical_shape, "logical_shape")
        _validate_shape(self.physical_shape, "physical_shape")
        _validate_tile_shape(self.tile_shape)
        _validate_dtype(self.dtype)
        for integer_value, label in (
            (self.logical_element_count, "logical_element_count"),
            (self.physical_element_count, "physical_element_count"),
            (self.logical_bytes, "logical_bytes"),
            (self.physical_bytes, "physical_bytes"),
        ):
            _require_positive_int(integer_value, label)
        _require_non_negative_int(self.padding_element_count, "padding_element_count")
        expected_logical_elements = prod(self.logical_shape)
        expected_physical_elements = prod(self.physical_shape)
        if self.logical_element_count != expected_logical_elements:
            raise ValueError("heterogeneous storage logical element count mismatch")
        if self.physical_element_count != expected_physical_elements:
            raise ValueError("heterogeneous storage physical element count mismatch")
        if self.physical_element_count > MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS:
            raise ValueError("heterogeneous storage physical element limit exceeded")
        if self.padding_element_count != (
            self.physical_element_count - self.logical_element_count
        ):
            raise ValueError("heterogeneous storage padding accounting mismatch")
        dtype_bytes = dtype_size_bytes(self.dtype)
        if self.logical_bytes != self.logical_element_count * dtype_bytes:
            raise ValueError("heterogeneous storage logical byte count mismatch")
        if self.physical_bytes != self.physical_element_count * dtype_bytes:
            raise ValueError("heterogeneous storage physical byte count mismatch")
        _validate_layout_shape(
            layout=self.layout,
            logical_shape=self.logical_shape,
            physical_shape=self.physical_shape,
            tile_shape=self.tile_shape,
        )
        if not isinstance(self.reusable, bool):
            raise TypeError("heterogeneous storage reusable must be bool")


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageSlot:
    """One conservative reusable slot for identical physical storage."""

    slot_id: str
    storage_role: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    physical_shape: tuple[int, ...]
    tile_shape: tuple[int, ...]
    bytes_reserved: int
    storage_ids: tuple[str, ...]
    total_storage_bytes: int
    reuse_savings_bytes: int
    non_overlapping: bool

    def __post_init__(self) -> None:
        _validate_text(self.slot_id, "slot_id")
        if self.storage_role not in RUNTIME_HETEROGENEOUS_STORAGE_ROLES:
            raise ValueError("heterogeneous storage slot role is unsupported")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("heterogeneous storage slot domain must be MemoryDomainKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("heterogeneous storage slot layout must be LayoutKind")
        _validate_dtype(self.dtype)
        _validate_shape(self.physical_shape, "slot physical_shape")
        _validate_tile_shape(self.tile_shape)
        _require_positive_int(self.bytes_reserved, "slot bytes_reserved")
        if type(self.storage_ids) is not tuple or not self.storage_ids:
            raise ValueError("heterogeneous storage slot IDs must be a non-empty tuple")
        for storage_id in self.storage_ids:
            _validate_text(storage_id, "slot storage_id")
        if len(set(self.storage_ids)) != len(self.storage_ids):
            raise ValueError("heterogeneous storage slot IDs must be unique")
        _require_positive_int(self.total_storage_bytes, "slot total_storage_bytes")
        _require_non_negative_int(self.reuse_savings_bytes, "slot reuse_savings_bytes")
        expected_total = self.bytes_reserved * len(self.storage_ids)
        if self.total_storage_bytes != expected_total:
            raise ValueError("heterogeneous storage slot total bytes mismatch")
        if self.reuse_savings_bytes != expected_total - self.bytes_reserved:
            raise ValueError("heterogeneous storage slot reuse savings mismatch")
        if not isinstance(self.non_overlapping, bool):
            raise TypeError("heterogeneous storage slot non_overlapping must be bool")

    @property
    def storage_count(self) -> int:
        """Return the number of storage lifetimes assigned to this slot."""

        return len(self.storage_ids)


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageDomainPeak:
    """Peak live and reserved physical bytes for one planned domain."""

    memory_domain: MemoryDomainKind
    peak_live_physical_bytes: int
    reserved_slot_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("heterogeneous storage peak domain must be MemoryDomainKind")
        _require_positive_int(
            self.peak_live_physical_bytes,
            "peak_live_physical_bytes",
        )
        _require_positive_int(self.reserved_slot_bytes, "reserved_slot_bytes")
        if self.peak_live_physical_bytes > self.reserved_slot_bytes:
            raise ValueError("heterogeneous storage domain peak exceeds reservation")


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageIssue:
    """One derived heterogeneous storage-plan issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "issue subject")
        _validate_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeHeterogeneousStoragePlanReport:
    """Deterministic physical storage plan for one heterogeneous graph."""

    graph_name: str
    operation_count: int
    event_count: int
    planned_transfer_count: int
    planned_layout_conversion_count: int
    source_transfer_partition_plan_digest: str
    source_layout_partition_plan_digest: str
    source_buffer_lifetime_digest: str
    source_transfer_evidence_digest: str
    source_layout_conversion_evidence_digest: str
    lifetimes: tuple[RuntimeHeterogeneousStorageLifetime, ...]
    slots: tuple[RuntimeHeterogeneousStorageSlot, ...]
    domain_peaks: tuple[RuntimeHeterogeneousStorageDomainPeak, ...]
    issues: tuple[RuntimeHeterogeneousStorageIssue, ...]
    storage_contract: str = RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT
    storage_scope: str = RUNTIME_HETEROGENEOUS_STORAGE_PLAN_SCOPE
    execution_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_POLICY
    layout_sizing_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_LAYOUT_POLICY
    reuse_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_REUSE_POLICY
    residency_claim: str = RUNTIME_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM
    performance_claim: str = RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    external_artifacts: str = RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_HETEROGENEOUS_STORAGE_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "graph_name")
        _require_positive_int(self.operation_count, "operation_count")
        _require_positive_int(self.event_count, "event_count")
        if self.event_count != self.operation_count * 4 + 1:
            raise ValueError("heterogeneous storage event count mismatch")
        _require_non_negative_int(self.planned_transfer_count, "planned_transfer_count")
        _require_non_negative_int(
            self.planned_layout_conversion_count,
            "planned_layout_conversion_count",
        )
        for value, label in (
            (
                self.source_transfer_partition_plan_digest,
                "source_transfer_partition_plan_digest",
            ),
            (
                self.source_layout_partition_plan_digest,
                "source_layout_partition_plan_digest",
            ),
            (self.source_buffer_lifetime_digest, "source_buffer_lifetime_digest"),
            (self.source_transfer_evidence_digest, "source_transfer_evidence_digest"),
            (
                self.source_layout_conversion_evidence_digest,
                "source_layout_conversion_evidence_digest",
            ),
        ):
            _validate_digest(value, label)
        _validate_contract(self)
        if type(self.lifetimes) is not tuple or not self.lifetimes:
            raise ValueError("heterogeneous storage lifetimes must be non-empty tuple")
        if len(self.lifetimes) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES:
            raise ValueError("heterogeneous storage lifetime count exceeds limit")
        for lifetime in self.lifetimes:
            if not isinstance(lifetime, RuntimeHeterogeneousStorageLifetime):
                raise TypeError("heterogeneous storage lifetimes must be lifetime objects")
            if lifetime.last_use_event >= self.event_count:
                raise ValueError("heterogeneous storage lifetime exceeds event timeline")
        if type(self.slots) is not tuple or not self.slots:
            raise ValueError("heterogeneous storage slots must be non-empty tuple")
        if len(self.slots) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS:
            raise ValueError("heterogeneous storage slot count exceeds limit")
        for slot in self.slots:
            if not isinstance(slot, RuntimeHeterogeneousStorageSlot):
                raise TypeError("heterogeneous storage slots must be slot objects")
        if type(self.domain_peaks) is not tuple or not self.domain_peaks:
            raise ValueError("heterogeneous storage domain peaks must be non-empty tuple")
        for peak in self.domain_peaks:
            if not isinstance(peak, RuntimeHeterogeneousStorageDomainPeak):
                raise TypeError("heterogeneous storage peaks must be peak objects")
        expected_peaks = _derive_domain_peaks(
            self.lifetimes,
            self.slots,
            self.event_count,
        )
        if self.domain_peaks != expected_peaks:
            raise ValueError("heterogeneous storage domain peaks must be derived")
        if self.layout_staging_count != self.planned_layout_conversion_count:
            raise ValueError("heterogeneous storage layout staging count mismatch")
        if self.transfer_staging_count != self.planned_transfer_count:
            raise ValueError("heterogeneous storage transfer staging count mismatch")
        if self.total_reserved_physical_bytes > (
            MAX_RUNTIME_HETEROGENEOUS_STORAGE_RESERVED_BYTES
        ):
            raise ValueError("heterogeneous storage reserved byte limit exceeded")
        if type(self.issues) is not tuple:
            raise TypeError("heterogeneous storage issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_ISSUES:
            raise ValueError("heterogeneous storage issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeHeterogeneousStorageIssue):
                raise TypeError("heterogeneous storage issues must be issue objects")
        expected_issues = _derive_issues(self.lifetimes, self.slots)
        if self.issues != expected_issues:
            raise ValueError("heterogeneous storage issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the storage plan is internally consistent."""

        return not self.issues

    @property
    def produced_storage_count(self) -> int:
        return _role_count(self.lifetimes, "produced_value")

    @property
    def layout_staging_count(self) -> int:
        return _role_count(self.lifetimes, "layout_staging")

    @property
    def transfer_staging_count(self) -> int:
        return _role_count(self.lifetimes, "transfer_target_staging")

    @property
    def reused_slot_count(self) -> int:
        return sum(slot.storage_count > 1 for slot in self.slots)

    @property
    def total_unreused_physical_bytes(self) -> int:
        return sum(lifetime.physical_bytes for lifetime in self.lifetimes)

    @property
    def total_reserved_physical_bytes(self) -> int:
        return sum(slot.bytes_reserved for slot in self.slots)

    @property
    def reuse_savings_bytes(self) -> int:
        return self.total_unreused_physical_bytes - self.total_reserved_physical_bytes

    @property
    def peak_live_physical_bytes(self) -> int:
        return max(
            sum(
                lifetime.physical_bytes
                for lifetime in self.lifetimes
                if lifetime.first_live_event <= event <= lifetime.last_use_event
            )
            for event in range(self.event_count)
        )

    @property
    def storage_metadata_digest(self) -> str:
        payload = {
            "domain_peaks": [
                _domain_peak_to_dict(peak) for peak in self.domain_peaks
            ],
            "lifetimes": [_lifetime_to_dict(item) for item in self.lifetimes],
            "slots": [_slot_to_dict(slot) for slot in self.slots],
            "source_layout_partition_plan_digest": (
                self.source_layout_partition_plan_digest
            ),
            "source_transfer_partition_plan_digest": (
                self.source_transfer_partition_plan_digest
            ),
        }
        return _metadata_digest(payload)


class RuntimeHeterogeneousStoragePlanError(AssertionError):
    """Raised when heterogeneous storage-plan evidence fails."""


def build_runtime_heterogeneous_storage_plan_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
) -> RuntimeHeterogeneousStoragePlanReport:
    """Build a bounded physical storage and staging plan without execution."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("heterogeneous storage graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("heterogeneous storage plan must be PartitionPlan")
    if graph.name != partition_plan.graph_name:
        raise ValueError("heterogeneous storage graph and plan names must match")

    buffer_lifetime = assert_runtime_buffer_lifetime(
        build_runtime_buffer_lifetime_report(graph, partition_plan)
    )
    transfer_evidence = assert_runtime_transfer_evidence(
        build_runtime_transfer_evidence_report(graph, partition_plan)
    )
    layout_evidence = assert_runtime_layout_conversion_evidence(
        build_runtime_layout_conversion_evidence_report(graph, partition_plan)
    )
    drafts = _build_storage_drafts(graph, partition_plan)
    lifetimes, slots = _assign_slots(drafts)
    event_count = len(graph.operations) * 4 + 1
    domain_peaks = _derive_domain_peaks(lifetimes, slots, event_count)
    issues = _derive_issues(lifetimes, slots)
    return RuntimeHeterogeneousStoragePlanReport(
        graph_name=graph.name,
        operation_count=len(graph.operations),
        event_count=event_count,
        planned_transfer_count=len(partition_plan.transfer_edges),
        planned_layout_conversion_count=len(partition_plan.layout_conversions),
        source_transfer_partition_plan_digest=(
            transfer_evidence.source_partition_plan_digest
        ),
        source_layout_partition_plan_digest=(
            layout_evidence.source_partition_plan_digest
        ),
        source_buffer_lifetime_digest=buffer_lifetime.lifetime_metadata_digest,
        source_transfer_evidence_digest=transfer_evidence.transfer_metadata_digest,
        source_layout_conversion_evidence_digest=(
            layout_evidence.conversion_metadata_digest
        ),
        lifetimes=lifetimes,
        slots=slots,
        domain_peaks=domain_peaks,
        issues=issues,
    )


def assert_runtime_heterogeneous_storage_plan(
    report: RuntimeHeterogeneousStoragePlanReport,
) -> RuntimeHeterogeneousStoragePlanReport:
    """Return the report or raise when heterogeneous planning failed."""

    if not isinstance(report, RuntimeHeterogeneousStoragePlanReport):
        raise TypeError("heterogeneous storage report must be report object")
    if report.issues:
        lines = [f"heterogeneous storage planning failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeHeterogeneousStoragePlanError("\n".join(lines))
    return report


def runtime_heterogeneous_storage_plan_report_to_dict(
    report: RuntimeHeterogeneousStoragePlanReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible storage-plan report."""

    if not isinstance(report, RuntimeHeterogeneousStoragePlanReport):
        raise TypeError("heterogeneous storage report must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "domain_peaks": [_domain_peak_to_dict(peak) for peak in report.domain_peaks],
        "event_count": report.event_count,
        "event_phases": list(RUNTIME_HETEROGENEOUS_STORAGE_EVENT_PHASES),
        "execution_policy": report.execution_policy,
        "external_artifacts": report.external_artifacts,
        "graph_name": report.graph_name,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "layout_sizing_policy": report.layout_sizing_policy,
        "layout_staging_count": report.layout_staging_count,
        "lifetimes": [_lifetime_to_dict(item) for item in report.lifetimes],
        "operation_count": report.operation_count,
        "passed": report.passed,
        "peak_live_physical_bytes": report.peak_live_physical_bytes,
        "performance_claim": report.performance_claim,
        "planned_layout_conversion_count": report.planned_layout_conversion_count,
        "planned_transfer_count": report.planned_transfer_count,
        "produced_storage_count": report.produced_storage_count,
        "raw_value_policy": report.raw_value_policy,
        "residency_claim": report.residency_claim,
        "reuse_policy": report.reuse_policy,
        "reuse_savings_bytes": report.reuse_savings_bytes,
        "reused_slot_count": report.reused_slot_count,
        "schema_version": RUNTIME_HETEROGENEOUS_STORAGE_PLAN_REPORT_SCHEMA_VERSION,
        "slot_count": len(report.slots),
        "slots": [_slot_to_dict(slot) for slot in report.slots],
        "source_buffer_lifetime_digest": report.source_buffer_lifetime_digest,
        "source_layout_conversion_evidence_digest": (
            report.source_layout_conversion_evidence_digest
        ),
        "source_layout_partition_plan_digest": (
            report.source_layout_partition_plan_digest
        ),
        "source_transfer_partition_plan_digest": (
            report.source_transfer_partition_plan_digest
        ),
        "source_transfer_evidence_digest": report.source_transfer_evidence_digest,
        "storage_contract": report.storage_contract,
        "storage_lifetime_count": len(report.lifetimes),
        "storage_metadata_digest": report.storage_metadata_digest,
        "storage_scope": report.storage_scope,
        "total_reserved_physical_bytes": report.total_reserved_physical_bytes,
        "total_unreused_physical_bytes": report.total_unreused_physical_bytes,
        "transfer_staging_count": report.transfer_staging_count,
    }


def dump_runtime_heterogeneous_storage_plan_report(
    report: RuntimeHeterogeneousStoragePlanReport,
) -> str:
    """Render stable metadata-only heterogeneous storage evidence."""

    text = json.dumps(
        runtime_heterogeneous_storage_plan_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_REPORT_BYTES:
        raise ValueError("heterogeneous storage report exceeds byte limit")
    return text + "\n"


def _build_storage_drafts(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
) -> tuple[_StorageDraft, ...]:
    operation_indices = {
        operation.name: index for index, operation in enumerate(graph.operations)
    }
    assignments = _assignments(graph, partition_plan)
    tensors, producers = _produced_tensors(graph)
    conversions = _conversion_by_edge(partition_plan.layout_conversions)
    transfers = _transfer_by_edge(partition_plan.transfer_edges)
    _validate_movement_relationships(
        graph=graph,
        assignments=assignments,
        tensors=tensors,
        producers=producers,
        conversions=conversions,
        transfers=transfers,
    )

    drafts: list[_StorageDraft] = []
    for tensor_name, tensor in tensors.items():
        producer = producers[tensor_name]
        producer_index = operation_indices[producer]
        use_events: list[tuple[int, str, str]] = []
        for operation in graph.operations:
            if tensor_name not in {item.name for item in operation.inputs}:
                continue
            key = (tensor_name, producer, operation.name)
            target_index = operation_indices[operation.name]
            if key in conversions:
                use_events.append(
                    (
                        _event_index(target_index, "layout_conversion"),
                        "layout_conversion",
                        operation.name,
                    )
                )
            elif key in transfers:
                use_events.append(
                    (_event_index(target_index, "transfer"), "transfer", operation.name)
                )
            else:
                use_events.append(
                    (
                        _event_index(target_index, "consumer_execution"),
                        "consumer_execution",
                        operation.name,
                    )
                )
        if use_events:
            last_use_event, last_use_phase, target_operation = max(
                use_events,
                key=lambda item: item[0],
            )
        else:
            last_use_event = len(graph.operations) * 4
            last_use_phase = "graph_end"
            target_operation = "graph_output"
        assignment = assignments[producer]
        drafts.append(
            _storage_draft(
                storage_id=f"storage.value.{tensor_name}",
                tensor=tensor,
                storage_role="produced_value",
                source_operation=producer,
                target_operation=target_operation,
                first_live_event=_event_index(producer_index, "output_produced"),
                first_live_phase="output_produced",
                last_use_event=last_use_event,
                last_use_phase=last_use_phase,
                memory_domain=assignment.memory_domain,
                layout=assignment.produced_layout,
            )
        )

    for key, conversion in sorted(conversions.items()):
        tensor_name, source_operation, target_operation = key
        tensor = tensors[tensor_name]
        target_index = operation_indices[target_operation]
        transfer = transfers.get(key)
        memory_domain = (
            transfer.source_domain
            if transfer is not None
            else assignments[source_operation].memory_domain
        )
        last_use_phase = "transfer" if transfer is not None else "consumer_execution"
        drafts.append(
            _storage_draft(
                storage_id=f"storage.layout.{tensor_name}.{target_operation}",
                tensor=tensor,
                storage_role="layout_staging",
                source_operation=source_operation,
                target_operation=target_operation,
                first_live_event=_event_index(target_index, "layout_conversion"),
                first_live_phase="layout_conversion",
                last_use_event=_event_index(target_index, last_use_phase),
                last_use_phase=last_use_phase,
                memory_domain=memory_domain,
                layout=conversion.target_layout,
            )
        )

    for key, transfer in sorted(transfers.items()):
        tensor_name, source_operation, target_operation = key
        tensor = tensors[tensor_name]
        target_index = operation_indices[target_operation]
        drafts.append(
            _storage_draft(
                storage_id=f"storage.transfer.{tensor_name}.{target_operation}",
                tensor=tensor,
                storage_role="transfer_target_staging",
                source_operation=source_operation,
                target_operation=target_operation,
                first_live_event=_event_index(target_index, "transfer"),
                first_live_phase="transfer",
                last_use_event=_event_index(target_index, "consumer_execution"),
                last_use_phase="consumer_execution",
                memory_domain=transfer.target_domain,
                layout=transfer.target_layout,
            )
        )

    if len(drafts) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES:
        raise ValueError("heterogeneous storage draft count exceeds limit")
    return tuple(drafts)


def _assign_slots(
    drafts: tuple[_StorageDraft, ...],
) -> tuple[
    tuple[RuntimeHeterogeneousStorageLifetime, ...],
    tuple[RuntimeHeterogeneousStorageSlot, ...],
]:
    states: list[_SlotState] = []
    state_by_storage: dict[str, _SlotState] = {}
    for draft in sorted(
        drafts,
        key=lambda item: (item.first_live_event, item.last_use_event, item.storage_id),
    ):
        state = next(
            (
                candidate
                for candidate in states
                if candidate.key == draft.slot_key
                and candidate.last_use_event < draft.first_live_event
            ),
            None,
        )
        if state is None:
            state = _SlotState(
                slot_id=f"storage_slot_{len(states) + 1:03d}",
                key=draft.slot_key,
            )
            states.append(state)
        state.drafts.append(draft)
        state.last_use_event = draft.last_use_event
        state_by_storage[draft.storage_id] = state

    lifetimes = tuple(
        _lifetime_from_draft(draft, state_by_storage[draft.storage_id])
        for draft in sorted(
            drafts,
            key=lambda item: (item.first_live_event, item.storage_role, item.storage_id),
        )
    )
    slots = tuple(_slot_from_state(state) for state in states)
    return lifetimes, slots


def _storage_draft(
    *,
    storage_id: str,
    tensor: TensorRef,
    storage_role: str,
    source_operation: str,
    target_operation: str,
    first_live_event: int,
    first_live_phase: str,
    last_use_event: int,
    last_use_phase: str,
    memory_domain: MemoryDomainKind,
    layout: LayoutKind,
) -> _StorageDraft:
    physical_shape, tile_shape = _physical_shape(tensor.shape, layout)
    logical_elements = prod(tensor.shape)
    physical_elements = prod(physical_shape)
    if physical_elements > MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS:
        raise ValueError("heterogeneous storage physical element limit exceeded")
    dtype_bytes = dtype_size_bytes(tensor.dtype)
    return _StorageDraft(
        storage_id=storage_id,
        tensor_name=tensor.name,
        storage_role=storage_role,
        source_operation=source_operation,
        target_operation=target_operation,
        first_live_event=first_live_event,
        first_live_phase=first_live_phase,
        last_use_event=last_use_event,
        last_use_phase=last_use_phase,
        memory_domain=memory_domain,
        layout=layout,
        dtype=tensor.dtype,
        logical_shape=tensor.shape,
        physical_shape=physical_shape,
        tile_shape=tile_shape,
        logical_element_count=logical_elements,
        physical_element_count=physical_elements,
        padding_element_count=physical_elements - logical_elements,
        logical_bytes=logical_elements * dtype_bytes,
        physical_bytes=physical_elements * dtype_bytes,
    )


def _lifetime_from_draft(
    draft: _StorageDraft,
    state: _SlotState,
) -> RuntimeHeterogeneousStorageLifetime:
    return RuntimeHeterogeneousStorageLifetime(
        **draft._asdict(),
        slot_id=state.slot_id,
        reusable=len(state.drafts) > 1,
    )


def _slot_from_state(state: _SlotState) -> RuntimeHeterogeneousStorageSlot:
    first = state.drafts[0]
    storage_ids = tuple(draft.storage_id for draft in state.drafts)
    total_storage_bytes = first.physical_bytes * len(storage_ids)
    return RuntimeHeterogeneousStorageSlot(
        slot_id=state.slot_id,
        storage_role=first.storage_role,
        memory_domain=first.memory_domain,
        layout=first.layout,
        dtype=first.dtype,
        physical_shape=first.physical_shape,
        tile_shape=first.tile_shape,
        bytes_reserved=first.physical_bytes,
        storage_ids=storage_ids,
        total_storage_bytes=total_storage_bytes,
        reuse_savings_bytes=total_storage_bytes - first.physical_bytes,
        non_overlapping=_lifetimes_non_overlapping(state.drafts),
    )


def _derive_domain_peaks(
    lifetimes: tuple[RuntimeHeterogeneousStorageLifetime, ...],
    slots: tuple[RuntimeHeterogeneousStorageSlot, ...],
    event_count: int,
) -> tuple[RuntimeHeterogeneousStorageDomainPeak, ...]:
    domains = sorted({item.memory_domain for item in lifetimes}, key=lambda item: item.value)
    peaks: list[RuntimeHeterogeneousStorageDomainPeak] = []
    for domain in domains:
        peak = max(
            sum(
                lifetime.physical_bytes
                for lifetime in lifetimes
                if lifetime.memory_domain is domain
                and lifetime.first_live_event <= event <= lifetime.last_use_event
            )
            for event in range(event_count)
        )
        reserved = sum(
            slot.bytes_reserved for slot in slots if slot.memory_domain is domain
        )
        peaks.append(
            RuntimeHeterogeneousStorageDomainPeak(
                memory_domain=domain,
                peak_live_physical_bytes=peak,
                reserved_slot_bytes=reserved,
            )
        )
    return tuple(peaks)


def _derive_issues(
    lifetimes: tuple[RuntimeHeterogeneousStorageLifetime, ...],
    slots: tuple[RuntimeHeterogeneousStorageSlot, ...],
) -> tuple[RuntimeHeterogeneousStorageIssue, ...]:
    issues: list[RuntimeHeterogeneousStorageIssue] = []
    slot_by_id = {slot.slot_id: slot for slot in slots}
    if len(slot_by_id) != len(slots):
        issues.append(RuntimeHeterogeneousStorageIssue("slots", "duplicate_slot_id"))
    lifetime_by_storage = {item.storage_id: item for item in lifetimes}
    if len(lifetime_by_storage) != len(lifetimes):
        issues.append(
            RuntimeHeterogeneousStorageIssue("lifetimes", "duplicate_storage_id")
        )
    for lifetime in lifetimes:
        slot = slot_by_id.get(lifetime.slot_id)
        if slot is None:
            issues.append(
                RuntimeHeterogeneousStorageIssue(
                    lifetime.storage_id,
                    "slot_missing",
                )
            )
            continue
        if _lifetime_slot_key(lifetime) != _slot_key(slot):
            issues.append(
                RuntimeHeterogeneousStorageIssue(
                    lifetime.storage_id,
                    "slot_storage_contract_mismatch",
                )
            )
        if lifetime.storage_id not in slot.storage_ids:
            issues.append(
                RuntimeHeterogeneousStorageIssue(
                    lifetime.storage_id,
                    "slot_membership_missing",
                )
            )
        if lifetime.reusable != (slot.storage_count > 1):
            issues.append(
                RuntimeHeterogeneousStorageIssue(
                    lifetime.storage_id,
                    "reuse_flag_mismatch",
                )
            )
    for slot in slots:
        members = tuple(
            lifetime_by_storage[storage_id]
            for storage_id in slot.storage_ids
            if storage_id in lifetime_by_storage
        )
        if len(members) != len(slot.storage_ids):
            issues.append(
                RuntimeHeterogeneousStorageIssue(slot.slot_id, "slot_member_missing")
            )
        elif not _runtime_lifetimes_non_overlapping(members):
            issues.append(
                RuntimeHeterogeneousStorageIssue(slot.slot_id, "slot_lifetimes_overlap")
            )
        if not slot.non_overlapping:
            issues.append(
                RuntimeHeterogeneousStorageIssue(slot.slot_id, "slot_overlap_flag_failed")
            )
    all_slot_members = tuple(
        storage_id for slot in slots for storage_id in slot.storage_ids
    )
    if len(set(all_slot_members)) != len(all_slot_members):
        issues.append(
            RuntimeHeterogeneousStorageIssue("slots", "duplicate_slot_membership")
        )
    return tuple(issues[:MAX_RUNTIME_HETEROGENEOUS_STORAGE_ISSUES])


def _assignments(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
) -> dict[str, Assignment]:
    operation_names = graph.operation_names()
    assignment_names = tuple(item.operation_name for item in partition_plan.assignments)
    if assignment_names != operation_names:
        raise ValueError("heterogeneous storage assignments must match graph order")
    return {item.operation_name: item for item in partition_plan.assignments}


def _produced_tensors(
    graph: ComputeGraph,
) -> tuple[dict[str, TensorRef], dict[str, str]]:
    tensors: dict[str, TensorRef] = {}
    producers: dict[str, str] = {}
    for operation in graph.operations:
        for tensor in operation.outputs:
            if tensor.name in tensors:
                raise ValueError("heterogeneous storage tensor producer is not unique")
            tensors[tensor.name] = tensor
            producers[tensor.name] = operation.name
    return tensors, producers


def _conversion_by_edge(
    conversions: tuple[LayoutConversionCost, ...],
) -> dict[tuple[str, str, str], LayoutConversionCost]:
    result: dict[tuple[str, str, str], LayoutConversionCost] = {}
    for conversion in conversions:
        if conversion.source_operation is None:
            raise ValueError("heterogeneous storage conversion source is required")
        key = (
            conversion.tensor_name,
            conversion.source_operation,
            conversion.target_operation,
        )
        if key in result:
            raise ValueError("heterogeneous storage conversion edge is duplicated")
        result[key] = conversion
    return result


def _transfer_by_edge(
    transfers: tuple[RuntimeTransferEdge, ...],
) -> dict[tuple[str, str, str], RuntimeTransferEdge]:
    result: dict[tuple[str, str, str], RuntimeTransferEdge] = {}
    for transfer in transfers:
        key = (
            transfer.tensor_name,
            transfer.source_operation,
            transfer.target_operation,
        )
        if key in result:
            raise ValueError("heterogeneous storage transfer edge is duplicated")
        result[key] = transfer
    return result


def _validate_movement_relationships(
    *,
    graph: ComputeGraph,
    assignments: dict[str, Assignment],
    tensors: dict[str, TensorRef],
    producers: dict[str, str],
    conversions: dict[tuple[str, str, str], LayoutConversionCost],
    transfers: dict[tuple[str, str, str], RuntimeTransferEdge],
) -> None:
    operation_indices = {
        operation.name: index for index, operation in enumerate(graph.operations)
    }
    operations = {operation.name: operation for operation in graph.operations}
    for key in sorted(set(conversions) | set(transfers)):
        tensor_name, source_operation, target_operation = key
        tensor = tensors.get(tensor_name)
        if tensor is None or producers.get(tensor_name) != source_operation:
            raise ValueError("heterogeneous storage movement producer mismatch")
        target = operations.get(target_operation)
        if target is None or tensor_name not in {item.name for item in target.inputs}:
            raise ValueError("heterogeneous storage movement consumer mismatch")
        if operation_indices[source_operation] >= operation_indices[target_operation]:
            raise ValueError("heterogeneous storage movement order is invalid")
        logical_bytes = prod(tensor.shape) * dtype_size_bytes(tensor.dtype)
        conversion = conversions.get(key)
        transfer = transfers.get(key)
        source_assignment = assignments[source_operation]
        target_assignment = assignments[target_operation]
        if conversion is not None:
            if conversion.source_layout is not source_assignment.produced_layout:
                raise ValueError("heterogeneous storage conversion source layout mismatch")
            if conversion.bytes_converted != logical_bytes:
                raise ValueError("heterogeneous storage conversion byte count mismatch")
        if transfer is not None:
            if (
                transfer.source_backend != source_assignment.backend_name
                or transfer.target_backend != target_assignment.backend_name
            ):
                raise ValueError("heterogeneous storage transfer backend mismatch")
            if (
                transfer.source_domain is not source_assignment.memory_domain
                or transfer.target_domain is not target_assignment.memory_domain
            ):
                raise ValueError("heterogeneous storage transfer domain mismatch")
            if transfer.source_layout is not source_assignment.produced_layout:
                raise ValueError("heterogeneous storage transfer source layout mismatch")
            if transfer.bytes_moved != logical_bytes:
                raise ValueError("heterogeneous storage transfer byte count mismatch")
            if conversion is None and transfer.source_layout is not transfer.target_layout:
                raise ValueError("heterogeneous storage transfer conversion is missing")
        if (
            conversion is not None
            and transfer is not None
            and (
                conversion.source_layout is not transfer.source_layout
                or conversion.target_layout is not transfer.target_layout
            )
        ):
            raise ValueError("heterogeneous storage movement layout chain mismatch")


def _event_index(operation_index: int, phase: str) -> int:
    offsets = {
        "layout_conversion": 0,
        "transfer": 1,
        "consumer_execution": 2,
        "output_produced": 3,
    }
    try:
        return operation_index * 4 + offsets[phase]
    except KeyError as exc:
        raise ValueError("heterogeneous storage event phase is unsupported") from exc


def _physical_shape(
    logical_shape: tuple[int, ...],
    layout: LayoutKind,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    _validate_shape(logical_shape, "logical_shape")
    if layout is LayoutKind.ROW_MAJOR:
        return logical_shape, ()
    if layout is LayoutKind.BLOCKED:
        if len(logical_shape) != 2:
            raise ValueError("blocked heterogeneous storage requires rank-2 tensor")
        rows, columns = logical_shape
        return (
            (rows + 1) // 2,
            (columns + 1) // 2,
            *RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE,
        ), RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE
    raise ValueError("heterogeneous storage layout is unsupported")


def _validate_layout_shape(
    *,
    layout: LayoutKind,
    logical_shape: tuple[int, ...],
    physical_shape: tuple[int, ...],
    tile_shape: tuple[int, ...],
) -> None:
    expected_physical, expected_tile = _physical_shape(logical_shape, layout)
    if physical_shape != expected_physical or tile_shape != expected_tile:
        raise ValueError("heterogeneous storage layout shape mismatch")


def _validate_role_phases(lifetime: RuntimeHeterogeneousStorageLifetime) -> None:
    allowed = {
        "produced_value": (
            "output_produced",
            {"layout_conversion", "transfer", "consumer_execution", "graph_end"},
        ),
        "layout_staging": (
            "layout_conversion",
            {"transfer", "consumer_execution"},
        ),
        "transfer_target_staging": (
            "transfer",
            {"consumer_execution"},
        ),
    }
    first_phase, last_phases = allowed[lifetime.storage_role]
    if lifetime.first_live_phase != first_phase or lifetime.last_use_phase not in last_phases:
        raise ValueError("heterogeneous storage role phase mismatch")


def _lifetimes_non_overlapping(drafts: list[_StorageDraft]) -> bool:
    ordered = sorted(drafts, key=lambda item: item.first_live_event)
    return all(
        previous.last_use_event < current.first_live_event
        for previous, current in zip(ordered, ordered[1:], strict=False)
    )


def _runtime_lifetimes_non_overlapping(
    lifetimes: tuple[RuntimeHeterogeneousStorageLifetime, ...],
) -> bool:
    ordered = sorted(lifetimes, key=lambda item: item.first_live_event)
    return all(
        previous.last_use_event < current.first_live_event
        for previous, current in zip(ordered, ordered[1:], strict=False)
    )


def _lifetime_slot_key(lifetime: RuntimeHeterogeneousStorageLifetime) -> tuple[object, ...]:
    return (
        lifetime.storage_role,
        lifetime.memory_domain,
        lifetime.layout,
        lifetime.dtype,
        lifetime.physical_shape,
        lifetime.tile_shape,
        lifetime.physical_bytes,
    )


def _slot_key(slot: RuntimeHeterogeneousStorageSlot) -> tuple[object, ...]:
    return (
        slot.storage_role,
        slot.memory_domain,
        slot.layout,
        slot.dtype,
        slot.physical_shape,
        slot.tile_shape,
        slot.bytes_reserved,
    )


def _role_count(
    lifetimes: tuple[RuntimeHeterogeneousStorageLifetime, ...],
    role: str,
) -> int:
    return sum(item.storage_role == role for item in lifetimes)


def _lifetime_to_dict(
    lifetime: RuntimeHeterogeneousStorageLifetime,
) -> dict[str, object]:
    return {
        "dtype": lifetime.dtype,
        "first_live_event": lifetime.first_live_event,
        "first_live_phase": lifetime.first_live_phase,
        "last_use_event": lifetime.last_use_event,
        "last_use_phase": lifetime.last_use_phase,
        "layout": lifetime.layout.value,
        "logical_bytes": lifetime.logical_bytes,
        "logical_element_count": lifetime.logical_element_count,
        "logical_shape": list(lifetime.logical_shape),
        "memory_domain": lifetime.memory_domain.value,
        "padding_element_count": lifetime.padding_element_count,
        "physical_bytes": lifetime.physical_bytes,
        "physical_element_count": lifetime.physical_element_count,
        "physical_shape": list(lifetime.physical_shape),
        "reusable": lifetime.reusable,
        "slot_id": lifetime.slot_id,
        "source_operation": lifetime.source_operation,
        "storage_id": lifetime.storage_id,
        "storage_role": lifetime.storage_role,
        "target_operation": lifetime.target_operation,
        "tensor_name": lifetime.tensor_name,
        "tile_shape": list(lifetime.tile_shape),
    }


def _slot_to_dict(slot: RuntimeHeterogeneousStorageSlot) -> dict[str, object]:
    return {
        "bytes_reserved": slot.bytes_reserved,
        "dtype": slot.dtype,
        "layout": slot.layout.value,
        "memory_domain": slot.memory_domain.value,
        "non_overlapping": slot.non_overlapping,
        "physical_shape": list(slot.physical_shape),
        "reuse_savings_bytes": slot.reuse_savings_bytes,
        "slot_id": slot.slot_id,
        "storage_count": slot.storage_count,
        "storage_ids": list(slot.storage_ids),
        "storage_role": slot.storage_role,
        "tile_shape": list(slot.tile_shape),
        "total_storage_bytes": slot.total_storage_bytes,
    }


def _domain_peak_to_dict(
    peak: RuntimeHeterogeneousStorageDomainPeak,
) -> dict[str, object]:
    return {
        "memory_domain": peak.memory_domain.value,
        "peak_live_physical_bytes": peak.peak_live_physical_bytes,
        "reserved_slot_bytes": peak.reserved_slot_bytes,
    }


def _validate_contract(report: RuntimeHeterogeneousStoragePlanReport) -> None:
    expected = (
        (report.storage_contract, RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT),
        (report.storage_scope, RUNTIME_HETEROGENEOUS_STORAGE_PLAN_SCOPE),
        (report.execution_policy, RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_POLICY),
        (report.layout_sizing_policy, RUNTIME_HETEROGENEOUS_STORAGE_LAYOUT_POLICY),
        (report.reuse_policy, RUNTIME_HETEROGENEOUS_STORAGE_REUSE_POLICY),
        (report.residency_claim, RUNTIME_HETEROGENEOUS_STORAGE_RESIDENCY_CLAIM),
        (report.performance_claim, RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM),
        (report.raw_value_policy, RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS),
        (
            report.external_artifacts,
            RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS,
        ),
    )
    if any(actual != required for actual, required in expected):
        raise ValueError("heterogeneous storage contract mismatch")
    if (
        report.blocked_execution_surfaces
        != RUNTIME_HETEROGENEOUS_STORAGE_BLOCKED_EXECUTION_SURFACES
    ):
        raise ValueError("heterogeneous storage blocked surfaces changed")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if len(value.encode("utf-8")) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds byte limit")
    if not _NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must be a simple metadata name")
    if value.lower() in _FORBIDDEN_TEXT:
        raise ValueError(f"{label} uses a forbidden execution-surface name")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError(f"{label} must be canonical SHA-256")


def _validate_dtype(value: str) -> None:
    _validate_text(value, "dtype")
    dtype_size_bytes(value)


def _validate_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"{label} must be a non-empty tuple")
    for dimension in value:
        _require_positive_int(dimension, f"{label} dimension")


def _validate_tile_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple:
        raise TypeError("tile_shape must be a tuple")
    for dimension in value:
        _require_positive_int(dimension, "tile_shape dimension")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


class _StorageDraft(NamedTuple):
    storage_id: str
    tensor_name: str
    storage_role: str
    source_operation: str
    target_operation: str
    first_live_event: int
    first_live_phase: str
    last_use_event: int
    last_use_phase: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    dtype: str
    logical_shape: tuple[int, ...]
    physical_shape: tuple[int, ...]
    tile_shape: tuple[int, ...]
    logical_element_count: int
    physical_element_count: int
    padding_element_count: int
    logical_bytes: int
    physical_bytes: int

    @property
    def slot_key(self) -> tuple[object, ...]:
        return (
            self.storage_role,
            self.memory_domain,
            self.layout,
            self.dtype,
            self.physical_shape,
            self.tile_shape,
            self.physical_bytes,
        )


@dataclass
class _SlotState:
    slot_id: str
    key: tuple[object, ...]
    drafts: list[_StorageDraft] = field(default_factory=list)
    last_use_event: int = -1


__all__ = [
    "MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES",
    "MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS",
    "MAX_RUNTIME_HETEROGENEOUS_STORAGE_REPORT_BYTES",
    "MAX_RUNTIME_HETEROGENEOUS_STORAGE_RESERVED_BYTES",
    "MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS",
    "RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE",
    "RUNTIME_HETEROGENEOUS_STORAGE_BLOCKED_EXECUTION_SURFACES",
    "RUNTIME_HETEROGENEOUS_STORAGE_EVENT_PHASES",
    "RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_POLICY",
    "RUNTIME_HETEROGENEOUS_STORAGE_LAYOUT_POLICY",
    "RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT",
    "RUNTIME_HETEROGENEOUS_STORAGE_PLAN_REPORT_SCHEMA_VERSION",
    "RUNTIME_HETEROGENEOUS_STORAGE_PLAN_SCOPE",
    "RUNTIME_HETEROGENEOUS_STORAGE_REUSE_POLICY",
    "RuntimeHeterogeneousStorageDomainPeak",
    "RuntimeHeterogeneousStorageIssue",
    "RuntimeHeterogeneousStorageLifetime",
    "RuntimeHeterogeneousStoragePlanError",
    "RuntimeHeterogeneousStoragePlanReport",
    "RuntimeHeterogeneousStorageSlot",
    "assert_runtime_heterogeneous_storage_plan",
    "build_runtime_heterogeneous_storage_plan_report",
    "dump_runtime_heterogeneous_storage_plan_report",
    "runtime_heterogeneous_storage_plan_report_to_dict",
]
