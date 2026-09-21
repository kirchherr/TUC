"""Neutral Linear semantics and FP64 reference checks, without native execution."""

from __future__ import annotations

from dataclasses import replace
from math import prod
from types import MappingProxyType

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
from tuc.reference.kernels import reference_matmul, reference_matmul_rhs_transposed
from tuc.runtime import Assignment, PartitionPlan, execute_graph


def _module(left=(2, 3), right=(4, 3), output=(2, 4),
            dtypes=("float32", "float32", "float32"), repeated=False):
    tensors = tuple(SourceIntentTensor(name, shape, dtype) for name, shape, dtype in zip(
        ("x", "weights", "result"), (left, right, output), dtypes, strict=True))
    if repeated:
        tensors = (tensors[0], tensors[2])
    return SourceIntentModule("linear", tensors, (
        SourceIntentOperation("projection", "matmul", ("x", "x" if repeated else "weights"),
                              ("result",), attributes={"rhs_transposed": True}),
    ))


def _operation(left=(2, 3), right=(4, 3), output=(2, 4),
               dtypes=("float32", "float32", "float32"), attributes=None):
    tensors = tuple(TensorRef(name, shape, dtype) for name, shape, dtype in zip(
        ("x", "weights", "result"), (left, right, output), dtypes, strict=True))
    return ComputeOperation("projection", OperationKind.MATMUL, tensors[:2], tensors[2:],
                            {"rhs_transposed": True} if attributes is None else attributes)


def _reject_runtime(operation, match):
    graph = ComputeGraph("invalid_linear", (operation,))
    plan = PartitionPlan(graph.name, (Assignment(
        operation.name, "reference-cpu", "test", MemoryDomainKind.HOST_RAM, LayoutKind.ROW_MAJOR,
    ),))
    # Readiness validates operations before missing input arrays can mask a rejection.
    with pytest.raises(ValueError, match=match):
        execute_graph(graph, plan, {})


@pytest.mark.parametrize("m,k,n", [(1, 1, 1), (2, 3, 4), (1, 3, 4), (3, 1, 2),
                                   (3, 4, 1), (33, 7, 5), (64, 64, 64)])
def test_linear_preserves_weight_orientation_and_neutral_intent(m, k, n):
    module = _module((m, k), (n, k), (m, n))
    metadata = source_intent_to_triton_metadata(module)
    assert metadata.operations[0].attributes == {"rhs_transposed": True}
    compiled = compile_graph(metadata.to_compute_graph(), [])
    for stage in (compiled.tlir, compiled.hac_ir, compiled.hs_ir):
        operation = stage.graph.operations[0]
        assert operation.kind is OperationKind.MATMUL
        assert tuple(tensor.shape for tensor in operation.inputs) == ((m, k), (n, k))
        assert operation.outputs[0].shape == (m, n)
        assert operation.attributes["rhs_transposed"] is True
    assert compiled.hac_ir.graph.operations[0].attributes["tuc.linearity"] == "linear"
    assert "rhs_transposed=true" in module.dump()
    assert len(compiled.hac_ir.graph.operations) == 1


@pytest.mark.parametrize("bad", [False, 0, 1, 1.0, "true", "True", None, (), []])
def test_linear_flag_requires_exact_true_when_present(bad):
    with pytest.raises(ValueError, match="rhs_transposed"):
        SourceIntentOperation("projection", "matmul", ("x", "weights"), ("result",),
                              attributes={"rhs_transposed": bad})
    operation = _operation()
    object.__setattr__(operation, "attributes", MappingProxyType({"rhs_transposed": bad}))
    with pytest.raises(ValueError, match="rhs_transposed"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "rhs_transposed")


