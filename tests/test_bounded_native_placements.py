import copy
import subprocess

import pytest

from examples import bounded_native_placements as placements
from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from tuc.runtime import runtime_execution_readiness_report


@pytest.fixture(scope="module")
def cases():
    return {p: placements.compile_case(p) for p in placements.PROFILES}


@pytest.mark.parametrize(
    "profile,copy_bytes,steps",
    [
        ("ccc", 0, 6),
        ("ccg", 792, 8),
        ("cgc", 1320, 8),
        ("cgg", 792, 8),
        ("gcc", 1724, 9),
        ("gcg", 2516, 11),
        ("ggc", 1724, 9),
        ("ggg", 1196, 9),
    ],
)
def test_all_eight_plans_have_correct_placement_and_boundary_costs(
    cases, profile, copy_bytes, steps
):
    compiled, plan = cases[profile]
    assert plan.copy_bytes == copy_bytes
    assert sum(b.bytes for b in plan.buffers) == 2516 + copy_bytes
    assert len(plan.steps) == steps
    assert [a.backend_name for a in compiled.partition_plan.assignments] == [
        "bounded-cuda" if p == "g" else "bounded-c11" for p in profile
    ]
    assert [e.required_backend for e in compiled.partition_plan.override_effects] == [
        a.backend_name for a in compiled.partition_plan.assignments
    ]
    with pytest.raises(ValueError, match="no trusted executor contract"):
        runtime_execution_readiness_report(compiled.hac_ir.graph, compiled.partition_plan)


def test_hac_ir_and_numeric_contract_are_invariant(cases):
    from tuc.ir.modules import IRStage

    assert len({c.dump(IRStage.HAC_IR) for c, _ in cases.values()}) == 1
    expected = placements.previous.compile_case("mixed")[0].dump(IRStage.HAC_IR)
    assert cases["ccc"][0].dump(IRStage.HAC_IR) == expected
    for profile in placements.PROFILES:
        value = placements.expected_observation(profile, "matrix")
        numeric = value["numeric_observation"]
        assert (
            numeric["contract_digest"]
            == placements.CHAIN.expected_observation("cuda")["contract_digest"]
        )
        assert numeric["scalar_checks"] == 363
        assert value["residency"]["cpu_calls"] == 11 * profile.count("c")
        assert value["residency"]["gpu_calls"] == 11 * profile.count("g")


@pytest.mark.parametrize(
    "profile", [None, True, [], {}, "", "ccc-extra", "CCC", "../ccc", "cgc\x00", "gggg"]
)
def test_no_open_profile_input(profile):
    with pytest.raises(BoundedCompilerEmissionError):
        placements.compile_case(profile)


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "overrides",
        "hac_ir",
        "hs_ir",
        "partition",
        "decisions",
        "residency",
        "copy_bytes",
        "latency_ns",
    ],
)
def test_modified_snapshots_rejected(field):
    value = placements.snapshot("cgc")
    value[field] = "modified"
    with pytest.raises(BoundedCompilerEmissionError):
        placements.lower(value, "cgc")


def test_cross_profile_lowering_rejected():
    with pytest.raises(BoundedCompilerEmissionError):
        placements.lower(placements.snapshot("gcg"), "cgc")


@pytest.mark.parametrize(
    "value",
    [{"x": [0] * 513}, {"x": "x" * 16385}, {"x": 2**64}, {"x": float("nan")}, {"x": object()}],
)
def test_metadata_rejected_before_compiler(value, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unbounded metadata reached compiler")

    monkeypatch.setattr(placements, "snapshot", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        placements.lower(value, "ccc")


@pytest.mark.parametrize("profile", placements.PROFILES)
def test_preflight_and_rejections_never_close_execution(profile):
    value = placements.expected_observation(profile, "matrix", True)
    with pytest.raises(BoundedCompilerEmissionError):
        placements.validate_observation(value, profile, "matrix")
    for mutation in placements.STATIC_FAULTS:
        value = placements.expected_observation(profile, "matrix", mutation=mutation)
        assert value["residency"]["completed_steps"] == 0
        assert value["numeric_observation"]["tensor_bytes"] == 0
    if profile != "ccc":
        missing = placements.expected_observation(profile, "matrix", mutation="skip-transfer")
        assert missing["residency"]["cpu_calls"] + missing["residency"]["gpu_calls"] <= 3
        assert missing["numeric_observation"]["reason_code"] == "execution_failed"
        with pytest.raises(BoundedCompilerEmissionError):
            placements.validate_observation(missing, profile, "matrix")


@pytest.mark.parametrize(
    "field",
    [
        "completed_steps",
        "cpu_calls",
        "gpu_calls",
        "upload_calls",
        "download_calls",
        "upload_bytes",
        "download_bytes",
    ],
)
def test_drift_in_completed_work_rejected(field):
    value = placements.expected_observation("cgc", "matrix")
    value["residency"][field] += 1
    with pytest.raises(BoundedCompilerEmissionError):
        placements.validate_observation(value, "cgc", "matrix")


def test_missing_duplicate_reordered_or_substituted_profiles_rejected():
    values = [placements.expected_observation(p, "matrix") for p in placements.PROFILES]
    for bad in (
        values[:-1],
        list(reversed(values)),
        [values[0]] * 8,
        [*values[:-1], placements.expected_observation("ccc", "c11")],
    ):
        with pytest.raises(BoundedCompilerEmissionError):
            placements.build_record(bad, "matrix", "sha256:" + "a" * 64)
    bad = copy.deepcopy(values)
    bad[0]["worker"] = "c11"
    with pytest.raises(BoundedCompilerEmissionError):
        placements.build_record(bad, "matrix", "sha256:" + "a" * 64)


def test_artifacts_pure_and_previous_code_unchanged(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verification executed a worker")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert placements.verify_artifacts()["status"] == "PASS"
    for name in ("generated.c", "generated.h", "kernels.cuh", "inputs.h", "oracle.h"):
        assert (placements.CONTEXT / name).read_bytes() == (
            placements.previous.CONTEXT / name
        ).read_bytes()
    operator = (placements.CONTEXT / "operator.sh").read_text()
    for flag in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--pids-limit=32",
        "--security-opt=no-new-privileges:true",
        "--memory=1g",
        "timeout 30s",
    ):
        assert flag in operator
    assert '"$image_id" /opt/tuc/proof "$profile"' in operator
    assert "--privileged" not in operator
    assert "contract-sanitized" in operator
