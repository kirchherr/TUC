"""Portable invocation boundary and malicious-input controls."""

from __future__ import annotations

import ast
import json
from hashlib import sha256
from pathlib import Path

import pytest

from integration.bounded_model_artifact_bundle.consumer import _OPS, _binding, _model
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_model_artifact_request as api
from tuc.compiler.bounded_model_artifact_bundle import create_bounded_model_artifact_bundle


def bindings():
    return (_binding("cpu", DAGTarget.C11, _OPS),)


def inputs(values=None):
    return json.dumps(
        {
            "schema_version": "tuc.bounded_cpu_inputs.v0",
            "inputs": {"x": values if values is not None else [1.0, -0.0, 3.0, 4.0]},
        }
    ).encode()


def context():
    model = _model(2.0)
    capabilities = bindings()
    bundle = create_bounded_model_artifact_bundle(model, capabilities)
    return model, capabilities, bundle


def canonical(root):
    return json.dumps(root, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"


def rehash(root):
    root.pop("request_digest")
    root["request_digest"] = sha256(canonical(root)).hexdigest()
    return canonical(root)


def test_portable_request_binds_model_bundle_parameters_and_variable_bits():
    model, capabilities, bundle = context()
    data = api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    value = api.validate_bounded_model_artifact_request(model, capabilities, bundle, inputs(), data)
    assert value == api.inspect_bounded_model_artifact_request(bundle, data)
    assert [item.tensor_name for item in value.inputs] == ["x", "w"]
    assert value.inputs[0].value_bits == "0000803f000000800000404000008040"
    assert value.inputs[1].value_bits == "00000040000080bf0000803f00004040"
    assert data.endswith(b"\n")
    assert data == api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())


def test_input_changes_request_identity_but_preserves_bundle():
    model, capabilities, bundle = context()
    first = api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    changed = api.create_bounded_model_artifact_request(
        model, capabilities, bundle, inputs([5.0, 6.0, 7.0, 8.0])
    )
    a = api.inspect_bounded_model_artifact_request(bundle, first)
    b = api.inspect_bounded_model_artifact_request(bundle, changed)
    assert a.request_digest != b.request_digest
    assert a.bundle_digest == b.bundle_digest
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.validate_bounded_model_artifact_request(model, capabilities, bundle, inputs(), changed)


@pytest.mark.parametrize(
    "values",
    [
        [],
        [1.0],
        [1.0] * 5,
        [True] * 4,
        [float("nan")] * 4,
        [float("inf")] * 4,
        [1e-40] * 4,
        [1e50] * 4,
        [1e-50] * 4,
    ],
)
def test_bad_variable_values_reject(values):
    model, capabilities, bundle = context()
    with pytest.raises(
        api.BoundedModelArtifactRequestError, match="^model_artifact_request_rejected$"
    ):
        api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs(values))


@pytest.mark.parametrize("mapping", [{}, {"w": [1.0] * 4}, {"x": [1.0] * 4, "w": [1.0] * 4}])
def test_missing_or_overridden_parameters_reject(mapping):
    model, capabilities, bundle = context()
    data = json.dumps({"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": mapping}).encode()
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.create_bounded_model_artifact_request(model, capabilities, bundle, data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("tensor_name", "w"),
        ("tensor_index", True),
        ("shape", [True, 2]),
        ("dtype", "float64"),
        ("value_bits", "00000000"),
        ("value_bits", "0000807f" * 4),
        ("value_bits", "01000000" * 4),
        ("value_bits", "0000803F" * 4),
        ("path", "../../secret"),
    ],
)
def test_rehashed_invalid_binding_or_numeric_bits_reject(field, value):
    model, capabilities, bundle = context()
    root = json.loads(
        api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    )
    root["inputs"][0][field] = value
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.inspect_bounded_model_artifact_request(bundle, rehash(root))


def test_rehashed_fixed_parameter_override_and_order_drift_reject():
    model, capabilities, bundle = context()
    original = api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    for mode in ("fixed", "order", "missing", "extra"):
        root = json.loads(original)
        if mode == "fixed":
            root["inputs"][1]["value_bits"] = "0000803f" * 4
        elif mode == "order":
            root["inputs"].reverse()
        elif mode == "missing":
            root["inputs"].pop()
        else:
            root["inputs"].append(root["inputs"][0])
        with pytest.raises(api.BoundedModelArtifactRequestError):
            api.inspect_bounded_model_artifact_request(bundle, rehash(root))


@pytest.mark.parametrize(
    "field",
    [
        "contract",
        "bundle_digest",
        "model_digest",
        "model_compilation_digest",
        "backend_bindings_digest",
        "request_digest",
    ],
)
def test_identity_drift_rejects_even_after_rehash(field):
    model, capabilities, bundle = context()
    root = json.loads(
        api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    )
    root[field] = "0" * 64
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.inspect_bounded_model_artifact_request(
            bundle, rehash(root) if field != "request_digest" else canonical(root)
        )


def test_model_and_backend_substitution_reject():
    model, capabilities, bundle = context()
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.create_bounded_model_artifact_request(_model(3.0), capabilities, bundle, inputs())
    cuda = (_binding("cuda", DAGTarget.CUDA_SM86, _OPS),)
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.create_bounded_model_artifact_request(model, cuda, bundle, inputs())
    other = create_bounded_model_artifact_bundle(model, cuda)
    data = api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.inspect_bounded_model_artifact_request(other, data)


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"{}",
        b"[]",
        b"NaN",
        b"\xff",
        b'{"a":1,"a":2}',
        bytearray(b"{}"),
        b"[" * 100 + b"]" * 100,
    ],
)
def test_malformed_request_is_closed(data):
    _, _, bundle = context()
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.inspect_bounded_model_artifact_request(bundle, data)


def test_noncanonical_and_oversized_request_reject():
    model, capabilities, bundle = context()
    data = api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    for damaged in (data[:-1], b" " + data, b" " * (api.MAX_MODEL_ARTIFACT_REQUEST_BYTES + 1)):
        with pytest.raises(api.BoundedModelArtifactRequestError):
            api.inspect_bounded_model_artifact_request(bundle, damaged)


def test_request_module_has_no_execution_or_filesystem_surface():
    tree = ast.parse(Path(api.__file__).read_text(encoding="utf-8"))
    imported = {
        name.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for name in node.names
    }
    assert imported.isdisjoint({"subprocess", "socket", "ctypes", "pathlib", "os", "importlib"})
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile"})


def test_aggregate_budget_counts_fixed_and_variable_inputs(monkeypatch):
    model, capabilities, bundle = context()
    monkeypatch.setattr(api, "MAX_MODEL_ARTIFACT_REQUEST_ELEMENTS", 8)
    data = api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    assert len(api.inspect_bounded_model_artifact_request(bundle, data).inputs) == 2
    monkeypatch.setattr(api, "MAX_MODEL_ARTIFACT_REQUEST_ELEMENTS", 7)
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.create_bounded_model_artifact_request(model, capabilities, bundle, inputs())
    with pytest.raises(api.BoundedModelArtifactRequestError):
        api.inspect_bounded_model_artifact_request(bundle, data)
