from __future__ import annotations

import copy
import json
import subprocess
import sys
from fractions import Fraction

import pytest

from examples import reduction_fma_variant as fma
from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _digest_text
from examples.bounded_reduction_c11 import load_observation


def test_fused_reference_keeps_product_precision_until_single_rounding():
    x, y = 1.0 + 2**-23, 1.0 - 2**-23
    case = {"a": [[-1.0, x, 0.0, 0.0, 0.0, 0.0, 0.0] for _ in range(33)],
            "b": [[1.0, 0.0, 0.0, 0.0, 0.0], [y, 0.0, 0.0, 0.0, 0.0]]
                 + [[0.0] * 5 for _ in range(5)]}
    assert fma.fp.ordered_reference(case) == [0.0] * 33
    assert fma.fused_reference(case) == [-2.0**-46] * 33
    assert all(exact == Fraction(-1, 2**46) for exact, _ in
               fma.fp.reference(case["a"], case["b"]))


def test_both_variants_fit_identical_intervals_but_observably_differ():
    cases = fma.fp.corpus()
    differences = 0
    for index in (*range(10), 0):
        case = cases[index]
        for left, right, (exact, budget) in zip(
            fma.fp.ordered_reference(case), fma.fused_reference(case),
            fma.fp.reference(case["a"], case["b"]), strict=True
        ):
            lo, hi = fma.fp.interval(exact, budget)
            assert lo <= left <= hi and lo <= right <= hi
            assert abs(Fraction(left) - Fraction(right)) <= 2 * budget
            differences += left != right
    assert differences == 61
    assert fma.fp.ordered_reference(cases[0]) != fma.fused_reference(cases[0])
    plan = fma.verify_artifacts()
    assert plan["expected_counts"]["different_outputs"] == differences
    assert plan["baseline_contract_digest"] == fma.fp.verify_artifacts()["contract_digest"]
    assert plan["acceptance_intervals_digest"] == _digest_text(
        (fma.fp.CONTEXT / "oracle.h").read_text())
    assert fma.fp.CONTRACT["fma_contraction"] is False
    assert plan["execution_policy_digest"] != plan["baseline_contract_digest"]


def test_codegen_changes_only_reviewed_arithmetic_and_names():
    payload = fma.fp.shapes.parse_source("odd")
    baseline = fma.fp.shapes.emit(payload, "odd")
    host = fma.emit(payload, "c11")["fma.c"]
    device = fma.emit(payload, "cuda")["fma.cuh"]
    for source, intrinsic in ((host, "fmaf"), (device, "__fmaf_rn")):
        assert source.count(f"value = {intrinsic}(") == 1
        assert "value += projection[row * 5U + column];" in source
        assert "inner < 7U" in source and "row < 33U" in source
    assert "index < 165U" in device
    assert baseline["generated.c"] == (fma.fp.shapes.CONTEXT / "generated.c").read_text()


