"""Proof that TUC can execute a planned graph through Runtime Executor v0."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import CompilationResult, compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, IRStage, OperationKind, TensorRef
from tuc.proof import ProofReportMetadata, proof_metadata_from_partition_plan
from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
)
from tuc.runtime import (
    RuntimeExecutionReadinessReport,
    RuntimeExecutionResult,
    execute_graph,
    runtime_execution_readiness_report,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ProofOfExecutionReport:
    """Deterministic proof artifact for Runtime Executor v0."""

    graph: ComputeGraph
    metadata: ProofReportMetadata
    compiled: CompilationResult
    readiness: RuntimeExecutionReadinessReport
    execution: RuntimeExecutionResult
    result: FloatArray
    reference: FloatArray
    passed: bool


def build_graph() -> ComputeGraph:
    """Build a graph that requires planning and trusted runtime execution."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 2))
    projection = TensorRef("projection", (2, 2))
    row_sum = TensorRef("row_sum", (2,))
    activated = TensorRef("activated", (2,))
    return ComputeGraph(
        name="proof_of_execution",
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
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(row_sum,),
                outputs=(activated,),
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


def reference_result(inputs: dict[str, FloatArray]) -> FloatArray:
    """Return an independent reference result for the execution proof graph."""

    projection = reference_matmul(inputs["lhs"], inputs["rhs"])
    row_sum = reference_reduction_sum(projection, axis=1)
    return reference_elementwise(row_sum, "relu")


def run_proof() -> ProofOfExecutionReport:
    """Compile, execute, and validate the proof graph."""

    graph = build_graph()
    inputs = proof_inputs()
    simulator = LinearAlgebraSimulatorBackend()
    compiled = compile_graph(graph, [simulator.capability])
    metadata = proof_metadata_from_partition_plan(
        proof_id="proof_of_execution",
        proof_version="alpha.execution.v0",
        graph_family="execution",
        partition_plan=compiled.partition_plan,
    )
    readiness = runtime_execution_readiness_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    result = execution.output_for("activated")
    expected = reference_result(inputs)
    passed = np.allclose(result, expected, rtol=1e-12, atol=1e-12)
    return ProofOfExecutionReport(
        graph=graph,
        metadata=metadata,
        compiled=compiled,
        readiness=readiness,
        execution=execution,
        result=result,
        reference=expected,
        passed=passed,
    )


def render_proof_report(report: ProofOfExecutionReport) -> str:
    """Render the proof report as deterministic text for validation."""

    lines = ["== proof metadata =="]
    lines.extend(report.metadata.render_lines())

    lines.append("")
    lines.append("== input graph ==")
    for operation in report.graph.operations:
        lines.append(f"{operation.name}: {operation.kind.value}")

    lines.append("")
    lines.append("== hac-ir ==")
    lines.append(report.compiled.dump(IRStage.HAC_IR))

    lines.append("")
    lines.append("== runtime plan ==")
    lines.append(report.compiled.dump_runtime_plan())

    lines.append("")
    lines.append("== execution readiness ==")
    lines.append(report.readiness.dump())

    lines.append("")
    lines.append("== execution trace ==")
    lines.append(report.execution.trace.dump())

    lines.append("")
    lines.append("== result ==")
    lines.append(_format_array(report.result))

    lines.append("")
    lines.append("== reference result ==")
    lines.append(_format_array(report.reference))

    lines.append("")
    lines.append("PASS" if report.passed else "FAIL")
    return "\n".join(lines)


def main() -> None:
    report = run_proof()
    print(render_proof_report(report))
    if not report.passed:
        raise SystemExit(1)


def _format_array(value: FloatArray) -> str:
    return np.array2string(value, precision=6, suppress_small=False)


if __name__ == "__main__":
    main()
