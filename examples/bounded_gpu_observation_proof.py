"""Run the opt-in bounded physical GPU observation proof."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from hashlib import sha256
from pathlib import Path
from typing import BinaryIO, cast

GPU_OBSERVATION_SCHEMA_VERSION = "tuc.bounded_gpu_observation_report.v0"
GPU_OBSERVATION_PROOF_CONTRACT = "bounded_gpu_observation.physical_device.v0"
GPU_OBSERVATION_PROOF_CLAIM = (
    "fixed_neutral_workload_executes_on_one_physical_gpu_and_matches_cpu_reference"
)
GPU_OBSERVATION_WORKER_PROTOCOL = "tuc.bounded_gpu_observation_worker.v0"
GPU_OBSERVATION_WORKLOAD_CONTRACT = (
    "objective_delta_matmul_elementwise_2x2_f64.v0"
)
GPU_OBSERVATION_SERVICE = "gpu-observation"
GPU_OBSERVATION_IMAGE = "tuc-gpu-observation:research-v0"
GPU_OBSERVATION_DEVEL_IMAGE = (
    "nvidia/cuda:12.8.1-devel-ubuntu24.04@"
    "sha256:4b9ed5fa8361736996499f64ecebf25d4ec37ff56e4d11323ccde10aa36e0c43"
)
GPU_OBSERVATION_RUNTIME_IMAGE = (
    "nvidia/cuda:12.8.1-runtime-ubuntu24.04@"
    "sha256:828c4d878adcaa4265d80c95d8ec877149b49bb2419a4cf3bb6aa889bbb7ca2e"
)
GPU_OBSERVATION_BLOCKED_CLAIMS = (
    "arbitrary_cuda_execution",
    "compiler_emitted_cuda",
    "general_native_backend",
    "native_performance_parity",
    "portable_hardware_execution",
    "production_device_admission",
    "vendor_replacement",
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.yml"
GPU_CONTEXT_PATH = REPOSITORY_ROOT / "docker/gpu-observation"
CUDA_SOURCE_PATH = GPU_CONTEXT_PATH / "bounded_gpu_observation.cu"
WORKLOAD_HEADER_PATH = GPU_CONTEXT_PATH / "objective_delta_workload.hpp"
WORKLOAD_MANIFEST_PATH = GPU_CONTEXT_PATH / "objective_delta_workload.v0.json"
GPU_DOCKERFILE_PATH = GPU_CONTEXT_PATH / "Dockerfile"
OBJECTIVE_DELTA_SOURCE_INTENT_PATH = (
    REPOSITORY_ROOT / "integration/objective_delta/source_intent.v0.json"
)
OBJECTIVE_DELTA_REPORT_PATH = (
    REPOSITORY_ROOT / "integration/objective_delta/expected_report.json"
)
OBJECTIVE_DELTA_CONFORMANCE_VECTOR_PATH = (
    REPOSITORY_ROOT
    / "integration/objective_delta_audit/conformance_vector.v0.json"
)

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_COMPOSE_BYTES = 256 * 1024
_MAX_INSPECT_BYTES = 256 * 1024
_MAX_WORKER_BYTES = 8 * 1024
_MAX_DIAGNOSTIC_BYTES = 8 * 1024
_MAX_REPORT_BYTES = 64 * 1024
_WORKER_TIMEOUT_SECONDS = 30.0
_ALLOWED_FAILURE_REASONS = frozenset(
    {
        "accelerator_class_mismatch",
        "bounded_allocation_failed",
        "device_properties_failed",
        "device_query_failed",
        "device_selection_failed",
        "device_cleanup_failed",
        "device_visibility_mismatch",
        "input_transfer_failed",
        "invalid_invocation",
        "kernel_completion_failed",
        "matmul_launch_failed",
        "output_transfer_failed",
        "reference_mismatch",
        "security_boundary_mismatch",
        "workload_reference_mismatch",
    }
)
_EXPECTED_WORKLOAD: dict[str, object] = {
    "dtype": "float64",
    "dynamic_input": False,
    "expected_output": [[4.0, 0.5], [-2.0, 1.25]],
    "input_policy": "fixed_public_non_sensitive_test_vector",
    "inputs": {
        "lhs": [[1.0, -2.0], [0.5, 3.0]],
        "rhs": [[2.0, 1.0], [-1.0, 0.25]],
    },
    "operations": [
        {
            "family": "matmul",
            "inputs": ["lhs", "rhs"],
            "name": "projection",
            "output": "projection",
        },
        {
            "family": "elementwise",
            "inputs": ["projection"],
            "kind": "identity",
            "name": "activation",
            "output": "activated",
        },
    ],
    "schema_version": "tuc.bounded_gpu_observation_workload.v0",
    "semantic_origin": "objective_delta_portable_compute_v0",
    "shape": [2, 2],
    "workload_contract": GPU_OBSERVATION_WORKLOAD_CONTRACT,
}
_WORKER_KEYS = frozenset(
    {
        "accelerator_class",
        "device_name_serialized",
        "driver_version_serialized",
        "dtype",
        "environment_serialized",
        "hardware_identifiers_serialized",
        "kernel_launch_count",
        "mode",
        "operation_families",
        "protocol",
        "raw_tensor_values_serialized",
        "raw_timing_samples_serialized",
        "reason_code",
        "reference_check_status",
        "security",
        "status",
        "tensor_shape",
        "visible_device_count",
        "workload_allocation_bytes",
        "workload_contract",
        "workload_manifest_digest",
    }
)
_WORKER_SECURITY_KEYS = frozenset(
    {
        "effective_capabilities_zero",
        "gid",
        "no_new_privileges",
        "seccomp_mode",
        "status_read",
        "uid",
    }
)
_REPORT_KEYS = frozenset(
    {
        "claim_boundary",
        "execution",
        "isolation",
        "privacy",
        "proof",
        "provenance",
        "report_digest",
        "schema_version",
        "workload",
    }
)


class GpuObservationError(ValueError):
    """Raised when the bounded hardware observation fails closed."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _digest_payload(value: object) -> str:
    return f"sha256:{sha256(_canonical_json(value).encode('utf-8')).hexdigest()}"


