from __future__ import annotations

import copy
import json
import subprocess
import sys

import numpy as np
import pytest

from examples import bounded_reduction_shapes as shapes
from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _digest_payload
from examples.bounded_reduction_c11 import ROOT, load_observation


def test_lowering_both_profiles_preserves_baseline_bytes_and_odd_bounds():
    baseline = shapes.emit(shapes.parse_source("baseline"), "baseline")
    assert baseline["generated.c"] == (ROOT / "docker/reduction-c11/generated.c").read_text()
    assert baseline["generated.h"] == (ROOT / "docker/reduction-c11/generated.h").read_text()
    assert baseline["kernels.cuh"] == (ROOT / "docker/reduction-cuda/kernels.cuh").read_text()
    odd = shapes.emit(shapes.parse_source("odd"), "odd")
    assert "index < 165U" in odd["kernels.cuh"]
    assert "row < 33U" in odd["kernels.cuh"]
    assert "inner < 7U" in odd["generated.c"]
    assert "column < 5U" in odd["generated.c"]
    assert odd["generated.c"] != baseline["generated.c"]


@pytest.mark.parametrize("profile", ["odd", "baseline"])
@pytest.mark.parametrize("change", ["axis", "dtype", "shape", "code", "extra", "returns"])
def test_unapproved_semantics_never_reach_emission(profile, change):
    value = copy.deepcopy(shapes.parse_source(profile))
    if change == "axis":
        value["operations"][1]["attributes"]["axis"] = 0
    elif change == "dtype":
        value["tensors"][0]["dtype"] = "float64"
    elif change == "shape":
        value["tensors"][0]["shape"][0] += 1
    elif change == "code":
        value["operations"][0]["name"] = "x);system(\"bad\");"
    elif change == "returns":
        value["returns"][0]["tensor_name"] = "projection"
    else:
        value["extra"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        shapes.emit(value, profile)


@pytest.mark.parametrize("profile", [None, {}, True, "../odd", "33,7,5", "huge"])
def test_only_explicit_profiles_are_admitted(profile):
    with pytest.raises(BoundedCompilerEmissionError):
        shapes.parse_source(profile)


def test_twenty_unique_vectors_agree_with_numpy_and_cover_last_row():
    cases = shapes.corpus()
    assert len(cases) == len({_digest_payload([c["a"], c["b"]]) for c in cases}) == 20
    for case in cases:
        a, b = np.array(case["a"], dtype=np.float32), np.array(case["b"], dtype=np.float32)
        np.testing.assert_array_equal((a @ b).sum(axis=1), case["expected"])
    by_name = {c["name"]: c for c in cases}
    baseline = np.array(by_name["baseline"]["expected"])
    np.testing.assert_array_equal(by_name["negated_a"]["expected"], -baseline)
    np.testing.assert_array_equal(by_name["reversed_a_rows"]["expected"], baseline[::-1])
    np.testing.assert_array_equal(by_name["rotated_b_columns"]["expected"], baseline)
    last = by_name["last_row_only"]["expected"]
    assert last[:-1] == [0.0] * 32
    assert last[-1] == baseline[-1] != 0.0


def test_launches_cover_each_logical_item_once_and_bound_excess_threads():
    plan = shapes.verify_artifacts()
    assert plan["tensor_bytes"] == 1856
    assert plan["input_shapes"] == [[33, 7], [7, 5]]
    assert plan["output_shape"] == [33]
    assert [x["blocks"] for x in plan["cuda_launches"]] == [6, 2]
    for launch in plan["cuda_launches"]:
        ids = [block * launch["threads"] + thread
               for block in range(launch["blocks"]) for thread in range(launch["threads"])]
        valid = [i for i in ids if i < launch["logical_items"]]
        assert valid == list(range(launch["logical_items"]))
        assert len(ids) > len(valid) > 32


def test_wrong_stride_and_missing_sum_are_detectable_in_first_case():
    case = shapes.corpus()[0]
    a, b = np.array(case["a"]), np.array(case["b"])
    wrong_b = np.array([[b.ravel()[k + c] for c in range(5)] for k in range(7)])
    assert not np.array_equal((a @ wrong_b).sum(axis=1), case["expected"])
    assert not np.array_equal((a @ b)[:, -1], case["expected"])


@pytest.mark.parametrize("bad", [True, 1, 4.25, 0.1, float("nan"), float("inf"), None])
def test_numeric_domain_rejects_unreviewed_values(bad):
    case = copy.deepcopy(shapes.corpus()[0])
    case["a"][0][0] = bad
    with pytest.raises(BoundedCompilerEmissionError):
        shapes.exact_reference(case["a"], case["b"])


@pytest.mark.parametrize("target", shapes.TARGETS)
def test_observations_require_complete_new_shape_and_exact_metadata(target):
    good = shapes.expected_observation(target)
    assert shapes.validate_observation(good, target)["cases_passed"] == 21
    for key, value in (("output_shape", [4]), ("tensor_bytes", 240), ("cases_passed", 20),
                       ("generated_function_calls", 2), ("reference_correctness", 1),
                       ("security_boundary_passed", False), ("raw_values_serialized", True),
                       ("code_digest", "sha256:" + "0" * 64), ("extra", "untrusted")):
        with pytest.raises(BoundedCompilerEmissionError):
            shapes.validate_observation({**good, key: value}, target)
    with pytest.raises(BoundedCompilerEmissionError):
        shapes.validate_observation(shapes.expected_observation(target, True), target)


def test_records_are_pure_and_bound_to_current_programs(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure shape verifier executed a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    cpu = shapes.build_record(shapes.expected_observation("c11"), "c11", "sha256:" + "1" * 64)
    gpu = shapes.build_record(shapes.expected_observation("cuda"), "cuda", "sha256:" + "2" * 64)
    assert shapes.compare_records(cpu, gpu)["status"] == "PASS"
    with pytest.raises(BoundedCompilerEmissionError):
        shapes.compare_records(cpu, cpu)
    for key in ("operator_image_id", "program_files_digest", "provenance"):
        with pytest.raises(BoundedCompilerEmissionError):
            shapes.compare_records(cpu, {**gpu, key: "wrong"})


def test_artifact_drift_is_rejected(monkeypatch):
    read = shapes._read_bounded_file
    def altered(path):
        data = read(path)
        return data + b"\n" if path.name == "kernels.cuh" else data
    monkeypatch.setattr(shapes, "_read_bounded_file", altered)
    with pytest.raises(BoundedCompilerEmissionError):
        shapes.verify_artifacts()


@pytest.mark.parametrize("flags", [["--preflight"], ["--target", "cuda"],
                                   ["--validate", "missing", "--target", "c11",
                                    "--negative", "wrong-stride", "--preflight"]])
def test_cli_rejects_incomplete_or_conflicting_modes(monkeypatch, capsys, flags):
    monkeypatch.setattr(sys, "argv", ["shape-proof", *flags])
    assert shapes.main() == 1
    assert capsys.readouterr().err == "bounded reduction shape verification rejected\n"


def test_native_controls_and_poisoning_are_explicit():
    script = (ROOT / "scripts/run_bounded_reduction_shapes.sh").read_text()
    for flag in ("--cuda-reviewed", "--network=none", "--read-only", "--user=10001:10001",
                 "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=1g",
                 "--pids-limit=32", "--gpus=device=0", "timeout 30s", "c11-sanitizer"):
        assert flag in script
    assert "--privileged" not in script and "--volume" not in script
    assert "projection[i] = NAN" in (shapes.CONTEXT / "host.c").read_text()
    assert "cudaMemset(buffers[2], 0xff" in (shapes.CONTEXT / "device.cu").read_text()


def test_recorded_native_shape_evidence_when_available():
    directory = ROOT / "tests/golden/proofs"
    if not (directory / "reduction_shape_cuda_record.json").exists():
        pytest.skip("native odd-shape observation pending")
    cpu = load_observation(directory / "reduction_shape_c11_record.json")
    gpu = load_observation(directory / "reduction_shape_cuda_record.json")
    report = shapes.compare_records(cpu, gpu)
    assert report == json.loads((directory / "reduction_shape_equivalence.json").read_text())
    for target in shapes.TARGETS:
        value = load_observation(directory / f"reduction_shape_{target}_incomplete_coverage.json")
        shapes.validate_negative(value, target, "incomplete-coverage")
        with pytest.raises(BoundedCompilerEmissionError):
            shapes.validate_observation(value, target)
