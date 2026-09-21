"""Pure batch input checks; fixtures and encodings are not native observations."""

import copy
import hashlib
import json
import math
from dataclasses import FrozenInstanceError, replace

import pytest

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_cpu_batch as api
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


def _application(left=(1, 2), right=(2, 2), *, outputs=1, kind="matmul"):
    if kind == "relu":
        tensors = [SourceIntentTensor("z_input", left)]
        inputs = ("z_input",)
        shape = left
        family, attributes = "elementwise", {"elementwise_kind": "relu"}
    else:
        tensors = [SourceIntentTensor("z_input", left), SourceIntentTensor("a_weight", right)]
        inputs = ("z_input", "a_weight")
        shape = (left[0], right[1]) if kind == "matmul" else left
        family, attributes = ("matmul", {}) if kind == "matmul" else (
            "elementwise", {"elementwise_kind": "add"})
    operations, returns = [], []
    for index in range(outputs):
        name = "result" + str(index)
        tensors.append(SourceIntentTensor(name, shape))
        operations.append(SourceIntentOperation("compute" + str(index), family, inputs,
                                                (name,), attributes=attributes))
        returns.append(SourceIntentReturn("public" + str(index), name))
    module = SourceIntentModule("batch_graph", tuple(tensors), tuple(operations),
                                returns=tuple(returns))
    bindings = (BoundedBackendBinding(BackendCapability(
        "cpu", frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.HOST_RAM), DAGTarget.C11),)
    return module, bindings, prepare_bounded_c11_application(module, bindings)


@pytest.fixture
def application():
    return _application()


