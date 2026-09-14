from __future__ import annotations

import copy
import math
import subprocess
import sys
from fractions import Fraction

import numpy as np
import pytest

from examples import reduction_fp32_contract as fp
from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _digest_payload


def test_rounding_is_ties_even_without_double_rounding():
    for numerator in (-3, -1, 1, 3):
        value = Fraction(1) + Fraction(numerator, 2**24)
        assert fp.round_f32(value) == float(np.float32(float(value)))
    midpoint = Fraction(1) + Fraction(1, 2**24)
    assert fp.round_f32(midpoint) == 1.0
    assert fp.round_f32(midpoint + Fraction(1, 2**100)) == 1.0 + 2**-23
    for bad in (Fraction(1, 2**110), Fraction(2**110)):
        with pytest.raises(BoundedCompilerEmissionError):
            fp.round_f32(bad)


def test_corpus_is_unique_inexact_and_within_a_priori_bound():
    cases = fp.corpus()
    assert len(cases) == len({_digest_payload([c["a"], c["b"]]) for c in cases}) == 10
    rounded = 0
    for case in cases:
        bounds = fp.reference(case["a"], case["b"])
        ordered = fp.ordered_reference(case)
        a, b = np.array(case["a"], dtype=np.float32), np.array(case["b"], dtype=np.float32)
        # Independent library arithmetic need not have the emitted operation order.
        numpy_result = (a @ b).sum(axis=1)
        for row, (exact, budget) in enumerate(bounds):
            flat_exact = sum((Fraction(case["a"][row][k]) * Fraction(case["b"][k][c])
                              for k in range(7) for c in range(5)), Fraction())
            assert flat_exact == exact
            for result in (ordered[row], float(numpy_result[row])):
                lo, hi = fp.interval(exact, budget)
                assert lo <= result <= hi
                assert abs(Fraction(result) - exact) <= budget
            rounded += Fraction(ordered[row]) != exact
    assert rounded > 200
    cancellation = next(c for c in cases if c["name"] == "cancellation")
    assert any(budget > abs(exact) * Fraction(1, 100)
               for exact, budget in fp.reference(cancellation["a"], cancellation["b"]))
    assert all(pair == (0, 0) for pair in fp.reference(cases[-2]["a"], cases[-2]["b"]))


def test_serialized_intervals_do_not_enlarge_budget_and_reject_adjacent_outsiders():
    for case in fp.corpus():
        for exact, budget in fp.reference(case["a"], case["b"]):
            lo, hi = fp.interval(exact, budget)
            assert Fraction(lo) >= exact - budget
            assert Fraction(hi) <= exact + budget
            above = float(np.nextafter(np.float32(hi), np.float32(math.inf)))
            below = float(np.nextafter(np.float32(lo), np.float32(-math.inf)))
            assert above > hi and below < lo
            assert abs(Fraction(above) - exact) > budget
            assert abs(Fraction(below) - exact) > budget
    with pytest.raises(BoundedCompilerEmissionError):
        fp.interval(Fraction(), Fraction(-1))


@pytest.mark.parametrize("bad", [True, 1, 0.1, None, "1.0", float("nan"), float("inf"),
                               float("-inf"), 2.0**-100, 2.0**17])
def test_input_domain_rejects_non_fp32_nonfinite_and_unreviewed_magnitudes(bad):
    case = copy.deepcopy(fp.corpus()[0])
    case["a"][0][0] = bad
    with pytest.raises(BoundedCompilerEmissionError):
        fp.reference(case["a"], case["b"])


