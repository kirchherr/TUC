"""Pure Softmax lowering checks; no C compilation or native execution evidence."""

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
from tuc.backends.bounded_softmax_dag import (
    lower_bounded_softmax_dag,
    validate_bounded_softmax_dag_artifacts,
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


def capability(target=DAGTarget.C11, *, softmax=True):
    kinds = {OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION}
    if softmax:
        kinds.add(OperationKind.SOFTMAX)
    return BackendCapability("cpu" if target is DAGTarget.C11 else "gpu", frozenset(kinds),
                             memory_domain=MemoryDomainKind.HOST_RAM if target is DAGTarget.C11
                             else MemoryDomainKind.UNKNOWN)


def raw_graph(shape=(2, 3)):
    x, y = TensorRef("x", shape), TensorRef("y", shape)
    return ComputeGraph("softmax", (ComputeOperation("normalize", OperationKind.SOFTMAX,
                                                     (x,), (y,), {"axis": 1}),))


def compiled(graph=None, target=DAGTarget.C11):
    cap = capability(target)
    result = compile_graph(raw_graph() if graph is None else graph, (cap,),
                           include_candidate_scores=True)
    return result, {cap.name: target}


def lower(graph=None):
    result, targets = compiled(graph)
    return lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)


def source(shape=(2, 3)):
    return SourceIntentModule("softmax", (SourceIntentTensor("x", shape),
                                          SourceIntentTensor("y", shape)), (
        SourceIntentOperation("normalize", "softmax", ("x",), ("y",), attributes={"axis": 1}),
    ), returns=(SourceIntentReturn("probabilities", "y"),))


