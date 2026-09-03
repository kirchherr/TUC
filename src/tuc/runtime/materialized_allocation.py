"""Metadata-only evidence for trusted materialized runtime allocation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph
from tuc.runtime.allocation_executor import (
    MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS,
    MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES,
    MAX_RUNTIME_MATERIALIZED_ALLOCATION_FIELD_BYTES,
    MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS,
    RUNTIME_ALLOCATION_EXECUTION_MODE,
    RUNTIME_ALLOCATION_EXECUTION_STATUS,
    RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_ALLOCATION_EXECUTOR_CONTRACT,
    RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS,
    RUNTIME_ALLOCATION_HANDLE_POLICY,
    RUNTIME_ALLOCATION_INTERNAL_DTYPE,
    RUNTIME_ALLOCATION_PERFORMANCE_CLAIM,
    RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM,
    RUNTIME_ALLOCATION_PLANNED_DTYPE,
    RUNTIME_ALLOCATION_RETENTION_POLICY,
    RUNTIME_ALLOCATION_WRITE_MODE,
    RuntimeAllocationExecutionPrerequisites,
    RuntimeAllocationSlotMaterialization,
    RuntimeMaterializedAllocationExecution,
    assert_materializable_runtime_allocation,
)
from tuc.runtime.memory_budget import dump_runtime_memory_budget_report
from tuc.runtime.output_manifest import build_runtime_output_manifest_report
from tuc.runtime.partitioning import PartitionPlan
from tuc.runtime.reference_correctness import RuntimeReferenceCorrectnessReport
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_MATERIALIZED_ALLOCATION_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_materialized_allocation_report.v0"
)
RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT = (
    "runtime_allocation.materialized_trusted_simulator.v0"
)
RUNTIME_MATERIALIZED_ALLOCATION_ARTIFACT_STATUS = "review_evidence"
RUNTIME_MATERIALIZED_ALLOCATION_SCOPE = "trusted_host_ram_row_major_slots_only"
RUNTIME_MATERIALIZED_ALLOCATION_POLICY = "preallocate_write_release_reuse"
RUNTIME_MATERIALIZED_ALLOCATION_KERNEL_TEMPORARY_POLICY = (
    "excluded_from_allocator_memory_claim"
)
RUNTIME_MATERIALIZED_ALLOCATION_BUDGET_INTERPRETATION = (
    "planned_float32_budget_separate_from_float64_executor_storage"
)
RUNTIME_MATERIALIZED_ALLOCATION_NATIVE_CLAIM = "not_claimed"
RUNTIME_MATERIALIZED_ALLOCATION_STATUS = "passed"
MAX_RUNTIME_MATERIALIZED_ALLOCATION_REPORT_BYTES = 128 * 1024

_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeMaterializedAllocationRecord:
    """Closed metadata for one slot write and its lifetime-bound release."""

    operation_name: str
    operation_index: int
    tensor_name: str
    slot_id: str
    slot_generation: int
    previous_tensor_name: str | None
    first_live_index: int
    last_use_index: int
    release_index: int
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    shape: tuple[int, ...]
    planned_dtype: str
    runtime_dtype: str
    planned_bytes: int
    runtime_bytes: int
    reuse_status: str
    write_verification: str
    release_verification: str
    address_exposure: str
    status: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.operation_name, "operation_name"),
            (self.tensor_name, "tensor_name"),
            (self.slot_id, "slot_id"),
        ):
            _require_safe_text(value, label)
        _require_non_negative_int(self.operation_index, "operation_index")
        _require_positive_int(self.slot_generation, "slot_generation")
        if self.previous_tensor_name is not None:
            _require_safe_text(self.previous_tensor_name, "previous_tensor_name")
        _require_non_negative_int(self.first_live_index, "first_live_index")
        _require_non_negative_int(self.last_use_index, "last_use_index")
        _require_non_negative_int(self.release_index, "release_index")
        if self.operation_index != self.first_live_index:
            raise ValueError("materialized allocation record producer index mismatch")
        if self.release_index != self.last_use_index:
            raise ValueError("materialized allocation record release index mismatch")
        if self.memory_domain is not MemoryDomainKind.HOST_RAM:
            raise ValueError("materialized allocation record domain mismatch")
        if self.layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("materialized allocation record layout mismatch")
        _require_shape(self.shape)
        elements = _element_count(self.shape)
        if self.planned_dtype != RUNTIME_ALLOCATION_PLANNED_DTYPE:
            raise ValueError("materialized allocation record planned dtype mismatch")
        if self.runtime_dtype != RUNTIME_ALLOCATION_INTERNAL_DTYPE:
            raise ValueError("materialized allocation record runtime dtype mismatch")
        if self.planned_bytes != elements * 4 or self.runtime_bytes != elements * 8:
            raise ValueError("materialized allocation record byte count mismatch")
        if self.reuse_status not in {"first_slot_generation", "reused_after_release"}:
            raise ValueError("materialized allocation record reuse status mismatch")
        if self.slot_generation == 1:
            if self.reuse_status != "first_slot_generation":
                raise ValueError("first materialized allocation generation cannot reuse")
            if self.previous_tensor_name is not None:
                raise ValueError("first materialized allocation generation has predecessor")
        elif (
            self.reuse_status != "reused_after_release"
            or self.previous_tensor_name is None
        ):
            raise ValueError("reused materialized allocation lacks predecessor")
        if self.write_verification != "exact_kernel_result":
            raise ValueError("materialized allocation write verification mismatch")
        if self.release_verification != "released_at_proven_last_use":
            raise ValueError("materialized allocation release verification mismatch")
        if self.address_exposure != RUNTIME_ALLOCATION_HANDLE_POLICY:
            raise ValueError("materialized allocation record exposes an address")
        if self.status != RUNTIME_ALLOCATION_EXECUTION_STATUS:
            raise ValueError("materialized allocation record status mismatch")


@dataclass(frozen=True)
class RuntimeMaterializedAllocationReport:
    """Closed proof report for one bounded materialized allocator execution."""

    graph_name: str
    source_allocation_plan_digest: str
    source_memory_budget_digest: str
    source_request_manifest_digest: str
    source_admission_digest: str
    source_receipt_digest: str
    source_reconciliation_digest: str
    runtime_execution_trace_digest: str
    allocation_execution_trace_digest: str
    output_metadata_digest: str
    reference_correctness_digest: str
    operation_count: int
    retained_tensor_record_count: int
    terminal_output_count: int
    terminal_output_snapshot_bytes: int
    slots: tuple[RuntimeAllocationSlotMaterialization, ...]
    allocations: tuple[RuntimeMaterializedAllocationRecord, ...]
    evidence_contract: str = RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT
    artifact_status: str = RUNTIME_MATERIALIZED_ALLOCATION_ARTIFACT_STATUS
    materialization_scope: str = RUNTIME_MATERIALIZED_ALLOCATION_SCOPE
    materialization_policy: str = RUNTIME_MATERIALIZED_ALLOCATION_POLICY
    allocator_contract: str = RUNTIME_ALLOCATION_EXECUTOR_CONTRACT
    allocation_mode: str = RUNTIME_ALLOCATION_EXECUTION_MODE
    write_mode: str = RUNTIME_ALLOCATION_WRITE_MODE
    retention_policy: str = RUNTIME_ALLOCATION_RETENTION_POLICY
    kernel_temporary_policy: str = (
        RUNTIME_MATERIALIZED_ALLOCATION_KERNEL_TEMPORARY_POLICY
    )
    budget_interpretation: str = RUNTIME_MATERIALIZED_ALLOCATION_BUDGET_INTERPRETATION
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    handle_policy: str = RUNTIME_ALLOCATION_HANDLE_POLICY
    external_artifacts: str = RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS
    physical_memory_claim: str = RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM
    native_allocator_claim: str = RUNTIME_MATERIALIZED_ALLOCATION_NATIVE_CLAIM
    performance_claim: str = RUNTIME_ALLOCATION_PERFORMANCE_CLAIM
    reference_correctness_passed: bool = True
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_MATERIALIZED_ALLOCATION_STATUS

    def __post_init__(self) -> None:
        _require_safe_text(self.graph_name, "materialized allocation graph_name")
        for digest in (
            self.source_allocation_plan_digest,
            self.source_memory_budget_digest,
            self.source_request_manifest_digest,
            self.source_admission_digest,
            self.source_receipt_digest,
            self.source_reconciliation_digest,
            self.runtime_execution_trace_digest,
            self.allocation_execution_trace_digest,
            self.output_metadata_digest,
            self.reference_correctness_digest,
        ):
            _require_digest(digest)
        _require_positive_int(self.operation_count, "operation_count")
        _require_positive_int(
            self.retained_tensor_record_count,
            "retained_tensor_record_count",
        )
        _require_positive_int(self.terminal_output_count, "terminal_output_count")
        _require_positive_int(
            self.terminal_output_snapshot_bytes,
            "terminal_output_snapshot_bytes",
        )
        if type(self.slots) is not tuple or not self.slots:
            raise ValueError("materialized allocation report requires slots")
        if len(self.slots) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS:
            raise ValueError("materialized allocation report slot count exceeds limit")
        if not all(isinstance(slot, RuntimeAllocationSlotMaterialization) for slot in self.slots):
            raise TypeError("materialized allocation report slots must be records")
        if type(self.allocations) is not tuple or not self.allocations:
            raise ValueError("materialized allocation report requires allocation records")
        if len(self.allocations) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS:
            raise ValueError("materialized allocation report binding count exceeds limit")
        if not all(
            isinstance(record, RuntimeMaterializedAllocationRecord)
            for record in self.allocations
        ):
            raise TypeError("materialized allocation entries must be records")
        slot_ids = tuple(slot.slot_id for slot in self.slots)
        if len(set(slot_ids)) != len(slot_ids):
            raise ValueError("materialized allocation report contains duplicate slots")
        tensor_names = tuple(record.tensor_name for record in self.allocations)
        if len(set(tensor_names)) != len(tensor_names):
            raise ValueError("materialized allocation report contains duplicate tensors")
        if any(record.slot_id not in slot_ids for record in self.allocations):
            raise ValueError("materialized allocation record references unknown slot")
        if self.reuse_event_count == 0:
            raise ValueError("materialized allocation report requires executed reuse")
        if self.runtime_reserved_bytes > MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES:
            raise ValueError("materialized allocation report runtime bytes exceed limit")
        if self.runtime_reuse_savings_bytes <= 0:
            raise ValueError("materialized allocation report requires positive reuse savings")
        expected = (
            (self.evidence_contract, RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT),
            (self.artifact_status, RUNTIME_MATERIALIZED_ALLOCATION_ARTIFACT_STATUS),
            (self.materialization_scope, RUNTIME_MATERIALIZED_ALLOCATION_SCOPE),
            (self.materialization_policy, RUNTIME_MATERIALIZED_ALLOCATION_POLICY),
            (self.allocator_contract, RUNTIME_ALLOCATION_EXECUTOR_CONTRACT),
            (self.allocation_mode, RUNTIME_ALLOCATION_EXECUTION_MODE),
            (self.write_mode, RUNTIME_ALLOCATION_WRITE_MODE),
            (self.retention_policy, RUNTIME_ALLOCATION_RETENTION_POLICY),
            (
                self.kernel_temporary_policy,
                RUNTIME_MATERIALIZED_ALLOCATION_KERNEL_TEMPORARY_POLICY,
            ),
            (
                self.budget_interpretation,
                RUNTIME_MATERIALIZED_ALLOCATION_BUDGET_INTERPRETATION,
            ),
            (self.raw_value_policy, RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS),
            (self.handle_policy, RUNTIME_ALLOCATION_HANDLE_POLICY),
            (self.external_artifacts, RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS),
            (self.physical_memory_claim, RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM),
            (self.native_allocator_claim, RUNTIME_MATERIALIZED_ALLOCATION_NATIVE_CLAIM),
            (self.performance_claim, RUNTIME_ALLOCATION_PERFORMANCE_CLAIM),
            (self.status, RUNTIME_MATERIALIZED_ALLOCATION_STATUS),
        )
        if any(observed != required for observed, required in expected):
            raise ValueError("materialized allocation report contract mismatch")
        if self.reference_correctness_passed is not True:
            raise ValueError("materialized allocation requires reference correctness PASS")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("materialized allocation report security boundary changed")

    @property
    def slot_count(self) -> int:
        return len(self.slots)

    @property
    def reused_slot_count(self) -> int:
        return sum(slot.allocation_kind == "reused" for slot in self.slots)

    @property
    def allocation_count(self) -> int:
        return len(self.allocations)

    @property
    def reuse_event_count(self) -> int:
        return sum(
            record.reuse_status == "reused_after_release"
            for record in self.allocations
        )

    @property
    def release_count(self) -> int:
        return len(self.allocations)

    @property
    def planned_reserved_bytes(self) -> int:
        return sum(slot.planned_bytes for slot in self.slots)

    @property
    def runtime_reserved_bytes(self) -> int:
        return sum(slot.runtime_bytes for slot in self.slots)

    @property
    def runtime_unreused_tensor_bytes(self) -> int:
        return sum(record.runtime_bytes for record in self.allocations)

    @property
    def runtime_reuse_savings_bytes(self) -> int:
        return self.runtime_unreused_tensor_bytes - self.runtime_reserved_bytes

    @property
    def report_metadata_digest(self) -> str:
        return _digest(
            json.dumps(
                runtime_materialized_allocation_report_to_dict(self),
                sort_keys=True,
                separators=(",", ":"),
            )
        )


def build_runtime_materialized_allocation_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    prerequisites: RuntimeAllocationExecutionPrerequisites,
    materialized: RuntimeMaterializedAllocationExecution,
    correctness: RuntimeReferenceCorrectnessReport,
) -> RuntimeMaterializedAllocationReport:
    """Bind executed slot reuse to canonical planning and correctness evidence."""

    if not isinstance(materialized, RuntimeMaterializedAllocationExecution):
        raise TypeError("materialized allocation execution must be execution object")
    if not isinstance(correctness, RuntimeReferenceCorrectnessReport):
        raise TypeError("materialized allocation correctness must be report")
    assert_materializable_runtime_allocation(graph, partition_plan, prerequisites)
    execution = materialized.execution
    trace = materialized.allocation_trace
    if (
        execution.trace.graph_name != graph.name
        or trace.graph_name != graph.name
        or correctness.graph_name != graph.name
    ):
        raise ValueError("materialized allocation graph linkage mismatch")
    if not correctness.passed:
        raise ValueError("materialized allocation requires passing correctness")
    output_manifest = build_runtime_output_manifest_report(graph, execution)
    if not output_manifest.passed:
        raise ValueError("materialized allocation output manifest must pass")
    if len(execution.trace.steps) != len(graph.operations):
        raise ValueError("materialized allocation operation trace count mismatch")

    expected_digests = _source_digests(prerequisites)
    observed_digests = (
        trace.source_allocation_plan_digest,
        trace.source_memory_budget_digest,
        trace.source_request_manifest_digest,
        trace.source_admission_digest,
        trace.source_receipt_digest,
        trace.source_reconciliation_digest,
    )
    if observed_digests != expected_digests:
        raise ValueError("materialized allocation source digest linkage mismatch")
    if tuple(trace.slots) != tuple(
        _expected_slot(slot) for slot in prerequisites.allocation_plan.slots
    ):
        raise ValueError("materialized allocation slot trace does not match plan")
    releases = {
        (release.tensor_name, release.slot_id, release.slot_generation): release
        for release in trace.releases
    }
    records = tuple(
        RuntimeMaterializedAllocationRecord(
            operation_name=write.operation_name,
            operation_index=write.operation_index,
            tensor_name=write.tensor_name,
            slot_id=write.slot_id,
            slot_generation=write.slot_generation,
            previous_tensor_name=write.previous_tensor_name,
            first_live_index=write.first_live_index,
            last_use_index=write.last_use_index,
            release_index=releases[
                (write.tensor_name, write.slot_id, write.slot_generation)
            ].release_index,
            memory_domain=write.memory_domain,
            layout=write.layout,
            shape=write.shape,
            planned_dtype=write.planned_dtype,
            runtime_dtype=write.runtime_dtype,
            planned_bytes=write.planned_bytes,
            runtime_bytes=write.runtime_bytes,
            reuse_status=write.reuse_status,
            write_verification=write.semantic_verification,
            release_verification="released_at_proven_last_use",
            address_exposure=write.address_exposure,
            status=write.status,
        )
        for write in trace.writes
    )
    expected_bindings = tuple(
        (
            binding.producer_operation,
            binding.producer_index,
            binding.tensor_name,
            binding.slot_id,
            binding.first_live_index,
            binding.last_use_index,
            binding.memory_domain,
            binding.layout,
            binding.shape,
            binding.dtype,
            binding.bytes_required,
        )
        for binding in prerequisites.allocation_plan.bindings
    )
    observed_bindings = tuple(
        (
            record.operation_name,
            record.operation_index,
            record.tensor_name,
            record.slot_id,
            record.first_live_index,
            record.last_use_index,
            record.memory_domain,
            record.layout,
            record.shape,
            record.planned_dtype,
            record.planned_bytes,
        )
        for record in records
    )
    if observed_bindings != expected_bindings:
        raise ValueError("materialized allocation execution does not match bindings")
    terminal_snapshot_bytes = sum(
        int(execution.output_for(output.tensor_name).nbytes)
        for output in output_manifest.expected_outputs
    )
    return RuntimeMaterializedAllocationReport(
        graph_name=graph.name,
        source_allocation_plan_digest=expected_digests[0],
        source_memory_budget_digest=expected_digests[1],
        source_request_manifest_digest=expected_digests[2],
        source_admission_digest=expected_digests[3],
        source_receipt_digest=expected_digests[4],
        source_reconciliation_digest=expected_digests[5],
        runtime_execution_trace_digest=_digest(execution.trace.dump()),
        allocation_execution_trace_digest=trace.metadata_digest,
        output_metadata_digest=output_manifest.output_metadata_digest,
        reference_correctness_digest=correctness.comparison_metadata_digest,
        operation_count=len(graph.operations),
        retained_tensor_record_count=len(execution.records),
        terminal_output_count=len(output_manifest.outputs),
        terminal_output_snapshot_bytes=terminal_snapshot_bytes,
        slots=trace.slots,
        allocations=records,
    )


def runtime_materialized_allocation_report_to_dict(
    report: RuntimeMaterializedAllocationReport,
) -> dict[str, object]:
    """Return deterministic metadata-only materialized allocation evidence."""

    if not isinstance(report, RuntimeMaterializedAllocationReport):
        raise TypeError("materialized allocation report must be report object")
    return {
        "allocation_count": report.allocation_count,
        "allocation_execution_trace_digest": (
            report.allocation_execution_trace_digest
        ),
        "allocation_mode": report.allocation_mode,
        "allocations": [_allocation_to_dict(record) for record in report.allocations],
        "allocator_contract": report.allocator_contract,
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "budget_interpretation": report.budget_interpretation,
        "evidence_contract": report.evidence_contract,
        "external_artifacts": report.external_artifacts,
        "graph_name": report.graph_name,
        "handle_policy": report.handle_policy,
        "kernel_temporary_policy": report.kernel_temporary_policy,
        "materialization_policy": report.materialization_policy,
        "materialization_scope": report.materialization_scope,
        "native_allocator_claim": report.native_allocator_claim,
        "operation_count": report.operation_count,
        "output_metadata_digest": report.output_metadata_digest,
        "performance_claim": report.performance_claim,
        "physical_memory_claim": report.physical_memory_claim,
        "planned_reserved_bytes": report.planned_reserved_bytes,
        "raw_value_policy": report.raw_value_policy,
        "reference_correctness_digest": report.reference_correctness_digest,
        "reference_correctness_passed": report.reference_correctness_passed,
        "release_count": report.release_count,
        "retained_tensor_record_count": report.retained_tensor_record_count,
        "retention_policy": report.retention_policy,
        "reuse_event_count": report.reuse_event_count,
        "reused_slot_count": report.reused_slot_count,
        "runtime_execution_trace_digest": report.runtime_execution_trace_digest,
        "runtime_reserved_bytes": report.runtime_reserved_bytes,
        "runtime_reuse_savings_bytes": report.runtime_reuse_savings_bytes,
        "runtime_unreused_tensor_bytes": report.runtime_unreused_tensor_bytes,
        "schema_version": RUNTIME_MATERIALIZED_ALLOCATION_REPORT_SCHEMA_VERSION,
        "slot_count": report.slot_count,
        "slots": [_slot_to_dict(slot) for slot in report.slots],
        "source_admission_digest": report.source_admission_digest,
        "source_allocation_plan_digest": report.source_allocation_plan_digest,
        "source_memory_budget_digest": report.source_memory_budget_digest,
        "source_receipt_digest": report.source_receipt_digest,
        "source_reconciliation_digest": report.source_reconciliation_digest,
        "source_request_manifest_digest": report.source_request_manifest_digest,
        "status": report.status,
        "terminal_output_count": report.terminal_output_count,
        "terminal_output_snapshot_bytes": report.terminal_output_snapshot_bytes,
        "write_mode": report.write_mode,
    }


def dump_runtime_materialized_allocation_report(
    report: RuntimeMaterializedAllocationReport,
) -> str:
    """Render stable JSON without values, addresses, pointers, or handles."""

    text = json.dumps(
        runtime_materialized_allocation_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_REPORT_BYTES:
        raise ValueError("materialized allocation report exceeds byte limit")
    return text + "\n"


def _source_digests(
    prerequisites: RuntimeAllocationExecutionPrerequisites,
) -> tuple[str, str, str, str, str, str]:
    return (
        prerequisites.allocation_plan.allocation_metadata_digest,
        _digest(dump_runtime_memory_budget_report(prerequisites.memory_budget)),
        prerequisites.request_manifest.manifest_metadata_digest,
        prerequisites.admission.admission_metadata_digest,
        prerequisites.receipt.receipt_metadata_digest,
        prerequisites.reconciliation.reconciliation_metadata_digest,
    )


def _expected_slot(slot: object) -> RuntimeAllocationSlotMaterialization:
    from tuc.runtime.allocation import RuntimeAllocationSlot

    if not isinstance(slot, RuntimeAllocationSlot):
        raise TypeError("materialized allocation expected slot is invalid")
    elements = _element_count(slot.shape)
    return RuntimeAllocationSlotMaterialization(
        slot_id=slot.slot_id,
        memory_domain=slot.memory_domain,
        layout=slot.layout,
        shape=slot.shape,
        planned_dtype=slot.dtype,
        runtime_dtype=RUNTIME_ALLOCATION_INTERNAL_DTYPE,
        planned_bytes=slot.bytes_reserved,
        runtime_bytes=elements * 8,
        tensor_count=slot.tensor_count,
        allocation_kind=slot.allocation_kind,
    )


def _slot_to_dict(slot: RuntimeAllocationSlotMaterialization) -> dict[str, object]:
    return {
        "allocation_kind": slot.allocation_kind,
        "layout": slot.layout.value,
        "memory_domain": slot.memory_domain.value,
        "planned_bytes": slot.planned_bytes,
        "planned_dtype": slot.planned_dtype,
        "runtime_bytes": slot.runtime_bytes,
        "runtime_dtype": slot.runtime_dtype,
        "shape": list(slot.shape),
        "slot_id": slot.slot_id,
        "status": slot.status,
        "tensor_count": slot.tensor_count,
    }


def _allocation_to_dict(
    record: RuntimeMaterializedAllocationRecord,
) -> dict[str, object]:
    return {
        "address_exposure": record.address_exposure,
        "first_live_index": record.first_live_index,
        "last_use_index": record.last_use_index,
        "layout": record.layout.value,
        "memory_domain": record.memory_domain.value,
        "operation_index": record.operation_index,
        "operation_name": record.operation_name,
        "planned_bytes": record.planned_bytes,
        "planned_dtype": record.planned_dtype,
        "previous_tensor_name": record.previous_tensor_name,
        "release_index": record.release_index,
        "release_verification": record.release_verification,
        "reuse_status": record.reuse_status,
        "runtime_bytes": record.runtime_bytes,
        "runtime_dtype": record.runtime_dtype,
        "shape": list(record.shape),
        "slot_generation": record.slot_generation,
        "slot_id": record.slot_id,
        "status": record.status,
        "tensor_name": record.tensor_name,
        "write_verification": record.write_verification,
    }


def _element_count(shape: tuple[int, ...]) -> int:
    _require_shape(shape)
    count = 1
    for dimension in shape:
        count *= dimension
    return count


def _require_shape(shape: tuple[int, ...]) -> None:
    if type(shape) is not tuple or not shape:
        raise TypeError("materialized allocation shape must be non-empty tuple")
    for dimension in shape:
        _require_positive_int(dimension, "shape dimension")


def _require_safe_text(value: str, label: str) -> None:
    if not isinstance(value, str) or _SAFE_TEXT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a safe identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds metadata byte limit")


def _require_digest(value: str) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError("materialized allocation metadata digest is invalid")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _digest(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_MATERIALIZED_ALLOCATION_REPORT_BYTES",
    "RUNTIME_MATERIALIZED_ALLOCATION_ARTIFACT_STATUS",
    "RUNTIME_MATERIALIZED_ALLOCATION_BUDGET_INTERPRETATION",
    "RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT",
    "RUNTIME_MATERIALIZED_ALLOCATION_KERNEL_TEMPORARY_POLICY",
    "RUNTIME_MATERIALIZED_ALLOCATION_NATIVE_CLAIM",
    "RUNTIME_MATERIALIZED_ALLOCATION_POLICY",
    "RUNTIME_MATERIALIZED_ALLOCATION_REPORT_SCHEMA_VERSION",
    "RUNTIME_MATERIALIZED_ALLOCATION_SCOPE",
    "RUNTIME_MATERIALIZED_ALLOCATION_STATUS",
    "RuntimeMaterializedAllocationRecord",
    "RuntimeMaterializedAllocationReport",
    "build_runtime_materialized_allocation_report",
    "dump_runtime_materialized_allocation_report",
    "runtime_materialized_allocation_report_to_dict",
]