@pytest.mark.parametrize("target", fp.TARGETS)
def test_observation_rejects_changed_contract_nonexecution_and_missing_rounding(target):
    good = fp.expected_observation(target, rounded=200)
    assert fp.validate_observation(good, target) == good
    for key, value in (("contract_digest", "sha256:" + "0" * 64), ("case_count", 20),
                       ("outputs_differing_from_reference64", 0),
                       ("outputs_differing_from_reference64", True),
                       ("outputs_differing_from_reference64", 364),
                       ("outputs_differing_from_reference64", -1),
                       ("outputs_differing_from_reference64", 1.0),
                       ("numeric_contract_passed", 1), ("cases_passed", 10),
                       ("security_boundary_passed", False), ("extra", "untrusted"),
                       ("raw_values_serialized", True)):
        with pytest.raises(BoundedCompilerEmissionError):
            fp.validate_observation({**good, key: value}, target)
    with pytest.raises(BoundedCompilerEmissionError):
        fp.validate_observation(fp.expected_observation(target, True), target)
    assert fp.validate_observation(fp.expected_observation(target, True), target, True)


def test_comparison_is_pure_bound_and_not_bitwise_equivalence(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier started a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    cpu, gpu = [fp.build_record(fp.expected_observation(t, rounded=200), t, "sha256:" + "1" * 64)
                for t in fp.TARGETS]
    result = fp.compare_records(cpu, gpu)
    assert result["comparison"] == "both_targets_satisfy_same_exact_reference_error_contract"
    assert "bitwise_backend_equivalence" in result["blocked_claims"]
    for key in ("program_files_digest", "operator_image_id", "provenance"):
        with pytest.raises(BoundedCompilerEmissionError):
            fp.compare_records(cpu, {**gpu, key: "wrong"})
    with pytest.raises(BoundedCompilerEmissionError):
        fp.compare_records(cpu, cpu)


@pytest.mark.parametrize("mutation", fp.MUTATIONS)
def test_negative_records_cannot_be_promoted_to_execution(mutation):
    value = fp.expected_observation("cuda")
    value.update(status="ERROR", reason_code="numeric_contract_mismatch", cases_passed=0,
                 failed_run_index=0, generated_function_calls=2,
                 numeric_contract_passed=False, repeated_baseline_passed=False)
    fp.validate_negative(value, "cuda", mutation)
    with pytest.raises(BoundedCompilerEmissionError):
        fp.validate_observation(value, "cuda")


@pytest.mark.parametrize("name", ["oracle.h", "inputs.h", "numeric_contract.json"])
def test_artifact_drift_is_rejected(monkeypatch, name):
    read = fp._read_bounded_file
    def altered(path):
        data = read(path)
        return data + b"\n" if path.name == name else data
    monkeypatch.setattr(fp, "_read_bounded_file", altered)
    with pytest.raises(BoundedCompilerEmissionError):
        fp.verify_artifacts()


@pytest.mark.parametrize("flags", [["--preflight"], ["--target", "cuda"],
                                   ["--validate", "missing", "--target", "c11",
                                    "--negative", "wrong-stride", "--preflight"]])
def test_cli_rejects_conflicting_modes(monkeypatch, capsys, flags):
    monkeypatch.setattr(sys, "argv", ["fp32-proof", *flags])
    assert fp.main() == 1
    assert capsys.readouterr().err == "bounded FP32 contract verification rejected\n"


def test_native_isolation_and_numerical_options_are_explicit():
    script = (fp.ROOT / "scripts/run_reduction_fp32_contract.sh").read_text()
    for flag in ("--cuda-reviewed", "--network=none", "--read-only", "--user=10001:10001",
                 "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=1g",
                 "--pids-limit=32", "--gpus=device=0", "timeout 30s", "c11-sanitizer"):
        assert flag in script
    assert "--privileged" not in script and "--volume" not in script
    cpu = (fp.CONTEXT / "build-c11.sh").read_text()
    gpu = (fp.CONTEXT / "build-cuda.sh").read_text()
    assert "-ffp-contract=off" in cpu and "-fno-fast-math" in cpu
    assert "--fmad=false --ftz=false" in gpu and "--list-ptx" in gpu
    common = (fp.CONTEXT / "common.h").read_text()
    assert "fegetround() != FE_TONEAREST" in common
    assert "!isfinite(value)" in common
    assert "nextafterf((float)TUC_UPPER[index][0], INFINITY)" in common
    assert max(len(s.encode()) for s in fp.artifact_files().values()) < 65536
