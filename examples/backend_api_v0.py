"""Minimal backend-authoring example for TUC Backend API v0.1."""

from __future__ import annotations

from tuc.backends.base import BackendCapability, LoweringResult
from tuc.compiler import compile_graph
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef


class MinimalLinearBackend:
    """Trusted in-process prototype backend for one matmul operation family."""

    def __init__(self) -> None:
        self._capability = BackendCapability(
            name="minimal-linear",
            supported_ops=frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
            memory_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
        )

    @property
    def capability(self) -> BackendCapability:
        """Return declarative capability data without executing backend logic."""

        return self._capability

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        """Lower only operations that the declared capability accepts."""

        unsupported = [
            operation.name
            for operation in graph.operations
            if not self.capability.supports(operation)
        ]
        if unsupported:
            raise ValueError("backend cannot lower: " + ", ".join(unsupported))

        lines = [f"# backend: {self.capability.name}", f"# graph: {graph.name}"]
        for operation in graph.operations:
            inputs = ", ".join(tensor.name for tensor in operation.inputs)
            outputs = ", ".join(tensor.name for tensor in operation.outputs)
            lines.append(f"{operation.kind.value} {operation.name}: ({inputs}) -> ({outputs})")

        return LoweringResult(
            backend_name=self.capability.name,
            graph_name=graph.name,
            artifact="\n".join(lines),
            diagnostics=("lowered=prototype",),
        )


def build_graph() -> ComputeGraph:
    """Create a tiny graph with one backend-friendly op and one fallback op."""

    a = TensorRef("a", (16, 32))
    b = TensorRef("b", (32, 8))
    c = TensorRef("c", (16, 8))
    y = TensorRef("y", (16, 8))
    return ComputeGraph(
        name="backend_api_v0_demo",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )


def main() -> None:
    backend = MinimalLinearBackend()
    graph = build_graph()
    result = compile_graph(graph, [backend.capability])

    assigned_names = {
        operation.name
        for operation in result.hs_ir.graph.operations
        if operation.attributes["tuc.assigned_backend"] == backend.capability.name
    }
    backend_graph = ComputeGraph(
        name=graph.name,
        operations=tuple(
            operation
            for operation in result.hac_ir.graph.operations
            if operation.name in assigned_names
        ),
        metadata=result.hac_ir.graph.metadata,
    )
    lowered = backend.lower(backend_graph)

    print(result.dump_runtime_plan())
    print()
    print(lowered.artifact)


if __name__ == "__main__":
    main()
