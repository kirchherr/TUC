"""Data-boundary tests, not native execution observations."""

import copy
import json
import struct
from dataclasses import FrozenInstanceError
from hashlib import sha256

import pytest

from tuc.bounded_cpu_application_cli import cpu_bindings
from tuc.compiler import bounded_cpu_model as api
from tuc.compiler.bounded_c11_application import (
    encode_bounded_c11_inputs,
    prepare_bounded_c11_application,
)
from tuc.compiler.bounded_cpu_batch import batch_from_json
from tuc.compiler.bounded_cpu_json import inputs_from_json, source_intent_from_json


def encode(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()


def graph():
    return {
        "schema_version": "source_intent.v0",
        "name": "model_linear",
        "tensors": [
            {"name": n, "shape": s}
            for n, s in (("x", [1, 2]), ("w", [2, 2]), ("p", [1, 2]), ("b", [2]), ("y", [1, 2]))
        ],
        "operations": [
            {
                "name": "linear",
                "family": "matmul",
                "inputs": ["x", "w"],
                "outputs": ["p"],
                "attributes": {"rhs_transposed": True},
            },
            {
                "name": "bias",
                "family": "elementwise",
                "inputs": ["p", "b"],
                "outputs": ["y"],
                "attributes": {"elementwise_kind": "add"},
            },
        ],
        "returns": [{"public_name": "scores", "tensor_name": "y"}],
    }


def inputs(value):
    return encode({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": value})


def model(parameters=None):
    return {
        "schema_version": api.MODEL_SCHEMA_VERSION,
        "graph": graph(),
        "parameters": {"w": [2, -1, 1, 3], "b": [0.5, -0.0]} if parameters is None else parameters,
    }


def test_canonical_model_roundtrip_and_independent_bit_identity():
    first = api.model_from_json(encode(model()))
    second = api.model_from_json(first.model_json)
    assert first == second
    assert api.pack_model(encode(graph()), inputs(model()["parameters"])) == first.model_json
    assert first.variable_inputs == ("x",)
    assert first.parameters == (("b", (0.5, -0.0)), ("w", (2.0, -1.0, 1.0, 3.0)))
    assert struct.pack("<f", dict(first.parameters)["b"][1]) == bytes.fromhex("00000080")
    document = json.loads(first.model_json)
    identity = {
        "schema_version": api.MODEL_SCHEMA_VERSION,
        "graph": document["graph"],
        "parameter_bits": {"b": "0000003f00000080", "w": "00000040000080bf0000803f00004040"},
    }
    assert (
        first.model_digest
        == sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()
    )
    assert first.model_json.endswith(b"\n")
    with pytest.raises(FrozenInstanceError):
        first.model_digest = "forged"


def test_spelling_order_defaults_and_fp32_rounding_are_canonical():
    a = model()
    b = copy.deepcopy(a)
    b["parameters"] = {"b": [0.500000001, -0.0], "w": [2.0, -1.0, 1.0, 3.0]}
    for t in b["graph"]["tensors"]:
        t["dtype"] = "float32"
    for op in b["graph"]["operations"]:
        op["hints"] = {}
    b["graph"]["returns"][0]["required"] = True
    assert (
        api.model_from_json(encode(a)).model_json
        == api.model_from_json(json.dumps(b, indent=2, sort_keys=True).encode()).model_json
    )


def test_literal_integer_negative_zero_survives_both_model_and_parameter_file():
    raw = encode(model()).replace(b"-0.0", b"-0")
    actual = api.model_from_json(raw)
    assert struct.pack("<f", dict(actual.parameters)["b"][1]) == bytes.fromhex("00000080")
    packed = api.pack_model(encode(graph()), inputs(model()["parameters"]).replace(b"-0.0", b"-0"))
    assert api.model_from_json(packed) == actual


@pytest.mark.parametrize("change", ["parameter", "signed_zero", "graph", "partition"])
def test_identity_changes_without_changing_unrelated_program(change):
    a, b = model(), model()
    if change == "parameter":
        b["parameters"]["w"][0] = 3
    elif change == "signed_zero":
        b["parameters"]["b"][1] = 0.0
    elif change == "graph":
        b["graph"]["name"] = "other_model"
    else:
        del b["parameters"]["b"]
    left, right = [api.model_from_json(encode(v)) for v in (a, b)]
    assert left.model_digest != right.model_digest
    if change != "graph":
        assert (
            prepare_bounded_c11_application(
                source_intent_from_json(left.graph_json), cpu_bindings()
            ).program_digest
            == prepare_bounded_c11_application(
                source_intent_from_json(right.graph_json), cpu_bindings()
            ).program_digest
        )


def test_existing_request_and_batch_identities_survive_parameter_expansion():
    data = encode(model())
    module = source_intent_from_json(encode(graph()))
    application = prepare_bounded_c11_application(module, cpu_bindings())
    expanded = api.expand_model_inputs(data, inputs({"x": [-0.0, 2]}))
    existing = inputs({**model()["parameters"], "x": [-0.0, 2]})
    values = [
        inputs_from_json(module, cpu_bindings(), application, d) for d in (expanded, existing)
    ]
    assert [encode_bounded_c11_inputs(module, cpu_bindings(), application, v) for v in values][
        0
    ] == encode_bounded_c11_inputs(module, cpu_bindings(), application, values[1])
    batch = {
        "schema_version": "tuc.bounded_cpu_batch.v0",
        "requests": [
            {"id": "first", "inputs": {"x": [1, 2]}},
            {"id": "last", "inputs": {"x": [-0.0, 4]}},
        ],
    }
    new = api.expand_model_batch(data, encode(batch))
    old = encode({**batch, "shared_inputs": model()["parameters"]})
    assert batch_from_json(module, cpu_bindings(), application, new) == batch_from_json(
        module, cpu_bindings(), application, old
    )


def test_variable_input_can_be_shared_without_overriding_parameters():
    batch = {
        "schema_version": "tuc.bounded_cpu_batch.v0",
        "shared_inputs": {"x": [1, 2]},
        "requests": [{"id": "a", "inputs": {}}, {"id": "b", "inputs": {}}],
    }
    expanded = json.loads(api.expand_model_batch(encode(model()), encode(batch)))
    assert set(expanded["shared_inputs"]) == {"x", "w", "b"}


@pytest.mark.parametrize(
    "bad",
    [
        b"",
        b"{}",
        b"[]",
        b"NaN",
        b"\xff",
        b"\xef\xbb\xbf{}",
        b'{"schema_version":"x","schema_version":"y"}',
        b'"\\ud800"',
        b"[" * 14 + b"0" + b"]" * 14,
        b" " * (api.MAX_MODEL_JSON_BYTES + 1),
        b"[" + b"0," * 102050 + b"0]",
        b"1" * 65,
        b"1e999",
        b"1e-999",
        bytearray(b"{}"),
        None,
        3,
    ],
    ids=range(17),
)
def test_hostile_serialized_model_rejects_with_closed_diagnostic(bad):
    with pytest.raises(api.BoundedCPUModelError, match="^model_json_rejected$"):
        api.model_from_json(bad)


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"x": [1, 2], "w": [1] * 4, "b": [1] * 2},
        {"missing": [1]},
        {"y": [1, 2]},
        {"p": [1, 2]},
        {"w": [1]},
        {"w": [[1] * 4]},
        {"w": [True] * 4},
        {"w": ["secret"] * 4},
        {"w": [1e100] * 4},
        {"w": [1e-50] * 4},
        {"w": [1e-40] * 4},
        {"w": [1] * 4097},
        [],
        None,
    ],
    ids=range(15),
)
def test_parameter_boundary_rejects_bad_binding_extent_or_numeric_domain(parameters):
    with pytest.raises(api.BoundedCPUModelError):
        api.model_from_json(encode(model(parameters))) if parameters is not None else (
            api.model_from_json(encode({**model(), "parameters": None}))
        )


