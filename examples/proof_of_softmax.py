"""Third proof that TUC can preserve nonlinear softmax intent."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.compiler.pipeline import CompilationResult
from tuc.ir import ComputeGraph, ComputeOperation, IRStage, OperationKind, TensorRef
from tuc.proof import ProofReportMetadata, proof_metadata_from_partition_plan
from tuc.reference import reference_matmul, reference_softmax
from tuc.runtime import (
    RuntimeExecutionReadinessReport,
    RuntimeExecutionResult,
    execute_graph,
    runtime_execution_readiness_report,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ProofOfSoftmaxReport:
    """Deterministic proof artifact for a nonlinear softmax graph family."""

    graph: ComputeGraph
    metadata: ProofReportMetadata
    compiled: CompilationResult
    readiness: RuntimeExecutionReadinessReport
    execution: RuntimeExecutionResult
    result: FloatArray
    reference: FloatArray
    passed: bool


def build_graph() -> ComputeGraph:
    """Build a proof graph with explicit nonlinear softmax intent."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 4))
    logits = TensorRef("logits", (2, 4))
    probabilities = TensorRef("probabilities", (2, 4))
    return ComputeGraph(
        name="proof_of_softmax",
        operations=(
            ComputeOperation(
                name="linear_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(logits,),
                attributes={"max_error_budget": 0.05, "prefer_linear_accelerator": True},
            ),
            ComputeOperation(
                name="row_softmax",
                kind=OperationKind.SOFTMAX,
                inputs=(logits,),
                outputs=(probabilities,),
                attributes={"axis": 1},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite proof inputs."""

    return {
        "lhs": np.array([[1.0, -1.0, 0.5], [0.0, 2.0, -0.5]], dtype=np.float64),
        "rhs": np.array(
            [
                [1.0, -2.0, 0.5, 3.0],
                [0.0, 1.0, -1.5, 2.0],
                [2.0, 0.5, 1.0, -1.0],
            ],
            dtype=np.float64,
        ),
    }


def evaluate_graph(graph: ComputeGraph, inputs: dict[str, FloatArray]) -> FloatArray:
    """Evaluate the proof graph with deterministic reference semantics."""

    values: dict[str, FloatArray] = dict(inputs)
    for operation in graph.operations:
        if operation.kind is OperationKind.MATMUL:
            values[operation.outputs[0].name] = reference_matmul(
                values[operation.inputs[0].name],
                values[operation.inputs[1].name],
            )
        elif operation.kind is OperationKind.SOFTMAX:
            axis = _softmax_axis(operation)
            values[operation.outputs[0].name] = reference_softmax(
                values[operation.inputs[0].name],
                axis=axis,
            )
        else:
            raise ValueError(f"unsupported proof operation: {operation.kind.value}")
    return values[graph.operations[-1].outputs[0].name]


def reference_result(inputs: dict[str, FloatArray]) -> FloatArray:
    """Return the independent reference result for the proof graph."""

    return reference_softmax(reference_matmul(inputs["lhs"], inputs["rhs"]), axis=1)


def run_proof() -> ProofOfSoftmaxReport:
    """Run the proof and return a stable report object."""

    graph = build_graph()
    inputs = proof_inputs()
    simulator = LinearAlgebraSimulatorBackend()
    compiled = compile_graph(graph, [simulator.capability])
    metadata = proof_metadata_from_partition_plan(
        proof_id="proof_of_softmax",
        proof_version="alpha.v1",
        graph_family="softmax",
        partition_plan=compiled.partition_plan,
    )
    readiness = runtime_execution_readiness_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    result = execution.output_for("probabilities")
    expected = reference_result(inputs)
    passed = np.allclose(result, expected, rtol=1e-12, atol=1e-12)
    return ProofOfSoftmaxReport(
        graph=graph,
        metadata=metadata,
        compiled=compiled,
        readiness=readiness,
        execution=execution,
        result=result,
        reference=expected,
        passed=passed,
    )


def render_proof_report(report: ProofOfSoftmaxReport) -> str:
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


def _softmax_axis(operation: ComputeOperation) -> int:
    axis = operation.attributes.get("axis")
    if not isinstance(axis, int) or isinstance(axis, bool):
        raise TypeError("softmax proof axis must be an integer")
    return axis


def _format_array(value: FloatArray) -> str:
    return np.array2string(value, precision=6, suppress_small=False)


if __name__ == "__main__":
    main()
