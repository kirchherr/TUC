"""Run a tiny Phase 0 TUC graph through partitioning and simulator lowering."""

from __future__ import annotations

from tuc import CompilationHints, ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.runtime import dump_partition_plan, partition_graph


def build_graph() -> ComputeGraph:
    hints = CompilationHints(
        robust_to_noise=True,
        prefer_analog_linear=True,
        max_error_budget=0.02,
    )
    a = TensorRef("a", (128, 256))
    b = TensorRef("b", (256, 64))
    c = TensorRef("c", (128, 64))
    y = TensorRef("y", (128, 64))

    matmul = ComputeOperation(
        name="dense_projection",
        kind=OperationKind.MATMUL,
        inputs=(a, b),
        outputs=(c,),
        attributes=hints.to_metadata(),
    )
    activation = ComputeOperation(
        name="gelu_approx",
        kind=OperationKind.ELEMENTWISE,
        inputs=(c,),
        outputs=(y,),
    )
    return ComputeGraph(name="phase0_mlp_block", operations=(matmul, activation))


def main() -> None:
    graph = build_graph()
    simulator = LinearAlgebraSimulatorBackend()
    plan = partition_graph(graph, [simulator.capability])

    print("Partition plan")
    for assignment in plan.assignments:
        print(f"- {assignment.operation_name}: {assignment.backend_name} ({assignment.reason})")
    print()
    print(dump_partition_plan(plan))
    if plan.transfer_edges:
        print()
        print("Runtime transfers")
        for edge in plan.transfer_edges:
            print(
                f"- %{edge.tensor_name}: {edge.source_backend}/{edge.source_domain.value}"
                f" -> {edge.target_backend}/{edge.target_domain.value}"
                f" ({edge.bytes_moved} bytes)"
            )

    simulator_graph = ComputeGraph(name=graph.name, operations=(graph.operations[0],))
    lowered = simulator.lower(simulator_graph)
    print()
    print("Simulator artifact")
    print(lowered.artifact)


if __name__ == "__main__":
    main()
