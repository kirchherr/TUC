"""Emit metadata-only equivalence evidence for mixed accelerator placement."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from tuc import (
    ComputeGraph,
    ComputeOperation,
    OperationKind,
    SystolicArraySimulatorBackend,
    TensorRef,
    VectorSimulatorBackend,
    build_runtime_backend_equivalence_report,
    compile_graph,
    dump_runtime_backend_equivalence_report,
    execute_graph,
)
from tuc.runtime import RuntimeBackendEquivalenceReport

FloatArray = NDArray[np.float64]


def build_graph() -> ComputeGraph:
    """Build one graph that requires two accelerator-style backend families."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 3))
    projection = TensorRef("projection", (2, 3))
    normalized = TensorRef("normalized", (2, 3))
    row_sum = TensorRef("row_sum", (2,))
    activated = TensorRef("activated", (2,))
    return ComputeGraph(
        name="runtime_mixed_backend_equivalence",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
            ),
            ComputeOperation(
                name="normalize",
                kind=OperationKind.SOFTMAX,
                inputs=(projection,),
                outputs=(normalized,),
                attributes={"axis": 1},
            ),
            ComputeOperation(
                name="sum_rows",
                kind=OperationKind.REDUCTION,
                inputs=(normalized,),
                outputs=(row_sum,),
                attributes={"axis": 1},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(row_sum,),
                outputs=(activated,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs for both backend placements."""

    return {
        "lhs": np.array(
            [[1.0, 2.0, -1.0], [0.5, -1.5, 3.0]],
            dtype=np.float64,
        ),
        "rhs": np.array(
            [[0.25, 1.0, -0.5], [2.0, -1.0, 0.75], [-1.5, 0.5, 1.25]],
            dtype=np.float64,
        ),
    }


def build_mixed_backend_equivalence_report() -> RuntimeBackendEquivalenceReport:
    """Compile and execute the same graph under two placement choices."""

    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, [])
    candidate = compile_graph(
        graph,
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    return build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        candidate_execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="mixed_accelerators",
    )


def build_report() -> str:
    """Return the stable serialized backend equivalence report."""

    return dump_runtime_backend_equivalence_report(
        build_mixed_backend_equivalence_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
