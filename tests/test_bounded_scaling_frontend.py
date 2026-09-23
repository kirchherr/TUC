"""Bounded right scaling across source, semantic and compiler boundaries."""

import json
from dataclasses import replace
from math import prod
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest

import tuc.compiler.bounded_source as bounded
from integration.bounded_cpu_batch import consumer as batch_consumer
from integration.bounded_cpu_softmax import consumer as softmax_consumer
from tuc.backends.bounded_dag import DAGTarget
from tuc.bounded_cpu_application_cli import cpu_bindings
from tuc.compiler import compile_graph
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_json import BoundedCPUJSONError, source_intent_from_json
from tuc.compiler.bounded_cpu_source import (
    _SECURITY,
    WORKER_PROTOCOL,
    decode_source_response,
    prepare_source_request,
)
from tuc.compiler.movement import estimate_operation_movement
from tuc.frontend import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
    source_intent_to_triton_metadata,
)
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
    source_to_intent_research_kernel_ingress_report_to_dict,
)
from tuc.ir import (
    ComputeGraph,
    ComputeOperation,
    LayoutKind,
    MemoryDomainKind,
    OperationKind,
    TensorRef,
)
from tuc.reference.kernels import reference_multiply
from tuc.runtime import Assignment, PartitionPlan, execute_graph


def typed(left=(2, 3), right=(1,), output=None, dtype="float32"):
    return SourceIntentModule("caller_scaling", (
        SourceIntentTensor("x", left), SourceIntentTensor("gain", right, dtype),
        SourceIntentTensor("y", left if output is None else output)), (
        SourceIntentOperation("scale", "elementwise", ("x", "gain"), ("y",),
                              attributes={"elementwise_kind": "mul"}),),
        returns=(SourceIntentReturn("scores", "y"),))


def operation(left, right, output=None):
    return ComputeOperation("scale", OperationKind.ELEMENTWISE,
                            (TensorRef("x", left), TensorRef("gain", right)),
                            (TensorRef("y", left if output is None else output),),
                            {"kernel": "mul"})


def parsed(left, right, expression="x * gain"):
    text = ("import triton\nimport triton.language as tl\n@triton.jit\n"
            "def scale(x, gain, scores):\n    y = " + expression + "\n    tl.store(scores, y)\n")
    return text, ingest_triton_module_source_to_source_intent(
        text, source_name="caller_scaling", kernel_name="scale",
        tensor_shapes={"x": left, "gain": right, "scores": left})


@pytest.mark.parametrize("left,right,kind,note", [
    ((1,), (1,), "mul", "exact_shape_elementwise_multiply"),
    ((5,), (5,), "mul", "exact_shape_elementwise_multiply"),
    ((1, 1), (1, 1), "mul", "exact_shape_elementwise_multiply"),
    ((2, 3), (2, 3), "mul", "exact_shape_elementwise_multiply"),
    ((5,), (1,), "mul_scalar", "right_scalar_multiply"),
    ((1, 1), (1,), "mul_scalar", "right_scalar_multiply"),
    ((2, 1), (1,), "mul_scalar", "right_scalar_multiply"),
    ((2, 3), (1,), "mul_scalar", "right_scalar_multiply"),
    ((64, 64), (1,), "mul_scalar", "right_scalar_multiply"),
    ((1, 3), (3,), "mul_row_scale", "right_row_scale_multiply"),
    ((2, 3), (3,), "mul_row_scale", "right_row_scale_multiply"),
    ((64, 64), (64,), "mul_row_scale", "right_row_scale_multiply"),
])
def test_source_json_ir_and_emission_use_same_bounded_rule(left, right, kind, note):
    _, result = parsed(left, right)
    document = json.dumps(result.parser_result.source_intent_payload).encode()
    decoded = source_intent_from_json(document)
    assert decoded == result.parser_result.module
    compiled = bounded.compile_bounded_source_intent(decoded, cpu_bindings())
    direct = bounded.compile_bounded_source_intent(typed(left, right), cpu_bindings())
    first = json.loads(compiled.artifacts.manifest_json)
    second = json.loads(direct.artifacts.manifest_json)
    for manifest in (first, second):
        expected_schema = "mul" if kind == "mul" else "scaling"
        assert manifest["schema_version"] == f"tuc.bounded_{expected_schema}_dag_artifacts.v0"
        assert manifest["operations"][0]["kind"] == kind
        assert manifest["scalar_work"] == prod(left)
        assert manifest["operations"][0]["input_shapes"] == [list(left), list(right)]
    for stage in (compiled.compilation.tlir, compiled.compilation.hac_ir,
                  compiled.compilation.hs_ir):
        op = stage.graph.operations[0]
        assert op.kind is OperationKind.ELEMENTWISE and op.attributes["kernel"] == "mul"
        assert tuple(t.shape for t in (*op.inputs, *op.outputs)) == (left, right, left)
    estimate = estimate_operation_movement(compiled.compilation.hac_ir.graph.operations[0])
    assert (estimate.bytes_read, estimate.bytes_written, estimate.arithmetic_ops) == (
        4 * (prod(left) + prod(right)), 4 * prod(left), prod(left))
    assert estimate.notes == (note,)
    assert [binding.shape for binding in compiled.input_bindings] == [left, right]
    bounded.validate_bounded_source_compilation(decoded, cpu_bindings(), compiled)


