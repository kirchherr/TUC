"""Native harness/audit contracts using synthetic responses, never execution evidence."""

import json
import struct

import numpy as np
import pytest

from integration.bounded_model_application import audit_native_receipt as audit
from integration.bounded_model_application import native_consumer as client
from tuc.compiler.bounded_model_application import (
    decode_bounded_model_application_response,
    prepare_bounded_model_application,
)
from tuc.runtime import bounded_model_application as runtime
from tuc.runtime.bounded_c11_application import BoundedC11ApplicationRuntimeError


@pytest.fixture
def synthetic_record(tmp_path, monkeypatch):
    def fake_run(model, capabilities, bundle, inputs, request, *, workspace):
        prepared = prepare_bounded_model_application(model, capabilities, bundle, inputs, request)
        values = dict(prepared.input_values)
        if max(abs(v) for v in values["x"]) > 1e30:
            raise BoundedC11ApplicationRuntimeError("numeric_rejection")
        x = np.array(values["x"], dtype=np.float32).reshape(2, 2)
        w = np.array(values["w"], dtype=np.float32).reshape(2, 2)
        raw = x @ w
        scores = np.maximum(raw, np.float32(0.0))
        rows = raw.sum(axis=1, dtype=np.float32)
        payload = b"".join(
            struct.pack("<f", float(v)) for array in (rows, scores) for v in array.flat
        )
        response = b"TUCOUT01" + prepared.request_frame[8:72] + struct.pack("<I", 0) + payload
        return decode_bounded_model_application_response(
            model, capabilities, bundle, inputs, request, response, 0
        )

    monkeypatch.setattr(runtime, "run_bounded_model_application", fake_run)
    client.run(tmp_path)
    return (tmp_path / "record.json").read_bytes()


def test_independent_equations_and_identity_audit(synthetic_record):
    report = audit.audit(synthetic_record)
    assert report["status"] == "PASS"
    assert report["scalar_checks"] == 18
    assert report["model_checks"] == report["request_checks"] == report["response_checks"] == 3
    assert report["rejection_checks"] == 4
    assert report["tuc_imported"] is False
    assert report["native_execution_performed"] is False


@pytest.mark.parametrize(
    "mode", ["output", "response", "request", "model", "claim", "count", "extra", "rejection"]
)
def test_tampering_rejects_even_with_new_result_hash(synthetic_record, mode):
    record = json.loads(synthetic_record)
    request, receipt = record["cases"][0]["request"], record["cases"][0]["receipt"]
    if mode == "output":
        receipt["outputs"][0]["value_bits"] = "00000000" * 4
    elif mode == "response":
        receipt["response_sha256"] = "0" * 64
    elif mode == "request":
        request["inputs"][0]["value_bits"] = "00000000" * 4
        request["request_digest"] = audit.digest(
            {k: v for k, v in request.items() if k != "request_digest"}
        )
        receipt["request_digest"] = request["request_digest"]
    elif mode == "model":
        request["model_digest"] = receipt["model_digest"] = "0" * 64
    elif mode == "claim":
        receipt["native_execution_observed"] = True
    elif mode == "count":
        record["successful_runs"] = True
    elif mode == "extra":
        receipt["source"] = "unexpected"
    else:
        record["rejections"].pop()
    receipt["result_digest"] = audit.digest(
        {k: v for k, v in receipt.items() if k != "result_digest"}
    )
    with pytest.raises(ValueError, match="^native_record_rejected$"):
        audit.audit(audit.encoded(record))


@pytest.mark.parametrize(
    "data",
    [
        b"{}",
        b"[]",
        b"NaN",
        b"\xff",
        b'{"x":1,"x":2}',
        b"[" * 20 + b"]" * 20,
        b" " * (audit.MAX_BYTES + 1),
    ],
    ids=["object", "array", "constant", "encoding", "duplicate", "nesting", "size"],
)
def test_malformed_and_oversized_audit_input_rejects(data):
    with pytest.raises(ValueError, match="^native_record_rejected$"):
        audit.audit(data)


def test_candidate_never_imports_runtime(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError("candidate executed runtime")

    monkeypatch.setattr(runtime, "run_bounded_model_application", reject)
    assert client.candidate()["native_execution_observed"] is False


def test_audit_has_no_tuc_or_consumer_import():
    import ast
    from pathlib import Path

    tree = ast.parse(Path(audit.__file__).read_text(encoding="utf-8"))
    imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
    assert not any(
        name and (name.startswith("tuc") or "native_consumer" in name) for name in imported
    )


def test_retained_original_native_observation_is_auditable():
    import hashlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    receipt = json.loads(
        (root / "integration/bounded_model_application/observed-ci-59ad813.json").read_bytes()
    )
    assert receipt["source_commit"] == "59ad8139813ac5eb7b891907b3d74ebb06059a67"
    report = audit.audit(audit.encoded(receipt["integration"]))
    assert report == receipt["audit"]
    for field, name in (
        ("consumer_sha256", "native_consumer.py"),
        ("audit_sha256", "audit_native_receipt.py"),
    ):
        source = (
            (root / "integration/bounded_model_application" / name)
            .read_bytes()
            .replace(b"\r\n", b"\n")
        )
        assert hashlib.sha256(source).hexdigest() == receipt[field]
