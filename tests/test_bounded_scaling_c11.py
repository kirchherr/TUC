"""Pure bounded scaling checks; generated text is not native execution evidence."""

import json
import math
import struct
from dataclasses import fields, replace
from hashlib import sha256
from types import MappingProxyType

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_add_dag import lower_bounded_add_dag
from tuc.backends.bounded_c11_codegen import (
    C11GraphSpec,
    C11OperationSpec,
    emit_checked_graph,
    validate_spec,
)
from tuc.backends.bounded_dag import BoundedDAGArtifacts, DAGTarget, lower_bounded_dag
from tuc.backends.bounded_linear_dag import lower_bounded_linear_dag
from tuc.backends.bounded_mul_dag import lower_bounded_mul_dag
from tuc.backends.bounded_scaling_dag import (
    lower_bounded_scaling_dag,
    validate_bounded_scaling_dag_artifacts,
)
from tuc.backends.bounded_softmax_dag import lower_bounded_softmax_dag
from tuc.compiler import compile_graph, emit_bounded_c11_entrypoint
from tuc.compiler.bounded_source import BoundedBackendBinding, compile_bounded_source_intent
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef


def capability(target=DAGTarget.C11):
    return BackendCapability("cpu", frozenset((OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                                               OperationKind.REDUCTION, OperationKind.SOFTMAX)),
                             memory_domain=MemoryDomainKind.HOST_RAM if target is DAGTarget.C11
                             else MemoryDomainKind.UNKNOWN)


def graph(lhs=(2, 3), rhs=(1,)):
    x, scale, y = TensorRef("x", lhs), TensorRef("scale", rhs), TensorRef("y", lhs)
    return ComputeGraph("scaling", (ComputeOperation("scale", OperationKind.ELEMENTWISE,
                                                     (x, scale), (y,), {"kernel": "mul"}),))


def compiled(value=None, target=DAGTarget.C11):
    result = compile_graph(graph() if value is None else value, (capability(target),),
                           include_candidate_scores=True)
    return result, {"cpu": target}


def lower(value=None):
    result, targets = compiled(value)
    return lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)


def source(lhs=(2, 3), rhs=(1,)):
    return SourceIntentModule("scaling", (SourceIntentTensor("x", lhs),
                                          SourceIntentTensor("scale", rhs),
                                          SourceIntentTensor("y", lhs)), (
        SourceIntentOperation("scale", "elementwise", ("x", "scale"), ("y",),
                              attributes={"elementwise_kind": "mul"}),),
        returns=(SourceIntentReturn("scaled", "y"),))


@pytest.mark.parametrize("lhs,rhs,kind", [((3,), (1,), "mul_scalar"),
    ((64,), (1,), "mul_scalar"), ((2, 3), (1,), "mul_scalar"),
    ((1, 1), (1,), "mul_scalar"), ((64, 1), (1,), "mul_scalar"),
    ((1, 3), (3,), "mul_row_scale"), ((2, 3), (3,), "mul_row_scale"),
    ((64, 64), (64,), "mul_row_scale"), ((64, 64), (1,), "mul_scalar")])
