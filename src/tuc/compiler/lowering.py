"""Prototype lowering passes between TUC IR stages."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind
from tuc.ir.modules import IRModule, IRStage
from tuc.runtime.partitioning import PartitionPlan

MVP_OPERATION_KINDS = frozenset(
    {
        OperationKind.MATMUL,
        OperationKind.ELEMENTWISE,
        OperationKind.REDUCTION,
        OperationKind.SOFTMAX,
    }
)


def lower_tlir_to_hac(tlir: IRModule) -> IRModule:
    """Lower Triton-like high-level intent into hardware-agnostic compute IR."""

    if tlir.stage is not IRStage.TLIR:
        raise ValueError(f"expected TLIR module, got {tlir.stage.value}")

    operations = tuple(_normalize_operation(operation) for operation in tlir.graph.operations)
    metadata = {
        **tlir.graph.metadata,
        **tlir.metadata,
        "lowered_from": tlir.stage.value,
        "mvp_operation_count": len(operations),
    }
    return IRModule(
        stage=IRStage.HAC_IR,
        graph=ComputeGraph(name=tlir.graph.name, operations=operations, metadata=metadata),
        metadata={"dialect_version": "hac-ir.v0"},
    )


def lower_hac_to_hs(hac_ir: IRModule, partition_plan: PartitionPlan) -> IRModule:
    """Specialize HAC-IR with backend assignments to form HS-IR."""

    if hac_ir.stage is not IRStage.HAC_IR:
        raise ValueError(f"expected HAC-IR module, got {hac_ir.stage.value}")

    operations = tuple(
        _attach_backend(operation, partition_plan)
        for operation in hac_ir.graph.operations
    )
    assignments = {
        assignment.operation_name: assignment.backend_name
        for assignment in partition_plan.assignments
    }
    metadata: dict[str, Any] = {
        **hac_ir.graph.metadata,
        "lowered_from": hac_ir.stage.value,
        "backend_assignments": assignments,
    }
    return IRModule(
        stage=IRStage.HS_IR,
        graph=ComputeGraph(name=hac_ir.graph.name, operations=operations, metadata=metadata),
        target="heterogeneous",
        metadata={"dialect_version": "hs-ir.v0"},
    )


def _normalize_operation(operation: ComputeOperation) -> ComputeOperation:
    if operation.kind not in MVP_OPERATION_KINDS:
        raise ValueError(f"operation {operation.kind.value!r} is outside the MVP scope")

    attributes = {
        **operation.attributes,
        "tuc.source_stage": IRStage.TLIR.value,
        "tuc.semantic_op": operation.kind.value,
        "tuc.linearity": _linearity(operation.kind),
    }
    return replace(operation, attributes=attributes)


def _attach_backend(operation: ComputeOperation, partition_plan: PartitionPlan) -> ComputeOperation:
    backend_name = partition_plan.backend_for(operation.name)
    attributes = {
        **operation.attributes,
        "tuc.assigned_backend": backend_name,
        "tuc.source_stage": IRStage.HAC_IR.value,
    }
    return replace(operation, attributes=attributes)


def _linearity(kind: OperationKind) -> str:
    if kind in {OperationKind.MATMUL, OperationKind.REDUCTION}:
        return "linear"
    return "nonlinear"
