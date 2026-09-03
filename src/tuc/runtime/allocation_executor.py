"""Bounded trusted simulator allocation and slot-reuse execution."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import cast

import numpy as np
from numpy.typing import NDArray

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, TensorRef
from tuc.runtime.allocation import (
    RuntimeAllocationBinding,
    RuntimeAllocationPlanReport,
    RuntimeAllocationSlot,
    assert_runtime_allocation_plan,
    build_runtime_allocation_plan_report,
    dump_runtime_allocation_plan_report,
)
from tuc.runtime.allocation_admission import (
    RuntimeAllocationAdmissionReport,
    assert_runtime_allocation_admission,
    build_runtime_allocation_admission_report,
    dump_runtime_allocation_admission_report,
)
from tuc.runtime.allocation_receipt import (
    RuntimeAllocationReceiptReport,
    assert_runtime_allocation_receipt,
    build_runtime_allocation_receipt_report,
    dump_runtime_allocation_receipt_report,
)
from tuc.runtime.allocation_reconciliation import (
    RuntimeAllocationReconciliationReport,
    assert_runtime_allocation_reconciliation,
    build_runtime_allocation_reconciliation_report,
    dump_runtime_allocation_reconciliation_report,
)
from tuc.runtime.allocation_request_manifest import (
    RuntimeAllocationRequestManifestReport,
    assert_runtime_allocation_request_manifest,
    build_runtime_allocation_request_manifest_report,
    dump_runtime_allocation_request_manifest_report,
)
from tuc.runtime.buffer_lifetime import build_runtime_buffer_lifetime_report
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN,
    RuntimeExecutionResult,
    RuntimeExecutionStep,
    RuntimeExecutionTrace,
    RuntimeValueRecord,
    runtime_execution_readiness_report,
    trusted_runtime_executor_registry,
)
from tuc.runtime.memory_budget import (
    RuntimeMemoryBudgetReport,
    assert_runtime_memory_budget,
    build_runtime_memory_budget_report,
    dump_runtime_memory_budget_report,
)
from tuc.runtime.partitioning import Assignment, PartitionPlan

RUNTIME_ALLOCATION_EXECUTOR_CONTRACT = "runtime_allocator.trusted_simulator.v0"
RUNTIME_ALLOCATION_EXECUTION_MODE = "in_process_preallocated_numpy_slots"
RUNTIME_ALLOCATION_WRITE_MODE = "trusted_kernel_result_copied_into_slot"
RUNTIME_ALLOCATION_RETENTION_POLICY = (
    "external_inputs_and_terminal_output_snapshots_only"
)
RUNTIME_ALLOCATION_INTERNAL_DTYPE = "float64"
RUNTIME_ALLOCATION_PLANNED_DTYPE = "float32"
RUNTIME_ALLOCATION_SUPPORTED_DOMAIN = MemoryDomainKind.HOST_RAM
RUNTIME_ALLOCATION_SUPPORTED_LAYOUT = LayoutKind.ROW_MAJOR
RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM = "host_process_storage_only"
RUNTIME_ALLOCATION_PERFORMANCE_CLAIM = "not_measured"
RUNTIME_ALLOCATION_HANDLE_POLICY = "not_exposed"
RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS = "forbidden"
RUNTIME_ALLOCATION_EXECUTION_STATUS = "executed_and_verified"
RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES = (
    *RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    "allocator_plugin_loading",
    "device_allocation",
    "external_allocator_calls",
    "memory_mapping",
    "pointer_or_address_exposure",
    "runtime_handle_serialization",
    "unbounded_memory_pool",
)
MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS = 256
MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS = 4096
MAX_RUNTIME_MATERIALIZED_ALLOCATION_ELEMENTS = 2_000_000
MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES = 128 * 1024 * 1024
MAX_RUNTIME_MATERIALIZED_ALLOCATION_FIELD_BYTES = 256

FloatArray = NDArray[np.float64]
_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class TrustedRuntimeAllocationExecutorContract:
    """Closed contract for the first materialized simulator allocator."""

    allocator_contract: str = RUNTIME_ALLOCATION_EXECUTOR_CONTRACT
    execution_mode: str = RUNTIME_ALLOCATION_EXECUTION_MODE
    write_mode: str = RUNTIME_ALLOCATION_WRITE_MODE
    retention_policy: str = RUNTIME_ALLOCATION_RETENTION_POLICY
    internal_dtype: str = RUNTIME_ALLOCATION_INTERNAL_DTYPE
    supported_domain: MemoryDomainKind = RUNTIME_ALLOCATION_SUPPORTED_DOMAIN
    supported_layout: LayoutKind = RUNTIME_ALLOCATION_SUPPORTED_LAYOUT
    physical_memory_claim: str = RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM
    performance_claim: str = RUNTIME_ALLOCATION_PERFORMANCE_CLAIM
    handle_policy: str = RUNTIME_ALLOCATION_HANDLE_POLICY
    external_artifacts: str = RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS
    max_slots: int = MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS
    max_bindings: int = MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS
    max_elements: int = MAX_RUNTIME_MATERIALIZED_ALLOCATION_ELEMENTS
    max_internal_bytes: int = MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        expected = (
            (self.allocator_contract, RUNTIME_ALLOCATION_EXECUTOR_CONTRACT),
            (self.execution_mode, RUNTIME_ALLOCATION_EXECUTION_MODE),
            (self.write_mode, RUNTIME_ALLOCATION_WRITE_MODE),
            (self.retention_policy, RUNTIME_ALLOCATION_RETENTION_POLICY),
            (self.internal_dtype, RUNTIME_ALLOCATION_INTERNAL_DTYPE),
            (self.supported_domain, RUNTIME_ALLOCATION_SUPPORTED_DOMAIN),
            (self.supported_layout, RUNTIME_ALLOCATION_SUPPORTED_LAYOUT),
            (self.physical_memory_claim, RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM),
            (self.performance_claim, RUNTIME_ALLOCATION_PERFORMANCE_CLAIM),
            (self.handle_policy, RUNTIME_ALLOCATION_HANDLE_POLICY),
            (self.external_artifacts, RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS),
            (self.max_slots, MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS),
            (self.max_bindings, MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS),
            (self.max_elements, MAX_RUNTIME_MATERIALIZED_ALLOCATION_ELEMENTS),
            (self.max_internal_bytes, MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES),
        )
        if any(observed != required for observed, required in expected):
            raise ValueError("runtime allocation executor contract changed")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("runtime allocation executor security boundary changed")


@dataclass(frozen=True)
class RuntimeAllocationExecutionPrerequisites:
    """Reviewed planning evidence required before materialized allocation."""

    allocation_plan: RuntimeAllocationPlanReport
    memory_budget: RuntimeMemoryBudgetReport
    request_manifest: RuntimeAllocationRequestManifestReport
    admission: RuntimeAllocationAdmissionReport
    receipt: RuntimeAllocationReceiptReport
    reconciliation: RuntimeAllocationReconciliationReport

    def __post_init__(self) -> None:
        expected_types = (
            (self.allocation_plan, RuntimeAllocationPlanReport),
            (self.memory_budget, RuntimeMemoryBudgetReport),
            (self.request_manifest, RuntimeAllocationRequestManifestReport),
            (self.admission, RuntimeAllocationAdmissionReport),
            (self.receipt, RuntimeAllocationReceiptReport),
            (self.reconciliation, RuntimeAllocationReconciliationReport),
        )
        if any(not isinstance(value, kind) for value, kind in expected_types):
            raise TypeError("runtime allocation prerequisites contain an invalid report")


@dataclass(frozen=True)
class RuntimeAllocationSlotMaterialization:
    """Metadata for one slot allocated before graph execution."""

    slot_id: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    shape: tuple[int, ...]
    planned_dtype: str
    runtime_dtype: str
    planned_bytes: int
    runtime_bytes: int
    tensor_count: int
    allocation_kind: str
    status: str = "preallocated"

    def __post_init__(self) -> None:
        _require_safe_text(self.slot_id, "slot_id")
        if self.memory_domain is not RUNTIME_ALLOCATION_SUPPORTED_DOMAIN:
            raise ValueError("materialized allocation slot domain is unsupported")
        if self.layout is not RUNTIME_ALLOCATION_SUPPORTED_LAYOUT:
            raise ValueError("materialized allocation slot layout is unsupported")
        _require_shape(self.shape)
        if self.planned_dtype != RUNTIME_ALLOCATION_PLANNED_DTYPE:
            raise ValueError("materialized allocation planned dtype is unsupported")
        if self.runtime_dtype != RUNTIME_ALLOCATION_INTERNAL_DTYPE:
            raise ValueError("materialized allocation runtime dtype mismatch")
        elements = _element_count(self.shape)
        if self.planned_bytes != elements * 4:
            raise ValueError("materialized allocation planned byte count mismatch")
        if self.runtime_bytes != elements * 8:
            raise ValueError("materialized allocation runtime byte count mismatch")
        _require_positive_int(self.tensor_count, "tensor_count")
        expected_kind = "reused" if self.tensor_count > 1 else "exclusive"
        if self.allocation_kind != expected_kind:
            raise ValueError("materialized allocation slot kind mismatch")
        if self.status != "preallocated":
            raise ValueError("materialized allocation slot status mismatch")


@dataclass(frozen=True)
class RuntimeAllocationWriteStep:
    """One verified write of a trusted kernel result into a planned slot."""

    operation_name: str
    operation_index: int
    tensor_name: str
    slot_id: str
    slot_generation: int
    previous_tensor_name: str | None
    first_live_index: int
    last_use_index: int
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    shape: tuple[int, ...]
    planned_dtype: str
    runtime_dtype: str
    planned_bytes: int
    runtime_bytes: int
    reuse_status: str
    write_mode: str = RUNTIME_ALLOCATION_WRITE_MODE
    semantic_verification: str = "exact_kernel_result"
    address_exposure: str = RUNTIME_ALLOCATION_HANDLE_POLICY
    status: str = RUNTIME_ALLOCATION_EXECUTION_STATUS

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
        if self.operation_index != self.first_live_index:
            raise ValueError("materialized allocation write index mismatch")
        if self.last_use_index < self.first_live_index:
            raise ValueError("materialized allocation live range is invalid")
        if self.memory_domain is not RUNTIME_ALLOCATION_SUPPORTED_DOMAIN:
            raise ValueError("materialized allocation write domain is unsupported")
        if self.layout is not RUNTIME_ALLOCATION_SUPPORTED_LAYOUT:
            raise ValueError("materialized allocation write layout is unsupported")
        _require_shape(self.shape)
        elements = _element_count(self.shape)
        if self.planned_dtype != RUNTIME_ALLOCATION_PLANNED_DTYPE:
            raise ValueError("materialized allocation write planned dtype mismatch")
        if self.runtime_dtype != RUNTIME_ALLOCATION_INTERNAL_DTYPE:
            raise ValueError("materialized allocation write runtime dtype mismatch")
        if self.planned_bytes != elements * 4 or self.runtime_bytes != elements * 8:
            raise ValueError("materialized allocation write byte count mismatch")
        if self.reuse_status not in {"first_slot_generation", "reused_after_release"}:
            raise ValueError("materialized allocation reuse status is unsupported")
        if self.slot_generation == 1:
            if self.reuse_status != "first_slot_generation":
                raise ValueError("first allocation generation cannot claim reuse")
            if self.previous_tensor_name is not None:
                raise ValueError("first allocation generation cannot have predecessor")
        elif (
            self.reuse_status != "reused_after_release"
            or self.previous_tensor_name is None
        ):
            raise ValueError("later allocation generation must bind released predecessor")
        if self.write_mode != RUNTIME_ALLOCATION_WRITE_MODE:
            raise ValueError("materialized allocation write mode mismatch")
        if self.semantic_verification != "exact_kernel_result":
            raise ValueError("materialized allocation semantic verification mismatch")
        if self.address_exposure != RUNTIME_ALLOCATION_HANDLE_POLICY:
            raise ValueError("materialized allocation must not expose addresses")
        if self.status != RUNTIME_ALLOCATION_EXECUTION_STATUS:
            raise ValueError("materialized allocation write status mismatch")


@dataclass(frozen=True)
class RuntimeAllocationReleaseStep:
    """One logical release after a tensor's proven final use."""

    tensor_name: str
    slot_id: str
    slot_generation: int
    release_index: int
    release_reason: str = "last_use_reached"
    status: str = "released"

    def __post_init__(self) -> None:
        _require_safe_text(self.tensor_name, "release tensor_name")
        _require_safe_text(self.slot_id, "release slot_id")
        _require_positive_int(self.slot_generation, "release slot_generation")
        _require_non_negative_int(self.release_index, "release_index")
        if self.release_reason != "last_use_reached":
            raise ValueError("materialized allocation release reason mismatch")
        if self.status != "released":
            raise ValueError("materialized allocation release status mismatch")