@pytest.mark.parametrize("shape", [(1, 1), (1, 7), (5, 1), (2, 3), (3, 17), (64, 64)])
def test_softmax_shapes_work_storage_and_conditional_checked_emission(shape):
    result, targets = compiled(raw_graph(shape))
    artifact = lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)
    validate_bounded_softmax_dag_artifacts(artifact, result.hac_ir, result.partition_plan, targets)
    manifest = json.loads(artifact.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_softmax_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "softmax_axis1"
    assert manifest["scalar_work"] == 5 * math.prod(shape)
    assert manifest["planned_buffer_bytes"] == 8 * math.prod(shape)
    assert manifest["planned_copy_bytes"] == 0
    assert manifest["cuda_source_emitted"] is False
    assert manifest["native_execution_observed"] is False
    assert "TUC_BOUNDED_SOFTMAX_GENERATED_H" in artifact.c11_header
    assert "TUC_BOUNDED_SOFTMAX_SCHEDULE_H" in artifact.schedule_header
    assert "TUC_BOUNDED_MUL" not in artifact.c11_header + artifact.schedule_header
    assert "TUC_SOFTMAX_AXIS1=7" in artifact.schedule_header
    assert "expf(shift)" in artifact.c11_source
    assert "no CUDA source is emitted" in artifact.cuda_source
    module, bindings = source(shape), (BoundedBackendBinding(capability(), DAGTarget.C11),)
    public = compile_bounded_source_intent(module, bindings)
    checked = emit_bounded_c11_entrypoint(module, bindings, public)
    numeric = json.loads(checked.manifest_json)["numeric_policy"]
    assert numeric["softmax_rounded_shift_exp_sum_quotient_checked"] is True
    assert numeric["softmax_logit_range_cap"] is None
    assert numeric["libm_accuracy"] == "implementation_dependent_not_bitexact_across_libraries"
    assert "#include <math.h>" in checked.source
    assert "static int tuc_add(" in checked.source
    assert "static int tuc_multiply(" not in checked.source
    assert f"row < {shape[0]}U" in checked.source
    assert f"const size_t base = row * {shape[1]}U" in checked.source


def test_every_rounded_stage_is_classified_before_reuse_and_publication():
    spec = C11GraphSpec(((2, 3), (2, 3)), (C11OperationSpec("softmax_axis1", (0,), 1),),
                        (0,), (1,))
    text = emit_checked_graph(spec, "a" * 64)[1]
    stages = [
        "float maximum = a0[base];",
        "if (a0[base + column] > maximum) maximum = a0[base + column];",
        "float sum = 0.0F;",
        "volatile float rounded_shift = a0[base + column] - maximum;",
        "if (!tuc_normal(&shift)) return 0;",
        "volatile float rounded_exp = expf(shift);",
        "if (!tuc_normal(&exponential) || !(exponential > 0.0F)) return 0;",
        "if (!tuc_add(sum, exponential, &sum)) return 0;",
        "if (!tuc_normal(&sum) || !(sum > 0.0F)) return 0;",
        "volatile float rounded_quotient = out[base + column] / sum;",
        "if (!tuc_normal(&quotient) || !(quotient > 0.0F)) return 0;",
    ]
    offsets = [text.index(stage) for stage in stages]
    assert offsets == sorted(offsets)
    assert "if (!tuc_normal(&a0[base + column])) return 0;" in text
    assert text.index("if (!tuc_op_0(") < text.index("memcpy(out[0].data,")
    assert "const float value = rounded;" in text  # Existing checked sum helper.
    assert "(csr & 0xe040U) != 0U" in text and "(csr & 0x1f80U) != 0x1f80U" in text
    assert "#ifdef __FAST_MATH__" in text
    assert "malloc" not in text and "float scratch[" not in text


@pytest.mark.parametrize("axis", [None, False, True, 0, -1, 2, 1.0, "1", object()], ids=range(9))
def test_axis_requires_exact_integer_one_before_emission(axis, monkeypatch):
    result, targets = compiled()
    operation = result.hac_ir.graph.operations[0]
    object.__setattr__(operation, "attributes", MappingProxyType(dict(operation.attributes,
                                                                    axis=axis)))
    monkeypatch.setattr("tuc.backends.bounded_softmax_dag._primitives",
                        lambda _: pytest.fail("emission before validation"))
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("attrs", [{}, {"axis": 1, "kernel": "softmax"},
    {"axis": 1, "rhs_transposed": True}, {"axis": 1, "tuc.layout": LayoutKind.COLUMN_MAJOR},
    {"axis": 1, "tuc.layout_tile_shape": (2, 3)}, {"axis": 1, "max_error_budget": float("nan")},
    {"axis": 1, "prefer_sparsity": 1}])
def test_unknown_semantics_layouts_and_nonfinite_hints_reject(attrs):
    result, targets = compiled()
    operation = result.hac_ir.graph.operations[0]
    merged = {key: value for key, value in operation.attributes.items() if key != "axis"}
    merged.update(attrs)
    object.__setattr__(operation, "attributes", MappingProxyType(merged))
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("shapes", [((3,), (3,)), ((2, 3), (3, 2)), ((2, 3), (6,)),
                                   ((1, 2, 3), (1, 2, 3)), ((True, 3), (2, 3)),
                                   ((2, 0), (2, 0)), ((65, 3), (65, 3))])
def test_tensor_shapes_fail_closed_before_formatting(shapes, monkeypatch):
    result, targets = compiled()
    operation = result.hac_ir.graph.operations[0]
    for tensor, shape in zip((*operation.inputs, *operation.outputs), shapes, strict=True):
        object.__setattr__(tensor, "shape", shape)
    monkeypatch.setattr("tuc.backends.bounded_softmax_dag._primitives",
                        lambda _: pytest.fail("emission before shape validation"))
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("change", ["arity", "inplace", "dtype", "op-budget", "metadata-budget"])
def test_structural_mutations_fail_closed(change):
    result, targets = compiled()
    operation = result.hac_ir.graph.operations[0]
    if change == "arity":
        object.__setattr__(operation, "inputs", operation.inputs * 2)
    elif change == "inplace":
        object.__setattr__(operation, "outputs", operation.inputs)
    elif change == "dtype":
        object.__setattr__(operation.inputs[0], "dtype", "float64")
    elif change == "op-budget":
        object.__setattr__(result.hac_ir.graph, "operations", (operation,) * 9)
    else:
        result.hac_ir.metadata["unbounded"] = "x" * 65537
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)


@pytest.mark.parametrize("which", ["module", "graph", "operation", "tensor", "partition",
                                    "assignment", "score", "artifact"])
