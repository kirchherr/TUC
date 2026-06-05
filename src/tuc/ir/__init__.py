"""Hardware-agnostic IR model used by the Phase 0 prototype."""

from tuc.ir.dialect import (
    HAC_ATTRIBUTE_CONTRACTS,
    HAC_IR_DIALECT_VERSION,
    HAC_IR_MLIR_DIALECT,
    HAC_OPERATION_CONTRACTS,
    HacAttributeContract,
    HacAttributeKind,
    HacOperationContract,
    validate_hac_module_contract,
    validate_hac_operation_contract,
)
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
    "HAC_ATTRIBUTE_CONTRACTS",
    "HAC_IR_DIALECT_VERSION",
    "HAC_IR_MLIR_DIALECT",
    "HAC_OPERATION_CONTRACTS",
    "HacAttributeContract",
    "HacAttributeKind",
    "HacOperationContract",
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
    "validate_hac_module_contract",
    "validate_hac_operation_contract",
]
