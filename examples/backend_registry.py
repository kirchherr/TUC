"""Explicit backend registry example for TUC Backend API v0.1."""

from __future__ import annotations

from pathlib import Path

from tuc.backends.registry import BackendRegistry
from tuc.compiler import compile_graph
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef


def build_graph() -> ComputeGraph:
    """Create a tiny graph planned through manifest-loaded backend capabilities."""

    lhs = TensorRef("lhs", (8, 16))
    rhs = TensorRef("rhs", (16, 4))
    out = TensorRef("out", (8, 4))
    return ComputeGraph(
        name="backend_registry_demo",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(out,),
            ),
        ),
    )


def main() -> None:
    manifest_path = Path("examples/manifests/linear_sim_backend.json")
    registry = BackendRegistry.from_manifest_paths([manifest_path])
    result = compile_graph(build_graph(), registry.capabilities())

    print("registered_backends=" + ",".join(registry.names()))
    print(result.dump_runtime_plan())


if __name__ == "__main__":
    main()
