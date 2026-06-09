"""Compile Triton-like metadata covering all MVP operation families."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from tuc import TritonKernelMetadata
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.compiler.pipeline import CompilationResult
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind
from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
    reference_softmax,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class TritonMvpMetadataReport:
    """Deterministic report data for the Triton MVP metadata path."""

    metadata: TritonKernelMetadata
    graph: ComputeGraph
    compiled: CompilationResult
    result: FloatArray
    reference: FloatArray
    passed: bool


def build_metadata() -> TritonKernelMetadata:
    """Return schema-versioned frontend metadata for all MVP operation families."""

    return TritonKernelMetadata.from_mapping(
        {
            "name": "triton_metadata_mvp_families",
            "tensors": [
                {"name": "q", "shape": [2, 3], "dtype": "float32"},
                {"name": "k", "shape": [3, 4], "dtype": "float32"},
                {"name": "scores", "shape": [2, 4], "dtype": "float32"},
                {"name": "weights", "shape": [2, 4], "dtype": "float32"},
                {"name": "v", "shape": [4, 3], "dtype": "float32"},
                {"name": "context", "shape": [2, 3], "dtype": "float32"},
                {"name": "summary", "shape": [2], "dtype": "float32"},
                {"name": "activated", "shape": [2], "dtype": "float32"},
            ],
            "operations": [
                {
                    "name": "score_projection",
                    "kind": "matmul",
                    "inputs": ["q", "k"],
                    "outputs": ["scores"],
                    "hints": {
                        "prefer_analog_linear": True,
                        "max_error_budget": 0.02,
                    },
                },
                {
                    "name": "attention_softmax",
                    "kind": "softmax",
                    "inputs": ["scores"],
                    "outputs": ["weights"],
                    "attributes": {"axis": 1},
                },
                {
                    "name": "value_projection",
                    "kind": "matmul",
                    "inputs": ["weights", "v"],
                    "outputs": ["context"],
                    "hints": {"prefer_analog_linear": True},
                },
                {
                    "name": "context_reduction",
                    "kind": "reduction",
                    "inputs": ["context"],
                    "outputs": ["summary"],
                    "attributes": {"axis": 1},
                },
                {
                    "name": "summary_activation",
                    "kind": "elementwise",
                    "inputs": ["summary"],
                    "outputs": ["activated"],
                    "attributes": {"kernel": "relu"},
                },
            ],
            "schema_version": "triton_metadata.v0",
            "metadata": {"frontend.source": "triton-like-mvp-metadata"},
        }
    )


def build_graph() -> ComputeGraph:
    """Return the hardware-agnostic graph built from frontend metadata."""

    return build_metadata().to_compute_graph()


def mvp_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs for the MVP metadata graph."""

    return {
        "q": np.array([[1.0, -0.5, 2.0], [0.25, 1.5, -1.0]], dtype=np.float64),
        "k": np.array(
            [
                [0.5, -1.0, 2.0, 1.0],
                [1.5, 0.0, -0.5, 2.0],
                [-1.0, 1.0, 0.25, 0.5],
            ],
            dtype=np.float64,
        ),
        "v": np.array(
            [
                [1.0, -2.0, 0.5],
                [0.5, 1.0, -1.5],
                [2.0, 0.25, 1.0],
                [-1.0, 0.75, 2.0],
            ],
            dtype=np.float64,
        ),
    }


def evaluate_graph(graph: ComputeGraph, inputs: dict[str, FloatArray]) -> FloatArray:
    """Evaluate the metadata graph with deterministic reference semantics."""

    values: dict[str, FloatArray] = dict(inputs)
    for operation in graph.operations:
        if operation.kind is OperationKind.MATMUL:
            values[operation.outputs[0].name] = reference_matmul(
                values[operation.inputs[0].name],
                values[operation.inputs[1].name],
            )
        elif operation.kind is OperationKind.SOFTMAX:
            values[operation.outputs[0].name] = reference_softmax(
                values[operation.inputs[0].name],
                axis=_axis(operation, "softmax"),
            )
        elif operation.kind is OperationKind.REDUCTION:
            values[operation.outputs[0].name] = reference_reduction_sum(
                values[operation.inputs[0].name],
                axis=_axis(operation, "reduction"),
            )
        elif operation.kind is OperationKind.ELEMENTWISE:
            kernel = operation.attributes.get("kernel", "identity")
            if not isinstance(kernel, str):
                raise TypeError("elementwise metadata kernel must be a string")
            values[operation.outputs[0].name] = reference_elementwise(
                values[operation.inputs[0].name],
                kernel,
            )
        else:
            raise ValueError(f"unsupported MVP metadata operation: {operation.kind.value}")
    return values[graph.operations[-1].outputs[0].name]


def reference_result(inputs: dict[str, FloatArray]) -> FloatArray:
    """Return an independent reference result for the MVP metadata graph."""

    scores = reference_matmul(inputs["q"], inputs["k"])
    weights = reference_softmax(scores, axis=1)
    context = reference_matmul(weights, inputs["v"])
    summary = reference_reduction_sum(context, axis=1)
    return reference_elementwise(summary, "relu")


def run_report() -> TritonMvpMetadataReport:
    """Compile and evaluate the MVP metadata graph."""

    metadata = build_metadata()
    graph = metadata.to_compute_graph()
    compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    inputs = mvp_inputs()
    result = evaluate_graph(graph, inputs)
    expected = reference_result(inputs)
    return TritonMvpMetadataReport(
        metadata=metadata,
        graph=graph,
        compiled=compiled,
        result=result,
        reference=expected,
        passed=np.allclose(result, expected, rtol=1e-12, atol=1e-12),
    )


def main() -> None:
    report = run_report()

    print("== graph ==")
    print(report.graph.name)
    print(", ".join(report.graph.operation_names()))

    print("\n== intake report ==")
    print(report.metadata.intake_report().dump())

    print("\n== runtime plan ==")
    print(report.compiled.dump_runtime_plan())

    print("\n== result ==")
    print(_format_array(report.result))

    print("\n== reference result ==")
    print(_format_array(report.reference))

    print("\nPASS" if report.passed else "\nFAIL")
    if not report.passed:
        raise SystemExit(1)


def _axis(operation: ComputeOperation, operation_label: str) -> int:
    axis = operation.attributes.get("axis")
    if not isinstance(axis, int) or isinstance(axis, bool):
        raise TypeError(f"{operation_label} metadata axis must be an integer")
    return axis


def _format_array(value: FloatArray) -> str:
    return np.array2string(value, precision=6, suppress_small=False)


if __name__ == "__main__":
    main()