def test_shapes_work_storage_and_checked_emission(lhs, rhs, kind):
    result, targets = compiled(graph(lhs, rhs))
    artifact = lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)
    validate_bounded_scaling_dag_artifacts(artifact, result.hac_ir, result.partition_plan, targets)
    manifest = json.loads(artifact.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_scaling_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == kind
    assert manifest["operations"][0]["input_shapes"] == [list(lhs), list(rhs)]
    assert manifest["scalar_work"] == math.prod(lhs)
    assert manifest["planned_buffer_bytes"] == 4 * (2 * math.prod(lhs) + math.prod(rhs))
    assert manifest["planned_copy_bytes"] == 0
    assert manifest["native_execution_observed"] is False
    assert manifest["cuda_source_emitted"] is False
    assert "TUC_BOUNDED_SCALING_GENERATED_H" in artifact.c11_header
    assert "TUC_BOUNDED_SCALING_SCHEDULE_H" in artifact.schedule_header
    assert "TUC_SCALING_MUL_SCALAR=8, TUC_SCALING_MUL_ROW_SCALE=9" in artifact.schedule_header
    assert "softmax" not in manifest["numeric_policy"]
    index = "0" if kind == "mul_scalar" else f"index % {lhs[1]}U"
    assert f"input_0[index] * input_1[{index}]" in artifact.c11_source
    module, bindings = source(lhs, rhs), (BoundedBackendBinding(capability(), DAGTarget.C11),)
    public = compile_bounded_source_intent(module, bindings)
    checked = emit_bounded_c11_entrypoint(module, bindings, public)
    numeric = json.loads(checked.manifest_json)["numeric_policy"]
    assert numeric["scaling_temporary_bytes"] == 0
    assert numeric["scaling_precedence"] == "equal_shapes_then_right_scalar_then_right_feature"
    assert numeric["nonzero_operands_product_rounding_to_zero_rejected"] is True
    assert "#include <math.h>" not in checked.source
    assert "static int tuc_add(" not in checked.source
    assert checked.source.count("static int tuc_multiply(") == 1
    checked_index = "0" if kind == "mul_scalar" else f"i % {lhs[1]}U"
    assert f"tuc_multiply(a0[i], a1[{checked_index}], &out[i])" in checked.source
    assert checked.source.index("if (!tuc_op_0(") < checked.source.index("memcpy(out[0].data,")


@pytest.mark.parametrize("shape", [(1,), (3,), (1, 1), (2, 3), (64, 64)])
def test_equal_shape_priority_remains_original_mul(shape):
    module, bindings = source(shape, shape), (BoundedBackendBinding(capability(), DAGTarget.C11),)
    artifact = compile_bounded_source_intent(module, bindings).artifacts
    manifest = json.loads(artifact.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_mul_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "mul"
    with pytest.raises(ValueError, match="scope"):
        lower(graph(shape, shape))


@pytest.mark.parametrize("lhs,rhs,out", [
    ((1,), (2, 3), (2, 3)), ((3,), (2, 3), (2, 3)),
    ((2, 3), (2, 1), (2, 3)), ((2, 3), (1, 3), (2, 3)),
    ((2, 3), (2,), (2, 3)), ((3,), (2,), (3,)),
    ((2, 3), (), (2, 3)), ((2, 3), (0,), (2, 3)),
    ((2, 3), (True,), (2, 3)), ((2, 3), (1,), (3, 2)),
    ((1, 2, 3), (1,), (1, 2, 3)), ((65, 3), (1,), (65, 3)),
])
def test_invalid_shapes_reject_before_formatting(lhs, rhs, out, monkeypatch):
    result, targets = compiled()
    op = result.hac_ir.graph.operations[0]
    for tensor, shape in zip((*op.inputs, *op.outputs), (lhs, rhs, out), strict=True):
        object.__setattr__(tensor, "shape", shape)
    monkeypatch.setattr("tuc.backends.bounded_scaling_dag._primitives",
                        lambda _: pytest.fail("emission before validation"))
    with pytest.raises(ValueError):
        lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("attrs", [{"axis": 1}, {"rhs_transposed": True},
    {"broadcast": "scalar"}, {"kernel": "mul_scalar"}, {"kernel": "multiply"},
    {"kernel": object()}, {"tuc.layout": LayoutKind.COLUMN_MAJOR},
    {"tuc.layout_tile_shape": (2, 3)}, {"max_error_budget": float("nan")},
    {"prefer_sparsity": 1}])
def test_unknown_semantics_layout_and_hints_reject(attrs):
    result, targets = compiled()
    op = result.hac_ir.graph.operations[0]
    object.__setattr__(op, "attributes", MappingProxyType(dict(op.attributes, **attrs)))
    with pytest.raises(ValueError):
        lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("which", ["module", "graph", "operation", "tensor", "partition",
                                    "assignment", "score", "artifact"])
def test_shadowed_records_reject_without_host_dispatch(which):
    result, targets = compiled()
    module, partition = result.hac_ir, result.partition_plan
    artifact = lower_bounded_scaling_dag(module, partition, targets)
    values = {"module": module, "graph": module.graph, "operation": module.graph.operations[0],
              "tensor": module.graph.operations[0].inputs[0], "partition": partition,
              "assignment": partition.assignments[0], "score": partition.candidate_scores[0],
              "artifact": artifact}
    object.__setattr__(values[which], "dump", lambda: pytest.fail("caller hook"))
    with pytest.raises(ValueError):
        validate_bounded_scaling_dag_artifacts(artifact, module, partition, targets)


def test_proxy_rejects_user_mapping_without_traversing_it():
    class Trap(dict):
        def __iter__(self):
            pytest.fail("caller iteration")

        def items(self):
            pytest.fail("caller items")

    result, targets = compiled()
    op = result.hac_ir.graph.operations[0]
    object.__setattr__(op, "attributes", MappingProxyType(Trap(dict(op.attributes))))
    with pytest.raises(ValueError):
        lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("field", [item.name for item in fields(BoundedDAGArtifacts)])
def test_all_artifact_fields_revalidated(field):
    result, targets = compiled()
    artifact = lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)
    changed = replace(artifact, **{field: getattr(artifact, field) + " "})
    with pytest.raises(ValueError):
        validate_bounded_scaling_dag_artifacts(changed, result.hac_ir,
                                              result.partition_plan, targets)


@pytest.mark.parametrize("change", ["arity", "dtype", "inplace", "operation-budget",
                                    "metadata-budget", "forward", "duplicate-producer"])
def test_structural_mutations_fail_closed(change):
    result, targets = compiled()
    op = result.hac_ir.graph.operations[0]
    if change == "arity":
        object.__setattr__(op, "inputs", (op.inputs[0],))
    elif change == "dtype":
        object.__setattr__(op.inputs[1], "dtype", "float64")
    elif change == "inplace":
        object.__setattr__(op, "outputs", (op.inputs[0],))
    elif change == "operation-budget":
        object.__setattr__(result.hac_ir.graph, "operations", (op,) * 9)
    elif change == "metadata-budget":
        result.hac_ir.metadata["oversized"] = "x" * 65537
    else:
        second = replace(op, name="second", inputs=(op.outputs[0], op.inputs[1]),
                         outputs=(TensorRef("z", (2, 3)),))
        if change == "forward":
            operations = (second, op)
        else:
            operations = (op, replace(second, outputs=op.outputs))
        object.__setattr__(result.hac_ir.graph, "operations", operations)
    with pytest.raises(ValueError):
        lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)


