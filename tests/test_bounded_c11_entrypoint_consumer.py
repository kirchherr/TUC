"""Pure entrypoint conformance generation and synthetic protocol tests.

No test compiles or executes generated native code. Synthetic receipts only
exercise the verifier and must not be published as execution observations.
"""
from __future__ import annotations

import ast
import json
import math
import re
import struct
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_c11_entrypoint import consumer as proof
from integration.bounded_dag_compiler import consumer as original


def _prepare(directory):
    source = Path(proof.__file__).resolve().parent
    for name in ("consumer.py", *proof.SUPPORT_FILES):
        (directory / name).write_bytes((source / name).read_bytes())
    (directory / "wheel-sha256.txt").write_bytes(("sha256:" + "a" * 64 + "\n").encode())


@pytest.fixture(autouse=True)
def synthetic_root(monkeypatch, tmp_path):
    _prepare(tmp_path)
    monkeypatch.setattr(proof, "ROOT", tmp_path.resolve())


@pytest.fixture(scope="module")
def artifacts(tmp_path_factory):
    directory = tmp_path_factory.mktemp("entrypoint_artifacts")
    _prepare(directory)
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(proof, "ROOT", directory.resolve())
        return proof.artifact_files()


def _product(a, b):
    result = np.zeros((a.shape[0], b.shape[1]), dtype=np.float32)
    for inner in range(a.shape[1]):
        result = np.add(result, np.multiply(a[:, inner, None], b[inner, None, :],
                                           dtype=np.float32), dtype=np.float32)
    return result


def _rows(a):
    result = np.zeros(a.shape[0], dtype=np.float32)
    for column in range(a.shape[1]):
        result = np.add(result, a[:, column], dtype=np.float32)
    return result


def _independent(graph, inputs):
    if graph == "tiny":
        left = np.asarray(inputs["left"], dtype=np.float32).reshape(1, 2)
        right = np.asarray(inputs["right"], dtype=np.float32).reshape(2, 1)
        return {"tiny_total": _rows(_product(left, right))}
    shapes = {"a": (3, 2), "b": (2, 4), "c": (4, 3), "d": (3, 2)}
    values = {name: np.asarray(inputs[name], dtype=np.float32).reshape(shape)
              for name, shape in shapes.items()}
    left, right = _product(values["a"], values["b"]), _product(values["c"], values["d"])
    joined = _product(np.maximum(left, np.float32(0)), np.maximum(right, np.float32(0)))
    return {"branch_total": _rows(left), "joined_total": _rows(joined)}


@pytest.mark.parametrize("graph", ("app", "tiny"))
@pytest.mark.parametrize("case", range(3))
def test_reference_matches_independent_ordered_fp32_math(graph, case):
    inputs = proof.fixed_inputs(graph, case)
    actual = proof.reference_outputs(graph, case)
    expected = _independent(graph, inputs)
    assert actual.keys() == expected.keys()
    for name in actual:
        np.testing.assert_array_equal(np.asarray(actual[name], dtype=np.float32), expected[name])
        assert all(math.isfinite(value) for value in actual[name])
    if graph == "app":
        assert actual["branch_total"][0] != actual["joined_total"][0]


def test_original_application_source_bindings_and_unique_tiny_entrypoint():
    app, app_entry = proof.compile_graph("app")
    tiny, tiny_entry = proof.compile_graph("tiny")
    previous = original.compile_profile("cpu")
    assert proof.source_module("app") == original.source_module()
    assert app.source_intent_digest == previous.source_intent_digest
    assert app.backend_bindings_digest == previous.backend_bindings_digest
    assert app.input_bindings == previous.input_bindings
    assert app.output_bindings == previous.output_bindings
    assert app_entry.entrypoint_symbol != tiny_entry.entrypoint_symbol
    assert [(b.public_name, b.shape) for b in tiny.input_bindings] == [
        ("left", (1, 2)), ("right", (2, 1)),
    ]
    assert [(b.public_name, b.shape) for b in tiny.output_bindings] == [("tiny_total", (1,))]


