"""Independent gated-MLP consumer checks; no console, OCI or native execution."""

import ast
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_gating import consumer
from tuc.compiler import bounded_cpu_source as source_api
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
)


def linear(left, weight, rows, inner, columns):
    lhs = np.asarray(left, dtype=np.float32).reshape(rows, inner)
    rhs = np.asarray(weight, dtype=np.float32).reshape(columns, inner).T
    output = np.zeros((rows, columns), dtype=np.float32)
    for index in range(inner):
        output = np.add(output, np.multiply(lhs[:, index, None], rhs[index, None, :],
                                            dtype=np.float32), dtype=np.float32)
    return output


def numpy_reference(family, profile, envelope):
    values = {name: np.asarray(items, dtype=np.float32)
              for name, items in envelope["inputs"].items()}
    if family == "vector":
        return np.multiply(values["left"], values["right"], dtype=np.float32)
    if family == "square":
        return np.multiply(values["x"], values["x"], dtype=np.float32)
    m, k, h, n = consumer.PROFILES[profile]
    value = np.add(linear(values["x"], values["wv"], m, k, h), values["bv"], dtype=np.float32)
    shifted = np.add(linear(values["x"], values["wg"], m, k, h), values["bg"], dtype=np.float32)
    gate = np.where(shifted < np.float32(0), np.float32(0), shifted)
    fused = np.multiply(value, gate, dtype=np.float32)
    output = linear(fused.ravel(), values["wo"], m, h, n)
    if profile == 1:
        output = np.add(output, values["bout"], dtype=np.float32)
    return output.ravel()


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(2))
def test_scalar_reference_matches_independent_numpy_fp32_bits(family, profile, case):
    data = consumer.input_envelope(family, profile, case)
    expected = numpy_reference(family, profile, data)
    actual = np.asarray(consumer.reference(family, profile, data)["scores"], dtype=np.float32)
    np.testing.assert_array_equal(actual.view(np.uint32), expected.view(np.uint32))


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_input_changes_change_outputs_and_include_nondyadic_numbers(family, profile):
    first = consumer.input_envelope(family, profile, 0)
    second = consumer.input_envelope(family, profile, 1)
    assert first != second
    assert consumer.reference(family, profile, first) != consumer.reference(family, profile, second)
    assert any(value * 8 != round(value * 8)
               for values in second["inputs"].values() for value in values)


@pytest.mark.parametrize("profile", range(2))
def test_signed_zero_and_repeated_operand_have_explicit_semantics(profile):
    vector = consumer.input_envelope("vector", profile, 1)
    square = consumer.input_envelope("square", profile, 1)
    assert struct.pack("<f", vector["inputs"]["left"][0]) == struct.pack("<I", 0x80000000)
    assert struct.pack("<f", square["inputs"]["x"][0]) == struct.pack("<I", 0x80000000)
    assert struct.pack("<f", consumer.reference("vector", profile, vector)["scores"][0]) == (
        struct.pack("<I", 0x80000000))
    assert struct.pack("<f", consumer.reference("square", profile, square)["scores"][0]) == (
        struct.pack("<I", 0))
    graph = consumer.graph("square", profile)
    assert graph["operations"][0]["inputs"] == ["x", "x"]
    assert len(consumer.public_bindings(graph)[0]) == 1


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_source_signature_and_graph_are_complete_and_shapes_match(family, profile):
    tree = ast.parse(consumer.source(family, profile))
    signature = consumer.signature(family, profile)
    graph = consumer.graph(family, profile)
    assert len(tree.body) == 3
    kernel = tree.body[-1]
    assert kernel.name == signature["source_name"] == signature["kernel_name"] == graph["name"]
    inputs, outputs = consumer.public_bindings(graph)
    assert signature["tensor_shapes"] == {
        item["public_name"]: item["shape"] for item in inputs + outputs}
    assert [argument.arg for argument in kernel.args.args] == list(signature["tensor_shapes"])
    assignments = [node for node in kernel.body if isinstance(node, ast.Assign)]
    shapes = {item["name"]: item["shape"] for item in graph["tensors"]}
    for node, operation in zip(assignments, graph["operations"], strict=True):
        assert node.targets[0].id == operation["name"]
        if operation.get("attributes", {}).get("elementwise_kind") == "mul":
            assert isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Mult)
            assert isinstance(node.value.left, ast.Name) and isinstance(node.value.right, ast.Name)
            assert [node.value.left.id, node.value.right.id] == operation["inputs"]
            assert len({tuple(shapes[name]) for name in
                        operation["inputs"] + operation["outputs"]}) == 1
    produced = {name for op in graph["operations"] for name in op["outputs"]}
    consumed = {name for op in graph["operations"] for name in op["inputs"]}
    assert produced - consumed == {item["tensor_name"] for item in graph["returns"]}
    assert len(graph["operations"]) <= 8 and len(graph["tensors"]) <= 24


