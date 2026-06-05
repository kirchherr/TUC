"""Backend contracts for TUC prototype backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind


@dataclass(frozen=True)
class BackendCapability:
    """Describes what a backend can accept during Phase 0 partitioning."""

    name: str
    supported_ops: frozenset[OperationKind]
    supports_noise_model: bool = False
    supports_calibration: bool = False
    preferred_for: frozenset[OperationKind] = field(default_factory=frozenset)
    max_error_budget: float | None = None

    def supports(self, operation: ComputeOperation) -> bool:
        if operation.kind not in self.supported_ops:
            return False
        if self.max_error_budget is None:
            return True
        requested_budget = operation.attributes.get("max_error_budget")
        return requested_budget is None or float(requested_budget) <= self.max_error_budget


@dataclass(frozen=True)
class LoweringResult:
    """Result produced by a backend lowering pass."""

    backend_name: str
    graph_name: str
    artifact: str
    diagnostics: tuple[str, ...] = ()


class Backend(Protocol):
    """Minimal backend protocol for early TUC experiments."""

    @property
    def capability(self) -> BackendCapability:
        """Return static backend capabilities."""

    def lower(self, graph: ComputeGraph) -> LoweringResult:
        """Lower a compute graph into backend-specific code or configuration."""
