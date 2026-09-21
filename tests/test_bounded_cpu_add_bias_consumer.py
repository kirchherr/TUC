"""Independent Add/Bias client checks; no console, container or native execution."""

import ast
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_add_bias import consumer
from tuc.compiler import bounded_cpu_source as source_api
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
)


def matmul(left, right, rows, inner, columns):
    lhs = np.asarray(left, dtype=np.float32).reshape(rows, inner)
    rhs = np.asarray(right, dtype=np.float32).reshape(inner, columns)
    result = np.zeros((rows, columns), dtype=np.float32)
    for index in range(inner):
        result = np.add(result, np.multiply(lhs[:, index, None], rhs[index, None, :],
                                            dtype=np.float32), dtype=np.float32)
    return result


def numpy_reference(family, profile, data):
    values = data["inputs"]
    m, k, n = consumer.PROFILES[profile]
    if family == "affine":
        projected = matmul(values["x"], values["w"], m, k, n)
        return {"scores": np.add(projected, np.asarray(values["bias"], dtype=np.float32),
                                  dtype=np.float32).ravel()}
    if family == "mlp":
        h = (4, 3)[profile]
        first = matmul(values["x"], values["w1"], m, k, h)
        hidden = np.maximum(np.add(first, np.asarray(values["b1"], dtype=np.float32),
                                    dtype=np.float32), np.float32(0))
        final = matmul(hidden.ravel(), values["w2"], m, h, n)
        return {"scores": np.add(final, np.asarray(values["b2"], dtype=np.float32),
                                  dtype=np.float32).ravel()}
    if family == "residual":
        positive = np.maximum(np.asarray(values["x"], dtype=np.float32), np.float32(0))
        return {"residual": np.add(positive, np.asarray(values["skip"], dtype=np.float32),
                                    dtype=np.float32)}
    values = np.asarray(values["x"], dtype=np.float32)
    return {"doubled": np.add(values, values, dtype=np.float32)}


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(2))
def test_scalar_oracle_matches_independent_numpy_fp32(family, profile, case):
    data = consumer.input_envelope(family, profile, case)
    expected = numpy_reference(family, profile, data)
    actual = consumer.reference(family, profile, data)
    assert list(actual) == list(expected)
    for name in expected:
        np.testing.assert_array_equal(actual[name], expected[name])


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_changed_inputs_change_results_and_cover_nondyadic_values(family, profile):
    first = consumer.input_envelope(family, profile, 0)
    second = consumer.input_envelope(family, profile, 1)
    assert first != second
    assert consumer.reference(family, profile, first) != consumer.reference(family, profile, second)
    assert any(value * 8 != round(value * 8)
               for values in second["inputs"].values() for value in values)


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_source_signature_and_independent_graph_declarations_match(family, profile):
    source = consumer.source(family, profile)
    tree = ast.parse(source)
    signature = consumer.signature(family, profile)
    graph = consumer.graph(family, profile)
    assert len(tree.body) == 3
    assert [(item.name, item.asname) for item in tree.body[0].names] == [("triton", None)]
    assert [(item.name, item.asname) for item in tree.body[1].names] == [
        ("triton.language", "tl")]
    kernel = tree.body[2]
    assert kernel.name == signature["kernel_name"] == signature["source_name"] == graph["name"]
    inputs, outputs = consumer.public_bindings(graph)
    expected_shapes = {item["public_name"]: item["shape"] for item in inputs + outputs}
    assert signature["tensor_shapes"] == expected_shapes
    assert [argument.arg for argument in kernel.args.args] == list(expected_shapes)
    assignments = [node for node in kernel.body if isinstance(node, ast.Assign)]
    assert [node.targets[0].id for node in assignments] == [
        op["name"] for op in graph["operations"]]
    for node, operation in zip(assignments, graph["operations"], strict=True):
        if operation.get("attributes", {}).get("elementwise_kind") == "add":
            assert isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add)
            assert isinstance(node.value.left, ast.Name) and isinstance(node.value.right, ast.Name)
            assert [node.value.left.id, node.value.right.id] == operation["inputs"]
    produced = {name for op in graph["operations"] for name in op["outputs"]}
    consumed = {name for op in graph["operations"] for name in op["inputs"]}
    assert produced - consumed == {item["tensor_name"] for item in graph["returns"]}
    assert set(expected_shapes).isdisjoint(produced)
    assert len(graph["operations"]) <= 8 and len(graph["tensors"]) <= 24


