"""Independent arithmetic and inert checks; no installed/native CLI is executed."""

import ast
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_json import consumer


def _numpy_matmul(left, right, rows, inner, columns):
    left = np.asarray(left, dtype=np.float32).reshape(rows, inner)
    right = np.asarray(right, dtype=np.float32).reshape(inner, columns)
    result = np.zeros((rows, columns), dtype=np.float32)
    for index in range(inner):
        product = np.multiply(left[:, index, None], right[index, None, :], dtype=np.float32)
        result = np.add(result, product, dtype=np.float32)
    return result


def _numpy_sums(values):
    result = np.zeros(values.shape[0], dtype=np.float32)
    for column in range(values.shape[1]):
        result = np.add(result, values[:, column], dtype=np.float32)
    return result


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(2))
def test_explicit_family_oracle_matches_independent_numpy_fp32(family, profile, case):
    envelope = consumer.input_envelope(family, profile, case)
    data = envelope["inputs"]
    actual = consumer.reference(family, profile, envelope)
    m, k, n = consumer.PROFILES[profile]
    if family == "fanout":
        projection = _numpy_matmul(data["a"], data["b"], m, k, n)
        expected = {"z_positive": np.maximum(projection, np.float32(0)).ravel(),
                    "a_rows": _numpy_sums(projection)}
    elif family == "truefanin":
        left = _numpy_matmul(data["a"], data["b"], m, k, n)
        right = _numpy_matmul(data["c"], data["d"], n, k, m)
        joined = _numpy_matmul(left.ravel(), right.ravel(), m, n, m)
        expected = {"joined_rows": _numpy_sums(joined)}
    else:
        source = np.asarray(data["x"], dtype=np.float32).reshape(m, n)
        expected = {"positive_rows": _numpy_sums(np.maximum(source, np.float32(0)))}
    assert list(actual) == list(expected)
    for name, values in expected.items():
        np.testing.assert_array_equal(actual[name], values)


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_corpus_inputs_outputs_and_shape_profiles_are_distinct(family, profile):
    envelopes = [consumer.input_envelope(family, profile, case) for case in range(2)]
    assert envelopes[0] != envelopes[1]
    assert consumer.reference(family, profile, envelopes[0]) != consumer.reference(
        family, profile, envelopes[1])
    for case, envelope in enumerate(envelopes):
        assert envelope["schema_version"] == "tuc.bounded_cpu_inputs.v0"
        bindings, _ = consumer.public_bindings(consumer.graph(family, profile))
        assert list(envelope["inputs"]) == [item["public_name"] for item in bindings]
        for item in bindings:
            values = envelope["inputs"][item["public_name"]]
            assert len(values) == math.prod(item["shape"])
            assert all(type(value) is float and math.isfinite(value) for value in values)
        if case == 1:
            assert any(value * 8 != round(value * 8)
                       for values in envelope["inputs"].values() for value in values)


@pytest.mark.parametrize("profile", range(2))
def test_graphs_have_true_fanin_complete_terminal_returns_and_rank1_reduction(profile):
    for family in consumer.FAMILIES:
        source = consumer.graph(family, profile)
        produced = {name for op in source["operations"] for name in op["outputs"]}
        consumed = {name for op in source["operations"] for name in op["inputs"]}
        assert {item["tensor_name"] for item in source["returns"]} == produced - consumed
        assert source["schema_version"] == "source_intent.v0"
        assert all(tensor["dtype"] == "float32" for tensor in source["tensors"])
        if family == "truefanin":
            first, second, joined, reduction = source["operations"]
            assert first["family"] == second["family"] == joined["family"] == "matmul"
            assert joined["inputs"] == first["outputs"] + second["outputs"]
            assert reduction["inputs"] == joined["outputs"]
        elif family == "fanout":
            assert [item["public_name"] for item in source["returns"]] == [
                "z_positive", "a_rows"]
        else:
            _, outputs = consumer.public_bindings(source)
            assert len(outputs) == 1 and len(outputs[0]["shape"]) == 1