def test_scaling_rejects_cuda_targets_and_all_old_emitters():
    result, targets = compiled(target=DAGTarget.CUDA_SM86)
    with pytest.raises(ValueError):
        lower_bounded_scaling_dag(result.hac_ir, result.partition_plan, targets)
    result, targets = compiled()
    for old in (lower_bounded_dag, lower_bounded_add_dag, lower_bounded_linear_dag,
                lower_bounded_mul_dag, lower_bounded_softmax_dag):
        with pytest.raises(ValueError):
            old(result.hac_ir, result.partition_plan, targets)
    without_elementwise = BackendCapability("cpu", frozenset((OperationKind.MATMUL,)),
                                            memory_domain=MemoryDomainKind.HOST_RAM)
    with pytest.raises(ValueError):
        compile_bounded_source_intent(source(), (
            BoundedBackendBinding(without_elementwise, DAGTarget.C11),))


_PRECEDING = {
    "matmul": (OperationKind.MATMUL, ((2, 3), (3, 4)), (2, 4), {}),
    "matmul_rhs_transposed": (OperationKind.MATMUL, ((2, 3), (4, 3)), (2, 4),
                             {"rhs_transposed": True}),
    "add": (OperationKind.ELEMENTWISE, ((2, 3), (2, 3)), (2, 3), {"kernel": "add"}),
    "add_row_bias": (OperationKind.ELEMENTWISE, ((2, 3), (3,)), (2, 3), {"kernel": "add"}),
    "mul": (OperationKind.ELEMENTWISE, ((2, 3), (2, 3)), (2, 3), {"kernel": "mul"}),
    "relu": (OperationKind.ELEMENTWISE, ((2, 3),), (2, 3), {"kernel": "relu"}),
    "sum_axis1": (OperationKind.REDUCTION, ((2, 3),), (2,), {"axis": 1}),
    "softmax_axis1": (OperationKind.SOFTMAX, ((2, 3),), (2, 3), {"axis": 1}),
}


