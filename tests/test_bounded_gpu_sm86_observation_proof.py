from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import examples.bounded_gpu_observation_proof as proof
from examples.bounded_gpu_observation_proof import (
    GPU_SM86_PROFILE,
    GpuObservationError,
    _digest_file,
    _expected_build_args,
    _expected_compose_contract,
    _expected_worker_response,
    _validate_compose_config,
    _validate_image_metadata,
    _validate_static_sources,
    assert_bounded_gpu_observation_report,
    build_bounded_gpu_observation_report,
    dump_bounded_gpu_observation_report,
    resolve_gpu_observation_profile,
)

PROFILE = GPU_SM86_PROFILE
SCHEMA_PATH = Path("schemas/bounded_gpu_sm86_observation_report.v0.schema.json")
PHYSICAL_OBSERVATION_PATH = Path(
    "tests/golden/proofs/bounded_gpu_sm86_observation_report.json"
)


def _rendered_compose_config() -> dict[str, object]:
    expected = _expected_compose_contract(PROFILE)
    return {
        "services": {
            PROFILE.service: {
                "build": {
                    "args": expected["build_args"],
                    "context": str(proof.GPU_CONTEXT_PATH.resolve()),
                    "dockerfile": PROFILE.dockerfile_path.name,
                },
                "cap_drop": expected["cap_drop"],
                "command": expected["command"],
                "cpus": expected["cpus"],
                "environment": expected["environment"],
                "gpus": expected["gpus"],
                "image": expected["image"],
                "ipc": expected["ipc"],
                "mem_limit": str(expected["mem_limit"]),
                "network_mode": expected["network_mode"],
                "pids_limit": expected["pids_limit"],
                "platform": expected["platform"],
                "profiles": expected["profiles"],
                "pull_policy": expected["pull_policy"],
                "read_only": expected["read_only"],
                "security_opt": expected["security_opt"],
                "shm_size": str(expected["shm_size"]),
                "stop_grace_period": expected["stop_grace_period"],
                "tmpfs": expected["tmpfs"],
                "user": expected["user"],
                "working_dir": expected["working_dir"],
            }
        }
    }


def _image_metadata() -> dict[str, object]:
    build_args = _expected_build_args(PROFILE)
    return {
        "Architecture": "amd64",
        "Config": {
            "Cmd": ["--preflight"],
            "Entrypoint": ["/opt/tuc/bin/tuc-bounded-gpu-observation"],
            "Env": [
                "CUDA_CACHE_DISABLE=1",
                "CUDA_DISABLE_PTX_JIT=1",
                "CUDA_VISIBLE_DEVICES=0",
                "NVIDIA_DRIVER_CAPABILITIES=compute",
                "NVIDIA_VISIBLE_DEVICES=0",
            ],
            "Labels": {
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
            },
            "User": "10001:10001",
            "WorkingDir": "/run/tuc",
        },
        "Id": "sha256:" + "2" * 64,
        "Os": "linux",
    }


def _build_report() -> dict[str, object]:
    return build_bounded_gpu_observation_report(
        _expected_worker_response("execute", PROFILE),
        _rendered_compose_config(),
        _image_metadata(),
        driver_security_reviewed=True,
        shared_display_risk_acknowledged=True,
        profile=PROFILE,
    )


def test_sm86_profile_is_static_and_free_form_targets_are_rejected() -> None:
    assert resolve_gpu_observation_profile("nvidia-sm86") is PROFILE

    with pytest.raises(GpuObservationError, match="profile rejected"):
        resolve_gpu_observation_profile("sm_90; execute arbitrary target")
    with pytest.raises(GpuObservationError, match="profile rejected"):
        _expected_build_args(replace(PROFILE, sass_target="sm_90"))


def test_sm86_worker_diff_is_restricted_to_reviewed_target_identity() -> None:
    sm70 = proof.CUDA_SOURCE_PATH.read_text(encoding="utf-8")
    sm86 = PROFILE.cuda_source_path.read_text(encoding="utf-8")
    normalized = (
        sm86.replace("kExpectedComputeMajor = 8", "kExpectedComputeMajor = 7")
        .replace("kExpectedComputeMinor = 6", "kExpectedComputeMinor = 0")
        .replace(
            "tuc.bounded_gpu_sm86_observation_worker.v0",
            proof.GPU_OBSERVATION_WORKER_PROTOCOL,
        )
        .replace("nvidia_cuda_sm86", "nvidia_cuda_sm70")
    )

    assert normalized == sm70


