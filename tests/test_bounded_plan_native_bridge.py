from __future__ import annotations

import copy
import json
import subprocess

import pytest

from examples import bounded_plan_native_bridge as bridge
from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.ir.model import OperationKind
from tuc.runtime import runtime_execution_readiness_report, trusted_runtime_executor_registry


def test_core_plan_drives_schedule_but_does_not_enable_default_native_execution():
    snapshots = []
    for target in bridge.TARGETS:
        compiled = bridge.compile_chain(target)
        value = bridge.snapshot(compiled, target)
        snapshots.append(value)
        header = bridge.lower_snapshot(value, target)
        projection, activated = (2, 3) if target == "c11" else (3, 2)
        assert f"{{1U, 0U, 1U, {projection}U}}" in header
        assert f"{{2U, {projection}U, 5U, {activated}U}}" in header
        assert f"{{3U, {activated}U, 5U, 4U}}" in header
        assert compiled.partition_plan.backend_for("activated") == f"bounded-{target}"
        assert f"bounded-{target}" not in trusted_runtime_executor_registry()
        with pytest.raises(ValueError, match="no trusted executor contract"):
            runtime_execution_readiness_report(compiled.hac_ir.graph, compiled.partition_plan)
    assert snapshots[0]["hac_ir"] == snapshots[1]["hac_ir"]
    assert snapshots[0]["runtime_plan"] != snapshots[1]["runtime_plan"]
    assert snapshots[1]["memory_domain"] == "unknown"
    assert snapshots[1]["external_io_in_core_transfer_plan"] is False


@pytest.mark.parametrize("change", ["order", "backend", "layout", "domain", "input", "output",
                                   "extra_step", "hac_ir", "hs_ir", "runtime_plan", "contract"])
def test_modified_core_snapshot_cannot_reach_native_lowering(change):
    value = copy.deepcopy(bridge.snapshot(bridge.compile_chain("cuda"), "cuda"))
    if change == "order":
        value["assignments"].reverse()
    elif change in ("backend", "layout", "domain"):
        value["assignments"][0][change] = "unreviewed"
    elif change in ("input", "output"):
        value["operations"][0][change + "s"] = ["bad"]
    elif change == "extra_step":
        value["operations"].append(value["operations"][0])
    elif change == "contract":
        value["numeric_contract_digest"] = "sha256:" + "0" * 64
    else:
        value[change] += " altered"
    with pytest.raises(BoundedCompilerEmissionError):
        bridge.lower_snapshot(value, "cuda")


def test_missing_capability_cannot_silently_fall_back_in_native_dispatch():
    original = bridge.compile_chain("c11")
    cap = bridge.capability("c11")
    incomplete = BackendCapability(name=cap.name,
                                   supported_ops=frozenset({OperationKind.MATMUL}),
                                   memory_domain=cap.memory_domain)
    altered = compile_graph(original.tlir.graph, [incomplete])
    assert altered.partition_plan.backend_for("activated") == "reference-cpu"
    with pytest.raises(BoundedCompilerEmissionError):
        bridge.lower_snapshot(bridge.snapshot(altered, "c11"), "c11")


@pytest.mark.parametrize("target", [None, True, {}, "../cuda", "plugin", "gpu"])
def test_unreviewed_targets_are_rejected(target):
    with pytest.raises(BoundedCompilerEmissionError):
        bridge.compile_chain(target)


def test_generated_build_preserves_kernels_oracle_and_isolation():
    files = bridge.artifact_files()
    for name in ("generated.c", "generated.h", "kernels.cuh", "inputs.h", "oracle.h", "common.h"):
        assert files[name].encode() == (bridge.chain.CONTEXT / name).read_bytes()
    for target in bridge.TARGETS:
        for mutation in bridge.PLAN_MUTATIONS:
            assert f"/out/{mutation}" in files[f"build-{target}.sh"]
            assert f"/out/{mutation}" in files["Dockerfile"]
        native = (bridge.CONTEXT / ("host.c" if target == "c11" else "device.cu")).read_text()
        assert "plan_step(i)" in native and "switch (s.opcode)" in native
        assert "plan_valid()" in native
    assert 'cd "$(dirname "$0")/../.."' in files["operator.sh"]
    for flag in ("--network=none", "--read-only", "--cap-drop=ALL", "--memory=1g",
                 "--security-opt=no-new-privileges:true", "--pids-limit=32", "timeout 30s"):
        assert flag in files["operator.sh"]
    assert "--privileged" not in files["operator.sh"]
    assert max(len(v.encode()) for v in files.values()) < 65536


@pytest.mark.parametrize("mutation", bridge.PLAN_MUTATIONS)
def test_schedule_rejection_requires_zero_calls_and_zero_reported_tensor_bytes(mutation):
    value = bridge.chain.expected_observation("cuda")
    value.update(status="ERROR", reason_code="target_not_ready", cases_passed=0,
                 generated_function_calls=0, tensor_bytes=0, scalar_checks=0,
                 outputs_differing_from_reference64=0, numeric_contract_passed=False,
                 execution_policy_passed=False, repeated_baseline_passed=False)
    bridge.validate_negative(value, "cuda", mutation)
    with pytest.raises(BoundedCompilerEmissionError):
        bridge.validate_negative({**value, "generated_function_calls": 1}, "cuda", mutation)


def test_verification_is_pure_and_binding_rejects_plan_drift(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("verifier started a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    value = bridge.chain.expected_observation("c11")
    record = bridge.build_record(value, "c11", "sha256:" + "1" * 64)
    assert record["normal_runtime_admission"] is False
    assert record["core_snapshot_digest"] != record["dispatch_header_digest"]
    reader = bridge._read_bounded_file
    monkeypatch.setattr(bridge, "_read_bounded_file", lambda p:
                        reader(p) + (b"\n" if p.name == "c11_dispatch.h" else b""))
    with pytest.raises(BoundedCompilerEmissionError):
        bridge.verify_artifacts()


def test_dispatch_artifacts_are_reproducible():
    assert bridge.verify_artifacts()["status"] == "PASS"
    for target in bridge.TARGETS:
        value = json.loads((bridge.CONTEXT / f"{target}_plan.json").read_text())
        assert bridge.lower_snapshot(value, target) == (
            bridge.CONTEXT / f"{target}_dispatch.h").read_text()


@pytest.mark.parametrize("value", [{"x": "x" * 16385}, {"x" * 16385: 1},
                                   {"x": 2**64}, {"x": float("nan")},
                                   {"x": [0] * 513}, {"x": object()}])
def test_snapshot_budgets_reject_before_compilation(value, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unbounded metadata reached compiler")
    monkeypatch.setattr(bridge, "compile_chain", forbidden)
    with pytest.raises(BoundedCompilerEmissionError):
        bridge.lower_snapshot(value, "cuda")
