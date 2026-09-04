"""Bounded trusted execution through planned heterogeneous storage slots."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from math import prod
from types import MappingProxyType

import numpy as np
from numpy.typing import NDArray

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, TensorRef
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
from tuc.runtime.heterogeneous_storage_plan import (
    MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES,
    MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS,
    MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS,
    RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE,
    RuntimeHeterogeneousStorageLifetime,
    RuntimeHeterogeneousStoragePlanReport,
    RuntimeHeterogeneousStorageSlot,
    assert_runtime_heterogeneous_storage_plan,
    build_runtime_heterogeneous_storage_plan_report,
    dump_runtime_heterogeneous_storage_plan_report,
)
from tuc.runtime.layout_conversion_executor import (
    RuntimeLayoutConversionExecutionStep,
    assert_materializable_layout_conversion,
)
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.plan import LayoutConversionCost, RuntimeTransferEdge
from tuc.runtime.transfer_executor import (
    RuntimeTransferExecutionStep,
    assert_materializable_runtime_transfer,
)

RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT = (
    "runtime_heterogeneous_storage_executor.trusted_simulator.v0"
)
RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE = (
    "in_process_preallocated_numpy_storage_slots"
)
RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY = (
    "planned_representation_written_into_exact_role_slot"
)
RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY = "release_at_planned_last_use_event"
RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY = (
    "external_inputs_and_terminal_output_snapshots_only"
)
RUNTIME_HETEROGENEOUS_STORAGE_INTERNAL_DTYPE = "float64"
RUNTIME_HETEROGENEOUS_STORAGE_PLANNED_DTYPE = "float32"
RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY = "not_exposed"
RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM = (
    "host_process_storage_with_simulated_domains"
)
RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM = "not_measured"
RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS = "forbidden"
RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_STATUS = "executed_and_verified"
RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES = (
    *RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    "allocator_plugin_discovery",
    "device_allocation",
    "external_allocator_calls",
    "memory_mapping",
    "pointer_or_address_exposure",
    "runtime_handle_serialization",
    "unbounded_memory_pool",
)
MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_BYTES = 32 * 1024 * 1024
MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_INPUT_BYTES = 32 * 1024 * 1024
MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_FIELD_BYTES = 256

FloatArray = NDArray[np.float64]
_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeHeterogeneousSlotMaterialization:
    """Metadata for one slot preallocated before heterogeneous execution."""

    slot_id: str
    storage_role: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    physical_shape: tuple[int, ...]
    tile_shape: tuple[int, ...]
    planned_dtype: str
    runtime_dtype: str
    planned_bytes: int
    runtime_bytes: int
    storage_count: int
    allocation_kind: str
    handle_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY
    status: str = "preallocated"

    def __post_init__(self) -> None:
        _require_safe_text(self.slot_id, "slot_id")
        _require_safe_text(self.storage_role, "storage_role")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("heterogeneous materialized slot domain is invalid")
        if self.layout not in {LayoutKind.ROW_MAJOR, LayoutKind.BLOCKED}:
            raise ValueError("heterogeneous materialized slot layout is unsupported")
        _require_shape(self.physical_shape, "physical_shape")
        _require_tile_shape(self.tile_shape, self.layout)
        if self.planned_dtype != RUNTIME_HETEROGENEOUS_STORAGE_PLANNED_DTYPE:
            raise ValueError("heterogeneous materialized slot planned dtype mismatch")
        if self.runtime_dtype != RUNTIME_HETEROGENEOUS_STORAGE_INTERNAL_DTYPE:
            raise ValueError("heterogeneous materialized slot runtime dtype mismatch")
        _require_positive_int(self.planned_bytes, "planned_bytes")
        _require_positive_int(self.runtime_bytes, "runtime_bytes")
        if self.runtime_bytes != prod(self.physical_shape) * 8:
            raise ValueError("heterogeneous materialized slot runtime bytes mismatch")
        _require_positive_int(self.storage_count, "storage_count")
        expected_kind = "reused" if self.storage_count > 1 else "exclusive"
        if self.allocation_kind != expected_kind:
            raise ValueError("heterogeneous materialized slot allocation kind mismatch")
        if self.handle_policy != RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY:
            raise ValueError("heterogeneous materialized slot exposes a handle")
        if self.status != "preallocated":
            raise ValueError("heterogeneous materialized slot status mismatch")


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageWrite:
    """One exact write into a planned physical storage lifetime."""

    storage_id: str
    tensor_name: str
    storage_role: str
    source_storage_id: str | None
    slot_id: str
    slot_generation: int
    previous_storage_id: str | None
    event_index: int
    event_phase: str
    last_use_event: int
    last_use_phase: str
    memory_domain: MemoryDomainKind
    layout: LayoutKind
    logical_shape: tuple[int, ...]
    physical_shape: tuple[int, ...]
    tile_shape: tuple[int, ...]
    planned_bytes: int
    runtime_bytes: int
    write_source: str
    reuse_status: str
    semantic_verification: str
    padding_verification: str
    handle_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY
    status: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.storage_id, "storage_id"),
            (self.tensor_name, "tensor_name"),
            (self.storage_role, "storage_role"),
            (self.slot_id, "slot_id"),
            (self.event_phase, "event_phase"),
            (self.last_use_phase, "last_use_phase"),
            (self.write_source, "write_source"),
        ):
            _require_safe_text(value, label)
        if self.source_storage_id is not None:
            _require_safe_text(self.source_storage_id, "source_storage_id")
        if self.previous_storage_id is not None:
            _require_safe_text(self.previous_storage_id, "previous_storage_id")
        _require_positive_int(self.slot_generation, "slot_generation")
        _require_non_negative_int(self.event_index, "event_index")
        _require_non_negative_int(self.last_use_event, "last_use_event")
        if self.last_use_event < self.event_index:
            raise ValueError("heterogeneous materialized lifetime is reversed")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("heterogeneous materialized write domain is invalid")
        if self.layout not in {LayoutKind.ROW_MAJOR, LayoutKind.BLOCKED}:
            raise ValueError("heterogeneous materialized write layout is unsupported")
        _require_shape(self.logical_shape, "logical_shape")
        _require_shape(self.physical_shape, "physical_shape")
        _require_tile_shape(self.tile_shape, self.layout)
        _require_positive_int(self.planned_bytes, "planned_bytes")
        _require_positive_int(self.runtime_bytes, "runtime_bytes")
        if self.runtime_bytes != prod(self.physical_shape) * 8:
            raise ValueError("heterogeneous materialized write runtime bytes mismatch")
        expected_source = {
            "produced_value": (None, "trusted_kernel_result"),
            "layout_staging": ("required", "trusted_layout_conversion"),
            "transfer_target_staging": ("required", "trusted_domain_copy"),
        }.get(self.storage_role)
        if expected_source is None:
            raise ValueError("heterogeneous materialized storage role is unsupported")
        if expected_source[0] is None and self.source_storage_id is not None:
            raise ValueError("produced storage cannot claim a source storage")
        if expected_source[0] == "required" and self.source_storage_id is None:
            raise ValueError("staging storage requires a source storage")
        if self.write_source != expected_source[1]:
            raise ValueError("heterogeneous materialized write source mismatch")
        if self.slot_generation == 1:
            if self.previous_storage_id is not None:
                raise ValueError("first slot generation cannot have a predecessor")
            if self.reuse_status != "first_slot_generation":
                raise ValueError("first slot generation cannot claim reuse")
        elif (
            self.previous_storage_id is None
            or self.reuse_status != "reused_after_release"
        ):
            raise ValueError("reused slot generation lacks a released predecessor")
        if self.semantic_verification != "exact_logical_values":
            raise ValueError("heterogeneous materialized semantic verification mismatch")
        expected_padding = (
            "zero_padding_verified"
            if self.layout is LayoutKind.BLOCKED
            else "not_applicable"
        )
        if self.padding_verification != expected_padding:
            raise ValueError("heterogeneous materialized padding verification mismatch")
        if self.handle_policy != RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY:
            raise ValueError("heterogeneous materialized write exposes a handle")
        if self.status != RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_STATUS:
            raise ValueError("heterogeneous materialized write status mismatch")


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageRelease:
    """One release at the exact final event declared by the storage plan."""

    storage_id: str
    slot_id: str
    slot_generation: int
    event_index: int
    event_phase: str
    release_verification: str = "released_at_planned_last_use"
    status: str = "released"

    def __post_init__(self) -> None:
        _require_safe_text(self.storage_id, "release storage_id")
        _require_safe_text(self.slot_id, "release slot_id")
        _require_positive_int(self.slot_generation, "release slot_generation")
        _require_non_negative_int(self.event_index, "release event_index")
        _require_safe_text(self.event_phase, "release event_phase")
        if self.release_verification != "released_at_planned_last_use":
            raise ValueError("heterogeneous materialized release verification mismatch")
        if self.status != "released":
            raise ValueError("heterogeneous materialized release status mismatch")


@dataclass(frozen=True)
class RuntimeHeterogeneousStorageExecutionTrace:
    """Metadata-only trace of exact slot writes, releases, and reuse."""

    graph_name: str
    source_storage_plan_digest: str
    slots: tuple[RuntimeHeterogeneousSlotMaterialization, ...]
    writes: tuple[RuntimeHeterogeneousStorageWrite, ...]
    releases: tuple[RuntimeHeterogeneousStorageRelease, ...]
    executor_contract: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT
    execution_mode: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE
    write_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY
    release_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY
    retention_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY
    physical_memory_claim: str = (
        RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM
    )
    performance_claim: str = RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM
    handle_policy: str = RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY
    external_artifacts: str = RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_STATUS

    def __post_init__(self) -> None:
        _require_safe_text(self.graph_name, "trace graph_name")
        _require_digest(self.source_storage_plan_digest)
        if type(self.slots) is not tuple or not self.slots:
            raise ValueError("heterogeneous storage trace requires slots")
        if len(self.slots) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS:
            raise ValueError("heterogeneous storage trace slot limit exceeded")
        if not all(
            isinstance(item, RuntimeHeterogeneousSlotMaterialization)
            for item in self.slots
        ):
            raise TypeError("heterogeneous storage trace slots are invalid")
        if type(self.writes) is not tuple or not self.writes:
            raise ValueError("heterogeneous storage trace requires writes")
        if len(self.writes) > MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES:
            raise ValueError("heterogeneous storage trace write limit exceeded")
        if not all(isinstance(item, RuntimeHeterogeneousStorageWrite) for item in self.writes):
            raise TypeError("heterogeneous storage trace writes are invalid")
        if type(self.releases) is not tuple or len(self.releases) != len(self.writes):
            raise ValueError("heterogeneous storage trace releases must match writes")
        if not all(
            isinstance(item, RuntimeHeterogeneousStorageRelease)
            for item in self.releases
        ):
            raise TypeError("heterogeneous storage trace releases are invalid")
        slot_ids = tuple(item.slot_id for item in self.slots)
        if len(set(slot_ids)) != len(slot_ids):
            raise ValueError("heterogeneous storage trace has duplicate slots")
        write_ids = tuple(item.storage_id for item in self.writes)
        release_ids = tuple(item.storage_id for item in self.releases)
        if len(set(write_ids)) != len(write_ids):
            raise ValueError("heterogeneous storage trace has duplicate writes")
        if set(write_ids) != set(release_ids):
            raise ValueError("heterogeneous storage trace release set mismatch")
        release_by_storage = {item.storage_id: item for item in self.releases}
        if any(item.slot_id not in slot_ids for item in self.writes):
            raise ValueError("heterogeneous storage write references an unknown slot")
        if any(item.slot_id not in slot_ids for item in self.releases):
            raise ValueError("heterogeneous storage release references an unknown slot")
        if tuple(item.event_index for item in self.writes) != tuple(
            sorted(item.event_index for item in self.writes)
        ):
            raise ValueError("heterogeneous storage writes are not event ordered")
        if tuple(item.event_index for item in self.releases) != tuple(
            sorted(item.event_index for item in self.releases)
        ):
            raise ValueError("heterogeneous storage releases are not event ordered")
        for slot in self.slots:
            slot_writes = tuple(item for item in self.writes if item.slot_id == slot.slot_id)
            if len(slot_writes) != slot.storage_count:
                raise ValueError("heterogeneous storage trace slot usage mismatch")
            for index, item in enumerate(slot_writes, start=1):
                if item.slot_generation != index:
                    raise ValueError("heterogeneous storage trace generation mismatch")
                expected_previous = None if index == 1 else slot_writes[index - 2].storage_id
                if item.previous_storage_id != expected_previous:
                    raise ValueError("heterogeneous storage trace predecessor mismatch")
                if expected_previous is not None and (
                    release_by_storage[expected_previous].event_index >= item.event_index
                ):
                    raise ValueError("heterogeneous storage trace reuse precedes release")
        expected = (
            (self.executor_contract, RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT),
            (self.execution_mode, RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE),
            (self.write_policy, RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY),
            (self.release_policy, RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY),
            (self.retention_policy, RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY),
            (
                self.physical_memory_claim,
                RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM,
            ),
            (self.performance_claim, RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM),
            (self.handle_policy, RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY),
            (self.external_artifacts, RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS),
            (self.status, RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_STATUS),
        )
        if any(observed != required for observed, required in expected):
            raise ValueError("heterogeneous storage trace contract mismatch")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("heterogeneous storage trace security boundary changed")
        if self.runtime_reserved_bytes > MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_BYTES:
            raise ValueError("heterogeneous storage trace runtime byte limit exceeded")
        if self.reuse_event_count <= 0 or self.runtime_reuse_savings_bytes <= 0:
            raise ValueError("heterogeneous storage trace requires executed reuse")

    @property
    def planned_reserved_bytes(self) -> int:
        return sum(item.planned_bytes for item in self.slots)

    @property
    def runtime_reserved_bytes(self) -> int:
        return sum(item.runtime_bytes for item in self.slots)

    @property
    def runtime_unreused_storage_bytes(self) -> int:
        return sum(item.runtime_bytes for item in self.writes)

    @property
    def runtime_reuse_savings_bytes(self) -> int:
        return self.runtime_unreused_storage_bytes - self.runtime_reserved_bytes

    @property
    def reuse_event_count(self) -> int:
        return sum(item.reuse_status == "reused_after_release" for item in self.writes)

    @property
    def trace_metadata_digest(self) -> str:
        return _metadata_digest(runtime_heterogeneous_storage_execution_trace_to_dict(self))


@dataclass(frozen=True)
class RuntimeMaterializedHeterogeneousStorageExecution:
    """Runtime outputs plus the private-arena metadata trace."""

    execution: RuntimeExecutionResult
    storage_trace: RuntimeHeterogeneousStorageExecutionTrace

    def __post_init__(self) -> None:
        if not isinstance(self.execution, RuntimeExecutionResult):
            raise TypeError("heterogeneous storage execution result is invalid")
        if not isinstance(self.storage_trace, RuntimeHeterogeneousStorageExecutionTrace):
            raise TypeError("heterogeneous storage execution trace is invalid")
        if self.execution.trace.graph_name != self.storage_trace.graph_name:
            raise ValueError("heterogeneous storage execution graph linkage mismatch")
        if not self.execution.trace.layout_conversion_steps:
            raise ValueError("heterogeneous storage execution requires layout conversion")
        if not self.execution.trace.transfer_steps:
            raise ValueError("heterogeneous storage execution requires transfer")

    def output_for(self, tensor_name: str) -> FloatArray:
        return self.execution.output_for(tensor_name)


@dataclass
class _RuntimeHeterogeneousSlotState:
    slot: RuntimeHeterogeneousStorageSlot
    storage: FloatArray
    generation: int = 0
    current_storage_id: str | None = None
    previous_storage_id: str | None = None


class _RuntimeHeterogeneousStorageArena:
    """Private fixed arena; NumPy identities never enter serialized evidence."""

    def __init__(self, slots: tuple[RuntimeHeterogeneousStorageSlot, ...]) -> None:
        self._states = {
            slot.slot_id: _RuntimeHeterogeneousSlotState(
                slot=slot,
                storage=np.empty(slot.physical_shape, dtype=np.float64),
            )
            for slot in slots
        }

    def materialize_produced(
        self,
        lifetime: RuntimeHeterogeneousStorageLifetime,
        value: FloatArray,
        *,
        event_index: int,
    ) -> RuntimeHeterogeneousStorageWrite:
        state, previous = self._prepare_write(lifetime, event_index)
        _validate_runtime_value(value, lifetime.logical_shape)
        if lifetime.layout is LayoutKind.ROW_MAJOR:
            np.copyto(state.storage, value, casting="no")
        elif lifetime.layout is LayoutKind.BLOCKED:
            _write_blocked_2x2(state.storage, value, lifetime.logical_shape)
        else:  # pragma: no cover - preflight narrows layouts.
            raise ValueError("heterogeneous produced layout is unsupported")
        self._verify_exact(lifetime, value, state.storage)
        generation = self._commit_write(state, lifetime.storage_id)
        return _write_record(
            lifetime,
            generation=generation,
            previous_storage_id=previous,
            source_storage_id=None,
            write_source="trusted_kernel_result",
        )

    def materialize_layout_conversion(
        self,
        source: RuntimeHeterogeneousStorageLifetime,
        target: RuntimeHeterogeneousStorageLifetime,
        *,
        event_index: int,
    ) -> tuple[RuntimeHeterogeneousStorageWrite, RuntimeLayoutConversionExecutionStep]:
        source_state = self._active_state(source)
        target_state, previous = self._prepare_write(target, event_index)
        if source.layout is not LayoutKind.BLOCKED:
            raise ValueError("heterogeneous layout source must be blocked")
        if target.layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("heterogeneous layout target must be row_major")
        if source.slot_id == target.slot_id:
            raise ValueError("heterogeneous layout conversion requires distinct slots")
        _copy_blocked_2x2_to_row_major(
            source_state.storage,
            target_state.storage,
            source.logical_shape,
        )
        if bool(np.shares_memory(source_state.storage, target_state.storage)):
            raise ValueError("heterogeneous layout slots must not share memory")
        self._verify_exact(source, target_state.storage, source_state.storage)
        generation = self._commit_write(target_state, target.storage_id)
        write = _write_record(
            target,
            generation=generation,
            previous_storage_id=previous,
            source_storage_id=source.storage_id,
            write_source="trusted_layout_conversion",
        )
        step = RuntimeLayoutConversionExecutionStep(
            tensor_name=source.tensor_name,
            source_operation=source.source_operation,
            target_operation=target.target_operation,
            source_layout=source.layout,
            target_layout=target.layout,
            logical_shape=source.logical_shape,
            physical_shape=source.physical_shape,
            tile_shape=RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE,
            planned_bytes=source.logical_bytes,
            runtime_logical_bytes=target.physical_element_count * 8,
            runtime_physical_bytes=source.physical_element_count * 8,
            logical_element_count=source.logical_element_count,
            physical_element_count=source.physical_element_count,
            padding_element_count=source.padding_element_count,
            temporary_storage_bytes=(
                source.physical_element_count * 8 + target.physical_element_count * 8
            ),
        )
        return write, step

    def materialize_transfer(
        self,
        source: RuntimeHeterogeneousStorageLifetime,
        target: RuntimeHeterogeneousStorageLifetime,
        transfer: RuntimeTransferEdge,
        *,
        event_index: int,
    ) -> tuple[RuntimeHeterogeneousStorageWrite, RuntimeTransferExecutionStep]:
        source_state = self._active_state(source)
        target_state, previous = self._prepare_write(target, event_index)
        if source.layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("heterogeneous transfer source must be row_major")
        if target.layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("heterogeneous transfer target must be row_major")
        if source.slot_id == target.slot_id:
            raise ValueError("heterogeneous transfer requires distinct slots")
        np.copyto(target_state.storage, source_state.storage, casting="no")
        if bool(np.shares_memory(source_state.storage, target_state.storage)):
            raise ValueError("heterogeneous transfer slots must not share memory")
        if not bool(np.array_equal(target_state.storage, source_state.storage)):
            raise ValueError("heterogeneous transfer changed logical values")
        generation = self._commit_write(target_state, target.storage_id)
        write = _write_record(
            target,
            generation=generation,
            previous_storage_id=previous,
            source_storage_id=source.storage_id,
            write_source="trusted_domain_copy",
        )
        step = RuntimeTransferExecutionStep(
            tensor_name=target.tensor_name,
            source_operation=transfer.source_operation,
            target_operation=transfer.target_operation,
            source_backend=transfer.source_backend,
            target_backend=transfer.target_backend,
            source_domain=transfer.source_domain,
            target_domain=transfer.target_domain,
            source_layout=transfer.source_layout,
            target_layout=transfer.target_layout,
            copy_input_layout=source.layout,
            logical_shape=target.logical_shape,
            planned_bytes=transfer.bytes_moved,
            runtime_bytes=target.physical_element_count * 8,
            element_count=target.logical_element_count,
        )
        return write, step

    def logical_view(self, lifetime: RuntimeHeterogeneousStorageLifetime) -> FloatArray:
        state = self._active_state(lifetime)
        if lifetime.layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("heterogeneous consumer requires row_major storage")
        view = state.storage.view()
        view.setflags(write=False)
        return view

    def release(
        self,
        lifetime: RuntimeHeterogeneousStorageLifetime,
        *,
        event_index: int,
    ) -> RuntimeHeterogeneousStorageRelease:
        state = self._active_state(lifetime)
        if event_index != lifetime.last_use_event:
            raise ValueError("heterogeneous storage release is not at planned last use")
        state.current_storage_id = None
        return RuntimeHeterogeneousStorageRelease(
            storage_id=lifetime.storage_id,
            slot_id=lifetime.slot_id,
            slot_generation=state.generation,
            event_index=event_index,
            event_phase=lifetime.last_use_phase,
        )

    def assert_empty(self) -> None:
        if any(state.current_storage_id is not None for state in self._states.values()):
            raise ValueError("heterogeneous storage arena retained live storage")

    def slot_materializations(self) -> tuple[RuntimeHeterogeneousSlotMaterialization, ...]:
        return tuple(_slot_materialization(state.slot) for state in self._states.values())

    def _prepare_write(
        self,
        lifetime: RuntimeHeterogeneousStorageLifetime,
        event_index: int,
    ) -> tuple[_RuntimeHeterogeneousSlotState, str | None]:
        if event_index != lifetime.first_live_event:
            raise ValueError("heterogeneous storage write is not at planned first use")
        state = self._states.get(lifetime.slot_id)
        if state is None:
            raise ValueError("heterogeneous storage lifetime references unknown slot")
        if state.current_storage_id is not None:
            raise ValueError("heterogeneous storage attempted reuse before release")
        if lifetime.storage_id not in state.slot.storage_ids:
            raise ValueError("heterogeneous storage lifetime is not assigned to slot")
        return state, state.previous_storage_id

    @staticmethod
    def _commit_write(
        state: _RuntimeHeterogeneousSlotState,
        storage_id: str,
    ) -> int:
        state.generation += 1
        state.current_storage_id = storage_id
        state.previous_storage_id = storage_id
        return state.generation

    def _active_state(
        self,
        lifetime: RuntimeHeterogeneousStorageLifetime,
    ) -> _RuntimeHeterogeneousSlotState:
        state = self._states.get(lifetime.slot_id)
        if state is None or state.current_storage_id != lifetime.storage_id:
            raise ValueError("heterogeneous storage lifetime is not active")
        return state

    @staticmethod
    def _verify_exact(
        lifetime: RuntimeHeterogeneousStorageLifetime,
        logical_value: FloatArray,
        physical_storage: FloatArray,
    ) -> None:
        if lifetime.layout is LayoutKind.ROW_MAJOR:
            if not bool(np.array_equal(physical_storage, logical_value)):
                raise ValueError("heterogeneous row_major storage verification failed")
            return
        _assert_blocked_2x2_equals(
            physical_storage,
            logical_value,
            lifetime.logical_shape,
        )


def execute_graph_with_materialized_heterogeneous_storage(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    inputs: Mapping[str, object],
    storage_plan: RuntimeHeterogeneousStoragePlanReport,
) -> RuntimeMaterializedHeterogeneousStorageExecution:
    """Execute one graph through the exact slots in a canonical storage plan."""

    canonical = assert_materializable_heterogeneous_storage_execution(
        graph,
        partition_plan,
        storage_plan,
    )
    external_tensors = _external_input_tensors(graph)
    validated_inputs = _preflight_inputs(external_tensors, inputs)
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
    external_values = {item.tensor_name: item.value for item in input_records}
    assignments = {item.operation_name: item for item in partition_plan.assignments}
    executors = trusted_runtime_executor_registry()
    produced_tensors, producers = _produced_tensors(graph)
    lifetimes = {item.storage_id: item for item in canonical.lifetimes}
    conversions = _conversions_by_target(partition_plan)
    transfers = _transfers_by_target(partition_plan)
    conversions_by_key = {
        (item.tensor_name, item.source_operation, item.target_operation): item
        for item in partition_plan.layout_conversions
        if item.source_operation is not None
    }
    transfers_by_key = {
        (item.tensor_name, item.source_operation, item.target_operation): item
        for item in partition_plan.transfer_edges
    }
    releases_by_event: dict[int, list[RuntimeHeterogeneousStorageLifetime]] = {}
    for lifetime in canonical.lifetimes:
        releases_by_event.setdefault(lifetime.last_use_event, []).append(lifetime)

    arena = _RuntimeHeterogeneousStorageArena(canonical.slots)
    writes: list[RuntimeHeterogeneousStorageWrite] = []
    releases: list[RuntimeHeterogeneousStorageRelease] = []
    operation_steps: list[RuntimeExecutionStep] = []
    conversion_steps: list[RuntimeLayoutConversionExecutionStep] = []
    transfer_steps: list[RuntimeTransferExecutionStep] = []

    def release_due(event_index: int) -> None:
        for lifetime in sorted(
            releases_by_event.get(event_index, ()),
            key=lambda item: item.storage_id,
        ):
            releases.append(arena.release(lifetime, event_index=event_index))

    for operation_index, operation in enumerate(graph.operations):
        layout_event = operation_index * 4
        transfer_event = layout_event + 1
        consumer_event = layout_event + 2
        output_event = layout_event + 3

        for conversion in conversions.get(operation.name, ()):
            source_id = f"storage.value.{conversion.tensor_name}"
            target_id = (
                f"storage.layout.{conversion.tensor_name}.{operation.name}"
            )
            write, conversion_step = arena.materialize_layout_conversion(
                lifetimes[source_id],
                lifetimes[target_id],
                event_index=layout_event,
            )
            writes.append(write)
            conversion_steps.append(conversion_step)
        release_due(layout_event)

        for transfer in transfers.get(operation.name, ()):
            key = (transfer.tensor_name, transfer.source_operation, operation.name)
            source_id = (
                f"storage.layout.{transfer.tensor_name}.{operation.name}"
                if key in conversions_by_key
                else f"storage.value.{transfer.tensor_name}"
            )
            target_id = (
                f"storage.transfer.{transfer.tensor_name}.{operation.name}"
            )
            write, transfer_step = arena.materialize_transfer(
                lifetimes[source_id],
                lifetimes[target_id],
                transfer,
                event_index=transfer_event,
            )
            writes.append(write)
            transfer_steps.append(transfer_step)
        release_due(transfer_event)

        operation_values: dict[str, FloatArray] = {}
        for tensor in operation.inputs:
            producer = producers.get(tensor.name)
            if producer is None:
                operation_values[tensor.name] = external_values[tensor.name]
                continue
            key = (tensor.name, producer, operation.name)
            if key in transfers_by_key:
                storage_id = f"storage.transfer.{tensor.name}.{operation.name}"
            elif key in conversions_by_key:
                storage_id = f"storage.layout.{tensor.name}.{operation.name}"
            else:
                storage_id = f"storage.value.{tensor.name}"
            operation_values[tensor.name] = arena.logical_view(lifetimes[storage_id])

        assignment = assignments[operation.name]
        executor = executors[assignment.backend_name]
        kernel_result = executor.execute(
            operation,
            MappingProxyType(operation_values),
        )
        _validate_kernel_result(operation, kernel_result)
        operation_steps.append(_operation_step(operation, assignment, kernel_result))
        release_due(consumer_event)

        output = operation.outputs[0]
        output_lifetime = lifetimes[f"storage.value.{output.name}"]
        writes.append(
            arena.materialize_produced(
                output_lifetime,
                kernel_result,
                event_index=output_event,
            )
        )
        release_due(output_event)

    graph_end_event = canonical.event_count - 1
    output_records: list[RuntimeValueRecord] = []
    for tensor_name in _terminal_output_names(graph):
        lifetime = lifetimes[f"storage.value.{tensor_name}"]
        assignment = assignments[lifetime.source_operation]
        output_records.append(
            RuntimeValueRecord(
                tensor_name=tensor_name,
                value=arena.logical_view(lifetime),
                shape=lifetime.logical_shape,
                dtype=RUNTIME_HETEROGENEOUS_STORAGE_INTERNAL_DTYPE,
                value_role="computed",
                producer_kind="operation",
                producer_id=lifetime.source_operation,
                planned_backend=assignment.backend_name,
                planned_memory_domain=assignment.memory_domain,
                planned_layout=assignment.produced_layout,
                placement_source=RUNTIME_VALUE_PLACEMENT_SOURCE_PARTITION_PLAN,
            )
        )
    release_due(graph_end_event)
    arena.assert_empty()

    retained_records = input_records + tuple(output_records)
    execution = RuntimeExecutionResult(
        values={item.tensor_name: item.value for item in retained_records},
        trace=RuntimeExecutionTrace(
            graph_name=graph.name,
            executor_contract=RUNTIME_EXECUTOR_CONTRACT,
            steps=tuple(operation_steps),
            layout_conversion_steps=tuple(conversion_steps),
            transfer_steps=tuple(transfer_steps),
        ),
        records=retained_records,
    )
    trace = RuntimeHeterogeneousStorageExecutionTrace(
        graph_name=graph.name,
        source_storage_plan_digest=_digest(
            dump_runtime_heterogeneous_storage_plan_report(canonical)
        ),
        slots=arena.slot_materializations(),
        writes=tuple(writes),
        releases=tuple(releases),
    )
    result = RuntimeMaterializedHeterogeneousStorageExecution(
        execution=execution,
        storage_trace=trace,
    )
    assert_materialized_heterogeneous_storage_execution(canonical, result)
    if set(produced_tensors) != {
        item.tensor_name
        for item in canonical.lifetimes
        if item.storage_role == "produced_value"
    }:
        raise ValueError("heterogeneous storage produced tensor set mismatch")
    return result


def assert_materializable_heterogeneous_storage_execution(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    storage_plan: RuntimeHeterogeneousStoragePlanReport,
) -> RuntimeHeterogeneousStoragePlanReport:
    """Validate the complete data-only plan before allocating any storage."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("heterogeneous storage execution graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("heterogeneous storage execution plan must be PartitionPlan")
    if not isinstance(storage_plan, RuntimeHeterogeneousStoragePlanReport):
        raise TypeError("heterogeneous storage execution requires a storage plan")
    runtime_execution_readiness_report(graph, partition_plan)
    assert_runtime_heterogeneous_storage_plan(storage_plan)
    canonical = build_runtime_heterogeneous_storage_plan_report(graph, partition_plan)
    if dump_runtime_heterogeneous_storage_plan_report(storage_plan) != (
        dump_runtime_heterogeneous_storage_plan_report(canonical)
    ):
        raise ValueError("heterogeneous storage execution plan is not canonical")
    if not canonical.planned_layout_conversion_count:
        raise ValueError("heterogeneous storage execution requires layout conversion")
    if not canonical.planned_transfer_count:
        raise ValueError("heterogeneous storage execution requires transfer")
    if not canonical.reused_slot_count:
        raise ValueError("heterogeneous storage execution requires planned reuse")
    if {item.memory_domain for item in canonical.slots} != {
        MemoryDomainKind.DEVICE_SRAM,
        MemoryDomainKind.HOST_RAM,
    }:
        raise ValueError("heterogeneous storage execution requires two simulated domains")
    if {item.layout for item in canonical.slots} != {
        LayoutKind.BLOCKED,
        LayoutKind.ROW_MAJOR,
    }:
        raise ValueError("heterogeneous storage execution requires blocked and row_major")
    runtime_bytes = 0
    for slot in canonical.slots:
        if slot.dtype != RUNTIME_HETEROGENEOUS_STORAGE_PLANNED_DTYPE:
            raise ValueError("heterogeneous storage execution supports float32 plans only")
        elements = prod(slot.physical_shape)
        if elements > MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS:
            raise ValueError("heterogeneous storage execution element limit exceeded")
        runtime_bytes += elements * 8
    if runtime_bytes > MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_BYTES:
        raise ValueError("heterogeneous storage execution runtime byte limit exceeded")
    tensors = _produced_tensors(graph)[0]
    for conversion in partition_plan.layout_conversions:
        tensor = tensors.get(conversion.tensor_name)
        if tensor is None:
            raise ValueError("heterogeneous storage conversion tensor is not produced")
        assert_materializable_layout_conversion(conversion, tensor)
    for transfer in partition_plan.transfer_edges:
        tensor = tensors.get(transfer.tensor_name)
        if tensor is None:
            raise ValueError("heterogeneous storage transfer tensor is not produced")
        assert_materializable_runtime_transfer(transfer, tensor)
    _validate_consumer_storage(graph, partition_plan, canonical)
    return canonical


