"""Independent arithmetic and inert checks; no installed/native CLI is executed."""

import ast
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_source import consumer
from tuc.compiler import bounded_cpu_source as source_api
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
    source_to_intent_research_kernel_ingress_report_to_dict,
)


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
               report["planned_source_conversions"], report["planned_negative_controls"])
    assert planned == (12, 56, 6, 10)
    assert report["case_runs"] == report["scalar_checks"] == 0
    assert len(report["programs"]) == 6
    assert len({program["source_sha256"] for program in report["programs"]}) == 6
    emitted = consumer.emit()
    directory = Path(emitted["fixture_directory"])
    assert directory.parent == tmp_path / "tmp"
    assert json.loads((directory / "fixtures.json").read_bytes()) == emitted
    for program in report["programs"]:
        source = (directory / program["id"] / "kernel.py").read_bytes()
        assert hashlib.sha256(source).hexdigest() == program["source_sha256"]
        assert source == consumer.source(program["family"], program["profile"])
        signature = (directory / program["id"] / "signature.json").read_bytes()
        assert hashlib.sha256(signature).hexdigest() == program["signature_sha256"]
        assert not (directory / program["id"] / "graph.json").exists()
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


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_literal_sources_and_signatures_describe_every_kernel_argument(family, profile):
    text = consumer.source(family, profile)
    signature = consumer.signature(family, profile)
    tree = ast.parse(text)
    assert len(tree.body) == 3
    assert isinstance(tree.body[0], ast.Import)
    assert [(item.name, item.asname) for item in tree.body[0].names] == [("triton", None)]
    assert [(item.name, item.asname) for item in tree.body[1].names] == [
        ("triton.language", "tl")]
    kernel = tree.body[2]
    assert isinstance(kernel, ast.FunctionDef)
    assert kernel.name == signature["kernel_name"] == signature["source_name"]
    assert isinstance(kernel.decorator_list[0], ast.Attribute)
    assert kernel.decorator_list[0].value.id == "triton"
    assert kernel.decorator_list[0].attr == "jit"
    inputs, outputs = consumer.public_bindings(consumer.graph(family, profile))
    expected = {item["public_name"]: item["shape"] for item in inputs + outputs}
    assert signature == {"schema_version": "tuc.bounded_cpu_source.v0",
                         "source_name": kernel.name, "kernel_name": kernel.name,
                         "tensor_shapes": expected}
    assert [argument.arg for argument in kernel.args.args] == list(expected)
    stores = [node for node in kernel.body if isinstance(node, ast.Expr)]
    assert [node.value.args[0].id for node in stores] == [
        item["public_name"] for item in outputs]
    assert [node.value.args[1].id for node in stores] == [
        item["tensor_name"] for item in outputs]


def test_negative_corpus_covers_source_signature_and_compiler_semantics_without_execution(tmp_path):
    cases = consumer.negative_cases(tmp_path / "forbidden-effect")
    assert len(cases) == len({case["id"] for case in cases}) == 10
    reasons = [case["reason"] for case in cases]
    assert reasons.count("source_rejected") == 7
    assert reasons.count("signature_rejected") == 2
    assert reasons.count("graph_rejected") == 1
    by_name = {case["id"]: case for case in cases}
    assert b"import os" in by_name["foreign_import"]["source"]
    assert b"eval(" in by_name["eval"]["source"]
    assert b"open(" in by_name["file_effect"]["source"]
    assert b"create_connection" in by_name["network_effect"]["source"]
    assert by_name["dimension_limit"]["signature"]["tensor_shapes"]["a"][0] == 65
    assert by_name["boolean_dimension"]["signature"]["tensor_shapes"]["a"][0] is True
    assert b"tl.softmax(" in by_name["softmax"]["source"]
    with pytest.raises(SyntaxError):
        ast.parse(by_name["syntax"]["source"])
    assert not (tmp_path / "forbidden-effect").exists()
    assert consumer.signature("fanout", 0)["tensor_shapes"]["a"] == [2, 3]


@pytest.mark.parametrize("case_id,expected_reason", (("softmax", "graph_rejected"),
                                                   ("nonterminal_return", "source_rejected")))
