"""Pure generation and synthetic receipt tests; these are not native observations."""

from __future__ import annotations

import ast
import json
import math
import re
import struct
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_dag_compiler import consumer as original
from integration.bounded_source_c11 import consumer as proof

_INPUT_SHAPES = {"a": (3, 2), "b": (2, 4), "c": (4, 3), "d": (3, 2)}


def _copy_consumer_root(destination):
    """Prepare a synthetic install-side context; its wheel identifier is a fixture."""

    source = Path(proof.__file__).resolve().parent
    for name in ("consumer.py", "Dockerfile", "Dockerfile.dockerignore", "build.sh", "operator.sh"):
        (destination / name).write_bytes((source / name).read_bytes())
    (destination / "wheel-sha256.txt").write_bytes(("sha256:" + "a" * 64 + "\n").encode())


@pytest.fixture(autouse=True)
def synthetic_consumer_root(monkeypatch, tmp_path):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    directory = tmp_path_factory.mktemp("source_c11_artifacts")
    _copy_consumer_root(directory)
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(proof, "ROOT", directory.resolve())
        return proof.artifact_files()


def _numpy_product(left, right):
    """Independent ordered FP32 arithmetic, without BLAS, FMA or code generation."""

    result = np.zeros((left.shape[0], right.shape[1]), dtype=np.float32)
    for inner in range(left.shape[1]):
        product = np.multiply(left[:, inner, None], right[inner, None, :], dtype=np.float32)
        result = np.add(result, product, dtype=np.float32)
    return result


def _numpy_rows(value):
    result = np.zeros(value.shape[0], dtype=np.float32)
    for column in range(value.shape[1]):
        result = np.add(result, value[:, column], dtype=np.float32)
    return result


def _independent_outputs(inputs):
    arrays = {
        name: np.asarray(inputs[name], dtype=np.float32).reshape(shape)
        for name, shape in _INPUT_SHAPES.items()
    }
    left = _numpy_product(arrays["a"], arrays["b"])
    right = _numpy_product(arrays["c"], arrays["d"])
    joined = _numpy_product(
        np.maximum(left, np.float32(0.0)), np.maximum(right, np.float32(0.0)),
    )
    return {"branch_total": _numpy_rows(left), "joined_total": _numpy_rows(joined)}


@pytest.mark.parametrize("case", range(3))
def test_reference_matches_independent_ordered_fp32_arithmetic(case):
    inputs = proof.fixed_inputs(case)
    assert set(inputs) == set(_INPUT_SHAPES)
    for name, shape in _INPUT_SHAPES.items():
        assert len(inputs[name]) == math.prod(shape)
        assert all(math.isfinite(value) for value in inputs[name])
    expected = _independent_outputs(inputs)
    actual = proof.reference_outputs(case)
    assert set(actual) == set(expected)
    for name in expected:
        assert len(actual[name]) == 3
        np.testing.assert_array_equal(np.asarray(actual[name], dtype=np.float32), expected[name])


def test_source_and_cpu_bindings_match_the_installed_metadata_consumer():
    result = proof.compile_cpu()
    previous = original.compile_profile("cpu")
    assert proof.source_module() == original.source_module()
    assert proof.backend_bindings() == original.backend_bindings("cpu")
    assert result.source_intent_digest == previous.source_intent_digest
    assert result.backend_bindings_digest == previous.backend_bindings_digest
    assert result.compilation.hac_ir == previous.compilation.hac_ir
    assert result.input_bindings == previous.input_bindings
    assert result.output_bindings == previous.output_bindings
    assert result.artifacts.c11_header == previous.artifacts.c11_header
    assert result.artifacts.c11_source == previous.artifacts.c11_source
    assert [(binding.public_name, binding.shape) for binding in result.input_bindings] == [
        (name, shape) for name, shape in _INPUT_SHAPES.items()
    ]
    assert [(binding.public_name, binding.shape) for binding in result.output_bindings] == [
        ("branch_total", (3,)), ("joined_total", (3,)),
    ]


