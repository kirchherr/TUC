"""Independent installed Linear client checks; no native or console execution."""

import ast
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_linear import consumer
from tuc.compiler import bounded_cpu_source as source_api
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
)


def matmul(left, right, rows, inner, columns, *, transposed=False):
    lhs = np.asarray(left, dtype=np.float32).reshape(rows, inner)
    if transposed:
        rhs = np.asarray(right, dtype=np.float32).reshape(columns, inner).T
    else:
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
        projected = matmul(values["x"], values["weight"], m, k, n, transposed=True)
        return np.add(projected, np.asarray(values["bias"], dtype=np.float32),
                      dtype=np.float32).ravel()
    h = (5, 3)[profile]
    if family == "mlp":
        first = matmul(values["x"], values["w1"], m, k, h, transposed=True)
        biased = np.add(first, np.asarray(values["b1"], dtype=np.float32), dtype=np.float32)
        hidden = np.where(biased < np.float32(0), np.float32(0), biased)
        final = matmul(hidden.ravel(), values["w2"], m, h, n, transposed=True)
        return np.add(final, np.asarray(values["b2"], dtype=np.float32), dtype=np.float32).ravel()
    first = matmul(values["x"], values["normal_weight"], m, k, h)
    return matmul(first.ravel(), values["linear_weight"], m, h, n, transposed=True).ravel()


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(2))
def test_ordered_scalar_oracle_matches_independent_numpy_bits(family, profile, case):
    data = consumer.input_envelope(family, profile, case)
    expected = numpy_reference(family, profile, data)
    actual = np.asarray(consumer.reference(family, profile, data)["scores"], dtype=np.float32)
    np.testing.assert_array_equal(actual.view(np.uint32), expected.view(np.uint32))


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_changing_nondyadic_inputs_change_results(family, profile):
    first = consumer.input_envelope(family, profile, 0)
    second = consumer.input_envelope(family, profile, 1)
    assert first != second
    assert consumer.reference(family, profile, first) != consumer.reference(family, profile, second)
    assert any(value * 8 != round(value * 8)
               for values in second["inputs"].values() for value in values)


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_literal_source_and_signature_define_physical_weight_shapes(family, profile):
    tree = ast.parse(consumer.source(family, profile))
    signature = consumer.signature(family, profile)
    graph = consumer.graph(family, profile)
    assert len(tree.body) == 3
    kernel = tree.body[-1]
    assert kernel.name == signature["kernel_name"] == signature["source_name"] == graph["name"]
    inputs, outputs = consumer.public_bindings(graph)
    assert signature["tensor_shapes"] == {
        item["public_name"]: item["shape"] for item in inputs + outputs}
    assert [argument.arg for argument in kernel.args.args] == list(signature["tensor_shapes"])
    shapes = {item["name"]: item["shape"] for item in graph["tensors"]}
    assignments = [node for node in kernel.body if isinstance(node, ast.Assign)]
    for node, operation in zip(assignments, graph["operations"], strict=True):
        assert node.targets[0].id == operation["name"]
        if operation["family"] != "matmul":
            continue
        left, right = (shapes[name] for name in operation["inputs"])
        output = shapes[operation["outputs"][0]]
        assert left[0] != left[1] and right[0] != right[1]
        if operation.get("attributes", {}).get("rhs_transposed") is True:
            assert left[1] == right[1] and output == [left[0], right[0]]
            assert isinstance(node.value.args[1], ast.Call)
            assert node.value.args[1].func.attr == "trans"
            assert node.value.args[1].args[0].id == operation["inputs"][1]
        else:
            assert left[1] == right[0] and output == [left[0], right[1]]
            assert isinstance(node.value.args[1], ast.Name)
    assert len(graph["operations"]) <= 8 and len(graph["tensors"]) <= 24


def test_corpus_contains_mlp_mixed_modes_and_single_row():
    for profile in range(2):
        mlp = consumer.graph("mlp", profile)["operations"]
        assert [item["family"] for item in mlp] == [
            "matmul", "elementwise", "elementwise", "matmul", "elementwise"]
        mixed = consumer.graph("mixed", profile)["operations"]
        assert "attributes" not in mixed[0]
        assert mixed[1]["attributes"] == {"rhs_transposed": True}
    assert consumer.PROFILES[1][0] == 1


