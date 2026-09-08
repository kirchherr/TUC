from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import examples.bounded_compiler_emission as emission
import examples.bounded_compiler_emitted_gpu_proof as proof
from examples.bounded_compiler_emission import (
    BoundedCompilerEmissionError,
    assert_compiler_emission_source_intent,
    build_compiler_emission_artifacts,
    dump_compiler_emission_plan,
    validate_checked_in_compiler_emission,
)
from examples.bounded_compiler_emitted_gpu_proof import (
    PROFILE,
    BoundedCompilerEmittedGpuProofError,
    assert_compiler_emitted_gpu_observation_report,
    build_compiler_emitted_gpu_observation_report,
    dump_compiler_emitted_gpu_observation_report,
    validate_compiler_emitted_gpu_sources,
)
from examples.bounded_gpu_observation_proof import (
    GpuObservationError,
    _digest_payload,
    _expected_build_args,
    _expected_worker_response,
    _parse_args,
    _validate_compose_config,
    _validate_image_metadata,
    _validate_static_sources,
)

SCHEMA_PATH = Path(
    "schemas/bounded_compiler_emitted_gpu_observation_report.v0.schema.json"
)
DOC_PATH = Path("docs/BOUNDED_COMPILER_EMITTED_GPU_PROOF.md")
THREAT_MODEL_PATH = Path("docs/BOUNDED_COMPILER_EMITTED_GPU_THREAT_MODEL.md")
RFC_PATH = Path("rfcs/0302-bounded-compiler-emitted-gpu-proof.md")
PHYSICAL_OBSERVATION_PATH = Path(
    "tests/golden/proofs/bounded_compiler_emitted_gpu_observation_report.json"
)


def _source_intent() -> dict[str, object]:
    return emission._load_json(emission.SOURCE_INTENT_PATH)


def _workload() -> dict[str, object]:
    return emission._load_json(emission.WORKLOAD_MANIFEST_PATH)


def _image_metadata() -> dict[str, object]:
    build_args = _expected_build_args(PROFILE)
    labels = {
        "io.tuc.gpu-observation.contract": PROFILE.proof_contract,
        "io.tuc.gpu-observation.header-digest": build_args[
            "TUC_GPU_OBSERVATION_HEADER_DIGEST"
        ],
        "io.tuc.gpu-observation.source-digest": build_args[
            "TUC_GPU_OBSERVATION_SOURCE_DIGEST"
        ],
        "io.tuc.gpu-observation.workload-digest": build_args[
            "TUC_GPU_OBSERVATION_WORKLOAD_DIGEST"
        ],
        "org.opencontainers.image.source": "https://github.com/kirchherr/TUC",
        "org.opencontainers.image.title": PROFILE.image_title,
        "org.opencontainers.image.version": PROFILE.image_version,
    }
    for build_arg, label, _path in PROFILE.extra_digest_bindings:
        labels[label] = build_args[build_arg]
    return {
        "Architecture": "amd64",
        "Config": {
            "Cmd": ["--preflight"],
            "Entrypoint": [PROFILE.entrypoint],
            "Env": [
                "CUDA_CACHE_DISABLE=1",
                "CUDA_DISABLE_PTX_JIT=1",
                "CUDA_VISIBLE_DEVICES=0",
                "NVIDIA_DRIVER_CAPABILITIES=compute",
                "NVIDIA_VISIBLE_DEVICES=0",
            ],
            "Labels": labels,
            "User": "10001:10001",
            "WorkingDir": "/run/tuc",
        },
        "Id": "sha256:" + "3" * 64,
        "Os": "linux",
    }


def _build_report() -> dict[str, object]:
    return build_compiler_emitted_gpu_observation_report(
        _expected_worker_response("execute", PROFILE),
        proof._synthetic_compose_config(PROFILE),
        _image_metadata(),
        driver_security_reviewed=True,
        shared_display_risk_acknowledged=True,
    )


