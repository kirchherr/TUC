"""Emit a diagnostic planner-overhead report for the Phase 1 example graph."""

from tuc import CompilationHints, ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.benchmarks import dump_planner_overhead_report, measure_pipeline_planner_overhead


def build_graph() -> ComputeGraph:
    hints = CompilationHints(
        robust_to_noise=True,
        prefer_linear_accelerator=True,
        max_error_budget=0.02,
    )
    a = TensorRef("a", (128, 256))
    b = TensorRef("b", (256, 64))
    c = TensorRef("c", (128, 64))
    y = TensorRef("y", (128, 64))

    return ComputeGraph(
        name="phase1_mlp_block",
        operations=(
            ComputeOperation(
                name="dense_projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes=hints.to_metadata(),
            ),
            ComputeOperation(
                name="gelu_approx",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )


def main() -> None:
    simulator = LinearAlgebraSimulatorBackend()
    measurement = measure_pipeline_planner_overhead(
        build_graph(),
        [simulator.capability],
    )
    print(dump_planner_overhead_report(measurement.report), end="")


if __name__ == "__main__":
    main()
