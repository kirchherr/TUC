"""Compile a small Triton-like metadata graph through the TUC pipeline."""

from __future__ import annotations

from tuc import TritonKernelMetadata
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph


def build_metadata() -> TritonKernelMetadata:
    return TritonKernelMetadata.from_mapping(
        {
            "name": "triton_metadata_mlp",
            "tensors": [
                {"name": "a", "shape": [32, 64], "dtype": "float32"},
                {"name": "b", "shape": [64, 16], "dtype": "float32"},
                {"name": "c", "shape": [32, 16], "dtype": "float32"},
                {"name": "y", "shape": [32, 16], "dtype": "float32"},
            ],
            "operations": [
                {
                    "name": "projection",
                    "kind": "matmul",
                    "inputs": ["a", "b"],
                    "outputs": ["c"],
                    "hints": {
                        "prefer_linear_accelerator": True,
                        "max_error_budget": 0.02,
                    },
                },
                {
                    "name": "activation",
                    "kind": "elementwise",
                    "inputs": ["c"],
                    "outputs": ["y"],
                    "attributes": {"semantic": "gelu_approx"},
                },
            ],
            "schema_version": "triton_metadata.v0",
            "metadata": {"frontend.source": "triton-like-metadata"},
        }
    )


def main() -> None:
    graph = build_metadata().to_compute_graph()
    result = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])

    print("== graph ==")
    print(graph.name)
    print(", ".join(graph.operation_names()))

    print("\n== intake report ==")
    print(build_metadata().intake_report().dump())

    print("\n== runtime plan ==")
    print(result.dump_runtime_plan())


if __name__ == "__main__":
    main()
