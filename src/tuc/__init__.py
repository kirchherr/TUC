"""TUC, the experimental Triton Universal Compiler prototype."""

from tuc.frontend.hints import CompilationHints
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef

__all__ = [
    "CompilationHints",
    "ComputeGraph",
    "ComputeOperation",
    "OperationKind",
    "TensorRef",
]
