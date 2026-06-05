from __future__ import annotations

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime import partition_graph


def test_partitioning_prefers_linear_simulator_for_matmul() -> None:
    a = TensorRef("a", (16, 16))
    b = TensorRef("b", (16, 16))
    c = TensorRef("c", (16, 16))
    y = TensorRef("y", (16, 16))
    graph = ComputeGraph(
        name="demo",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.01},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )

    simulator = LinearAlgebraSimulatorBackend()
    plan = partition_graph(graph, [simulator.capability])

    assert plan.backend_for("projection") == "linear-sim"
    assert plan.backend_for("activation") == "gpu"
    assert plan.assignments[0].memory_domain is MemoryDomainKind.ANALOG_WEIGHT_BANK
    assert plan.assignments[1].transfer_bytes == 16 * 16 * 4
    assert plan.total_transfer_bytes() == 16 * 16 * 4
    assert len(plan.transfer_edges) == 1
    edge = plan.transfer_edges[0]
    assert edge.tensor_name == "c"
    assert edge.source_operation == "projection"
    assert edge.target_operation == "activation"
    assert edge.source_domain is MemoryDomainKind.ANALOG_WEIGHT_BANK
    assert edge.target_domain is MemoryDomainKind.GPU_HBM
    assert plan.total_data_movement_bytes() == 16 * 16 * 4


def test_partitioning_selects_supported_backend_with_lower_transfer_cost() -> None:
    x = TensorRef("x", (8, 8))
    y = TensorRef("y", (8, 8))
    z = TensorRef("z", (8, 8))
    graph = ComputeGraph(
        name="transfer_aware",
        operations=(
            ComputeOperation(
                name="first",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(y,),
            ),
            ComputeOperation(
                name="second",
                kind=OperationKind.ELEMENTWISE,
                inputs=(y,),
                outputs=(z,),
            ),
        ),
    )
    gpu_backend = BackendCapability(
        name="gpu",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )
    sram_backend = BackendCapability(
        name="sram",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.DEVICE_SRAM,
    )

    plan = partition_graph(graph, [gpu_backend, sram_backend])

    assert plan.backend_for("first") == "gpu"
    assert plan.backend_for("second") == "gpu"
    assert plan.total_transfer_bytes() == 0


def test_partitioning_records_layout_conversion_costs() -> None:
    x = TensorRef("x", (8, 8))
    y = TensorRef("y", (8, 8))
    z = TensorRef("z", (8, 8))
    graph = ComputeGraph(
        name="layout_aware",
        operations=(
            ComputeOperation(
                name="first",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(y,),
            ),
            ComputeOperation(
                name="second",
                kind=OperationKind.ELEMENTWISE,
                inputs=(y,),
                outputs=(z,),
                attributes={"tuc.layout": LayoutKind.BLOCKED.value},
            ),
        ),
    )
    gpu_backend = BackendCapability(
        name="gpu",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )

    plan = partition_graph(graph, [gpu_backend])

    assert plan.total_transfer_bytes() == 0
    assert plan.total_layout_conversion_bytes() == 8 * 8 * 4
    assert plan.total_data_movement_bytes() == 8 * 8 * 4
    assert len(plan.layout_conversions) == 1
    conversion = plan.layout_conversions[0]
    assert conversion.tensor_name == "y"
    assert conversion.source_layout is LayoutKind.ROW_MAJOR
    assert conversion.target_layout is LayoutKind.BLOCKED


def test_partitioning_rejects_invalid_operation_layout() -> None:
    graph = ComputeGraph(
        name="bad_layout",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (8, 8)),),
                outputs=(TensorRef("y", (8, 8)),),
                attributes={"tuc.layout": "surprise"},
            ),
        ),
    )
    gpu_backend = BackendCapability(
        name="gpu",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )

    with pytest.raises(ValueError, match="unsupported operation layout"):
        partition_graph(graph, [gpu_backend])
