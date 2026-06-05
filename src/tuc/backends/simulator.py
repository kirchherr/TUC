"""Reference simulator backend for Phase 0 experiments."""

from __future__ import annotations

from tuc.backends.base import BackendCapability, LoweringResult
from tuc.ir.model import ComputeGraph, OperationKind


class LinearAlgebraSimulatorBackend:
    """Toy backend that accepts linear algebra oriented HAC-IR operations."""

    def __init__(self, name: str = "linear-sim") -> None:
        self._capability = BackendCapability(
            name=name,
            supported_ops=frozenset({OperationKind.MATMUL, OperationKind.REDUCTION}),
            supports_noise_model=True,
            supports_calibration=True,
            preferred_for=frozenset({OperationKind.MATMUL}),
            max_error_budget=0.05,
        )

    @property
    def capability(self) -> BackendCapability:
        return self._capability

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        unsupported = [
            operation.name
            for operation in graph.operations
            if not self.capability.supports(operation)
        ]
        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(f"Backend {self.capability.name!r} cannot lower: {names}")

        lines = [f"# backend: {self.capability.name}", f"# graph: {graph.name}"]
        for operation in graph.operations:
            inputs = ", ".join(tensor.name for tensor in operation.inputs)
            outputs = ", ".join(tensor.name for tensor in operation.outputs)
            lines.append(f"{operation.kind.value} {operation.name}: ({inputs}) -> ({outputs})")

        diagnostics = (
            "noise_model=enabled",
            "calibration=required",
        )
        return LoweringResult(
            backend_name=self.capability.name,
            graph_name=graph.name,
            artifact="\n".join(lines),
            diagnostics=diagnostics,
        )
