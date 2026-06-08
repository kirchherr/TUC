from __future__ import annotations

from dataclasses import replace

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import (
    HAC_IR_DIALECT_VERSION,
    HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES,
    HAC_OPERATION_CONTRACTS,
    ComputeGraph,
    ComputeOperation,
    IRModule,
    IRStage,
    OperationKind,
    TensorRef,
    validate_hac_module_contract,
)


def _compiled_hac_module() -> IRModule:
    a = TensorRef("a", (16, 32))
    b = TensorRef("b", (32, 8))
    c = TensorRef("c", (16, 8))
    graph = ComputeGraph(
        name="projection_graph",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.02},
            ),
        ),
    )
    return compile_graph(graph, [LinearAlgebraSimulatorBackend().capability]).hac_ir


def test_hac_ir_contracts_describe_the_mvp_mlir_operation_names() -> None:
    assert HAC_OPERATION_CONTRACTS[OperationKind.MATMUL].mlir_operation == "tuc_hac.matmul"
    assert (
        HAC_OPERATION_CONTRACTS[OperationKind.ELEMENTWISE].mlir_operation
        == "tuc_hac.elementwise"
    )
    assert HAC_OPERATION_CONTRACTS[OperationKind.REDUCTION].mlir_operation == "tuc_hac.reduction"
    assert HAC_OPERATION_CONTRACTS[OperationKind.SOFTMAX].mlir_operation == "tuc_hac.softmax"


def test_compiler_outputs_hac_ir_that_satisfies_the_dialect_contract() -> None:
    hac_ir = _compiled_hac_module()

    validate_hac_module_contract(hac_ir)

    assert hac_ir.metadata["dialect_version"] == HAC_IR_DIALECT_VERSION
    assert hac_ir.graph.operations[0].attributes["tuc.semantic_op"] == "matmul"
    assert hac_ir.graph.operations[0].attributes["tuc.linearity"] == "linear"


def test_hac_ir_contract_rejects_wrong_stage_or_dialect_version() -> None:
    hac_ir = _compiled_hac_module()

    with pytest.raises(ValueError, match="expected HAC-IR module"):
        validate_hac_module_contract(replace(hac_ir, stage=IRStage.TLIR))

    with pytest.raises(ValueError, match="dialect_version"):
        validate_hac_module_contract(replace(hac_ir, metadata={"dialect_version": "hac-ir.v99"}))


def test_hac_ir_contract_rejects_unknown_compiler_attribute() -> None:
    hac_ir = _compiled_hac_module()
    operation = hac_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={
            **operation.attributes,
            "tuc.unreviewed_compiler_fact": True,
        },
    )
    bad_graph = ComputeGraph(
        name=hac_ir.graph.name,
        operations=(bad_operation,),
        metadata=hac_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="unsupported HAC-IR compiler attribute"):
        validate_hac_module_contract(replace(hac_ir, graph=bad_graph))


@pytest.mark.parametrize(
    "attribute_name, attribute_value",
    [
        ("tuc.assigned_backend", "gpu"),
        ("tuc.backend_binary", "kernel.cubin"),
        ("tuc.backend_config", "vendor-fast-math"),
        ("tuc.backend_kernel", "vendor_matmul"),
        ("tuc.cuda_arch", "sm_90"),
        ("tuc.cuda_device", "cuda:0"),
        ("tuc.cuda_launch_grid", (16, 16, 1)),
        ("tuc.cuda_stream", "stream0"),
        ("tuc.device_path", "/dev/nvidia0"),
        ("tuc.dynamic_library", "unexpected_backend.dll"),
        ("tuc.generated_artifact", "build/backend.o"),
        ("tuc.hip_target", "gfx942"),
        ("tuc.metal_device", "mps0"),
        ("tuc.neuromorphic_core", "core0"),
        ("tuc.photonic_mesh", "mesh0"),
        ("tuc.plugin_entrypoint", "package.module:backend"),
        ("tuc.produced_layout", "row_major"),
        ("tuc.vendor", "example-vendor"),
    ],
)
def test_hac_ir_contract_rejects_hardware_specific_leakage(
    attribute_name: str,
    attribute_value: object,
) -> None:
    hac_ir = _compiled_hac_module()
    operation = hac_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={
            **operation.attributes,
            attribute_name: attribute_value,
        },
    )
    bad_graph = ComputeGraph(
        name=hac_ir.graph.name,
        operations=(bad_operation,),
        metadata=hac_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="forbidden HAC-IR hardware attribute"):
        validate_hac_module_contract(replace(hac_ir, graph=bad_graph))


def test_hac_ir_forbidden_hardware_attributes_are_not_hac_attributes() -> None:
    hac_attributes = set(HAC_OPERATION_CONTRACTS[OperationKind.MATMUL].allowed_attributes)

    assert set(HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES).isdisjoint(hac_attributes)


def test_hac_ir_contract_rejects_invalid_operation_arity() -> None:
    hac_ir = _compiled_hac_module()
    operation = hac_ir.graph.operations[0]
    bad_operation = replace(operation, inputs=operation.inputs[:1])
    bad_graph = ComputeGraph(
        name=hac_ir.graph.name,
        operations=(bad_operation,),
        metadata=hac_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="inputs count must be between 2 and 2"):
        validate_hac_module_contract(replace(hac_ir, graph=bad_graph))


def test_hac_ir_contract_rejects_operations_over_tensor_budget() -> None:
    hac_ir = _compiled_hac_module()
    operation = hac_ir.graph.operations[0]
    input_tensors = tuple(TensorRef(f"x{i}", (4, 4)) for i in range(16))
    bad_operation = replace(
        operation,
        kind=OperationKind.ELEMENTWISE,
        inputs=input_tensors,
        outputs=(TensorRef("y", (4, 4)),),
        attributes={
            **operation.attributes,
            "tuc.linearity": "nonlinear",
            "tuc.semantic_op": "elementwise",
        },
    )
    bad_graph = ComputeGraph(
        name=hac_ir.graph.name,
        operations=(bad_operation,),
        metadata=hac_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="total tensor count must be between 2 and 16"):
        validate_hac_module_contract(replace(hac_ir, graph=bad_graph))


def test_hac_ir_contract_validates_known_user_hints() -> None:
    hac_ir = _compiled_hac_module()
    operation = hac_ir.graph.operations[0]
    bad_operation = replace(
        operation,
        attributes={
            **operation.attributes,
            "max_error_budget": -0.1,
        },
    )
    bad_graph = ComputeGraph(
        name=hac_ir.graph.name,
        operations=(bad_operation,),
        metadata=hac_ir.graph.metadata,
    )

    with pytest.raises(ValueError, match="max_error_budget must be finite and non-negative"):
        validate_hac_module_contract(replace(hac_ir, graph=bad_graph))