def test_candidate_and_emit_are_standalone_inert_and_preserve_fixture_bytes(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure consumer invoked a process")

    monkeypatch.setattr(consumer.subprocess, "Popen", forbidden)
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    report = consumer.candidate()
    assert report == consumer.candidate()
    assert report["native_execution_observed"] is False
    planned = (report["planned_case_runs"], report["planned_scalar_checks"],
               report["planned_numeric_rejections"], report["planned_negative_controls"])
    assert planned == (12, 56, 1, 6)
    assert report["case_runs"] == report["scalar_checks"] == 0
    assert len(report["programs"]) == 6
    assert len({program["source_sha256"] for program in report["programs"]}) == 6
    emitted = consumer.emit()
    directory = Path(emitted["fixture_directory"])
    assert directory.parent == tmp_path / "tmp"
    assert json.loads((directory / "fixtures.json").read_bytes()) == emitted
    for program in report["programs"]:
        source = (directory / program["id"] / "graph.json").read_bytes()
        assert hashlib.sha256(source).hexdigest() == program["source_sha256"]
        assert json.loads(source) == consumer.graph(program["family"], program["profile"])
        for case in program["cases"]:
            raw = (directory / program["id"] / f"inputs-{case['case']}.json").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == case["input_sha256"]
    assert not (tmp_path / "record.json").exists()


def test_no_tuc_numpy_repository_or_dynamic_imports_in_standalone_client():
    tree = ast.parse(Path(consumer.__file__).read_text(encoding="utf-8"))
    allowed = {"__future__", "argparse", "hashlib", "json", "math", "os", "re", "selectors",
               "signal", "stat", "struct", "subprocess", "sys", "tempfile", "time",
               "contextlib", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module in allowed
        elif isinstance(node, ast.Import):
            assert all(alias.name in allowed for alias in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "__import__"}


def test_public_binding_order_and_indices_are_independently_determined():
    inputs, outputs = consumer.public_bindings(consumer.graph("truefanin", 0))
    assert [(item["public_name"], item["tensor_index"]) for item in inputs] == [
        ("a", 0), ("b", 1), ("c", 3), ("d", 4)]
    assert outputs == [{"public_name": "joined_rows", "tensor_name": "rows",
                        "tensor_index": 7, "shape": [2], "dtype": "float32"}]


def test_request_identity_uses_original_named_input_order_and_binary32_bytes():
    bindings, _ = consumer.public_bindings(consumer.graph("fanout", 0))
    data = consumer.input_envelope("fanout", 0, 0)
    payload = struct.pack("<12f", *data["inputs"]["a"], *data["inputs"]["b"])
    expected = hashlib.sha256(bytes.fromhex("a" * 64) + payload).hexdigest()
    assert consumer._request_digest("a" * 64, bindings, data) == expected
    changed = consumer.input_envelope("fanout", 0, 1)
    assert consumer._request_digest("a" * 64, bindings, changed) != expected
    assert consumer._request_digest("b" * 64, bindings, data) != expected


def _synthetic_success():
    return {"schema_version": consumer.CLI_SCHEMA, "action": "run", "program_digest": "a" * 64,
            "request_digest": "b" * 64, "outputs": {"positive_rows": [1.0, 2.0]},
            "native_execution_observed": True}


@pytest.mark.parametrize("field,value", (("program_digest", "x" * 64),
                                        ("request_digest", "B" * 64),
                                        ("native_execution_observed", 1),
                                        ("action", "inspect"),
                                        ("schema_version", "other")))
def test_synthetic_cli_response_header_corruptions_reject(field, value):
    response = _synthetic_success()
    response[field] = value
    with pytest.raises(ValueError):
        consumer._success((0, consumer.encoded(response), b""), "run")


def test_synthetic_cli_success_requires_zero_status_empty_stderr_and_no_duplicate_keys():
    raw = consumer.encoded(_synthetic_success())
    assert consumer._success((0, raw, b""), "run") == _synthetic_success()
    for result in ((1, raw, b""), (0, raw, b"warning"),
                   (0, b'{"action":"run",' + raw[1:], b"")):
        with pytest.raises(ValueError):
            consumer._success(result, "run")


@pytest.mark.parametrize("actual", ({"a": [True]}, {"a": [1]}, {"a": [1.01]},
                                   {"a": [float("nan")]}, {"a": [float("inf")]},
                                   {"a": [1.0, 0.0]}, {"b": [1.0]}, {"a": (1.0,)}))
def test_output_comparison_rejects_wrong_values_types_extents_or_bindings(actual):
    with pytest.raises(ValueError):
        consumer._check_outputs(actual, {"a": [1.0]})


def test_negative_controls_require_exact_source_free_stderr_and_empty_stdout(monkeypatch):
    monkeypatch.setattr(consumer, "_invoke", lambda *args: (
        1, b"", b"tuc-cpu-app: numeric_rejection\n"))
    consumer._rejected(Path("never-executed"), (), "numeric_rejection", 1)
    for result in ((2, b"", b"tuc-cpu-app: numeric_rejection\n"),
                   (1, b"partial result", b"tuc-cpu-app: numeric_rejection\n"),
                   (1, b"", b"tuc-cpu-app: numeric_rejection /private/path\n")):
        monkeypatch.setattr(consumer, "_invoke", lambda *args, current=result: current)
        with pytest.raises(ValueError):
            consumer._rejected(Path("never-executed"), (), "numeric_rejection", 1)


def test_original_file_and_workspace_checks_reject_drift(tmp_path):
    source = tmp_path / "graph.json"
    source.write_bytes(b"original")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    snapshot = {source: b"original"}
    consumer._unchanged(snapshot, workspace)
    source.write_bytes(b"changed")
    with pytest.raises(ValueError):
        consumer._unchanged(snapshot, workspace)
    source.write_bytes(b"original")
    (workspace / "leftover").write_bytes(b"resource")
    with pytest.raises(ValueError):
        consumer._unchanged(snapshot, workspace)