def assert_materialized_heterogeneous_storage_execution(
    storage_plan: RuntimeHeterogeneousStoragePlanReport,
    materialized: RuntimeMaterializedHeterogeneousStorageExecution,
) -> RuntimeMaterializedHeterogeneousStorageExecution:
    """Bind every runtime write and release to one exact planned lifetime."""

    if not isinstance(storage_plan, RuntimeHeterogeneousStoragePlanReport):
        raise TypeError("heterogeneous materialized assertion requires storage plan")
    if not isinstance(materialized, RuntimeMaterializedHeterogeneousStorageExecution):
        raise TypeError("heterogeneous materialized assertion requires execution")
    trace = materialized.storage_trace
    expected_plan_digest = _digest(
        dump_runtime_heterogeneous_storage_plan_report(storage_plan)
    )
    if trace.source_storage_plan_digest != expected_plan_digest:
        raise ValueError("heterogeneous materialized source plan digest mismatch")
    expected_slots = tuple(_slot_materialization(item) for item in storage_plan.slots)
    if trace.slots != expected_slots:
        raise ValueError("heterogeneous materialized slots do not match plan")
    writes = {item.storage_id: item for item in trace.writes}
    releases = {item.storage_id: item for item in trace.releases}
    if set(writes) != {item.storage_id for item in storage_plan.lifetimes}:
        raise ValueError("heterogeneous materialized write set does not match plan")
    for lifetime in storage_plan.lifetimes:
        write = writes[lifetime.storage_id]
        release = releases[lifetime.storage_id]
        expected_source_storage_id: str | None = None
        if lifetime.storage_role == "layout_staging":
            expected_source_storage_id = f"storage.value.{lifetime.tensor_name}"
        elif lifetime.storage_role == "transfer_target_staging":
            layout_storage_id = (
                f"storage.layout.{lifetime.tensor_name}.{lifetime.target_operation}"
            )
            expected_source_storage_id = (
                layout_storage_id
                if layout_storage_id in writes
                else f"storage.value.{lifetime.tensor_name}"
            )
        if write.source_storage_id != expected_source_storage_id:
            raise ValueError("heterogeneous materialized source storage mismatch")
        expected_write = (
            lifetime.tensor_name,
            lifetime.storage_role,
            lifetime.slot_id,
            lifetime.first_live_event,
            lifetime.first_live_phase,
            lifetime.last_use_event,
            lifetime.last_use_phase,
            lifetime.memory_domain,
            lifetime.layout,
            lifetime.logical_shape,
            lifetime.physical_shape,
            lifetime.tile_shape,
            lifetime.physical_bytes,
            lifetime.physical_element_count * 8,
        )
        observed_write = (
            write.tensor_name,
            write.storage_role,
            write.slot_id,
            write.event_index,
            write.event_phase,
            write.last_use_event,
            write.last_use_phase,
            write.memory_domain,
            write.layout,
            write.logical_shape,
            write.physical_shape,
            write.tile_shape,
            write.planned_bytes,
            write.runtime_bytes,
        )
        if observed_write != expected_write:
            raise ValueError("heterogeneous materialized write does not match lifetime")
        if (
            release.slot_id,
            release.slot_generation,
            release.event_index,
            release.event_phase,
        ) != (
            lifetime.slot_id,
            write.slot_generation,
            lifetime.last_use_event,
            lifetime.last_use_phase,
        ):
            raise ValueError("heterogeneous materialized release does not match lifetime")
    for slot in storage_plan.slots:
        slot_writes = sorted(
            (item for item in trace.writes if item.slot_id == slot.slot_id),
            key=lambda item: item.slot_generation,
        )
        for previous, current in zip(slot_writes, slot_writes[1:], strict=False):
            previous_release = releases[previous.storage_id]
            if previous_release.event_index >= current.event_index:
                raise ValueError("heterogeneous materialized reuse precedes release")
    if len(materialized.execution.trace.layout_conversion_steps) != (
        storage_plan.planned_layout_conversion_count
    ):
        raise ValueError("heterogeneous materialized conversion count mismatch")
    if len(materialized.execution.trace.transfer_steps) != (
        storage_plan.planned_transfer_count
    ):
        raise ValueError("heterogeneous materialized transfer count mismatch")
    return materialized


