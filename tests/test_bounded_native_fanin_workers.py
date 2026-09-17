"""Synthetic protocol tests, not observed native fan-in evidence."""

import copy
import json
import re
import subprocess

import pytest

from examples import bounded_native_fanin_workers as workers
from examples.bounded_compiler_emission import BoundedCompilerEmissionError


@pytest.fixture(scope="module")
def artifacts():
    return workers.artifact_files()


@pytest.fixture
def protocol(monkeypatch, artifacts):
    # Avoid re-emitting the whole fixed corpus for every protocol-field mutation.
    monkeypatch.setattr(workers, "artifact_files", lambda: copy.deepcopy(artifacts))
    return workers


def test_artifacts_are_exact_and_candidate_is_unchanged(artifacts):
    assert workers.verify_artifacts()["native_execution_observed"] is False
    for name, value in artifacts.items():
        assert (workers.CONTEXT / name).read_bytes() == value.encode()
        assert len(value) <= 65536
    for p in workers.PROFILES:
        assert (
            artifacts[f"{p}_plan.json"].encode()
            == (workers.candidate.CONTEXT / f"{p}_plan.json").read_bytes()
        )
    emission = json.loads(artifacts["emission_plan.json"])
    assert emission["expected_rounded_outputs"] == 265
    assert emission["scalar_checks_per_profile"] == 363
    assert emission["native_execution_observed"] is False
    assert emission["normal_runtime_admission"] is False
    assert artifacts["kernels.cuh"].count("__global__ void") == 4
    for side, extent in (("left", 231), ("right", 35)):
        for name in ("generated.c", "kernels.cuh"):
            assert f"void tuc_relu_{side}" in artifacts[name]
            assert f"index < {extent}U" in artifacts[name]
            assert f"TUC_INCOMPLETE_{side.upper()}" in artifacts[name]


@pytest.mark.parametrize("field", ("operations", "tensors", "returns", "schema_version"))
def test_emission_rejects_changed_source(field):
    payload = workers.candidate.parse_source()
    payload[field] = []
    with pytest.raises(BoundedCompilerEmissionError):
        workers.emit(payload)


@pytest.mark.parametrize("profile", workers.PROFILES)
def test_fixed_lowering_checks_every_snapshot_field(profile):
    value = workers.candidate.snapshot(profile)
    assert workers.lower(value, profile)
    for field in value:
        wrong = copy.deepcopy(value)
        wrong[field] = "changed"
        with pytest.raises(BoundedCompilerEmissionError):
            workers.lower(wrong, profile)


