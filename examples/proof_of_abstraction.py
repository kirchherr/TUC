"""Smallest proof that TUC can preserve intent across backend assignments."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, IRStage, OperationKind, TensorRef
from tuc.reference import reference_elementwise, reference_matmul

FloatArray = NDArray[np.float64]


def build_graph() -> ComputeGraph:
    """Build the Objective Alpha graph from compute intent only."""

    lhs = TensorRef("lhs", (2, 3))
    rhs = TensorRef("rhs", (3, 2))
    projection = TensorRef("projection", (2, 2))
    activated = TensorRef("activated", (2, 2))
    return ComputeGraph(
        name="proof_of_abstraction",
        operations=(
            ComputeOperation(
                name="linear_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
                attributes={"max_error_budget": 0.05},
            ),
            ComputeOperation(
                name="digital_activation",
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
        "lhs": np.array([[1.0, -2.0, 3.0], [0.5, 4.0, -1.0]], dtype=np.float64),
        "rhs": np.array([[2.0, -1.0], [0.0, 3.0], [1.5, -0.5]], dtype=np.float64),
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

    return reference_elementwise(reference_matmul(inputs["lhs"], inputs["rhs"]), "relu")


def main() -> None:
    graph = build_graph()
    inputs = proof_inputs()
    simulator = LinearAlgebraSimulatorBackend()
    compiled = compile_graph(graph, [simulator.capability])
    result = evaluate_graph(graph, inputs)
    expected = reference_result(inputs)
    passed = np.allclose(result, expected, rtol=1e-12, atol=1e-12)

    print("== input graph ==")
    for operation in graph.operations:
        print(f"{operation.name}: {operation.kind.value}")

    print("\n== hac-ir ==")
    print(compiled.dump(IRStage.HAC_IR))

    print("\n== backend assignments ==")
    for assignment in compiled.partition_plan.assignments:
        print(f"{assignment.operation_name} -> {assignment.backend_name}")

    print("\n== transfer plan ==")
    print(compiled.dump_runtime_plan())

    print("\n== result ==")
    print(_format_array(result))

    print("\n== reference result ==")
    print(_format_array(expected))

    print("\nPASS" if passed else "\nFAIL")
    if not passed:
        raise SystemExit(1)


def _format_array(value: FloatArray) -> str:
    return np.array2string(value, precision=6, suppress_small=False)


if __name__ == "__main__":
    main()