def runtime_heterogeneous_storage_execution_trace_to_dict(
    trace: RuntimeHeterogeneousStorageExecutionTrace,
) -> dict[str, object]:
    """Return deterministic metadata without values, identities, or addresses."""

    if not isinstance(trace, RuntimeHeterogeneousStorageExecutionTrace):
        raise TypeError("heterogeneous storage execution trace must be trace object")
    return {
        "blocked_execution_surfaces": list(trace.blocked_execution_surfaces),
        "execution_mode": trace.execution_mode,
        "executor_contract": trace.executor_contract,
        "external_artifacts": trace.external_artifacts,
        "graph_name": trace.graph_name,
        "handle_policy": trace.handle_policy,
        "performance_claim": trace.performance_claim,
        "physical_memory_claim": trace.physical_memory_claim,
        "planned_reserved_bytes": trace.planned_reserved_bytes,
        "release_count": len(trace.releases),
        "release_policy": trace.release_policy,
        "releases": [_release_to_dict(item) for item in trace.releases],
        "retention_policy": trace.retention_policy,
        "reuse_event_count": trace.reuse_event_count,
        "runtime_reserved_bytes": trace.runtime_reserved_bytes,
        "runtime_reuse_savings_bytes": trace.runtime_reuse_savings_bytes,
        "runtime_unreused_storage_bytes": trace.runtime_unreused_storage_bytes,
        "slot_count": len(trace.slots),
        "slots": [_slot_materialization_to_dict(item) for item in trace.slots],
        "source_storage_plan_digest": trace.source_storage_plan_digest,
        "status": trace.status,
        "storage_write_count": len(trace.writes),
        "write_policy": trace.write_policy,
        "writes": [_write_to_dict(item) for item in trace.writes],
    }


