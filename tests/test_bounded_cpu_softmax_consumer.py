"""Independent installed Softmax client checks, with no native/OCI execution."""

import ast
import copy
import hashlib
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_softmax import consumer
from tuc.compiler import bounded_cpu_source as source_api
from tuc.compiler.bounded_cpu_json import source_intent_from_json
from tuc.frontend.source_to_intent_research_kernel_ingress import (
    ingest_triton_module_source_to_source_intent,
)


def numpy_matmul(left, right):
    output = np.zeros((left.shape[0], right.shape[1]), dtype=np.float32)
    for index in range(left.shape[1]):
        product = np.multiply(left[:, index, None], right[None, index, :], dtype=np.float32)
        output = np.add(output, product, dtype=np.float32)
    return output


def numpy_softmax(values):
    shifted = np.subtract(values, np.max(values, axis=1, keepdims=True), dtype=np.float32)
    exponentials = np.exp(shifted, dtype=np.float32)
    total = np.zeros(values.shape[0], dtype=np.float32)
    for column in range(values.shape[1]):
        total = np.add(total, exponentials[:, column], dtype=np.float32)
    return np.divide(exponentials, total[:, None], dtype=np.float32)


def numpy_reference(family, profile, data):
    values = {key: np.asarray(items, dtype=np.float32) for key, items in data["inputs"].items()}
    if family == "alone":
        return numpy_softmax(values["x"].reshape(((2, 1), (3, 7))[profile])).ravel()
    if family == "classifier":
        m, k, n = ((2, 3, 4), (1, 2, 3))[profile]
        logits = numpy_matmul(values["x"].reshape(m, k), values["weight"].reshape(n, k).T)
        return numpy_softmax(np.add(logits, values["bias"], dtype=np.float32)).ravel()
    m, k, s, d = ((2, 3, 4, 2), (1, 2, 3, 3))[profile]
    logits = numpy_matmul(values["q"].reshape(m, k), values["key"].reshape(s, k).T)
    probability = numpy_softmax(logits)
    return numpy_matmul(probability, values["value"].reshape(s, d)).ravel()


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(2))
def test_scalar_oracle_matches_independent_numpy_fp32(family, profile, case):
    data = consumer.input_envelope(family, profile, case)
    expected = numpy_reference(family, profile, data)
    actual = np.asarray(consumer.reference(family, profile, data)["scores"], dtype=np.float32)
    np.testing.assert_allclose(actual, expected, rtol=2e-5, atol=2e-6)
    assert np.isfinite(actual).all()
    if family != "attention":
        rows = consumer._check_row_mass(
            {"scores": [float(item) for item in actual]}, family, profile)
        assert rows == (((2, 3) if family == "alone" else (2, 1))[profile])


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_source_signatures_match_real_owned_parser_and_complete_graph(family, profile):
    signature = consumer.signature(family, profile)
    source = consumer.source(family, profile)
    request = json.loads(source_api.prepare_source_request(source, consumer.encoded(signature)))
    parsed = ingest_triton_module_source_to_source_intent(
        source.decode("ascii"), source_name=signature["source_name"],
        kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
    payload = parsed.parser_result.source_intent_payload
    assert payload == consumer.graph(family, profile)
    source_api._bound_graph(payload, request["payload"])
    graph = source_intent_from_json(consumer.encoded(payload))
    assert len(graph.operations) in (1, 3)
    assert sum(op.family == "softmax" for op in graph.operations) == 1
    tree = ast.parse(source)
    inputs, outputs = consumer.public_bindings(payload)
    assert [arg.arg for arg in tree.body[-1].args.args] == [
        item["public_name"] for item in inputs + outputs]
    assert signature["tensor_shapes"] == {item["public_name"]: item["shape"]
                                          for item in inputs + outputs}
    first = consumer.input_envelope(family, profile, 0)
    second = consumer.input_envelope(family, profile, 1)
    assert first != second
    # Width one deliberately has the same all-one result for changing input data.
    if (family, profile) != ("alone", 0):
        assert consumer.reference(family, profile, first) != consumer.reference(
            family, profile, second)


def test_width_one_and_nonsquare_attention_shapes():
    for case in range(2):
        assert consumer.reference("alone", 0, consumer.input_envelope("alone", 0, case)) == (
            {"scores": [1.0, 1.0]})
    assert consumer.graph("alone", 1)["tensors"][0]["shape"] == [3, 7]
    for profile, expected in ((0, [2, 2]), (1, [1, 3])):
        graph = consumer.graph("attention", profile)
        assert graph["tensors"][-1]["shape"] == expected
        assert graph["operations"][0]["attributes"] == {"rhs_transposed": True}
        assert "attributes" not in graph["operations"][-1]
    assert consumer._check_row_mass({"scores": [-1.0]}, "attention", 0) == 0


def test_shared_classifier_batch_oracle_and_identity_equations():
    batch = consumer.batch_data()
    inputs, _ = consumer.public_bindings(consumer.graph("classifier", 0))
    assert set(batch["shared_inputs"]) == {"weight", "bias"}
    assert [item["id"] for item in batch["requests"]] == ["sample_0", "sample_1", "sample_2"]
    identities = []
    for request in batch["requests"]:
        assert set(request["inputs"]) == {"x"}
        data = consumer.merged_input(batch, request)
        expected = numpy_reference("classifier", 0, data)
        actual = consumer.reference("classifier", 0, data)["scores"]
        np.testing.assert_allclose(actual, expected, rtol=2e-5, atol=2e-6)
        payload = b"".join(struct.pack("<f", number) for binding in inputs
                           for number in data["inputs"][binding["public_name"]])
        identity = hashlib.sha256(bytes.fromhex("a" * 64) + payload).hexdigest()
        assert consumer._request_digest("a" * 64, inputs, data) == identity
        identities.append({"id": request["id"], "request_digest": identity})
    assert len({item["request_digest"] for item in identities}) == 3
    payload = {"schema_version": "tuc.bounded_cpu_batch.v0", "program_digest": "a" * 64,
               "requests": identities}
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=True, allow_nan=False).encode("ascii"))
    assert consumer._batch_digest("a" * 64, identities) == expected.hexdigest()
    assert consumer._batch_digest("a" * 64, identities[::-1]) != expected.hexdigest()


