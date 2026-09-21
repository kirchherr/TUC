"""Pure checked multiplication lowering tests, including hostile typed records."""

import json
from dataclasses import fields, replace
from math import prod
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
from tuc.backends.bounded_mul_dag import (
    lower_bounded_mul_dag,
    validate_bounded_mul_dag_artifacts,
)
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
    return BackendCapability(
        "cpu" if target is DAGTarget.C11 else "gpu",
        frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}),
        memory_domain=(MemoryDomainKind.HOST_RAM if target is DAGTarget.C11
                       else MemoryDomainKind.UNKNOWN),
    )


def raw_graph(shape=(2, 3), square=False):
    x, scale, y = TensorRef("x", shape), TensorRef("scale", shape), TensorRef("y", shape)
    return ComputeGraph("mul", (ComputeOperation(
        "multiply", OperationKind.ELEMENTWISE, (x, x if square else scale), (y,),
        {"kernel": "mul"}),))


def compile_mul(graph=None, target=DAGTarget.C11):
    cap = capability(target)
    result = compile_graph(raw_graph() if graph is None else graph, (cap,),
                           include_candidate_scores=True)
    return result, {cap.name: target}


def lower(graph=None, target=DAGTarget.C11):
    compilation, targets = compile_mul(graph, target)
    return lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)


def source(shape=(2, 3), square=False):
    return SourceIntentModule("mul", (
        SourceIntentTensor("x", shape),
        *((SourceIntentTensor("scale", shape),) if not square else ()),
        SourceIntentTensor("y", shape)), (
        SourceIntentOperation("multiply", "elementwise", ("x", "x" if square else "scale"),
                              ("y",), attributes={"elementwise_kind": "mul"}),
    ), returns=(SourceIntentReturn("scores", "y"),))


@pytest.mark.parametrize("shape", [(1,), (5,), (64,), (1, 1), (1, 7), (5, 1), (2, 3), (64, 64)])
@pytest.mark.parametrize("square", [False, True])
def test_exact_shapes_work_no_broadcast_or_extra_storage_and_checked_helper(shape, square):
    compilation, targets = compile_mul(raw_graph(shape, square))
    artifact = lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)
    validate_bounded_mul_dag_artifacts(artifact, compilation.hac_ir,
                                      compilation.partition_plan, targets)
    manifest = json.loads(artifact.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_mul_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "mul"
    assert manifest["scalar_work"] == prod(shape)
    assert manifest["planned_buffer_bytes"] == 4 * prod(shape) * (2 if square else 3)
    assert len(manifest["input_tensors"]) == (1 if square else 2)
    assert manifest["planned_copy_bytes"] == 0 and manifest["cuda_source_emitted"] is False
    assert "volatile float value = input_0[index] * input_1[index];" in artifact.c11_source
    assert "TUC_MUL_EQUAL_PRODUCT=6" in artifact.schedule_header
    assert artifact.cuda_source.startswith('#error "bounded Mul DAG is CPU-only;')
    module, bindings = source(shape, square), (BoundedBackendBinding(capability(), DAGTarget.C11),)
    public = compile_bounded_source_intent(module, bindings)
    checked = emit_bounded_c11_entrypoint(module, bindings, public)
    assert "if (!tuc_multiply(a0[i], a1[i], &out[i])) return 0;" in checked.source
    assert "static int tuc_multiply(" in checked.source
    assert "static int tuc_add(" not in checked.source
    numeric = json.loads(checked.manifest_json)["numeric_policy"]
    assert numeric["multiplication_shapes"] == "equal_rank1_or_rank2_without_broadcasting"
    if square:
        assert "tuc_op_0(tensor_0, tensor_0, tensor_1)" in checked.source


@pytest.mark.parametrize("shapes", [((2, 3), (3,), (2, 3)), ((3,), (2, 3), (2, 3)),
                                   ((2, 3), (2, 1), (2, 3)), ((2, 3), (3, 2), (2, 3)),
                                   ((2, 3), (2, 3), (3, 2)), ((2, 3), (), (2, 3)),
                                   ((True, 3), (2, 3), (2, 3)), ((65,), (65,), (65,))])
def test_broadcast_rank_bounds_and_output_shapes_reject_before_emission(shapes, monkeypatch):
    compilation, targets = compile_mul()
    op = compilation.hac_ir.graph.operations[0]
    for tensor, shape in zip((*op.inputs, *op.outputs), shapes, strict=True):
        object.__setattr__(tensor, "shape", shape)
    monkeypatch.setattr("tuc.backends.bounded_mul_dag._primitives",
                        lambda _: pytest.fail("emission before validation"))
    with pytest.raises(ValueError):
        lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("attrs", [{"kernel": "multiply"}, {"elementwise_kind": "mul"},
    {"kernel": "mul", "axis": 1}, {"kernel": "mul", "rhs_transposed": True},
    {"kernel": "mul", "tuc.layout": LayoutKind.COLUMN_MAJOR},
    {"kernel": "mul", "tuc.layout_tile_shape": (2, 3)}, {"kernel": True}, {"kernel": object()}])
def test_unknown_semantics_aliases_layout_and_kernel_types_reject(attrs):
    compilation, targets = compile_mul()
    op = compilation.hac_ir.graph.operations[0]
    merged = {key: value for key, value in op.attributes.items() if key != "kernel"}
    merged.update(attrs)
    object.__setattr__(op, "attributes", MappingProxyType(merged))
    with pytest.raises(ValueError):
        lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("which", ["module", "graph", "operation", "tensor", "partition",
                                    "assignment", "score", "artifact"])
def test_exact_record_fields_reject_shadowed_hooks(which):
    compilation, targets = compile_mul()
    artifact = lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)
    module, partition = compilation.hac_ir, compilation.partition_plan
    objects = {"module": module, "graph": module.graph, "operation": module.graph.operations[0],
               "tensor": module.graph.operations[0].inputs[0], "partition": partition,
               "assignment": partition.assignments[0], "score": partition.candidate_scores[0],
               "artifact": artifact}
    object.__setattr__(objects[which], "dump", lambda: pytest.fail("caller hook"))
    with pytest.raises(ValueError):
        validate_bounded_mul_dag_artifacts(artifact, module, partition, targets)