@dataclass(frozen=True)
class RuntimeAllocationExecutionTrace:
    """Closed metadata-only trace of materialized slot allocation and reuse."""

    graph_name: str
    source_allocation_plan_digest: str
    source_memory_budget_digest: str
    source_request_manifest_digest: str
    source_admission_digest: str
    source_receipt_digest: str
    source_reconciliation_digest: str
    slots: tuple[RuntimeAllocationSlotMaterialization, ...]
    writes: tuple[RuntimeAllocationWriteStep, ...]
    releases: tuple[RuntimeAllocationReleaseStep, ...]
    allocator_contract: str = RUNTIME_ALLOCATION_EXECUTOR_CONTRACT
    execution_mode: str = RUNTIME_ALLOCATION_EXECUTION_MODE
    retention_policy: str = RUNTIME_ALLOCATION_RETENTION_POLICY
    physical_memory_claim: str = RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM
    performance_claim: str = RUNTIME_ALLOCATION_PERFORMANCE_CLAIM
    handle_policy: str = RUNTIME_ALLOCATION_HANDLE_POLICY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_ALLOCATION_EXECUTION_STATUS

    def __post_init__(self) -> None:
        _require_safe_text(self.graph_name, "allocation trace graph_name")
        for digest in (
            self.source_allocation_plan_digest,
            self.source_memory_budget_digest,
            self.source_request_manifest_digest,
            self.source_admission_digest,
            self.source_receipt_digest,
            self.source_reconciliation_digest,
        ):
            _require_digest(digest)
        if type(self.slots) is not tuple or not self.slots:
            raise ValueError("materialized allocation trace requires slots")
        if len(self.slots) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS:
            raise ValueError("materialized allocation slot count exceeds limit")
        if type(self.writes) is not tuple or not self.writes:
            raise ValueError("materialized allocation trace requires writes")
        if len(self.writes) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS:
            raise ValueError("materialized allocation write count exceeds limit")
        if type(self.releases) is not tuple or len(self.releases) != len(self.writes):
            raise ValueError("materialized allocation releases must match writes")
        if not all(isinstance(slot, RuntimeAllocationSlotMaterialization) for slot in self.slots):
            raise TypeError("materialized allocation slots must be slot records")
        if not all(isinstance(step, RuntimeAllocationWriteStep) for step in self.writes):
            raise TypeError("materialized allocation writes must be write steps")
        if not all(isinstance(step, RuntimeAllocationReleaseStep) for step in self.releases):
            raise TypeError("materialized allocation releases must be release steps")
        slot_ids = tuple(slot.slot_id for slot in self.slots)
        if len(set(slot_ids)) != len(slot_ids):
            raise ValueError("materialized allocation trace has duplicate slots")
        write_keys = {
            (step.tensor_name, step.slot_id, step.slot_generation)
            for step in self.writes
        }
        release_keys = {
            (step.tensor_name, step.slot_id, step.slot_generation)
            for step in self.releases
        }
        if write_keys != release_keys:
            raise ValueError("materialized allocation release set mismatch")
        if any(step.slot_id not in slot_ids for step in self.writes):
            raise ValueError("materialized allocation write references unknown slot")
        expected = (
            (self.allocator_contract, RUNTIME_ALLOCATION_EXECUTOR_CONTRACT),
            (self.execution_mode, RUNTIME_ALLOCATION_EXECUTION_MODE),
            (self.retention_policy, RUNTIME_ALLOCATION_RETENTION_POLICY),
            (self.physical_memory_claim, RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM),
            (self.performance_claim, RUNTIME_ALLOCATION_PERFORMANCE_CLAIM),
            (self.handle_policy, RUNTIME_ALLOCATION_HANDLE_POLICY),
            (self.status, RUNTIME_ALLOCATION_EXECUTION_STATUS),
        )
        if any(observed != required for observed, required in expected):
            raise ValueError("materialized allocation trace contract mismatch")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("materialized allocation trace security boundary changed")
        if self.runtime_reserved_bytes > MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES:
            raise ValueError("materialized allocation runtime byte limit exceeded")

    @property
    def planned_reserved_bytes(self) -> int:
        return sum(slot.planned_bytes for slot in self.slots)

    @property
    def runtime_reserved_bytes(self) -> int:
        return sum(slot.runtime_bytes for slot in self.slots)

    @property
    def runtime_unreused_tensor_bytes(self) -> int:
        return sum(step.runtime_bytes for step in self.writes)

    @property
    def runtime_reuse_savings_bytes(self) -> int:
        return self.runtime_unreused_tensor_bytes - self.runtime_reserved_bytes

    @property
    def reuse_event_count(self) -> int:
        return sum(step.reuse_status == "reused_after_release" for step in self.writes)

    @property
    def metadata_digest(self) -> str:
        return _digest(self.dump())

    def dump(self) -> str:
        """Render deterministic allocation metadata without values or addresses."""

        lines = [f"runtime.allocation_execution_trace @{self.graph_name} {{"]
        lines.append(f'  allocator_contract = "{self.allocator_contract}"')
        lines.append(f'  execution_mode = "{self.execution_mode}"')
        lines.append(f'  retention_policy = "{self.retention_policy}"')
        lines.append(f'  handle_policy = "{self.handle_policy}"')
        lines.append(f"  planned_reserved_bytes = {self.planned_reserved_bytes}")
        lines.append(f"  runtime_reserved_bytes = {self.runtime_reserved_bytes}")
        lines.append(f"  runtime_reuse_savings_bytes = {self.runtime_reuse_savings_bytes}")
        lines.append("  slots {")
        for slot in self.slots:
            lines.append(
                "    slot "
                f"{slot.slot_id} domain={slot.memory_domain.value} "
                f"layout={slot.layout.value} shape={_format_shape(slot.shape)} "
                f"planned_bytes={slot.planned_bytes} runtime_bytes={slot.runtime_bytes} "
                f"tensor_count={slot.tensor_count} kind={slot.allocation_kind}"
            )
        lines.append("  }")
        lines.append("  writes {")
        for write_step in self.writes:
            previous = write_step.previous_tensor_name or "none"
            lines.append(
                "    write "
                f"op={write_step.operation_name} index={write_step.operation_index} "
                f"tensor={write_step.tensor_name} slot={write_step.slot_id} "
                f"generation={write_step.slot_generation} previous={previous} "
                f"last_use={write_step.last_use_index} reuse={write_step.reuse_status}"
            )
        lines.append("  }")
        lines.append("  releases {")
        for release_step in self.releases:
            lines.append(
                "    release "
                f"tensor={release_step.tensor_name} slot={release_step.slot_id} "
                f"generation={release_step.slot_generation} "
                f"index={release_step.release_index}"
            )
        lines.append("  }")
        lines.append(f'  status = "{self.status}"')
        lines.append("}")
        return "\n".join(lines)