def _json(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _document():
    return {"schema_version": api.BATCH_SCHEMA_VERSION,
            "shared_inputs": {"a_weight": [1, 2, 3, 4]},
            "requests": [{"id": "first", "inputs": {"z_input": [1, -2]}},
                         {"id": "second", "inputs": {"z_input": [3, 0]}}]}


def _reject(application, data):
    with pytest.raises(api.BoundedCPUBatchError) as caught:
        api.batch_from_json(*application, data)
    assert caught.value.reason == str(caught.value) == "batch_json_rejected"
    assert caught.value.__suppress_context__


def _forbidden(*args, **kwargs):
    raise AssertionError("downstream processing before rejection")


def test_complete_batch_matches_single_request_frames_and_independent_digest(application):
    batch = api.batch_from_json(*application, _json(_document()))
    assert batch.program_digest == application[2].program_digest
    assert [item.request_id for item in batch.requests] == ["first", "second"]
    for request, raw in zip(batch.requests, _document()["requests"], strict=True):
        values = {"z_input": tuple(float(v) for v in raw["inputs"]["z_input"]),
                  "a_weight": (1.0, 2.0, 3.0, 4.0)}
        assert request.inputs == tuple(values.items())  # Binding order, not alphabetical.
        assert request.values() == values
        assert request.request_digest == encode_bounded_c11_inputs(
            *application, values)[40:72].hex()
    material = {"schema_version": "tuc.bounded_cpu_batch.v0",
                "program_digest": application[2].program_digest,
                "requests": [{"id": item.request_id, "request_digest": item.request_digest}
                             for item in batch.requests]}
    expected = json.dumps(material, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    assert batch.batch_digest == hashlib.sha256(expected).hexdigest()
    assert len(batch.batch_digest) == 64


def test_optional_shared_layout_whitespace_and_key_order_do_not_change_identity(application):
    original = _document()
    expected = api.batch_from_json(*application, _json(original))
    expanded = copy.deepcopy(original)
    shared = expanded.pop("shared_inputs")
    for request in expanded["requests"]:
        request["inputs"].update(shared)
        request["inputs"] = dict(reversed(tuple(request["inputs"].items())))
    assert api.batch_from_json(*application, json.dumps(expanded, indent=3,
                                                       sort_keys=True).encode()) == expected
    expanded["shared_inputs"] = {}
    assert api.batch_from_json(*application, _json(expanded)) == expected


@pytest.mark.parametrize("change", ["id", "order", "value"])
def test_semantic_changes_are_bound_in_batch_digest(application, change):
    document = _document()
    original = api.batch_from_json(*application, _json(document))
    if change == "id":
        document["requests"][0]["id"] = "renamed"
    elif change == "order":
        document["requests"].reverse()
    else:
        document["requests"][0]["inputs"]["z_input"][0] = 5
    changed = api.batch_from_json(*application, _json(document))
    assert changed.batch_digest != original.batch_digest
    if change == "id":
        assert changed.requests[0].request_digest == original.requests[0].request_digest
    elif change == "order":
        assert changed.requests == original.requests[::-1]
    else:
        assert changed.requests[0].request_digest != original.requests[0].request_digest


def test_request_identity_uses_encoded_binary32_not_decimal_spelling(application):
    document = _document()
    first = api.batch_from_json(*application, _json(document))
    document["requests"][0]["inputs"]["z_input"][0] = 1.0 + 2.0**-25
    second = api.batch_from_json(*application, _json(document))
    assert first.requests[0].values() != second.requests[0].values()
    assert first.requests[0].request_digest == second.requests[0].request_digest
    assert first.batch_digest == second.batch_digest


@pytest.mark.parametrize("token", [b"-0", b"-0.0", b"-0e-999", b"-0.000e+999"])
def test_signed_zero_is_preserved_and_digest_distinct(application, token):
    positive = _json(_document())
    negative = positive.replace(b"[3,0]", b"[3," + token + b"]")
    first = api.batch_from_json(*application, positive)
    second = api.batch_from_json(*application, negative)
    assert math.copysign(1.0, second.requests[1].values()["z_input"][1]) == -1.0
    assert first.requests[1].request_digest != second.requests[1].request_digest
    assert first.batch_digest != second.batch_digest


def test_result_is_immutable_and_values_returns_an_independent_mapping(application):
    batch = api.batch_from_json(*application, _json(_document()))
    request = batch.requests[0]
    assert not hasattr(batch, "__dict__") and not hasattr(request, "__dict__")
    with pytest.raises(FrozenInstanceError):
        batch.batch_digest = "changed"
    with pytest.raises(FrozenInstanceError):
        request.request_id = "changed"
    values = request.values()
    values["z_input"] = (99.0, 99.0)
    assert request.values()["z_input"] == (1.0, -2.0)


@pytest.mark.parametrize("identifier", ["", "1a", "_a", "-a", "a b", "a/b", "a.b", "é",
                                       "a\n", "a" * 65, None, True, 1, [], {}], ids=range(15))
def test_request_ids_are_bounded_ascii_identifiers(application, identifier):
    document = _document()
    document["requests"][0]["id"] = identifier
    _reject(application, _json(document))


def test_ids_are_case_sensitive_unique_and_allow_exact_length_boundary(application):
    document = _document()
    document["requests"][0]["id"] = "A" + "a_-9" * 15 + "xyz"
    document["requests"][1]["id"] = document["requests"][0]["id"].lower()
    assert len(document["requests"][0]["id"]) == 64
    assert len(api.batch_from_json(*application, _json(document)).requests) == 2
    document["requests"][1]["id"] = document["requests"][0]["id"]
    _reject(application, _json(document))


@pytest.mark.parametrize("mutation", ["missing-schema", "schema", "extra", "missing-requests",
                                     "empty", "too-many", "not-list", "missing-id",
                                     "missing-inputs", "request-extra", "request-type",
                                     "shared-type", "inputs-type"])
def test_envelope_and_request_fields_are_closed(application, mutation):
    document = _document()
    if mutation == "missing-schema":
        del document["schema_version"]
    elif mutation == "schema":
        document["schema_version"] += "bad"
    elif mutation == "extra":
        document["command"] = "not permitted"
    elif mutation == "missing-requests":
        del document["requests"]
    elif mutation == "empty":
        document["requests"] = []
    elif mutation == "too-many":
        document["requests"] = [{"id": "r" + str(i), "inputs": {}} for i in range(17)]
    elif mutation == "not-list":
        document["requests"] = {}
    elif mutation == "missing-id":
        del document["requests"][0]["id"]
    elif mutation == "missing-inputs":
        del document["requests"][0]["inputs"]
    elif mutation == "request-extra":
        document["requests"][0]["request_digest"] = "untrusted"
    elif mutation == "request-type":
        document["requests"][0] = []
    elif mutation == "shared-type":
        document["shared_inputs"] = []
    else:
        document["requests"][0]["inputs"] = []
    _reject(application, _json(document))


@pytest.mark.parametrize("mutation", ["overlap", "missing", "extra", "short", "long", "empty",
                                     "nested", "boolean", "string"])
def test_last_request_rejects_without_returning_a_partial_batch(application, mutation):
    document = _document()
    values = document["requests"][-1]["inputs"]
    if mutation == "overlap":
        values["a_weight"] = [1, 2, 3, 4]  # Equal overlapping values still reject.
    elif mutation == "missing":
        del values["z_input"]
    elif mutation == "extra":
        values["other"] = [0]
    else:
        values["z_input"] = {"short": [1], "long": [1, 2, 3], "empty": [],
                             "nested": [[1], [2]], "boolean": [True, 1],
                             "string": ["1", 2]}[mutation]
    _reject(application, _json(document))


def test_hostile_last_request_is_preflighted_before_any_encoding(application, monkeypatch):
    document = _document()
    document["requests"][-1]["inputs"]["z_input"] = [False, 0]
    monkeypatch.setattr(api, "inputs_from_json", _forbidden)
    monkeypatch.setattr(api, "encode_bounded_c11_inputs", _forbidden)
    _reject(application, _json(document))


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"-Infinity", b"1e999", b"1e-999",
                                   b"1e-50", b"1e-40", b"1e40"])