def _digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _load_json(path: Path, *, max_bytes: int = 64 * 1024) -> dict[str, object]:
    if path.stat().st_size > max_bytes:
        raise GpuObservationError("bounded GPU observation JSON exceeds limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GpuObservationError("bounded GPU observation JSON rejected") from exc
    if type(payload) is not dict:
        raise GpuObservationError("bounded GPU observation JSON must be a plain object")
    return cast(dict[str, object], payload)


def _read_text_bounded(path: Path, *, max_bytes: int = 64 * 1024) -> str:
    if path.stat().st_size > max_bytes:
        raise GpuObservationError("bounded GPU observation text exceeds limit")
    try:
        return path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise GpuObservationError("bounded GPU observation text rejected") from exc


def _validate_workload_manifest(payload: object) -> dict[str, object]:
    if payload != _EXPECTED_WORKLOAD:
        raise GpuObservationError("bounded GPU workload manifest drift")
    return cast(dict[str, object], payload)


def _flatten_matrix(value: object) -> list[float]:
    if type(value) is not list or len(value) != 2:
        raise GpuObservationError("bounded GPU workload matrix shape drift")
    flattened: list[float] = []
    for row in value:
        if type(row) is not list or len(row) != 2:
            raise GpuObservationError("bounded GPU workload matrix shape drift")
        for item in row:
            if type(item) not in (int, float):
                raise GpuObservationError("bounded GPU workload matrix dtype drift")
            flattened.append(float(item))
    return flattened


def render_workload_header(workload: object) -> str:
    """Render the only C++ header accepted for the fixed public workload."""

    typed = _validate_workload_manifest(workload)
    inputs = cast(dict[str, object], typed["inputs"])
    arrays = (
        ("kLhs", _flatten_matrix(inputs["lhs"])),
        ("kRhs", _flatten_matrix(inputs["rhs"])),
        ("kExpectedOutput", _flatten_matrix(typed["expected_output"])),
    )
    lines = [
        "#pragma once",
        "",
        "#include <array>",
        "#include <cstddef>",
        "",
        "namespace tuc::gpu_observation {",
        "",
        "inline constexpr char kWorkloadContract[] =",
        f'    "{GPU_OBSERVATION_WORKLOAD_CONTRACT}";',
        "inline constexpr std::size_t kDimension = 2;",
        "inline constexpr std::size_t kElementCount = 4;",
    ]
    for name, values in arrays:
        lines.append(f"inline constexpr std::array<double, kElementCount> {name} = {{")
        lines.extend(f"    {value!r}," for value in values)
        lines.append("};")
    lines.extend(("", "}  // namespace tuc::gpu_observation", ""))
    return "\n".join(lines)


def _validate_objective_delta_link(workload: dict[str, object]) -> None:
    inputs = cast(dict[str, object], workload["inputs"])
    conformance = _load_json(OBJECTIVE_DELTA_CONFORMANCE_VECTOR_PATH)
    if conformance.get("contract") != "objective_delta.fixed_semantics.v0":
        raise GpuObservationError("Objective Delta conformance contract drift")
    delta_inputs = conformance.get("inputs")
    if type(delta_inputs) is not dict:
        raise GpuObservationError("Objective Delta conformance inputs drift")
    delta_input_map = cast(dict[str, object], delta_inputs)
    if delta_input_map.get("lhs") != inputs["lhs"]:
        raise GpuObservationError("Objective Delta lhs binding drift")
    if delta_input_map.get("rhs") != inputs["rhs"]:
        raise GpuObservationError("Objective Delta rhs binding drift")
    public_outputs = conformance.get("expected_public_outputs")
    if type(public_outputs) is not dict or cast(dict[str, object], public_outputs).get(
        "api_activated"
    ) != workload["expected_output"]:
        raise GpuObservationError("Objective Delta result binding drift")

    source_intent = _load_json(OBJECTIVE_DELTA_SOURCE_INTENT_PATH)
    if source_intent.get("name") != "source_intent_backend_package_portfolio":
        raise GpuObservationError("Objective Delta Source Intent binding drift")
    operation_families = [
        item.get("family")
        for item in cast(list[dict[str, object]], source_intent["operations"])
    ]
    if operation_families != ["matmul", "elementwise"]:
        raise GpuObservationError("Objective Delta operation binding drift")

    report = _load_json(OBJECTIVE_DELTA_REPORT_PATH)
    expected_report_facts = {
        "backend_equivalence_passed": True,
        "operation_families": ["matmul", "elementwise"],
        "physical_device_execution": False,
        "proof_status": "PASS",
        "reference_correctness_passed": True,
        "source_text_executed": False,
    }
    for key, expected_value in expected_report_facts.items():
        if report.get(key) != expected_value:
            raise GpuObservationError(f"Objective Delta {key} binding drift")


def _expected_build_args() -> dict[str, str]:
    return {
        "TUC_GPU_OBSERVATION_HEADER_DIGEST": _digest_file(WORKLOAD_HEADER_PATH),
        "TUC_GPU_OBSERVATION_SOURCE_DIGEST": _digest_file(CUDA_SOURCE_PATH),
        "TUC_GPU_OBSERVATION_WORKLOAD_DIGEST": _digest_file(WORKLOAD_MANIFEST_PATH),
    }


def _expected_compose_contract() -> dict[str, object]:
    return {
        "build_args": _expected_build_args(),
        "build_context": "docker/gpu-observation",
        "dockerfile": "Dockerfile",
        "cap_drop": ["ALL"],
        "command": ["--preflight"],
        "cpus": 1,
        "devices": [],
        "entrypoint": None,
        "environment": {
            "CUDA_CACHE_DISABLE": "1",
            "CUDA_DISABLE_PTX_JIT": "1",
            "CUDA_VISIBLE_DEVICES": "0",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NVIDIA_DRIVER_CAPABILITIES": "compute",
            "NVIDIA_VISIBLE_DEVICES": "0",
        },
        "gpus": [{"device_ids": ["0"], "driver": "nvidia"}],
        "image": GPU_OBSERVATION_IMAGE,
        "ipc": "private",
        "mem_limit": 1024 * 1024 * 1024,
        "network_mode": "none",
        "pids_limit": 16,
        "platform": "linux/amd64",
        "privileged": False,
        "profiles": ["gpu-observation"],
        "pull_policy": "never",
        "read_only": True,
        "security_opt": ["no-new-privileges:true"],
        "shm_size": 16 * 1024 * 1024,
        "stdin_open": False,
        "stop_grace_period": "1s",
        "tmpfs": [
            "/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1700,uid=10001,gid=10001"
        ],
        "user": "10001:10001",
        "volumes": [],
        "working_dir": "/run/tuc",
        "tty": False,
    }


def _bounded_subprocess_json(command: tuple[str, ...], *, max_bytes: int) -> dict[str, object]:
    try:
        completed = subprocess.run(  # noqa: S603 - fixed Docker inspection command
            command,
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            timeout=15,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GpuObservationError("bounded Docker inspection failed closed") from exc
    if (
        completed.returncode != 0
        or len(completed.stdout) > max_bytes
        or len(completed.stderr) > _MAX_DIAGNOSTIC_BYTES
    ):
        raise GpuObservationError("bounded Docker inspection failed closed")
    try:
        payload = json.loads(completed.stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GpuObservationError("bounded Docker inspection JSON rejected") from exc
    if type(payload) is not dict:
        raise GpuObservationError("bounded Docker inspection must be a plain object")
    return cast(dict[str, object], payload)


def _load_compose_config() -> dict[str, object]:
    return _bounded_subprocess_json(
        (
            "docker",
            "compose",
            "--file",
            str(COMPOSE_PATH),
            "--profile",
            "gpu-observation",
            "config",
            "--format",
            "json",
        ),
        max_bytes=_MAX_COMPOSE_BYTES,
    )


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise GpuObservationError(f"GPU Compose {field} rejected")
    try:
        result = int(cast(int | str, value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise GpuObservationError(f"GPU Compose {field} rejected") from exc
    return result


def _validate_compose_config(config: object) -> dict[str, object]:
    if type(config) is not dict:
        raise GpuObservationError("GPU Compose config must be a plain object")
    services = cast(dict[str, object], config).get("services")
    if type(services) is not dict:
        raise GpuObservationError("GPU Compose services missing")
    service_map = cast(dict[str, object], services)
    if "gpu" in service_map:
        raise GpuObservationError("legacy broad GPU development service is forbidden")
    service = service_map.get(GPU_OBSERVATION_SERVICE)
    if type(service) is not dict:
        raise GpuObservationError("bounded GPU Compose service missing")
    typed = cast(dict[str, object], service)
    build = typed.get("build")
    if type(build) is not dict:
        raise GpuObservationError("bounded GPU build contract missing")
    build_typed = cast(dict[str, object], build)
    context = build_typed.get("context")
    if not isinstance(context, str) or Path(context).resolve() != GPU_CONTEXT_PATH:
        raise GpuObservationError("bounded GPU build context drift")

    normalized: dict[str, object] = {
        "build_args": build_typed.get("args"),
        "build_context": "docker/gpu-observation",
        "dockerfile": build_typed.get("dockerfile"),
        "cap_drop": typed.get("cap_drop"),
        "command": typed.get("command"),
        "cpus": typed.get("cpus"),
        "devices": typed.get("devices", []),
        "entrypoint": typed.get("entrypoint"),
        "environment": typed.get("environment"),
        "gpus": typed.get("gpus"),
        "image": typed.get("image"),
        "ipc": typed.get("ipc"),
        "mem_limit": _as_int(typed.get("mem_limit"), "mem_limit"),
        "network_mode": typed.get("network_mode"),
        "pids_limit": typed.get("pids_limit"),
        "platform": typed.get("platform"),
        "privileged": typed.get("privileged", False),
        "profiles": typed.get("profiles"),
        "pull_policy": typed.get("pull_policy"),
        "read_only": typed.get("read_only"),
        "security_opt": typed.get("security_opt"),
        "shm_size": _as_int(typed.get("shm_size"), "shm_size"),
        "stdin_open": typed.get("stdin_open", False),
        "stop_grace_period": typed.get("stop_grace_period"),
        "tmpfs": typed.get("tmpfs"),
        "user": typed.get("user"),
        "volumes": typed.get("volumes", []),
        "working_dir": typed.get("working_dir"),
        "tty": typed.get("tty", False),
    }
    if normalized != _expected_compose_contract():
        raise GpuObservationError("bounded GPU Compose security contract drift")
    return normalized


def _load_image_metadata() -> dict[str, object]:
    return _bounded_subprocess_json(
        ("docker", "image", "inspect", GPU_OBSERVATION_IMAGE, "--format", "{{json .}}"),
        max_bytes=_MAX_INSPECT_BYTES,
    )


def _validate_image_metadata(metadata: object) -> dict[str, object]:
    if type(metadata) is not dict:
        raise GpuObservationError("bounded GPU image metadata must be a plain object")
    typed = cast(dict[str, object], metadata)
    image_id = typed.get("Id")
    if not isinstance(image_id, str) or _DIGEST_RE.fullmatch(image_id) is None:
        raise GpuObservationError("bounded GPU image digest rejected")
    if typed.get("Architecture") != "amd64" or typed.get("Os") != "linux":
        raise GpuObservationError("bounded GPU image platform rejected")
    config = typed.get("Config")
    if type(config) is not dict:
        raise GpuObservationError("bounded GPU image config missing")
    config_typed = cast(dict[str, object], config)
    labels = config_typed.get("Labels")
    if type(labels) is not dict:
        raise GpuObservationError("bounded GPU image labels missing")
    expected_labels = {
        "io.tuc.gpu-observation.contract": GPU_OBSERVATION_PROOF_CONTRACT,
        "io.tuc.gpu-observation.header-digest": _digest_file(WORKLOAD_HEADER_PATH),
        "io.tuc.gpu-observation.source-digest": _digest_file(CUDA_SOURCE_PATH),
        "io.tuc.gpu-observation.workload-digest": _digest_file(WORKLOAD_MANIFEST_PATH),
        "org.opencontainers.image.source": "https://github.com/kirchherr/TUC",
        "org.opencontainers.image.title": "TUC bounded GPU observation",
        "org.opencontainers.image.version": "research-v0",
    }
    label_map = cast(dict[str, object], labels)
    if any(label_map.get(key) != value for key, value in expected_labels.items()):
        raise GpuObservationError("bounded GPU image provenance labels rejected")
    expected_config = {
        "Cmd": ["--preflight"],
        "Entrypoint": ["/opt/tuc/bin/tuc-bounded-gpu-observation"],
        "User": "10001:10001",
        "WorkingDir": "/run/tuc",
    }
    if any(config_typed.get(key) != value for key, value in expected_config.items()):
        raise GpuObservationError("bounded GPU image runtime config rejected")
    image_environment = config_typed.get("Env")
    required_environment = {
        "CUDA_CACHE_DISABLE=1",
        "CUDA_DISABLE_PTX_JIT=1",
        "CUDA_VISIBLE_DEVICES=0",
        "NVIDIA_DRIVER_CAPABILITIES=compute",
        "NVIDIA_VISIBLE_DEVICES=0",
    }
    if type(image_environment) is not list or not required_environment.issubset(
        set(cast(list[str], image_environment))
    ):
        raise GpuObservationError("bounded GPU image environment rejected")
    return {
        "container_image_digest": image_id,
        "image_config_verified": True,
        "image_source_binding_verified": True,
    }


def _worker_command(mode: str, image_digest: str) -> tuple[str, ...]:
    if mode not in {"execute", "preflight"}:
        raise GpuObservationError("bounded GPU worker mode rejected")
    if _DIGEST_RE.fullmatch(image_digest) is None:
        raise GpuObservationError("bounded GPU worker image digest rejected")
    return (
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
        f"--{mode}",
    )


def _read_bounded_file(handle: BinaryIO, limit: int, label: str) -> bytes:
    handle.seek(0)
    data = handle.read(limit + 1)
    if len(data) > limit:
        raise GpuObservationError(f"bounded GPU worker {label} exceeds limit")
    return data


def _decode_worker_json(payload: bytes) -> dict[str, object]:
    try:
        decoded = json.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GpuObservationError("bounded GPU worker returned invalid JSON") from exc
    if type(decoded) is not dict:
        raise GpuObservationError("bounded GPU worker response must be a plain object")
    return cast(dict[str, object], decoded)


def _run_worker(mode: str, image_digest: str) -> dict[str, object]:
    command = _worker_command(mode, image_digest)
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            process = subprocess.Popen(  # noqa: S603 - fixed Compose service and mode only
                command,
                cwd=REPOSITORY_ROOT,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                shell=False,
                close_fds=True,
            )
        except OSError as exc:
            raise GpuObservationError("bounded GPU worker failed closed") from exc
        deadline = time.monotonic() + _WORKER_TIMEOUT_SECONDS
        while process.poll() is None:
            if time.monotonic() >= deadline:
                process.kill()
                process.wait()
                raise GpuObservationError("bounded GPU worker exceeded wall-clock limit")
            if os.fstat(stdout_file.fileno()).st_size > _MAX_WORKER_BYTES:
                process.kill()
                process.wait()
                raise GpuObservationError("bounded GPU worker response exceeds limit")
            if os.fstat(stderr_file.fileno()).st_size > _MAX_DIAGNOSTIC_BYTES:
                process.kill()
                process.wait()
                raise GpuObservationError("bounded GPU worker diagnostics exceed limit")
            time.sleep(0.01)
        response_bytes = _read_bounded_file(stdout_file, _MAX_WORKER_BYTES, "response")
        _read_bounded_file(stderr_file, _MAX_DIAGNOSTIC_BYTES, "diagnostics")
        if process.returncode != 0:
            if not response_bytes:
                raise GpuObservationError(
                    "bounded GPU worker failed before protocol response"
                )
            response = _decode_worker_json(response_bytes)
            reason = response.get("reason_code")
            if not isinstance(reason, str) or reason not in _ALLOWED_FAILURE_REASONS:
                reason = "unclassified_failure"
            raise GpuObservationError(f"bounded GPU worker rejected observation: {reason}")
        response = _decode_worker_json(response_bytes)
    return _validate_worker_response(response, mode=mode)


def _expected_worker_response(mode: str) -> dict[str, object]:
    execute = mode == "execute"
    return {
        "accelerator_class": "nvidia_cuda_sm70",
        "device_name_serialized": False,
        "driver_version_serialized": False,
        "dtype": "float64",
        "environment_serialized": False,
        "hardware_identifiers_serialized": False,
        "kernel_launch_count": 2 if execute else 0,
        "mode": mode,
        "operation_families": ["matmul", "elementwise"],
        "protocol": GPU_OBSERVATION_WORKER_PROTOCOL,
        "raw_tensor_values_serialized": False,
        "raw_timing_samples_serialized": False,
        "reason_code": "none",
        "reference_check_status": "passed" if execute else "not_executed",
        "security": {
            "effective_capabilities_zero": True,
            "gid": 10001,
            "no_new_privileges": 1,
            "seccomp_mode": 2,
            "status_read": True,
            "uid": 10001,
        },
        "status": "PASS",
        "tensor_shape": [2, 2],
        "visible_device_count": 1,
        "workload_allocation_bytes": 128 if execute else 0,
        "workload_contract": GPU_OBSERVATION_WORKLOAD_CONTRACT,
        "workload_manifest_digest": _digest_file(WORKLOAD_MANIFEST_PATH),
    }


def _validate_worker_response(response: object, *, mode: str) -> dict[str, object]:
    if type(response) is not dict:
        raise GpuObservationError("bounded GPU worker response must be a plain object")
    typed = cast(dict[str, object], response)
    security = typed.get("security")
    if frozenset(typed) != _WORKER_KEYS:
        raise GpuObservationError("bounded GPU worker response key drift")
    if type(security) is not dict or frozenset(security) != _WORKER_SECURITY_KEYS:
        raise GpuObservationError("bounded GPU worker security key drift")
    if typed != _expected_worker_response(mode):
        raise GpuObservationError("bounded GPU worker invariant drift")
    if len(_canonical_json(typed).encode("utf-8")) > _MAX_WORKER_BYTES:
        raise GpuObservationError("bounded GPU worker response exceeds limit")
    return typed


def _validate_static_sources() -> dict[str, object]:
    workload = _validate_workload_manifest(_load_json(WORKLOAD_MANIFEST_PATH))
    if _read_text_bounded(WORKLOAD_HEADER_PATH) != (
        render_workload_header(workload)
    ):
        raise GpuObservationError("generated GPU workload header drift")
    _validate_objective_delta_link(workload)

    dockerfile = _read_text_bounded(GPU_DOCKERFILE_PATH)
    required_fragments = (
        f"FROM {GPU_OBSERVATION_DEVEL_IMAGE} AS build",
        f"FROM {GPU_OBSERVATION_RUNTIME_IMAGE}",
        "--generate-code=arch=compute_70,code=sm_70",
        "CUDA_DISABLE_PTX_JIT=1",
        'ENTRYPOINT ["/opt/tuc/bin/tuc-bounded-gpu-observation"]',
    )
    if any(fragment not in dockerfile for fragment in required_fragments):
        raise GpuObservationError("bounded GPU Dockerfile contract drift")
    forbidden_fragments = ("apt-get", "curl ", "wget ", "ADD http", "git clone")
    if any(fragment in dockerfile for fragment in forbidden_fragments):
        raise GpuObservationError("bounded GPU Dockerfile dependency surface rejected")
    return workload


def build_bounded_gpu_observation_report(
    response: object,
    compose_contract: object,
    image_metadata: object,
    *,
    driver_security_reviewed: bool,
    shared_display_risk_acknowledged: bool,
) -> dict[str, object]:
    """Bind one successful fixed-kernel run into sanitized public evidence."""

    if not driver_security_reviewed:
        raise GpuObservationError("current vendor driver security update not attested")
    if not shared_display_risk_acknowledged:
        raise GpuObservationError("shared display GPU risk not acknowledged")
    workload = _validate_static_sources()
    worker = _validate_worker_response(response, mode="execute")
    compose = _validate_compose_config(compose_contract)
    image = _validate_image_metadata(image_metadata)
    report: dict[str, object] = {
        "claim_boundary": {
            "blocked_claims": list(GPU_OBSERVATION_BLOCKED_CLAIMS),
            "device_access_gate_reinterpreted": False,
            "driver_security_review": "operator_attested_current_vendor_update",
            "external_reproduction": "not_yet_supplied",
            "native_backend_gate_reinterpreted": False,
            "normal_executor_modified": False,
            "shared_display_risk_acknowledged": True,
        },
        "execution": {
            "accelerator_class": worker["accelerator_class"],
            "device_access": True,
            "driver_api_called": True,
            "fixed_native_probe_execution": True,
            "jit_execution": False,
            "kernel_launch_count": worker["kernel_launch_count"],
            "performance_measurement_collected": False,
            "physical_device_execution": True,
            "runtime_generated_code": False,
            "tuc_native_backend_admitted": False,
            "visible_device_count": worker["visible_device_count"],
            "workload_device_allocation_bytes": worker["workload_allocation_bytes"],
        },
        "isolation": {
            "capabilities_dropped": True,
            "cpu_limit": compose["cpus"],
            "driver_capabilities": ["compute"],
            "effective_capabilities_zero": True,
            "gpu_selection": "single_logical_device_zero",
            "memory_limit_bytes": compose["mem_limit"],
            "network_access": False,
            "no_new_privileges": True,
            "non_root_gid": 10001,
            "non_root_uid": 10001,
            "pids_limit": compose["pids_limit"],
            "repository_mount": False,
            "root_filesystem_read_only": True,
            "runtime_boundary": "docker_compose_nvidia_device_request",
            "seccomp_mode": 2,
        },
        "privacy": {
            "device_name_serialized": False,
            "driver_version_serialized": False,
            "environment_serialized": False,
            "hardware_identifiers_serialized": False,
            "host_paths_serialized": False,
            "raw_tensor_values_serialized": False,
            "raw_timing_samples_serialized": False,
        },
        "proof": {
            "claim": GPU_OBSERVATION_PROOF_CLAIM,
            "contract": GPU_OBSERVATION_PROOF_CONTRACT,
            "scope": "single_fixed_local_hardware_observation",
            "status": "PASS",
        },
        "provenance": {
            "builder_image": GPU_OBSERVATION_DEVEL_IMAGE,
            "compose_contract_digest": _digest_payload(compose),
            "container_image_digest": image["container_image_digest"],
            "cuda_source_digest": _digest_file(CUDA_SOURCE_PATH),
            "dockerfile_digest": _digest_file(GPU_DOCKERFILE_PATH),
            "image_config_verified": image["image_config_verified"],
            "image_source_binding_verified": image["image_source_binding_verified"],
            "objective_delta_report_file_digest": _digest_file(OBJECTIVE_DELTA_REPORT_PATH),
            "objective_delta_source_intent_file_digest": _digest_file(
                OBJECTIVE_DELTA_SOURCE_INTENT_PATH
            ),
            "objective_delta_vector_file_digest": _digest_file(
                OBJECTIVE_DELTA_CONFORMANCE_VECTOR_PATH
            ),
            "ptx_jit_disabled": True,
            "runtime_image": GPU_OBSERVATION_RUNTIME_IMAGE,
            "sass_target": "sm_70",
            "worker_observation_digest": _digest_payload(worker),
            "workload_header_digest": _digest_file(WORKLOAD_HEADER_PATH),
            "workload_manifest_digest": _digest_file(WORKLOAD_MANIFEST_PATH),
        },
        "schema_version": GPU_OBSERVATION_SCHEMA_VERSION,
        "workload": {
            "dtype": workload["dtype"],
            "input_policy": workload["input_policy"],
            "operation_families": ["matmul", "elementwise"],
            "reference_correctness_passed": True,
            "semantic_origin": workload["semantic_origin"],
            "shape": workload["shape"],
            "workload_contract": workload["workload_contract"],
        },
    }
    report["report_digest"] = _digest_payload(report)
    return assert_bounded_gpu_observation_report(report)


def assert_bounded_gpu_observation_report(report: object) -> dict[str, object]:
    """Fail closed unless a report preserves the narrow physical claim."""

    if type(report) is not dict:
        raise GpuObservationError("bounded GPU observation report must be a plain object")
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise GpuObservationError("bounded GPU observation report key drift")
    if typed.get("schema_version") != GPU_OBSERVATION_SCHEMA_VERSION:
        raise GpuObservationError("bounded GPU observation schema drift")

    proof = typed.get("proof")
    execution = typed.get("execution")
    isolation = typed.get("isolation")
    privacy = typed.get("privacy")
    provenance = typed.get("provenance")
    workload = typed.get("workload")
    if not all(
        type(item) is dict
        for item in (proof, execution, isolation, privacy, provenance, workload)
    ):
        raise GpuObservationError("bounded GPU observation section shape drift")

    expected_sections = {
        "claim_boundary": {
            "blocked_claims": list(GPU_OBSERVATION_BLOCKED_CLAIMS),
            "device_access_gate_reinterpreted": False,
            "driver_security_review": "operator_attested_current_vendor_update",
            "external_reproduction": "not_yet_supplied",
            "native_backend_gate_reinterpreted": False,
            "normal_executor_modified": False,
            "shared_display_risk_acknowledged": True,
        },
        "execution": {
            "accelerator_class": "nvidia_cuda_sm70",
            "device_access": True,
            "driver_api_called": True,
            "fixed_native_probe_execution": True,
            "jit_execution": False,
            "kernel_launch_count": 2,
            "performance_measurement_collected": False,
            "physical_device_execution": True,
            "runtime_generated_code": False,
            "tuc_native_backend_admitted": False,
            "visible_device_count": 1,
            "workload_device_allocation_bytes": 128,
        },
        "isolation": {
            "capabilities_dropped": True,
            "cpu_limit": 1,
            "driver_capabilities": ["compute"],
            "effective_capabilities_zero": True,
            "gpu_selection": "single_logical_device_zero",
            "memory_limit_bytes": 1024 * 1024 * 1024,
            "network_access": False,
            "no_new_privileges": True,
            "non_root_gid": 10001,
            "non_root_uid": 10001,
            "pids_limit": 16,
            "repository_mount": False,
            "root_filesystem_read_only": True,
            "runtime_boundary": "docker_compose_nvidia_device_request",
            "seccomp_mode": 2,
        },
        "privacy": {
            "device_name_serialized": False,
            "driver_version_serialized": False,
            "environment_serialized": False,
            "hardware_identifiers_serialized": False,
            "host_paths_serialized": False,
            "raw_tensor_values_serialized": False,
            "raw_timing_samples_serialized": False,
        },
        "proof": {
            "claim": GPU_OBSERVATION_PROOF_CLAIM,
            "contract": GPU_OBSERVATION_PROOF_CONTRACT,
            "scope": "single_fixed_local_hardware_observation",
            "status": "PASS",
        },
        "workload": {
            "dtype": "float64",
            "input_policy": "fixed_public_non_sensitive_test_vector",
            "operation_families": ["matmul", "elementwise"],
            "reference_correctness_passed": True,
            "semantic_origin": "objective_delta_portable_compute_v0",
            "shape": [2, 2],
            "workload_contract": GPU_OBSERVATION_WORKLOAD_CONTRACT,
        },
    }
    for section_name, expected in expected_sections.items():
        if typed.get(section_name) != expected:
            raise GpuObservationError(f"bounded GPU observation {section_name} drift")

    provenance_typed = cast(dict[str, object], provenance)
    expected_provenance_keys = frozenset(
        {
            "builder_image",
            "compose_contract_digest",
            "container_image_digest",
            "cuda_source_digest",
            "dockerfile_digest",
            "image_config_verified",
            "image_source_binding_verified",
            "objective_delta_report_file_digest",
            "objective_delta_source_intent_file_digest",
            "objective_delta_vector_file_digest",
            "ptx_jit_disabled",
            "runtime_image",
            "sass_target",
            "worker_observation_digest",
            "workload_header_digest",
            "workload_manifest_digest",
        }
    )
    if frozenset(provenance_typed) != expected_provenance_keys:
        raise GpuObservationError("bounded GPU observation provenance key drift")
    digest_fields = (
        "compose_contract_digest",
        "container_image_digest",
        "cuda_source_digest",
        "dockerfile_digest",
        "objective_delta_report_file_digest",
        "objective_delta_source_intent_file_digest",
        "objective_delta_vector_file_digest",
        "worker_observation_digest",
        "workload_header_digest",
        "workload_manifest_digest",
    )
    if any(
        not isinstance(provenance_typed.get(field), str)
        or _DIGEST_RE.fullmatch(cast(str, provenance_typed[field])) is None
        for field in digest_fields
    ):
        raise GpuObservationError("bounded GPU observation provenance digest rejected")
    fixed_provenance = {
        "builder_image": GPU_OBSERVATION_DEVEL_IMAGE,
        "compose_contract_digest": _digest_payload(_expected_compose_contract()),
        "cuda_source_digest": _digest_file(CUDA_SOURCE_PATH),
        "dockerfile_digest": _digest_file(GPU_DOCKERFILE_PATH),
        "image_config_verified": True,
        "image_source_binding_verified": True,
        "objective_delta_report_file_digest": _digest_file(OBJECTIVE_DELTA_REPORT_PATH),
        "objective_delta_source_intent_file_digest": _digest_file(
            OBJECTIVE_DELTA_SOURCE_INTENT_PATH
        ),
        "objective_delta_vector_file_digest": _digest_file(
            OBJECTIVE_DELTA_CONFORMANCE_VECTOR_PATH
        ),
        "ptx_jit_disabled": True,
        "runtime_image": GPU_OBSERVATION_RUNTIME_IMAGE,
        "sass_target": "sm_70",
        "worker_observation_digest": _digest_payload(_expected_worker_response("execute")),
        "workload_header_digest": _digest_file(WORKLOAD_HEADER_PATH),
        "workload_manifest_digest": _digest_file(WORKLOAD_MANIFEST_PATH),
    }
    for key, value in fixed_provenance.items():
        if provenance_typed.get(key) != value:
            raise GpuObservationError(f"bounded GPU observation provenance {key} drift")

    report_digest = typed.get("report_digest")
    if not isinstance(report_digest, str) or _DIGEST_RE.fullmatch(report_digest) is None:
        raise GpuObservationError("bounded GPU observation report digest rejected")
    digest_source = dict(typed)
    del digest_source["report_digest"]
    if report_digest != _digest_payload(digest_source):
        raise GpuObservationError("bounded GPU observation report digest mismatch")
    return typed


def dump_bounded_gpu_observation_report(report: object) -> str:
    """Return bounded, deterministic, metadata-only public evidence."""

    typed = assert_bounded_gpu_observation_report(report)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise GpuObservationError("bounded GPU observation report exceeds limit")
    forbidden_fragments = (
        '"command"',
        '"device_uuid"',
        '"host_path"',
        '"pci_bus_id"',
        '"raw_tensor_values"',
        '"serial_number"',
        "C:\\\\Users\\\\",
        "/home/",
    )
    if any(fragment in rendered for fragment in forbidden_fragments):
        raise GpuObservationError("bounded GPU observation report leaks forbidden data")
    return rendered


def run_gpu_observation(
    mode: str,
    *,
    driver_security_reviewed: bool = False,
    shared_display_risk_acknowledged: bool = False,
) -> dict[str, object]:
    """Run a preflight or the explicit fixed-kernel observation."""

    if mode == "execute" and not driver_security_reviewed:
        raise GpuObservationError("current vendor driver security update not attested")
    if mode == "execute" and not shared_display_risk_acknowledged:
        raise GpuObservationError("shared display GPU risk not acknowledged")
    _validate_static_sources()
    compose = _load_compose_config()
    _validate_compose_config(compose)
    image_metadata = _load_image_metadata()
    image = _validate_image_metadata(image_metadata)
    response = _run_worker(mode, cast(str, image["container_image_digest"]))
    if mode == "preflight":
        return {
            "accelerator_class": response["accelerator_class"],
            "container_image_digest": image["container_image_digest"],
            "device_access": True,
            "kernel_launch_count": 0,
            "mode": "preflight",
            "proof_status": "NOT_EXECUTED",
            "sanitized": True,
            "schema_version": "tuc.bounded_gpu_observation_preflight.v0",
            "security_boundary_passed": True,
            "visible_device_count": 1,
            "workload_manifest_digest": response["workload_manifest_digest"],
        }
    return build_bounded_gpu_observation_report(
        response,
        compose,
        image_metadata,
        driver_security_reviewed=driver_security_reviewed,
        shared_display_risk_acknowledged=shared_display_risk_acknowledged,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--attest-current-driver-security-update", action="store_true")
    parser.add_argument("--acknowledge-shared-display-risk", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mode = "execute" if args.execute else "preflight"
    try:
        report = run_gpu_observation(
            mode,
            driver_security_reviewed=args.attest_current_driver_security_update,
            shared_display_risk_acknowledged=args.acknowledge_shared_display_risk,
        )
        if mode == "execute":
            sys.stdout.write(dump_bounded_gpu_observation_report(report))
        else:
            sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except GpuObservationError as exc:
        print(f"bounded GPU observation rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