@dataclass(frozen=True)
class RuntimeMaterializedAllocationExecution:
    """Runtime outputs plus allocation trace for the opt-in allocator path."""

    execution: RuntimeExecutionResult
    allocation_trace: RuntimeAllocationExecutionTrace

    def __post_init__(self) -> None:
        if not isinstance(self.execution, RuntimeExecutionResult):
            raise TypeError("materialized allocation execution must contain runtime result")
        if not isinstance(self.allocation_trace, RuntimeAllocationExecutionTrace):
            raise TypeError("materialized allocation execution must contain allocation trace")
        if self.execution.trace.graph_name != self.allocation_trace.graph_name:
            raise ValueError("materialized allocation execution graph linkage mismatch")
        if self.execution.trace.layout_conversion_steps:
            raise ValueError("materialized allocation v0 does not execute layout conversion")
        if self.execution.trace.transfer_steps:
            raise ValueError("materialized allocation v0 does not execute transfers")

    def output_for(self, tensor_name: str) -> FloatArray:
        """Return one retained terminal output snapshot."""

        return self.execution.output_for(tensor_name)


@dataclass
class _RuntimeSlotState:
    slot: RuntimeAllocationSlot
    storage: FloatArray
    generation: int = 0
    current_tensor_name: str | None = None
    previous_tensor_name: str | None = None