def test_invalid_numeric_domain_rejects_in_last_request(application, token):
    _reject(application, _json(_document()).replace(b"[3,0]", b"[3," + token + b"]"))


@pytest.mark.parametrize("data", [b"", b" ", b"\xef\xbb\xbf{}", b"\xff", b"{}{}",
                                  b'{"x":"\\ud800"}', b'{"x":1,"x":2}',
                                  b'{"x":1,"\\u0078":2}', b'{"x":{"a":1,"a":2}}',
                                  b'{"x":1,}', b'{"x":"\x00"}'], ids=range(11))
def test_malformed_json_utf8_and_duplicate_keys_reject(application, data):
    _reject(application, data)


class _BytesHook(bytes):
    def __len__(self):
        raise AssertionError("caller byte hook")


class _ObjectHook:
    def __str__(self):
        raise AssertionError("caller string hook")

    def __bytes__(self):
        raise AssertionError("caller bytes hook")


@pytest.mark.parametrize("data", [None, False, {}, [], "{}", bytearray(b"{}"),
                                  memoryview(b"{}"), _BytesHook(b"{}"), _ObjectHook()],
                         ids=range(9))
def test_only_exact_bytes_are_accepted_without_host_hooks(application, data):
    _reject(application, data)


@pytest.mark.parametrize("data", [b" " * (api.MAX_BATCH_JSON_BYTES + 1),
                                  b"[" * 9 + b"0" + b"]" * 9,
                                  b"[" + b"0," * 100000 + b"0]", b"1" * 65],
                         ids=("bytes", "depth", "tokens", "number"))
def test_lexical_budgets_precede_json_loading_and_application_validation(
    application, monkeypatch, data,
):
    monkeypatch.setattr(api.json, "loads", _forbidden)
    monkeypatch.setattr(api, "validate_bounded_c11_application", _forbidden)
    _reject(application, data)


def test_exact_document_byte_boundary_is_accepted(application):
    data = _json(_document())
    padded = data + b" " * (api.MAX_BATCH_JSON_BYTES - len(data))
    assert api.batch_from_json(*application, padded) == api.batch_from_json(*application, data)


