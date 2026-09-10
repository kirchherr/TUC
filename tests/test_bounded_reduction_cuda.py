from __future__ import annotations

import copy
import json

import pytest

from examples.bounded_compiler_emission import BoundedCompilerEmissionError
from examples.bounded_reduction_c11 import (
    ROOT,
    load_observation,
    parse_fixed_source,
)
from examples.bounded_reduction_c11 import (
    expected_observation as expected_cpu,
)
from examples.bounded_reduction_c11 import (
    verify_artifacts as verify_cpu,
)
from examples.bounded_reduction_cuda import (
    BLOCKED_CLAIMS,
    artifact_files,
    build_equivalence,
    build_record,
    expected_observation,
    validate_observation,
    verify_artifacts,
)


def test_exact_source_produces_two_bounded_cuda_kernels() -> None:
    plan = verify_artifacts()
    files = artifact_files(parse_fixed_source())
    assert plan["source_intent_digest"] == verify_cpu().plan["source_intent_digest"]
    assert plan["output_shape"] == [4]
    assert plan["working_set_bytes"] == 240
    assert plan["ptx_jit"] is False
    assert files["kernels.cuh"].count("__global__ void") == 2
    assert "<<<" not in files["kernels.cuh"]
    assert plan["generated_source_digest"] != plan["c11_source_digest"]


@pytest.mark.parametrize("mutation", ["axis", "shape", "injection", "family", "extra"])
def test_unreviewed_source_never_reaches_cuda_emission(mutation: str) -> None:
    payload = copy.deepcopy(parse_fixed_source())
    if mutation == "axis":
        payload["operations"][1]["attributes"]["axis"] = 0
    elif mutation == "shape":
        payload["tensors"][0]["shape"][0] = 2**31
    elif mutation == "injection":
        payload["operations"][1]["name"] = "system(injected)"
    elif mutation == "family":
        payload["operations"][1]["family"] = "elementwise"
    else:
        payload["execute"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        artifact_files(payload)


@pytest.mark.parametrize("field,value", [
    ("target", "nvidia_cuda_sm70"), ("visible_device_count", 2),
    ("generated_function_calls", True), ("working_set_bytes", 256),
    ("reference_correctness", 1), ("security_boundary_passed", False),
    ("output_shape", [4, 2]), ("source_intent_digest", "sha256:" + "0" * 64),
    ("generated_source_digest", "sha256:" + "0" * 64),
    ("vector_digest", "sha256:" + "0" * 64),
])
def test_worker_observation_rejects_drift(field, value) -> None:
    report = expected_observation("execute")
    report[field] = value
    with pytest.raises(BoundedCompilerEmissionError):
        validate_observation(report)


def test_preflight_and_extra_claim_are_not_execution() -> None:
    assert validate_observation(expected_observation("preflight"), "preflight")
    with pytest.raises(BoundedCompilerEmissionError):
        build_record(expected_observation("preflight"), "sha256:" + "1" * 64)
    report = expected_observation("execute")
    report["universal_hardware"] = True
    with pytest.raises(BoundedCompilerEmissionError):
        validate_observation(report)


@pytest.mark.parametrize("image", ["latest", "sha256:bad", "sha256:" + "a" * 65, "x;sh"])
def test_record_rejects_noncanonical_image_id(image) -> None:
    with pytest.raises(BoundedCompilerEmissionError):
        build_record(expected_observation("execute"), image)


def test_equivalence_requires_validated_children_and_current_program_binding() -> None:
    cpu = expected_cpu("execute", verify_cpu().plan)
    record = build_record(expected_observation("execute"), "sha256:" + "1" * 64)
    report = build_equivalence(cpu, record)
    assert report["targets"] == ["c11_x86_64", "nvidia_cuda_sm86"]
    assert report["blocked_claims"] == BLOCKED_CLAIMS
    record["program_files_digest"] = "sha256:" + "0" * 64
    with pytest.raises(BoundedCompilerEmissionError):
        build_equivalence(cpu, record)
    with pytest.raises(BoundedCompilerEmissionError):
        build_equivalence(expected_cpu("preflight", verify_cpu().plan), record)


def test_emission_and_validation_never_spawn_processes(monkeypatch) -> None:
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError("pure verifier launched a process")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    verify_artifacts()
    validate_observation(expected_observation("execute"))


def test_native_procedure_has_fixed_containment_and_negative_probes() -> None:
    script = (ROOT / "scripts/run_bounded_reduction_cuda_proof.sh").read_text()
    for control in (
        "--network=none", "--read-only", "--user=10001:10001", "--gpus=device=0",
        "--cap-drop=ALL", "--security-opt=no-new-privileges:true", "--memory=1g",
        "--pids-limit=32", "timeout 30s", "--pull=never", "trap cleanup",
        "missing-sum accidental-relu wrong-axis", "--execute-reviewed-gpu",
    ):
        assert control in script
    for forbidden in ("--privileged", "--volume", "--gpus=all", "docker system prune"):
        assert forbidden not in script
    build = (ROOT / "docker/reduction-cuda/build.sh").read_text()
    assert "--generate-code=arch=compute_86,code=sm_86" in build
    assert '--list-ptx "$1")"' in build
    assert "--fmad=false" in build


def test_accepted_physical_gpu_record_is_required_and_matches_current_program() -> None:
    path = ROOT / "tests/golden/proofs/bounded_reduction_cuda_record.json"
    report = build_equivalence(
        load_observation(ROOT / "tests/golden/proofs/bounded_reduction_c11_observation.json"),
        load_observation(path),
    )
    golden = ROOT / "tests/golden/proofs/bounded_reduction_target_equivalence.json"
    assert report == json.loads(golden.read_text())


@pytest.mark.parametrize("mutation", ["extra", "missing", "preflight", "cpu_vector"])
def test_record_and_baseline_cannot_be_promoted_by_metadata_mutation(mutation) -> None:
    cpu = expected_cpu("execute", verify_cpu().plan)
    record = build_record(expected_observation("execute"), "sha256:" + "1" * 64)
    if mutation == "extra":
        record["independent_reproduction"] = True
    elif mutation == "missing":
        del record["observation"]
    elif mutation == "preflight":
        record["observation"] = expected_observation("preflight")
    else:
        cpu["vector_digest"] = "sha256:" + "0" * 64
    with pytest.raises(BoundedCompilerEmissionError):
        build_equivalence(cpu, record)
