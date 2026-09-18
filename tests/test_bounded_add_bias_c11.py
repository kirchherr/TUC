"""Pure Add/Bias graph, checked C11 and hostile-data tests; no native execution."""

import json
import struct
from dataclasses import fields, replace
from hashlib import sha256
from types import MappingProxyType

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_add_dag import (
    lower_bounded_add_dag,
    validate_bounded_add_dag_artifacts,
)
from tuc.backends.bounded_c11_codegen import (
    C11GraphSpec,
    C11OperationSpec,
    emit_checked_graph,
    validate_spec,
)
from tuc.backends.bounded_dag import DAGTarget, lower_bounded_dag
from tuc.compiler import compile_graph, emit_bounded_c11_entrypoint
from tuc.compiler.bounded_c11_application import (
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
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


def add_graph(lhs=(2, 3), rhs=(3,), out=None, attrs=None):
    tensors = (TensorRef("left", lhs), TensorRef("right", rhs),
               TensorRef("result", lhs if out is None else out))
    return ComputeGraph("add_graph", (ComputeOperation(
        "combine", OperationKind.ELEMENTWISE, tensors[:2], tensors[2:],
        {"kernel": "add"} if attrs is None else attrs),))


def compile_add(graph=None, target=DAGTarget.C11):
    cap = capability(target)
    result = compile_graph(add_graph() if graph is None else graph, (cap,),
                           include_candidate_scores=True)
    return result, {cap.name: target}


def lower(graph=None, target=DAGTarget.C11):
    compilation, targets = compile_add(graph, target)
    return lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)


def forged(value, **changes):
    result = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(result, field.name, changes.get(field.name, getattr(value, field.name)))
    return result


@pytest.mark.parametrize("lhs,rhs,kind", [
    ((5,), (5,), "add"), ((1,), (1,), "add"), ((2, 3), (2, 3), "add"),
    ((2, 3), (3,), "add_row_bias"), ((1, 3), (3,), "add_row_bias"),
    ((3, 1), (1,), "add_row_bias"), ((64, 64), (64,), "add_row_bias"),
])
def test_shape_contract_manifest_primitives_and_schedule(lhs, rhs, kind):
    compilation, targets = compile_add(add_graph(lhs, rhs))
    artifact = lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)
    validate_bounded_add_dag_artifacts(artifact, compilation.hac_ir,
                                      compilation.partition_plan, targets)
    manifest = json.loads(artifact.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_add_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == kind
    assert manifest["operations"][0]["inputs"] == [0, 1]
    assert manifest["operations"][0]["outputs"] == [2]
    assert manifest["operations"][0]["input_shapes"] == [list(lhs), list(rhs)]
    assert manifest["scalar_work"] == len(range(lhs[0])) * (lhs[1] if len(lhs) == 2 else 1)
    assert manifest["planned_copy_bytes"] == 0
    assert {buffer["space"] for buffer in manifest["buffers"]} == {"host"}
    assert manifest["input_tensors"] == [0, 1] and manifest["output_tensors"] == [2]
    assert [e["kind"] for e in manifest["events"]] == [
        "bind_input", "bind_input", "execute", "publish_output"]
    assert manifest["native_execution_observed"] is manifest["normal_runtime_admission"] is False
    assert manifest["cuda_source_emitted"] is False
    assert "cuda_symbol" not in manifest["operations"][0]
    assert "launch" not in manifest["operations"][0]
    assert artifact.cuda_source.startswith("#error ")
    assert "TUC_ADD_EQUAL=3, TUC_ADD_ROW_BIAS=4" in artifact.schedule_header
    rhs_index = "index" if kind == "add" else f"index % {lhs[1]}U"
    assert f"volatile float value = input_0[index] + input_1[{rhs_index}];" in artifact.c11_source
    for name, text in artifact.files().items():
        if name != "manifest.json":
            assert manifest["source_digests"][name] == "sha256:" + sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("lhs,rhs,out", [
    ((3,), (1,), (3,)), ((3,), (2, 3), (2, 3)), ((2, 3), (2,), (2, 3)),
    ((2, 3), (1, 3), (2, 3)), ((2, 3), (2, 1), (2, 3)),
    ((2, 3), (3,), (3, 2)), ((2, 3), (2, 3), (6,)),
])
def test_no_general_broadcasting_or_wrong_output_shape(lhs, rhs, out):
    with pytest.raises(ValueError):
        lower(add_graph(lhs, rhs, out))


@pytest.mark.parametrize("attributes", [
    {"kernel": "add", "axis": 1}, {"kernel": "add", "broadcast": "row"},
    {"kernel": "add", "elementwise_kind": "add"}, {"kernel": "add", "max_error_budget": True},
    {"kernel": "add", "prefer_sparsity": 1}, {"kernel": "add", "max_error_budget": -1},
])
def test_unrecognized_or_mistyped_semantics_reject(attributes):
    with pytest.raises((ValueError, TypeError)):
        lower(add_graph(attrs=attributes))


def test_cuda_and_legacy_lowerer_stay_closed_to_add():
    compilation, targets = compile_add(target=DAGTarget.CUDA_SM86)
    with pytest.raises(ValueError, match="CPU"):
        lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)
    compilation, targets = compile_add()
    with pytest.raises(ValueError):
        lower_bounded_dag(compilation.hac_ir, compilation.partition_plan, targets)


