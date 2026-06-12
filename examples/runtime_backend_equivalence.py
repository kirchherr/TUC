"""Emit metadata-only equivalence evidence for two backend placements."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from tuc import (
    ComputeGraph,
    ComputeOperation,
    OperationKind,
    SystolicArraySimulatorBackend,
    TensorRef,
    build_runtime_backend_equivalence_report,
    compile_graph,
    dump_runtime_backend_equivalence_report,
    execute_graph,
)
from tuc.runtime import RuntimeBackendEquivalenceReport

FloatArray = NDArray[np.float64]


def build_graph() -> ComputeGraph:
    """Build one neutral compute-intent graph for placement equivalence."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 2))
    projection = TensorRef("projection", (2, 2))
    activated = TensorRef("activated", (2, 2))
    return ComputeGraph(
        name="runtime_backend_equivalence",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection,),
                outputs=(activated,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs for both backend placements."""

    return {
        "lhs": np.array([[1.0, 2.0, -1.0], [3.0, -2.0, 0.5]], dtype=np.float64),
        "rhs": np.array([[2.0, -1.0], [0.5, 1.0], [4.0, -3.0]], dtype=np.float64),
    }


def build_backend_equivalence_report() -> RuntimeBackendEquivalenceReport:
    """Compile and execute the same graph under two placement choices."""

    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, [])
    candidate = compile_graph(graph, [SystolicArraySimulatorBackend().capability])
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
        candidate_run_id="systolic_sim",
    )


def build_report() -> str:
    """Return the stable serialized backend equivalence report."""

    return dump_runtime_backend_equivalence_report(build_backend_equivalence_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