def test_record_shadowing_never_calls_instance_hooks(which):
    result, targets = compiled()
    module, partition = result.hac_ir, result.partition_plan
    artifact = lower_bounded_softmax_dag(module, partition, targets)
    values = {"module": module, "graph": module.graph, "operation": module.graph.operations[0],
              "tensor": module.graph.operations[0].inputs[0], "partition": partition,
              "assignment": partition.assignments[0], "score": partition.candidate_scores[0],
              "artifact": artifact}
    object.__setattr__(values[which], "dump", lambda: pytest.fail("untrusted dump hook"))
    with pytest.raises(ValueError):
        validate_bounded_softmax_dag_artifacts(artifact, module, partition, targets)


def test_proxy_and_dataclass_shadowing_reject_before_custom_traversal():
    class Trap(dict):
        def __iter__(self):
            pytest.fail("caller iteration")

        def items(self):
            pytest.fail("caller items")

        def values(self):
            pytest.fail("caller values")

    result, targets = compiled()
    operation = result.hac_ir.graph.operations[0]
    object.__setattr__(operation, "attributes", MappingProxyType(Trap(dict(operation.attributes))))
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)
    fake = object.__new__(type(result.hac_ir))
    object.__setattr__(fake, "__dataclass_fields__", Trap())
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(fake, result.partition_plan, targets)


@pytest.mark.parametrize("field", [item.name for item in fields(BoundedDAGArtifacts)])
def test_every_artifact_field_is_bound_to_the_source(field):
    result, targets = compiled()
    artifact = lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)
    with pytest.raises(ValueError):
        validate_bounded_softmax_dag_artifacts(replace(artifact, **{
            field: getattr(artifact, field) + " "}), result.hac_ir, result.partition_plan, targets)


def test_softmax_is_cpu_only_and_old_lowerers_reject_it():
    result, targets = compiled(target=DAGTarget.CUDA_SM86)
    with pytest.raises(ValueError):
        lower_bounded_softmax_dag(result.hac_ir, result.partition_plan, targets)
    result, targets = compiled()
    for old in (lower_bounded_dag, lower_bounded_add_dag, lower_bounded_linear_dag,
                lower_bounded_mul_dag):
        with pytest.raises(ValueError):
            old(result.hac_ir, result.partition_plan, targets)
    x, y = TensorRef("x", (2, 3)), TensorRef("y", (2, 3))
    with pytest.raises(ValueError, match="scope"):
        lower(ComputeGraph("relu", (ComputeOperation("relu", OperationKind.ELEMENTWISE,
                                                     (x,), (y,), {"kernel": "relu"}),)))


def test_softmax_composes_all_existing_kinds_in_eight_operations():
    shapes = {"x": (2, 3), "w": (3, 4), "p": (2, 4), "bias": (4,), "biased": (2, 4),
              "wt": (3, 4), "q": (2, 3), "other": (2, 3), "added": (2, 3),
              "scale": (2, 3), "product": (2, 3), "positive": (2, 3), "probs": (2, 3),
              "sums": (2,)}
    tensors = {name: TensorRef(name, shape) for name, shape in shapes.items()}
    definitions = (
        ("p", OperationKind.MATMUL, ("x", "w"), {}),
        ("biased", OperationKind.ELEMENTWISE, ("p", "bias"), {"kernel": "add"}),
        ("q", OperationKind.MATMUL, ("biased", "wt"), {"rhs_transposed": True}),
        ("added", OperationKind.ELEMENTWISE, ("q", "other"), {"kernel": "add"}),
        ("product", OperationKind.ELEMENTWISE, ("added", "scale"), {"kernel": "mul"}),
        ("positive", OperationKind.ELEMENTWISE, ("product",), {"kernel": "relu"}),
        ("probs", OperationKind.SOFTMAX, ("positive",), {"axis": 1}),
        ("sums", OperationKind.REDUCTION, ("probs",), {"axis": 1}),
    )
    graph = ComputeGraph("all_kinds", tuple(ComputeOperation(
        name, kind, tuple(tensors[item] for item in inputs), (tensors[name],), attrs)
        for name, kind, inputs, attrs in definitions))
    artifact = lower(graph)
    manifest = json.loads(artifact.manifest_json)
    assert [op["kind"] for op in manifest["operations"]] == [
        "matmul", "add_row_bias", "matmul_rhs_transposed", "add", "mul", "relu",
        "softmax_axis1", "sum_axis1"]
    assert manifest["scalar_work"] == 158
    assert len(manifest["tensors"]) == 14
    assert "input_1[column * 4U + k]" in artifact.c11_source


