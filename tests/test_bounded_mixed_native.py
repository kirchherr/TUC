import copy
import subprocess

import pytest

from examples import bounded_mixed_native as mixed
from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _digest_payload
from examples.bounded_reduction_c11 import load_observation
from tuc.runtime import runtime_execution_readiness_report


@pytest.mark.parametrize("target", mixed.TARGETS)
def test_plan_lowering_and_native_admission_stays_closed(target):
    value = mixed.snapshot(target)
    assert mixed.lower(value, target) == (mixed.CONTEXT / f"{target}_plan.h").read_text()
    compiled, _ = mixed.compile_case(target)
    with pytest.raises(ValueError, match="no trusted executor contract"):
        runtime_execution_readiness_report(compiled.hac_ir.graph, compiled.partition_plan)


@pytest.mark.parametrize(
    "change",
    [
        "step",
        "slot",
        "space",
        "bytes",
        "domain",
        "duplicate",
        "delete",
        "copy-bytes",
        "latency",
        "core",
        "command",
        "target",
    ],
)
def test_unreviewed_schedule_rejected(change):
    value = mixed.snapshot("mixed")
    if change == "step":
        value["residency"]["steps"].reverse()
    elif change == "slot":
        value["residency"]["steps"][0]["outputs"] = [255]
    elif change in ("space", "bytes", "domain"):
        b = value["residency"]["buffers"][0]
        if change == "space":
            b["space"]["name"] = "accelerator"
        elif change == "domain":
            b["space"]["physical_kind"] = "gpu_hbm"
        else:
            b["bytes"] += 4
    elif change == "duplicate":
        value["residency"]["steps"].append(copy.deepcopy(value["residency"]["steps"][0]))
    elif change == "delete":
        value["residency"]["steps"].pop()
    else:
        key = {
            "copy-bytes": "copy_bytes",
            "latency": "latency_ns",
            "core": "hac_ir",
            "command": "command",
            "target": "target",
        }[change]
        value[key] = 0 if change in ("latency", "copy-bytes") else "modified"
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.lower(value, "mixed")


@pytest.mark.parametrize(
    "value",
    [{"x": [0] * 513}, {"x": "x" * 16385}, {"x": 2**64}, {"x": float("nan")}, {"x": object()}],
)
def test_unbounded_metadata_rejected_before_compilation(value, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unbounded input reached compiler")

    monkeypatch.setattr(mixed, "snapshot", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.lower(value, "mixed")


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
def test_completion_counters_bind_actual_placement(field):
    value = {
        "schema_version": "tuc.bounded_mixed_native_observation.v0",
        "plan_digest": _digest_payload(mixed.snapshot("mixed")),
        "residency": mixed.counters("mixed", 11),
        "numeric_observation": mixed.expected_numeric("mixed"),
    }
    value["residency"][field] += 1
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.validate_observation(value, "mixed")


def test_prior_kernels_and_oracle_are_unchanged_and_verifier_is_pure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier started native execution")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert mixed.verify_artifacts()["status"] == "PASS"
    for name in ("generated.c", "generated.h", "kernels.cuh", "inputs.h", "oracle.h"):
        assert (mixed.CONTEXT / name).read_bytes() == (
            mixed.bridge.chain.CONTEXT / name
        ).read_bytes()
    operator = (mixed.CONTEXT / "operator.sh").read_text()
    for flag in (
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--memory=1g",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=32",
        "timeout 30s",
    ):
        assert flag in operator
    assert "--privileged" not in operator
    assert '--target "$build_target-runtime"' in operator


def test_observed_native_comparison_and_cpu_sanitizers():
    directory = mixed.ROOT / "tests/golden/proofs"
    records = [load_observation(directory / f"mixed_native_{t}_record.json") for t in mixed.TARGETS]
    assert mixed.compare_records(*records) == load_observation(
        directory / "mixed_native_comparison.json"
    )
    assert records[1]["observation"]["residency"]["cpu_calls"] == 11
    assert records[1]["observation"]["residency"]["gpu_calls"] == 22
    assert records[0]["observation"] == load_observation(
        directory / "mixed_native_c11_sanitized.json"
    )
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.compare_records(records[0], {**records[1], "program_files_digest": "changed"})


@pytest.mark.parametrize(
    "target,mutation",
    [
        (t, m)
        for t in mixed.TARGETS
        for m in (*mixed.MUTATIONS, *(("skip-transfer",) if t == "mixed" else ()))
    ],
)
def test_observed_rejections_cannot_be_execution_evidence(target, mutation):
    value = load_observation(
        mixed.ROOT / "tests/golden/proofs" / f"mixed_native_{target}_{mutation}.json"
    )
    mixed.validate_observation(value, target, mutation=mutation)
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.validate_observation(value, target)
    if mutation in mixed.STATIC_FAULTS:
        assert value["residency"] == mixed.counters(target, 0)
        assert value["numeric_observation"]["tensor_bytes"] == 0
    elif mutation == "skip-transfer":
        assert value["residency"]["gpu_calls"] == 1
        assert value["residency"]["cpu_calls"] == 0
        assert value["residency"]["download_calls"] == 0


@pytest.mark.parametrize("target", mixed.TARGETS)
def test_observed_preflight_is_not_execution(target):
    value = load_observation(
        mixed.ROOT / "tests/golden/proofs" / f"mixed_native_{target}_preflight.json"
    )
    mixed.validate_observation(value, target, True)
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.build_record(value, target, "sha256:" + "1" * 64)


@pytest.mark.parametrize("target", mixed.TARGETS)
def test_old_numeric_schema_cannot_be_reinterpreted_as_mixed_evidence(target):
    value = {
        "schema_version": "tuc.bounded_mixed_native_observation.v0",
        "plan_digest": _digest_payload(mixed.snapshot(target)),
        "residency": mixed.counters(target, 11),
        "numeric_observation": mixed.expected_numeric(target),
    }
    value["numeric_observation"]["schema_version"] = "tuc.bounded_chain_observation.v0"
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.validate_observation(value, target)


@pytest.mark.parametrize(
    "preflight,mutation",
    [
        (0, None),
        (1, None),
        (None, None),
        ("true", None),
        (False, 0),
        (False, ""),
        (False, []),
        (False, 1),
    ],
)
def test_observation_modes_fail_closed(preflight, mutation):
    with pytest.raises(BoundedCompilerEmissionError):
        mixed.validate_observation({}, "mixed", preflight, mutation)
