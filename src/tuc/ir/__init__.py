"""Hardware-agnostic IR model used by the Phase 0 prototype."""

from tuc.ir.dump import dump_module
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.modules import IRModule, IRStage

__all__ = [
    "ComputeGraph",
    "ComputeOperation",
    "IRModule",
    "IRStage",
    "OperationKind",
    "TensorRef",
    "dump_module",
]
