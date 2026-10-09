"""CPU admission and response binding; synthetic fixtures are not execution evidence."""

import ast
import json
import struct
from hashlib import sha256
from pathlib import Path

import pytest

from integration.bounded_model_application.consumer import _model
from integration.bounded_model_artifact_bundle.consumer import _OPS, _binding
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler import bounded_model_application as api
from tuc.compiler.bounded_model_artifact_bundle import create_bounded_model_artifact_bundle
from tuc.compiler.bounded_model_artifact_request import create_bounded_model_artifact_request
from tuc.ir.model import OperationKind


def context(weight=2.0, values=(1.0, -0.0, 3.0, 4.0)):
    model = _model(weight)
    bindings = (_binding("cpu", DAGTarget.C11, _OPS),)
    bundle = create_bounded_model_artifact_bundle(model, bindings)
    inputs = json.dumps(
        {"schema_version": "tuc.bounded_cpu_inputs.v0", "inputs": {"x": values}}
    ).encode()
    request = create_bounded_model_artifact_request(model, bindings, bundle, inputs)
    return model, bindings, bundle, inputs, request


def response(prepared, values=(0.0, -0.0, 2.0, 3.0), status=0):
    return (
        b"TUCOUT01"
        + prepared.request_frame[8:72]
        + struct.pack("<I", status)
        + (struct.pack("<4f", *values) if status == 0 else b"")
    )


def test_admission_preserves_bits_and_protocol_output_identity():
    ctx = context()
    prepared = api.prepare_bounded_model_application(*ctx)
    assert prepared == api.prepare_bounded_model_application(*ctx)
    assert prepared.request_frame[:8] == b"TUCIN001"
    assert prepared.request_frame[72:] == bytes.fromhex(
        "0000803f00000080000040400000804000000040000080bf0000803f00004040"
    )
    answer = response(prepared)
    result = api.decode_bounded_model_application_response(*ctx, answer, 0)
    assert result == api.validate_bounded_model_application_result(
        *ctx, answer, 0, result.receipt_data
    )
    receipt = json.loads(result.receipt_data)
    assert receipt["request_digest"] == prepared.request_digest
    assert receipt["bundle_digest"] == prepared.bundle_digest
    assert receipt["program_digest"] == prepared.application.program_digest
    assert receipt["protocol_request_digest"] == prepared.request_frame[40:72].hex()
    assert receipt["response_sha256"] == sha256(answer).hexdigest()
    assert receipt["protocol_validated"] is True
    assert receipt["native_execution_observed"] is False
    assert result.outputs[0].public_name == "scores"
    assert result.outputs[0].shape == (2, 2)
    assert result.outputs[0].value_bits == "00000000000000800000004000004040"


@pytest.mark.parametrize("changed", [context(4.0), context(values=(5.0, 6.0, 7.0, 8.0))])
def test_data_changes_context_and_rejects_response_replay(changed):
    original = context()
    a = api.prepare_bounded_model_application(*original)
    b = api.prepare_bounded_model_application(*changed)
    assert a.application.program_digest == b.application.program_digest
    assert a.request_digest != b.request_digest
    assert a.request_frame[40:72] != b.request_frame[40:72]
    with pytest.raises(api.BoundedModelApplicationError):
        api.decode_bounded_model_application_response(*changed, response(a), 0)


@pytest.mark.parametrize("position", [0, 2, 3, 4])
def test_original_context_substitution_rejects(position):
    ctx = list(context())
    alternative = context(4.0, (5.0, 6.0, 7.0, 8.0))
    ctx[position] = alternative[position]
    with pytest.raises(api.BoundedModelApplicationError, match="^model_application_rejected$"):
        api.prepare_bounded_model_application(*ctx)


@pytest.mark.parametrize("mixed", [False, True])
def test_cuda_and_mixed_plans_reject_without_fallback(mixed):
    model, cpu, _, inputs, _ = context()
    cuda = (
        _binding(
            "cuda",
            DAGTarget.CUDA_SM86,
            frozenset({OperationKind.MATMUL}) if mixed else _OPS,
            frozenset({OperationKind.MATMUL}) if mixed else frozenset(),
        ),
    )
    bindings = (*cpu, *cuda) if mixed else cuda
    bundle = create_bounded_model_artifact_bundle(model, bindings)
    request = create_bounded_model_artifact_request(model, bindings, bundle, inputs)
    with pytest.raises(api.BoundedModelApplicationError):
        api.prepare_bounded_model_application(model, bindings, bundle, inputs, request)


@pytest.mark.parametrize(
    "mode",
    [
        "magic",
        "program",
        "digest",
        "short",
        "long",
        "type",
        "nan",
        "subnormal",
        "status",
        "exit",
        "bool_exit",
    ],
)
def test_malformed_or_failed_responses_reject(mode):
    ctx = context()
    prepared = api.prepare_bounded_model_application(*ctx)
    data = response(prepared)
    code = 0
    if mode in ("magic", "program", "digest"):
        offset = {"magic": 0, "program": 8, "digest": 40}[mode]
        data = data[:offset] + bytes([data[offset] ^ 1]) + data[offset + 1 :]
    elif mode == "short":
        data = data[:-1]
    elif mode == "long":
        data += b"x"
    elif mode == "type":
        data = bytearray(data)
    elif mode in ("nan", "subnormal"):
        data = data[:76] + struct.pack("<I", 0x7FC00000 if mode == "nan" else 1) + data[80:]
    elif mode == "status":
        data = response(prepared, status=9)
    elif mode == "exit":
        code = 2
    else:
        code = False
    with pytest.raises(api.BoundedModelApplicationError):
        api.decode_bounded_model_application_response(*ctx, data, code)


@pytest.mark.parametrize("status", [1, 2, 3])
def test_checked_native_errors_produce_no_result(status):
    ctx = context()
    prepared = api.prepare_bounded_model_application(*ctx)
    with pytest.raises(api.BoundedModelApplicationError):
        api.decode_bounded_model_application_response(*ctx, response(prepared, status=status), 1)


@pytest.mark.parametrize(
    "mode", ["digest", "rehashed_output", "claim", "noncanonical", "oversized", "type"]
)
def test_receipt_validation_recomputes_originals(mode):
    ctx = context()
    answer = response(api.prepare_bounded_model_application(*ctx))
    receipt = api.decode_bounded_model_application_response(*ctx, answer, 0).receipt_data
    root = json.loads(receipt)
    if mode == "digest":
        root["result_digest"] = "0" * 64
    elif mode in ("rehashed_output", "claim"):
        if mode == "claim":
            root["native_execution_observed"] = True
        else:
            root["outputs"][0]["value_bits"] = "00000000" * 4
        root.pop("result_digest")
        root["result_digest"] = sha256(api._json(root)).hexdigest()
    if mode in ("digest", "rehashed_output", "claim"):
        receipt = api._json(root)
    elif mode == "noncanonical":
        receipt = b" " + receipt
    elif mode == "oversized":
        receipt = b" " * (1024 * 1024 + 1)
    elif mode == "type":
        receipt = bytearray(receipt)
    with pytest.raises(api.BoundedModelApplicationError):
        api.validate_bounded_model_application_result(*ctx, answer, 0, receipt)


def test_module_has_no_native_or_io_surface():
    tree = ast.parse(Path(api.__file__).read_text(encoding="utf-8"))
    modules = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert modules.isdisjoint({"os", "pathlib", "subprocess", "socket", "ctypes", "importlib"})
    imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(name and name.startswith("tuc.runtime") for name in imports)
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert calls.isdisjoint({"open", "exec", "eval", "compile"})
