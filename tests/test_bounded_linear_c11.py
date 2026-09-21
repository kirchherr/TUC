"""Pure Linear lowering/checked-C11 security tests; never execute native code."""

import json
from dataclasses import fields, replace
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
from tuc.backends.bounded_dag import DAGTarget, lower_bounded_dag
from tuc.backends.bounded_linear_dag import (
    lower_bounded_linear_dag,
    validate_bounded_linear_dag_artifacts,
)
from tuc.compiler import compile_graph, emit_bounded_c11_entrypoint
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
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


def raw_graph(m=2, k=3, n=4):
    x, w, y = TensorRef("x", (m, k)), TensorRef("w", (n, k)), TensorRef("y", (m, n))
    return ComputeGraph("linear", (ComputeOperation(
        "linear", OperationKind.MATMUL, (x, w), (y,), {"rhs_transposed": True}),))


def compile_linear(graph=None, target=DAGTarget.C11):
    cap = capability(target)
    result = compile_graph(raw_graph() if graph is None else graph, (cap,),
                           include_candidate_scores=True)
    return result, {cap.name: target}


def source(m=2, k=3, n=4):
    return SourceIntentModule("linear", (
        SourceIntentTensor("x", (m, k)), SourceIntentTensor("w", (n, k)),
        SourceIntentTensor("y", (m, n))), (
        SourceIntentOperation("linear", "matmul", ("x", "w"), ("y",),
                              attributes={"rhs_transposed": True}),
    ), returns=(SourceIntentReturn("scores", "y"),))


def lower(graph=None, target=DAGTarget.C11):
    compilation, targets = compile_linear(graph, target)
    return lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("m,k,n", [(2, 3, 4), (3, 2, 5), (1, 1, 1), (1, 3, 4),
                                  (2, 1, 4), (2, 3, 1), (64, 64, 64)])
def test_shapes_work_storage_and_checked_indices(m, k, n):
    compilation, targets = compile_linear(raw_graph(m, k, n))
    artifact = lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)
    validate_bounded_linear_dag_artifacts(artifact, compilation.hac_ir,
                                         compilation.partition_plan, targets)
    manifest = json.loads(artifact.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_linear_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "matmul_rhs_transposed"
    assert manifest["scalar_work"] == 2 * m * k * n
    assert manifest["planned_buffer_bytes"] == 4 * (m * k + n * k + m * n)
    assert len(manifest["tensors"]) == len(manifest["buffers"]) == 3
    assert manifest["planned_copy_bytes"] == 0
    assert manifest["cuda_source_emitted"] is False
    assert manifest["numeric_policy"]["transpose_temporary_bytes"] == 0
    assert f"input_1[column * {k}U + k]" in artifact.c11_source
    assert "TUC_LINEAR_MATMUL_RHS_TRANSPOSED=5" in artifact.schedule_header
    assert artifact.cuda_source.startswith('#error "bounded Linear DAG is CPU-only;')
    module, bindings = source(m, k, n), (BoundedBackendBinding(capability(), DAGTarget.C11),)
    public = compile_bounded_source_intent(module, bindings)
    checked = emit_bounded_c11_entrypoint(module, bindings, public)
    assert f"a1[(i % {n}U) * {k}U + k]" in checked.source
    assert "if (!tuc_multiply(" in checked.source
    assert "if (!tuc_add(sum, product, &sum))" in checked.source
    assert json.loads(checked.manifest_json)["scratch_bytes"] == 4 * (m * k + n * k + m * n)


@pytest.mark.parametrize("flag", [False, 1, 0, 1.0, "true", None, (), {}, object()],
                         ids=range(9))
def test_rhs_transposed_requires_exact_true_before_emission(flag, monkeypatch):
    compilation, targets = compile_linear()
    operation = compilation.hac_ir.graph.operations[0]
    attributes = dict(operation.attributes, rhs_transposed=flag)
    object.__setattr__(operation, "attributes", MappingProxyType(attributes))
    monkeypatch.setattr("tuc.backends.bounded_linear_dag._primitives",
                        lambda _: pytest.fail("emission before validation"))
    with pytest.raises(ValueError):
        lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("shapes", [((2,), (4, 3), (2, 4)), ((2, 3), (4,), (2, 4)),
                                   ((2, 3), (3, 4), (2, 4)), ((2, 3), (4, 3), (4, 2)),
                                   ((2, 3), (4, 3), (2,)), ((True, 3), (4, 3), (2, 4)),
                                   ((65, 3), (4, 3), (65, 4))])
def test_mutated_tensor_shapes_fail_closed(shapes):
    compilation, targets = compile_linear()
    op = compilation.hac_ir.graph.operations[0]
    for tensor, shape in zip((*op.inputs, *op.outputs), shapes, strict=True):
        object.__setattr__(tensor, "shape", shape)
    with pytest.raises(ValueError):
        lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("attributes", [{"transpose_rhs": True}, {"rhs_transposed": True,
    "axis": 1}, {"rhs_transposed": True, "kernel": "linear"}, {"rhs_transposed": True,
    "tuc.layout": LayoutKind.COLUMN_MAJOR}, {"rhs_transposed": True,
    "tuc.layout_tile_shape": (2, 3)}])
def test_semantic_aliases_unknown_attributes_and_layouts_reject(attributes):
    compilation, targets = compile_linear()
    op = compilation.hac_ir.graph.operations[0]
    attrs = {k: v for k, v in op.attributes.items() if k != "rhs_transposed"}
    attrs.update(attributes)
    object.__setattr__(op, "attributes", MappingProxyType(attrs))
    with pytest.raises(ValueError):
        lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("which", ["module", "graph", "operation", "tensor", "partition",
                                    "assignment", "score", "artifact"])
def test_exact_records_reject_instance_hooks(which):
    compilation, targets = compile_linear()
    artifact = lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)
    module, partition = compilation.hac_ir, compilation.partition_plan
    objects = {"module": module, "graph": module.graph, "operation": module.graph.operations[0],
               "tensor": module.graph.operations[0].inputs[0], "partition": partition,
               "assignment": partition.assignments[0], "score": partition.candidate_scores[0],
               "artifact": artifact}
    object.__setattr__(objects[which], "dump", lambda: pytest.fail("untrusted hook"))
    with pytest.raises(ValueError):
        validate_bounded_linear_dag_artifacts(artifact, module, partition, targets)


