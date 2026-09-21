"""Independent installed-client checks; no console, Docker or native execution."""

import ast
import copy
import hashlib
import json
import math
import struct
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_cpu_batch import consumer
from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_cpu_json import source_intent_from_json
from tuc.compiler.bounded_source import BoundedBackendBinding, compile_bounded_source_intent
from tuc.ir.memory import MemoryDomainKind
from tuc.ir.model import OperationKind


def numpy_linear(left, weight, m, k, n):
    lhs = np.asarray(left, dtype=np.float32).reshape(m, k)
    rhs = np.asarray(weight, dtype=np.float32).reshape(n, k)
    result = np.zeros((m, n), dtype=np.float32)
    for inner in range(k):
        product = np.multiply(lhs[:, inner, None], rhs[None, :, inner], dtype=np.float32)
        result = np.add(result, product, dtype=np.float32)
    return result


def numpy_reference(family, profile, data):
    values = {name: np.asarray(items, dtype=np.float32)
              for name, items in data["inputs"].items()}
    if family == "product":
        return (np.multiply(values["left"], values["right"], dtype=np.float32) if profile == 0
                else np.square(values["x"], dtype=np.float32))
    if family == "linear":
        m, k, n = ((2, 3, 3), (1, 2, 2))[profile]
        return np.add(numpy_linear(values["x"], values["weight"], m, k, n),
                      values["bias"], dtype=np.float32).ravel()
    m, k, h, n = ((2, 3, 4, 2), (1, 2, 3, 3))[profile]
    value = np.add(numpy_linear(values["x"], values["wv"], m, k, h), values["bv"],
                   dtype=np.float32)
    shift = np.add(numpy_linear(values["x"], values["wg"], m, k, h), values["bg"],
                   dtype=np.float32)
    gated = np.multiply(value, np.where(shift < np.float32(0), np.float32(0), shift),
                        dtype=np.float32)
    result = numpy_linear(gated.ravel(), values["wo"], m, h, n)
    return np.add(result, values["bout"], dtype=np.float32).ravel()


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
@pytest.mark.parametrize("case", range(3))
def test_scalar_oracle_matches_independently_ordered_numpy_bits(family, profile, case):
    batch = consumer.batch_data(family, profile)
    data = consumer.merged_input(batch, batch["requests"][case])
    expected = numpy_reference(family, profile, data)
    actual = np.asarray(consumer.reference(family, profile, data)["scores"], dtype=np.float32)
    np.testing.assert_array_equal(actual.view(np.uint32), expected.view(np.uint32))


@pytest.mark.parametrize("family", consumer.FAMILIES)
@pytest.mark.parametrize("profile", range(2))
def test_typed_graph_binding_and_batch_input_coverage(family, profile):
    graph = consumer.graph(family, profile)
    module = source_intent_from_json(consumer.encoded(graph))
    bindings = (BoundedBackendBinding(BackendCapability(
        "json_cpu", frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE,
                               OperationKind.REDUCTION}), memory_domain=MemoryDomainKind.HOST_RAM),
        DAGTarget.C11),)
    compiled = compile_bounded_source_intent(module, bindings)
    inputs, outputs = consumer.public_bindings(graph)
    actual_inputs = json.loads(consumer.encoded([asdict(item) for item in compiled.input_bindings]))
    actual_outputs = json.loads(consumer.encoded(
        [asdict(item) for item in compiled.output_bindings]))
    assert actual_inputs == inputs
    assert actual_outputs == outputs
    batch = consumer.batch_data(family, profile)
    assert len(batch["requests"]) == 3
    assert len(graph["operations"]) <= 8 and len(graph["tensors"]) <= 24
    shared = batch["shared_inputs"]
    counts = []
    for request in batch["requests"]:
        assert not set(shared) & set(request["inputs"])
        data = consumer.merged_input(batch, request)["inputs"]
        assert set(data) == {item["public_name"] for item in inputs}
        assert all(len(data[item["public_name"]]) == math.prod(item["shape"]) for item in inputs)
        assert all(type(value) is float for values in data.values() for value in values)
        counts.append(sum(map(len, data.values())))
    assert sum(counts) <= 65536
    assert 3 * sum(math.prod(item["shape"]) for item in outputs) <= 65536
    assert len(consumer.encoded(batch)) < 2 * 1024 * 1024
    assert len({consumer.encoded(request["inputs"]) for request in batch["requests"]}) == 3
    results = [consumer.reference(family, profile, consumer.merged_input(batch, request))
               for request in batch["requests"]]
    assert len({consumer.encoded(result) for result in results}) == 3


