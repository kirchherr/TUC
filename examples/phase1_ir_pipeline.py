"""Run a graph through the Phase 1 TLIR -> HAC-IR -> HS-IR skeleton."""

from __future__ import annotations

from tuc import CompilationHints, ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph


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
    result = compile_graph(build_graph(), [simulator.capability])

    for stage, dump in result.dumps().items():
        print(f"\n== {stage} ==")
        print(dump)


if __name__ == "__main__":
    main()
