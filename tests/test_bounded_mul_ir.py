"""Exact-shape Mul and trusted FP64 reference tests; no native execution evidence."""

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
from tuc.reference.kernels import reference_elementwise, reference_multiply
from tuc.runtime import Assignment, PartitionPlan, execute_graph


def _module(left=(2, 3), right=(2, 3), output=(2, 3),
            dtypes=("float32", "float32", "float32"), repeated=False):
    tensors = tuple(SourceIntentTensor(name, shape, dtype) for name, shape, dtype in zip(
        ("left", "right", "result"), (left, right, output), dtypes, strict=True))
    if repeated:
        tensors = (tensors[0], tensors[2])
    return SourceIntentModule("multiply", tensors, (
        SourceIntentOperation("product", "elementwise", ("left", "left" if repeated else "right"),
                              ("result",), attributes={"elementwise_kind": "mul"}),))


def _operation(left=(2, 3), right=(2, 3), output=(2, 3),
               dtypes=("float32", "float32", "float32")):
    tensors = tuple(TensorRef(name, shape, dtype) for name, shape, dtype in zip(
        ("left", "right", "result"), (left, right, output), dtypes, strict=True))
    return ComputeOperation("product", OperationKind.ELEMENTWISE, tensors[:2], tensors[2:],
                            {"kernel": "mul"})


def _reject_runtime(operation, match):
    graph = ComputeGraph("invalid_mul", (operation,))
    plan = PartitionPlan(graph.name, (Assignment(
        operation.name, "reference-cpu", "test", MemoryDomainKind.HOST_RAM, LayoutKind.ROW_MAJOR,
    ),))
    # Readiness rejects before absent arrays can hide malformed operations.
    with pytest.raises(ValueError, match=match):
        execute_graph(graph, plan, {})


@pytest.mark.parametrize("shape", [(1,), (7,), (1, 1), (1, 5), (5, 1), (2, 3), (64, 64)])
def test_mul_is_neutral_elementwise_through_all_ir_stages(shape):
    module = _module(shape, shape, shape)
    metadata = source_intent_to_triton_metadata(module)
    assert metadata.operations[0].attributes == {"kernel": "mul"}
    compiled = compile_graph(metadata.to_compute_graph(), [])
    for stage in (compiled.tlir, compiled.hac_ir, compiled.hs_ir):
        operation = stage.graph.operations[0]
        assert operation.kind is OperationKind.ELEMENTWISE
        assert operation.attributes["kernel"] == "mul"
        assert tuple(t.shape for t in (*operation.inputs, *operation.outputs)) == (shape,) * 3
    assert compiled.hac_ir.graph.operations[0].attributes["tuc.linearity"] == "nonlinear"
    assert "elementwise_kind=mul" in module.dump()
    estimate = estimate_operation_movement(compiled.hac_ir.graph.operations[0])
    assert (estimate.bytes_read, estimate.bytes_written, estimate.arithmetic_ops) == (
        8 * prod(shape), 4 * prod(shape), prod(shape))
    assert estimate.notes == ("exact_shape_elementwise_multiply",)


@pytest.mark.parametrize("left,right,output", [
    ((2, 3), (2,), (2, 3)),  # A feature gain must match the final dimension.
    ((3,), (2, 3), (2, 3)),
    ((2, 3), (1, 3), (2, 3)),
    ((2, 3), (2, 1), (2, 3)),
    ((3,), (2,), (3,)),
    ((2, 3), (6,), (2, 3)),
    ((2, 3), (2, 3), (3, 2)),
    ((2, 3), (2, 3), (6,)),
    ((1, 2, 3), (1, 2, 3), (1, 2, 3)),
])
def test_mul_shapes_reject_before_runtime_inputs(left, right, output):
    with pytest.raises(ValueError, match="bounded right scaling"):
        _module(left, right, output)
    operation = _operation(left, right, output)
    with pytest.raises(ValueError, match="bounded right scaling"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "bounded right scaling")


@pytest.mark.parametrize("position", range(3))
@pytest.mark.parametrize("dtype", ["float16", "float64", "int32"])
def test_mul_does_not_promote_declared_dtypes(position, dtype):
    dtypes = ["float32"] * 3
    dtypes[position] = dtype
    with pytest.raises(ValueError, match="float32"):
        _module(dtypes=tuple(dtypes))
    operation = _operation(dtypes=tuple(dtypes))
    with pytest.raises(ValueError, match="float32"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "float32")