class _RuntimeAllocationArena:
    """Private bounded arena; storage identity never enters public evidence."""

    def __init__(self, slots: tuple[RuntimeAllocationSlot, ...]) -> None:
        self._states: dict[str, _RuntimeSlotState] = {}
        for slot in slots:
            storage = _allocate_slot_storage(slot.shape)
            self._states[slot.slot_id] = _RuntimeSlotState(slot=slot, storage=storage)

    def materialize(
        self,
        binding: RuntimeAllocationBinding,
        value: FloatArray,
    ) -> tuple[FloatArray, RuntimeAllocationWriteStep]:
        state = self._states.get(binding.slot_id)
        if state is None:
            raise ValueError("materialized allocation binding references missing slot")
        if state.current_tensor_name is not None:
            raise ValueError("materialized allocation attempted reuse before release")
        _validate_kernel_result(binding, value)
        state.generation += 1
        previous = state.previous_tensor_name
        np.copyto(state.storage, value, casting="no")
        if not bool(np.array_equal(state.storage, value)):
            raise ValueError("materialized allocation slot write verification failed")
        view = state.storage.view()
        view.setflags(write=False)
        state.current_tensor_name = binding.tensor_name
        state.previous_tensor_name = binding.tensor_name
        step = RuntimeAllocationWriteStep(
            operation_name=binding.producer_operation,
            operation_index=binding.producer_index,
            tensor_name=binding.tensor_name,
            slot_id=binding.slot_id,
            slot_generation=state.generation,
            previous_tensor_name=previous,
            first_live_index=binding.first_live_index,
            last_use_index=binding.last_use_index,
            memory_domain=binding.memory_domain,
            layout=binding.layout,
            shape=binding.shape,
            planned_dtype=binding.dtype,
            runtime_dtype=str(view.dtype),
            planned_bytes=binding.bytes_required,
            runtime_bytes=int(view.nbytes),
            reuse_status=(
                "first_slot_generation"
                if state.generation == 1
                else "reused_after_release"
            ),
        )
        return view, step

    def release(
        self,
        binding: RuntimeAllocationBinding,
        *,
        release_index: int,
    ) -> RuntimeAllocationReleaseStep:
        state = self._states.get(binding.slot_id)
        if state is None or state.current_tensor_name != binding.tensor_name:
            raise ValueError("materialized allocation release does not own slot")
        if release_index != binding.last_use_index:
            raise ValueError("materialized allocation release precedes proven last use")
        state.current_tensor_name = None
        return RuntimeAllocationReleaseStep(
            tensor_name=binding.tensor_name,
            slot_id=binding.slot_id,
            slot_generation=state.generation,
            release_index=release_index,
        )

    def assert_empty(self) -> None:
        if any(state.current_tensor_name is not None for state in self._states.values()):
            raise ValueError("materialized allocation arena retained live tensors")


