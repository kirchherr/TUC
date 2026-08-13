"""Prove heterogeneous execution across two admitted data-only packages."""

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
from tuc.report_output import emit_public_json_report
from tuc.runtime.backend_equivalence import build_runtime_backend_equivalence_report
from tuc.runtime.backend_package_execution import (
    build_backend_package_execution_admission_report,
)
from tuc.runtime.backend_package_execution_portfolio import (
    BackendPackageExecutionPortfolioReport,
    build_backend_package_execution_portfolio_admission,
    build_backend_package_execution_portfolio_report,
    dump_backend_package_execution_portfolio_report,
    execute_backend_package_execution_portfolio,
)
from tuc.runtime.executor import execute_graph

PACKAGE_DIRECTORY = Path(__file__).with_name("backend_packages")
SYSTOLIC_PACKAGE_PATH = PACKAGE_DIRECTORY / "external_systolic.v0.json"
VECTOR_PACKAGE_PATH = PACKAGE_DIRECTORY / "external_vector.v0.json"

FloatArray = NDArray[np.float64]


def build_graph() -> ComputeGraph:
    """Build the minimal cross-package graph with an explicit layout boundary."""

    lhs = TensorRef("lhs", (2, 2), "float64")
    rhs = TensorRef("rhs", (2, 2), "float64")
    projection = TensorRef("projection", (2, 2), "float64")
    activated = TensorRef("activated", (2, 2), "float64")
    return ComputeGraph(
        name="backend_package_execution_portfolio",
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
    """Return deterministic finite inputs shared by candidate and baseline."""

    return {
        "lhs": np.array([[1.0, -2.0], [0.5, 3.0]], dtype=np.float64),
        "rhs": np.array([[2.0, 1.0], [-1.0, 0.25]], dtype=np.float64),
    }


def build_proof_report() -> BackendPackageExecutionPortfolioReport:
    """Run package validation through heterogeneous equivalence evidence."""

    packages = tuple(
        load_backend_integration_package(path)
        for path in (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH)
    )
    admissions = tuple(
        build_backend_package_execution_admission_report(
            evaluate_backend_integration_package(package)
        )
        for package in packages
    )
    portfolio = build_backend_package_execution_portfolio_admission(admissions)
    graph = build_graph()
    inputs = proof_inputs()

    source_compilation = compile_graph(
        graph,
        tuple(package.capability for package in packages),
    )
    candidate = execute_backend_package_execution_portfolio(
        source_compilation.hac_ir.graph,
        source_compilation.partition_plan,
        inputs,
        portfolio,
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
        candidate.projected_partition_plan,
        candidate.execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="admitted_package_portfolio_projection",
    )
    return build_backend_package_execution_portfolio_report(
        graph,
        candidate,
        equivalence,
    )


def build_report() -> str:
    """Return deterministic source-free portfolio proof evidence."""

    return dump_backend_package_execution_portfolio_report(build_proof_report())


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
