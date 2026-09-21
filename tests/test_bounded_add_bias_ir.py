"""Add/bias semantics and FP64 reference checks; these are not native evidence."""

from __future__ import annotations

from dataclasses import replace
from math import prod

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from tuc.compiler import compile_graph
from tuc.compiler.movement import estimate_operation_movement
from tuc.frontend import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentTensor,
    source_intent_to_triton_metadata,
)
from tuc.ir import (
    ComputeGraph,
    ComputeOperation,
    LayoutKind,
    MemoryDomainKind,
    OperationKind,
    TensorRef,
)
from tuc.reference.kernels import reference_add, reference_elementwise
from tuc.runtime import Assignment, PartitionPlan, execute_graph


def _module(
    left: tuple[int, ...],
    right: tuple[int, ...],
    output: tuple[int, ...] | None = None,
    dtypes: tuple[str, str, str] = ("float32", "float32", "float32"),
    *,
    repeated: bool = False,
) -> SourceIntentModule:
    tensors = (
        SourceIntentTensor("left", left, dtypes[0]),
        SourceIntentTensor("right", right, dtypes[1]),
        SourceIntentTensor("output", left if output is None else output, dtypes[2]),
    )
    if repeated:
        tensors = (tensors[0], tensors[2])
    return SourceIntentModule(
        "bounded_add",
        tensors,
        (SourceIntentOperation(
            "addition", "elementwise", ("left", "left" if repeated else "right"),
            ("output",), attributes={"elementwise_kind": "add"},
        ),),
    )


def _operation(
    left: tuple[int, ...],
    right: tuple[int, ...],
    output: tuple[int, ...] | None = None,
    dtypes: tuple[str, str, str] = ("float32", "float32", "float32"),
) -> ComputeOperation:
    return ComputeOperation(
        "addition", OperationKind.ELEMENTWISE,
        (TensorRef("left", left, dtypes[0]), TensorRef("right", right, dtypes[1])),
        (TensorRef("output", left if output is None else output, dtypes[2]),),
        {"kernel": "add"},
    )


def _reject_invalid_runtime_operation(operation: ComputeOperation, match: str) -> None:
    graph = ComputeGraph("invalid_add", (operation,))
    plan = PartitionPlan(graph.name, (Assignment(
        "addition", "reference-cpu", "test", MemoryDomainKind.HOST_RAM, LayoutKind.ROW_MAJOR,
    ),))
    with pytest.raises(ValueError, match=match):
        execute_graph(graph, plan, {})


@pytest.mark.parametrize("left,right", [
    ((1,), (1,)), ((4,), (4,)), ((2, 3), (2, 3)),
    ((2, 3), (3,)), ((1, 3), (3,)), ((3, 1), (1,)), ((64, 64), (64,)),
])
def test_add_intent_metadata_and_lowering_preserve_ports_and_semantics(left, right) -> None:
    module = _module(left, right)
    metadata = source_intent_to_triton_metadata(module)
    assert metadata.operations[0].attributes == {"kernel": "add"}
    compiled = compile_graph(metadata.to_compute_graph(), [])
    for stage in (compiled.tlir, compiled.hac_ir, compiled.hs_ir):
        operation = stage.graph.operations[0]
        assert operation.kind is OperationKind.ELEMENTWISE
        assert tuple(tensor.shape for tensor in operation.inputs) == (left, right)
        assert operation.outputs[0].shape == left
        assert operation.attributes["kernel"] == "add"
    assert compiled.hac_ir.graph.operations[0].attributes["tuc.linearity"] == "nonlinear"
    assert "backend" not in module.operations[0].attributes
    assert "elementwise_kind=add" in module.dump()


@pytest.mark.parametrize("left,right,output", [
    ((2, 3), (2, 1), (2, 3)),  # Column broadcast.
    ((2, 3), (1, 3), (2, 3)),  # Rank-2 singleton broadcast.
    ((3,), (2, 3), (2, 3)),  # Reversed bias.
    ((3,), (1,), (3,)),  # Vector scalar-like broadcast.
    ((1, 2, 3), (1, 2, 3), (1, 2, 3)),
    ((2, 3), (6,), (2, 3)),
    ((2, 3), (2,), (2, 3)),
    ((2, 3), (3,), (3, 2)),
    ((2, 3), (3,), (6,)),
])
def test_add_shapes_fail_closed_at_intent_movement_and_runtime(left, right, output) -> None:
    with pytest.raises(ValueError):
        _module(left, right, output)
    operation = _operation(left, right, output)
    with pytest.raises(ValueError):
        estimate_operation_movement(operation)
    # Public runtime readiness must reject before any input arrays are admitted.
    _reject_invalid_runtime_operation(operation, "runtime executor add")


@pytest.mark.parametrize("dtypes", [
    ("float16", "float32", "float32"),
    ("float32", "float64", "float32"),
    ("float32", "float32", "int32"),
    ("float64", "float64", "float64"),
])
def test_add_requires_fp32_declarations(dtypes) -> None:
    with pytest.raises(ValueError, match="float32"):
        _module((2, 3), (3,), dtypes=dtypes)
    with pytest.raises(ValueError, match="float32"):
        estimate_operation_movement(_operation((2, 3), (3,), dtypes=dtypes))
    _reject_invalid_runtime_operation(_operation((2, 3), (3,), dtypes=dtypes), "float32")