def trusted_runtime_allocation_executor_contract() -> (
    TrustedRuntimeAllocationExecutorContract
):
    """Return the fixed trusted materialized allocator contract."""

    return TrustedRuntimeAllocationExecutorContract()


def execute_graph_with_materialized_allocations(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    inputs: Mapping[str, object],
    prerequisites: RuntimeAllocationExecutionPrerequisites,
) -> RuntimeMaterializedAllocationExecution:
    """Execute produced values through preallocated, lifetime-bound slots."""

    assert_materializable_runtime_allocation(graph, partition_plan, prerequisites)
    external_tensors = _preflight_inputs(graph, inputs)
    validated_inputs = {
        name: cast(FloatArray, inputs[name]) for name in external_tensors
    }
    allocation_plan = prerequisites.allocation_plan
    arena = _RuntimeAllocationArena(allocation_plan.slots)
    input_records = tuple(
        RuntimeValueRecord(
            tensor_name=name,
            value=validated_inputs[name],
            shape=tensor.shape,
            dtype=str(validated_inputs[name].dtype),
            value_role="input",
            producer_kind="external_input",
            producer_id=name,
        )
        for name, tensor in sorted(external_tensors.items())
    )
    external_values = {record.tensor_name: record.value for record in input_records}
    active_values: dict[str, FloatArray] = {}
    bindings = {binding.tensor_name: binding for binding in allocation_plan.bindings}
    assignments = {
        assignment.operation_name: assignment for assignment in partition_plan.assignments
    }
    executors = trusted_runtime_executor_registry()
    operation_steps: list[RuntimeExecutionStep] = []
    write_steps: list[RuntimeAllocationWriteStep] = []
    release_steps: list[RuntimeAllocationReleaseStep] = []

    for operation_index, operation in enumerate(graph.operations):
        assignment = assignments[operation.name]
        executor = executors[assignment.backend_name]
        operation_values = MappingProxyType({**external_values, **active_values})
        kernel_result = executor.execute(operation, operation_values)
        output = operation.outputs[0]
        binding = bindings[output.name]
        allocated_value, write_step = arena.materialize(binding, kernel_result)
        active_values[output.name] = allocated_value
        write_steps.append(write_step)
        operation_steps.append(_operation_step(operation, assignment, kernel_result))

        for expired in allocation_plan.bindings:
            if expired.last_use_index != operation_index:
                continue
            if expired.tensor_name not in active_values:
                raise ValueError("materialized allocation live tensor missing at release")
            del active_values[expired.tensor_name]
            release_steps.append(
                arena.release(expired, release_index=operation_index)
            )

    output_names = _terminal_output_names(graph)
    output_records: list[RuntimeValueRecord] = []
    for tensor_name in output_names:
        binding = bindings[tensor_name]
        value = active_values.get(tensor_name)
        if value is None:
            raise ValueError("materialized allocation terminal output is not live")
        assignment = assignments[binding.producer_operation]
        output_records.append(
            RuntimeValueRecord(
                tensor_name=tensor_name,
                value=value,
                shape=binding.shape,
                dtype=str(value.dtype),
                value_role="computed",
                producer_kind="operation",
                producer_id=binding.producer_operation,
                planned_backend=assignment.backend_name,
                planned_memory_domain=assignment.memory_domain,
                planned_layout=assignment.produced_layout,
                placement_source=RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN,
            )
        )
    for tensor_name in output_names:
        binding = bindings[tensor_name]
        del active_values[tensor_name]
        release_steps.append(
            arena.release(binding, release_index=allocation_plan.operation_count)
        )
    if active_values:
        raise ValueError("materialized allocation execution retained non-terminal values")
    arena.assert_empty()

    retained_records = input_records + tuple(output_records)
    execution = RuntimeExecutionResult(
        values={record.tensor_name: record.value for record in retained_records},
        trace=RuntimeExecutionTrace(
            graph_name=graph.name,
            executor_contract=RUNTIME_EXECUTOR_CONTRACT,
            steps=tuple(operation_steps),
        ),
        records=retained_records,
    )
    allocation_trace = RuntimeAllocationExecutionTrace(
        graph_name=graph.name,
        source_allocation_plan_digest=allocation_plan.allocation_metadata_digest,
        source_memory_budget_digest=_digest(
            dump_runtime_memory_budget_report(prerequisites.memory_budget)
        ),
        source_request_manifest_digest=(
            prerequisites.request_manifest.manifest_metadata_digest
        ),
        source_admission_digest=prerequisites.admission.admission_metadata_digest,
        source_receipt_digest=prerequisites.receipt.receipt_metadata_digest,
        source_reconciliation_digest=(
            prerequisites.reconciliation.reconciliation_metadata_digest
        ),
        slots=tuple(_slot_materialization(slot) for slot in allocation_plan.slots),
        writes=tuple(write_steps),
        releases=tuple(release_steps),
    )
    expected_reuse_events = len(allocation_plan.bindings) - len(allocation_plan.slots)
    if allocation_trace.reuse_event_count != expected_reuse_events:
        raise ValueError("materialized allocation did not execute planned slot reuse")
    return RuntimeMaterializedAllocationExecution(
        execution=execution,
        allocation_trace=allocation_trace,
    )


