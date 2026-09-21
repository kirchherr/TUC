"""Bounded symbolic Linear source and JSON boundaries; native execution is separate."""

import copy
import json
from dataclasses import replace

import pytest

from tuc.backends.bounded_dag import DAGTarget
from tuc.bounded_cpu_application_cli import cpu_bindings
from tuc.compiler.bounded_c11_application import prepare_bounded_c11_application
from tuc.compiler.bounded_cpu_json import BoundedCPUJSONError, source_intent_from_json
from tuc.compiler.bounded_cpu_source import (
    _SECURITY,
    WORKER_PROTOCOL,
    decode_source_response,
    prepare_source_request,
)
from tuc.compiler.bounded_source import compile_bounded_source_intent
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
    source_to_intent_research_kernel_ingress_report_to_dict,
)
from tuc.ir.memory import MemoryDomainKind


def fixture(lhs=(2, 3), rhs=(4, 3), expression="tl.dot(x, tl.trans(w))"):
    source = ("import triton\nimport triton.language as tl\n@triton.jit\n"
              "def linear(x, w, y):\n    p = " + expression + "\n    tl.store(y, p)\n")
    return source, {"x": lhs, "w": rhs, "y": (lhs[0], rhs[0])}


def parse(lhs=(2, 3), rhs=(4, 3), expression="tl.dot(x, tl.trans(w))"):
    source, shapes = fixture(lhs, rhs, expression)
    return ingest_triton_module_source_to_source_intent(
        source, source_name="caller_linear", kernel_name="linear", tensor_shapes=shapes)


@pytest.mark.parametrize("lhs,rhs", [
    ((2, 3), (4, 3)), ((1, 4), (2, 4)), ((3, 1), (5, 1)),
    ((1, 1), (1, 1)), ((64, 64), (64, 64)),
])
def test_source_json_application_preserve_physical_weights_and_logical_result(lhs, rhs):
    parsed = parse(lhs, rhs)
    document = json.dumps(parsed.parser_result.source_intent_payload).encode()
    module = source_intent_from_json(document)
    assert module == parsed.parser_result.module
    assert dict(module.operations[0].attributes) == {"rhs_transposed": True}
    compiled = compile_bounded_source_intent(module, cpu_bindings())
    manifest = json.loads(compiled.artifacts.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_linear_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "matmul_rhs_transposed"
    assert manifest["operations"][0]["input_shapes"] == [list(lhs), list(rhs)]
    assert manifest["operations"][0]["output_shape"] == [lhs[0], rhs[0]]
    assert manifest["scalar_work"] == 2 * lhs[0] * lhs[1] * rhs[0]
    assert [binding.shape for binding in compiled.input_bindings] == [lhs, rhs]
    assert [binding.shape for binding in compiled.output_bindings] == [(lhs[0], rhs[0])]
    assert len(prepare_bounded_c11_application(module, cpu_bindings()).program_digest) == 64


def test_symbolic_transpose_passes_synthetic_parent_protocol_without_host_user_execution():
    """Owned literal source and synthetic security fields establish no OCI observation."""
    source, shapes = fixture()
    signature = {"schema_version": "tuc.bounded_cpu_source.v0", "source_name": "caller_linear",
                 "kernel_name": "linear", "tensor_shapes": shapes}
    request = prepare_source_request(source.encode(), json.dumps(signature).encode())
    parsed = parse()
    wire = {"protocol": WORKER_PROTOCOL, "status": "accepted",
            "request_digest": json.loads(request)["request_digest"], "security": dict(_SECURITY),
            "source_intent_payload": parsed.parser_result.source_intent_payload,
            "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(
                parsed.report)}
    graph = decode_source_response(request, json.dumps(wire).encode())
    assert source_intent_from_json(graph) == parsed.parser_result.module


@pytest.mark.parametrize("expression", [
    "tl.dot(tl.trans(x), w)", "tl.dot(x, tl.trans(tl.trans(w)))",
    "tl.dot(x, tl.trans(w, 1, 0))", "tl.dot(x, tl.trans(w, dims=(1, 0)))",
    "tl.dot(x, tl.trans(input=w))", "tl.dot(x, tl.trans())", "tl.dot(x, w.T)",
    "tl.dot(x, w.trans())", "tl.trans(w)", "tl.dot(x, tl.trans(w[0]))",
    "tl.dot(x, tl.trans(w + w))", "tl.dot(x, tl.trans(unknown))",
    "tl.dot(x, tl.trans(__import__('os')))", "tl.dot(x, (lambda: w)())",
    "tl.dot(x, tl.trans(w), allow_tf32=True)", "tl.dot(x, tl.where(w > 0.0, w, 0.0))",
])
def test_only_direct_named_rhs_transpose_is_accepted(expression):
    with pytest.raises(ValueError):
        parse(expression=expression)


@pytest.mark.parametrize("lhs,rhs", [
    ((2, 3), (3, 4)), ((2, 3), (4, 2)), ((3,), (2, 3)),
    ((2, 3), (3,)), ((2, 3, 4), (2, 3, 4)),
])
def test_transposed_dot_rejects_incompatible_ranks_and_inner_dimensions(lhs, rhs):
    with pytest.raises(ValueError):
        parse(lhs, rhs)


@pytest.mark.parametrize("marker", [False, 0, 1, 1.0, "true", None, [], {}])
def test_json_marker_is_exact_canonical_true(marker):
    graph = copy.deepcopy(dict(parse().parser_result.source_intent_payload))
    graph["operations"][0]["attributes"]["rhs_transposed"] = marker
    with pytest.raises(BoundedCPUJSONError):
        source_intent_from_json(json.dumps(graph).encode())


@pytest.mark.parametrize("mutation", ["wrong-shape", "dtype", "axis", "family", "missing-input"])
def test_json_transpose_rejects_inconsistent_records(mutation):
    graph = copy.deepcopy(dict(parse().parser_result.source_intent_payload))
    operation = graph["operations"][0]
    if mutation == "wrong-shape":
        graph["tensors"][1]["shape"] = [3, 4]
    elif mutation == "dtype":
        graph["tensors"][1]["dtype"] = "float16"
    elif mutation == "axis":
        operation["attributes"]["axis"] = 1
    elif mutation == "family":
        operation["family"] = "elementwise"
    else:
        operation["inputs"] = ["x"]
    with pytest.raises(BoundedCPUJSONError):
        source_intent_from_json(json.dumps(graph).encode())


def test_transposed_repeated_operand_keeps_one_public_input():
    source = ("import triton\nimport triton.language as tl\n@triton.jit\n"
              "def gram(x, y):\n    p = tl.dot(x, tl.trans(x))\n    tl.store(y, p)\n")
    parsed = ingest_triton_module_source_to_source_intent(
        source, source_name="gram", kernel_name="gram", tensor_shapes={"x": [2, 3], "y": [2, 2]})
    compiled = compile_bounded_source_intent(parsed.parser_result.module, cpu_bindings())
    assert [binding.public_name for binding in compiled.input_bindings] == ["x"]
    assert compiled.output_bindings[0].shape == (2, 2)


def test_transposed_matmul_cannot_silently_select_cuda():
    binding = cpu_bindings()[0]
    cuda = replace(binding, target=DAGTarget.CUDA_SM86,
                   capability=replace(binding.capability, memory_domain=MemoryDomainKind.UNKNOWN))
    with pytest.raises(ValueError):
        compile_bounded_source_intent(parse().parser_result.module, (cuda,))
