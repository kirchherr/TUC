"""Actual bounded fan-in receipts and fail-closed metadata comparison."""

import copy
import subprocess

import pytest

from examples import bounded_native_fanin_equivalence as equivalence
from examples import bounded_native_fanin_workers as workers
from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _canonical_json


def observed(name):
    return workers.load_observation(
        workers.ROOT / "tests/golden/proofs" / f"native_fanin_{name}.json"
    )


@pytest.fixture(scope="module")
def artifacts():
    return workers.artifact_files()


@pytest.fixture
def protocol(monkeypatch, artifacts):
    # Reuse the reconstructed corpus while checking individual receipt fields.
    monkeypatch.setattr(workers, "artifact_files", lambda: copy.deepcopy(artifacts))


def test_observed_six_profile_comparison_is_pure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure comparison started a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    cpu, matrix = observed("c11_record"), observed("matrix_record")
    report = equivalence.compare_records(cpu, matrix)
    assert report == observed("comparison")
    assert report["matrix_scalar_checks"] == 2178
    assert report["matrix_rounding_witnesses"] == 1590
    assert report["one_matrix_image"] is True
    assert report["normal_runtime_admission"] is False
    assert report["latency_ns"] is report["energy_pj"] is None
    assert list(o["profile"] for o in matrix["observations"]) == list(workers.PROFILES)
    counts = [o["residency"] for o in matrix["observations"]]
    assert sum(c["cpu_calls"] for c in counts) == 132
    assert sum(c["gpu_calls"] for c in counts) == 132
    assert sum(c["upload_bytes"] + c["download_bytes"] for c in counts) == 62876
    for value in counts:
        for field in (
            "left_producer_calls",
            "right_producer_calls",
            "join_calls",
            "published_outputs",
        ):
            assert value[field] == 11
    for index, field in (
        (1, "left_copy_calls"),
        (2, "right_copy_calls"),
        (3, "right_copy_calls"),
        (4, "left_copy_calls"),
    ):
        assert counts[index][field] == 11


def test_actual_c11_sanitizers():
    assert observed("c11_record")["observations"][0] == observed("c11_sanitized")
    assert _canonical_json(observed("c11_contract_sanitized")) == _canonical_json(
        workers.sanitizer_observation()
    )
    assert observed("c11_contract_sanitized")["bitflip_rejections"] == 16032


@pytest.mark.parametrize("worker", ("c11", "matrix"))
def test_observed_preflights_and_unknown_selectors(worker, protocol):
    values = observed(f"{worker}_preflights")
    assert set(values) == set(workers.profiles_for(worker))
    for profile, value in values.items():
        workers.validate_observation(value, profile, worker, True)
        with pytest.raises(BoundedCompilerEmissionError):
            workers.validate_observation(value, profile, worker)
    unknown = observed(f"{worker}_unknown_profile")
    workers.validate_observation(unknown, "cccc", worker, mutation="unknown-profile")
    with pytest.raises(BoundedCompilerEmissionError):
        workers.validate_observation(unknown, "cccc", worker)


@pytest.mark.parametrize(
    "worker,profile",
    [(w, p) for w in ("c11", "matrix") for p in workers.profiles_for(w)],
)
def test_all_observed_fault_controls(worker, profile, protocol):
    mutations = workers.mutations_for(profile)
    seen = set()
    for group in range(4):
        values = observed(f"{worker}_{profile}_controls_{group + 1}")
        assert set(values) == set(mutations[group * 8 : (group + 1) * 8])
        assert not seen.intersection(values)
        seen.update(values)
        for mutation, value in values.items():
            workers.validate_observation(value, profile, worker, mutation=mutation)
            with pytest.raises(BoundedCompilerEmissionError):
                workers.validate_observation(value, profile, worker)
    assert seen == set(mutations)


@pytest.mark.parametrize(
    "field,value",
    [
        ("program_files_digest", "sha256:" + "0" * 64),
        ("operator_image_id", "unbound"),
        ("worker", "c11"),
        ("provenance", "independent_reproduction"),
        ("normal_runtime_admission", 0),
        ("latency_ns", 1),
        ("energy_pj", 1),
        ("unexpected", True),
    ],
)
def test_changed_record_metadata_rejected(field, value, protocol):
    matrix = observed("matrix_record")
    matrix[field] = value
    with pytest.raises(BoundedCompilerEmissionError):
        equivalence.compare_records(observed("c11_record"), matrix)


@pytest.mark.parametrize("change", ("missing", "duplicate", "reordered", "preflight", "c11"))
def test_substituted_execution_coverage_rejected(change, protocol):
    matrix = observed("matrix_record")
    values = matrix["observations"]
    if change == "missing":
        values.pop()
    elif change == "duplicate":
        values[-1] = copy.deepcopy(values[0])
    elif change == "reordered":
        values.reverse()
    elif change == "preflight":
        values[0] = observed("matrix_preflights")["cccc"]
    else:
        values[0] = observed("c11_record")["observations"][0]
    with pytest.raises(BoundedCompilerEmissionError):
        equivalence.compare_records(observed("c11_record"), matrix)


@pytest.mark.parametrize("value", (None, True, [], {"observations": [0] * 513}))
def test_invalid_record_rejected_before_build(value, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unbounded or invalid record reached compiler")

    monkeypatch.setattr(workers, "build_record", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        equivalence.compare_records(value, observed("matrix_record"))
