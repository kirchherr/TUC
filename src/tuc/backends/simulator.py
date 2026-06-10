"""Reference simulator backend for Phase 0 experiments."""

from __future__ import annotations

from tuc.backends.base import BackendCapability, LoweringResult
from tuc.ir.memory import LayoutKind, MemoryDomainKind
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
            memory_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
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


class SystolicArraySimulatorBackend:
    """Toy digital accelerator backend for rank-2 matrix multiplication."""

    def __init__(self, name: str = "systolic-sim") -> None:
        self._capability = BackendCapability(
            name=name,
            supported_ops=frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
            memory_domain=MemoryDomainKind.DEVICE_SRAM,
            supported_layouts=frozenset({LayoutKind.ROW_MAJOR}),
            produced_layouts=frozenset({LayoutKind.BLOCKED}),
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
            lines.append(
                f"systolic_tile {operation.kind.value} {operation.name}: "
                f"({inputs}) -> ({outputs})"
            )

        diagnostics = (
            "array_topology=2d_systolic",
            "external_artifacts=forbidden",
        )
        return LoweringResult(
            backend_name=self.capability.name,
            graph_name=graph.name,
            artifact="\n".join(lines),
            diagnostics=diagnostics,
        )
