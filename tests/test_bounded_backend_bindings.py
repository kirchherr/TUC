"""Untrusted declarative bindings, with no backend loading or execution."""

import copy
import json
from dataclasses import replace

import pytest

from integration.bounded_model_artifact_bundle.consumer import _OPS, _binding
from tests.test_bounded_model_application import context
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import (
    BACKEND_BINDINGS_SCHEMA,
    BoundedBackendBindingsError,
    backend_bindings_from_json,
    backend_bindings_to_json,
    create_bounded_model_artifact_bundle,
)
from tuc.compiler.bounded_backend_bindings import MAX_BACKEND_BINDINGS_JSON_BYTES
from tuc.ir.model import OperationKind


def record():
    return json.loads(backend_bindings_to_json(context()[1]))


@pytest.mark.parametrize("mode", ["cpu", "cuda", "mixed"])
def test_roundtrip_preserves_original_compilation_identity(mode):
    model, cpu, *_ = context()
    cuda = _binding("accelerator", DAGTarget.CUDA_SM86, _OPS)
    if mode == "cpu":
        bindings = cpu
    elif mode == "cuda":
        bindings = (cuda,)
    else:
        cuda = replace(cuda, capability=replace(
            cuda.capability, supported_ops=frozenset({OperationKind.MATMUL}),
            preferred_for=frozenset({OperationKind.MATMUL}),
        ))
        bindings = (*cpu, cuda)
    data = backend_bindings_to_json(bindings)
    clean = backend_bindings_from_json(data)
    assert json.loads(data)["schema_version"] == BACKEND_BINDINGS_SCHEMA
    assert backend_bindings_to_json(tuple(reversed(clean))) == data
    assert create_bounded_model_artifact_bundle(model, bindings) == (
        create_bounded_model_artifact_bundle(model, clean)
    )


@pytest.mark.parametrize("field,value", [
    ("name", "../plugin"), ("name", "x" * 65), ("target", "cuda"),
    ("target", "https://remote"), ("supported_ops", []),
    ("supported_ops", ["matmul", "matmul"]), ("supported_ops", ["eval"]),
    ("supported_ops", "matmul"), ("supported_ops", [True]),
    ("preferred_for", ["matmul", "matmul"]), ("preferred_for", ["softmax"]),
    ("supports_noise_model", 1), ("supports_calibration", "true"),
    ("max_error_budget", True), ("max_error_budget", -0.1),
    ("max_error_budget", 1000001), ("max_error_budget", "0"),
    ("memory_domain", "gpu_hbm"), ("memory_domain", "unknown"),
    ("supported_layouts", []), ("supported_layouts", ["blocked"]),
    ("produced_layouts", ["row_major", "row_major"]), ("produced_layouts", "row_major"),
    ("command", "private executable"), ("image", "arbitrary"),
    ("plugin", {"module": "os"}),
])
def test_invalid_capabilities_and_execution_hooks_reject(field, value):
    data = record()
    data["bindings"][0][field] = value
    with pytest.raises(BoundedBackendBindingsError, match="^backend_bindings_json_rejected$"):
        backend_bindings_from_json(json.dumps(data).encode())


@pytest.mark.parametrize("change", ["empty", "many", "duplicate", "same_target", "field", "schema"])
def test_envelope_and_ambiguous_portfolios_reject(change):
    data = record()
    if change == "empty":
        data["bindings"] = []
    elif change == "many":
        data["bindings"] *= 3
    elif change in {"duplicate", "same_target"}:
        second = copy.deepcopy(data["bindings"][0])
        if change == "same_target":
            second["name"] = "another_cpu"
        data["bindings"].append(second)
    elif change == "field":
        del data["bindings"][0]["max_error_budget"]
    else:
        data["schema_version"] = "future"
    with pytest.raises(BoundedBackendBindingsError):
        backend_bindings_from_json(json.dumps(data).encode())


@pytest.mark.parametrize("data", [
    b"{}", b"[]", b"null", b"\xff", b"\xef\xbb\xbf{}",
    b'{"schema_version":0,"schema_version":1,"bindings":[]}',
    b'{"schema_version":"\\ud800","bindings":[]}', b"[" * 9 + b"0" + b"]" * 9,
    b" " * (MAX_BACKEND_BINDINGS_JSON_BYTES + 1), b"NaN", b"1e999", b"1e-999",
    bytearray(b"{}"),
], ids=["object", "array", "null", "utf8", "bom", "duplicate", "surrogate", "depth",
        "bytes", "nan", "overflow", "underflow", "bytearray"])
def test_lexical_and_resource_controls(data):
    with pytest.raises(BoundedBackendBindingsError):
        backend_bindings_from_json(data)


def test_capability_budget_and_boolean_fields_roundtrip():
    binding = context()[1][0]
    binding = replace(binding, capability=replace(
        binding.capability, max_error_budget=0.25,
        supports_noise_model=True, supports_calibration=True,
    ))
    assert backend_bindings_from_json(backend_bindings_to_json((binding,))) == (binding,)


def test_serializer_does_not_dispatch_hostile_objects():
    class Hostile:
        def __getattribute__(self, name):
            pytest.fail("caller method dispatched")

        def __iter__(self):
            pytest.fail("caller iterator dispatched")

    for value in (Hostile(), (Hostile(),)):
        with pytest.raises(BoundedBackendBindingsError):
            backend_bindings_to_json(value)