@pytest.mark.parametrize("inputs,outputs", [
    (("left",), ("output",)),
    (("left", "right", "left"), ("output",)),
    (("left", "right"), ("output", "other")),
])
def test_add_arity_is_explicit(inputs, outputs) -> None:
    with pytest.raises(ValueError, match="two inputs and one output"):
        SourceIntentOperation("add", "elementwise", inputs, outputs,
                              attributes={"elementwise_kind": "add"})
    operation = _operation((2, 3), (3,))
    by_name = {tensor.name: tensor for tensor in (*operation.inputs, *operation.outputs)}
    by_name["other"] = TensorRef("other", (2, 3))
    malformed = replace(operation, inputs=tuple(by_name[name] for name in inputs),
                        outputs=tuple(by_name[name] for name in outputs))
    with pytest.raises(ValueError, match="two inputs and one output"):
        estimate_operation_movement(malformed)
    _reject_invalid_runtime_operation(malformed, "arity must be 2->1")


@pytest.mark.parametrize("left,right", [((4,), (4,)), ((2, 3), (2, 3)), ((2, 3), (3,))])
def test_add_movement_counts_operand_storage_and_one_sum_per_output(left, right) -> None:
    estimate = estimate_operation_movement(_operation(left, right))
    assert estimate.bytes_read == (prod(left) + prod(right)) * 4
    assert estimate.bytes_written == prod(left) * 4
    assert estimate.arithmetic_ops == prod(left)
    assert estimate.notes == (
        "right_row_bias_add" if len(right) == 1 and len(left) == 2
        else "exact_shape_elementwise",
    )


@pytest.mark.parametrize("shape", [(4,), (2, 3)])
def test_add_same_symbol_twice_preserves_both_reads(shape) -> None:
    module = _module(shape, shape, repeated=True)
    graph = source_intent_to_triton_metadata(module).to_compute_graph()
    compiled = compile_graph(graph, [])
    operation = compiled.hac_ir.graph.operations[0]
    assert tuple(tensor.name for tensor in operation.inputs) == ("left", "left")
    assert estimate_operation_movement(operation).bytes_read == prod(shape) * 8
    value = np.arange(prod(shape), dtype=np.float64).reshape(shape) - 2.0
    observed = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, {"left": value})
    assert_array_equal(observed.output_for("output"), value * 2.0)
    assert len(observed.records) == 2


@pytest.mark.parametrize("left,right", [((4,), (4,)), ((2, 3), (2, 3)), ((2, 3), (3,))])
def test_add_reference_and_public_executor_use_fp64_policy_without_mutating_inputs(left, right):
    left_value = np.arange(prod(left), dtype=np.float64).reshape(left) - 4.25
    right_value = np.arange(prod(right), dtype=np.float64).reshape(right) * 3.5
    left_saved, right_saved = left_value.copy(), right_value.copy()
    expected = np.array([
        float(value) + float(right_value.flat[index % prod(right)])
        for index, value in enumerate(left_value.flat)
    ]).reshape(left)
    assert_array_equal(reference_add(left_value, right_value), expected)
    graph = source_intent_to_triton_metadata(_module(left, right)).to_compute_graph()
    compiled = compile_graph(graph, [])
    result = execute_graph(compiled.hac_ir.graph, compiled.partition_plan,
                           {"left": left_value, "right": right_value})
    assert result.output_for("output").dtype == np.dtype("float64")
    assert_array_equal(result.output_for("output"), expected)
    assert_array_equal(left_value, left_saved)
    assert_array_equal(right_value, right_saved)
    assert not np.shares_memory(result.output_for("output"), left_value)
    assert not np.shares_memory(result.output_for("output"), right_value)


def test_add_reference_precision_is_not_a_native_fp32_claim() -> None:
    result = reference_add(np.array([2.0**24]), np.array([1.0]))
    assert result[0] == 16777217.0
    assert result[0] != float(np.float32(16777217.0))


@pytest.mark.parametrize("left,right", [
    ((2, 3), (2, 1)), ((2, 3), (1, 3)), ((3,), (2, 3)),
    ((3,), (1,)), ((1, 2, 3), (1, 2, 3)),
])
def test_add_reference_disallows_other_numpy_broadcasts(left, right) -> None:
    with pytest.raises(ValueError):
        reference_add(np.ones(left), np.ones(right))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("operand", [0, 1])
def test_add_reference_rejects_nonfinite_operands(bad, operand) -> None:
    values = [np.ones((2, 3)), np.ones((3,))]
    values[operand].flat[0] = bad
    with pytest.raises(ValueError, match="finite"):
        reference_add(*values)


def test_add_reference_rejects_overflowed_result() -> None:
    maximum = np.array([np.finfo(np.float64).max])
    with pytest.raises(ValueError, match="result must contain only finite"):
        reference_add(maximum, maximum)


def test_add_does_not_expand_unary_reference_api() -> None:
    with pytest.raises(ValueError, match="unsupported elementwise reference kernel"):
        reference_elementwise(np.ones((2, 3)), "add")


def test_relu_movement_still_requires_exact_shapes() -> None:
    operation = replace(_operation((2, 3), (3,)), attributes={"kernel": "relu"})
    with pytest.raises(ValueError, match="exact-shape"):
        estimate_operation_movement(operation)