@pytest.mark.parametrize("left,right", [((5,), (1,)), ((2, 3), (1,)), ((2, 3), (3,))])
def test_reference_and_runtime_apply_explicit_scalar_or_feature_index(left, right):
    x = (np.arange(prod(left), dtype=np.float64) - 2.5).reshape(left)
    gain = (np.arange(prod(right), dtype=np.float64) - 1.25).reshape(right)
    expected = np.array([float(v) * float(gain.flat[0 if right == (1,) else i % left[1]])
                         for i, v in enumerate(x.flat)]).reshape(left)
    saved = (x.copy(), gain.copy())
    actual = reference_multiply(x, gain)
    np.testing.assert_array_equal(actual, expected)
    graph = source_intent_to_triton_metadata(typed(left, right)).to_compute_graph()
    compiled = compile_graph(graph, [])
    result = execute_graph(compiled.hac_ir.graph, compiled.partition_plan,
                           {"x": x, "gain": gain}).output_for("y")
    np.testing.assert_array_equal(result, expected)
    np.testing.assert_array_equal(x, saved[0])
    np.testing.assert_array_equal(gain, saved[1])
    assert result.dtype == np.dtype("float64")
    assert not np.shares_memory(result, x) and not np.shares_memory(result, gain)


def test_reference_scaling_keeps_signed_zero_and_rejects_bad_values():
    value = reference_multiply(np.array([-0.0, 0.0]), np.array([-2.0]))
    np.testing.assert_array_equal(np.signbit(value), [False, True])
    for bad in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="finite"):
            reference_multiply(np.ones((2, 3)), np.array([bad]))
    with pytest.raises(ValueError, match="finite"):
        reference_multiply(np.array([np.finfo(np.float64).max]), np.array([2.0]))


@pytest.mark.parametrize("left,right,output", [
    ((1,), (3,), (3,)), ((1,), (2, 3), (2, 3)), ((3,), (2, 3), (2, 3)),
    ((2, 3), (2, 1), (2, 3)), ((2, 3), (1, 3), (2, 3)),
    ((2, 3), (1, 1), (2, 3)), ((2, 3), (2,), (2, 3)),
    ((3,), (2,), (3,)), ((2, 3), (1,), (3, 2)), ((2, 3, 4), (1,), (2, 3, 4)),
])
def test_invalid_shapes_reject_at_each_semantic_boundary(left, right, output, monkeypatch):
    with pytest.raises(ValueError):
        typed(left, right, output)
    op = operation(left, right, output)
    with pytest.raises(ValueError):
        estimate_operation_movement(op)
    graph = ComputeGraph("bad_scaling", (op,))
    plan = PartitionPlan(graph.name, (Assignment(
        op.name, "reference-cpu", "test", MemoryDomainKind.HOST_RAM, LayoutKind.ROW_MAJOR),))
    with pytest.raises(ValueError, match="bounded right scaling"):
        execute_graph(graph, plan, {})
    if output == left or right != (1,):
        # Output-shape mismatch is not an input to the reference API.
        monkeypatch.setattr(np, "multiply", lambda *a, **k: pytest.fail("invalid multiplication"))
        with pytest.raises(ValueError):
            reference_multiply(np.ones(left), np.ones(right))


@pytest.mark.parametrize("expression", [
    "x * 2.0", "x * 2", "2 * x", "x * True", "x * gain[0]", "x * (gain + gain)",
    "x * gain * gain", "x * tl.sum(gain, axis=0)", "x * missing", "gain * x",
])
def test_scaling_source_retains_two_known_names_and_right_operand_only(expression):
    with pytest.raises(ValueError):
        parsed((2, 3), (1,), expression)


@pytest.mark.parametrize("mutation", [
    "dtype", "rank0", "bool-dimension", "oversize", "column", "extra-axis", "extra-kind",
    "reverse", "inplace", "missing-input", "unknown-input",
])
def test_scaling_json_keeps_exact_dtype_shape_and_attribute_validation(mutation):
    _, parsed_result = parsed((2, 3), (1,))
    document = json.loads(json.dumps(parsed_result.parser_result.source_intent_payload))
    tensors = {item["name"]: item for item in document["tensors"]}
    op = document["operations"][0]
    if mutation == "dtype":
        tensors["gain"]["dtype"] = "float64"
    elif mutation in {"rank0", "bool-dimension", "oversize", "column"}:
        tensors["gain"]["shape"] = {"rank0": [], "bool-dimension": [True],
                                    "oversize": [65], "column": [2, 1]}[mutation]
    elif mutation == "extra-axis":
        op["attributes"]["axis"] = 1
    elif mutation == "extra-kind":
        op["attributes"]["elementwise_kind"] = "mul_scalar"
    elif mutation == "reverse":
        op["inputs"].reverse()
    elif mutation == "inplace":
        op["outputs"] = ["x"]
    elif mutation == "missing-input":
        op["inputs"] = ["x"]
    else:
        op["inputs"] = ["x", "missing"]
    with pytest.raises(BoundedCPUJSONError):
        source_intent_from_json(json.dumps(document).encode())