def _write_record(
    lifetime: RuntimeHeterogeneousStorageLifetime,
    *,
    generation: int,
    previous_storage_id: str | None,
    source_storage_id: str | None,
    write_source: str,
) -> RuntimeHeterogeneousStorageWrite:
    return RuntimeHeterogeneousStorageWrite(
        storage_id=lifetime.storage_id,
        tensor_name=lifetime.tensor_name,
        storage_role=lifetime.storage_role,
        source_storage_id=source_storage_id,
        slot_id=lifetime.slot_id,
        slot_generation=generation,
        previous_storage_id=previous_storage_id,
        event_index=lifetime.first_live_event,
        event_phase=lifetime.first_live_phase,
        last_use_event=lifetime.last_use_event,
        last_use_phase=lifetime.last_use_phase,
        memory_domain=lifetime.memory_domain,
        layout=lifetime.layout,
        logical_shape=lifetime.logical_shape,
        physical_shape=lifetime.physical_shape,
        tile_shape=lifetime.tile_shape,
        planned_bytes=lifetime.physical_bytes,
        runtime_bytes=lifetime.physical_element_count * 8,
        write_source=write_source,
        reuse_status=(
            "first_slot_generation" if generation == 1 else "reused_after_release"
        ),
        semantic_verification="exact_logical_values",
        padding_verification=(
            "zero_padding_verified"
            if lifetime.layout is LayoutKind.BLOCKED
            else "not_applicable"
        ),
    )


