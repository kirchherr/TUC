"""Proof that TUC can target a second accelerator simulator safely."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc.backends import SystolicArraySimulatorBackend
from tuc.compiler import compile_graph
from tuc.compiler.pipeline import CompilationResult
from tuc.ir import ComputeGraph, ComputeOperation, IRStage, OperationKind, TensorRef
from tuc.proof import ProofReportMetadata, proof_metadata_from_partition_plan
from tuc.reference import reference_elementwise, reference_matmul
from tuc.runtime import (
    RuntimeExecutionReadinessReport,
    RuntimeExecutionResult,
    execute_graph,
    runtime_execution_readiness_report,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ProofOfSystolicExecutionReport:
    """Deterministic proof artifact for the systolic simulator slice."""

    graph: ComputeGraph
    metadata: ProofReportMetadata
    compiled: CompilationResult
    readiness: RuntimeExecutionReadinessReport
    execution: RuntimeExecutionResult
    result: FloatArray
    reference: FloatArray
    passed: bool


def build_graph() -> ComputeGraph:
    """Build a small compute-intent graph for systolic placement."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 2))
    projection = TensorRef("projection", (2, 2))
    activated = TensorRef("activated", (2, 2))
    return ComputeGraph(
        name="proof_of_systolic_execution",
        operations=(
            ComputeOperation(
                name="systolic_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
            ),
            ComputeOperation(
                name="host_activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection,),
                outputs=(activated,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite proof inputs."""

    return {
        "lhs": np.array([[1.0, 2.0, -1.0], [3.0, -2.0, 0.5]], dtype=np.float64),
        "rhs": np.array([[2.0, -1.0], [0.5, 1.0], [4.0, -3.0]], dtype=np.float64),
    }


def reference_result(inputs: dict[str, FloatArray]) -> FloatArray:
    """Return the independent reference result for the proof graph."""

    return reference_elementwise(reference_matmul(inputs["lhs"], inputs["rhs"]), "relu")


def run_proof() -> ProofOfSystolicExecutionReport:
    """Run the systolic simulator proof and return a stable report object."""

    graph = build_graph()
    inputs = proof_inputs()
    simulator = SystolicArraySimulatorBackend()
    compiled = compile_graph(graph, [simulator.capability])
    metadata = proof_metadata_from_partition_plan(
        proof_id="proof_of_systolic_execution",
        proof_version="alpha.v1",
        graph_family="systolic_execution",
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
    return ProofOfSystolicExecutionReport(
        graph=graph,
        metadata=metadata,
        compiled=compiled,
        readiness=readiness,
        execution=execution,
        result=result,
        reference=expected,
        passed=passed,
    )


def render_proof_report(report: ProofOfSystolicExecutionReport) -> str:
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
    lines.append("== backend assignments ==")
    for assignment in report.compiled.partition_plan.assignments:
        lines.append(f"{assignment.operation_name} -> {assignment.backend_name}")

    lines.append("")
    lines.append("== transfer plan ==")
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