def test_default_and_emit_are_inert_portable_and_hash_complete(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("inert consumer launched a process")
    monkeypatch.setattr(consumer.subprocess, "Popen", forbidden)
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    report = consumer.candidate()
    assert report == consumer.candidate()
    assert report["native_execution_observed"] is False
    assert len(report["programs"]) == 6
    assert (report["planned_source_conversions"], report["planned_case_runs"],
            report["planned_scalar_checks"], report["planned_negative_controls"],
            report["planned_numeric_rejections"]) == (6, 12, 60, 10, 2)
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


def test_standalone_consumer_imports_only_standard_library():
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


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_fixed_sources_match_actual_trusted_parser_graphs(family, profile):
    """Parse only owned test literals as data, with no worker/isolation claim."""
    signature = consumer.signature(family, profile)
    parsed = ingest_triton_module_source_to_source_intent(
        consumer.source(family, profile).decode("ascii"),
        source_name=signature["source_name"], kernel_name=signature["kernel_name"],
        tensor_shapes=signature["tensor_shapes"])
    assert parsed.parser_result.source_intent_payload == consumer.graph(family, profile)


@pytest.mark.parametrize("case_id", (
    "arbitrary_call", "double_transpose", "lhs_transpose", "axes", "keyword_axes",
    "method", "attribute", "nested_add", "standalone", "shape_mismatch",
))
def test_fixed_negative_sources_have_real_parser_rejection(case_id):
    """Do not derive error classification by echoing a mocked CLI response."""
    case = next(case for case in consumer.negative_cases() if case["id"] == case_id)
    signature = case["signature"]
    source_api.prepare_source_request(case["source"], consumer.encoded(signature))
    with pytest.raises(ValueError):
        ingest_triton_module_source_to_source_intent(
            case["source"].decode("ascii"), source_name=signature["source_name"],
            kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
    assert case["reason"] == "source_rejected"


def test_numeric_controls_have_normal_operands_and_invalid_products():
    cases = consumer.numeric_cases()
    assert [case["id"] for case in cases] == ["product_overflow", "product_subnormal"]
    for case in cases:
        for values in case["inputs"].values():
            for value in values:
                assert type(value) is float and math.isfinite(value)
                assert consumer.f32(value) == value
    with np.errstate(over="ignore", under="ignore"):
        products = [np.multiply(np.float32(case["inputs"]["x"][0]),
                                np.float32(case["inputs"]["weight"][0]), dtype=np.float32)
                    for case in cases]
    assert np.isposinf(products[0])
    assert products[1].view(np.uint32) == 0x00400000


@pytest.mark.parametrize("actual,expected", [
    ({"scores": [0.0]}, {"scores": [-0.0]}),
    ({"scores": [1.0 + 1e-9]}, {"scores": [1.0]}),
    ({"scores": [1]}, {"scores": [1.0]}),
    ({"other": [1.0]}, {"scores": [1.0]}),
    ({"scores": [float("nan")]}, {"scores": [0.0]}),
])
def test_output_checks_are_bitwise_exact_and_require_declared_public_names(actual, expected):
    with pytest.raises(ValueError):
        consumer._check_outputs(actual, expected)


def test_request_digest_uses_physical_weight_order_and_input_order():
    source = consumer.graph("affine", 0)
    inputs, _ = consumer.public_bindings(source)
    data = consumer.input_envelope("affine", 0, 1)
    assert [item["public_name"] for item in inputs] == ["x", "weight", "bias"]
    payload = b"".join(struct.pack("<f", value)
                       for name in ("x", "weight", "bias") for value in data["inputs"][name])
    expected = hashlib.sha256(bytes.fromhex("a" * 64) + payload).hexdigest()
    assert consumer._request_digest("a" * 64, inputs, data) == expected


@pytest.mark.parametrize("field", ("tensor_index", "shape"))
def test_inspected_binding_rejects_boolean_in_place_of_integer(field):
    inputs, outputs = consumer.public_bindings(consumer.graph("affine", 1))
    expected = {"inputs": inputs, "outputs": outputs}
    actual = json.loads(json.dumps(expected))
    consumer._check_public_bindings(actual, expected)
    if field == "tensor_index":
        assert actual["inputs"][1][field] == 1
        actual["inputs"][1][field] = True
    else:
        assert actual["inputs"][0][field][0] == 1
        actual["inputs"][0][field][0] = True
    assert actual == expected  # Plain Python equality would miss this type change.
    with pytest.raises(ValueError, match="public binding"):
        consumer._check_public_bindings(actual, expected)


@pytest.mark.parametrize("wrong", ((0, b"partial", b""),
                                  (1, b"", b"tuc-cpu-app: protocol_rejection\n"),
                                  (1, b"data", b"tuc-cpu-app: numeric_rejection\n")))
def test_numeric_driver_rejects_wrong_reason_or_partial_output(monkeypatch, tmp_path, wrong):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    program = next(item for item in consumer.candidate()["programs"] if item["id"] == "affine_0")
    program["program_digest"] = "a" * 64
    monkeypatch.setattr(consumer, "_invoke", lambda *args: wrong)
    with pytest.raises(ValueError, match="product_overflow"):
        consumer._numeric_controls(Path("never-executed"), tmp_path, workspace, {}, program)
    assert not (tmp_path / "record.json").exists()


def test_readable_linear_example_has_independently_computed_output():
    root = Path(consumer.__file__).resolve().parent
    source = (root / "linear.py.txt").read_text()
    signature = json.loads((root / "linear-signature.json").read_bytes())
    data = json.loads((root / "linear-inputs.json").read_bytes())["inputs"]
    assert ast.parse(source).body[-1].name == signature["kernel_name"]
    projected = matmul(data["x"], data["weight"], 2, 3, 2, transposed=True)
    scores = np.add(projected, np.asarray(data["bias"], dtype=np.float32), dtype=np.float32)
    np.testing.assert_array_equal(scores.ravel(), [-0.5, 1.0, 4.5, 7.0])
    parsed = ingest_triton_module_source_to_source_intent(
        source, source_name=signature["source_name"], kernel_name=signature["kernel_name"],
        tensor_shapes=signature["tensor_shapes"])
    assert parsed.parser_result.source_intent_payload["operations"][0]["attributes"] == {
        "rhs_transposed": True}