def _slot_materialization(
    slot: RuntimeHeterogeneousStorageSlot,
) -> RuntimeHeterogeneousSlotMaterialization:
    return RuntimeHeterogeneousSlotMaterialization(
        slot_id=slot.slot_id,
        storage_role=slot.storage_role,
        memory_domain=slot.memory_domain,
        layout=slot.layout,
        physical_shape=slot.physical_shape,
        tile_shape=slot.tile_shape,
        planned_dtype=slot.dtype,
        runtime_dtype=RUNTIME_HETEROGENEOUS_STORAGE_INTERNAL_DTYPE,
        planned_bytes=slot.bytes_reserved,
        runtime_bytes=prod(slot.physical_shape) * 8,
        storage_count=slot.storage_count,
        allocation_kind="reused" if slot.storage_count > 1 else "exclusive",
    )


def _slot_materialization_to_dict(
    slot: RuntimeHeterogeneousSlotMaterialization,
) -> dict[str, object]:
    return {
        "allocation_kind": slot.allocation_kind,
        "handle_policy": slot.handle_policy,
        "layout": slot.layout.value,
        "memory_domain": slot.memory_domain.value,
        "physical_shape": list(slot.physical_shape),
        "planned_bytes": slot.planned_bytes,
        "planned_dtype": slot.planned_dtype,
        "runtime_bytes": slot.runtime_bytes,
        "runtime_dtype": slot.runtime_dtype,
        "slot_id": slot.slot_id,
        "status": slot.status,
        "storage_count": slot.storage_count,
        "storage_role": slot.storage_role,
        "tile_shape": list(slot.tile_shape),
    }


