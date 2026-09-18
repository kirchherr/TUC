"""Pure bounded JSON frontend tests; no filesystem or native execution."""

import copy
import json
import math
from dataclasses import replace

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_cpu_json as api
from tuc.compiler.bounded_c11_application import (
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
from tuc.compiler.bounded_source import BoundedBackendBinding
from tuc.frontend.source_intent import (
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentReturn,
    SourceIntentTensor,
)
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind


def document():
    return {
        "schema_version": "source_intent.v0", "name": "json_branch",
        "tensors": [
            {"name": "a", "shape": [1, 2]}, {"name": "b", "shape": [2, 2]},
            {"name": "p", "shape": [1, 2]}, {"name": "r", "shape": [1, 2]},
            {"name": "raw", "shape": [1]}, {"name": "positive", "shape": [1]},
        ],
        "operations": [
            {"name": "project", "family": "matmul", "inputs": ["a", "b"], "outputs": ["p"]},
            {"name": "activate", "family": "elementwise", "inputs": ["p"], "outputs": ["r"],
             "attributes": {"elementwise_kind": "relu"}},
            {"name": "raw_rows", "family": "reduction", "inputs": ["p"], "outputs": ["raw"],
             "attributes": {"axis": 1}},
            {"name": "positive_rows", "family": "reduction", "inputs": ["r"],
             "outputs": ["positive"], "attributes": {"axis": 1}},
        ],
        "returns": [{"public_name": "z_raw", "tensor_name": "raw", "required": True},
                    {"public_name": "a_positive", "tensor_name": "positive", "required": True}],
    }


def typed():
    return SourceIntentModule(
        "json_branch",
        tuple(SourceIntentTensor(name, shape) for name, shape in (
            ("a", (1, 2)), ("b", (2, 2)), ("p", (1, 2)), ("r", (1, 2)),
            ("raw", (1,)), ("positive", (1,)),
        )),
        (
            SourceIntentOperation("project", "matmul", ("a", "b"), ("p",)),
            SourceIntentOperation("activate", "elementwise", ("p",), ("r",),
                                  attributes={"elementwise_kind": "relu"}),
            SourceIntentOperation("raw_rows", "reduction", ("p",), ("raw",),
                                  attributes={"axis": 1}),
            SourceIntentOperation("positive_rows", "reduction", ("r",), ("positive",),
                                  attributes={"axis": 1}),
        ), returns=(SourceIntentReturn("z_raw", "raw"),
                    SourceIntentReturn("a_positive", "positive")),
    )


def backends():
    kinds = frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE, OperationKind.REDUCTION})
    return (BoundedBackendBinding(BackendCapability("cpu", kinds,
                                                  memory_domain=MemoryDomainKind.HOST_RAM),
                                  DAGTarget.C11),)


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def input_document(values=None):
    return {"schema_version": api.INPUT_SCHEMA_VERSION,
            "inputs": {"a": [2, -3], "b": [4, 5, 6, 7]} if values is None else values}


@pytest.fixture
def application():
    module, bindings = typed(), backends()
    return module, bindings, prepare_bounded_c11_application(module, bindings)


def reject_graph(data):
    with pytest.raises(api.BoundedCPUJSONError) as caught:
        api.source_intent_from_json(data)
    assert caught.value.reason == str(caught.value) == "graph_json_rejected"
    assert caught.value.__suppress_context__


def reject_input(application, data):
    with pytest.raises(api.BoundedCPUJSONError) as caught:
        api.inputs_from_json(*application, data)
    assert caught.value.reason == str(caught.value) == "input_json_rejected"
    assert caught.value.__suppress_context__


def test_json_and_typed_graph_produce_identical_application_bytes(application):
    module = api.source_intent_from_json(encode(document()))
    assert module == typed()
    json_application = prepare_bounded_c11_application(module, application[1])
    assert json_application.files() == application[2].files()
    assert json_application.program_digest == application[2].program_digest
    assert [binding.public_name for binding in module.returns] == ["z_raw", "a_positive"]


def test_whitespace_key_order_and_optional_defaults_do_not_change_identity(application):
    value = document()
    value = {key: value[key] for key in reversed(value)}
    for item in value["tensors"]:
        item["dtype"] = "float32"
    for item in value["operations"]:
        item["hints"] = {}
    for item in value["returns"]:
        item.pop("required")
    module = api.source_intent_from_json(json.dumps(value, indent=4, sort_keys=True).encode())
    assert prepare_bounded_c11_application(module, application[1]).files() == application[2].files()