def test_python_client_has_no_native_loader_or_runner(monkeypatch, artifacts):
    def deny(*args, **kwargs):
        pytest.fail("native process launched by inert Python consumer")

    monkeypatch.setattr(subprocess, "Popen", deny)
    assert proof.artifact_files() == artifacts
    report = proof.report(artifacts)
    assert report["native_execution_observed"] is False
    assert report["cuda_execution_observed"] is False
    assert report["normal_runtime_admission"] is False
    tree = ast.parse(Path(proof.__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imports.add(node.module.split(".")[0])
    assert imports <= sys.stdlib_module_names | {"tuc"}
    assert not imports & {"subprocess", "ctypes", "socket", "examples", "integration"}


def test_worker_calls_only_two_public_entrypoints_and_preserves_canonical_sources(artifacts):
    source = artifacts["worker.c"]
    assert "tuc_dag_op_" not in source and "tuc_dag_cuda" not in source
    assert source.count("test->run(") == 2
    assert artifacts["entrypoint.h"] == (
        '#include "app-entrypoint.h"\n#include "tiny-entrypoint.h"\n'
    )
    for graph in proof.GRAPHS:
        _, entrypoint = proof.compile_graph(graph)
        assert source.count(entrypoint.entrypoint_symbol) == 1
        for name, text in entrypoint.files().items():
            assert artifacts[f"{graph}-{name}"] == text


def test_generated_corpus_follows_public_binding_order(artifacts):
    source = artifacts["worker.c"]
    arrays = re.findall(
        r"static const uint32_t (app|tiny)_(in|out)_(\d+)\[3\]\[(\d+)\] = \{([^;]+)\};",
        source,
    )
    assert len(arrays) == 9
    for graph, kind, tensor, width, text in arrays:
        compilation, _ = proof.compile_graph(graph)
        bindings = compilation.input_bindings if kind == "in" else compilation.output_bindings
        binding = next(binding for binding in bindings if binding.tensor_index == int(tensor))
        width = int(width)
        assert width == math.prod(binding.shape)
        bits = [int(value, 16) for value in re.findall(r"UINT32_C\(0x([0-9a-f]{8})\)", text)]
        assert len(bits) == width * 3
        for case in range(3):
            inputs = proof.fixed_inputs(graph, case)
            values = inputs[binding.public_name] if kind == "in" else (
                _independent(graph, inputs)[binding.public_name]
            )
            expected = [struct.unpack("<I", struct.pack("<f", value))[0] for value in values]
            assert bits[case * width:(case + 1) * width] == expected


def test_worker_controls_and_preservation_guards_cover_declared_boundaries(artifacts):
    source = artifacts["worker.c"]
    assert len(proof.CONTROL_NAMES) == proof.CONTROL_COUNT == 34
    assert [int(value) for value in re.findall(r"case (\d+):", source)] == list(range(34))
    assert "graph == 1U && control == 12U" in source
    assert "control < 34U" in source and "replay < 2U" in source
    for required in ("input_before", "inputs_before", "outputs_before"):
        assert source.count(f"memcmp({required},") == 2
    assert "j = test->output_sizes[i]; j < 3U" in source
    assert "UINTPTR_C" not in source
    assert source.count("UINTPTR_MAX - (uintptr_t)3U") == 2
    for constant in ("0x7f800001", "0x7f800000", "0x00800000", "0x00800001", "0x80800000"):
        assert constant in source
    assert "fesetround(saved_round)" in source and "_mm_setcsr(saved_csr);" in source
    assert "(csr & UINT32_C(0x1f80)) != UINT32_C(0x1f80)" in source
    assert "(void)alarm(20U);" in source


def test_numeric_controls_are_normal_operands_with_hidden_invalid_intermediates():
    def f32(bits):
        return struct.unpack("<f", struct.pack("<I", bits))[0]

    minimum, next_normal = f32(0x00800000), f32(0x00800001)
    assert minimum * 0.5 < minimum and minimum * 0.5 != 0
    assert np.float32(minimum * minimum) == 0
    assert next_normal - minimum == f32(1)
    assert np.float32(np.float32(next_normal - minimum) + np.float32(1)) == 1


@pytest.mark.parametrize(
    "fault,invalid", ((0, False), (1, False), (2, False), (3, False), (0, True)),
)
def test_synthetic_receipt_exact_fields_and_decoded_c_printf(artifacts, fault, invalid):
    expected = proof.expected_receipt(fault, invalid)
    assert proof.validate_receipt(expected, fault, invalid) == expected
    for key in expected:
        changed = {**expected, key: "changed"}
        with pytest.raises(ValueError):
            proof.validate_receipt(changed, fault, invalid)
        with pytest.raises(ValueError):
            proof.validate_receipt({name: value for name, value in expected.items() if name != key},
                                   fault, invalid)
    with pytest.raises(ValueError):
        proof.validate_receipt({**expected, "extra": 0}, fault, invalid)
    groups = re.findall(r'printf\(((?:"(?:\\.|[^"\\])*"\s*)+)', artifacts["worker.c"])
    assert len(groups) == 1
    pattern = "".join(ast.literal_eval(value)
                      for value in re.findall(r'"(?:\\.|[^"\\])*"', groups[0]))
    binding = re.search(r'#define TUC_ENTRYPOINT_BINDING "([^"]+)"', artifacts["worker.c"]).group(1)
    values = (expected["status"], expected["reason"], binding, fault,
              *(expected[key] for key in proof.COUNTERS))
    assert json.loads(pattern.replace("%zu", "%d") % values) == expected
    assert pattern.endswith("\n") and "\\n" not in pattern


def test_receipt_counters_independently_cover_success_controls_and_falsification():
    baseline = proof.expected_receipt()
    assert tuple(baseline[key] for key in proof.COUNTERS) == (
        2 * 3 * 2, (2 + 34 + 33) * 3 * 2, (6 + 1) * 3 * 2,
        (2 + 1) * 3 * 2, (34 + 33) * 3 * 2, 6 * (34 + 33) * 3 * 2,
    )
    expected = ((0, 1, 0, 0, 0, 0), (1, 2, 6, 2, 0, 0), (1, 2, 6, 2, 0, 5))
    for fault, counters in enumerate(expected, 1):
        assert tuple(proof.expected_receipt(fault)[key] for key in proof.COUNTERS) == counters


@pytest.mark.parametrize("replacement", (True, False, 1.0, "1", None, [], {}))
def test_receipt_rejects_counter_type_confusion(replacement):
    expected = proof.expected_receipt()
    for key in (*proof.COUNTERS, "fault"):
        with pytest.raises(ValueError):
            proof.validate_receipt({**expected, key: replacement})


@pytest.mark.parametrize("text", ('{"a":1,"a":2}', '[NaN]', '[Infinity]', '[1.0]', '[1e400]',
                                 '[1000001]', '[-1]', '{} trailing', '{', 'true'))
def test_untrusted_receipt_data_fail_closed(text):
    with pytest.raises(ValueError):
        value = proof._receipt_json(text)
        proof.validate_receipt(value)


def test_receipt_parser_explicit_resource_budgets():
    for text in (" " * (proof.MAX_RECEIPT_BYTES + 1),
                 "[" * (proof.MAX_RECEIPT_DEPTH + 1) + "0" + "]" * (proof.MAX_RECEIPT_DEPTH + 1),
                 "[" + ",".join("0" for _ in range(proof.MAX_RECEIPT_ITEMS + 1)) + "]"):
        with pytest.raises(ValueError):
            proof._receipt_json(text)
    quoted = {"text": '[{{{,::"escaped"\\]]'}
    assert proof._receipt_json(json.dumps(quoted)) == quoted


@pytest.mark.parametrize("field", ("header", "source", "manifest_json", "entrypoint_symbol"))
def test_changed_entrypoint_text_rejected_before_context(monkeypatch, tmp_path, field):
    _, artifact = proof.compile_graph("app")
    changed = replace(artifact, **{field: getattr(artifact, field) + " changed"})
    monkeypatch.setattr(proof, "emit_bounded_c11_entrypoint", lambda *args: changed)
    with pytest.raises(ValueError):
        proof.emit_context()
    assert not (tmp_path / "tmp").exists()


def _synthetic_context():
    directory = proof.emit_context()
    files = proof.artifact_files()
    for build in ("static", "sanitized"):
        (directory / f"{build}-image-id.txt").write_text("sha256:" + "b" * 64)
        for fault, invalid in ((0, False), (1, False), (2, False), (3, False), (0, True)):
            suffix = "invalid" if invalid else "proof" if fault == 0 else f"fault{fault}"
            (directory / f"{build}-{suffix}.json").write_text(
                json.dumps(proof._expected_from_files(files, fault, invalid)),
            )
    return directory


def test_exclusive_emission_and_synthetic_receipt_validation():
    first = _synthetic_context()
    second = proof.emit_context()
    assert first != second and first.parent == second.parent
    assert (first / "static-proof.json").exists()
    assert not (second / "static-proof.json").exists()
    (first / "record.json").write_bytes(b"")
    record = proof.accept(first)
    assert len(record["observations"]) == 10
    assert record["normal_runtime_admission"] is False
    assert record["cuda_execution_observed"] is False


@pytest.mark.parametrize("name", ("app-entrypoint.c", "tiny-entrypoint.h", "entrypoint.h",
                                  "worker.c", "source-bindings.json", "operator.sh", "consumer.py"))
def test_changed_context_source_is_rejected(name):
    directory = _synthetic_context()
    (directory / name).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError):
        proof.accept(directory)


def test_old_receipts_rejected_after_regenerating_changed_context(tmp_path):
    old = _synthetic_context()
    operator = tmp_path / "operator.sh"
    operator.write_bytes(operator.read_bytes() + b"\n# changed source fixture\n")
    fresh = proof.emit_context()
    for path in old.iterdir():
        if path.name.startswith(("static-", "sanitized-")):
            (fresh / path.name).write_bytes(path.read_bytes())
    with pytest.raises(ValueError):
        proof.accept(fresh)


@pytest.mark.parametrize("name", ("static-proof.json", "sanitized-fault3.json",
                                  "sanitized-invalid.json", "static-image-id.txt"))
def test_missing_receipt_or_image_identity_is_rejected(name):
    directory = _synthetic_context()
    (directory / name).unlink()
    with pytest.raises(ValueError):
        proof.accept(directory)


@pytest.mark.parametrize("kind", ("file", "directory", "oversized", "invalid_image"))
def test_context_type_size_and_coverage_fail_closed(kind):
    directory = _synthetic_context()
    if kind == "file":
        (directory / "extra").write_bytes(b"x")
    elif kind == "directory":
        (directory / "extra").mkdir()
    elif kind == "oversized":
        (directory / "static-proof.json").write_bytes(b" " * (proof.MAX_RECEIPT_BYTES + 1))
    else:
        (directory / "static-image-id.txt").write_bytes(b"sha256:no")
    with pytest.raises(ValueError):
        proof.accept(directory)


@pytest.mark.parametrize("name", ("MAX_FILE_BYTES", "MAX_CONTEXT_BYTES"))
def test_generation_resource_limits_apply_before_writes(monkeypatch, tmp_path, name):
    monkeypatch.setattr(proof, name, 16)
    with pytest.raises(ValueError):
        proof.emit_context()
    assert not (tmp_path / "tmp").exists()


@pytest.mark.parametrize("name", ("../escape.c", "/absolute.c", "nested/source.c", "worker.c"))
def test_context_mapping_requires_exact_flat_names_and_types(artifacts, name):
    changed = {**artifacts, name: False}
    with pytest.raises(ValueError):
        proof.report(changed)


def test_parent_file_and_directory_escape_rejected(tmp_path):
    with pytest.raises(ValueError):
        proof.accept(tmp_path)
    (tmp_path / "tmp").write_text("not a directory")
    with pytest.raises(ValueError):
        proof.emit_context()


@pytest.mark.parametrize("name", ("worker.c", "static-proof.json"))
def test_symlink_evidence_rejected(tmp_path, name):
    directory = _synthetic_context()
    target = directory / name
    outside = tmp_path / "outside"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable for this host account")
    with pytest.raises(ValueError):
        proof.accept(directory)


def test_symlink_emission_parent_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (tmp_path / "tmp").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable for this host account")
    with pytest.raises(ValueError):
        proof.emit_context()
    assert list(outside.iterdir()) == []


def test_symlink_ancestor_cannot_alias_an_otherwise_valid_context(tmp_path):
    directory = _synthetic_context()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(directory.parent, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable for this host account")
    with pytest.raises(ValueError):
        proof.accept(alias / directory.name)


@pytest.mark.parametrize("value", (None, "", "sha256:abcd", "sha256:" + "G" * 64))
def test_wheel_identity_required_before_emission(tmp_path, value):
    sidecar = tmp_path / "wheel-sha256.txt"
    if value is None:
        sidecar.unlink()
    else:
        sidecar.write_text(value, encoding="utf-8")
    with pytest.raises(ValueError):
        proof.emit_context()
    assert not (tmp_path / "tmp").exists()
