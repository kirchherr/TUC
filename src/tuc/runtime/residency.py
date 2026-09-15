"""Opt-in, data-only residency scheduling around checked partition assignments."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import prod

from tuc.ir.dialect import validate_hac_operation_contract
from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, ComputeOperation, TensorRef
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.plan import RuntimeTransferEdge

MAX_RESIDENCY_OPERATIONS = 64
MAX_RESIDENCY_PORTS = 256
MAX_RESIDENCY_BUFFERS = 512
MAX_RESIDENCY_BYTES = 128 * 1024 * 1024
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


@dataclass(frozen=True)
class ResidencySpace:
    """A logical address-space identity, independent of physical RAM technology."""

    name: str
    physical_kind: MemoryDomainKind

    def __post_init__(self) -> None:
        if type(self.name) is not str or not _NAME.fullmatch(self.name):
            raise ValueError("invalid residency space name")
        if type(self.physical_kind) is not MemoryDomainKind:
            raise ValueError("invalid residency physical kind")


@dataclass(frozen=True)
class ResidencyBuffer:
    tensor: str
    space: ResidencySpace
    shape: tuple[int, ...]
    dtype: str
    bytes: int


@dataclass(frozen=True)
class ResidencyStep:
    kind: str
    operation: str
    backend: str
    inputs: tuple[int, ...]
    outputs: tuple[int, ...]


@dataclass(frozen=True)
class ResidencyPlan:
    """Immutable slots and ordered events; no allocation, handles, or costs."""

    graph_name: str
    buffers: tuple[ResidencyBuffer, ...]
    steps: tuple[ResidencyStep, ...]

    @property
    def copy_bytes(self) -> int:
        return sum(self.buffers[s.outputs[0]].bytes for s in self.steps if s.kind == "copy")


def plan_residency(
    graph: ComputeGraph,
    partition: PartitionPlan,
    backend_spaces: dict[str, ResidencySpace],
    host_space: ResidencySpace,
) -> ResidencyPlan:
    """Plan immutable row-major values, all external inputs and terminal outputs.

    Spaces are caller-reviewed logical identities, not discovered devices. This
    post-partition schedule neither changes placement nor admits native execution.
    Layout conversion, aliasing, mutation and buffer reuse are deliberately absent.
    """
    if type(graph) is not ComputeGraph or type(partition) is not PartitionPlan:
        raise ValueError("residency requires typed graph and partition")
    if type(graph.name) is not str or not _NAME.fullmatch(graph.name):
        raise ValueError("residency graph name rejected")
    if (
        type(graph.operations) is not tuple
        or not 0 < len(graph.operations) <= MAX_RESIDENCY_OPERATIONS
    ):
        raise ValueError("residency operation budget exceeded")
    ports = 0
    for op in graph.operations:
        if (
            type(op) is not ComputeOperation
            or type(op.inputs) is not tuple
            or type(op.outputs) is not tuple
        ):
            raise ValueError("residency operation rejected")
        if type(op.name) is not str or not _NAME.fullmatch(op.name):
            raise ValueError("residency operation name rejected")
        ports += len(op.inputs) + len(op.outputs)
        if ports > MAX_RESIDENCY_PORTS:
            raise ValueError("residency port budget exceeded")
        for tensor in (*op.inputs, *op.outputs):
            if (
                type(tensor) is not TensorRef
                or type(tensor.name) is not str
                or not _NAME.fullmatch(tensor.name)
                or len(tensor.dtype) > 128
            ):
                raise ValueError("residency tensor rejected")
            TensorRef(tensor.name, tensor.shape, tensor.dtype)
        validate_hac_operation_contract(op)
    ComputeGraph(graph.name, graph.operations)
    if (
        partition.graph_name != graph.name
        or type(partition.assignments) is not tuple
        or len(partition.assignments) != len(graph.operations)
        or partition.layout_conversions
    ):
        raise ValueError("residency partition mismatch or unsupported layout conversion")
    if (
        type(backend_spaces) is not dict
        or not 0 < len(backend_spaces) <= 16
        or type(host_space) is not ResidencySpace
    ):
        raise ValueError("residency space mapping rejected")
    spaces = {host_space.name: host_space.physical_kind}
    for name, space in backend_spaces.items():
        if type(name) is not str or not _NAME.fullmatch(name) or type(space) is not ResidencySpace:
            raise ValueError("residency backend space rejected")
        if space.name in spaces and spaces[space.name] != space.physical_kind:
            raise ValueError("conflicting residency space identity")
        spaces[space.name] = space.physical_kind
    for op, assignment in zip(graph.operations, partition.assignments, strict=True):
        if (
            type(assignment) is not Assignment
            or assignment.operation_name != op.name
            or type(assignment.memory_domain) is not MemoryDomainKind
            or assignment.backend_name not in backend_spaces
            or assignment.memory_domain != backend_spaces[assignment.backend_name].physical_kind
            or assignment.produced_layout is not LayoutKind.ROW_MAJOR
        ):
            raise ValueError("residency assignment mismatch")
    if set(backend_spaces) != {a.backend_name for a in partition.assignments}:
        raise ValueError("unused residency backend space")

    producers: dict[str, tuple[int, TensorRef]] = {}
    consumed: set[str] = set()
    for index, op in enumerate(graph.operations):
        consumed.update(t.name for t in op.inputs)
        for tensor in op.outputs:
            if tensor.name in producers:
                raise ValueError("residency requires single tensor producers")
            producers[tensor.name] = (index, tensor)
    # Reconcile inter-operation physical-domain edges without importing their
    # prototype cost estimates into actual copy accounting.
    expected_edges = []
    for index, op in enumerate(graph.operations):
        dst = partition.assignments[index]
        for tensor in op.inputs:
            if tensor.name not in producers:
                continue
            producer_index, _ = producers[tensor.name]
            if producer_index >= index:
                raise ValueError("residency rejects cycles, forward uses and in-place outputs")
            src = partition.assignments[producer_index]
            if src.memory_domain != dst.memory_domain:
                expected_edges.append(
                    (
                        tensor.name,
                        src.operation_name,
                        dst.operation_name,
                        src.backend_name,
                        dst.backend_name,
                        src.memory_domain,
                        dst.memory_domain,
                        LayoutKind.ROW_MAJOR,
                        LayoutKind.ROW_MAJOR,
                        prod(tensor.shape) * dtype_size_bytes(tensor.dtype),
                    )
                )
    if type(partition.transfer_edges) is not tuple or len(partition.transfer_edges) > ports:
        raise ValueError("residency transfer budget exceeded")
    actual_edges = []
    for edge in partition.transfer_edges:
        if type(edge) is not RuntimeTransferEdge:
            raise ValueError("residency transfer rejected")
        actual_edges.append(
            (
                edge.tensor_name,
                edge.source_operation,
                edge.target_operation,
                edge.source_backend,
                edge.target_backend,
                edge.source_domain,
                edge.target_domain,
                edge.source_layout,
                edge.target_layout,
                edge.bytes_moved,
            )
        )
    if actual_edges != expected_edges:
        raise ValueError("residency transfer topology mismatch")

    buffers: list[ResidencyBuffer] = []
    steps: list[ResidencyStep] = []
    resident: dict[tuple[str, str], int] = {}
    origins: dict[str, int] = {}
    reserved = 0

    def allocate(tensor: TensorRef, space: ResidencySpace) -> int:
        nonlocal reserved
        size = prod(tensor.shape) * dtype_size_bytes(tensor.dtype)
        reserved += size
        if len(buffers) >= MAX_RESIDENCY_BUFFERS or reserved > MAX_RESIDENCY_BYTES:
            raise ValueError("residency buffer budget exceeded")
        slot = len(buffers)
        buffers.append(ResidencyBuffer(tensor.name, space, tensor.shape, tensor.dtype, size))
        resident[tensor.name, space.name] = slot
        return slot

    def ensure(tensor: TensorRef, space: ResidencySpace) -> int:
        existing = resident.get((tensor.name, space.name))
        if existing is not None:
            return existing
        source = origins[tensor.name]
        target = allocate(tensor, space)
        steps.append(ResidencyStep("copy", "", "", (source,), (target,)))
        return target

    for op, assignment in zip(graph.operations, partition.assignments, strict=True):
        space = backend_spaces[assignment.backend_name]
        inputs = []
        for tensor in op.inputs:
            if tensor.name not in origins:
                slot = allocate(tensor, host_space)
                origins[tensor.name] = slot
                steps.append(ResidencyStep("bind_input", "", "", (), (slot,)))
            inputs.append(ensure(tensor, space))
        outputs = []
        for tensor in op.outputs:
            slot = allocate(tensor, space)
            origins[tensor.name] = slot
            outputs.append(slot)
        steps.append(
            ResidencyStep(
                "execute", op.name, assignment.backend_name, tuple(inputs), tuple(outputs)
            )
        )
    for name, (_, tensor) in producers.items():
        if name not in consumed:
            slot = ensure(tensor, host_space)
            steps.append(ResidencyStep("publish_output", "", "", (slot,), ()))
    return ResidencyPlan(graph.name, tuple(buffers), tuple(steps))