def test_input_integer_and_fractional_tokens_convert_to_floats_and_encode_identically(application):
    result = api.inputs_from_json(*application, encode(input_document()))
    assert result == {"a": (2.0, -3.0), "b": (4.0, 5.0, 6.0, 7.0)}
    assert all(type(value) is float for values in result.values() for value in values)
    expected = {"a": (2.0, -3.0), "b": (4.0, 5.0, 6.0, 7.0)}
    assert encode_bounded_c11_inputs(*application, result) == encode_bounded_c11_inputs(
        *application, expected)
    reverse = {"b": [4.0, 5.0, 6.0, 7.0], "a": [2.0, -3.0]}
    assert api.inputs_from_json(*application, encode(input_document(reverse))) == expected


@pytest.mark.parametrize("zero", ("-0", "-0.0", "-0e-999", "-0.000e+999"))
def test_negative_zero_keeps_its_sign_in_json_integer_and_float_tokens(application, zero):
    payload = encode(input_document()).replace(b"[2,-3]", ("[" + zero + ",1]").encode())
    result = api.inputs_from_json(*application, payload)
    assert math.copysign(1.0, result["a"][0]) == -1.0


class HookBytes(bytes):
    def __len__(self):
        raise AssertionError("caller bytes hook")


class Hook:
    def __str__(self):
        raise AssertionError("caller string hook")

    def __bytes__(self):
        raise AssertionError("caller bytes hook")


@pytest.mark.parametrize("bad", (None, False, 0, "{}", {}, [], bytearray(b"{}"),
                                memoryview(b"{}"), HookBytes(b"{}"), Hook()),
                         ids=map(str, range(10)))
def test_public_boundaries_accept_only_exact_bytes_without_hooks(application, bad):
    reject_graph(bad)
    reject_input(application, bad)


@pytest.mark.parametrize("bad", (
    b"", b" ", b"\xef\xbb\xbf{}", b"\xff", b"\xc0\x80", b"\xed\xa0\x80", b"{} trailing",
    b"{}{}", b"[}", b'{"x":}', b'{"x":1,}', b'{"x":\n}', b'{"x":"\\q"}',
    b'{"x":"\\u123"}', b'{"x":"\\ud800"}', b'{"\\udfff":1}', b'{"x":"\x00"}',
    b'"unterminated', b"NaN", b"Infinity", b"-Infinity", b"01", b"+1", b"1.", b".1", b"1e",
    b'{"x":1,"x":2}', b'{"x":{"y":1,"y":2}}', b'{"x":1,"\\u0078":2}',
), ids=map(str, range(29)))
def test_invalid_json_utf8_and_duplicate_keys_reject_source_free(application, bad):
    reject_graph(bad)
    reject_input(application, bad)


def _no_call(*args, **kwargs):
    raise AssertionError("downstream call before boundary validation")


@pytest.mark.parametrize("bad", (
    b" " * (api.MAX_GRAPH_JSON_BYTES + 1),
    b"[" * (api.MAX_GRAPH_JSON_DEPTH + 1) + b"0" + b"]" * (api.MAX_GRAPH_JSON_DEPTH + 1),
    b"[" + b"0," * api.MAX_GRAPH_JSON_TOKENS + b"0]",
    b"1" * (api.MAX_JSON_NUMBER_CHARS + 1),
), ids=("bytes", "depth", "tokens", "number"))
def test_graph_lexical_budgets_reject_before_json_loads(monkeypatch, bad):
    monkeypatch.setattr(api.json, "loads", _no_call)
    reject_graph(bad)


@pytest.mark.parametrize("bad", (
    b" " * (api.MAX_INPUT_JSON_BYTES + 1),
    b"[" * (api.MAX_INPUT_JSON_DEPTH + 1) + b"0" + b"]" * (api.MAX_INPUT_JSON_DEPTH + 1),
    b"[" + b"0," * api.MAX_INPUT_JSON_TOKENS + b"0]",
    b"-1e" + b"9" * api.MAX_JSON_NUMBER_CHARS,
), ids=("bytes", "depth", "tokens", "number"))
def test_input_lexical_budgets_reject_before_json_loads(application, monkeypatch, bad):
    monkeypatch.setattr(api.json, "loads", _no_call)
    reject_input(application, bad)


