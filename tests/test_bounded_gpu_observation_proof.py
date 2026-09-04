from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest

import examples.bounded_gpu_observation_proof as proof
from examples.bounded_gpu_observation_proof import (
    GPU_OBSERVATION_PROOF_CONTRACT,
    GPU_OBSERVATION_SCHEMA_VERSION,
    GpuObservationError,
    _digest_file,
    _digest_payload,
    _expected_compose_contract,
    _expected_worker_response,
    _validate_compose_config,
    _validate_image_metadata,
    _validate_static_sources,
    _validate_worker_response,
    _worker_command,
    assert_bounded_gpu_observation_report,
    build_bounded_gpu_observation_report,
    dump_bounded_gpu_observation_report,
    render_workload_header,
    run_gpu_observation,
)

SCHEMA_PATH = Path("schemas/bounded_gpu_observation_report.v0.schema.json")
DOC_PATH = Path("docs/BOUNDED_GPU_OBSERVATION_PROOF.md")
THREAT_MODEL_PATH = Path("docs/BOUNDED_GPU_OBSERVATION_THREAT_MODEL.md")
RFC_PATH = Path("rfcs/0300-bounded-gpu-observation-proof.md")


def _rendered_compose_config() -> dict[str, object]:
    expected = _expected_compose_contract()
    return {
        "services": {
            proof.GPU_OBSERVATION_SERVICE: {
                "build": {
                    "args": expected["build_args"],
                    "context": str(proof.GPU_CONTEXT_PATH.resolve()),
                    "dockerfile": "Dockerfile",
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
    build_args = proof._expected_build_args()
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
                "io.tuc.gpu-observation.contract": GPU_OBSERVATION_PROOF_CONTRACT,
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
                "org.opencontainers.image.title": "TUC bounded GPU observation",
                "org.opencontainers.image.version": "research-v0",
            },
            "User": "10001:10001",
            "WorkingDir": "/run/tuc",
        },
        "Id": "sha256:" + "1" * 64,
        "Os": "linux",
    }


def _build_report() -> dict[str, object]:
    return build_bounded_gpu_observation_report(
        _expected_worker_response("execute"),
        _rendered_compose_config(),
        _image_metadata(),
        driver_security_reviewed=True,
        shared_display_risk_acknowledged=True,
    )


def test_public_workload_matches_objective_delta_and_generated_header() -> None:
    workload = json.loads(proof.WORKLOAD_MANIFEST_PATH.read_text(encoding="utf-8"))

    assert _validate_static_sources() == workload
    assert render_workload_header(workload) == proof.WORKLOAD_HEADER_PATH.read_text(
        encoding="utf-8"
    )
    conformance = json.loads(
        proof.OBJECTIVE_DELTA_CONFORMANCE_VECTOR_PATH.read_text(encoding="utf-8")
    )
    assert workload["inputs"] == conformance["inputs"]
    assert workload["expected_output"] == conformance["expected_public_outputs"][
        "api_activated"
    ]


def test_cuda_probe_has_fixed_native_surface() -> None:
    source = proof.CUDA_SOURCE_PATH.read_text(encoding="utf-8")
    dockerfile = proof.GPU_DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert source.count("<<<1, kThreadsPerBlock>>>") == 2
    assert source.count("cudaMalloc(") == 4
    assert "std::getenv" not in source
    assert "std::system" not in source
    assert "popen(" not in source
    assert "fork(" not in source
    assert "dlopen(" not in source
    assert "--generate-code=arch=compute_70,code=sm_70" in dockerfile
    assert "CUDA_DISABLE_PTX_JIT=1" in dockerfile
    assert "apt-get" not in dockerfile
    assert "curl " not in dockerfile
    assert "wget " not in dockerfile


def test_compose_contract_is_single_device_and_fail_closed() -> None:
    config = _rendered_compose_config()

    assert _validate_compose_config(config) == _expected_compose_contract()
    service = config["services"][proof.GPU_OBSERVATION_SERVICE]
    service["network_mode"] = "bridge"
    service["volumes"] = [".:/workspace"]
    with pytest.raises(GpuObservationError, match="security contract drift"):
        _validate_compose_config(config)


def test_legacy_broad_gpu_service_is_rejected() -> None:
    config = _rendered_compose_config()
    config["services"]["gpu"] = {"gpus": "all"}

    with pytest.raises(GpuObservationError, match="legacy broad GPU"):
        _validate_compose_config(config)


def test_worker_response_is_exact_and_metadata_only() -> None:
    response = _expected_worker_response("execute")

    assert _validate_worker_response(response, mode="execute") == response
    assert response["kernel_launch_count"] == 2
    assert response["workload_allocation_bytes"] == 128
    assert response["raw_tensor_values_serialized"] is False
    assert response["raw_timing_samples_serialized"] is False

    tampered = dict(response)
    tampered["device_uuid"] = "forbidden"
    with pytest.raises(GpuObservationError, match="key drift"):
        _validate_worker_response(tampered, mode="execute")


def test_preflight_worker_contract_cannot_claim_execution() -> None:
    response = _expected_worker_response("preflight")

    assert _validate_worker_response(response, mode="preflight") == response
    assert response["kernel_launch_count"] == 0
    assert response["workload_allocation_bytes"] == 0
    assert response["reference_check_status"] == "not_executed"


def test_image_metadata_binds_reviewed_sources_and_fixed_entrypoint() -> None:
    metadata = _image_metadata()

    assert _validate_image_metadata(metadata) == {
        "container_image_digest": "sha256:" + "1" * 64,
        "image_config_verified": True,
        "image_source_binding_verified": True,
    }
    labels = metadata["Config"]["Labels"]
    labels["io.tuc.gpu-observation.source-digest"] = "sha256:" + "0" * 64
    with pytest.raises(GpuObservationError, match="provenance labels"):
        _validate_image_metadata(metadata)


def test_execution_requires_both_operator_acknowledgements_before_docker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker_called = False

    def unexpected_docker_call() -> dict[str, object]:
        nonlocal docker_called
        docker_called = True
        raise AssertionError("Docker must not run before operator acknowledgement")

    monkeypatch.setattr(proof, "_load_compose_config", unexpected_docker_call)
    with pytest.raises(GpuObservationError, match="driver security update"):
        run_gpu_observation("execute")
    with pytest.raises(GpuObservationError, match="shared display GPU risk"):
        run_gpu_observation("execute", driver_security_reviewed=True)
    assert docker_called is False


def test_worker_command_has_no_shell_or_unbounded_user_input() -> None:
    image_digest = "sha256:" + "1" * 64
    assert _worker_command("preflight", image_digest) == (
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--read-only",
        "--user=10001:10001",
        "--workdir=/run/tuc",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=16",
        "--memory=1g",
        "--memory-swap=1g",
        "--cpus=1",
        "--ipc=private",
        "--shm-size=16m",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1700,uid=10001,gid=10001",
        "--ulimit=core=0",
        "--ulimit=nofile=64:64",
        "--log-driver=none",
        "--gpus=device=0",
        "--env=CUDA_CACHE_DISABLE=1",
        "--env=CUDA_DISABLE_PTX_JIT=1",
        "--env=CUDA_VISIBLE_DEVICES=0",
        "--env=LANG=C.UTF-8",
        "--env=LC_ALL=C.UTF-8",
        "--env=NVIDIA_DRIVER_CAPABILITIES=compute",
        "--env=NVIDIA_VISIBLE_DEVICES=0",
        image_digest,
        "--preflight",
    )
    with pytest.raises(GpuObservationError, match="mode rejected"):
        _worker_command("--privileged", image_digest)
    with pytest.raises(GpuObservationError, match="image digest rejected"):
        _worker_command("preflight", "tuc-gpu-observation:latest")


def test_report_binds_physical_execution_without_broadening_claims() -> None:
    report = _build_report()
    rendered = dump_bounded_gpu_observation_report(report)

    assert assert_bounded_gpu_observation_report(report) == report
    assert report["schema_version"] == GPU_OBSERVATION_SCHEMA_VERSION
    assert report["proof"]["status"] == "PASS"
    assert report["execution"]["physical_device_execution"] is True
    assert report["execution"]["tuc_native_backend_admitted"] is False
    assert report["execution"]["performance_measurement_collected"] is False
    assert report["claim_boundary"]["normal_executor_modified"] is False
    assert "device_uuid" not in rendered
    assert "pci_bus_id" not in rendered
    assert "raw_tensor_values\"" not in rendered
    assert "C:\\Users\\" not in rendered


def test_report_digest_and_semantic_fields_fail_closed() -> None:
    report = _build_report()
    tampered = deepcopy(report)
    tampered["execution"]["kernel_launch_count"] = 1
    digest_source = dict(tampered)
    del digest_source["report_digest"]
    tampered["report_digest"] = _digest_payload(digest_source)

    with pytest.raises(GpuObservationError, match="execution drift"):
        assert_bounded_gpu_observation_report(tampered)


def test_schema_and_documentation_preserve_closed_boundaries() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert schema["properties"]["execution"]["additionalProperties"] is False
    assert schema["properties"]["privacy"]["additionalProperties"] is False
    assert schema["properties"]["execution"]["properties"][
        "performance_measurement_collected"
    ] == {"const": False}
    for path in (DOC_PATH, THREAT_MODEL_PATH, RFC_PATH, Path("docs/ROADMAP_STATUS.md")):
        text = path.read_text(encoding="utf-8")
        assert str(SCHEMA_PATH).replace("\\", "/") in text or path.name == (
            "BOUNDED_GPU_OBSERVATION_THREAT_MODEL.md"
        )


def test_compose_build_args_match_current_files() -> None:
    args = proof._expected_build_args()

    assert args == {
        "TUC_GPU_OBSERVATION_HEADER_DIGEST": _digest_file(proof.WORKLOAD_HEADER_PATH),
        "TUC_GPU_OBSERVATION_SOURCE_DIGEST": _digest_file(proof.CUDA_SOURCE_PATH),
        "TUC_GPU_OBSERVATION_WORKLOAD_DIGEST": _digest_file(
            proof.WORKLOAD_MANIFEST_PATH
        ),
    }


@pytest.mark.skipif(
    os.environ.get("TUC_RUN_GPU_OBSERVATION_TEST") != "1",
    reason="physical GPU observation is explicit opt-in only",
)
def test_live_gpu_preflight_is_explicit_opt_in() -> None:
    report = run_gpu_observation("preflight")

    assert report["proof_status"] == "NOT_EXECUTED"
    assert report["kernel_launch_count"] == 0
    assert report["security_boundary_passed"] is True