def assert_materializable_runtime_allocation(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    prerequisites: RuntimeAllocationExecutionPrerequisites,
) -> RuntimeAllocationExecutionPrerequisites:
    """Validate the complete allocation proof chain before allocating memory."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("materialized allocation graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("materialized allocation plan must be PartitionPlan")
    if not isinstance(prerequisites, RuntimeAllocationExecutionPrerequisites):
        raise TypeError("materialized allocation prerequisites are required")
    runtime_execution_readiness_report(graph, partition_plan)
    if partition_plan.transfer_edges or partition_plan.layout_conversions:
        raise ValueError(
            "materialized allocation v0 requires a transfer-free row-major proof slice"
        )
    reports = prerequisites
    assert_runtime_allocation_plan(reports.allocation_plan)
    assert_runtime_memory_budget(reports.memory_budget)
    assert_runtime_allocation_request_manifest(reports.request_manifest)
    assert_runtime_allocation_admission(reports.admission)
    assert_runtime_allocation_receipt(reports.receipt)
    assert_runtime_allocation_reconciliation(reports.reconciliation)

    canonical_lifetime = build_runtime_buffer_lifetime_report(graph, partition_plan)
    canonical_allocation = build_runtime_allocation_plan_report(canonical_lifetime)
    _require_canonical_report(
        "allocation plan",
        dump_runtime_allocation_plan_report(reports.allocation_plan),
        dump_runtime_allocation_plan_report(canonical_allocation),
    )
    canonical_budget = build_runtime_memory_budget_report(
        canonical_allocation,
        reports.memory_budget.budgets,
    )
    _require_canonical_report(
        "memory budget",
        dump_runtime_memory_budget_report(reports.memory_budget),
        dump_runtime_memory_budget_report(canonical_budget),
    )
    canonical_manifest = build_runtime_allocation_request_manifest_report(
        canonical_allocation,
        canonical_budget,
    )
    _require_canonical_report(
        "request manifest",
        dump_runtime_allocation_request_manifest_report(reports.request_manifest),
        dump_runtime_allocation_request_manifest_report(canonical_manifest),
    )
    canonical_admission = build_runtime_allocation_admission_report(
        canonical_manifest,
        canonical_budget,
    )
    _require_canonical_report(
        "admission",
        dump_runtime_allocation_admission_report(reports.admission),
        dump_runtime_allocation_admission_report(canonical_admission),
    )
    canonical_receipt = build_runtime_allocation_receipt_report(canonical_admission)
    _require_canonical_report(
        "receipt",
        dump_runtime_allocation_receipt_report(reports.receipt),
        dump_runtime_allocation_receipt_report(canonical_receipt),
    )
    canonical_reconciliation = build_runtime_allocation_reconciliation_report(
        canonical_admission,
        canonical_receipt,
    )
    _require_canonical_report(
        "reconciliation",
        dump_runtime_allocation_reconciliation_report(reports.reconciliation),
        dump_runtime_allocation_reconciliation_report(canonical_reconciliation),
    )

    allocation = reports.allocation_plan
    if not allocation.slots or not allocation.bindings:
        raise ValueError("materialized allocation requires planned slots and bindings")
    if len(allocation.slots) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS:
        raise ValueError("materialized allocation slot count exceeds limit")
    if len(allocation.bindings) > MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS:
        raise ValueError("materialized allocation binding count exceeds limit")
    if allocation.reuse_slot_count == 0:
        raise ValueError("materialized allocation proof requires planned slot reuse")
    runtime_bytes = 0
    for slot in allocation.slots:
        if slot.memory_domain is not RUNTIME_ALLOCATION_SUPPORTED_DOMAIN:
            raise ValueError("materialized allocation slot domain is unsupported")
        if slot.layout is not RUNTIME_ALLOCATION_SUPPORTED_LAYOUT:
            raise ValueError("materialized allocation slot layout is unsupported")
        if slot.dtype != RUNTIME_ALLOCATION_PLANNED_DTYPE:
            raise ValueError("materialized allocation slot dtype is unsupported")
        elements = _element_count(slot.shape)
        if elements > MAX_RUNTIME_MATERIALIZED_ALLOCATION_ELEMENTS:
            raise ValueError("materialized allocation slot element limit exceeded")
        runtime_bytes += elements * 8
    if runtime_bytes > MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES:
        raise ValueError("materialized allocation runtime byte limit exceeded")
    return prerequisites


def _preflight_inputs(
    graph: ComputeGraph,
    inputs: Mapping[str, object],
) -> dict[str, TensorRef]:
    if type(inputs) is not dict:
        raise TypeError("materialized allocation inputs must be a plain dict")
    external = _external_input_tensors(graph)
    missing = sorted(set(external) - set(inputs))
    extra = sorted(set(inputs) - set(external))
    if missing:
        raise ValueError(f"materialized allocation missing inputs: {','.join(missing)}")
    if extra:
        raise ValueError(f"materialized allocation unexpected inputs: {','.join(extra)}")
    for name, tensor in external.items():
        value = inputs[name]
        if not isinstance(value, np.ndarray):
            raise TypeError(f"materialized allocation input {name} must be NumPy array")
        if value.dtype != np.dtype(np.float64):
            raise TypeError(f"materialized allocation input {name} dtype must be float64")
        if tuple(value.shape) != tensor.shape:
            raise ValueError(f"materialized allocation input {name} shape mismatch")
        if value.size > MAX_RUNTIME_MATERIALIZED_ALLOCATION_ELEMENTS:
            raise ValueError(f"materialized allocation input {name} exceeds element limit")
        if not bool(np.all(np.isfinite(value))):
            raise ValueError(f"materialized allocation input {name} must be finite")
    return external


def _external_input_tensors(graph: ComputeGraph) -> dict[str, TensorRef]:
    produced: set[str] = set()
    external: dict[str, TensorRef] = {}
    for operation in graph.operations:
        for tensor in operation.inputs:
            if tensor.name not in produced:
                external.setdefault(tensor.name, tensor)
        for tensor in operation.outputs:
            produced.add(tensor.name)
    return external


def _terminal_output_names(graph: ComputeGraph) -> tuple[str, ...]:
    consumed = {tensor.name for operation in graph.operations for tensor in operation.inputs}
    return tuple(
        tensor.name
        for operation in graph.operations
        for tensor in operation.outputs
        if tensor.name not in consumed
    )


def _operation_step(
    operation: ComputeOperation,
    assignment: Assignment,
    value: FloatArray,
) -> RuntimeExecutionStep:
    return RuntimeExecutionStep(
        operation_name=operation.name,
        operation_kind=operation.kind,
        planned_backend=assignment.backend_name,
        executor_backend=assignment.backend_name,
        input_tensors=tuple(tensor.name for tensor in operation.inputs),
        output_tensors=tuple(tensor.name for tensor in operation.outputs),
        output_shapes=(tuple(int(dimension) for dimension in value.shape),),
        output_dtypes=(str(value.dtype),),
    )


def _slot_materialization(
    slot: RuntimeAllocationSlot,
) -> RuntimeAllocationSlotMaterialization:
    return RuntimeAllocationSlotMaterialization(
        slot_id=slot.slot_id,
        memory_domain=slot.memory_domain,
        layout=slot.layout,
        shape=slot.shape,
        planned_dtype=slot.dtype,
        runtime_dtype=RUNTIME_ALLOCATION_INTERNAL_DTYPE,
        planned_bytes=slot.bytes_reserved,
        runtime_bytes=_element_count(slot.shape) * 8,
        tensor_count=slot.tensor_count,
        allocation_kind=slot.allocation_kind,
    )


def _allocate_slot_storage(shape: tuple[int, ...]) -> FloatArray:
    return np.empty(shape, dtype=np.float64)


def _validate_kernel_result(
    binding: RuntimeAllocationBinding,
    value: object,
) -> None:
    if not isinstance(value, np.ndarray):
        raise TypeError("materialized allocation kernel result must be NumPy array")
    if value.dtype != np.dtype(np.float64):
        raise TypeError("materialized allocation kernel result dtype must be float64")
    if tuple(value.shape) != binding.shape:
        raise ValueError("materialized allocation kernel result shape mismatch")
    if not bool(np.all(np.isfinite(value))):
        raise ValueError("materialized allocation kernel result must be finite")


def _require_canonical_report(label: str, observed: str, expected: str) -> None:
    if observed != expected:
        raise ValueError(f"materialized allocation {label} is not canonical")


def _element_count(shape: tuple[int, ...]) -> int:
    _require_shape(shape)
    count = 1
    for dimension in shape:
        count *= dimension
    return count


def _require_shape(shape: tuple[int, ...]) -> None:
    if type(shape) is not tuple or not shape:
        raise TypeError("materialized allocation shape must be a non-empty tuple")
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


def _format_shape(shape: tuple[int, ...]) -> str:
    return "x".join(str(dimension) for dimension in shape)


def _digest(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS",
    "MAX_RUNTIME_MATERIALIZED_ALLOCATION_BYTES",
    "MAX_RUNTIME_MATERIALIZED_ALLOCATION_ELEMENTS",
    "MAX_RUNTIME_MATERIALIZED_ALLOCATION_FIELD_BYTES",
    "MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS",
    "RUNTIME_ALLOCATION_EXECUTION_MODE",
    "RUNTIME_ALLOCATION_EXECUTION_STATUS",
    "RUNTIME_ALLOCATION_EXECUTOR_BLOCKED_EXECUTION_SURFACES",
    "RUNTIME_ALLOCATION_EXECUTOR_CONTRACT",
    "RUNTIME_ALLOCATION_EXTERNAL_ARTIFACTS",
    "RUNTIME_ALLOCATION_HANDLE_POLICY",
    "RUNTIME_ALLOCATION_INTERNAL_DTYPE",
    "RUNTIME_ALLOCATION_PERFORMANCE_CLAIM",
    "RUNTIME_ALLOCATION_PHYSICAL_MEMORY_CLAIM",
    "RUNTIME_ALLOCATION_PLANNED_DTYPE",
    "RUNTIME_ALLOCATION_RETENTION_POLICY",
    "RUNTIME_ALLOCATION_SUPPORTED_DOMAIN",
    "RUNTIME_ALLOCATION_SUPPORTED_LAYOUT",
    "RUNTIME_ALLOCATION_WRITE_MODE",
    "RuntimeAllocationExecutionPrerequisites",
    "RuntimeAllocationExecutionTrace",
    "RuntimeAllocationReleaseStep",
    "RuntimeAllocationSlotMaterialization",
    "RuntimeAllocationWriteStep",
    "RuntimeMaterializedAllocationExecution",
    "TrustedRuntimeAllocationExecutorContract",
    "assert_materializable_runtime_allocation",
    "execute_graph_with_materialized_allocations",
    "trusted_runtime_allocation_executor_contract",
]
