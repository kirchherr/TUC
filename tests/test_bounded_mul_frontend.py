"""Bounded symbolic multiplication boundaries; no user or native code execution."""

import copy
import json
from dataclasses import replace
from math import prod

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


def fixture(left=(2, 3), right=(2, 3), expression="a * b"):
    source = ("import triton\nimport triton.language as tl\n@triton.jit\n"
              "def product(a, b, y):\n    p = " + expression + "\n    tl.store(y, p)\n")
    return source, {"a": left, "b": right, "y": left}


def parse(left=(2, 3), right=(2, 3), expression="a * b"):
    source, shapes = fixture(left, right, expression)
    return ingest_triton_module_source_to_source_intent(
        source, source_name="caller_mul", kernel_name="product", tensor_shapes=shapes)


@pytest.mark.parametrize("shape", [(1,), (5,), (1, 1), (2, 3), (3, 1), (64, 64)])
def test_source_json_application_preserve_exact_shapes_and_product_work(shape):
    parsed = parse(shape, shape)
    document = json.dumps(parsed.parser_result.source_intent_payload).encode()
    module = source_intent_from_json(document)
    assert module == parsed.parser_result.module
    assert dict(module.operations[0].attributes) == {"elementwise_kind": "mul"}
    compiled = compile_bounded_source_intent(module, cpu_bindings())
    manifest = json.loads(compiled.artifacts.manifest_json)
    assert manifest["schema_version"] == "tuc.bounded_mul_dag_artifacts.v0"
    assert manifest["operations"][0]["kind"] == "mul"
    assert manifest["operations"][0]["input_shapes"] == [list(shape), list(shape)]
    assert manifest["operations"][0]["output_shape"] == list(shape)
    assert manifest["scalar_work"] == prod(shape)
    assert [item.shape for item in compiled.input_bindings] == [shape, shape]
    assert [item.public_name for item in compiled.output_bindings] == ["y"]
    assert len(prepare_bounded_c11_application(module, cpu_bindings()).program_digest) == 64


def test_real_parser_product_passes_synthetic_parent_protocol():
    """Synthetic security fields establish no OCI execution observation."""
    source, shapes = fixture()
    signature = {"schema_version": "tuc.bounded_cpu_source.v0", "source_name": "caller_mul",
                 "kernel_name": "product", "tensor_shapes": shapes}
    request = prepare_source_request(source.encode(), json.dumps(signature).encode())
    parsed = parse()
    wire = {"protocol": WORKER_PROTOCOL, "status": "accepted",
            "request_digest": json.loads(request)["request_digest"], "security": dict(_SECURITY),
            "source_intent_payload": parsed.parser_result.source_intent_payload,
            "ingress_report": source_to_intent_research_kernel_ingress_report_to_dict(
                parsed.report)}
    assert source_intent_from_json(decode_source_response(request, json.dumps(wire).encode())) == (
        parsed.parser_result.module)


@pytest.mark.parametrize("expression", [
    "a * 1", "1 * a", "a * True", "a * -1.0", "a * b * b", "a * (a + b)",
    "(a + b) * b", "a[0] * b", "a * b[0]", "a * tl.sum(b, axis=1)",
    "tl.mul(a, b)", "a.__mul__(b)", "a / b", "a ** b", "a @ b", "a - b",
    "missing * b", "a * __import__('os')", "a * (lambda: b)()", "a * tl.trans(b)",
])
def test_product_source_accepts_only_two_known_tensor_names(expression):
    with pytest.raises(ValueError):
        parse(expression=expression)


@pytest.mark.parametrize("left,right", [
    ((2, 3), (2,)), ((3,), (2, 3)), ((2, 3), (1, 3)), ((2, 3), (2, 1)),
    ((2, 3), (3, 2)), ((3,), (2,)), ((1, 3), (1, 1)), ((2, 3, 4), (2, 3, 4)),
])
def test_product_rejects_shapes_outside_bounded_right_scaling(left, right):
    with pytest.raises(ValueError):
        parse(left, right)


def test_repeated_operand_has_one_external_binding():
    source = ("import triton\nimport triton.language as tl\n@triton.jit\n"
              "def square(x, y):\n    squared = x * x\n    tl.store(y, squared)\n")
    parsed = ingest_triton_module_source_to_source_intent(
        source, source_name="square", kernel_name="square", tensor_shapes={"x": (2, 3),
                                                                             "y": (2, 3)})
    module = parsed.parser_result.module
    assert module.operations[0].inputs == ("x", "x")
    compiled = compile_bounded_source_intent(module, cpu_bindings())
    assert [binding.public_name for binding in compiled.input_bindings] == ["x"]
    assert len(prepare_bounded_c11_application(module, cpu_bindings()).program_digest) == 64


@pytest.mark.parametrize("mutation", [
    "missing-input", "extra-input", "input-shape", "output-shape", "bool-dimension",
    "huge-dimension", "dtype", "kind-type", "wrong-family", "transpose", "axis", "unknown-kind",
])
def test_json_product_rejects_malformed_or_inconsistent_records(mutation):
    document = copy.deepcopy(dict(parse().parser_result.source_intent_payload))
    operation = document["operations"][0]
    if mutation == "missing-input":
        operation["inputs"] = ["a"]
    elif mutation == "extra-input":
        operation["inputs"] = ["a", "b", "a"]
    elif mutation == "output-shape":
        document["tensors"][2]["shape"] = [3, 2]
    elif mutation in ("input-shape", "bool-dimension", "huge-dimension"):
        document["tensors"][1]["shape"] = {
            "input-shape": [2, 1], "bool-dimension": [True, 3], "huge-dimension": [65, 3]}[mutation]
    elif mutation == "dtype":
        document["tensors"][1]["dtype"] = "float16"
    elif mutation == "kind-type":
        operation["attributes"]["elementwise_kind"] = True
    elif mutation == "wrong-family":
        operation["family"] = "matmul"
    elif mutation == "unknown-kind":
        operation["attributes"]["elementwise_kind"] = "multiply"
    else:
        operation["attributes"]["rhs_transposed" if mutation == "transpose" else "axis"] = True
    with pytest.raises(BoundedCPUJSONError):
        source_intent_from_json(json.dumps(document).encode())


def test_product_cuda_binding_rejects_without_host_fallback():
    binding = cpu_bindings()[0]
    cuda = replace(binding, target=DAGTarget.CUDA_SM86,
                   capability=replace(binding.capability, memory_domain=MemoryDomainKind.UNKNOWN))
    with pytest.raises(ValueError):
        compile_bounded_source_intent(parse().parser_result.module, (cuda,))