def test_reference_does_not_use_compiler_or_manifest(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("independent oracle must not inspect compiler metadata")

    monkeypatch.setattr(proof, "compile_cpu", deny)
    monkeypatch.setattr(proof, "source_module", deny)
    monkeypatch.setattr(proof, "compile_bounded_source_intent", deny)
    for case in range(3):
        expected = _independent_outputs(proof.fixed_inputs(case))
        for name, actual in proof.reference_outputs(case).items():
            np.testing.assert_array_equal(np.asarray(actual, dtype=np.float32), expected[name])


@pytest.mark.parametrize("field", ("c11_header", "c11_source", "schedule_header", "manifest_json"))
def test_changed_compiler_text_is_rejected_before_emission(monkeypatch, tmp_path, field):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    result = proof.compile_cpu()
    changed_artifacts = replace(result.artifacts, **{
        field: getattr(result.artifacts, field) + "\n/* synthetic alteration */",
    })
    changed = replace(result, artifacts=changed_artifacts)
    monkeypatch.setattr(proof, "compile_bounded_source_intent", lambda *args, **kwargs: changed)
    with pytest.raises(ValueError):
        proof.emit_context()
    assert not (tmp_path / "tmp").exists()


def test_pure_generation_is_deterministic_and_never_launches_native_code(
    monkeypatch, tmp_path, artifacts,
):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())

    def deny(*args, **kwargs):
        pytest.fail("Python consumer must not execute a native program")

    monkeypatch.setattr(subprocess, "Popen", deny)
    assert proof.artifact_files() == artifacts
    assert proof.report(artifacts) == proof.report(artifacts)
    report = proof.report(artifacts)
    assert report["native_execution_observed"] is False
    assert report["normal_runtime_admission"] is False
    assert report["cuda_execution_observed"] is False
    assert str(tmp_path) not in json.dumps(report)
    assert artifacts["generated.c"] == proof.compile_cpu().artifacts.c11_source
    assert artifacts["generated.h"] == proof.compile_cpu().artifacts.c11_header


