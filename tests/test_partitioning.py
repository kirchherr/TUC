from __future__ import annotations

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
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
