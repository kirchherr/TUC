from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from examples.bounded_compiler_emission import (
    WORKLOAD_MANIFEST_PATH,
    BoundedCompilerEmissionError,
    _load_json,
)
from examples.bounded_reduction_c11 import (
    BLOCKED_CLAIMS,
    EXPECTED_OUTPUT,
    ROOT,
    artifact_files,
    build_artifacts,
    expected_observation,
    load_observation,
    parse_fixed_source,
    validate_observation,
    verify_artifacts,
)


def test_live_source_parse_matches_exact_reviewed_reduction_artifacts() -> None:
    artifacts = verify_artifacts()
    assert artifacts == build_artifacts(parse_fixed_source())
    assert artifacts.plan["operation_families"] == ["matmul", "reduction"]
    assert artifacts.plan["output_shape"] == [4]
    assert artifacts.plan["working_set_bytes"] == 240
    assert artifacts.plan["blocked_claims"] == BLOCKED_CLAIMS
    assert len(artifact_files(artifacts)) == 5


def test_reference_is_exact_and_distinguishes_wrong_code() -> None:
    workload = _load_json(WORKLOAD_MANIFEST_PATH)
    inputs = workload["inputs"]
    a = np.array(inputs["a"], dtype=np.float32)
    b = np.array(inputs["b"], dtype=np.float32)
    projection = a @ b
    expected = np.array(EXPECTED_OUTPUT, dtype=np.float32)
    np.testing.assert_array_equal(projection.sum(axis=1), expected)
    assert not np.array_equal(projection[:, 1], expected)
    assert not np.array_equal(np.maximum(projection.sum(axis=1), 0), expected)
    assert not np.array_equal(projection.reshape(-1).reshape(2, 4).sum(axis=0), expected)


@pytest.mark.parametrize("mutation", ["axis", "shape", "semantics", "name", "return", "extra"])
def test_unreviewed_intent_cannot_reach_emission(mutation: str) -> None:
    payload = copy.deepcopy(parse_fixed_source())
    if mutation == "axis":
        payload["operations"][1]["attributes"]["axis"] = 0
    elif mutation == "shape":
        payload["tensors"][0]["shape"][0] = 2**31
    elif mutation == "semantics":
        payload["operations"][1]["family"] = "elementwise"
    elif mutation == "name":
        payload["operations"][0]["name"] = 'x; system("injected");'
    elif mutation == "return":
        payload["returns"][0]["tensor_name"] = "projection"
    else:
        payload["command"] = "unreviewed"
    with pytest.raises(BoundedCompilerEmissionError, match="Source Intent drift"):
        build_artifacts(payload)


@pytest.mark.parametrize("value", [None, True, [], float("nan"), {"x": object()}])
def test_non_plain_or_wrong_type_intent_rejected(value: object) -> None:
    with pytest.raises(BoundedCompilerEmissionError):
        build_artifacts(value)


def test_emitter_does_not_invoke_source_imports_or_external_processes(monkeypatch) -> None:
    import subprocess
    import sys

    def forbidden(*args, **kwargs):
        raise AssertionError("external process reached during pure emission")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    verify_artifacts()
    assert "triton" not in sys.modules


@pytest.mark.parametrize("mode", ["preflight", "execute"])
def test_observation_validator_and_closed_schema(mode: str) -> None:
    report = expected_observation(mode, verify_artifacts().plan)
    assert validate_observation(report, mode) == report
    schema = json.loads(
        (ROOT / "schemas/bounded_reduction_c11_observation.v0.schema.json").read_text()
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(report) == set(schema["properties"])


@pytest.mark.parametrize("field,value", [
    ("status", "PASS_WITH_WARNINGS"), ("mode", "preflight"),
    ("reference_correctness", 1), ("generated_function_calls", True),
    ("source_intent_digest", "sha256:" + "0" * 64),
    ("generated_source_digest", "sha256:" + "0" * 64),
    ("vector_digest", "sha256:" + "0" * 64),
    ("output_shape", [2]), ("working_set_bytes", 256),
    ("raw_values_serialized", True), ("security_boundary_passed", False),
])
def test_observation_rejects_semantic_provenance_and_type_drift(field, value) -> None:
    report = expected_observation("execute", verify_artifacts().plan)
    report[field] = value
    with pytest.raises(BoundedCompilerEmissionError, match="observation rejected"):
        validate_observation(report)


def test_preflight_and_extra_claims_cannot_become_execution_evidence() -> None:
    plan = verify_artifacts().plan
    with pytest.raises(BoundedCompilerEmissionError):
        validate_observation(expected_observation("preflight", plan))
    report = expected_observation("execute", plan)
    report["universal_hardware"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        validate_observation(report)


def test_artifact_tamper_is_rejected(tmp_path: Path, monkeypatch) -> None:
    import examples.bounded_reduction_c11 as proof
    for name, content in artifact_files(build_artifacts(parse_fixed_source())).items():
        (tmp_path / name).write_bytes(content.encode("utf-8"))
    monkeypatch.setattr(proof, "CONTEXT", tmp_path)
    (tmp_path / "generated.c").write_text("int main(void) { return 0; }", encoding="utf-8")
    with pytest.raises(BoundedCompilerEmissionError, match="artifact drift"):
        verify_artifacts()


@pytest.mark.parametrize("raw", [
    b'{"mode":"execute","mode":"preflight"}', b'{"value":NaN}',
    b'\xff', b'{', b'', b' ' * (64 * 1024 + 1), b'[' * 2000,
], ids=["duplicate", "nonfinite", "utf8", "syntax", "empty", "oversize", "deep"])
def test_observation_loader_rejects_malformed_and_unbounded_data(tmp_path, raw) -> None:
    path = tmp_path / "observation.json"
    path.write_bytes(raw)
    with pytest.raises(BoundedCompilerEmissionError):
        load_observation(path)


def test_observation_loader_rejects_special_files(tmp_path) -> None:
    import os

    with pytest.raises(BoundedCompilerEmissionError):
        load_observation(tmp_path)
    if hasattr(os, "mkfifo"):
        fifo = tmp_path / "fifo"
        os.mkfifo(fifo)
        with pytest.raises(BoundedCompilerEmissionError):
            load_observation(fifo)


def test_accepted_native_observation_matches_current_program() -> None:
    report = load_observation(ROOT / "tests/golden/proofs/bounded_reduction_c11_observation.json")
    assert validate_observation(report)["reference_correctness"] is True


def test_native_procedure_enforces_containment_and_wrong_code_checks() -> None:
    procedure = (ROOT / "scripts/run_bounded_reduction_c11_proof.sh").read_text()
    for control in (
        "--network=none", "--read-only", "--cap-drop=ALL", "--user=10001:10001",
        "--security-opt=no-new-privileges:true", "--memory=128m", "timeout 20s",
        "--pids-limit=8", "trap cleanup", "--pull=never", "--log-driver=none",
        "missing-sum accidental-relu wrong-axis", "sanitizer-tests",
    ):
        assert control in procedure
    assert "--privileged" not in procedure
    assert "--gpus" not in procedure
    assert "--volume" not in procedure