def test_work_budget_includes_softmax_and_preceding_matmuls():
    x, w, p, q, out = (TensorRef(name, (64, 64)) for name in ("x", "w", "p", "q", "out"))
    graph = ComputeGraph("over_budget", (
        ComputeOperation("first", OperationKind.MATMUL, (x, w), (p,)),
        ComputeOperation("second", OperationKind.MATMUL, (p, w), (q,)),
        ComputeOperation("normalize", OperationKind.SOFTMAX, (q,), (out,), {"axis": 1})))
    with pytest.raises(ValueError, match="budget"):
        lower(graph)


@pytest.mark.parametrize("change", ["rank", "shape", "arity", "inplace", "kind", "bool-index",
                                    "extra-field", "forward"])
def test_private_closed_descriptor_rejects_invalid_softmax(change):
    operation = C11OperationSpec("softmax_axis1", (0,), 1)
    spec = C11GraphSpec(((2, 3), (2, 3)), (operation,), (0,), (1,))
    if change == "rank":
        spec = replace(spec, tensor_shapes=((6,), (6,)))
    elif change == "shape":
        spec = replace(spec, tensor_shapes=((2, 3), (3, 2)))
    elif change == "arity":
        object.__setattr__(operation, "inputs", (0, 0))
    elif change == "inplace":
        object.__setattr__(operation, "output", 0)
    elif change == "kind":
        object.__setattr__(operation, "kind", "softmax")
    elif change == "bool-index":
        object.__setattr__(operation, "inputs", (False,))
    elif change == "extra-field":
        object.__setattr__(operation, "__dataclass_fields__", object())
    else:
        spec = replace(spec, tensor_shapes=((2, 3),) * 3,
                       operations=(C11OperationSpec("softmax_axis1", (1,), 2), operation),
                       output_tensors=(2,))
    with pytest.raises(ValueError):
        emit_checked_graph(spec, "a" * 64)


def test_private_descriptor_accounts_for_softmax_work_and_owned_storage():
    spec = C11GraphSpec(((64, 64), (64, 64)),
                        (C11OperationSpec("softmax_axis1", (0,), 1),), (0,), (1,))
    assert validate_spec(spec) == (32768, 20480)


# Captured before the Softmax change; covers both private C text and public
# provenance/entrypoint identity. These are emission baselines, not native evidence.
_OLD = {
    "matmul": (((2, 3), (3, 4), (2, 4)), (0, 1), 2, "matmul", {},
               "fcaf694413803575e7c20e2121e78363e5efd6bddc41a9eabf81fc3f9df523f3",
               "943acbf692561fc3988dacf757221ce9c67c70a6b2b37d805c50598739c62a54"),
    "matmul_rhs_transposed": (((2, 3), (4, 3), (2, 4)), (0, 1), 2, "matmul",
                             {"rhs_transposed": True},
                             "c6517c6bcec494df528085c11af9ffccfcae26b1b1f079442e7518e603d515f3",
                             "210fe043305a049205a01b6f90c9768ade454624d1eb1a5eee641562de66ac3a"),
    "add": (((2, 3), (2, 3), (2, 3)), (0, 1), 2, "elementwise", {"elementwise_kind": "add"},
            "3cd324cffc1ddea115e0e2625b3ee7b7d84cedb9994ee2ee5d3569774c25874e",
            "b2ba4a10217c83d30707fa262b53833667efc66b0173ac67473a0ce5524eadc5"),
    "add_row_bias": (((2, 3), (3,), (2, 3)), (0, 1), 2, "elementwise",
                     {"elementwise_kind": "add"},
                     "a10e3debed7b30c6c98118b21c7db92510b74f42a7bf42cc3cd9985850221a4b",
                     "b5032ea2b6e3fd036e79d0fc97124c63595d4f7b3a03600bc16e851bbbbcab16"),
    "mul": (((2, 3), (2, 3), (2, 3)), (0, 1), 2, "elementwise", {"elementwise_kind": "mul"},
            "b7ea62a91e2d99431b9cf4bee8df45db0a1fa50b1a637a00940453a7cdb78219",
            "fe100f4796689140e20a664e6aecc4dc31b06cebb6d7ac8f4a2bc06ac7efee2f"),
    "relu": (((2, 3), (2, 3)), (0,), 1, "elementwise", {"elementwise_kind": "relu"},
             "41f12d86ac659e753974828fe2e40b635725fa31b202f0a4773431db22226dc5",
             "38f0147c300c9b343382026b91c371a2d60144530726cd6466c073241691f007"),
    "sum_axis1": (((2, 3), (2,)), (0,), 1, "reduction", {"axis": 1},
                  "42ca81aeb12466da471299589fded06df9d9d65582a1d86efdcec13a40837d8b",
                  "1f65282b260651d2b09f23eef965b623bbc33fd39b188a4b99c64f5e5995b5d8"),
}


