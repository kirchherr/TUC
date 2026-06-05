"""Hardware-agnostic IR model used by the Phase 0 prototype."""

from tuc.ir.dump import dump_module
from tuc.ir.memory import (
    LayoutConstraint,
    LayoutKind,
    MemoryDomain,
    MemoryDomainKind,
    MovementEstimate,
    TransferEdge,
    dtype_size_bytes,
)
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.modules import IRModule, IRStage

__all__ = [
    "ComputeGraph",
    "ComputeOperation",
    "IRModule",
    "IRStage",
    "LayoutConstraint",
    "LayoutKind",
    "MemoryDomain",
    "MemoryDomainKind",
    "MovementEstimate",
    "OperationKind",
    "TensorRef",
    "TransferEdge",
    "dtype_size_bytes",
    "dump_module",
]