def test_gated_mlp_covers_seven_and_eight_operations_and_two_live_branches():
    for profile in range(2):
        operations = consumer.graph("gated_mlp", profile)["operations"]
        assert len(operations) == 7 + profile
        assert operations[0]["inputs"][0] == operations[2]["inputs"][0] == "x"
        assert operations[5]["inputs"] == ["value", "gate"]
        assert operations[5]["attributes"] == {"elementwise_kind": "mul"}
        assert operations[4]["attributes"] == {"elementwise_kind": "relu"}
        for case in range(2):
            output = consumer.reference("gated_mlp", profile,
                                        consumer.input_envelope("gated_mlp", profile, case))
            assert any(value != 0.0 for value in output["scores"])


def test_default_and_emit_are_inert_portable_and_have_complete_hashes(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("inert consumer launched a process")
    monkeypatch.setattr(consumer.subprocess, "Popen", forbidden)
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    report = consumer.candidate()
    assert report == consumer.candidate() and report["native_execution_observed"] is False
    assert len(report["programs"]) == 6
    assert (report["planned_source_conversions"], report["planned_case_runs"],
            report["planned_scalar_checks"], report["planned_negative_controls"],
            report["planned_numeric_rejections"]) == (6, 12, 56, 10, 3)
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
    """Parse only owned literal fixture data; this is not worker execution evidence."""
    signature = consumer.signature(family, profile)
    parsed = ingest_triton_module_source_to_source_intent(
        consumer.source(family, profile).decode("ascii"),
        source_name=signature["source_name"], kernel_name=signature["kernel_name"],
        tensor_shapes=signature["tensor_shapes"])
    assert parsed.parser_result.source_intent_payload == consumer.graph(family, profile)


@pytest.mark.parametrize("case_id", (
    "scalar_right", "scalar_left", "nested", "division", "power", "call",
    "left_row_broadcast", "column_broadcast", "shape_mismatch", "left_vector_broadcast",
))
def test_fixed_negative_sources_reject_in_actual_parser(case_id):
    case = next(case for case in consumer.negative_cases() if case["id"] == case_id)
    signature = case["signature"]
    if case_id.startswith("left_"):
        shapes = signature["tensor_shapes"]
        expected = (([3], [2, 3]) if case_id == "left_row_broadcast" else ([1], [3]))
        assert (shapes["x"], shapes["rhs"]) == expected
        assert shapes["result"] == shapes["x"]
    source_api.prepare_source_request(case["source"], consumer.encoded(signature))
    with pytest.raises(ValueError):
        ingest_triton_module_source_to_source_intent(
            case["source"].decode("ascii"), source_name=signature["source_name"],
            kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
    assert case["reason"] == "source_rejected"


def test_numeric_controls_have_normal_inputs_but_invalid_rounded_products():
    cases = consumer.numeric_cases()
    assert [case["id"] for case in cases] == [
        "product_overflow", "product_subnormal", "nonzero_product_to_zero"]
    for case in cases:
        for values in case["inputs"].values():
            for value in values:
                assert type(value) is float and math.isfinite(value)
                assert consumer.f32(value) == value
        with pytest.raises((ValueError, OverflowError)):
            consumer.reference("vector", 0, case)
    with np.errstate(over="ignore", under="ignore"):
        products = [np.multiply(np.float32(case["inputs"]["left"][0]),
                                np.float32(case["inputs"]["right"][0]), dtype=np.float32)
                    for case in cases]
    assert [int(value.view(np.uint32)) for value in products] == [0x7f800000, 0x00400000, 0]


@pytest.mark.parametrize("actual,expected", [
    ({"scores": [0.0]}, {"scores": [-0.0]}),
    ({"scores": [1.0 + 1e-9]}, {"scores": [1.0]}),
    ({"scores": [1]}, {"scores": [1.0]}),
    ({"other": [1.0]}, {"scores": [1.0]}),
    ({"scores": [float("nan")]}, {"scores": [0.0]}),
])
def test_output_checks_require_bitwise_exact_public_float_arrays(actual, expected):
    with pytest.raises(ValueError):
        consumer._check_outputs(actual, expected)


def test_request_digest_uses_one_physical_input_for_repeated_operands():
    inputs, _ = consumer.public_bindings(consumer.graph("square", 1))
    data = consumer.input_envelope("square", 1, 1)
    assert [item["public_name"] for item in inputs] == ["x"]
    payload = b"".join(struct.pack("<f", value) for value in data["inputs"]["x"])
    expected = hashlib.sha256(bytes.fromhex("a" * 64) + payload).hexdigest()
    assert consumer._request_digest("a" * 64, inputs, data) == expected


@pytest.mark.parametrize("field", ("tensor_index", "shape"))
def test_inspected_binding_rejects_boolean_in_place_of_integer(field):
    inputs, outputs = consumer.public_bindings(consumer.graph("gated_mlp", 1))
    expected = {"inputs": inputs, "outputs": outputs}
    actual = json.loads(json.dumps(expected))
    consumer._check_public_bindings(actual, expected)
    if field == "tensor_index":
        assert actual["inputs"][1][field] == 1
        actual["inputs"][1][field] = True
    else:
        assert actual["inputs"][0][field][0] == 1
        actual["inputs"][0][field][0] = True
    assert actual == expected
    with pytest.raises(ValueError, match="public binding"):
        consumer._check_public_bindings(actual, expected)


@pytest.mark.parametrize("wrong", ((0, b"partial", b""),
                                  (1, b"", b"tuc-cpu-app: protocol_rejection\n"),
                                  (1, b"data", b"tuc-cpu-app: numeric_rejection\n")))
def test_numeric_driver_rejects_wrong_reason_or_partial_output(monkeypatch, tmp_path, wrong):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    program = next(item for item in consumer.candidate()["programs"] if item["id"] == "vector_0")
    program["program_digest"] = "a" * 64
    monkeypatch.setattr(consumer, "_invoke", lambda *args: wrong)
    with pytest.raises(ValueError, match="product_overflow"):
        consumer._numeric_controls(Path("never-executed"), tmp_path, workspace, {}, program)
    assert not (tmp_path / "record.json").exists()


def test_readable_gated_mlp_example_has_independently_computed_branches_and_output():
    root = Path(consumer.__file__).resolve().parent
    source = (root / "gated-mlp.py.txt").read_text()
    signature = json.loads((root / "gated-mlp-signature.json").read_bytes())
    data = json.loads((root / "gated-mlp-inputs.json").read_bytes())["inputs"]
    assert ast.parse(source).body[-1].name == signature["kernel_name"]
    value = np.add(linear(data["x"], data["wv"], 2, 2, 2),
                   np.asarray(data["bv"], dtype=np.float32), dtype=np.float32)
    shifted = np.add(linear(data["x"], data["wg"], 2, 2, 2),
                     np.asarray(data["bg"], dtype=np.float32), dtype=np.float32)
    gate = np.where(shifted < np.float32(0), np.float32(0), shifted)
    np.testing.assert_array_equal(value, [[2, -3], [4, 3]])
    np.testing.assert_array_equal(gate, [[0, 4], [7, 0]])
    fused = np.multiply(value, gate, dtype=np.float32)
    scores = linear(fused.ravel(), data["wo"], 2, 2, 1)
    np.testing.assert_array_equal(scores.ravel(), [-24.0, 28.0])
    parsed = ingest_triton_module_source_to_source_intent(
        source, source_name=signature["source_name"], kernel_name=signature["kernel_name"],
        tensor_shapes=signature["tensor_shapes"])
    assert len(parsed.parser_result.source_intent_payload["operations"]) == 7
    assert parsed.parser_result.source_intent_payload["operations"][5]["attributes"] == {
        "elementwise_kind": "mul"}