def test_exact_source_intent_emits_checked_artifacts_byte_for_byte() -> None:
    artifacts = build_compiler_emission_artifacts(_source_intent(), _workload())

    assert validate_checked_in_compiler_emission() == artifacts
    assert artifacts.kernel_header == emission.EMITTED_KERNEL_PATH.read_text(
        encoding="utf-8"
    )
    assert artifacts.workload_header == emission.WORKLOAD_HEADER_PATH.read_text(
        encoding="utf-8"
    )
    assert dump_compiler_emission_plan(
        artifacts.plan, _source_intent(), _workload()
    ) == emission.EMISSION_PLAN_PATH.read_text(encoding="utf-8")
    assert artifacts.kernel_header.count("__global__ void") == 2
    assert artifacts.plan["runtime_generated_code"] is False


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("name",), "research_matmul_elementwise; system('id')"),
        (("operations", 1, "attributes", "elementwise_kind"), "identity"),
        (("tensors", 2, "shape"), [8, 4]),
    ],
)
def test_source_intent_semantic_or_identifier_drift_is_rejected(
    path: tuple[object, ...],
    value: object,
) -> None:
    source: object = copy.deepcopy(_source_intent())
    cursor = source
    for key in path[:-1]:
        cursor = cursor[key]  # type: ignore[index]
    cursor[path[-1]] = value  # type: ignore[index]

    with pytest.raises(BoundedCompilerEmissionError, match="digest drift"):
        assert_compiler_emission_source_intent(source)


def test_workload_drift_is_rejected_before_emission() -> None:
    workload = copy.deepcopy(_workload())
    inputs = workload["inputs"]
    assert isinstance(inputs, dict)
    a = inputs["a"]
    assert isinstance(a, list)
    first_row = a[0]
    assert isinstance(first_row, list)
    first_row[0] = 4096.0

    with pytest.raises(BoundedCompilerEmissionError, match="digest drift"):
        build_compiler_emission_artifacts(_source_intent(), workload)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":"x","schema_version":"y"}',
        b'{"value":NaN}',
    ],
)
def test_compiler_emission_json_rejects_ambiguous_numbers_and_keys(
    tmp_path: Path,
    raw: bytes,
) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes(raw)

    with pytest.raises(BoundedCompilerEmissionError):
        emission._load_json(candidate)


def test_compiler_emission_json_enforces_size_and_symlink_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_bytes(b"{" + (b" " * emission.MAX_INPUT_BYTES) + b"}")
    with pytest.raises(BoundedCompilerEmissionError, match="boundary rejected"):
        emission._load_json(candidate)

    candidate.write_text("{}", encoding="utf-8")
    original_is_symlink = Path.is_symlink

    def report_candidate_as_symlink(path: Path) -> bool:
        return path == candidate or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", report_candidate_as_symlink)
    with pytest.raises(BoundedCompilerEmissionError, match="symbolic link"):
        emission._load_json(candidate)


def test_static_gpu_surface_binds_emission_without_harness_kernels() -> None:
    artifacts = validate_compiler_emitted_gpu_sources()
    harness = PROFILE.cuda_source_path.read_text(encoding="utf-8")
    dockerfile = PROFILE.dockerfile_path.read_text(encoding="utf-8")

    assert "__global__" not in harness
    assert artifacts.kernel_header.count("__global__ void") == 2
    assert "--generate-code=arch=compute_86,code=sm_86" in dockerfile
    assert "cuobjdump --list-ptx" in dockerfile
    assert "apt-get" not in dockerfile
    assert "curl " not in dockerfile
    assert "wget " not in dockerfile


def test_compiler_emitted_profile_cannot_enter_legacy_report_path() -> None:
    with pytest.raises(GpuObservationError, match="dedicated compiler-emission"):
        _validate_static_sources(PROFILE)
    with pytest.raises(SystemExit):
        _parse_args(["--preflight", "--profile", PROFILE.profile_id])


def test_compose_and_image_contracts_bind_all_emission_artifacts() -> None:
    compose = proof._synthetic_compose_config(PROFILE)
    image_metadata = _image_metadata()

    assert _validate_compose_config(compose, PROFILE)["build_args"] == (
        _expected_build_args(PROFILE)
    )
    assert _validate_image_metadata(image_metadata, PROFILE) == {
        "container_image_digest": "sha256:" + "3" * 64,
        "image_config_verified": True,
        "image_source_binding_verified": True,
    }
    labels = image_metadata["Config"]["Labels"]  # type: ignore[index]
    labels["io.tuc.gpu-observation.emission-plan-digest"] = "sha256:" + "0" * 64
    with pytest.raises(GpuObservationError, match="provenance labels"):
        _validate_image_metadata(image_metadata, PROFILE)