def test_prescan_ignores_brackets_and_escaped_quotes_inside_strings():
    text = json.dumps({"x": '[{]}\\\"' * 20})
    api._scan(text, 1, 5)
    assert api._decode(text.encode(), max_bytes=1000, max_depth=1,
                       max_tokens=5, inputs=False) == json.loads(text)
    with pytest.raises(ValueError):
        api._scan(text, 1, 4)


@pytest.mark.parametrize("field,value", (
    ("schema_version", None), ("schema_version", "source_intent.v1"),
    ("name", "x" * 65), ("tensors", []), ("tensors", [None] * 25),
    ("operations", []), ("operations", [None] * 9), ("returns", []), ("returns", [None] * 9),
), ids=map(str, range(9)))
def test_top_level_graph_limits_precede_legacy_intake(monkeypatch, field, value):
    graph = document()
    graph[field] = value
    monkeypatch.setattr(api, "source_intent_from_mapping", _no_call)
    reject_graph(encode(graph))


@pytest.mark.parametrize("field", ("name", "schema_version", "tensors", "operations", "returns"))
def test_every_required_graph_field_is_explicit(field):
    graph = document()
    del graph[field]
    reject_graph(encode(graph))


@pytest.mark.parametrize("path,key,value", (
    ((), "python_source", "SECRET_SOURCE"), (("tensors", 0), "command", "SECRET_COMMAND"),
    (("operations", 0), "backend", "gpu"), (("returns", 0), "file_path", "/secret"),
    (("operations", 0, "hints"), "device", "gpu"),
    (("operations", 0, "attributes"), "kernel", "arbitrary"),
), ids=map(str, range(6)))
def test_unknown_fields_reject_before_legacy_intake(monkeypatch, path, key, value):
    graph = document()
    graph["operations"][0].update({"hints": {}, "attributes": {}})
    target = graph
    for component in path:
        target = target[component]
    target[key] = value
    monkeypatch.setattr(api, "source_intent_from_mapping", _no_call)
    reject_graph(encode(graph))


@pytest.mark.parametrize("shape", ([], [0], [-1], [65], [1, 2, 3], [True], [1.0], ["1"], [None]))
def test_shape_bounds_and_integer_types_precede_intake(monkeypatch, shape):
    graph = document()
    graph["tensors"][0]["shape"] = shape
    monkeypatch.setattr(api, "source_intent_from_mapping", _no_call)
    reject_graph(encode(graph))


@pytest.mark.parametrize("mutation", (
    "duplicate_tensor", "duplicate_producer", "forward_reference", "in_place", "unused_tensor",
    "unknown_tensor", "nonterminal_return", "partial_returns", "duplicate_alias", "wrong_matmul",
    "nonrelu", "optional_return", "unknown_family", "wrong_axis",
))
def test_json_graph_still_requires_all_bounded_semantics(mutation):
    graph = document()
    if mutation == "duplicate_tensor":
        graph["tensors"][1]["name"] = "a"
    elif mutation == "duplicate_producer":
        graph["operations"][1]["outputs"] = ["p"]
    elif mutation == "forward_reference":
        graph["operations"][:2] = graph["operations"][1::-1]
    elif mutation == "in_place":
        graph["operations"][1]["outputs"] = ["p"]
    elif mutation == "unused_tensor":
        graph["tensors"].append({"name": "unused", "shape": [1]})
    elif mutation == "unknown_tensor":
        graph["operations"][0]["inputs"] = ["missing", "b"]
    elif mutation == "nonterminal_return":
        graph["returns"][0]["tensor_name"] = "p"
    elif mutation == "partial_returns":
        graph["returns"].pop()
    elif mutation == "duplicate_alias":
        graph["returns"][1]["public_name"] = "z_raw"
    elif mutation == "wrong_matmul":
        graph["tensors"][1]["shape"] = [1, 2]
    elif mutation == "nonrelu":
        graph["operations"][1]["attributes"]["elementwise_kind"] = "gelu"
    elif mutation == "optional_return":
        graph["returns"][0]["required"] = False
    elif mutation == "unknown_family":
        graph["operations"][0]["family"] = "softmax"
    else:
        graph["operations"][2]["attributes"]["axis"] = 0
    reject_graph(encode(graph))