def test_weights_are_shared_and_product_covers_single_input_and_signed_zero():
    for family in ("linear", "gated_mlp"):
        for profile in range(2):
            batch = consumer.batch_data(family, profile)
            assert batch["shared_inputs"]
            assert all(list(item["inputs"]) == ["x"] for item in batch["requests"])
    for profile, expected_bits in ((0, 0x80000000), (1, 0)):
        batch = consumer.batch_data("product", profile)
        data = consumer.merged_input(batch, batch["requests"][1])
        result = consumer.reference("product", profile, data)["scores"][0]
        assert struct.pack("<f", result) == struct.pack("<I", expected_bits)
    graph = consumer.graph("product", 1)
    assert graph["operations"][0]["inputs"] == ["x", "x"]
    assert len(consumer.public_bindings(graph)[0]) == 1
    assert consumer.batch_data("product", 1)["shared_inputs"] == {}


def test_batch_digest_is_exact_canonical_no_newline_and_identity_sensitive():
    program = "a" * 64
    requests = [{"id": "first", "request_digest": "b" * 64},
                {"id": "last", "request_digest": "c" * 64}]
    expected = hashlib.sha256(json.dumps({
        "schema_version": "tuc.bounded_cpu_batch.v0", "program_digest": program,
        "requests": requests}, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False).encode("ascii")).hexdigest()
    assert consumer.batch_digest(program, requests) == expected
    assert consumer.batch_digest(program, list(reversed(requests))) != expected
    renamed = copy.deepcopy(requests)
    renamed[0]["id"] = "renamed"
    assert consumer.batch_digest(program, renamed) != expected
    assert consumer.batch_digest("d" * 64, requests) != expected


def test_variation_changes_batch_but_preserves_content_only_request_identities():
    base, variation = consumer.batch_data("linear", 0), consumer.varied_batch()
    inputs, _ = consumer.public_bindings(consumer.graph("linear", 0))
    program = "a" * 64
    def requests(batch):
        return [{"id": request["id"], "request_digest": consumer.request_digest(
            program, inputs, consumer.merged_input(batch, request))}
                for request in batch["requests"]]
    original, changed = requests(base), requests(variation)
    assert [item["id"] for item in changed] == ["renamed_2", "sample_0", "sample_1"]
    assert changed[0]["request_digest"] == original[2]["request_digest"]
    assert changed[1]["request_digest"] == original[0]["request_digest"]
    assert changed[2]["request_digest"] != original[1]["request_digest"]
    assert consumer.batch_digest(program, original) != consumer.batch_digest(program, changed)
    for request in variation["requests"]:
        data = consumer.merged_input(variation, request)
        expected = numpy_reference("linear", 0, data)
        actual = np.asarray(consumer.reference("linear", 0, data)["scores"], dtype=np.float32)
        np.testing.assert_array_equal(actual.view(np.uint32), expected.view(np.uint32))


def test_request_hash_has_one_physical_input_and_preserves_negative_zero():
    inputs, _ = consumer.public_bindings(consumer.graph("product", 1))
    batch = consumer.batch_data("product", 1)
    data = consumer.merged_input(batch, batch["requests"][1])
    payload = b"".join(struct.pack("<f", value) for value in data["inputs"]["x"])
    assert len(payload) == 6 * 4 and payload[:4] == b"\x00\x00\x00\x80"
    expected = hashlib.sha256(bytes.fromhex("a" * 64) + payload).hexdigest()
    assert consumer.request_digest("a" * 64, inputs, data) == expected


