"""Hardware-agnostic IR model used by the Phase 0 prototype."""

from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef

__all__ = [
    "ComputeGraph",
    "ComputeOperation",
    "OperationKind",
    "TensorRef",
]