def _write_to_dict(write: RuntimeHeterogeneousStorageWrite) -> dict[str, object]:
    return {
        "event_index": write.event_index,
        "event_phase": write.event_phase,
        "handle_policy": write.handle_policy,
        "last_use_event": write.last_use_event,
        "last_use_phase": write.last_use_phase,
        "layout": write.layout.value,
        "logical_shape": list(write.logical_shape),
        "memory_domain": write.memory_domain.value,
        "padding_verification": write.padding_verification,
        "physical_shape": list(write.physical_shape),
        "planned_bytes": write.planned_bytes,
        "previous_storage_id": write.previous_storage_id,
        "reuse_status": write.reuse_status,
        "runtime_bytes": write.runtime_bytes,
        "semantic_verification": write.semantic_verification,
        "slot_generation": write.slot_generation,
        "slot_id": write.slot_id,
        "source_storage_id": write.source_storage_id,
        "status": write.status,
        "storage_id": write.storage_id,
        "storage_role": write.storage_role,
        "tensor_name": write.tensor_name,
        "tile_shape": list(write.tile_shape),
        "write_source": write.write_source,
    }


def _release_to_dict(
    release: RuntimeHeterogeneousStorageRelease,
) -> dict[str, object]:
    return {
        "event_index": release.event_index,
        "event_phase": release.event_phase,
        "release_verification": release.release_verification,
        "slot_generation": release.slot_generation,
        "slot_id": release.slot_id,
        "status": release.status,
        "storage_id": release.storage_id,
    }