@pytest.mark.parametrize("token", ("NaN", "Infinity", "-Infinity", "1e999", "-1e999",
                                   "1e-999", "-1e-999", "0.0001e-999", "1e-324",
                                   "3.5e38", "1e-40", "-1e-40", "1e-100", "true", "false", "null"))
def test_numeric_inputs_reject_nonfinite_underflow_subnormal_and_non_numbers(application, token):
    data = encode(input_document()).replace(b"[2,-3]", ("[" + token + ",1]").encode())
    reject_input(application, data)


@pytest.mark.parametrize("token", ("1e-999", "1e999", "-1e-999"))
def test_binary64_range_rejects_before_encoder(application, monkeypatch, token):
    data = encode(input_document()).replace(b"[2,-3]", ("[" + token + ",1]").encode())
    monkeypatch.setattr(api, "encode_bounded_c11_inputs", _no_call)
    reject_input(application, data)


@pytest.mark.parametrize("value", (
    {}, {"inputs": {}}, {"schema_version": api.INPUT_SCHEMA_VERSION},
    {"schema_version": "unknown", "inputs": {}},
    {"schema_version": api.INPUT_SCHEMA_VERSION, "inputs": {}, "path": "SECRET"},
    {"schema_version": api.INPUT_SCHEMA_VERSION, "inputs": []},
    input_document({}), input_document({"a": []}), input_document({"x" * 65: [1]}),
    input_document({"a": [[1]], "b": [1]}), input_document({"a": [True], "b": [1]}),
    input_document({str(i): [0] for i in range(25)}),
    input_document({"a": [0] * 4097}),
), ids=map(str, range(13)))
def test_input_structure_and_bounds_precede_encoder(application, monkeypatch, value):
    monkeypatch.setattr(api, "encode_bounded_c11_inputs", _no_call)
    reject_input(application, encode(value))


def test_input_total_scalar_budget_precedes_encoder(application, monkeypatch):
    # 69,632 values remain below the byte/token caps but exceed total elements.
    data = encode(input_document({f"x{i}": [0] * 4096 for i in range(17)}))
    monkeypatch.setattr(api, "encode_bounded_c11_inputs", _no_call)
    reject_input(application, data)


@pytest.mark.parametrize("value", (
    {"a": [1], "b": [1, 2, 3, 4]}, {"a": [1, 2], "b": [1, 2, 3]},
    {"a": [1, 2]}, {"a": [1, 2], "b": [1, 2, 3, 4], "extra": [1]},
    {"wrong": [1, 2], "b": [1, 2, 3, 4]},
))
def test_existing_encoder_enforces_exact_public_names_and_lengths(application, value):
    reject_input(application, encode(input_document(value)))


def test_input_json_revalidates_original_graph_bindings_and_application(application):
    data = encode(input_document())
    module, bindings, compiled = application
    reject_input((replace(module, name="drift"), bindings, compiled), data)
    rejected = replace(bindings[0], capability=replace(bindings[0].capability, name="other"))
    reject_input((module, (rejected,), compiled), data)
    altered = replace(compiled, application_c=compiled.application_c + " ")
    reject_input((module, bindings, altered), data)


def test_graph_neutral_hint_numbers_remain_bounded_and_normalized():
    graph = document()
    graph["operations"][0]["hints"] = {"max_error_budget": 2, "robust_to_noise": False}
    parsed = api.source_intent_from_json(encode(graph))
    assert parsed.operations[0].hints["max_error_budget"] == 2.0
    for bad in (True, -1, 1000001, "2", None):
        altered = copy.deepcopy(graph)
        altered["operations"][0]["hints"]["max_error_budget"] = bad
        reject_graph(encode(altered))


def test_graph_and_input_failures_do_not_include_user_text(application):
    secret = "private-token-/sensitive/path"
    bad = ('{"' + secret + '":"' + secret + '"}').encode()
    for call in (lambda: api.source_intent_from_json(bad),
                 lambda: api.inputs_from_json(*application, bad)):
        with pytest.raises(api.BoundedCPUJSONError) as caught:
            call()
        assert secret not in str(caught.value)
        assert secret not in repr(caught.value)
