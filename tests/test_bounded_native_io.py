from __future__ import annotations

import copy
import json
import subprocess

import pytest

from examples import bounded_native_io as native
from examples.bounded_compiler_emission import BoundedCompilerEmissionError, _digest_payload
from examples.bounded_reduction_c11 import load_observation
from tuc.runtime import runtime_execution_readiness_report


@pytest.mark.parametrize("target", native.TARGETS)
def test_boundary_plan_derives_shapes_slots_and_explicit_address_spaces(target):
    plan = native.io_plan(target)
    assert [r["tensor"] for r in plan["steps"]] == ["a", "b", "row_sum"]
    assert [r["bytes"] for r in plan["steps"]] == [924, 140, 132]
    assert [r["slot"] for r in plan["steps"]] == [0, 1, 4]
    assert plan["buffer_bytes"] == [924, 140, 660, 660, 132]
    assert plan["latency_ns"] is None and plan["energy_pj"] is None
    assert plan["normal_runtime_admission"] is False
    if target == "cuda":
        assert plan["cross_space_bytes_per_run"] == 1196
        assert plan["memory_spaces"]["execution"] == {
            "address_space": "device_global", "physical_kind": "unknown"}
        assert [r["mode"] for r in plan["steps"]] == ["upload", "upload", "download"]
    else:
        assert plan["cross_space_bytes_per_run"] == 0
        assert all(r["mode"] == "host_binding" for r in plan["steps"])
    compiled = native.bridge.compile_chain(target)
    assert not compiled.partition_plan.transfer_edges
    with pytest.raises(ValueError, match="no trusted executor contract"):
        runtime_execution_readiness_report(compiled.hac_ir.graph, compiled.partition_plan)


@pytest.mark.parametrize("target", native.TARGETS)
@pytest.mark.parametrize("field,value", [("bytes", 0), ("bytes", 928), ("slot", 1),
    ("mode", "download"), ("phase", "after_compute"), ("source_space", "device_global"),
    ("target_space", "unreviewed"), ("shape", [33, 6]), ("dtype", "float64"),
    ("layout", "blocked"), ("tensor", "b")])
def test_modified_boundary_row_rejected(target, field, value):
    plan = native.io_plan(target)
    plan["steps"][0][field] = value
    with pytest.raises(BoundedCompilerEmissionError):
        native.lower_io(plan, target)


@pytest.mark.parametrize("change", ["delete", "duplicate", "reorder", "late", "technology",
                                   "free_latency", "bytes", "core", "extra", "shape"])
def test_global_plan_drift_rejected(change):
    plan = native.io_plan("cuda")
    if change == "delete":
        plan["steps"].pop()
    elif change == "duplicate":
        plan["steps"].append(copy.deepcopy(plan["steps"][0]))
    elif change == "reorder":
        plan["steps"].reverse()
    elif change == "late":
        plan["steps"][2]["phase"] = "before_compute"
    elif change == "technology":
        plan["memory_spaces"]["execution"]["physical_kind"] = "gpu_hbm"
    elif change == "free_latency":
        plan["latency_ns"] = 0
    elif change == "bytes":
        plan["cross_space_bytes_per_run"] = 0
    elif change == "core":
        plan["core_snapshot_digest"] = "sha256:" + "0" * 64
    elif change == "shape":
        plan["buffer_bytes"][0] = 2**63
    else:
        plan["command"] = "untrusted"
    with pytest.raises(BoundedCompilerEmissionError):
        native.lower_io(plan, "cuda")


@pytest.mark.parametrize("value", [{"x": "x" * 16385}, {"x": 2**64}, {"x": float("nan")},
                                  {"x": [0] * 513}, {"x": object()}])
