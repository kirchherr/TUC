from __future__ import annotations

from dataclasses import replace

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import (
    HS_IR_DIALECT_VERSION,
    HS_OPERATION_CONTRACTS,
    ComputeGraph,
    ComputeOperation,
    IRModule,
    IRStage,
    OperationKind,
    TensorRef,
    validate_hs_module_contract,
)


def _compiled_hs_module() -> IRModule:
    a = TensorRef("a", (16, 32))
    b = TensorRef("b", (32, 8))
    c = TensorRef("c", (16, 8))
    y = TensorRef("y", (16, 8))
    graph = ComputeGraph(
        name="hs_projection_graph",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.02},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )
    return compile_graph(graph, [LinearAlgebraSimulatorBackend().capability]).hs_ir


def test_hs_ir_contracts_describe_backend_specific_operation_names() -> None:
    assert HS_OPERATION_CONTRACTS[OperationKind.MATMUL].mlir_operation == "tuc_hs.matmul"
    assert (
        HS_OPERATION_CONTRACTS[OperationKind.ELEMENTWISE].mlir_operation
        == "tuc_hs.elementwise"
    )
    assert HS_OPERATION_CONTRACTS[OperationKind.REDUCTION].mlir_operation == "tuc_hs.reduction"
    assert HS_OPERATION_CONTRACTS[OperationKind.SOFTMAX].mlir_operation == "tuc_hs.softmax"


def test_compiler_outputs_hs_ir_that_satisfies_the_dialect_contract() -> None:
    hs_ir = _compiled_hs_module()

    validate_hs_module_contract(hs_ir)

    projection = hs_ir.graph.operations[0]
    assert hs_ir.metadata["dialect_version"] == HS_IR_DIALECT_VERSION
    assert projection.attributes["tuc.assigned_backend"] == "linear-sim"
    assert projection.attributes["tuc.produced_layout"] == "row_major"
    assert projection.attributes["tuc.source_stage"] == "hac-ir"


def test_hs_ir_contract_rejects_wrong_stage_target_or_dialect_version() -> None:
    hs_ir = _compiled_hs_module()

    with pytest.raises(ValueError, match="expected HS-IR module"):
        validate_hs_module_contract(replace(hs_ir, stage=IRStage.HAC_IR))

    with pytest.raises(ValueError, match="target"):
        validate_hs_module_contract(replace(hs_ir, target="gpu"))

    with pytest.raises(ValueError, match="dialect_version"):
        validate_hs_module_contract(replace(hs_ir, metadata={"dialect_version": "hs-ir.v99"}))


def test_hs_ir_contract_rejects_backend_assignment_metadata_drift() -> None:
    hs_ir = _compiled_hs_module()
    metadata = dict(hs_ir.graph.metadata)
    metadata["backend_assignments"] = {"projection": "linear-sim"}
    bad_graph = ComputeGraph(
        name=hs_ir.graph.name,
        operations=hs_ir.graph.operations,
        metadata=metadata,
    )

    with pytest.raises(ValueError, match="backend_assignments must match operations"):
        validate_hs_module_contract(replace(hs_ir, graph=bad_graph))


def test_hs_ir_contract_rejects_operation_assignment_mismatch() -> None:
    hs_ir = _compiled_hs_module()
    operation = hs_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={
            **operation.attributes,
            "tuc.assigned_backend": "gpu",
        },
    )
    bad_graph = ComputeGraph(
        name=hs_ir.graph.name,
        operations=(bad_operation, *hs_ir.graph.operations[1:]),
        metadata=hs_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="backend assignment does not match"):
        validate_hs_module_contract(replace(hs_ir, graph=bad_graph))


def test_hs_ir_contract_rejects_invalid_produced_layout() -> None:
    hs_ir = _compiled_hs_module()
    operation = hs_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={
            **operation.attributes,
            "tuc.produced_layout": "layout_from_plugin",
        },
    )
    bad_graph = ComputeGraph(
        name=hs_ir.graph.name,
        operations=(bad_operation, *hs_ir.graph.operations[1:]),
        metadata=hs_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="unsupported tuc.produced_layout"):
        validate_hs_module_contract(replace(hs_ir, graph=bad_graph))


def test_hs_ir_contract_rejects_unknown_compiler_attribute() -> None:
    hs_ir = _compiled_hs_module()
    operation = hs_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={
            **operation.attributes,
            "tuc.plugin_path": "/tmp/backend.so",
        },
    )
    bad_graph = ComputeGraph(
        name=hs_ir.graph.name,
        operations=(bad_operation, *hs_ir.graph.operations[1:]),
        metadata=hs_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="unsupported HS-IR compiler attribute"):
        validate_hs_module_contract(replace(hs_ir, graph=bad_graph))


def test_hs_ir_contract_rejects_runtime_transfer_summary_drift() -> None:
    hs_ir = _compiled_hs_module()
    metadata = dict(hs_ir.graph.metadata)
    summary = dict(metadata["runtime_transfer_summary"])
    summary["total_data_movement_bytes"] = summary["total_data_movement_bytes"] + 1
    metadata["runtime_transfer_summary"] = summary
    bad_graph = ComputeGraph(
        name=hs_ir.graph.name,
        operations=hs_ir.graph.operations,
        metadata=metadata,
    )

    with pytest.raises(ValueError, match="total_data_movement_bytes must equal"):
        validate_hs_module_contract(replace(hs_ir, graph=bad_graph))


def test_hs_ir_contract_rejects_movement_summary_operation_count_drift() -> None:
    hs_ir = _compiled_hs_module()
    metadata = dict(hs_ir.graph.metadata)
    summary = dict(metadata["movement_summary"])
    summary["operation_count"] = 99
    metadata["movement_summary"] = summary
    bad_graph = ComputeGraph(
        name=hs_ir.graph.name,
        operations=hs_ir.graph.operations,
        metadata=metadata,
    )

    with pytest.raises(ValueError, match="operation_count must match"):
        validate_hs_module_contract(replace(hs_ir, graph=bad_graph))