def test_untrusted_proxy_and_dimension_hooks_reject_before_compiler(monkeypatch):
    calls = []
    class Hostile(dict):
        def items(self):
            calls.append("items")
            raise AssertionError
    class Dimension(int):
        def __eq__(self, other):
            calls.append("eq")
            raise AssertionError
    value = typed()
    object.__setattr__(value.operations[0], "attributes",
                       MappingProxyType(Hostile(elementwise_kind="mul")))
    monkeypatch.setattr(bounded, "compile_graph", lambda *a, **k: pytest.fail("compiler called"))
    with pytest.raises(ValueError):
        bounded.compile_bounded_source_intent(value, cpu_bindings())
    value = typed()
    object.__setattr__(value.tensors[1], "shape", (Dimension(1),))
    with pytest.raises(ValueError):
        bounded.compile_bounded_source_intent(value, cpu_bindings())
    assert calls == []


@pytest.mark.parametrize("right", [(1,), (3,)])
def test_existing_source_worker_protocol_carries_scaling_without_new_files(right):
    """Synthetic security metadata does not establish an OCI execution observation."""
    text, parsed_result = parsed((2, 3), right)
    signature = {"schema_version": "tuc.bounded_cpu_source.v0", "source_name": "caller_scaling",
                 "kernel_name": "scale", "tensor_shapes": {
                     "x": [2, 3], "gain": list(right), "scores": [2, 3]}}
    request = prepare_source_request(text.encode(), json.dumps(signature).encode())
    wire = {"protocol": WORKER_PROTOCOL, "status": "accepted",
            "request_digest": json.loads(request)["request_digest"], "security": dict(_SECURITY),
            "source_intent_payload": parsed_result.parser_result.source_intent_payload,
            "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(
                parsed_result.report)}
    result = source_intent_from_json(decode_source_response(request, json.dumps(wire).encode()))
    assert result == parsed_result.parser_result.module


def test_scaled_attention_dispatches_scaling_before_softmax():
    shapes = {"q": (2, 3), "k": (4, 3), "factor": (1,), "v": (4, 2),
              "logits": (2, 4), "scaled": (2, 4), "probability": (2, 4), "y": (2, 2)}
    ops = (("logits", "matmul", ("q", "k"), {"rhs_transposed": True}),
           ("scaled", "elementwise", ("logits", "factor"), {"elementwise_kind": "mul"}),
           ("probability", "softmax", ("scaled",), {"axis": 1}),
           ("y", "matmul", ("probability", "v"), {}))
    value = SourceIntentModule("scaled_attention", tuple(
        SourceIntentTensor(name, shape) for name, shape in shapes.items()), tuple(
        SourceIntentOperation(name, family, inputs, (name,), attributes=attributes)
        for name, family, inputs, attributes in ops), returns=(SourceIntentReturn("scores", "y"),))
    result = bounded.compile_bounded_source_intent(value, cpu_bindings(softmax=True))
    manifest = json.loads(result.artifacts.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_scaling_dag_artifacts.v0"
    assert [op["kind"] for op in manifest["operations"]] == [
        "matmul_rhs_transposed", "mul_scalar", "softmax_axis1", "matmul"]
    assert manifest["scalar_work"] == 48 + 8 + 40 + 32
    application = prepare_bounded_c11_application(value, cpu_bindings(softmax=True))
    assert len(application.program_digest) == 64


def test_cuda_scaling_rejects_without_host_fallback():
    binding = cpu_bindings()[0]
    gpu = replace(binding, target=DAGTarget.CUDA_SM86,
                  capability=replace(binding.capability, memory_domain=MemoryDomainKind.UNKNOWN))
    with pytest.raises(ValueError):
        bounded.compile_bounded_source_intent(typed(), (gpu,))


@pytest.mark.parametrize("family,index", [(family, i) for family in ("batch", "softmax")
                                         for i in range(6)])
def test_twelve_observed_program_ids_remain_unchanged(family, index):
    """Reconstruct original identities; neither old receipts nor native code are rerun."""
    basename = ("bounded-cpu-batch-35609641378.json" if family == "batch" else
                "bounded-cpu-softmax-35694760750.json")
    path = Path(__file__).resolve().parents[1] / "docs/evidence" / basename
    record = json.loads(path.read_bytes())["integration"]["programs"][index]
    consumer = batch_consumer if family == "batch" else softmax_consumer
    graph = consumer.graph(record["family"], record["profile"])
    value = source_intent_from_json(json.dumps(graph).encode())
    application = prepare_bounded_c11_application(value, cpu_bindings(softmax=family == "softmax"))
    assert application.program_digest == record["program_digest"]
