"""Build data-only runtime evidence for a graph with two terminal outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc import (
    RuntimeExecutionResult,
    RuntimeOutputManifestReport,
    RuntimeReferenceCorrectnessReport,
    build_runtime_output_manifest_report,
    build_runtime_reference_correctness_report,
    compile_graph,
    runtime_output_manifest_report_to_dict,
    runtime_reference_correctness_report_to_dict,
)
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.reference import reference_elementwise, reference_matmul, reference_reduction_sum
from tuc.runtime import execute_graph

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class MultiOutputRuntimeEvidence:
    """Runtime evidence for one graph with more than one terminal output."""

    graph: ComputeGraph
    execution: RuntimeExecutionResult
    output_manifest: RuntimeOutputManifestReport
    reference_correctness: RuntimeReferenceCorrectnessReport


def build_graph() -> ComputeGraph:
    """Return a graph with one shared intermediate and two terminal outputs."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 2))
    projection = TensorRef("projection", (2, 2))
    row_sum = TensorRef("row_sum", (2,))
    positive_projection = TensorRef("positive_projection", (2, 2))
    return ComputeGraph(
        name="multi_output_execution",
        operations=(
            ComputeOperation(
                name="linear_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
                attributes={"max_error_budget": 0.05, "prefer_linear_accelerator": True},
            ),
            ComputeOperation(
                name="row_reduction",
                kind=OperationKind.REDUCTION,
                inputs=(projection,),
                outputs=(row_sum,),
                attributes={"axis": 1},
            ),
            ComputeOperation(
                name="positive_branch",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection,),
                outputs=(positive_projection,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite proof inputs."""

    return {
        "lhs": np.array([[1.0, -2.0, 0.5], [0.0, 1.5, -1.0]], dtype=np.float64),
        "rhs": np.array(
            [[1.0, -1.0], [2.0, 0.5], [-1.0, 3.0]],
            dtype=np.float64,
        ),
    }


def reference_outputs(inputs: dict[str, FloatArray]) -> dict[str, FloatArray]:
    """Return independent reference outputs for both terminal graph outputs."""

    projection = reference_matmul(inputs["lhs"], inputs["rhs"])
    return {
        "positive_projection": reference_elementwise(projection, "relu"),
        "row_sum": reference_reduction_sum(projection, axis=1),
    }


def run_evidence() -> MultiOutputRuntimeEvidence:
    """Compile, execute, and build data-only evidence for the multi-output graph."""

    graph = build_graph()
    inputs = proof_inputs()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    output_manifest = build_runtime_output_manifest_report(
        compiled.hac_ir.graph,
        execution,
    )
    reference_correctness = build_runtime_reference_correctness_report(
        compiled.hac_ir.graph,
        execution,
        reference_outputs(inputs),
    )
    return MultiOutputRuntimeEvidence(
        graph=compiled.hac_ir.graph,
        execution=execution,
        output_manifest=output_manifest,
        reference_correctness=reference_correctness,
    )


def build_report() -> str:
    """Return stable combined metadata-only evidence for this fixture."""

    evidence = run_evidence()
    report = {
        "evidence_fixture": "runtime_multi_output_evidence.v0",
        "graph_name": evidence.graph.name,
        "output_manifest": runtime_output_manifest_report_to_dict(
            evidence.output_manifest
        ),
        "reference_correctness": runtime_reference_correctness_report_to_dict(
            evidence.reference_correctness
        ),
    }
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