def test_extension_does_not_replace_legacy_no_add_emission():
    x, y = TensorRef("x", (2, 3)), TensorRef("y", (2, 3))
    graph = ComputeGraph("relu_only", (ComputeOperation(
        "relu", OperationKind.ELEMENTWISE, (x,), (y,), {"kernel": "relu"}),))
    compilation, targets = compile_add(graph)
    with pytest.raises(ValueError, match="scope"):
        lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)
    original = lower_bounded_dag(compilation.hac_ir, compilation.partition_plan, targets)
    assert json.loads(original.manifest_json)["schema_version"] == "tuc.bounded_dag_artifacts.v0"


@pytest.mark.parametrize("field", ["manifest_json", "c11_header", "c11_source", "cuda_source",
                                   "schedule_header"])
def test_artifact_validation_binds_every_field(field):
    compilation, targets = compile_add()
    artifact = lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)
    changed = replace(artifact, **{field: getattr(artifact, field) + " "})
    with pytest.raises(ValueError):
        validate_bounded_add_dag_artifacts(changed, compilation.hac_ir,
                                          compilation.partition_plan, targets)


@pytest.mark.parametrize("which", ["module", "graph", "operation", "tensor", "partition",
                                   "assignment", "score", "artifact"])
def test_record_method_shadowing_rejects_without_call(which):
    compilation, targets = compile_add()
    module, partition = compilation.hac_ir, compilation.partition_plan
    artifact = lower_bounded_add_dag(module, partition, targets)
    objects = {"module": module, "graph": module.graph, "operation": module.graph.operations[0],
               "tensor": module.graph.operations[0].inputs[0], "partition": partition,
               "assignment": partition.assignments[0], "score": partition.candidate_scores[0],
               "artifact": artifact}
    object.__setattr__(objects[which], "unexpected_hook", lambda: pytest.fail("hook called"))
    with pytest.raises(ValueError):
        validate_bounded_add_dag_artifacts(artifact, module, partition, targets)


def test_proxy_backed_by_custom_mapping_cannot_invoke_hooks():
    class HostileDict(dict):
        def __len__(self):
            pytest.fail("untrusted length")

        def items(self):
            pytest.fail("untrusted items")

        def __iter__(self):
            pytest.fail("untrusted iteration")

    compilation, targets = compile_add()
    operation = compilation.hac_ir.graph.operations[0]
    bad = MappingProxyType(HostileDict(dict(operation.attributes)))
    object.__setattr__(operation, "attributes", bad)
    with pytest.raises(ValueError, match="proxy"):
        lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)


def test_dataclass_fields_shadow_cannot_trigger_caller_iteration():
    class Trap:
        def values(self):
            pytest.fail("untrusted dataclass field traversal")

    compilation, targets = compile_add()
    module = object.__new__(type(compilation.hac_ir))
    object.__setattr__(module, "__dataclass_fields__", Trap())
    with pytest.raises(ValueError):
        lower_bounded_add_dag(module, compilation.partition_plan, targets)


@pytest.mark.parametrize("change", ["bool-dimension", "tuple-subclass", "tensor-subclass",
                                    "extra-metadata", "wrong-layout", "tile", "kind", "arity"])
def test_hostile_graph_records_are_rejected(change):
    compilation, targets = compile_add()
    operation = compilation.hac_ir.graph.operations[0]
    if change == "bool-dimension":
        object.__setattr__(operation.inputs[0], "shape", (True, 3))
    elif change == "tuple-subclass":
        class HostileTuple(tuple):
            def __iter__(self):
                pytest.fail("untrusted tuple iteration")
        object.__setattr__(operation, "inputs", HostileTuple(operation.inputs))
    elif change == "tensor-subclass":
        class HostileTensor(TensorRef):
            pass
        object.__setattr__(operation, "inputs", (HostileTensor("left", (2, 3)),
                                                 operation.inputs[1]))
    elif change == "extra-metadata":
        object.__setattr__(operation, "attributes", MappingProxyType({"kernel": object()}))
    elif change in ("wrong-layout", "tile"):
        attributes = dict(operation.attributes)
        attributes["tuc.layout" if change == "wrong-layout" else "tuc.layout_tile_shape"] = (
            LayoutKind.COLUMN_MAJOR if change == "wrong-layout" else (2, 3))
        object.__setattr__(operation, "attributes", MappingProxyType(attributes))
    elif change == "kind":
        object.__setattr__(operation, "kind", "elementwise")
    else:
        object.__setattr__(operation, "inputs", operation.inputs[:1])
    with pytest.raises(ValueError):
        lower_bounded_add_dag(compilation.hac_ir, compilation.partition_plan, targets)