def test_fixed_negative_sources_use_real_parser_and_parent_classification(
        tmp_path, case_id, expected_reason):
    """Parse fixed test literals as data; the worker envelope/isolation is synthetic.

    Nonterminal returns fail SourceIntentModule construction inside the parser,
    whereas valid softmax Source Intent reaches the narrower CPU parent boundary.
    No caller source path, source execution, process or container is involved.
    """
    cases = {case["id"]: case for case in consumer.negative_cases(tmp_path / "unused-marker")}
    case = cases[case_id]
    signature = case["signature"]
    request = source_api.prepare_source_request(case["source"], consumer.encoded(signature))
    envelope = {"protocol": source_api.WORKER_PROTOCOL,
                "request_digest": json.loads(request)["request_digest"]}
    try:
        parsed = ingest_triton_module_source_to_source_intent(
            case["source"].decode("utf-8"), source_name=signature["source_name"],
            kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
    except ValueError:
        # The unchanged worker maps parser ValueError to this closed response.
        envelope.update(status="rejected", reason_code="source_rejected")
    else:
        envelope.update(
            status="accepted", security=dict(source_api._SECURITY),
            source_intent_payload=parsed.parser_result.source_intent_payload,
            ingress_report=source_to_intent_research_kernel_ingress_report_to_dict(parsed.report))
    with pytest.raises(source_api.BoundedCPUSourceError) as caught:
        source_api.decode_source_response(request, consumer.encoded(envelope))
    assert caught.value.reason == expected_reason
    assert case["reason"] == expected_reason


def test_mocked_negative_control_driver_requires_exact_source_free_rejection(monkeypatch, tmp_path):
    directory = tmp_path / "controls"
    directory.mkdir()
    workspace = directory / "workspace"
    workspace.mkdir()
    reasons = {case["id"]: case["reason"] for case in consumer.negative_cases(directory / "marker")}

    def fake_invoke(executable, arguments):
        name = Path(arguments[0]).stem.removeprefix("negative-")
        return 2, b"", f"tuc-source-to-json: {reasons[name]}\n".encode()

    monkeypatch.setattr(consumer, "_invoke", fake_invoke)
    results = consumer._negative_controls(Path("never-executed"), directory, workspace, {})
    assert len(results) == 10
    assert all(consumer._is_digest(item["source_sha256"]) and
               consumer._is_digest(item["signature_sha256"]) for item in results)


@pytest.mark.parametrize("response", ((1, b"", b"tuc-source-to-json: source_rejected\n"),
                                     (2, b"partial", b"tuc-source-to-json: source_rejected\n"),
                                     (2, b"", b"tuc-source-to-json: source_rejected /private\n")))
def test_mocked_control_failure_never_becomes_observation(monkeypatch, tmp_path, response):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(consumer, "_invoke", lambda *args: response)
    with pytest.raises(ValueError):
        consumer._negative_controls(Path("never-executed"), tmp_path, workspace, {})
    assert not (tmp_path / "record.json").exists()


def test_converted_graph_is_checked_independently_before_publication():
    expected = consumer.graph("fanout", 0)
    raw = consumer.encoded(expected)
    assert consumer._graph_result((0, raw, b""), expected) == raw
    changed = consumer.graph("fanout", 0)
    changed["operations"][2]["inputs"] = ["positive"]
    bool_shape = consumer.graph("fanout", 0)
    bool_shape["tensors"][0]["shape"][0] = True
    for result in ((1, raw, b""), (0, raw, b"warning"),
                   (0, consumer.encoded(changed), b""),
                   (0, consumer.encoded(bool_shape), b""),
                   (0, b'{"name":"duplicate",' + raw[1:], b""),
                   (0, b"x" * 65537, b"")):
        with pytest.raises(ValueError):
            consumer._graph_result(result, expected)


def test_small_projection_example_is_literal_data_with_independent_expected_result():
    root = Path(consumer.__file__).resolve().parent
    tree = ast.parse((root / "projection.py.txt").read_text())
    signature = json.loads((root / "projection-signature.json").read_bytes())
    inputs = json.loads((root / "projection-inputs.json").read_bytes())["inputs"]
    assert isinstance(tree.body[-1], ast.FunctionDef)
    assert tree.body[-1].name == signature["kernel_name"]
    assert signature["tensor_shapes"] == {"x": [2, 2], "weights": [2, 1], "scores": [2, 1]}
    projection = _numpy_matmul(inputs["x"], inputs["weights"], 2, 2, 1)
    np.testing.assert_array_equal(np.maximum(projection, np.float32(0)).ravel(), [0.0, 10.0])