@pytest.mark.parametrize("inputs,outputs", [
    (("left",), ("result",)),
    (("left", "right", "left"), ("result",)),
    (("left", "right"), ("result", "other")),
])
def test_mul_requires_two_inputs_and_one_output(inputs, outputs):
    with pytest.raises(ValueError, match="two inputs and one output"):
        SourceIntentOperation("product", "elementwise", inputs, outputs,
                              attributes={"elementwise_kind": "mul"})
    operation = _operation()
    tensors = {t.name: t for t in (*operation.inputs, *operation.outputs)}
    tensors["other"] = TensorRef("other", (2, 3))
    malformed = replace(operation, inputs=tuple(tensors[name] for name in inputs),
                        outputs=tuple(tensors[name] for name in outputs))
    with pytest.raises(ValueError, match="two inputs and one output"):
        estimate_operation_movement(malformed)
    _reject_runtime(malformed, "arity must be 2->1")


@pytest.mark.parametrize("port", [0, 1])
def test_mul_output_is_fresh_even_when_all_shapes_match(port):
    operation = _operation()
    name = operation.inputs[port].name
    with pytest.raises(ValueError, match="fresh output"):
        SourceIntentOperation("product", "elementwise", ("left", "right"), (name,),
                              attributes={"elementwise_kind": "mul"})
    operation = replace(operation, outputs=(operation.inputs[port],))
    with pytest.raises(ValueError, match="fresh output"):
        estimate_operation_movement(operation)
    _reject_runtime(operation, "output collides with external input")


@pytest.mark.parametrize("family", ["matmul", "reduction", "softmax"])
def test_mul_attribute_belongs_only_to_elementwise(family):
    with pytest.raises(ValueError, match="only for elementwise"):
        SourceIntentOperation("product", family, ("left", "right"), ("result",),
                              attributes={"elementwise_kind": "mul"})


@pytest.mark.parametrize("shape", [(5,), (2, 3)])
def test_repeated_operand_is_one_public_tensor_but_two_operand_reads(shape):
    graph = source_intent_to_triton_metadata(_module(shape, shape, shape, repeated=True))
    compiled = compile_graph(graph.to_compute_graph(), [])
    operation = compiled.hac_ir.graph.operations[0]
    assert [tensor.name for tensor in operation.inputs] == ["left", "left"]
    assert estimate_operation_movement(operation).bytes_read == prod(shape) * 8
    value = (np.arange(prod(shape), dtype=np.float64) - 2.5).reshape(shape)
    expected = np.array([float(item) * float(item) for item in value.flat]).reshape(shape)
    result = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, {"left": value})
    assert_array_equal(result.output_for("result"), expected)
    assert len(result.records) == 2


@pytest.mark.parametrize("shape", [(5,), (2, 3)])
def test_fp64_reference_and_executor_match_scalar_products_and_preserve_inputs(shape):
    left = (np.arange(prod(shape), dtype=np.float64) - 3.25).reshape(shape)
    right = (np.arange(prod(shape), dtype=np.float64) * -0.75 + 0.5).reshape(shape)
    saved = (left.copy(), right.copy())
    expected = np.array([float(a) * float(b) for a, b in zip(left.flat, right.flat,
                                                           strict=True)]).reshape(shape)
    assert_array_equal(reference_multiply(left, right), expected)
    graph = source_intent_to_triton_metadata(_module(shape, shape, shape)).to_compute_graph()
    compiled = compile_graph(graph, [])
    result = execute_graph(compiled.hac_ir.graph, compiled.partition_plan,
                           {"left": left, "right": right}).output_for("result")
    assert result.dtype == np.dtype("float64")
    assert_array_equal(result, expected)
    assert_array_equal(left, saved[0])
    assert_array_equal(right, saved[1])
    assert not np.shares_memory(result, left) and not np.shares_memory(result, right)


def test_fp64_reference_does_not_claim_native_binary32_rounding():
    left, right = np.array([1.0 + 2.0**-23]), np.array([1.0 - 2.0**-23])
    result = reference_multiply(left, right)
    assert result[0] == 1.0 - 2.0**-46
    assert result[0] != float(np.float32(result[0]))
    zeros = reference_multiply(np.array([0.0, -0.0]), np.array([-1.0, -1.0]))
    assert_array_equal(np.signbit(zeros), [True, False])