def test_candidate_emit_are_portable_inert_and_fixtures_have_complete_hashes(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("pure mode invoked a console")
    monkeypatch.setattr(consumer, "_invoke", forbidden)
    monkeypatch.setattr(consumer, "_installed_cli", forbidden)
    monkeypatch.setattr(consumer, "ROOT", tmp_path)
    report = consumer.candidate()
    assert report == consumer.candidate()
    assert report["native_execution_observed"] is False
    assert [report[key] for key in ("planned_batch_runs", "planned_request_runs",
                                   "planned_scalar_checks", "planned_negative_controls",
                                   "planned_numeric_rejections")] == [7, 21, 96, 6, 2]
    assert [report[key] for key in ("batch_runs", "request_runs", "scalar_checks",
                                   "negative_controls", "numeric_rejections")] == [0] * 5
    emitted = consumer.emit()
    root = Path(emitted["fixture_directory"])
    assert root.parent == tmp_path / "tmp"
    assert json.loads((root / "fixtures.json").read_bytes()) == emitted
    for program in report["programs"]:
        folder = root / program["id"]
        for filename, key in (("graph.json", "graph_sha256"), ("batch.json", "batch_sha256")):
            assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == program[key]
    assert hashlib.sha256((root / "varied-batch.json").read_bytes()).hexdigest() == (
        report["variation"]["batch_sha256"])
    assert not (root / "record.json").exists()


def test_consumer_imports_only_stdlib_and_never_evaluates_source():
    tree = ast.parse(Path(consumer.__file__).read_text(encoding="utf-8"))
    allowed = {"__future__", "argparse", "copy", "hashlib", "json", "math", "os", "re",
               "selectors", "signal", "stat", "struct", "subprocess", "sys", "tempfile", "time",
               "contextlib", "pathlib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(item.name in allowed for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module in allowed
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "compile", "__import__"}


def valid_batch_response(program, batch):
    results = []
    for request in batch["requests"]:
        data = consumer.merged_input(batch, request)
        results.append({"id": request["id"], "request_digest": consumer.request_digest(
            program["program_digest"], program["inputs"], data), "outputs": consumer.reference(
                program["family"], program["profile"], data)})
    return {"schema_version": consumer.OUTPUT_SCHEMA, "action": "run-batch",
            "program_digest": program["program_digest"],
            "batch_digest": consumer.batch_digest(program["program_digest"], results),
            "results": results, "native_execution_observed": True}


@pytest.mark.parametrize("change", ["program", "batch_digest", "order", "missing", "extra",
    "id", "request_digest", "output_name", "output_value", "integer", "signed_zero",
    "extra_result_field", "extra_field", "schema", "action", "native_bool"])
def test_batch_checker_rejects_forged_or_partial_responses(change):
    program = next(item for item in consumer.candidate()["programs"] if item["id"] == "product_0")
    program["program_digest"] = "a" * 64
    batch = consumer.batch_data("product", 0)
    value = valid_batch_response(program, batch)
    checked, _, count = consumer._check_batch((0, consumer.encoded(value), b""),
                                               program, batch, program["cases"])
    assert len(checked) == 3 and count == 15
    if change == "program":
        value["program_digest"] = "b" * 64
    elif change == "batch_digest":
        value["batch_digest"] = "b" * 64
    elif change == "order":
        value["results"].reverse()
    elif change == "missing":
        value["results"].pop()
    elif change == "extra":
        value["results"].append(value["results"][0])
    elif change in ("id", "request_digest"):
        value["results"][0][change] = "changed"
    elif change == "output_name":
        value["results"][0]["outputs"] = {"other": value["results"][0]["outputs"]["scores"]}
    elif change in ("output_value", "integer"):
        value["results"][0]["outputs"]["scores"][0] = 1.0 if change == "output_value" else 1
    elif change == "signed_zero":
        value["results"][1]["outputs"]["scores"][0] = 0.0
    elif change == "extra_result_field":
        value["results"][0]["extra"] = 0
    elif change == "extra_field":
        value["extra"] = 0
    elif change == "schema":
        value["schema_version"] = "unknown"
    elif change == "action":
        value["action"] = "run"
    else:
        value["native_execution_observed"] = 1
    with pytest.raises(ValueError):
        consumer._check_batch((0, consumer.encoded(value), b""), program, batch, program["cases"])


@pytest.mark.parametrize("raw", [b'{"x":0,"x":1}', b'{"x":NaN}', b'{"x":Infinity}'])
def test_response_decoder_rejects_duplicate_and_nonfinite_values(raw):
    with pytest.raises(ValueError):
        consumer._response((0, raw, b""))


@pytest.mark.parametrize("field", ("tensor_index", "shape"))
def test_inspect_rejects_boolean_integer_substitution(field):
    program = consumer.candidate()["programs"][1]
    value = {"schema_version": "tuc.bounded_cpu_cli.v0", "action": "inspect",
             "program_digest": "a" * 64, "inputs": copy.deepcopy(program["inputs"]),
             "outputs": copy.deepcopy(program["outputs"]), "native_execution_observed": False}
    assert consumer._inspect((0, consumer.encoded(value), b""), program) == "a" * 64
    if field == "tensor_index":
        assert value["inputs"][1][field] == 1
        value["inputs"][1][field] = True
    else:
        assert value["inputs"][0][field][0] == 1
        value["inputs"][0][field][0] = True
    with pytest.raises(ValueError, match="binding"):
        consumer._inspect((0, consumer.encoded(value), b""), program)


def test_numeric_controls_fail_after_one_or_two_valid_requests():
    for case, expected_bits in zip(consumer.numeric_cases(), (0x7f800000, 0), strict=True):
        bad_index = case["request_index"]
        assert bad_index in (1, 2)
        for index, request in enumerate(case["batch"]["requests"]):
            data = consumer.merged_input(case["batch"], request)
            if index == bad_index:
                number = np.float32(data["inputs"]["x"][0])
                bits = int(number.view(np.uint32)) & 0x7fffffff
                assert 0 < bits & 0x7f800000 < 0x7f800000
                with np.errstate(over="ignore", under="ignore"):
                    result = np.multiply(number, number, dtype=np.float32)
                assert int(result.view(np.uint32)) == expected_bits
                with pytest.raises((ValueError, OverflowError)):
                    consumer.reference("product", 1, data)
            else:
                assert consumer.reference("product", 1, data)


def test_negative_corpus_has_distinct_late_and_structural_errors():
    cases = {case["id"]: case for case in consumer.negative_cases()}
    assert set(cases) == {"bad_last_input", "duplicate_ids", "shared_overlap", "wrong_shape",
                          "malformed_json", "max17"}
    assert all(case["reason"] == "batch_json_rejected" for case in cases.values())
    late = json.loads(cases["bad_last_input"]["data"])
    assert late["requests"][-1]["inputs"] == {}
    assert all(request["inputs"]["x"] for request in late["requests"][:-1])
    assert len(json.loads(cases["max17"]["data"])["requests"]) == 17
    with pytest.raises(ValueError):
        json.loads(cases["malformed_json"]["data"])


@pytest.mark.parametrize("wrong", ((2, b"partial", b"tuc-cpu-app: batch_json_rejected\n"),
                                   (0, b"", b""), (2, b"", b"tuc-cpu-app: file_rejected\n")))
def test_rejection_driver_requires_exact_status_empty_stdout_and_reason(
        monkeypatch, tmp_path, wrong):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(consumer, "_invoke", lambda *args: wrong)
    with pytest.raises(ValueError, match="bad_last_input"):
        consumer._controls(Path("not-executed"), tmp_path, workspace, {}, [])


def test_context_guard_detects_changed_graph_and_unclean_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    graph = tmp_path / "graph.json"
    graph.write_bytes(b"original")
    consumer._unchanged({graph: b"original"}, workspace)
    graph.write_bytes(b"changed")
    with pytest.raises(ValueError, match="original"):
        consumer._unchanged({graph: b"original"}, workspace)
    graph.write_bytes(b"original")
    (workspace / "leftover").write_bytes(b"x")
    with pytest.raises(ValueError, match="resources"):
        consumer._unchanged({graph: b"original"}, workspace)


def test_mock_driver_full_coverage_writes_only_complete_record(monkeypatch, tmp_path):
    """Synthetic responses validate driver wiring; this supplies no execution evidence."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(consumer, "_installed_cli", lambda: Path("never-executed"))
    calls = []
    def invoke(executable, arguments):
        calls.append(arguments)
        if arguments[0] == "inspect":
            source = json.loads(Path(arguments[1]).read_bytes())
            inputs, outputs = consumer.public_bindings(source)
            return 0, consumer.encoded({"schema_version": "tuc.bounded_cpu_cli.v0",
                "action": "inspect", "program_digest": consumer.digest(consumer.encoded(source)),
                "inputs": inputs, "outputs": outputs, "native_execution_observed": False}), b""
        batch_path = Path(arguments[3])
        if batch_path.name.startswith("negative-"):
            return 2, b"", b"tuc-cpu-app: batch_json_rejected\n"
        if batch_path.name.startswith("numeric-"):
            return 1, b"", b"tuc-cpu-app: numeric_rejection\n"
        source = json.loads(Path(arguments[1]).read_bytes())
        program = next(item for item in consumer.candidate()["programs"]
                       if source["name"] == "batch_" + item["id"])
        program["program_digest"] = consumer.digest(consumer.encoded(source))
        return 0, consumer.encoded(valid_batch_response(
            program, json.loads(batch_path.read_bytes()))), b""
    monkeypatch.setattr(consumer, "_invoke", invoke)
    report = consumer.run()
    assert len(calls) == 6 + 7 + 6 + 2
    assert [report[key] for key in ("batch_runs", "request_runs", "scalar_checks",
                                   "negative_controls", "numeric_rejections")] == [7, 21, 96, 6, 2]
    assert report["original_files_unchanged"] is True and report["workspaces_clean"] is True
    assert json.loads((tmp_path / "record.json").read_bytes()) == report