@pytest.mark.parametrize("kind", _PRECEDING)
def test_scaling_composes_all_previous_operation_kinds(kind):
    operation, shapes, output, attrs = _PRECEDING[kind]
    inputs = tuple(TensorRef("x" + str(i), shape) for i, shape in enumerate(shapes))
    middle, scale, out = TensorRef("middle", output), TensorRef("s", (1,)), TensorRef("out", output)
    value = ComputeGraph("compose", (
        ComputeOperation("first", operation, inputs, (middle,), attrs),
        ComputeOperation("scale", OperationKind.ELEMENTWISE, (middle, scale), (out,),
                         {"kernel": "mul"})))
    artifact = lower(value)
    manifest = json.loads(artifact.manifest_json)
    assert [op["kind"] for op in manifest["operations"]] == [kind, "mul_scalar"]
    assert ("#include <math.h>" in artifact.c11_source) == (kind == "softmax_axis1")
    assert ("softmax" in manifest["numeric_policy"]) == (kind == "softmax_axis1")
    spec = C11GraphSpec((*shapes, output, (1,), output), (
        C11OperationSpec(kind, tuple(range(len(shapes))), len(shapes)),
        C11OperationSpec("mul_scalar", (len(shapes), len(shapes) + 1), len(shapes) + 2)),
        (*range(len(shapes)), len(shapes) + 1), (len(shapes) + 2,))
    emitted = emit_checked_graph(spec, "a" * 64)[1]
    assert "tuc_multiply(a0[i], a1[0], &out[i])" in emitted


def test_work_and_storage_budget_remain_bounded():
    x, w, p, q, scale, y = (TensorRef(name, (1,) if name == "s" else (64, 64))
                            for name in ("x", "w", "p", "q", "s", "y"))
    value = ComputeGraph("work_budget", (
        ComputeOperation("first", OperationKind.MATMUL, (x, w), (p,)),
        ComputeOperation("second", OperationKind.MATMUL, (p, w), (q,)),
        ComputeOperation("scale", OperationKind.ELEMENTWISE, (q, scale), (y,), {"kernel": "mul"})))
    with pytest.raises(ValueError, match="budget"):
        lower(value)
    operations = tuple(ComputeOperation("op" + str(i), OperationKind.ELEMENTWISE,
        (TensorRef("x" + str(i), (64, 64)), TensorRef("s" + str(i), (1,))),
        (TensorRef("y" + str(i), (64, 64)),), {"kernel": "mul"}) for i in range(8))
    with pytest.raises(ValueError, match="budget"):
        lower(ComputeGraph("storage_budget", operations))


@pytest.mark.parametrize("kind,lhs,rhs,out", [
    ("mul_scalar", (1,), (1,), (1,)),
    ("mul_scalar", (2, 3), (3,), (2, 3)),
    ("mul_scalar", (1,), (2, 3), (2, 3)),
    ("mul_scalar", (2, 3), (), (2, 3)),
    ("mul_scalar", (2, 3), (True,), (2, 3)),
    ("mul_scalar", (2, 3), (1,), (3, 2)),
    ("mul_row_scale", (3,), (3,), (3,)),
    ("mul_row_scale", (2, 1), (1,), (2, 1)),
    ("mul_row_scale", (2, 3), (2, 3), (2, 3)),
    ("mul_row_scale", (2, 3), (2,), (2, 3)),
    ("mul_row_scale", (2, 3), (1, 3), (2, 3)),
    ("mul_row_scale", (2, 3), (2, 1), (2, 3)),
])
def test_private_descriptor_rejects_noncanonical_scaling_before_indexing(kind, lhs, rhs, out):
    spec = C11GraphSpec((lhs, rhs, out), (C11OperationSpec(kind, (0, 1), 2),), (0, 1), (2,))
    with pytest.raises(ValueError):
        emit_checked_graph(spec, "a" * 64)