def _write_blocked_2x2(
    storage: FloatArray,
    value: FloatArray,
    logical_shape: tuple[int, ...],
) -> None:
    rows, columns = logical_shape
    expected_shape = ((rows + 1) // 2, (columns + 1) // 2, 2, 2)
    if tuple(storage.shape) != expected_shape:
        raise ValueError("heterogeneous blocked storage shape mismatch")
    storage.fill(0.0)
    for row in range(rows):
        for column in range(columns):
            storage[row // 2, column // 2, row % 2, column % 2] = value[row, column]


def _copy_blocked_2x2_to_row_major(
    source: FloatArray,
    target: FloatArray,
    logical_shape: tuple[int, ...],
) -> None:
    rows, columns = logical_shape
    if tuple(target.shape) != logical_shape:
        raise ValueError("heterogeneous row_major staging shape mismatch")
    for row in range(rows):
        for column in range(columns):
            target[row, column] = source[
                row // 2,
                column // 2,
                row % 2,
                column % 2,
            ]


def _assert_blocked_2x2_equals(
    storage: FloatArray,
    logical: FloatArray,
    logical_shape: tuple[int, ...],
) -> None:
    rows, columns = logical_shape
    for row in range(rows):
        for column in range(columns):
            if storage[row // 2, column // 2, row % 2, column % 2] != logical[
                row,
                column,
            ]:
                raise ValueError("heterogeneous blocked logical value mismatch")
    for tile_row in range(storage.shape[0]):
        for tile_column in range(storage.shape[1]):
            for inner_row in range(2):
                for inner_column in range(2):
                    row = tile_row * 2 + inner_row
                    column = tile_column * 2 + inner_column
                    if (row >= rows or column >= columns) and storage[
                        tile_row,
                        tile_column,
                        inner_row,
                        inner_column,
                    ] != 0.0:
                        raise ValueError("heterogeneous blocked padding is not zero")


def _validate_consumer_storage(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    storage_plan: RuntimeHeterogeneousStoragePlanReport,
) -> None:
    producers = _produced_tensors(graph)[1]
    lifetimes = {item.storage_id: item for item in storage_plan.lifetimes}
    conversion_keys = {
        (item.tensor_name, item.source_operation, item.target_operation)
        for item in partition_plan.layout_conversions
        if item.source_operation is not None
    }
    transfer_keys = {
        (item.tensor_name, item.source_operation, item.target_operation)
        for item in partition_plan.transfer_edges
    }
    for operation in graph.operations:
        for tensor in operation.inputs:
            producer = producers.get(tensor.name)
            if producer is None:
                continue
            key = (tensor.name, producer, operation.name)
            if key in transfer_keys:
                storage_id = f"storage.transfer.{tensor.name}.{operation.name}"
            elif key in conversion_keys:
                storage_id = f"storage.layout.{tensor.name}.{operation.name}"
            else:
                storage_id = f"storage.value.{tensor.name}"
            if lifetimes[storage_id].layout is not LayoutKind.ROW_MAJOR:
                raise ValueError("heterogeneous trusted consumer requires row_major input")
    for tensor_name in _terminal_output_names(graph):
        if lifetimes[f"storage.value.{tensor_name}"].layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("heterogeneous terminal output requires row_major storage")


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


def _produced_tensors(
    graph: ComputeGraph,
) -> tuple[dict[str, TensorRef], dict[str, str]]:
    tensors: dict[str, TensorRef] = {}
    producers: dict[str, str] = {}
    for operation in graph.operations:
        for tensor in operation.outputs:
            tensors[tensor.name] = tensor
            producers[tensor.name] = operation.name
    return tensors, producers


def _preflight_inputs(
    external_tensors: Mapping[str, TensorRef],
    inputs: Mapping[str, object],
) -> dict[str, FloatArray]:
    if type(inputs) is not dict:
        raise TypeError("heterogeneous storage inputs must be a plain dict")
    missing = sorted(set(external_tensors) - set(inputs))
    extra = sorted(set(inputs) - set(external_tensors))
    if missing:
        raise ValueError(f"heterogeneous storage missing inputs: {','.join(missing)}")
    if extra:
        raise ValueError(f"heterogeneous storage unexpected inputs: {','.join(extra)}")
    validated: dict[str, FloatArray] = {}
    total_bytes = 0
    for name, tensor in external_tensors.items():
        value = inputs[name]
        if not isinstance(value, np.ndarray):
            raise TypeError(f"heterogeneous storage input {name} must be NumPy array")
        if value.dtype != np.dtype(np.float64):
            raise TypeError(f"heterogeneous storage input {name} dtype must be float64")
        if tuple(value.shape) != tensor.shape:
            raise ValueError(f"heterogeneous storage input {name} shape mismatch")
        if value.size > MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS:
            raise ValueError(f"heterogeneous storage input {name} exceeds element limit")
        if not bool(np.all(np.isfinite(value))):
            raise ValueError(f"heterogeneous storage input {name} must be finite")
        total_bytes += int(value.nbytes)
        validated[name] = value
    if total_bytes > MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_INPUT_BYTES:
        raise ValueError("heterogeneous storage input byte limit exceeded")
    return validated


def _conversions_by_target(
    partition_plan: PartitionPlan,
) -> dict[str, tuple[LayoutConversionCost, ...]]:
    grouped: dict[str, list[LayoutConversionCost]] = {}
    for item in partition_plan.layout_conversions:
        grouped.setdefault(item.target_operation, []).append(item)
    return {key: tuple(value) for key, value in grouped.items()}


def _transfers_by_target(
    partition_plan: PartitionPlan,
) -> dict[str, tuple[RuntimeTransferEdge, ...]]:
    grouped: dict[str, list[RuntimeTransferEdge]] = {}
    for item in partition_plan.transfer_edges:
        grouped.setdefault(item.target_operation, []).append(item)
    return {key: tuple(value) for key, value in grouped.items()}


def _terminal_output_names(graph: ComputeGraph) -> tuple[str, ...]:
    consumed = {
        tensor.name for operation in graph.operations for tensor in operation.inputs
    }
    return tuple(
        tensor.name
        for operation in graph.operations
        for tensor in operation.outputs
        if tensor.name not in consumed
    )


def _validate_kernel_result(
    operation: ComputeOperation,
    value: object,
) -> None:
    if len(operation.outputs) != 1:
        raise ValueError("heterogeneous storage executor supports one output")
    output = operation.outputs[0]
    if not isinstance(value, np.ndarray):
        raise TypeError("heterogeneous storage kernel result must be NumPy array")
    if value.dtype != np.dtype(np.float64):
        raise TypeError("heterogeneous storage kernel result must be float64")
    if tuple(value.shape) != output.shape:
        raise ValueError("heterogeneous storage kernel result shape mismatch")
    if value.size > MAX_RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_ELEMENTS:
        raise ValueError("heterogeneous storage kernel result exceeds element limit")
    if not bool(np.all(np.isfinite(value))):
        raise ValueError("heterogeneous storage kernel result must be finite")


def _validate_runtime_value(
    value: object,
    shape: tuple[int, ...],
) -> None:
    if not isinstance(value, np.ndarray):
        raise TypeError("heterogeneous materialized value must be NumPy array")
    if value.dtype != np.dtype(np.float64):
        raise TypeError("heterogeneous materialized value must be float64")
    if tuple(value.shape) != shape:
        raise ValueError("heterogeneous materialized value shape mismatch")
    if not bool(np.all(np.isfinite(value))):
        raise ValueError("heterogeneous materialized value must be finite")


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
        input_tensors=tuple(item.name for item in operation.inputs),
        output_tensors=tuple(item.name for item in operation.outputs),
        output_shapes=(tuple(int(item) for item in value.shape),),
        output_dtypes=(str(value.dtype),),
    )


def _require_safe_text(value: str, label: str) -> None:
    if not isinstance(value, str) or _SAFE_TEXT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a safe identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds metadata byte limit")


def _require_digest(value: str) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError("heterogeneous storage metadata digest is invalid")


def _require_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise TypeError(f"{label} must be a non-empty tuple")
    for dimension in value:
        _require_positive_int(dimension, f"{label} dimension")


def _require_tile_shape(value: tuple[int, ...], layout: LayoutKind) -> None:
    if type(value) is not tuple:
        raise TypeError("tile_shape must be a tuple")
    expected = (
        RUNTIME_HETEROGENEOUS_STORAGE_BLOCK_TILE_SHAPE
        if layout is LayoutKind.BLOCKED
        else ()
    )
    if value != expected:
        raise ValueError("heterogeneous materialized tile shape mismatch")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _digest(encoded)


def _digest(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_BYTES",
    "MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_FIELD_BYTES",
    "MAX_RUNTIME_MATERIALIZED_HETEROGENEOUS_INPUT_BYTES",
    "RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_MODE",
    "RUNTIME_HETEROGENEOUS_STORAGE_EXECUTION_STATUS",
    "RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_BLOCKED_EXECUTION_SURFACES",
    "RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT",
    "RUNTIME_HETEROGENEOUS_STORAGE_EXTERNAL_ARTIFACTS",
    "RUNTIME_HETEROGENEOUS_STORAGE_HANDLE_POLICY",
    "RUNTIME_HETEROGENEOUS_STORAGE_INTERNAL_DTYPE",
    "RUNTIME_HETEROGENEOUS_STORAGE_PERFORMANCE_CLAIM",
    "RUNTIME_HETEROGENEOUS_STORAGE_PHYSICAL_MEMORY_CLAIM",
    "RUNTIME_HETEROGENEOUS_STORAGE_PLANNED_DTYPE",
    "RUNTIME_HETEROGENEOUS_STORAGE_RELEASE_POLICY",
    "RUNTIME_HETEROGENEOUS_STORAGE_RETENTION_POLICY",
    "RUNTIME_HETEROGENEOUS_STORAGE_WRITE_POLICY",
    "RuntimeHeterogeneousSlotMaterialization",
    "RuntimeHeterogeneousStorageExecutionTrace",
    "RuntimeHeterogeneousStorageRelease",
    "RuntimeHeterogeneousStorageWrite",
    "RuntimeMaterializedHeterogeneousStorageExecution",
    "assert_materializable_heterogeneous_storage_execution",
    "assert_materialized_heterogeneous_storage_execution",
    "execute_graph_with_materialized_heterogeneous_storage",
    "runtime_heterogeneous_storage_execution_trace_to_dict",
]
