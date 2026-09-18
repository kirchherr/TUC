"""Independent arithmetic and schedule checks for the installed-package consumer."""

from __future__ import annotations

import ast
import json
import math
import struct
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from integration.bounded_dag_compiler import consumer
from tuc.compiler.bounded_source import validate_bounded_source_compilation

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "integration/bounded_dag_compiler/expected_report.json"


@pytest.fixture(scope="module")
def compilations():
    return {profile: consumer.compile_profile(profile) for profile in consumer.PROFILES}


def _f32(value):
    rounded = struct.unpack("<f", struct.pack("<f", value))[0]
    assert math.isfinite(rounded)
    assert rounded == 0.0 or abs(rounded) >= 2**-126
    return rounded


def _ordered_product(left, right):
    """Scalar reference, independent of compiler metadata and emitted functions."""

    output = []
    for row in left:
        output_row = []
        for col in range(len(right[0])):
            value = 0.0
            for inner in range(len(row)):
                value = _f32(value + _f32(row[inner] * right[inner][col]))
            output_row.append(value)
        output.append(output_row)
    return output


def _ordered_rows(values):
    output = []
    for row in values:
        total = 0.0
        for value in row:
            total = _f32(total + value)
        output.append(total)
    return output


def _reference(inputs):
    a, b, c, d = (inputs[name].tolist() for name in ("a", "b", "c", "d"))
    left = _ordered_product(a, b)
    right = _ordered_product(c, d)
    positive_left = [[value if value > 0.0 else 0.0 for value in row] for row in left]
    positive_right = [[value if value > 0.0 else 0.0 for value in row] for row in right]
    joined = _ordered_product(positive_left, positive_right)
    return {"branch_total": _ordered_rows(left), "joined_total": _ordered_rows(joined)}


def _inputs(case):
    result = {}
    for tensor_index, (name, shape) in enumerate(
        (("a", (3, 2)), ("b", (2, 4)), ("c", (4, 3)), ("d", (3, 2)))
    ):
        values = []
        for index in range(math.prod(shape)):
            numerator = ((index * 7 + tensor_index * 3) % 19) - 9
            if case == "dyadic":
                value = numerator / 8.0
            elif case == "rounded":
                value = numerator / 7.0
            else:
                value = -0.0 if index % 3 == 0 else numerator / 16.0
            values.append(_f32(value))
        result[name] = np.asarray(values, dtype=np.float32).reshape(shape)
    return result


def _simulate(manifest, inputs):
    """NumPy data-only simulation of slots; never calls a generated primitive."""

    tensors = manifest["tensors"]
    buffers = manifest["buffers"]
    slots = [
        np.full(tensors[buffer["tensor"]]["shape"], np.nan, dtype=np.float32)
        for buffer in buffers
    ]
    ready = set()
    executed = []
    published = {}
    copied_bytes = 0
    for event in manifest["events"]:
        kind = event["kind"]
        assert all(slot in ready for slot in event["inputs"])
        assert all(slot not in ready for slot in event["outputs"])
        if kind == "bind_input":
            assert event["inputs"] == [] and len(event["outputs"]) == 1
            destination = event["outputs"][0]
            tensor = tensors[buffers[destination]["tensor"]]
            slots[destination][...] = inputs[tensor["name"]]
        elif kind == "copy":
            assert len(event["inputs"]) == len(event["outputs"]) == 1
            source, destination = event["inputs"][0], event["outputs"][0]
            assert buffers[source]["tensor"] == buffers[destination]["tensor"]
            assert buffers[source]["space"] != buffers[destination]["space"]
            slots[destination][...] = slots[source]
            copied_bytes += slots[destination].nbytes
        elif kind == "execute":
            op = manifest["operations"][event["operation"]]
            assert [buffers[index]["tensor"] for index in event["inputs"]] == op["inputs"]
            assert [buffers[index]["tensor"] for index in event["outputs"]] == op["outputs"]
            assert event["target"] == op["target"]
            operands = [slots[index] for index in event["inputs"]]
            output = np.zeros(op["output_shape"], dtype=np.float32)
            if op["kind"] == "matmul":
                for inner in range(operands[0].shape[1]):
                    product = np.multiply(
                        operands[0][:, inner, None], operands[1][inner, None, :], dtype=np.float32,
                    )
                    output = np.add(output, product, dtype=np.float32)
            elif op["kind"] == "relu":
                output = np.maximum(operands[0], np.float32(0.0))
            elif op["kind"] == "sum_axis1":
                for column in range(operands[0].shape[1]):
                    output = np.add(output, operands[0][:, column], dtype=np.float32)
            else:
                pytest.fail("unexpected consumer primitive")
            assert np.isfinite(output).all()
            assert ((output == 0.0) | (np.abs(output) >= np.finfo(np.float32).tiny)).all()
            slots[event["outputs"][0]][...] = output
            executed.append(op["index"])
        elif kind == "publish_output":
            assert len(event["inputs"]) == 1 and event["outputs"] == []
            source = event["inputs"][0]
            tensor_index = buffers[source]["tensor"]
            assert tensor_index not in published
            published[tensor_index] = slots[source].copy()
        else:
            pytest.fail("unexpected consumer event")
        ready.update(event["outputs"])
    assert executed == list(range(len(manifest["operations"])))
    assert list(published) == manifest["output_tensors"]
    assert copied_bytes == manifest["planned_copy_bytes"]
    return published