@pytest.mark.parametrize("change", ["fallback", "override", "transfers", "candidate-object",
                                    "wrong-domain", "bool-bytes", "name", "target-alias"])
def test_partition_escape_routes_reject(change):
    compilation, targets = compile_add()
    partition = compilation.partition_plan
    assignment = partition.assignments[0]
    if change == "fallback":
        partition = replace(partition, assignments=(replace(assignment, reason="fallback:cpu"),))
    elif change == "override":
        partition = forged(partition, override_effects=(object(),))
    elif change == "transfers":
        partition = forged(partition, transfer_edges=(object(),))
    elif change == "candidate-object":
        partition = forged(partition, candidate_scores=(object(),))
    elif change == "wrong-domain":
        partition = replace(partition, assignments=(replace(
            assignment, memory_domain=MemoryDomainKind.UNKNOWN),))
    elif change == "bool-bytes":
        partition = replace(partition, assignments=(replace(assignment, transfer_bytes=False),))
    elif change == "name":
        partition = replace(partition, graph_name="other")
    else:
        targets = {**targets, "other": DAGTarget.C11}
    with pytest.raises(ValueError):
        lower_bounded_add_dag(compilation.hac_ir, partition, targets)


def test_scratch_budget_rejects_disconnected_large_additions():
    operations = []
    for i in range(8):
        x, y, z = (TensorRef(f"t{i}_{n}", (64, 64)) for n in range(3))
        operations.append(ComputeOperation(f"add{i}", OperationKind.ELEMENTWISE, (x, y), (z,),
                                           {"kernel": "add"}))
    with pytest.raises(ValueError, match="budget"):
        lower(ComputeGraph("large", tuple(operations)))


def test_scalar_work_budget_accounts_for_legacy_operations_together_with_add():
    x, y, p, q, z = (TensorRef(name, (64, 64)) for name in ("x", "y", "p", "q", "z"))
    graph = ComputeGraph("expensive", (
        ComputeOperation("mm0", OperationKind.MATMUL, (x, y), (p,)),
        ComputeOperation("mm1", OperationKind.MATMUL, (p, y), (q,)),
        ComputeOperation("add", OperationKind.ELEMENTWISE, (q, x), (z,), {"kernel": "add"}),
    ))
    with pytest.raises(ValueError, match="budget"):
        lower(graph)


@pytest.mark.parametrize("kind,shapes", [
    ("add", ((5,), (5,), (5,))), ("add", ((2, 3), (2, 3), (2, 3))),
    ("add_row_bias", ((2, 3), (3,), (2, 3))),
])
def test_checked_c11_performs_exact_one_guarded_add_per_result(kind, shapes):
    spec = C11GraphSpec(shapes, (C11OperationSpec(kind, (0, 1), 2),), (0, 1), (2,))
    scratch, work = validate_spec(spec)
    assert scratch == sum(4 * len(range(s[0])) * (s[1] if len(s) == 2 else 1) for s in shapes)
    assert work == shapes[0][0] * (shapes[0][1] if len(shapes[0]) == 2 else 1)
    header, source, symbol = emit_checked_graph(spec, "a" * 64)
    assert symbol in header
    right = "i" if kind == "add" else "i % 3U"
    assert f"if (!tuc_add(a0[i], a1[{right}], &out[i])) return 0;" in source
    assert "volatile float rounded = left + right;" in source
    assert source.index("tuc_op_0(tensor_0, tensor_1, tensor_2)") < source.index(
        "memcpy(out[0].data, tensor_2")
    assert "(csr & 0x1f80U) != 0x1f80U" in source


@pytest.mark.parametrize("kind,shapes,inputs", [
    ("add", ((2, 3), (3,), (2, 3)), (0, 1)),
    ("add_row_bias", ((2, 3), (2, 3), (2, 3)), (0, 1)),
    ("add_row_bias", ((3,), (3,), (3,)), (0, 1)),
    ("add", ((2, 3), (2, 3), (2, 3)), (0,)),
    ("add", ((2, 3), (2, 3), (3, 2)), (0, 1)),
])
def test_checked_codegen_keeps_normalized_kind_and_arity_exact(kind, shapes, inputs):
    spec = C11GraphSpec(shapes, (C11OperationSpec(kind, inputs, 2),), (0, 1), (2,))
    with pytest.raises(ValueError):
        emit_checked_graph(spec, "a" * 64)