def test_proxy_and_shadowed_dataclass_fields_cannot_trigger_hooks():
    class Trap(dict):
        def __iter__(self):
            pytest.fail("caller iteration")

        def items(self):
            pytest.fail("caller items")

        def values(self):
            pytest.fail("caller fields")

    compilation, targets = compile_mul()
    op = compilation.hac_ir.graph.operations[0]
    object.__setattr__(op, "attributes", MappingProxyType(Trap(dict(op.attributes))))
    with pytest.raises(ValueError):
        lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)
    fake = object.__new__(type(compilation.hac_ir))
    object.__setattr__(fake, "__dataclass_fields__", Trap())
    with pytest.raises(ValueError):
        lower_bounded_mul_dag(fake, compilation.partition_plan, targets)


def test_cpu_only_and_prior_frozen_lowerers_reject_mul():
    compilation, targets = compile_mul(target=DAGTarget.CUDA_SM86)
    with pytest.raises(ValueError):
        lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)
    compilation, targets = compile_mul()
    for old in (lower_bounded_dag, lower_bounded_add_dag, lower_bounded_linear_dag):
        with pytest.raises(ValueError):
            old(compilation.hac_ir, compilation.partition_plan, targets)
    op = raw_graph().operations[0]
    with pytest.raises(ValueError, match="scope"):
        lower(ComputeGraph("add", (replace(op, attributes={"kernel": "add"}),)))


@pytest.mark.parametrize("field", [item.name for item in fields(BoundedDAGArtifacts)])
def test_every_artifact_field_bound(field):
    compilation, targets = compile_mul()
    artifact = lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)
    with pytest.raises(ValueError):
        validate_bounded_mul_dag_artifacts(replace(artifact, **{
            field: getattr(artifact, field) + " "}), compilation.hac_ir,
            compilation.partition_plan, targets)


@pytest.mark.parametrize("change", ["arity", "inplace", "dtype", "metadata-budget", "op-budget"])
def test_structural_mutations_fail_closed(change):
    compilation, targets = compile_mul()
    op = compilation.hac_ir.graph.operations[0]
    if change == "arity":
        object.__setattr__(op, "inputs", op.inputs[:1])
    elif change == "inplace":
        object.__setattr__(op, "outputs", (op.inputs[0],))
    elif change == "dtype":
        object.__setattr__(op.inputs[1], "dtype", "float16")
    elif change == "metadata-budget":
        object.__setattr__(op, "attributes", MappingProxyType({
            "kernel": "mul", "tuc.x": "x"*70000}))
    else:
        object.__setattr__(compilation.hac_ir.graph, "operations", (op,)*9)
    with pytest.raises(ValueError):
        lower_bounded_mul_dag(compilation.hac_ir, compilation.partition_plan, targets)


def test_private_descriptor_mul_only_and_mul_relu_helper_selection():
    square = C11GraphSpec(((3,), (3,)), (C11OperationSpec("mul", (0, 0), 1),), (0,), (1,))
    assert validate_spec(square) == (24, 3)
    assert "static int tuc_add(" not in emit_checked_graph(square, "a"*64)[1]
    relu = C11GraphSpec(((3,), (3,), (3,)), (C11OperationSpec("mul", (0, 0), 1),
        C11OperationSpec("relu", (1,), 2)), (0,), (2,))
    assert "static int tuc_add(" not in emit_checked_graph(relu, "a"*64)[1]
    assert "static int tuc_multiply(" in emit_checked_graph(relu, "a"*64)[1]


@pytest.mark.parametrize("shapes", [((2, 3), (3,), (2, 3)), ((2,), (2,), (1, 2)),
                                   ((1, 2), (2, 1), (1, 2))])
def test_private_descriptor_never_broadcasts(shapes):
    spec = C11GraphSpec(shapes, (C11OperationSpec("mul", (0, 1), 2),), (0, 1), (2,))
    with pytest.raises(ValueError):
        emit_checked_graph(spec, "a"*64)