def test_proxy_provenance_and_dataclass_field_shadow_reject_without_hooks():
    class Trap(dict):
        def __iter__(self):
            pytest.fail("untrusted iteration")

        def items(self):
            pytest.fail("untrusted items")

        def values(self):
            pytest.fail("untrusted fields")

    compilation, targets = compile_linear()
    op = compilation.hac_ir.graph.operations[0]
    object.__setattr__(op, "attributes", MappingProxyType(Trap(dict(op.attributes))))
    with pytest.raises(ValueError):
        lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)
    fake = object.__new__(type(compilation.hac_ir))
    object.__setattr__(fake, "__dataclass_fields__", Trap())
    with pytest.raises(ValueError):
        lower_bounded_linear_dag(fake, compilation.partition_plan, targets)


def test_cpu_only_and_frozen_lowerers_never_accept_linear():
    compilation, targets = compile_linear(target=DAGTarget.CUDA_SM86)
    with pytest.raises(ValueError):
        lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)
    compilation, targets = compile_linear()
    for old in (lower_bounded_dag, lower_bounded_add_dag):
        with pytest.raises(ValueError):
            old(compilation.hac_ir, compilation.partition_plan, targets)
    op = raw_graph().operations[0]
    ordinary = replace(op, inputs=(op.inputs[0], TensorRef("w", (3, 4))), attributes={})
    with pytest.raises(ValueError, match="scope"):
        lower(ComputeGraph("ordinary", (ordinary,)))


@pytest.mark.parametrize("field", [item.name for item in fields(type(lower()))])
def test_every_artifact_field_bound(field):
    compilation, targets = compile_linear()
    artifact = lower_bounded_linear_dag(compilation.hac_ir, compilation.partition_plan, targets)
    with pytest.raises(ValueError):
        validate_bounded_linear_dag_artifacts(replace(artifact, **{
            field: getattr(artifact, field) + " "}), compilation.hac_ir,
            compilation.partition_plan, targets)


def test_work_budget_counts_both_linear_and_ordinary_operations():
    tensors = tuple(TensorRef(name, (64, 64)) for name in ("x", "w", "p", "z", "y"))
    graph = ComputeGraph("too_much_work", (
        ComputeOperation("linear", OperationKind.MATMUL, tensors[:2], (tensors[2],),
                         {"rhs_transposed": True}),
        ComputeOperation("ordinary", OperationKind.MATMUL, (tensors[2], tensors[3]), (tensors[4],)),
    ))
    with pytest.raises(ValueError, match="budget"):
        lower(graph)


def test_renamed_symbols_do_not_change_primitives_and_public_application_is_inert():
    graph = raw_graph()
    op = graph.operations[0]
    tensors = tuple(replace(t, name=f"renamed{i}") for i, t in enumerate((*op.inputs, *op.outputs)))
    renamed = ComputeGraph("renamed", (replace(op, name="different", inputs=tensors[:2],
                                               outputs=tensors[2:]),))
    assert lower(graph).c11_source == lower(renamed).c11_source
    module, bindings = source(), (BoundedBackendBinding(capability(), DAGTarget.C11),)
    app = prepare_bounded_c11_application(module, bindings)
    assert json.loads(app.application_json)["native_execution_observed"] is False


@pytest.mark.parametrize("shapes", [((2, 3), (4, 3), (2, 4)), ((1, 1), (1, 1), (1, 1))])
def test_private_closed_descriptor_support(shapes):
    spec = C11GraphSpec(shapes, (C11OperationSpec("matmul_rhs_transposed", (0, 1), 2),),
                        (0, 1), (2,))
    scratch, work = validate_spec(spec)
    assert work == 2 * shapes[0][0] * shapes[0][1] * shapes[1][0]
    assert scratch == sum(a * b * 4 for a, b in shapes)
    assert "static int tuc_multiply(" in emit_checked_graph(spec, "a" * 64)[1]


@pytest.mark.parametrize("change", ["shape", "arity", "output", "flag-alias", "duplicate",
                                    "ssa", "bool-index", "extra-field"])
def test_private_closed_descriptor_rejections(change):
    op = C11OperationSpec("matmul_rhs_transposed", (0, 1), 2)
    spec = C11GraphSpec(((2, 3), (4, 3), (2, 4)), (op,), (0, 1), (2,))
    if change == "shape":
        spec = replace(spec, tensor_shapes=((2, 3), (3, 4), (2, 4)))
    elif change == "arity":
        object.__setattr__(op, "inputs", (0,))
    elif change == "output":
        object.__setattr__(op, "output", 0)
    elif change == "flag-alias":
        object.__setattr__(op, "kind", "linear")
    elif change == "duplicate":
        spec = replace(spec, operations=(op, op))
    elif change == "ssa":
        spec = replace(spec, input_tensors=(0, 2))
    elif change == "bool-index":
        object.__setattr__(op, "inputs", (False, 1))
    else:
        object.__setattr__(op, "__dataclass_fields__", object())
    with pytest.raises(ValueError):
        emit_checked_graph(spec, "a" * 64)