def _shared_requests(shared, specific, count):
    return {"schema_version": api.BATCH_SCHEMA_VERSION, "shared_inputs": shared,
            "requests": [{"id": "r" + str(i), "inputs": specific} for i in range(count)]}


def test_sixteen_shared_expansions_hit_both_element_budgets_exactly():
    application = _application((64, 64), kind="relu")
    document = _shared_requests({"z_input": [1] * 4096}, {}, 16)
    batch = api.batch_from_json(*application, _json(document))
    assert len(batch.requests) == 16
    assert sum(len(request.values()["z_input"]) for request in batch.requests) == 65536


def test_aggregate_inputs_count_shared_values_for_every_request_before_encoding(monkeypatch):
    application = _application((64, 64), (64,), kind="add")
    document = _shared_requests({"z_input": [1] * 4096}, {"a_weight": [1] * 64}, 15)
    assert len(api.batch_from_json(*application, _json(document)).requests) == 15
    document["requests"].append({"id": "r15", "inputs": {"a_weight": [1] * 64}})
    monkeypatch.setattr(api, "validate_bounded_c11_application", _forbidden)
    monkeypatch.setattr(api, "inputs_from_json", _forbidden)
    _reject(application, _json(document))  # 16 * (4096 + 64) > 65536.


def test_aggregate_output_budget_counts_every_public_output_before_encoding(monkeypatch):
    application = _application((64, 1), (1, 64), outputs=2)
    document = _shared_requests({"a_weight": [1] * 64}, {"z_input": [1] * 64}, 8)
    assert len(api.batch_from_json(*application, _json(document)).requests) == 8
    document["requests"].append({"id": "r8", "inputs": {"z_input": [1] * 64}})
    monkeypatch.setattr(api, "inputs_from_json", _forbidden)
    monkeypatch.setattr(api, "encode_bounded_c11_inputs", _forbidden)
    _reject(application, _json(document))  # 9 * 2 * 4096 > 65536.


@pytest.mark.parametrize("target", ["graph", "bindings", "artifact", "manifest", "digest"])
def test_tampered_graph_binding_and_application_are_closed_errors(application, target):
    module, bindings, artifact = application
    if target == "graph":
        object.__setattr__(module.tensors[0], "shape", (True, 2))
    elif target == "bindings":
        bindings = (_ObjectHook(),)
    elif target == "artifact":
        artifact = replace(artifact, application_c=artifact.application_c + " ")
    elif target == "manifest":
        artifact = replace(artifact, application_json='{"output_elements":[0]}')
    else:
        artifact = replace(artifact, program_digest="0" * 64)
    _reject((module, bindings, artifact), _json(_document()))


def test_manifest_is_not_parsed_before_artifact_validation(application, monkeypatch):
    artifact = replace(application[2], application_json="malformed secret input")
    real_decode = api._decode
    # Decode the valid batch first, then forbid any subsequent JSON load.
    def decode_then_forbid(*args, **kwargs):
        result = real_decode(*args, **kwargs)
        monkeypatch.setattr(api.json, "loads", _forbidden)
        return result
    monkeypatch.setattr(api, "_decode", decode_then_forbid)
    # Revalidation itself reconstructs manifests, so intercept only its initial
    # rejection to prove this module cannot inspect an unvalidated artifact.
    def reject_artifact(*args):
        raise ValueError("untrusted artifact")
    monkeypatch.setattr(api, "validate_bounded_c11_application", reject_artifact)
    _reject((*application[:2], artifact), _json(_document()))


def test_parser_does_not_mutate_input_artifacts_or_source_records(application):
    module, _, artifact = application
    data = _json(_document())
    original = (module.dump(), artifact.files(), data)
    first = api.batch_from_json(*application, data)
    second = api.batch_from_json(*application, data)
    assert first == second
    assert (module.dump(), artifact.files(), data) == original
