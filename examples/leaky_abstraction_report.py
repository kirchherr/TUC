"""Emit a diagnostic leaky-abstraction report for the Phase 1 example graph."""

from tuc import (
    CompilationHints,
    ComputeGraph,
    ComputeOperation,
    LeakyAbstractionFact,
    OperationKind,
    TensorRef,
    build_leaky_abstraction_report,
    compile_graph,
    dump_leaky_abstraction_report,
)
from tuc.backends import LinearAlgebraSimulatorBackend


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
    compiled = compile_graph(build_graph(), [simulator.capability])
    report = build_leaky_abstraction_report(
        compiled.hac_ir,
        performance_facts=(
            LeakyAbstractionFact(
                fact_id="matmul_tile_shape",
                correct_home="backend_implementation",
                required_for_performance=True,
            ),
            LeakyAbstractionFact(
                fact_id="transfer_latency_model",
                correct_home="runtime_plan",
                required_for_performance=True,
            ),
        ),
    )
    print(dump_leaky_abstraction_report(report), end="")


if __name__ == "__main__":
    main()