@pytest.mark.parametrize("case_id", [case["id"] for case in consumer.negative_cases()])
def test_negative_fixtures_follow_real_pure_parser_and_graph_boundaries(case_id):
    case = next(item for item in consumer.negative_cases() if item["id"] == case_id)
    if "source" not in case:
        with pytest.raises(ValueError):
            source_intent_from_json(consumer.encoded(case["graph"]))
        assert case["reason"] == "graph_json_rejected"
        return
    signature = case["signature"]
    request = json.loads(source_api.prepare_source_request(case["source"],
                                                          consumer.encoded(signature)))
    if case_id == "source_axis0":
        parsed = ingest_triton_module_source_to_source_intent(
            case["source"].decode("ascii"), source_name=signature["source_name"],
            kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
        with pytest.raises(ValueError):
            source_api._bound_graph(parsed.parser_result.source_intent_payload, request["payload"])
        assert case["reason"] == "graph_rejected"
    else:
        with pytest.raises(ValueError):
            ingest_triton_module_source_to_source_intent(
                case["source"].decode("ascii"), source_name=signature["source_name"],
                kernel_name=signature["kernel_name"], tensor_shapes=signature["tensor_shapes"])
        assert case["reason"] == "source_rejected"


def test_numeric_controls_have_valid_inputs_but_different_invalid_intermediates():
    cases = consumer.numeric_cases()
    assert [case["id"] for case in cases] == ["shift_overflow", "exponential_subnormal",
                                             "exponential_zero", "shift_subnormal"]
    for case in cases:
        for value in case["inputs"]["x"]:
            bits = struct.unpack("<I", struct.pack("<f", value))[0] & 0x7fffffff
            assert bits == 0 or 0 < bits & 0x7f800000 < 0x7f800000
        assert len(case["inputs"]["x"]) == 21
        with pytest.raises((OverflowError, ValueError)):
            consumer.reference("alone", 1, case)
    with np.errstate(over="ignore", under="ignore"):
        overflow = np.subtract(np.float32(cases[0]["inputs"]["x"][1]),
                               np.float32(cases[0]["inputs"]["x"][0]), dtype=np.float32)
        subnormal_exp = np.exp(np.float32(-90), dtype=np.float32)
        zero_exp = np.exp(np.float32(-110), dtype=np.float32)
        subnormal_shift = np.subtract(np.float32(cases[3]["inputs"]["x"][0]),
                                       np.float32(cases[3]["inputs"]["x"][1]), dtype=np.float32)
    assert int(overflow.view(np.uint32)) == 0xff800000
    assert 0 < int(subnormal_exp.view(np.uint32)) < 0x00800000
    assert int(zero_exp.view(np.uint32)) == 0
    assert int(subnormal_shift.view(np.uint32)) == 0x80000001


def test_candidate_and_fixture_emit_are_inert_and_bound(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("inert mode invoked CLI")
    monkeypatch.setattr(consumer, "_invoke", forbidden)
    monkeypatch.setattr(consumer, "_installed_cli", forbidden)
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    candidate = consumer.candidate()
    assert candidate == consumer.candidate() and candidate["native_execution_observed"] is False
    keys = ("source_conversions", "case_runs", "batch_runs", "batch_request_runs",
            "scalar_checks", "row_mass_checks", "negative_controls", "numeric_rejections")
    assert [candidate[key] for key in keys] == [0] * 8
    assert [candidate["planned_" + key] for key in keys] == [6, 12, 1, 3, 106, 22, 8, 4]
    emitted = consumer.emit()
    folder = Path(emitted["fixture_directory"])
    assert folder.parent == tmp_path / "tmp"
    for program in candidate["programs"]:
        for name, field in (("kernel.py", "source_sha256"), ("signature.json", "signature_sha256")):
            assert hashlib.sha256((folder / program["id"] / name).read_bytes()).hexdigest() == (
                program[field])
        for case in program["cases"]:
            assert hashlib.sha256((folder / program["id"] /
                                   f"inputs-{case['case']}.json").read_bytes()).hexdigest() == (
                case["input_sha256"])
    assert hashlib.sha256((folder / "classifier-batch.json").read_bytes()).hexdigest() == (
        candidate["batch"]["batch_sha256"])
    assert not (folder / "record.json").exists()


def test_standalone_consumer_imports_only_standard_library():
    tree = ast.parse(Path(consumer.__file__).read_text(encoding="utf-8"))
    allowed = {"__future__", "argparse", "hashlib", "json", "math", "os", "re", "selectors",
               "signal", "stat", "struct", "subprocess", "sys", "tempfile", "time",
               "contextlib", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name in allowed for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module in allowed
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "compile", "__import__"}


@pytest.mark.parametrize("actual", [0.0, -0.0, -0.1, float("nan"), float("inf"), 1, True])
def test_row_probability_checks_reject_nonpositive_nonfinite_or_inexact_types(actual):
    with pytest.raises(ValueError):
        consumer._check_row_mass({"scores": [actual, 1.0]}, "alone", 0)


def test_tolerance_allows_small_exp_approximation_but_row_mass_is_independent():
    assert consumer._check_outputs({"scores": [0.250001]}, {"scores": [0.25]}) == 1
    with pytest.raises(ValueError):
        consumer._check_outputs({"scores": [0.2501]}, {"scores": [0.25]})
    expected = {"scores": [0.25] * 8}
    observed = {"scores": [0.250003] * 8}
    assert consumer._check_outputs(observed, expected) == 8
    with pytest.raises(ValueError, match="mass"):
        consumer._check_row_mass(observed, "classifier", 0)


def batch_response(program):
    batch = consumer.batch_data()
    results = [{"id": request["id"], "request_digest": consumer._request_digest(
        program["program_digest"], program["inputs"], consumer.merged_input(batch, request)),
        "outputs": consumer.reference("classifier", 0, consumer.merged_input(batch, request))}
        for request in batch["requests"]]
    return {"schema_version": consumer.BATCH_CLI_SCHEMA, "action": "run-batch",
            "program_digest": program["program_digest"], "results": results,
            "batch_digest": consumer._batch_digest(program["program_digest"], results),
            "native_execution_observed": True}


@pytest.mark.parametrize("change", ["program", "batch_digest", "request_digest", "id", "order",
                                   "missing", "extra", "extra_field", "output", "nonfloat",
                                   "native", "action", "output_name"])
def test_batch_checker_rejects_forged_envelope_identity_or_outputs(change):
    report = consumer.candidate()
    program = report["programs"][2]
    program["program_digest"] = "a" * 64
    value = batch_response(program)
    _, scalars, rows = consumer._check_batch(
        (0, consumer.encoded(value), b""), program, report["batch"])
    assert (scalars, rows) == (24, 6)
    if change == "program":
        value["program_digest"] = "b" * 64
    elif change == "batch_digest":
        value["batch_digest"] = "b" * 64
    elif change in ("request_digest", "id"):
        value["results"][0][change] = "changed"
    elif change == "order":
        value["results"].reverse()
    elif change == "missing":
        value["results"].pop()
    elif change == "extra":
        value["results"].append(value["results"][0])
    elif change == "extra_field":
        value["results"][0]["extra"] = 0
    elif change in ("output", "nonfloat"):
        value["results"][0]["outputs"]["scores"][0] = 1.0 if change == "output" else 1
    elif change == "native":
        value["native_execution_observed"] = 1
    elif change == "output_name":
        value["results"][0]["outputs"]["unknown"] = value["results"][0]["outputs"].pop("scores")
    else:
        value["action"] = "run"
    with pytest.raises(ValueError):
        consumer._check_batch((0, consumer.encoded(value), b""), program, report["batch"])


@pytest.mark.parametrize("field", ("tensor_index", "shape"))
def test_binding_comparison_rejects_boolean_integer_substitution(field):
    inputs, outputs = consumer.public_bindings(consumer.graph("classifier", 1))
    expected = {"inputs": inputs, "outputs": outputs}
    actual = copy.deepcopy(expected)
    if field == "tensor_index":
        actual["inputs"][1][field] = True
    else:
        actual["inputs"][0][field][0] = True
    assert actual == expected
    with pytest.raises(ValueError):
        consumer._check_public_bindings(actual, expected)


@pytest.mark.parametrize("wrong", [(1, b"partial", b"tuc-cpu-app: numeric_rejection\n"),
                                   (0, b"", b""), (1, b"", b"tuc-cpu-app: input_rejection\n")])
def test_numeric_driver_requires_exact_closed_failure(monkeypatch, tmp_path, wrong):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    program = consumer.candidate()["programs"][1]
    program["program_digest"] = "a" * 64
    monkeypatch.setattr(consumer, "_invoke", lambda *args: wrong)
    with pytest.raises(ValueError, match="shift_overflow"):
        consumer._numeric_controls(Path("not-executed"), tmp_path, workspace, {}, program)


def test_context_guard_detects_changed_original_graph_and_leftover_workspace(tmp_path):
    path = tmp_path / "graph.json"
    path.write_bytes(b"original")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    consumer._unchanged({path: b"original"}, workspace)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="original"):
        consumer._unchanged({path: b"original"}, workspace)
    path.write_bytes(b"original")
    (workspace / "leftover").write_bytes(b"x")
    with pytest.raises(ValueError, match="resources"):
        consumer._unchanged({path: b"original"}, workspace)


def test_mock_driver_covers_counts_and_publishes_only_complete_record(monkeypatch, tmp_path):
    """Synthetic client wiring only; these responses are not native evidence."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(consumer, "_installed_cli", lambda name: Path(name))
    calls = []
    def invoke(executable, arguments):
        calls.append((str(executable), arguments))
        if "negative-" in arguments[0] or (len(arguments) > 1 and "negative-" in arguments[1]):
            path = arguments[0] if str(executable) == "tuc-source-to-json" else arguments[1]
            case_id = Path(path).stem.removeprefix("negative-")
            case = next(item for item in consumer.negative_cases() if item["id"] == case_id)
            return 2, b"", f"{executable}: {case['reason']}\n".encode("ascii")
        if str(executable) == "tuc-source-to-json":
            name = json.loads(Path(arguments[2]).read_bytes())["source_name"]
            graph = next(consumer.graph(family, profile) for family in consumer.FAMILIES
                         for profile in range(2)
                         if consumer.graph(family, profile)["name"] == name)
            return 0, consumer.encoded(graph), b""
        graph = json.loads(Path(arguments[1]).read_bytes())
        program = next(item for item in consumer.candidate()["programs"]
                       if graph["name"] == "softmax_" + item["id"])
        program["program_digest"] = consumer.digest(consumer.encoded(graph))
        if arguments[0] == "inspect":
            return 0, consumer.encoded({"schema_version": consumer.CLI_SCHEMA, "action": "inspect",
                "program_digest": program["program_digest"], "inputs": program["inputs"],
                "outputs": program["outputs"], "native_execution_observed": False}), b""
        if arguments[0] == "run-batch":
            return 0, consumer.encoded(batch_response(program)), b""
        if Path(arguments[3]).name.startswith("numeric-"):
            return 1, b"", b"tuc-cpu-app: numeric_rejection\n"
        data = json.loads(Path(arguments[3]).read_bytes())
        return 0, consumer.encoded({"schema_version": consumer.CLI_SCHEMA, "action": "run",
            "program_digest": program["program_digest"], "request_digest": consumer._request_digest(
                program["program_digest"], program["inputs"], data), "outputs": consumer.reference(
                    program["family"], program["profile"], data),
            "native_execution_observed": True}), b""
    monkeypatch.setattr(consumer, "_invoke", invoke)
    report = consumer.run()
    assert len(calls) == 6 + 6 + 12 + 1 + 8 + 4
    assert [report[key] for key in ("source_conversions", "case_runs", "batch_runs",
                                   "batch_request_runs", "scalar_checks", "row_mass_checks",
                                   "negative_controls", "numeric_rejections")] == [6, 12, 1, 3,
                                                                                 106, 22, 8, 4]
    assert report["original_files_unchanged"] is True and report["workspaces_clean"] is True
    assert json.loads((tmp_path / "record.json").read_bytes()) == report