@pytest.mark.parametrize("kind,rhs", [("mul_scalar", (1,)), ("mul_row_scale", (64,))])
def test_private_descriptor_accounts_for_actual_rhs_storage(kind, rhs):
    spec = C11GraphSpec(((64, 64), rhs, (64, 64)),
                        (C11OperationSpec(kind, (0, 1), 2),), (0, 1), (2,))
    assert validate_spec(spec) == (32768 + 4 * math.prod(rhs), 4096)


def test_scaling_reuses_exact_checked_product_and_environment_guards():
    def text(kind, rhs):
        return emit_checked_graph(C11GraphSpec(((2, 3), rhs, (2, 3)),
            (C11OperationSpec(kind, (0, 1), 2),), (0, 1), (2,)), "a" * 64)[1]

    original = text("mul", (2, 3))
    start, end = original.index("static int tuc_multiply("), original.index("static int tuc_op_0(")
    helper = original[start:end]
    for kind, rhs in (("mul_scalar", (1,)), ("mul_row_scale", (3,))):
        emitted = text(kind, rhs)
        assert helper in emitted
        assert "volatile float rounded = left * right;" in helper
        assert "(lbits & UINT32_C(0x7fffffff)) != 0U" in helper
        assert "(rbits & UINT32_C(0x7fffffff)) != 0U" in helper
        assert "(csr & 0xe040U) != 0U" in emitted
        assert "(csr & 0x1f80U) != 0x1f80U" in emitted


def test_softmax_old_primitive_and_checked_artifact_bytes_stay_exact():
    # Captured before scaling edits, independently of new lowering. Not execution evidence.
    spec = C11GraphSpec(((2, 3), (2, 3)), (C11OperationSpec("softmax_axis1", (0,), 1),),
                        (0,), (1,))
    private = json.dumps(emit_checked_graph(spec, "a" * 64), separators=(",", ":")).encode()
    assert sha256(private).hexdigest() == (
        "c31ea275585c68b81ab648514b1a9a16ca5f0fd8392793ed854972517648ba99")
    module = SourceIntentModule("frozen_softmax", (SourceIntentTensor("t0", (2, 3)),
        SourceIntentTensor("t1", (2, 3))), (SourceIntentOperation("compute", "softmax", ("t0",),
            ("t1",), attributes={"axis": 1}),), returns=(SourceIntentReturn("scores", "t1"),))
    bindings = (BoundedBackendBinding(capability(), DAGTarget.C11),)
    result = compile_bounded_source_intent(module, bindings)
    primitive = json.dumps(result.artifacts.files(), sort_keys=True, separators=(",", ":")).encode()
    assert sha256(primitive).hexdigest() == (
        "974e683c19636e91ba879006f3f3e6c7dc7db03e0f8be1c5b1034b2c45bb0005")
    artifact = emit_bounded_c11_entrypoint(module, bindings, result)
    public = json.dumps(artifact.files(), sort_keys=True, separators=(",", ":")).encode()
    assert sha256(public).hexdigest() == (
        "1a4300ee3e3a9971ef4a89e29068bf11dada08a623d80a9b38a336de128d32c3")


@pytest.mark.parametrize("rhs,expected", [([2.0], [2.0, -4.0, 6.0, -8.0, 10.0, -12.0]),
    ([2.0, 3.0, -4.0], [2.0, -6.0, -12.0, -8.0, 15.0, 24.0])])
def test_independent_binary32_contract_witness_for_rhs_indices(rhs, expected):
    # Independent scalar oracle for corpus expectations, not a C interpreter or native proof.
    values = [1.0, -2.0, 3.0, -4.0, 5.0, -6.0]
    outputs = [struct.unpack("<f", struct.pack("<f", value * rhs[i % len(rhs)]))[0]
               for i, value in enumerate(values)]
    assert outputs == expected