@pytest.mark.parametrize("change", ["axis", "shape", "dtype", "symbol", "extra"])
def test_unapproved_intent_does_not_reach_fma_emission(change):
    payload = copy.deepcopy(fma.fp.shapes.parse_source("odd"))
    if change == "axis":
        payload["operations"][1]["attributes"]["axis"] = 0
    elif change == "shape":
        payload["tensors"][0]["shape"][0] = 34
    elif change == "dtype":
        payload["tensors"][0]["dtype"] = "float64"
    elif change == "symbol":
        payload["operations"][0]["name"] = 'x);system("bad");'
    else:
        payload["fma_allowed"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        fma.emit(payload, "cuda")


@pytest.mark.parametrize("target", [True, {}, None, "arbitrary", "../cuda"])
def test_targets_are_explicitly_allowlisted(target):
    with pytest.raises(BoundedCompilerEmissionError):
        fma.emit(fma.fp.shapes.parse_source("odd"), target)


@pytest.mark.parametrize("target", fma.TARGETS)
def test_observations_require_two_variants_and_bound_policy(target):
    good = fma.expected_observation(target)
    assert fma.validate_observation(good, target) == good
    for key, value in (("different_outputs", 0), ("different_outputs", 61.0),
                       ("execution_policy_passed", 1), ("scalar_checks", 363),
                       ("generated_function_calls", 22), ("runs_passed", 10),
                       ("execution_policy_digest", good["baseline_contract_digest"]),
                       ("acceptance_intervals_digest", "sha256:" + "0" * 64),
                       ("security_boundary_passed", False), ("raw_values_serialized", True),
                       ("untrusted_extra", "bad")):
        with pytest.raises(BoundedCompilerEmissionError):
            fma.validate_observation({**good, key: value}, target)
    with pytest.raises(BoundedCompilerEmissionError):
        fma.validate_observation(fma.expected_observation(target, True), target)


@pytest.mark.parametrize("mutation", fma.MUTATIONS)
def test_negative_observations_never_become_success(mutation):
    value = fma.expected_observation("cuda")
    value.update(status="ERROR", reason_code="execution_policy_mismatch" if
                 mutation == "separate-as-fma" else "numeric_contract_mismatch",
                 runs_passed=0, failed_run_index=0, generated_function_calls=4, scalar_checks=0,
                 baseline_rounding_outputs=0, fma_rounding_outputs=0, different_outputs=0,
                 numeric_contract_passed=False, execution_policy_passed=False,
                 repeated_baseline_passed=False)
    fma.validate_negative(value, "cuda", mutation)
    with pytest.raises(BoundedCompilerEmissionError):
        fma.validate_observation(value, "cuda")
    if mutation == "separate-as-fma":
        with pytest.raises(BoundedCompilerEmissionError):
            fma.validate_negative({**value, "reason_code": "numeric_contract_mismatch"},
                                  "cuda", mutation)


def test_comparison_is_pure_and_rejects_drift(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier launched a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    cpu, gpu = [fma.build_record(fma.expected_observation(t), t, "sha256:" + "1" * 64)
                for t in fma.TARGETS]
    assert fma.compare_records(cpu, gpu)["different_outputs_per_target"] == 61
    for key in ("program_files_digest", "operator_image_id", "provenance"):
        with pytest.raises(BoundedCompilerEmissionError):
            fma.compare_records(cpu, {**gpu, key: "wrong"})
    with pytest.raises(BoundedCompilerEmissionError):
        fma.compare_records(cpu, cpu)
    read = fma._read_bounded_file
    def altered(path):
        data = read(path)
        return data + b"\n" if path.name == "fma.cuh" else data
    monkeypatch.setattr(fma, "_read_bounded_file", altered)
    with pytest.raises(BoundedCompilerEmissionError):
        fma.verify_artifacts()


@pytest.mark.parametrize("flags", [["--preflight"], ["--target", "cuda"],
                                   ["--validate", "missing", "--target", "c11",
                                    "--negative", "separate-as-fma", "--preflight"]])
def test_cli_rejects_conflicting_modes(monkeypatch, capsys, flags):
    monkeypatch.setattr(sys, "argv", ["fma-proof", *flags])
    assert fma.main() == 1
    assert capsys.readouterr().err == "bounded FMA verification rejected\n"


def test_isolation_sass_and_policy_controls_are_explicit():
    script = (fma.ROOT / "scripts/run_reduction_fma_variant.sh").read_text()
    for flag in ("--cuda-reviewed", "--network=none", "--read-only", "--user=10001:10001",
                 "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=1g",
                 "--pids-limit=32", "--gpus=device=0", "timeout 30s", "c11-sanitizer"):
        assert flag in script
    assert "--privileged" not in script and "--volume" not in script
    gpu = (fma.CONTEXT / "build-cuda.sh").read_text()
    assert "--fmad=false --ftz=false" in gpu and "--list-ptx" in gpu
    assert "--dump-sass" in gpu and "/FFMA/" in gpu
    cpu = (fma.CONTEXT / "build-c11.sh").read_text()
    assert "-ffp-contract=off" in cpu and "-fno-fast-math" in cpu
    common = (fma.CONTEXT / "common.h").read_text()
    assert "first_baseline[row] != baseline[row]" in common
    assert "first_fused[row] != fused[row]" in common
    assert max(len(s.encode()) for s in fma.artifact_files().values()) < 65536
    assert json.loads((fma.CONTEXT / "execution_policy.json").read_text()) == fma.POLICY


def test_actual_native_records_match_accepted_comparison():
    directory = fma.ROOT / "tests/golden/proofs"
    records = [load_observation(directory / f"reduction_fma_{t}_record.json") for t in fma.TARGETS]
    assert fma.compare_records(*records) == json.loads(
        (directory / "reduction_fma_comparison.json").read_text())


@pytest.mark.parametrize("target", fma.TARGETS)
@pytest.mark.parametrize("mutation", fma.MUTATIONS)
def test_actual_native_negative_controls_are_rejected(target, mutation):
    value = load_observation(fma.ROOT / "tests/golden/proofs" /
                             f"reduction_fma_{target}_{mutation}.json")
    fma.validate_negative(value, target, mutation)
    with pytest.raises(BoundedCompilerEmissionError):
        fma.validate_observation(value, target)