def test_compiler_emitted_report_is_closed_metadata_only_evidence() -> None:
    report = _build_report()
    rendered = dump_compiler_emitted_gpu_observation_report(report)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert assert_compiler_emitted_gpu_observation_report(report) == report
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"] == {
        "const": proof.COMPILER_EMITTED_GPU_SCHEMA_VERSION
    }
    assert report["emission"]["code_generated"] is True  # type: ignore[index]
    assert report["emission"]["source_text_executed"] is False  # type: ignore[index]
    assert report["execution"]["compiler_emitted_cuda_execution"] is True  # type: ignore[index]
    assert report["execution"]["tuc_native_backend_admitted"] is False  # type: ignore[index]
    assert report["claim_boundary"]["normal_executor_modified"] is False  # type: ignore[index]
    assert '"raw_tensor_values":' not in rendered
    assert "generated_compiler_emitted_sm86_kernels.cuh" not in rendered


def test_compiler_emitted_report_rejects_reinterpreted_claim_with_valid_digest() -> None:
    report = _build_report()
    execution = report["execution"]
    assert isinstance(execution, dict)
    execution["tuc_native_backend_admitted"] = True
    report_without_digest = dict(report)
    report_without_digest.pop("report_digest")
    report["report_digest"] = _digest_payload(report_without_digest)

    with pytest.raises(BoundedCompilerEmittedGpuProofError, match="execution invariant"):
        assert_compiler_emitted_gpu_observation_report(report)


def test_execution_requires_both_explicit_operator_acknowledgements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(proof, "_load_compose_config", pytest.fail)

    with pytest.raises(BoundedCompilerEmittedGpuProofError, match="driver security"):
        proof.run_compiler_emitted_gpu_observation("execute")
    with pytest.raises(BoundedCompilerEmittedGpuProofError, match="display GPU"):
        proof.run_compiler_emitted_gpu_observation(
            "execute", driver_security_reviewed=True
        )


def test_preflight_is_zero_kernel_and_does_not_require_execution_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proof,
        "_load_compose_config",
        lambda profile: proof._synthetic_compose_config(profile),
    )
    monkeypatch.setattr(proof, "_load_image_metadata", lambda profile: _image_metadata())
    monkeypatch.setattr(
        proof,
        "_run_worker",
        lambda mode, image_digest, profile: _expected_worker_response(mode, profile),
    )

    result = proof.run_compiler_emitted_gpu_observation("preflight")

    assert result["proof_status"] == "NOT_EXECUTED"
    assert result["kernel_launch_count"] == 0
    assert result["generated_kernel_count"] == 2
    assert result["source_text_executed"] is False


@pytest.mark.skipif(
    not PHYSICAL_OBSERVATION_PATH.exists(),
    reason="compiler-emitted physical observation awaits explicit opt-in execution",
)
def test_checked_in_physical_observation_is_valid() -> None:
    rendered = PHYSICAL_OBSERVATION_PATH.read_text(encoding="utf-8")
    report = json.loads(rendered)

    assert dump_compiler_emitted_gpu_observation_report(report) == rendered
    assert report["proof"]["status"] == "PASS"
    assert report["execution"]["kernel_launch_count"] == 2
    assert report["claim_boundary"]["external_reproduction"] == "not_yet_supplied"


def test_public_docs_preserve_claim_and_host_privacy() -> None:
    texts = [
        path.read_text(encoding="utf-8")
        for path in (DOC_PATH, THREAT_MODEL_PATH, RFC_PATH)
    ]
    combined = "\n".join(texts)

    assert str(SCHEMA_PATH).replace("\\", "/") in combined
    assert str(PHYSICAL_OBSERVATION_PATH).replace("\\", "/") in combined
    assert "general CUDA backend" in combined
    assert "independent reproduction" in combined
    assert "dev001" not in combined
    assert "dev002" not in combined
    assert "192.168." not in combined
    assert "id_ed25519" not in combined
