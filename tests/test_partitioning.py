from __future__ import annotations

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import MemoryDomainKind
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