def test_corpus_covers_bias_ranks_duplicate_inputs_and_five_operation_mlp():
    assert len(consumer.graph("mlp", 0)["operations"]) == 5
    for profile, rank in ((0, 1), (1, 2)):
        for family in ("double", "residual"):
            inputs, _ = consumer.public_bindings(consumer.graph(family, profile))
            assert all(len(item["shape"]) == rank for item in inputs)
        doubled = consumer.graph("double", profile)
        assert doubled["operations"][0]["inputs"] == ["x", "x"]
        inputs, _ = consumer.public_bindings(doubled)
        assert len(inputs) == 1
        affine = consumer.graph("affine", profile)
        shapes = {tensor["name"]: tensor["shape"] for tensor in affine["tensors"]}
        assert shapes["p"][1] == shapes["bias"][0] and len(shapes["bias"]) == 1


def test_default_and_emit_are_inert_and_hash_exact_original_fixtures(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("inert consumer started a process")

    monkeypatch.setattr(consumer.subprocess, "Popen", forbidden)
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    report = consumer.candidate()
    assert report == consumer.candidate()
    assert report["native_execution_observed"] is False
    assert len(report["programs"]) == 8
    assert (report["planned_source_conversions"], report["planned_case_runs"],
            report["planned_scalar_checks"], report["planned_negative_controls"],
            report["planned_numeric_rejections"]) == (8, 16, 86, 8, 2)
    emitted = consumer.emit()
    folder = Path(emitted["fixture_directory"])
    assert folder.parent == tmp_path / "tmp"
    assert json.loads((folder / "fixtures.json").read_bytes()) == emitted
    for program in report["programs"]:
        base = folder / program["id"]
        for name, field in (("kernel.py", "source_sha256"), ("signature.json", "signature_sha256")):
            assert hashlib.sha256((base / name).read_bytes()).hexdigest() == program[field]
        assert not (base / "graph.json").exists()
        for case in program["cases"]:
            raw = (base / f"inputs-{case['case']}.json").read_bytes()
            assert hashlib.sha256(raw).hexdigest() == case["input_sha256"]


def test_standalone_client_imports_only_standard_library():
    tree = ast.parse(Path(consumer.__file__).read_text(encoding="utf-8"))
    allowed = {"__future__", "argparse", "hashlib", "json", "math", "os", "re", "selectors",
               "signal", "stat", "struct", "subprocess", "sys", "tempfile", "time",
               "contextlib", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module in allowed
        elif isinstance(node, ast.Import):
            assert all(item.name in allowed for item in node.names)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "compile", "__import__"}


def test_numeric_controls_use_normal_inputs_and_fail_only_at_addition():
    cases = consumer.numeric_cases()
    assert [case["id"] for case in cases] == ["addition_overflow", "addition_subnormal"]
    for case in cases:
        for values in case["inputs"].values():
            for value in values:
                assert type(value) is float and math.isfinite(value)
                assert consumer.f32(value) == value
    with np.errstate(over="ignore", under="ignore"):
        overflow = numpy_reference("residual", 0, cases[0])["residual"]
        subnormal = numpy_reference("residual", 0, cases[1])["residual"]
    assert np.isposinf(overflow[0])
    assert subnormal[0].view(np.uint32) == 0x80000001
    assert np.all(overflow[1:] == 0) and np.all(subnormal[1:] == 0)


def test_negative_corpus_has_closed_shape_and_syntax_cases():
    cases = consumer.negative_cases()
    assert len(cases) == len({case["id"] for case in cases}) == 8
    assert [case["reason"] for case in cases].count("source_rejected") == 7
    assert [case["reason"] for case in cases].count("signature_rejected") == 1
    by_id = {case["id"]: case for case in cases}
    assert b"x + 1.0" in by_id["scalar"]["source"]
    assert b"(x + rhs) + rhs" in by_id["nested"]["source"]
    assert b"x - rhs" in by_id["subtract"]["source"]
    assert by_id["column_broadcast"]["signature"]["tensor_shapes"]["rhs"] == [2, 1]
    assert by_id["lhs_vector"]["signature"]["tensor_shapes"]["x"] == [3]
    assert by_id["rank3"]["signature"]["tensor_shapes"]["x"] == [1, 2, 3]


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_fixed_literal_sources_match_real_parser_graphs(family, profile):
    """Parse only the owned test literals as data; no worker/isolation claim."""
    signature = consumer.signature(family, profile)
    parsed = ingest_triton_module_source_to_source_intent(
        consumer.source(family, profile).decode("ascii"),
        source_name=signature["source_name"], kernel_name=signature["kernel_name"],
        tensor_shapes=signature["tensor_shapes"])
    assert parsed.parser_result.source_intent_payload == consumer.graph(family, profile)


@pytest.mark.parametrize("case_id", ("scalar", "nested", "subtract", "shape_mismatch",
                                    "column_broadcast", "lhs_vector", "bias_length", "rank3"))
def test_fixed_negative_fixtures_have_real_parser_or_signature_rejections(case_id):
    """Check actual classification rather than echoing a mock's expected reason."""
    case = next(case for case in consumer.negative_cases() if case["id"] == case_id)
    signature = case["signature"]
    if case_id == "rank3":
        with pytest.raises(source_api.BoundedCPUSourceError) as caught:
            source_api.prepare_source_request(case["source"], consumer.encoded(signature))
        assert caught.value.reason == "signature_rejected"
        assert case["reason"] == "signature_rejected"
    else:
        source_api.prepare_source_request(case["source"], consumer.encoded(signature))
        # The unchanged worker closes parser ValueError as source_rejected.
        with pytest.raises(ValueError):
            ingest_triton_module_source_to_source_intent(
                case["source"].decode("ascii"), source_name=signature["source_name"],
                kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
        assert case["reason"] == "source_rejected"


@pytest.mark.parametrize("wrong", ((0, b"partial", b""),
                                  (1, b"", b"tuc-cpu-app: protocol_rejection\n"),
                                  (1, b"data", b"tuc-cpu-app: numeric_rejection\n")))
def test_numeric_control_driver_rejects_wrong_status_or_partial_publication(monkeypatch, tmp_path,
                                                                         wrong):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    program = next(item for item in consumer.candidate()["programs"] if item["id"] == "residual_0")
    program["program_digest"] = "a" * 64
    monkeypatch.setattr(consumer, "_invoke", lambda *args: wrong)
    with pytest.raises(ValueError, match="addition_overflow"):
        consumer._numeric_controls(Path("never-executed"), tmp_path, workspace, {}, program)
    assert not (tmp_path / "record.json").exists()


def test_small_mlp_example_has_independently_computed_scores():
    root = Path(consumer.__file__).resolve().parent
    source = ast.parse((root / "mlp.py.txt").read_text())
    signature = json.loads((root / "mlp-signature.json").read_bytes())
    data = json.loads((root / "mlp-inputs.json").read_bytes())["inputs"]
    assert source.body[-1].name == signature["kernel_name"]
    first = matmul(data["x"], data["w1"], 2, 2, 2)
    hidden = np.maximum(np.add(first, np.asarray(data["b1"], dtype=np.float32),
                                dtype=np.float32), np.float32(0))
    final = matmul(hidden.ravel(), data["w2"], 2, 2, 1)
    scores = np.add(final, np.asarray(data["b2"], dtype=np.float32), dtype=np.float32)
    np.testing.assert_array_equal(scores.ravel(), [1.5, 23.5])
