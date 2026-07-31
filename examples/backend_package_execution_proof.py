"""Execute a portable backend package through digest-bound trusted projection."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from tuc.backends.integration_package import (
    evaluate_backend_integration_package,
    load_backend_integration_package,
)
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.runtime.backend_equivalence import build_runtime_backend_equivalence_report
from tuc.runtime.backend_package_execution import (
    BackendPackageExecutionProofReport,
    build_backend_package_execution_admission_report,
    build_backend_package_execution_proof_report,
    dump_backend_package_execution_proof_report,
    execute_admitted_backend_package,
)
from tuc.runtime.executor import execute_graph

PACKAGE_PATH = (
    Path(__file__).with_name("backend_packages") / "external_vector.v0.json"
)

FloatArray = NDArray[np.float64]


def build_graph() -> ComputeGraph:
    """Build a graph split between neutral fallback and the package backend."""

    lhs = TensorRef("lhs", (2, 2), "float64")
    rhs = TensorRef("rhs", (2, 2), "float64")
    projection = TensorRef("projection", (2, 2), "float64")
    activated = TensorRef("activated", (2, 2), "float64")
    return ComputeGraph(
        name="backend_package_execution_proof",
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
    """Return deterministic finite inputs for baseline and admitted execution."""

    return {
        "lhs": np.array([[1.0, -2.0], [0.5, 3.0]], dtype=np.float64),
        "rhs": np.array([[2.0, 1.0], [-1.0, 0.25]], dtype=np.float64),
    }


def build_proof_report() -> BackendPackageExecutionProofReport:
    """Run package validation, admission, projection, execution, and equivalence."""

    package = load_backend_integration_package(PACKAGE_PATH)
    integration = evaluate_backend_integration_package(package)
    admission = build_backend_package_execution_admission_report(integration)
    graph = build_graph()
    inputs = proof_inputs()

    source_compilation = compile_graph(graph, (package.capability,))
    admitted = execute_admitted_backend_package(
        source_compilation.hac_ir.graph,
        source_compilation.partition_plan,
        inputs,
        admission,
    )
    baseline_compilation = compile_graph(graph, ())
    baseline_execution = execute_graph(
        baseline_compilation.hac_ir.graph,
        baseline_compilation.partition_plan,
        inputs,
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline_compilation.partition_plan,
        baseline_execution,
        admitted.projected_partition_plan,
        admitted.execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="admitted_package_projection",
    )
    return build_backend_package_execution_proof_report(
        graph,
        admitted,
        equivalence,
    )


def build_report() -> str:
    """Return the deterministic source-free execution proof report."""

    return dump_backend_package_execution_proof_report(build_proof_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
