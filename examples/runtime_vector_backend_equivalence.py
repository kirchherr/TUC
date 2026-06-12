"""Emit metadata-only equivalence evidence for the vector simulator placement."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from tuc import (
    ComputeGraph,
    ComputeOperation,
    OperationKind,
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
    """Build one vector-oriented neutral compute-intent graph."""

    logits = TensorRef("logits", (2, 3))
    weights = TensorRef("weights", (2, 3))
    row_sum = TensorRef("row_sum", (2,))
    activated = TensorRef("activated", (2,))
    return ComputeGraph(
        name="runtime_vector_backend_equivalence",
        operations=(
            ComputeOperation(
                name="normalize",
                kind=OperationKind.SOFTMAX,
                inputs=(logits,),
                outputs=(weights,),
                attributes={"axis": 1},
            ),
            ComputeOperation(
                name="sum_rows",
                kind=OperationKind.REDUCTION,
                inputs=(weights,),
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
        "logits": np.array(
            [[1.0, 2.0, 0.5], [0.25, -1.0, 3.0]],
            dtype=np.float64,
        ),
    }


def build_vector_backend_equivalence_report() -> RuntimeBackendEquivalenceReport:
    """Compile and execute the vector graph under two placement choices."""

    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, [])
    candidate = compile_graph(graph, [VectorSimulatorBackend().capability])
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
        candidate_run_id="vector_sim",
    )


def build_report() -> str:
    """Return the stable serialized backend equivalence report."""

    return dump_runtime_backend_equivalence_report(
        build_vector_backend_equivalence_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