def test_generated_dispatch_and_allocations_match_typed_manifest(artifacts):
    result = proof.compile_cpu()
    manifest = json.loads(artifacts["manifest.json"])
    source = artifacts["worker.c"]
    calls = re.findall(r"tuc_dag_op_(\d+)\(([^;]+)\);", source)
    expected_calls = []
    for event in manifest["events"]:
        if event["kind"] == "execute":
            args = ", ".join(f"slot_{slot}" for slot in (*event["inputs"], *event["outputs"]))
            expected_calls.append((str(event["operation"]), args))
    assert calls == expected_calls
    allocations = re.findall(r"float slot_(\d+)\[(\d+)\];", source)
    assert allocations == [(str(buffer["index"]), str(buffer["bytes"] // 4))
                           for buffer in manifest["buffers"]]
    for event in manifest["events"]:
        if event["kind"] == "bind_input":
            slot = event["outputs"][0]
            buffer = manifest["buffers"][slot]
            assert (f"tuc_bind(slot_{slot}, input_{buffer['tensor']}[vector], "
                    f"{buffer['bytes'] // 4}U);") in source
    assert len(calls) == 7 and len(allocations) == 11
    assert "unsigned char ready[11] = {0};" in source
    assert sum(event["kind"] == "publish_output" for event in manifest["events"]) == 2
    assert "return publications == 2U ? 0 : 3;" in source
    for binding in result.output_bindings:
        assert f"expected_{binding.tensor_index}[vector], 3U, counts)" in source


def test_generated_corpus_bits_match_public_inputs_and_independent_outputs(artifacts):
    result = proof.compile_cpu()
    arrays = re.findall(
        r"static const uint32_t (input|expected)_(\d+)\[3\]\[(\d+)\] = \{([^;]+)\};",
        artifacts["worker.c"],
    )
    assert len(arrays) == 6
    inputs = {binding.tensor_index: binding for binding in result.input_bindings}
    outputs = {binding.tensor_index: binding for binding in result.output_bindings}
    for kind, tensor, width, text in arrays:
        tensor, width = int(tensor), int(width)
        bits = [int(value, 16) for value in re.findall(r"UINT32_C\(0x([0-9a-f]{8})\)", text)]
        assert len(bits) == 3 * width
        binding = inputs[tensor] if kind == "input" else outputs[tensor]
        assert width == math.prod(binding.shape)
        for case in range(3):
            values = (proof.fixed_inputs(case)[binding.public_name] if kind == "input" else
                      _independent_outputs(proof.fixed_inputs(case))[binding.public_name])
            expected_bits = [struct.unpack("<I", struct.pack("<f", value))[0] for value in values]
            assert bits[case * width:(case + 1) * width] == expected_bits


def test_c_printf_strings_decode_to_exact_json_receipts_without_execution(artifacts):
    groups = re.findall(r'printf\(((?:"(?:\\.|[^"\\])*"\s*)+)', artifacts["worker.c"])
    assert len(groups) == 1
    pattern = "".join(ast.literal_eval(token)
                      for token in re.findall(r'"(?:\\.|[^"\\])*"', groups[0]))
    assert pattern.endswith("\n") and "\\n" not in pattern
    binding = re.search(r'#define TUC_SOURCE_BINDING "(sha256:[0-9a-f]{64})"',
                        artifacts["worker.c"]).group(1)
    for fault, invalid in [*((fault, False) for fault in range(14)), (0, True)]:
        expected = proof.expected_receipt(fault, invalid)
        assert expected["binding_digest"] == binding
        values = (expected["status"], expected["reason"], binding, fault,
                  *(expected[name] for name in ("case_runs", "function_calls", "scalar_checks",
                                               "published_outputs", "rejected_cases")))
        decoded = json.loads(pattern.replace("%zu", "%d") % values)
        assert proof.validate_receipt(decoded, fault, invalid) == expected


def test_worker_requires_numeric_environment_identity_and_deadline(artifacts):
    source = artifacts["worker.c"]
    assert "#if !defined(__x86_64__) || !defined(__SSE2__)" in source
    assert "fegetround() != FE_TONEAREST" in source
    assert "(_mm_getcsr() & UINT32_C(0xe040)) != 0U" in source
    assert "(void)alarm(20U);" in source
    for identity in ("getuid", "geteuid", "getgid", "getegid"):
        assert f"{identity}() != 10001U" in source
    assert source.index("fegetround()") < source.index("tuc_run(vector, &counts)")
    assert "vector < 3U" in source and "replay < 2U" in source
    assert "category != FP_NORMAL && category != FP_ZERO" in source
    for fault in range(1, 8):
        assert f"TUC_SOURCE_FAULT != {fault})" in source
    for fault in (8, 9, 12, 13):
        assert f"TUC_SOURCE_FAULT == {fault}" in source
    assert "tuc_poison(slot_9 + 2U, 1U)" in source


def test_artifact_context_binds_consumer_wheel_and_compiler_sources(artifacts):
    bindings = json.loads(artifacts["source-bindings.json"])
    previous = original.compile_profile("cpu")
    assert bindings["source_intent_digest"] == previous.source_intent_digest
    assert bindings["backend_bindings_digest"] == previous.backend_bindings_digest
    assert bindings["wheel_digest"] == "sha256:" + "a" * 64
    assert len(bindings["package_sources"]) == 22
    assert "compiler/bounded_source.py" in bindings["package_sources"]
    assert "backends/bounded_dag_codegen.py" in bindings["package_sources"]
    for digest in (bindings["consumer_digest"], *bindings["package_sources"].values()):
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
    allowlist = artifacts["Dockerfile.dockerignore"].splitlines()
    assert allowlist[0] == "**"
    assert "!consumer.py" not in allowlist and "!operator.sh" not in allowlist


def test_consumer_imports_only_installed_package_and_stdlib():
    tree = ast.parse(Path(proof.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            assert not (isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"})
    assert imports <= sys.stdlib_module_names | {"tuc"}
    assert not imports & {"examples", "integration", "subprocess", "ctypes", "socket"}


@pytest.mark.parametrize("fault", range(14))
def test_synthetic_receipt_checks_every_field_exactly(fault):
    # These records are synthetic protocol fixtures, never observed execution evidence.
    value = proof.expected_receipt(fault)
    assert proof.validate_receipt(value, fault) == value
    for key in value:
        changed = deepcopy(value)
        changed[key] = "not_the_expected_value"
        with pytest.raises(ValueError):
            proof.validate_receipt(changed, fault)
        missing = deepcopy(value)
        del missing[key]
        with pytest.raises(ValueError):
            proof.validate_receipt(missing, fault)
    with pytest.raises(ValueError):
        proof.validate_receipt({**value, "unexpected": 1}, fault)
    if fault != 0:
        with pytest.raises(ValueError):
            proof.validate_receipt(value)


@pytest.mark.parametrize("replacement", (True, False, 0.0, 1.0, "0", None, [], {}))
def test_receipt_integer_counts_reject_type_confusion(replacement):
    expected = proof.expected_receipt()
    counts = [key for key, value in expected.items() if type(value) is int]
    assert counts
    for key in counts:
        value = {**expected, key: replacement}
        with pytest.raises(ValueError):
            proof.validate_receipt(value)


@pytest.mark.parametrize("value", ([], None, True, 0, "PASS"))
def test_receipt_requires_an_exact_object(value):
    with pytest.raises(ValueError):
        proof.validate_receipt(value)


@pytest.mark.parametrize("text", (
    '{"status":"FAIL","status":"PASS"}',
    '{"outer":{"a":1,"a":2}}',
    '{"status":"PASS"} trailing',
    '{"status":',
))
def test_receipt_parser_rejects_duplicate_or_malformed_json(text):
    with pytest.raises(ValueError):
        proof._receipt_json(text)


@pytest.mark.parametrize("number", ("NaN", "Infinity", "-Infinity", "1e400", "-1e400"))
def test_receipt_parser_rejects_nonfinite_numbers(number):
    with pytest.raises(ValueError):
        proof._receipt_json('{"number":' + number + "}")


def test_receipt_parser_has_explicit_byte_depth_and_item_budgets():
    with pytest.raises(ValueError):
        proof._receipt_json(" " * (proof.MAX_RECEIPT_BYTES + 1))
    with pytest.raises(ValueError):
        proof._receipt_json("[" * (proof.MAX_RECEIPT_DEPTH + 1) + "0" +
                            "]" * (proof.MAX_RECEIPT_DEPTH + 1))
    with pytest.raises(ValueError):
        proof._receipt_json("[" + ",".join("0" for _ in range(proof.MAX_RECEIPT_ITEMS + 1)) + "]")
    quoted = {"brackets": '[{{,::"escaped"\\]]'}
    assert proof._receipt_json(json.dumps(quoted)) == quoted


@pytest.mark.parametrize("text", (None, b"{}", [], 4))
def test_receipt_parser_rejects_nontext_inputs(text):
    with pytest.raises(ValueError):
        proof._receipt_json(text)


def test_synthetic_receipt_counters_cover_every_replay_scalar_and_return():
    baseline = proof.expected_receipt()
    assert baseline["case_runs"] == 6
    assert baseline["function_calls"] == 42
    assert baseline["scalar_checks"] == 36
    assert baseline["published_outputs"] == 12
    assert baseline["rejected_cases"] == 0
    for fault in range(1, 14):
        rejected = proof.expected_receipt(fault)
        assert rejected["rejected_cases"] == 6
        assert rejected["fault"] == fault
    invalid = proof.expected_receipt(invalid=True)
    assert proof.validate_receipt(invalid, invalid=True) == invalid
    with pytest.raises(ValueError):
        proof.validate_receipt(invalid)


def test_fault_counters_match_independent_fixed_application_analysis():
    # Per replay: skipping an op stops at its first consumer/publication; faults
    # 7/9/10/11 finish the other public return, and fault13 checks two scalars.
    expected_per_replay = (
        (1, 0, 0), (2, 0, 0), (3, 0, 0), (3, 0, 0), (5, 0, 0), (6, 0, 0),
        (6, 3, 1), (7, 0, 0), (7, 3, 1), (7, 3, 1), (7, 3, 1), (7, 0, 0),
        (7, 2, 0),
    )
    for fault, (calls, checks, publications) in enumerate(expected_per_replay, 1):
        receipt = proof.expected_receipt(fault)
        assert receipt["function_calls"] == calls * 6
        assert receipt["scalar_checks"] == checks * 6
        assert receipt["published_outputs"] == publications * 6
        assert receipt["case_runs"] == 0 and receipt["rejected_cases"] == 6


@pytest.mark.parametrize("fault", (-1, 14, True, False, 0.0, "0", None))
def test_fault_selector_requires_bounded_exact_integer(fault):
    with pytest.raises(ValueError):
        proof.expected_receipt(fault)


@pytest.mark.parametrize("case", (-1, 3, True, 0.0, "0", None))
def test_input_corpus_requires_bounded_exact_integer(case):
    with pytest.raises(ValueError):
        proof.fixed_inputs(case)
    with pytest.raises(ValueError):
        proof.reference_outputs(case)


def _synthetic_context(monkeypatch, tmp_path):
    """Receipt-shaped fixtures exercise validation only, not native execution."""

    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    path = proof.emit_context()
    for build in ("static", "sanitized"):
        (path / f"{build}-image-id.txt").write_text("sha256:" + "b" * 64 + "\n")
        for fault in range(14):
            name = "proof" if fault == 0 else f"fault{fault}"
            (path / f"{build}-{name}.json").write_text(json.dumps(proof.expected_receipt(fault)))
        (path / f"{build}-invalid.json").write_text(
            json.dumps(proof.expected_receipt(invalid=True)),
        )
    return path


def test_exclusive_context_emission_preserves_previous_files(monkeypatch, tmp_path):
    first = _synthetic_context(monkeypatch, tmp_path)
    second = proof.emit_context()
    assert first != second
    assert first.parent == second.parent == tmp_path / "tmp"
    assert (first / "static-proof.json").is_file()
    assert not (second / "static-proof.json").exists()
    assert (first / "generated.c").read_bytes() == (second / "generated.c").read_bytes()


def test_synthetic_complete_receipts_validate_only_the_protocol(monkeypatch, tmp_path):
    path = _synthetic_context(monkeypatch, tmp_path)
    record = proof.accept(path)
    assert record["normal_runtime_admission"] is False
    assert record["cuda_execution_observed"] is False
    assert len(record["observations"]) == 30
    # Do not publish this synthetic fixture or treat its record as an observation.


def test_old_synthetic_receipts_cannot_validate_a_regenerated_changed_context(
    monkeypatch, tmp_path,
):
    old = _synthetic_context(monkeypatch, tmp_path)
    receipt_names = [path.name for path in old.iterdir()
                     if path.name.startswith(("static-", "sanitized-"))]
    old_binding = json.loads((old / "static-proof.json").read_text())["binding_digest"]
    support = tmp_path / "operator.sh"
    support.write_bytes(support.read_bytes() + b"\n# changed isolation source fixture\n")
    fresh = proof.emit_context()
    assert proof.expected_receipt()["binding_digest"] != old_binding
    for name in receipt_names:
        (fresh / name).write_bytes((old / name).read_bytes())
    with pytest.raises(ValueError):
        proof.accept(fresh)


@pytest.mark.parametrize("name", ("generated.c", "generated.h", "worker.c", "source-bindings.json",
                                  "operator.sh", "wheel-sha256.txt"))
def test_accept_rejects_changed_context_sources(monkeypatch, tmp_path, name):
    path = _synthetic_context(monkeypatch, tmp_path)
    (path / name).write_text("synthetic alteration", encoding="utf-8")
    with pytest.raises(ValueError):
        proof.accept(path)


@pytest.mark.parametrize("name", ("consumer.py", "operator.sh", "wheel-sha256.txt"))
def test_accept_rebinds_current_consumer_support_and_wheel_identity(monkeypatch, tmp_path, name):
    path = _synthetic_context(monkeypatch, tmp_path)
    target = tmp_path / name
    if name == "wheel-sha256.txt":
        target.write_text("sha256:" + "c" * 64 + "\n", encoding="utf-8")
    else:
        target.write_bytes(target.read_bytes() + b"\n# synthetic alteration\n")
    with pytest.raises(ValueError):
        proof.accept(path)


@pytest.mark.parametrize("receipt", ("static-proof.json", "static-fault13.json",
                                     "sanitized-fault1.json", "sanitized-invalid.json"))
def test_accept_requires_baseline_every_control_and_invalid_invocation(
    monkeypatch, tmp_path, receipt,
):
    path = _synthetic_context(monkeypatch, tmp_path)
    (path / receipt).unlink()
    with pytest.raises(ValueError):
        proof.accept(path)


@pytest.mark.parametrize("kind", ("file", "directory"))
def test_accept_rejects_unlisted_context_entries(monkeypatch, tmp_path, kind):
    path = _synthetic_context(monkeypatch, tmp_path)
    extra = path / "unexpected"
    if kind == "file":
        extra.write_text("unapproved", encoding="utf-8")
    else:
        extra.mkdir()
    with pytest.raises(ValueError):
        proof.accept(path)


def test_accept_allows_the_operator_record_redirection_placeholder(monkeypatch, tmp_path):
    path = _synthetic_context(monkeypatch, tmp_path)
    (path / "record.json").write_bytes(b"")
    assert len(proof.accept(path)["observations"]) == 30


@pytest.mark.parametrize("contents", (" " * 4097, '{"status":"FAIL","status":"PASS"}',
                                     '[true]', '{"x":NaN}'),
                         ids=("oversized", "duplicate", "wrong_shape", "nonfinite"))
def test_accept_rejects_invalid_receipt_files(monkeypatch, tmp_path, contents):
    path = _synthetic_context(monkeypatch, tmp_path)
    (path / "static-proof.json").write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        proof.accept(path)


@pytest.mark.parametrize("identity", ("", "sha256:abcd", "not-an-image", "sha256:" + "A" * 64))
def test_accept_rejects_malformed_image_identity(monkeypatch, tmp_path, identity):
    path = _synthetic_context(monkeypatch, tmp_path)
    (path / "static-image-id.txt").write_text(identity, encoding="utf-8")
    with pytest.raises(ValueError):
        proof.accept(path)


def test_accept_rejects_context_directory_escape_and_wrong_name(monkeypatch, tmp_path):
    path = _synthetic_context(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        proof.accept(tmp_path)
    with pytest.raises(ValueError):
        proof.accept(path.parent)
    renamed = path.with_name("unapproved-context-name")
    path.rename(renamed)
    with pytest.raises(ValueError):
        proof.accept(renamed)


def test_emission_rejects_file_instead_of_parent_directory(monkeypatch, tmp_path):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    (tmp_path / "tmp").write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError):
        proof.emit_context()


@pytest.mark.parametrize("name", ("MAX_FILE_BYTES", "MAX_CONTEXT_BYTES"))
def test_generation_enforces_context_resource_budgets(monkeypatch, tmp_path, name):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    monkeypatch.setattr(proof, name, 32)
    with pytest.raises(ValueError):
        proof.emit_context()
    assert not (tmp_path / "tmp").exists()


@pytest.mark.parametrize("identity", ("", "sha256:abcd", "sha256:" + "G" * 64,
                                     "sha256:" + "0" * 65, " " * 4097),
                         ids=("empty", "short", "nonhex", "long", "oversized"))
def test_generation_rejects_invalid_wheel_identity(monkeypatch, tmp_path, identity):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    (tmp_path / "wheel-sha256.txt").write_text(identity, encoding="utf-8")
    with pytest.raises(ValueError):
        proof.emit_context()
    assert not (tmp_path / "tmp").exists()


def test_generation_requires_wheel_identity_sidecar(monkeypatch, tmp_path):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    (tmp_path / "wheel-sha256.txt").unlink()
    with pytest.raises(ValueError):
        proof.artifact_files()


def test_emission_rejects_symlink_parent(monkeypatch, tmp_path):
    _copy_consumer_root(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())
    destination = tmp_path / "outside"
    destination.mkdir()
    try:
        (tmp_path / "tmp").symlink_to(destination, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable for this host account")
    with pytest.raises(ValueError):
        proof.emit_context()
    assert list(destination.iterdir()) == []


@pytest.mark.parametrize("name", ("worker.c", "static-proof.json"))
def test_accept_rejects_symlink_source_or_receipt(monkeypatch, tmp_path, name):
    path = _synthetic_context(monkeypatch, tmp_path)
    target = path / name
    external = tmp_path / "same-content.txt"
    external.write_bytes(target.read_bytes())
    target.unlink()
    try:
        target.symlink_to(external)
    except OSError:
        pytest.skip("file symlinks unavailable for this host account")
    with pytest.raises(ValueError):
        proof.accept(path)