@pytest.mark.parametrize("profile", consumer.PROFILES)
@pytest.mark.parametrize("case", ("dyadic", "rounded", "signed_zero"))
def test_independent_fp32_reference_matches_each_schedule(compilations, profile, case):
    result = compilations[profile]
    manifest = json.loads(result.artifacts.manifest_json)
    inputs = _inputs(case)
    expected = _reference(inputs)
    for _ in range(2):
        published = _simulate(manifest, inputs)
        actual = {
            binding.public_name: published[binding.tensor_index]
            for binding in result.output_bindings
        }
        assert actual.keys() == expected.keys()
        for name in expected:
            # Exact finite FP32 values, with the contract's numerical signed-zero policy.
            np.testing.assert_array_equal(
                actual[name], np.asarray(expected[name], dtype=np.float32),
            )


def test_capabilities_select_placements_without_operation_overrides(compilations):
    for profile, result in compilations.items():
        plan = result.compilation.partition_plan
        assert plan.override_effects == ()
        expected_backends = (
            ["consumer_gpu"] * 7 if profile == "gpu" else
            ["consumer_cpu"] * 7 if profile == "cpu" else
            ["consumer_gpu", "consumer_gpu", "consumer_cpu", "consumer_cpu",
             "consumer_gpu", "consumer_cpu", "consumer_cpu"]
        )
        assert [assignment.backend_name for assignment in plan.assignments] == expected_backends
        prefix = "preferred_for:" if profile == "mixed" else "supported:"
        assert all(assignment.reason.startswith(prefix) for assignment in plan.assignments)
    manifests = {name: json.loads(result.artifacts.manifest_json)
                 for name, result in compilations.items()}
    assert manifests["cpu"]["planned_copy_bytes"] == 0
    assert manifests["mixed"]["planned_copy_bytes"] > manifests["gpu"]["planned_copy_bytes"] > 0
    assert len({result.artifacts.files()["schedule.h"] for result in compilations.values()}) == 3


def test_all_profiles_preserve_source_hac_primitives_and_public_aliases(compilations):
    baseline = compilations["cpu"]
    for result in compilations.values():
        assert result.source_intent_digest == baseline.source_intent_digest
        assert result.compilation.hac_ir == baseline.compilation.hac_ir
        assert result.input_bindings == baseline.input_bindings
        assert result.output_bindings == baseline.output_bindings
        for name in ("generated.c", "generated.h", "kernels.cuh"):
            assert result.artifacts.files()[name] == baseline.artifacts.files()[name]
    assert [binding.public_name for binding in baseline.input_bindings] == ["a", "b", "c", "d"]
    assert [(binding.public_name, binding.tensor_name) for binding in baseline.output_bindings] == [
        ("branch_total", "raw_rows"), ("joined_total", "joint_rows"),
    ]
    assert len({result.backend_bindings_digest for result in compilations.values()}) == 3


@pytest.mark.parametrize("removed_kind", ("copy", "execute", "publish_output"))
def test_schedule_comparison_detects_omitted_work(compilations, removed_kind):
    manifest = deepcopy(json.loads(compilations["mixed"].artifacts.manifest_json))
    position = next(index for index, event in enumerate(manifest["events"])
                    if event["kind"] == removed_kind)
    del manifest["events"][position]
    with pytest.raises(AssertionError):
        _simulate(manifest, _inputs("rounded"))


def test_compiler_revalidator_rejects_forged_public_return(compilations):
    result = compilations["cpu"]
    forged = replace(result, output_bindings=(
        replace(result.output_bindings[0], public_name="wrong_public_name"),
        result.output_bindings[1],
    ))
    with pytest.raises(ValueError):
        validate_bounded_source_compilation(
            consumer.source_module(), consumer.backend_bindings("cpu"), forged,
        )


def test_consumer_uses_only_installed_tuc_and_stdlib():
    tree = ast.parse(Path(consumer.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imports.append(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            assert not (isinstance(node.func, ast.Name) and node.func.id in {"exec", "eval"})
    assert set(imports) <= sys.stdlib_module_names | {"tuc"}
    assert "examples" not in imports


def test_compact_report_matches_golden_without_native_execution(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail("consumer must not launch a native process")

    monkeypatch.setattr(subprocess, "Popen", deny)
    text = consumer.report_text()
    assert text.encode("utf-8") == GOLDEN.read_bytes()
    assert text == consumer.report_text()
    report = json.loads(text)
    assert report["native_execution_observed"] is False
    assert report["normal_runtime_admission"] is False
    assert report["same_source_hac_primitives_and_returns"] is True
    assert "latency_ns" not in text and "energy_pj" not in text
    assert str(ROOT) not in text
    assert len(text.encode("utf-8")) < consumer.MAX_REPORT_BYTES


def test_check_success_prints_exact_report(capsys):
    assert consumer.main(["--check", str(GOLDEN)]) == 0
    captured = capsys.readouterr()
    assert captured.out.encode("utf-8") == GOLDEN.read_bytes()
    assert captured.err == ""


@pytest.mark.parametrize(
    "contents", (b"{}\n", b"x" * (consumer.MAX_REPORT_BYTES + 1)),
    ids=("mismatch", "oversized"),
)
def test_check_rejects_mismatched_or_oversized_report(tmp_path, capsys, contents):
    expected = tmp_path / "expected.json"
    expected.write_bytes(contents)
    assert consumer.main(["--check", str(expected)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "bounded source consumer verification failed\n"


def test_check_rejects_missing_file_and_directory(tmp_path, capsys):
    for path in (tmp_path / "missing.json", tmp_path):
        assert consumer.main(["--check", str(path)]) == 1
        captured = capsys.readouterr()
        assert captured.out == ""
        assert str(path) not in captured.err