@pytest.mark.parametrize(
    "field",
    ["model_digest", "path", "url", "pickle", "backend", "source", "module", "device", "command"],
)
def test_no_executable_or_external_reference_fields(field):
    value = model()
    value[field] = "private-data"
    with pytest.raises(api.BoundedCPUModelError):
        api.model_from_json(encode(value))


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "dimension",
        "bool_dimension",
        "forward",
        "unused",
        "return",
        "dtype",
        "axis",
        "token_budget",
    ],
)
def test_graph_still_uses_existing_strict_bounded_gate(change):
    value = model()
    g = value["graph"]
    if change == "schema":
        g["schema_version"] = "unknown"
    elif change == "dimension":
        g["tensors"][0]["shape"] = [65, 2]
    elif change == "bool_dimension":
        g["tensors"][0]["shape"][0] = True
    elif change == "forward":
        g["operations"].reverse()
    elif change == "unused":
        g["tensors"].append({"name": "unused", "shape": [1]})
    elif change == "return":
        g["returns"][0]["tensor_name"] = "x"
    elif change == "dtype":
        g["tensors"][0]["dtype"] = "float64"
    elif change == "axis":
        g["operations"][0]["attributes"]["axis"] = 1
    else:
        g["extra"] = [0] * 3000
    with pytest.raises(api.BoundedCPUModelError):
        api.model_from_json(encode(value))


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"x": [1]},
        {"x": [1, 2], "b": [0.5, -0.0]},
        {"x": [1, 2], "unknown": [0]},
        {"x": [True, 0]},
        {"x": [1e100, 0]},
        {"x": [1e-40, 0]},
        {"x": [1e-50, 0]},
    ],
    ids=range(8),
)
def test_exact_variable_input_contract(bad):
    with pytest.raises(api.BoundedCPUModelError):
        api.expand_model_inputs(encode(model()), inputs(bad))


@pytest.mark.parametrize("location", ["shared", "last"])
def test_fixed_parameter_override_rejects_even_if_identical(location):
    batch = {
        "schema_version": "tuc.bounded_cpu_batch.v0",
        "requests": [
            {"id": "first", "inputs": {"x": [1, 2]}},
            {"id": "last", "inputs": {"x": [3, 4]}},
        ],
    }
    if location == "shared":
        batch["shared_inputs"] = {"b": [0.5, -0.0]}
    else:
        batch["requests"][-1]["inputs"]["b"] = [0.5, -0.0]
    with pytest.raises(api.BoundedCPUModelError):
        api.expand_model_batch(encode(model()), encode(batch))


def test_hostile_byte_subclass_never_runs_user_methods():
    class Hostile(bytes):
        def decode(self, *args, **kwargs):
            pytest.fail("untrusted method called")

        def __len__(self):
            pytest.fail("untrusted method called")

    with pytest.raises(api.BoundedCPUModelError):
        api.model_from_json(Hostile(b"{}"))
