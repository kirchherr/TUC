"""TUC, the experimental Triton Universal Compiler prototype."""

from tuc.compiler import CompilationResult, CompilerPipeline, compile_graph
from tuc.frontend.hints import CompilationHints
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
    "CompilationHints",
    "CompilationResult",
    "ComputeGraph",
    "ComputeOperation",
    "CompilerPipeline",
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
    "compile_graph",
    "dtype_size_bytes",
]
