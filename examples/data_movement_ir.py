"""Inspect data-movement metadata carried from HAC-IR into HS-IR."""

from __future__ import annotations

from tuc import CompilationHints, ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph


def build_graph() -> ComputeGraph:
    hints = CompilationHints(
        prefer_analog_linear=True,
        max_error_budget=0.02,
    )
    a = TensorRef("a", (64, 128))
    b = TensorRef("b", (128, 32))
    c = TensorRef("c", (64, 32))
    y = TensorRef("y", (64, 32))

    return ComputeGraph(
        name="movement_aware_mlp",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes=hints.to_metadata(),
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )


def main() -> None:
    result = compile_graph(build_graph(), [LinearAlgebraSimulatorBackend().capability])

    print("== movement summary ==")
    for key, value in sorted(result.hs_ir.graph.metadata["movement_summary"].items()):
        print(f"{key}: {value}")

    print("\n== hs-ir ==")
    print(result.dump(result.hs_ir.stage))


if __name__ == "__main__":
    main()