def test_linear_flag_rejects_hostile_values_without_boolean_or_equality_hooks():
    class Trap:
        def __bool__(self):
            pytest.fail("caller boolean dispatched")

        def __eq__(self, other):
            pytest.fail("caller equality dispatched")

    trap = Trap()
    with pytest.raises(ValueError, match="rhs_transposed"):
        SourceIntentOperation("projection", "matmul", ("x", "weights"), ("result",),
                              attributes={"rhs_transposed": trap})
    operation = _operation()
    object.__setattr__(operation, "attributes", MappingProxyType({"rhs_transposed": trap}))
    with pytest.raises(ValueError, match="rhs_transposed"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "rhs_transposed")


@pytest.mark.parametrize("kind", [OperationKind.ELEMENTWISE, OperationKind.REDUCTION,
                                  OperationKind.SOFTMAX])
def test_transposition_flag_is_owned_by_matmul(kind):
    with pytest.raises(ValueError, match="rhs_transposed"):
        SourceIntentOperation("other", kind.value, ("x",), ("result",),
                              attributes={"rhs_transposed": True})
    operation = replace(_operation(), kind=kind)
    with pytest.raises(ValueError, match="belongs only to matmul"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "belongs only to matmul")


@pytest.mark.parametrize("left,right,output", [
    ((3,), (4, 3), (1, 4)), ((2, 3), (3,), (2, 1)), ((2, 3), (4, 3), (8,)),
    ((1, 2, 3), (4, 3), (2, 4)), ((2, 3), (1, 4, 3), (2, 4)),
    ((2, 3), (3, 4), (2, 4)), ((2, 3), (4, 2), (2, 4)),
    ((2, 3), (4, 3), (4, 2)), ((2, 3), (4, 3), (2, 3)),
])
def test_linear_rank_and_shape_mismatch_reject_at_all_three_boundaries(left, right, output):
    with pytest.raises(ValueError):
        _module(left, right, output)
    operation = _operation(left, right, output)
    with pytest.raises(ValueError):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "rank must be 2|transposed matmul shape")


@pytest.mark.parametrize("dtypes", [("float16", "float32", "float32"),
                                    ("float32", "float64", "float32"),
                                    ("float32", "float32", "int32"),
                                    ("float64", "float64", "float64")])
def test_linear_requires_fp32_tensor_declarations(dtypes):
    with pytest.raises(ValueError, match="float32"):
        _module(dtypes=dtypes)
    operation = _operation(dtypes=dtypes)
    with pytest.raises(ValueError, match="float32"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "float32")


@pytest.mark.parametrize("inputs,outputs", [(("x",), ("result",)),
    (("x", "weights", "x"), ("result",)), (("x", "weights"), ("result", "other"))])
def test_linear_exact_arity(inputs, outputs):
    with pytest.raises(ValueError, match="two inputs and one output"):
        SourceIntentOperation("projection", "matmul", inputs, outputs,
                              attributes={"rhs_transposed": True})
    operation = _operation()
    tensors = {t.name: t for t in (*operation.inputs, *operation.outputs)}
    tensors["other"] = TensorRef("other", (2, 4))
    operation = replace(operation, inputs=tuple(tensors[name] for name in inputs),
                         outputs=tuple(tensors[name] for name in outputs))
    with pytest.raises(ValueError, match="two inputs and one output"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "arity must be 2->1")


def test_linear_movement_accounts_original_weights_without_temporary_transpose():
    estimate = estimate_operation_movement(_operation())
    assert estimate.bytes_read == (2 * 3 + 4 * 3) * 4
    assert estimate.bytes_written == 2 * 4 * 4
    assert estimate.arithmetic_ops == 2 * 2 * 3 * 4
    assert estimate.notes == ("rank2_matmul_rhs_transposed_no_materialization",)
    assert estimate.arithmetic_intensity == pytest.approx(48 / 104)