@pytest.mark.parametrize("kind", _OLD)
def test_every_old_normalized_kind_retains_identical_emission_and_public_identity(kind):
    shapes, inputs, output, family, attributes, private_digest, public_digest = _OLD[kind]
    spec = C11GraphSpec(shapes, (C11OperationSpec(kind, inputs, output),), inputs, (output,))
    texts = emit_checked_graph(spec, "a" * 64)
    assert sha256(json.dumps(texts, separators=(",", ":")).encode()).hexdigest() == private_digest
    assert "#include <math.h>" not in texts[1] and "expf(" not in texts[1]
    module = SourceIntentModule("frozen_" + kind, tuple(
        SourceIntentTensor("t" + str(i), shape) for i, shape in enumerate(shapes)), (
        SourceIntentOperation("compute", family, tuple("t" + str(i) for i in inputs),
                              ("t" + str(output),), attributes=attributes),),
        returns=(SourceIntentReturn("scores", "t" + str(output)),))
    bindings = (BoundedBackendBinding(capability(softmax=False), DAGTarget.C11),)
    result = compile_bounded_source_intent(module, bindings)
    artifact = emit_bounded_c11_entrypoint(module, bindings, result)
    serialized = json.dumps(artifact.files(), sort_keys=True, separators=(",", ":")).encode()
    assert sha256(serialized).hexdigest() == public_digest


def _f32(value):
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def _normal(value):
    magnitude = struct.unpack("<I", struct.pack("<f", value))[0] & 0x7fffffff
    return magnitude == 0 or 0x00800000 <= magnitude < 0x7f800000


def _contract_row(values):
    """Independent scalar contract witness; Python exp is not C libm evidence."""
    if any(not _normal(value) for value in values):
        return "input"
    maximum = values[0]
    for value in values[1:]:
        if value > maximum:
            maximum = value
    exponents, total = [], 0.0
    for value in values:
        shift = _f32(value - maximum)
        if not _normal(shift):
            return "shift"
        exponential = _f32(math.exp(shift))
        if not _normal(exponential) or exponential <= 0.0:
            return "exp"
        exponents.append(exponential)
        total = _f32(total + exponential)
        if not _normal(total):
            return "sum"
    result = [_f32(value / total) for value in exponents]
    return "quotient" if any(not _normal(value) or value <= 0.0 for value in result) else result


@pytest.mark.parametrize("values,stage", [
    ([_f32(-3.4028234663852886e38), _f32(3.4028234663852886e38)], "shift"),
    ([struct.unpack("<f", struct.pack("<I", value))[0] for value in (0x00800000, 0x00800001)],
     "shift"),
    ([-90.0, 0.0], "exp"), ([-104.0, 0.0], "exp"), ([-87.0, 0.0, 0.0], "quotient"),
])
def test_numeric_controls_reach_distinct_contract_failures(values, stage):
    assert all(_normal(value) for value in values)
    assert _contract_row(values) == stage


@pytest.mark.parametrize("value", [0.0, -0.0, 1000.0, -1000.0,
                                  _f32(3.4028234663852886e38), _f32(-3.4028234663852886e38)])
def test_contract_has_no_artificial_logit_range_cap(value):
    assert _contract_row([value]) == [1.0]
    assert _contract_row([value] * 4) == [0.25] * 4
