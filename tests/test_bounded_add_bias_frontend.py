"""Fixed source/JSON Add boundary checks; no source or native execution."""

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


def fixture(left=(2, 3), right=(3,), expression="a + b"):
    source = ("import triton\nimport triton.language as tl\n@triton.jit\n"
              "def affine(a, b, y):\n    p = " + expression + "\n    tl.store(y, p)\n")
    return source, {"a": left, "b": right, "y": left}


def parse(left=(2, 3), right=(3,), expression="a + b"):
    source, shapes = fixture(left, right, expression)
    return ingest_triton_module_source_to_source_intent(
        source, source_name="caller_add", kernel_name="affine", tensor_shapes=shapes)


@pytest.mark.parametrize("left,right,kind", [
    ((3,), (3,), "add"), ((2, 3), (2, 3), "add"), ((2, 3), (3,), "add_row_bias"),
    ((1, 1), (1,), "add_row_bias"), ((64, 64), (64,), "add_row_bias"),
])
def test_source_json_compiler_and_application_agree_on_add(left, right, kind):
    parsed = parse(left, right)
    document = json.dumps(parsed.parser_result.source_intent_payload).encode()
    module = source_intent_from_json(document)
    assert module == parsed.parser_result.module
    assert module.operations[0].inputs == ("a", "b")
    assert dict(module.operations[0].attributes) == {"elementwise_kind": "add"}
    compiled = compile_bounded_source_intent(module, cpu_bindings())
    manifest = json.loads(compiled.artifacts.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_add_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == kind
    assert manifest["scalar_work"] == left[0] * (left[1] if len(left) == 2 else 1)
    application = prepare_bounded_c11_application(module, cpu_bindings())
    assert len(application.program_digest) == 64
    assert [item.public_name for item in compiled.input_bindings] == ["a", "b"]
    assert [item.public_name for item in compiled.output_bindings] == ["y"]


def test_real_parser_graph_passes_synthetic_parent_protocol_validation():
    """Security envelope is synthetic; this establishes no OCI observation."""
    source, shapes = fixture()
    signature = {"schema_version": "tuc.bounded_cpu_source.v0", "source_name": "caller_add",
                 "kernel_name": "affine", "tensor_shapes": shapes}
    request = prepare_source_request(source.encode(), json.dumps(signature).encode())
    parsed = parse()
    wire = {"protocol": WORKER_PROTOCOL, "status": "accepted",
            "request_digest": json.loads(request)["request_digest"], "security": dict(_SECURITY),
            "source_intent_payload": parsed.parser_result.source_intent_payload,
            "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(
                parsed.report)}
    graph = decode_source_response(request, json.dumps(wire).encode())
    assert graph.endswith(b"\n")
    assert source_intent_from_json(graph) == parsed.parser_result.module


@pytest.mark.parametrize("expression", [
    "a - b", "a * b[0]", "a / b", "a + 1", "1 + a", "a + True", "a + b + b",
    "(a + b) + b", "a[0] + b", "a + tl.sum(b, axis=0)", "missing + b",
    "a.__class__ + b", "a + __import__('os')", "a + (lambda: b)()",
])
def test_only_two_named_tensor_operands_are_admitted(expression):
    with pytest.raises(ValueError):
        parse(expression=expression)


@pytest.mark.parametrize("left,right", [
    ((2, 3), (2,)), ((2, 3), (1, 3)), ((2, 3), (2, 1)), ((3,), (2, 3)),
    ((3,), (1,)), ((2, 3, 4), (2, 3, 4)), ((2, 3), (3, 2)),
])
def test_source_shape_rules_reject_other_broadcast_forms(left, right):
    with pytest.raises(ValueError):
        parse(left, right)


def test_same_symbol_twice_has_one_public_input():
    source = ("import triton\nimport triton.language as tl\n@triton.jit\n"
              "def twice(a, y):\n    p = a + a\n    tl.store(y, p)\n")
    parsed = ingest_triton_module_source_to_source_intent(
        source, source_name="twice", kernel_name="twice", tensor_shapes={"a": [3], "y": [3]})
    compiled = compile_bounded_source_intent(parsed.parser_result.module, cpu_bindings())
    assert [binding.public_name for binding in compiled.input_bindings] == ["a"]
    assert compiled.compilation.hac_ir.graph.operations[0].inputs[0].name == "a"


@pytest.mark.parametrize("mutation", ["missing-input", "extra-input", "shape", "bool",
                                      "dtype", "unknown-kind", "extra-attribute", "huge"])
def test_json_add_rejects_inconsistent_or_oversized_records(mutation):
    document = copy.deepcopy(dict(parse().parser_result.source_intent_payload))
    operation = document["operations"][0]
    if mutation == "missing-input":
        operation["inputs"] = ["a"]
    elif mutation == "extra-input":
        operation["inputs"] = ["a", "b", "a"]
    elif mutation in ("shape", "bool", "huge"):
        document["tensors"][1]["shape"] = {"shape": [2], "bool": [True], "huge": [65]}[mutation]
    elif mutation == "dtype":
        document["tensors"][1]["dtype"] = "float16"
    elif mutation == "unknown-kind":
        operation["attributes"]["elementwise_kind"] = "add_broadcast"
    else:
        operation["attributes"]["axis"] = 1
    with pytest.raises(BoundedCPUJSONError):
        source_intent_from_json(json.dumps(document).encode())


def test_add_cuda_binding_rejects_explicitly():
    binding = cpu_bindings()[0]
    cuda = replace(binding, target=DAGTarget.CUDA_SM86,
                   capability=replace(binding.capability, memory_domain=MemoryDomainKind.UNKNOWN))
    with pytest.raises(ValueError):
        compile_bounded_source_intent(parse().parser_result.module, (cuda,))