@pytest.mark.parametrize("m,k,n", [(1, 1, 1), (2, 3, 4), (1, 3, 4), (3, 1, 2), (33, 7, 5)])
def test_linear_reference_and_executor_match_independent_rows_without_mutating_weights(m, k, n):
    left = np.arange(m * k, dtype=np.float64).reshape(m, k) / 4.0 - 2.0
    right = np.arange(n * k, dtype=np.float64).reshape(n, k) / 2.0 - 3.0
    saved_left, saved_right = left.copy(), right.copy()
    expected = np.array([[sum(float(left[row, j]) * float(right[column, j])
                              for j in range(k)) for column in range(n)] for row in range(m)])
    assert_array_equal(reference_matmul_rhs_transposed(left, right), expected)
    graph = source_intent_to_triton_metadata(_module((m, k), (n, k), (m, n))).to_compute_graph()
    compiled = compile_graph(graph, [])
    result = execute_graph(compiled.hac_ir.graph, compiled.partition_plan,
                           {"x": left, "weights": right}).output_for("result")
    assert result.dtype == np.dtype("float64")
    assert_array_equal(result, expected)
    assert_array_equal(left, saved_left)
    assert_array_equal(right, saved_right)
    assert not np.shares_memory(result, left) and not np.shares_memory(result, right)


def test_linear_same_symbol_twice_forms_gram_matrix_with_one_public_input():
    module = _module((2, 3), (2, 3), (2, 2), repeated=True)
    compiled = compile_graph(source_intent_to_triton_metadata(module).to_compute_graph(), [])
    values = np.array([[1.0, 2.0, 3.0], [-4.0, 5.0, -6.0]])
    result = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, {"x": values})
    assert_array_equal(result.output_for("result"), [[14.0, -12.0], [-12.0, 77.0]])
    assert len(result.records) == 2
    assert estimate_operation_movement(compiled.hac_ir.graph.operations[0]).bytes_read == 48


def test_linear_reference_keeps_fp64_policy_separate_from_native_fp32():
    result = reference_matmul_rhs_transposed(np.array([[2.0**24, 1.0]]), np.ones((1, 2)))
    assert result[0, 0] == 16777217.0
    assert result[0, 0] != float(np.float32(result[0, 0]))


def test_linear_reference_checks_output_budget_before_matrix_multiplication():
    with pytest.raises(ValueError, match="output exceeds"):
        reference_matmul_rhs_transposed(np.ones((1001, 1)), np.ones((1000, 1)))


@pytest.mark.parametrize("left,right", [((3,), (4, 3)), ((2, 3), (3,)), ((2, 3), (3, 4))])
def test_linear_reference_rejects_rank_or_inner_dimension_mismatch(left, right):
    with pytest.raises(ValueError, match="rank-2|dimensions must agree"):
        reference_matmul_rhs_transposed(np.ones(left), np.ones(right))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("index", [0, 1])
def test_linear_reference_rejects_nonfinite_inputs(bad, index):
    inputs = [np.ones((2, 3)), np.ones((4, 3))]
    inputs[index].flat[0] = bad
    with pytest.raises(ValueError, match="finite"):
        reference_matmul_rhs_transposed(*inputs)


def test_linear_reference_rejects_overflowed_fp64_result():
    with pytest.raises(ValueError, match="result must contain only finite"):
        reference_matmul_rhs_transposed(np.array([[np.finfo(np.float64).max]]), np.array([[2.0]]))


def test_normal_matmul_keeps_original_mixed_dtype_movement_and_reference():
    operation = _operation((2, 3), (3, 4), (2, 4),
                           ("float32", "float16", "float32"), attributes={})
    estimate = estimate_operation_movement(operation)
    assert estimate.notes == ("rank2_matmul",)
    assert estimate.bytes_read == prod((2, 3)) * 4 + prod((3, 4)) * 2
    left = np.arange(6, dtype=np.float64).reshape(2, 3)
    right = np.arange(12, dtype=np.float64).reshape(3, 4)
    assert_array_equal(reference_matmul(left, right), left @ right)
    assert "rhs_transposed" not in operation.attributes
