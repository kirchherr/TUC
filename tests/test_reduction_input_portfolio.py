from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _digest_payload
from examples.bounded_reduction_c11 import ROOT, load_observation
from examples.reduction_input_portfolio import (
    artifact_files,
    build_record,
    compare_records,
    corpus,
    exact_reference,
    expected_observation,
    validate_negative,
    validate_observation,
    verify_artifacts,
)


def test_all_twenty_cases_match_fp32_and_keep_old_generated_programs() -> None:
    cases = corpus()
    assert len(cases) == len({_digest_payload(c) for c in cases}) == 20
    for case in cases:
        result = (np.array(case["a"], dtype=np.float32) @ np.array(case["b"], dtype=np.float32))
        np.testing.assert_array_equal(result.sum(axis=1), case["expected"])
    files = artifact_files()
    assert files["generated.c"] == (ROOT / "docker/reduction-c11/generated.c").read_text()
    assert files["kernels.cuh"] == (ROOT / "docker/reduction-cuda/kernels.cuh").read_text()
    plan = verify_artifacts()
    assert plan["execution_order"] == [*range(20), 0]
    assert plan["recompile_between_cases"] is False


def test_corpus_covers_sign_scale_permutation_cancellation_and_each_inner_position() -> None:
    cases = {c["name"]: c for c in corpus()}
    y = np.array(cases["baseline"]["expected"])
    np.testing.assert_array_equal(cases["negated_a"]["expected"], -y)
    np.testing.assert_array_equal(cases["half_a"]["expected"], y / 2)
    np.testing.assert_array_equal(cases["swapped_b_columns"]["expected"], y)
    np.testing.assert_array_equal(cases["reversed_a_rows"]["expected"], y[::-1])
    for name in ("zero_a", "cancelling_b_columns"):
        assert cases[name]["expected"] == [0.0] * 4
    for k in range(8):
        assert np.count_nonzero(cases[f"basis_{k}"]["a"]) == 4


@pytest.mark.parametrize("bad", [True, 5.0, 0.1, float("nan"), float("inf"), "1", None])
def test_numeric_domain_is_bounded_and_exact(bad) -> None:
    case = copy.deepcopy(corpus()[0])
    case["a"][0][0] = bad
    with pytest.raises(BoundedCompilerEmissionError):
        exact_reference(case["a"], case["b"])


@pytest.mark.parametrize("target", ["c11", "cuda"])
def test_both_targets_require_42_calls_and_baseline_replay(target) -> None:
    report = expected_observation(target)
    assert validate_observation(report, target)["generated_function_calls"] == 42
    for key, value in (
        ("cases_passed", 20), ("case_count", 1), ("repeated_baseline_passed", False),
        ("reference_correctness", 1), ("case_tensor_bytes", 256),
        ("corpus_digest", "sha256:" + "0" * 64), ("code_digest", "sha256:" + "0" * 64),
        ("security_boundary_passed", False), ("raw_values_serialized", True),
    ):
        wrong = {**report, key: value}
        with pytest.raises(BoundedCompilerEmissionError):
            validate_observation(wrong, target)
    with pytest.raises(BoundedCompilerEmissionError):
        validate_observation(expected_observation(target, "preflight"), target)


@pytest.mark.parametrize("target", ["c11", "cuda"])
def test_frozen_output_probe_must_pass_baseline_then_fail_zero_case(target) -> None:
    report = expected_observation(target)
    report.update(status="ERROR", reason_code="reference_mismatch", cases_passed=1,
                  failed_run_index=1, generated_function_calls=4,
                  reference_correctness=False, repeated_baseline_passed=False)
    validate_negative(report, target, "frozen-output")
    with pytest.raises(BoundedCompilerEmissionError):
        validate_observation(report, target)
    changes = (("failed_run_index", 0), ("cases_passed", 0), ("generated_function_calls", 2))
    for key, value in changes:
        with pytest.raises(BoundedCompilerEmissionError):
            validate_negative({**report, key: value}, target, "frozen-output")


def test_records_require_both_targets_and_current_program_binding(monkeypatch) -> None:
    cpu = build_record(expected_observation("c11"), "c11", "sha256:" + "1" * 64)
    gpu = build_record(expected_observation("cuda"), "cuda", "sha256:" + "2" * 64)
    assert compare_records(cpu, gpu)["runs_per_target"] == 21
    with pytest.raises(BoundedCompilerEmissionError):
        compare_records(cpu, cpu)
    for field in ("program_files_digest", "operator_image_id", "provenance"):
        with pytest.raises(BoundedCompilerEmissionError):
            compare_records(cpu, {**gpu, field: "wrong"})
    with pytest.raises(BoundedCompilerEmissionError):
        compare_records(cpu, {**gpu, "independent": True})
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier spawned a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    compare_records(cpu, gpu)


def test_operator_is_explicit_bounded_and_does_not_recompile_inside_case_loop() -> None:
    script = (ROOT / "scripts/run_reduction_input_portfolio.sh").read_text()
    for item in ("--cuda-reviewed", "--network=none", "--read-only", "--cap-drop=ALL",
                 "--pids-limit=32", "--memory=1g", "timeout 30s", "--gpus=device=0",
                 "--user=10001:10001", "trap cleanup", "frozen-output", "c11-sanitizer"):
        assert item in script
    assert "--privileged" not in script
    assert "--volume" not in script
    common = (ROOT / "docker/reduction-portfolio/common.h").read_text()
    assert common.index("if (!prepare())") < common.index("for (unsigned int run")
    assert common.index("if (!finish())") > common.index("for (unsigned int run")


def test_accepted_portfolio_when_observed() -> None:
    directory = ROOT / "tests/golden/proofs"
    if not (directory / "reduction_portfolio_cuda_record.json").exists():
        pytest.skip("physical portfolio not observed yet")
    report = compare_records(load_observation(directory / "reduction_portfolio_c11_record.json"),
                             load_observation(directory / "reduction_portfolio_cuda_record.json"))
    assert report == json.loads((directory / "reduction_portfolio_equivalence.json").read_text())