def test_sm86_static_sources_bind_sass_only_build() -> None:
    workload = _validate_static_sources(PROFILE)
    dockerfile = PROFILE.dockerfile_path.read_text(encoding="utf-8")
    dockerignore = PROFILE.dockerfile_path.with_name(
        f"{PROFILE.dockerfile_path.name}.dockerignore"
    ).read_text(encoding="utf-8")

    assert workload["workload_contract"] == proof.GPU_OBSERVATION_WORKLOAD_CONTRACT
    assert "--generate-code=arch=compute_86,code=sm_86" in dockerfile
    assert "grep 'sm_86'" in dockerfile
    assert "cuobjdump --list-ptx" in dockerfile
    assert "apt-get" not in dockerfile
    assert "curl " not in dockerfile
    assert "wget " not in dockerfile
    assert dockerignore.splitlines() == [
        "*",
        "!Dockerfile.sm86",
        "!bounded_gpu_observation_sm86.cu",
        "!objective_delta_workload.hpp",
        "!objective_delta_workload.v0.json",
    ]


def test_sm86_compose_contract_is_closed_and_single_device() -> None:
    config = _rendered_compose_config()

    assert _validate_compose_config(config, PROFILE) == _expected_compose_contract(
        PROFILE
    )
    service = config["services"][PROFILE.service]
    service["gpus"] = [{"driver": "nvidia", "device_ids": ["0", "1"]}]
    with pytest.raises(GpuObservationError, match="security contract drift"):
        _validate_compose_config(config, PROFILE)


def test_sm86_image_metadata_is_profile_and_source_bound() -> None:
    metadata = _image_metadata()

    assert _validate_image_metadata(metadata, PROFILE) == {
        "container_image_digest": "sha256:" + "2" * 64,
        "image_config_verified": True,
        "image_source_binding_verified": True,
    }
    labels = metadata["Config"]["Labels"]
    labels["io.tuc.gpu-observation.contract"] = proof.GPU_OBSERVATION_PROOF_CONTRACT
    with pytest.raises(GpuObservationError, match="provenance labels"):
        _validate_image_metadata(metadata, PROFILE)


def test_sm86_report_preserves_narrow_claim_and_validates_schema() -> None:
    report = _build_report()
    rendered = dump_bounded_gpu_observation_report(report, profile=PROFILE)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert assert_bounded_gpu_observation_report(report, profile=PROFILE) == report
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"] == {
        "const": PROFILE.schema_version
    }
    assert report["execution"]["accelerator_class"] == "nvidia_cuda_sm86"
    assert report["provenance"]["sass_target"] == "sm_86"
    assert report["proof"]["scope"] == "single_fixed_remote_hardware_observation"
    assert report["execution"]["tuc_native_backend_admitted"] is False
    assert report["execution"]["performance_measurement_collected"] is False
    assert "device_uuid" not in rendered
    assert "driver_version" not in rendered or (
        '"driver_version_serialized": false' in rendered
    )


@pytest.mark.skipif(
    not PHYSICAL_OBSERVATION_PATH.exists(),
    reason="sm86 physical observation awaits explicit opt-in execution",
)
def test_checked_in_sm86_physical_observation_is_valid() -> None:
    rendered = PHYSICAL_OBSERVATION_PATH.read_text(encoding="utf-8")
    report = json.loads(rendered)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert dump_bounded_gpu_observation_report(report, profile=PROFILE) == rendered
    assert schema["properties"]["execution"]["properties"][
        "accelerator_class"
    ] == {"const": PROFILE.accelerator_class}
    assert report["proof"]["status"] == "PASS"
    assert report["execution"]["kernel_launch_count"] == 2
    assert report["execution"]["accelerator_class"] == "nvidia_cuda_sm86"
    assert report["claim_boundary"]["external_reproduction"] == "not_yet_supplied"


def test_sm86_compose_build_args_match_reviewed_files() -> None:
    assert _expected_build_args(PROFILE) == {
        "TUC_GPU_OBSERVATION_HEADER_DIGEST": _digest_file(
            proof.WORKLOAD_HEADER_PATH
        ),
        "TUC_GPU_OBSERVATION_SOURCE_DIGEST": _digest_file(
            PROFILE.cuda_source_path
        ),
        "TUC_GPU_OBSERVATION_WORKLOAD_DIGEST": _digest_file(
            proof.WORKLOAD_MANIFEST_PATH
        ),
    }