def source_program():
    tensors = tuple(SourceIntentTensor(name, shape) for name, shape in (
        ("x", (2, 3)), ("weights", (3, 4)), ("bias", (4,)), ("residual", (2, 4)),
        ("p", (2, 4)), ("biased", (2, 4)), ("active", (2, 4)), ("joined", (2, 4)), ("rows", (2,)),
    ))
    return SourceIntentModule("bias_residual", tensors, (
        SourceIntentOperation("p", "matmul", ("x", "weights"), ("p",)),
        SourceIntentOperation("biased", "elementwise", ("p", "bias"), ("biased",),
                              attributes={"elementwise_kind": "add"}),
        SourceIntentOperation("active", "elementwise", ("biased",), ("active",),
                              attributes={"elementwise_kind": "relu"}),
        SourceIntentOperation("joined", "elementwise", ("active", "residual"), ("joined",),
                              attributes={"elementwise_kind": "add"}),
        SourceIntentOperation("rows", "reduction", ("joined",), ("rows",), attributes={"axis": 1}),
    ), returns=(SourceIntentReturn("scores", "rows"),))


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def test_complete_source_to_application_path_and_independent_manifest_replay():
    source = source_program()
    bindings = (BoundedBackendBinding(capability(), DAGTarget.C11),)
    compilation = compile_bounded_source_intent(source, bindings)
    manifest = json.loads(compilation.artifacts.manifest_json)
    artifact = emit_bounded_c11_entrypoint(source, bindings, compilation)
    application = prepare_bounded_c11_application(source, bindings)
    assert application.entrypoint == artifact
    values = {"x": (-1.0, 0.5, 2.0, 1.5, -2.0, 1.0),
              "weights": tuple(f32((i - 5) / 4.0) for i in range(12)),
              "bias": (-2.0, 0.5, 3.0, -1.0),
              "residual": (1.0, -0.5, -2.0, 0.25, 2.0, -1.0, 0.5, 3.0)}
    assert encode_bounded_c11_inputs(source, bindings, application, values).startswith(b"TUCIN001")
    # Direct math follows the application definition, independently of compiler indices.
    expected = []
    for row in range(2):
        total = 0.0
        for column in range(4):
            product = 0.0
            for k in range(3):
                product = f32(product + f32(values["x"][row * 3 + k] *
                                             values["weights"][k * 4 + column]))
            activated = max(0.0, f32(product + values["bias"][column]))
            total = f32(total + f32(activated + values["residual"][row * 4 + column]))
        expected.append(total)
    # Replay physical slot identity and operation inputs from the emitted manifest.
    slots, published = {}, []
    for event in manifest["events"]:
        if event["kind"] == "bind_input":
            slot = event["outputs"][0]
            tensor = manifest["tensors"][manifest["buffers"][slot]["tensor"]]
            slots[slot] = values[tensor["name"]]
        elif event["kind"] == "execute":
            op = manifest["operations"][event["operation"]]
            operands = [slots[i] for i in event["inputs"]]
            if op["kind"] == "matmul":
                rows, inner = op["input_shapes"][0]
                columns = op["output_shape"][1]
                output = []
                for r in range(rows):
                    for c in range(columns):
                        value = 0.0
                        for k in range(inner):
                            value = f32(value + f32(operands[0][r * inner + k] *
                                                    operands[1][k * columns + c]))
                        output.append(value)
            elif op["kind"] in ("add", "add_row_bias"):
                output = [f32(a + operands[1][i % len(operands[1])])
                          for i, a in enumerate(operands[0])]
            elif op["kind"] == "relu":
                output = [max(0.0, a) for a in operands[0]]
            else:
                columns = op["input_shapes"][0][1]
                output = []
                for start in range(0, len(operands[0]), columns):
                    value = 0.0
                    for a in operands[0][start:start + columns]:
                        value = f32(value + a)
                    output.append(value)
            slots[event["outputs"][0]] = tuple(output)
        elif event["kind"] == "publish_output":
            published.append(slots[event["inputs"][0]])
        else:
            pytest.fail("CPU Add graphs cannot contain transfers")
    assert published == [tuple(expected)]
    numeric = json.loads(artifact.manifest_json)["numeric_policy"]
    assert numeric["addition"] == "one_checked_binary32_addition_per_output_element"