def test_resource_limits_before_plan_reconstruction(value, monkeypatch):
    def forbidden(*args):
        raise AssertionError("unbounded value reached planner")
    monkeypatch.setattr(native, "io_plan", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        native.lower_io(value, "cuda")


def fixture(target, preflight=False):
    return {"schema_version": "tuc.bounded_native_io_observation.v0",
            "io_plan_digest": _digest_payload(native.io_plan(target)),
            "io": native.io_counters(target, 0 if preflight else 11),
            "numeric_observation": native.bridge.chain.expected_observation(target, preflight)}


@pytest.mark.parametrize("field", ["completed_steps", "host_bindings", "upload_calls",
                                 "upload_bytes", "download_calls", "download_bytes"])
def test_metadata_counter_tampering_rejected(field):
    observation = fixture("cuda")
    observation["io"][field] += 1
    with pytest.raises(BoundedCompilerEmissionError):
        native.validate_observation(observation, "cuda")


@pytest.mark.parametrize("target", native.TARGETS)
def test_preflight_is_not_execution(target):
    observation = fixture(target, True)
    native.validate_observation(observation, target, True)
    with pytest.raises(BoundedCompilerEmissionError):
        native.build_record(observation, target, "sha256:" + "1" * 64)


def test_artifacts_preserve_previous_proofs_and_verification_is_pure(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier executed native code")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert native.verify_artifacts()["status"] == "PASS"
    files = native.artifact_files()
    for name in ("generated.c", "generated.h", "kernels.cuh", "inputs.h", "oracle.h",
                 "c11_dispatch.h", "cuda_dispatch.h", "c11_plan.json", "cuda_plan.json"):
        assert files[name].encode() == (native.bridge.CONTEXT / name).read_bytes()
    for target in native.TARGETS:
        plan = json.loads((native.CONTEXT / f"{target}_io.json").read_text())
        assert native.lower_io(plan, target) == files[f"{target}_io.h"]
        for fault in native.IO_MUTATIONS:
            assert "/out/" + fault in files[f"build-{target}.sh"]
            assert "/out/" + fault in files["Dockerfile"]
    for flag in ("--network=none", "--read-only", "--cap-drop=ALL", "--memory=1g",
                 "--security-opt=no-new-privileges:true", "--pids-limit=32", "timeout 30s"):
        assert flag in files["operator.sh"]
    assert "--privileged" not in files["operator.sh"]


@pytest.mark.parametrize("target", native.TARGETS)
def test_skip_output_is_detected_even_when_all_kernels_ran(target):
    observation = fixture(target)
    observation["io"] = native.io_counters(target, 1, True)
    observation["numeric_observation"].update(
        status="ERROR", reason_code="execution_failed", cases_passed=0, failed_run_index=0,
        generated_function_calls=3, scalar_checks=0, outputs_differing_from_reference64=0,
        numeric_contract_passed=False, execution_policy_passed=False,
        repeated_baseline_passed=False)
    native.validate_observation(observation, target, mutation="io-skip-output")
    with pytest.raises(BoundedCompilerEmissionError):
        native.build_record(observation, target, "sha256:" + "1" * 64)


def test_actual_native_records_bind_completed_io_and_numerical_contract():
    directory = native.ROOT / "tests/golden/proofs"
    records = [load_observation(directory / f"native_io_{t}_record.json") for t in native.TARGETS]
    comparison = native.compare_records(*records)
    assert comparison == load_observation(directory / "native_io_comparison.json")
    assert comparison["cuda_copy_calls"] == 33
    assert comparison["cuda_copy_bytes"] == 13156
    assert comparison["latency_ns"] is None
    assert comparison["external_io_in_core_partition_plan"] is False
    assert records[0]["observation"]["io"]["host_bindings"] == 33
    assert records[1]["observation"]["io"]["upload_bytes"] == 11704
    sanitized = load_observation(directory / "native_io_c11_sanitized.json")
    assert native.validate_observation(sanitized, "c11") == records[0]["observation"]
    with pytest.raises(BoundedCompilerEmissionError):
        native.compare_records(records[0], {**records[1], "program_files_digest": "altered"})


@pytest.mark.parametrize("target", native.TARGETS)
@pytest.mark.parametrize("mutation", native.MUTATIONS)
def test_actual_native_rejections(target, mutation):
    value = load_observation(native.ROOT / "tests/golden/proofs" /
                             f"native_io_{target}_{mutation}.json")
    native.validate_observation(value, target, mutation=mutation)
    with pytest.raises(BoundedCompilerEmissionError):
        native.validate_observation(value, target)
    if mutation in (*native.bridge.PLAN_MUTATIONS, *native.IO_MUTATIONS):
        assert value["io"] == native.io_counters(target, 0)
        assert value["numeric_observation"]["generated_function_calls"] == 0
        assert value["numeric_observation"]["tensor_bytes"] == 0
    elif mutation == "io-skip-output":
        assert value["io"]["completed_steps"] == 2
        assert value["numeric_observation"]["generated_function_calls"] == 3


@pytest.mark.parametrize("target", native.TARGETS)
def test_actual_native_preflight_never_claims_execution(target):
    value = load_observation(native.ROOT / "tests/golden/proofs" /
                             f"native_io_{target}_preflight.json")
    native.validate_observation(value, target, True)
    assert value["io"] == native.io_counters(target, 0)
    with pytest.raises(BoundedCompilerEmissionError):
        native.build_record(value, target, "sha256:" + "1" * 64)