@pytest.mark.parametrize(
    "value", ({"x": [0] * 513}, {"x": "x" * 16385}, {"x": 2**64}, {"x": float("nan")})
)
def test_budget_before_source_plan_or_observation_work(value, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unbounded metadata reached reconstruction")

    monkeypatch.setattr(workers.candidate, "snapshot", forbidden)
    monkeypatch.setattr(workers, "expected_observation", forbidden)
    for check in (
        lambda: workers.emit(value),
        lambda: workers.lower(value, "cccc"),
        lambda: workers.validate_observation(value, "cccc", "c11"),
    ):
        with pytest.raises(BoundedCompilerEmissionError):
            check()


@pytest.mark.parametrize(
    "profile,copy_bytes,buffer_bytes,left_copies,right_copies",
    (
        ("cccc", 0, 2920, 0, 0),
        ("gccc", 1848, 4768, 1, 0),
        ("cgcc", 280, 3200, 0, 1),
        ("gcgg", 1196, 4116, 0, 1),
        ("cggg", 1196, 4116, 1, 0),
        ("gggg", 1196, 4116, 0, 0),
    ),
)
def test_complete_protocol_counts(
    protocol, profile, copy_bytes, buffer_bytes, left_copies, right_copies
):
    value = protocol.expected_observation(profile, "matrix")
    c, n = value["residency"], value["numeric_observation"]
    assert c["left_producer_calls"] == c["right_producer_calls"] == c["join_calls"] == 11
    assert c["published_outputs"] == 11
    assert c["left_copy_calls"] == 11 * left_copies
    assert c["right_copy_calls"] == 11 * right_copies
    assert c["upload_bytes"] + c["download_bytes"] == 11 * copy_bytes
    assert n["tensor_bytes"] == buffer_bytes
    assert n["scalar_checks"] == 363
    assert n["generated_function_calls"] == 44
    assert protocol.validate_observation(value, profile, "matrix") == value
    for section in ("residency", "numeric_observation"):
        for key in value[section]:
            wrong = copy.deepcopy(value)
            wrong[section][key] = "changed"
            with pytest.raises(BoundedCompilerEmissionError):
                protocol.validate_observation(wrong, profile, "matrix")


@pytest.mark.parametrize("profile", workers.PROFILES)
@pytest.mark.parametrize("mutation", workers.MUTATIONS)
def test_each_synthetic_negative_protocol_rejects_as_execution(protocol, profile, mutation):
    value = protocol.expected_observation(profile, "matrix", mutation=mutation)
    assert protocol.validate_observation(value, profile, "matrix", mutation=mutation) == value
    with pytest.raises(BoundedCompilerEmissionError):
        protocol.validate_observation(value, profile, "matrix")
    n = value["numeric_observation"]
    assert n["status"] == "ERROR" and not n["numeric_contract_passed"]
    if mutation in protocol.STATIC_FAULTS:
        assert n["tensor_bytes"] == 0 and not any(value["residency"].values())
    if mutation in ("skip-left", "skip-right", "invalidate-left", "invalidate-right"):
        assert n["reason_code"] == "execution_failed"
        assert value["residency"]["join_calls"] == 0
        assert value["residency"]["published_outputs"] == 0


@pytest.mark.parametrize(
    "profile,side", (("gccc", "left"), ("cggg", "left"), ("cgcc", "right"), ("gcgg", "right"))
)
def test_required_operand_copy_fails_before_join(protocol, profile, side):
    value = protocol.expected_observation(profile, "matrix", mutation=f"skip-{side}-copy")
    c = value["residency"]
    assert c["left_producer_calls"] == c["right_producer_calls"] == 1
    assert c["join_calls"] == c[f"{side}_copy_calls"] == c["published_outputs"] == 0


@pytest.mark.parametrize("profile", workers.PROFILES)
def test_preflight_has_no_computation(protocol, profile):
    value = protocol.expected_observation(profile, "matrix", True)
    assert not any(value["residency"].values())
    assert value["numeric_observation"]["tensor_bytes"] == 0
    with pytest.raises(BoundedCompilerEmissionError):
        protocol.validate_observation(value, profile, "matrix")


@pytest.mark.parametrize(
    "profile,worker,preflight,mutation",
    (
        (None, "c11", False, None),
        ([], "matrix", False, None),
        ("gggg", "c11", False, None),
        ("ccc", "matrix", False, None),
        ("cccc", None, False, None),
        ("cccc", "cuda", False, None),
        ("cccc", "c11", 1, None),
        ("cccc", "c11", False, []),
        ("cccc", "c11", True, "skip-left"),
        ("cccc", "matrix", False, "skip-left-copy"),
        ("gggg", "matrix", False, "skip-right-copy"),
        ("gccc", "matrix", False, "unknown-profile"),
    ),
)
def test_modes_fail_closed(profile, worker, preflight, mutation):
    with pytest.raises(BoundedCompilerEmissionError):
        workers.expected_observation(profile, worker, preflight, mutation)


def test_synthetic_record_cannot_omit_reorder_or_relabel_coverage(protocol):
    values = [protocol.expected_observation(p, "matrix") for p in protocol.PROFILES]
    for wrong in (
        values[:-1],
        values[::-1],
        [values[0]] * 6,
        [protocol.expected_observation("cccc", "c11"), *values[1:]],
    ):
        with pytest.raises(BoundedCompilerEmissionError):
            protocol.build_record(wrong, "matrix", "sha256:" + "a" * 64)
    for image in (None, True, [], "latest", "sha256:" + "A" * 64):
        with pytest.raises(BoundedCompilerEmissionError):
            protocol.build_record(values, "matrix", image)
    old = protocol.fanout.expected_observation("cccc", "c11")
    with pytest.raises(BoundedCompilerEmissionError):
        protocol.validate_observation(old, "cccc", "c11")


def test_acceptance_requires_every_control_and_sanitizer(protocol, tmp_path, monkeypatch):
    files = {
        "cccc-preflight.json": protocol.expected_observation("cccc", "c11", True),
        "cccc-execution.json": protocol.expected_observation("cccc", "c11"),
        "unknown-profile.json": protocol.expected_observation(
            "cccc", "c11", mutation="unknown-profile"
        ),
        "sanitized.json": protocol.expected_observation("cccc", "c11"),
        "contract-sanitized.json": protocol.sanitizer_observation(),
        **{
            f"cccc-{m}.json": protocol.expected_observation("cccc", "c11", mutation=m)
            for m in protocol.mutations_for("cccc")
        },
    }

    def load(path):
        if path.name not in files:
            raise OSError("missing synthetic observation")
        return copy.deepcopy(files[path.name])

    monkeypatch.setattr(protocol, "load_observation", load)
    record = protocol.accept_directory(tmp_path, "c11", "sha256:" + "a" * 64)
    assert record["observations"] == [files["cccc-execution.json"]]
    assert record["normal_runtime_admission"] is False
    for name in tuple(files):
        original = files.pop(name)
        with pytest.raises(OSError):
            protocol.accept_directory(tmp_path, "c11", "sha256:" + "a" * 64)
        files[name] = original
    files["contract-sanitized.json"]["profiles_checked"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        protocol.accept_directory(tmp_path, "c11", "sha256:" + "a" * 64)


def test_pure_verifier_and_operator_boundary(monkeypatch, artifacts):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier launched a process")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert workers.verify_artifacts()["status"] == "PASS"
    operator = (workers.CONTEXT / "operator.sh").read_text()
    for flag in (
        "--network=none",
        "--read-only",
        "--user=10001:10001",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=32",
        "--memory=1g",
        "--cpus=1",
        "timeout 30s",
        "--pull=never",
        "--log-driver=none",
    ):
        assert flag in operator
    assert (
        "--privileged" not in operator and "--mount" not in operator and "--volume" not in operator
    )
    assert '"$image_id" /opt/tuc/proof "$profile"' in operator
    assert re.search(r'^mutations="([^"]+)"', operator, re.M)[1].split() == list(workers.MUTATIONS)
    build = (workers.CONTEXT / "build-cuda.sh").read_text()
    assert "--fmad=false --ftz=false" in build and "--list-ptx" in build
    assert "code=sm_86" in build and "code=compute_86" not in build
    ignored = artifacts["Dockerfile.dockerignore"]
    assert ignored.startswith("**\n") and "operator.sh" not in ignored
    for path in workers.CONTEXT.iterdir():
        assert path.stat().st_size <= 65536


def test_drift_is_detected(artifacts, monkeypatch):
    original = workers._read_bounded_file

    def read(path):
        return b"changed" if path == workers.CONTEXT / "plans.h" else original(path)

    monkeypatch.setattr(workers, "_read_bounded_file", read)
    with pytest.raises(BoundedCompilerEmissionError):
        workers.verify_artifacts()


def test_cpu_ci_is_pinned_read_only_and_has_no_gpu_operator():
    workflow = (workers.ROOT / ".github/workflows/bounded-c11-proof.yml").read_text()
    assert "permissions:\n  contents: read\n" in workflow
    job = workflow.split("\n  native-fanin:\n", 1)[1]
    assert "    runs-on: ubuntu-24.04\n    timeout-minutes: 15\n" in job
    uses = re.findall(r"uses: (\S+)", job)
    assert len(uses) == 2
    assert all(re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", action) for action in uses)
    assert "persist-credentials: false" in job
    assert "--require-hashes -r requirements/ci.txt" in job
    assert "sh docker/native-fanin/operator.sh --c11" in job
    assert "--matrix-reviewed" not in job and "permissions:" not in job