@pytest.mark.parametrize("left,right", [
    ((2, 3), (2,)), ((2, 3), (1, 3)), ((3,), (2,)),
    ((3,), (2, 3)), ((1, 2, 3), (1, 2, 3)),
])
def test_reference_rejects_numpy_broadcasting_before_multiplication(left, right, monkeypatch):
    monkeypatch.setattr(np, "multiply", lambda *a, **kw: pytest.fail("broadcast evaluated"))
    with pytest.raises(ValueError, match="bounded right scaling"):
        reference_multiply(np.ones(left), np.ones(right))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("operand", [0, 1])
def test_reference_rejects_nonfinite_operands(bad, operand):
    values = [np.ones((2, 3)), np.ones((2, 3))]
    values[operand].flat[0] = bad
    with pytest.raises(ValueError, match="finite"):
        reference_multiply(*values)


def test_reference_rejects_overflow_and_respects_array_budget(monkeypatch):
    maximum = np.array([np.finfo(np.float64).max])
    with pytest.raises(ValueError, match="result must contain only finite"):
        reference_multiply(maximum, maximum)
    monkeypatch.setattr("tuc.reference.kernels.MAX_REFERENCE_ARRAY_ELEMENTS", 4)
    monkeypatch.setattr(np, "multiply", lambda *a, **kw: pytest.fail("budget checked late"))
    with pytest.raises(ValueError, match="element count"):
        reference_multiply(np.ones(5), np.ones(5))


@pytest.mark.parametrize("bad", [1.0, np.array(1.0), np.array([True]), np.array(["1"])])
def test_reference_rejects_scalars_and_non_numeric_arrays(bad):
    with pytest.raises((TypeError, ValueError)):
        reference_multiply(bad, np.ones(1))


def test_mul_does_not_change_unary_reference_api():
    with pytest.raises(ValueError, match="unsupported elementwise reference kernel"):
        reference_elementwise(np.ones(2), "mul")
    assert_array_equal(reference_elementwise(np.array([-1.0, 2.0]), "relu"), [0.0, 2.0])


def test_seven_operation_relu_gated_mlp_composes_without_a_new_operation_family():
    shapes = {"x": (2, 3), "wv": (4, 3), "bv": (4,), "wg": (4, 3), "bg": (4,),
              "wo": (2, 4), "value": (2, 4), "biased_value": (2, 4), "gate": (2, 4),
              "biased_gate": (2, 4), "positive_gate": (2, 4), "gated": (2, 4),
              "result": (2, 2)}
    calls = (
        ("value", "matmul", ("x", "wv"), {"rhs_transposed": True}),
        ("biased_value", "elementwise", ("value", "bv"), {"elementwise_kind": "add"}),
        ("gate", "matmul", ("x", "wg"), {"rhs_transposed": True}),
        ("biased_gate", "elementwise", ("gate", "bg"), {"elementwise_kind": "add"}),
        ("positive_gate", "elementwise", ("biased_gate",), {"elementwise_kind": "relu"}),
        ("gated", "elementwise", ("biased_value", "positive_gate"), {"elementwise_kind": "mul"}),
        ("result", "matmul", ("gated", "wo"), {"rhs_transposed": True}),
    )
    module = SourceIntentModule("relu_gated_mlp", tuple(
        SourceIntentTensor(name, shape) for name, shape in shapes.items()), tuple(
        SourceIntentOperation(name, family, inputs, (name,), attributes=attrs)
        for name, family, inputs, attrs in calls))
    values = {name: ((np.arange(prod(shapes[name]), dtype=np.float64) % 7 - 3) / 4).reshape(
        shapes[name]) for name in ("x", "wv", "bv", "wg", "bg", "wo")}

    def linear(left, weight):
        return np.array([[sum(float(a) * float(b) for a, b in zip(row, coefficients,
                                                                strict=True))
                          for coefficients in weight] for row in left])

    value = linear(values["x"], values["wv"]) + values["bv"]
    gate = linear(values["x"], values["wg"]) + values["bg"]
    positive = np.array([[max(float(item), 0.0) for item in row] for row in gate])
    assert np.any(gate < 0.0) and np.any(gate > 0.0)
    gated = np.array([[float(a) * float(b) for a, b in zip(row, gates, strict=True)]
                     for row, gates in zip(value, positive, strict=True)])
    expected = linear(gated, values["wo"])
    graph = source_intent_to_triton_metadata(module).to_compute_graph()
    compiled = compile_graph(graph, [])
    actual = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, values)
    assert_array_equal(actual.output_for("result"), expected)
    assert len(compiled.hac_ir.graph.operations) == 7
    assert set(op.kind for op in compiled.hac_ir.graph.operations) == {
        OperationKind.MATMUL, OperationKind.ELEMENTWISE}
