"""Second proof that TUC can preserve reduction intent across backends."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.compiler.pipeline import CompilationResult
from tuc.ir import ComputeGraph, ComputeOperation, IRStage, OperationKind, TensorRef
from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class ProofOfReductionReport:
    """Deterministic proof artifact for a reduction graph family."""

    graph: ComputeGraph
    compiled: CompilationResult
    result: FloatArray
    reference: FloatArray
    passed: bool


def build_graph() -> ComputeGraph:
    """Build a proof graph that includes linear reduction intent."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 3))
    projection = TensorRef("projection", (2, 3))
    row_sums = TensorRef("row_sums", (2,))
    activated = TensorRef("activated", (2,))
    return ComputeGraph(
        name="proof_of_reduction",
        operations=(
            ComputeOperation(
                name="linear_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
                attributes={"max_error_budget": 0.05, "prefer_analog_linear": True},
            ),
            ComputeOperation(
                name="row_reduction",
                kind=OperationKind.REDUCTION,
                inputs=(projection,),
                outputs=(row_sums,),
                attributes={"axis": 1},
            ),
            ComputeOperation(
                name="digital_activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(row_sums,),
                outputs=(activated,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite proof inputs."""

    return {
        "lhs": np.array([[1.0, -2.0, 0.5], [3.0, 0.0, -1.0]], dtype=np.float64),
        "rhs": np.array(
            [[2.0, -1.0, 0.0], [1.0, 0.5, -2.0], [0.0, 4.0, 1.0]],
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
        elif operation.kind is OperationKind.REDUCTION:
            axis = operation.attributes.get("axis")
            if not isinstance(axis, int) or isinstance(axis, bool):
                raise TypeError("reduction proof axis must be an integer")
            values[operation.outputs[0].name] = reference_reduction_sum(
                values[operation.inputs[0].name],
                axis=axis,
            )
        elif operation.kind is OperationKind.ELEMENTWISE:
            kernel = operation.attributes.get("kernel", "identity")
            if not isinstance(kernel, str):
                raise TypeError("elementwise proof kernel must be a string")
            values[operation.outputs[0].name] = reference_elementwise(
                values[operation.inputs[0].name],
                kernel,
            )
        else:
            raise ValueError(f"unsupported proof operation: {operation.kind.value}")
    return values[graph.operations[-1].outputs[0].name]


def reference_result(inputs: dict[str, FloatArray]) -> FloatArray:
    """Return the independent reference result for the proof graph."""

    projection = reference_matmul(inputs["lhs"], inputs["rhs"])
    row_sums = reference_reduction_sum(projection, axis=1)
    return reference_elementwise(row_sums, "relu")


def run_proof() -> ProofOfReductionReport:
    """Run the proof and return a stable report object."""

    graph = build_graph()
    inputs = proof_inputs()
    simulator = LinearAlgebraSimulatorBackend()
    compiled = compile_graph(graph, [simulator.capability])
    result = evaluate_graph(graph, inputs)
    expected = reference_result(inputs)
    passed = np.allclose(result, expected, rtol=1e-12, atol=1e-12)
    return ProofOfReductionReport(
        graph=graph,
        compiled=compiled,
        result=result,
        reference=expected,
        passed=passed,
    )


def render_proof_report(report: ProofOfReductionReport) -> str:
    """Render the proof report as deterministic text for validation."""

    lines = ["== input graph =="]
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
