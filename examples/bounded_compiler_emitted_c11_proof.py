"""Prove one exact compiler-emitted Source Intent on a non-CUDA AOT target."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import BinaryIO, cast

from examples.bounded_compiler_emission import (
    COMPILER_EMISSION_WORKLOAD_CONTRACT,
    BoundedCompilerEmissionError,
    _digest_payload,
    _object_without_duplicates,
    _reject_non_finite,
)
from examples.bounded_compiler_emitted_c11_emission import (
    C11_CONTEXT_PATH,
    C11_EMISSION_CONTRACT,
    C11_EMISSION_PLAN_PATH,
    C11_GENERATED_HEADER_PATH,
    C11_GENERATED_SOURCE_PATH,
    C11_SOURCE_INTENT_PATH,
    C11_TARGET_PROFILE,
    C11_WORKLOAD_HEADER_PATH,
    C11_WORKLOAD_MANIFEST_PATH,
    C11CompilerEmissionArtifacts,
    validate_checked_in_c11_compiler_emission,
)
from examples.bounded_gpu_observation_proof import _digest_file

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.yml"
C11_DOCKERFILE_PATH = C11_CONTEXT_PATH / "Dockerfile.compiler-emitted-c11"
C11_DOCKERIGNORE_PATH = C11_CONTEXT_PATH / "Dockerfile.compiler-emitted-c11.dockerignore"
C11_HARNESS_PATH = C11_CONTEXT_PATH / "bounded_compiler_emitted_c11_observation.c"
C11_SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "schemas/bounded_compiler_emitted_c11_observation_report.v0.schema.json"
)
C11_GOLDEN_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/proofs/bounded_compiler_emitted_c11_observation_report.json"
)

C11_SCHEMA_VERSION = "tuc.bounded_compiler_emitted_c11_observation_report.v0"
C11_WORKER_PROTOCOL = "tuc.bounded_compiler_emitted_c11_worker.v0"
C11_PROOF_CONTRACT = "bounded_compiler_emitted_c11_observation.controlled_host.v0"
C11_PROOF_CLAIM = (
    "one_admitted_source_intent_lowers_to_reviewed_c11_and_executes_as_static_"
    "x86_64_elf_with_reference_equivalence"
)
C11_BLOCKED_CLAIMS = (
    "arbitrary_source_programs",
    "cross_isa_portability",
    "general_cpu_backend",
    "independent_reproduction",
    "native_performance_parity",
    "production_runtime_admission",
    "universal_hardware_proof",
    "vendor_replacement",
)

C11_BUILDER_IMAGE = (
    "gcc:14.2.0-bookworm@"
    "sha256:82549aa8f90ada3236a8be70c74543132a76662ef33f0c3271ed802b81584a82"
)
C11_RUNTIME_IMAGE = "scratch-static-elf"
C11_IMAGE = "tuc-compiler-emitted-c11:research-v0"
C11_IMAGE_TITLE = "TUC bounded compiler-emitted C11 observation"
C11_IMAGE_VERSION = "research-compiler-emitted-c11-v0"
C11_SERVICE = "compiler-emitted-c11"
C11_COMPOSE_PROFILE = "compiler-emitted-c11"
C11_ENTRYPOINT = "/opt/tuc/bin/tuc-bounded-compiler-emitted-c11-observation"

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MAX_COMPOSE_BYTES = 256 * 1024
_MAX_DIAGNOSTIC_BYTES = 8 * 1024
_MAX_INSPECT_BYTES = 256 * 1024
_MAX_REPORT_BYTES = 64 * 1024
_MAX_WORKER_BYTES = 8 * 1024
_WORKER_TIMEOUT_SECONDS = 20.0
_REPORT_KEYS = frozenset(
    {
        "claim_boundary",
        "emission",
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
_WORKER_KEYS = frozenset(
    {
        "architecture",
        "binary_format",
        "cuda_dependency",
        "device_access",
        "dtype",
        "environment_serialized",
        "generated_function_call_count",
        "generated_function_count",
        "hardware_identifiers_serialized",
        "mode",
        "operation_families",
        "protocol",
        "raw_tensor_values_serialized",
        "raw_timing_samples_serialized",
        "reason_code",
        "reference_check_status",
        "security",
        "source_language",
        "status",
        "tensor_shape",
        "working_set_bytes",
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
_ALLOWED_FAILURE_REASONS = frozenset(
    {
        "invalid_invocation",
        "reference_mismatch",
        "security_boundary_mismatch",
        "workload_reference_mismatch",
    }
)
_DIGEST_BINDINGS = (
    (
        "TUC_C11_EMISSION_PLAN_DIGEST",
        "io.tuc.c11-observation.emission-plan-digest",
        C11_EMISSION_PLAN_PATH,
    ),
    (
        "TUC_C11_GENERATED_HEADER_DIGEST",
        "io.tuc.c11-observation.generated-header-digest",
        C11_GENERATED_HEADER_PATH,
    ),
    (
        "TUC_C11_GENERATED_SOURCE_DIGEST",
        "io.tuc.c11-observation.generated-source-digest",
        C11_GENERATED_SOURCE_PATH,
    ),
    (
        "TUC_C11_HARNESS_DIGEST",
        "io.tuc.c11-observation.harness-digest",
        C11_HARNESS_PATH,
    ),
    (
        "TUC_C11_SOURCE_INTENT_DIGEST",
        "io.tuc.c11-observation.source-intent-digest",
        C11_SOURCE_INTENT_PATH,
    ),
    (
        "TUC_C11_WORKLOAD_HEADER_DIGEST",
        "io.tuc.c11-observation.workload-header-digest",
        C11_WORKLOAD_HEADER_PATH,
    ),
    (
        "TUC_C11_WORKLOAD_MANIFEST_DIGEST",
        "io.tuc.c11-observation.workload-manifest-digest",
        C11_WORKLOAD_MANIFEST_PATH,
    ),
)


class BoundedCompilerEmittedC11ProofError(ValueError):
    """Raised when the bounded non-CUDA proof fails closed."""


def _read_text(path: Path, maximum_bytes: int = 64 * 1024) -> str:
    if path.is_symlink():
        raise BoundedCompilerEmittedC11ProofError("C11 proof symbolic link rejected")
    try:
        before = path.stat()
        if not path.is_file() or not 0 < before.st_size <= maximum_bytes:
            raise BoundedCompilerEmittedC11ProofError("C11 proof file boundary rejected")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise BoundedCompilerEmittedC11ProofError("C11 proof file unavailable") from exc
    if len(raw) != before.st_size or before.st_size != after.st_size:
        raise BoundedCompilerEmittedC11ProofError("C11 proof file changed while reading")
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise BoundedCompilerEmittedC11ProofError("C11 proof encoding rejected") from exc


def _expected_build_args() -> dict[str, str]:
    return {build_arg: _digest_file(path) for build_arg, _label, path in _DIGEST_BINDINGS}


def validate_compiler_emitted_c11_sources() -> C11CompilerEmissionArtifacts:
    """Validate exact emission, the harness, and the immutable build surface."""

    try:
        artifacts = validate_checked_in_c11_compiler_emission()
    except BoundedCompilerEmissionError as exc:
        raise BoundedCompilerEmittedC11ProofError(
            "compiler-emitted C11 static validation rejected"
        ) from exc
    harness = _read_text(C11_HARNESS_PATH)
    dockerfile = _read_text(C11_DOCKERFILE_PATH)
    dockerignore = _read_text(C11_DOCKERIGNORE_PATH)
    required_harness = (
        '#include "generated_compiler_emitted_c11_functions.h"',
        "tuc_projection_matmul_4x8x2_f32(a, b, projection);",
        "tuc_activated_relu_4x2_f32(projection, activated);",
        C11_WORKER_PROTOCOL,
        "TUC_WORKLOAD_BYTES",
        "device_access\\\":false",
    )
    if any(fragment not in harness for fragment in required_harness):
        raise BoundedCompilerEmittedC11ProofError("C11 harness contract drift")
    forbidden_harness = (
        "dlopen(",
        "exec(",
        "fork(",
        "malloc(",
        "popen(",
        "pthread_",
        "system(",
    )
    if any(fragment in harness for fragment in forbidden_harness):
        raise BoundedCompilerEmittedC11ProofError("C11 harness capability rejected")
    if any(line.startswith("void tuc_") for line in harness.splitlines()):
        raise BoundedCompilerEmittedC11ProofError(
            "C11 harness may not define compiler-emitted functions"
        )
    generated = artifacts.generated_source
    if generated.count("void tuc_") != 2:
        raise BoundedCompilerEmittedC11ProofError("C11 generated function surface drift")
    if any(fragment in generated for fragment in ("asm(", "#include <dlfcn.h>", "syscall(")):
        raise BoundedCompilerEmittedC11ProofError("C11 generated capability rejected")
    required_dockerfile = (
        f"FROM --platform=linux/amd64 {C11_BUILDER_IMAGE} AS build",
        "FROM scratch",
        "-std=c11",
        "-static",
        "readelf -d",
        "grep '(NEEDED)'",
        "ENTRYPOINT",
    )
    if any(fragment not in dockerfile for fragment in required_dockerfile):
        raise BoundedCompilerEmittedC11ProofError("C11 Dockerfile contract drift")
    if any(fragment in dockerfile for fragment in ("apt-get", "curl ", "git clone", "wget ")):
        raise BoundedCompilerEmittedC11ProofError("C11 Dockerfile dependency drift")
    expected_allowlist = "\n".join(
        (
            "*",
            f"!{C11_DOCKERFILE_PATH.name}",
            f"!{C11_HARNESS_PATH.name}",
            f"!{C11_GENERATED_HEADER_PATH.name}",
            f"!{C11_GENERATED_SOURCE_PATH.name}",
            f"!{C11_WORKLOAD_HEADER_PATH.name}",
            f"!{C11_WORKLOAD_MANIFEST_PATH.name}",
            f"!{C11_SOURCE_INTENT_PATH.name}",
            f"!{C11_EMISSION_PLAN_PATH.name}",
            "",
        )
    )
    if dockerignore != expected_allowlist:
        raise BoundedCompilerEmittedC11ProofError("C11 build-context allowlist drift")
    return artifacts


def _decode_json(payload: bytes, label: str) -> dict[str, object]:
    try:
        decoded = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_object_without_duplicates,
            parse_constant=_reject_non_finite,
        )
    except (
        BoundedCompilerEmissionError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as exc:
        raise BoundedCompilerEmittedC11ProofError(f"{label} JSON rejected") from exc
    if type(decoded) is not dict:
        raise BoundedCompilerEmittedC11ProofError(f"{label} must be a plain object")
    return cast(dict[str, object], decoded)


def _bounded_subprocess_json(
    command: tuple[str, ...], *, maximum_bytes: int, label: str
) -> dict[str, object]:
    try:
        completed = subprocess.run(  # noqa: S603 - command tuples are fixed below
            command,
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            timeout=15,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BoundedCompilerEmittedC11ProofError(f"{label} failed closed") from exc
    if (
        completed.returncode != 0
        or len(completed.stdout) > maximum_bytes
        or len(completed.stderr) > _MAX_DIAGNOSTIC_BYTES
    ):
        raise BoundedCompilerEmittedC11ProofError(f"{label} failed closed")
    return _decode_json(completed.stdout, label)


def _load_compose_config() -> dict[str, object]:
    return _bounded_subprocess_json(
        (
            "docker",
            "compose",
            "--file",
            str(COMPOSE_PATH),
            "--profile",
            C11_COMPOSE_PROFILE,
            "config",
            "--format",
            "json",
        ),
        maximum_bytes=_MAX_COMPOSE_BYTES,
        label="C11 Compose inspection",
    )


def _as_int(value: object, field: str) -> int:
    if isinstance(value, bool):
        raise BoundedCompilerEmittedC11ProofError(f"C11 Compose {field} rejected")
    try:
        return int(cast(int | str, value))
    except (TypeError, ValueError, OverflowError) as exc:
        raise BoundedCompilerEmittedC11ProofError(
            f"C11 Compose {field} rejected"
        ) from exc


def _expected_compose_contract() -> dict[str, object]:
    return {
        "build_args": _expected_build_args(),
        "build_context": "docker/c11-observation",
        "cap_drop": ["ALL"],
        "command": ["--preflight"],
        "cpus": 1,
        "devices": [],
        "dockerfile": C11_DOCKERFILE_PATH.name,
        "entrypoint": None,
        "environment": {"LANG": "C", "LC_ALL": "C"},
        "gpus": None,
        "image": C11_IMAGE,
        "ipc": "private",
        "mem_limit": 128 * 1024 * 1024,
        "network_mode": "none",
        "pids_limit": 8,
        "platform": "linux/amd64",
        "privileged": False,
        "profiles": [C11_COMPOSE_PROFILE],
        "pull_policy": "never",
        "read_only": True,
        "security_opt": ["no-new-privileges:true"],
        "shm_size": 4 * 1024 * 1024,
        "stdin_open": False,
        "stop_grace_period": "1s",
        "tmpfs": [],
        "tty": False,
        "user": "10001:10001",
        "volumes": [],
        "working_dir": "/run/tuc",
    }


def _synthetic_compose_config() -> dict[str, object]:
    expected = _expected_compose_contract()
    return {
        "services": {
            C11_SERVICE: {
                "build": {
                    "args": expected["build_args"],
                    "context": str(C11_CONTEXT_PATH.resolve()),
                    "dockerfile": expected["dockerfile"],
                },
                "cap_drop": expected["cap_drop"],
                "command": expected["command"],
                "cpus": expected["cpus"],
                "environment": expected["environment"],
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
                "user": expected["user"],
                "working_dir": expected["working_dir"],
            }
        }
    }


def _validate_compose_config(config: object) -> dict[str, object]:
    if type(config) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 Compose config rejected")
    services = cast(dict[str, object], config).get("services")
    if type(services) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 Compose services missing")
    service = cast(dict[str, object], services).get(C11_SERVICE)
    if type(service) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 Compose service missing")
    typed = cast(dict[str, object], service)
    build = typed.get("build")
    if type(build) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 build contract missing")
    build_typed = cast(dict[str, object], build)
    context = build_typed.get("context")
    if not isinstance(context, str) or Path(context).resolve() != C11_CONTEXT_PATH:
        raise BoundedCompilerEmittedC11ProofError("C11 build context drift")
    normalized: dict[str, object] = {
        "build_args": build_typed.get("args"),
        "build_context": "docker/c11-observation",
        "cap_drop": typed.get("cap_drop"),
        "command": typed.get("command"),
        "cpus": typed.get("cpus"),
        "devices": typed.get("devices", []),
        "dockerfile": build_typed.get("dockerfile"),
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
        "tmpfs": typed.get("tmpfs", []),
        "tty": typed.get("tty", False),
        "user": typed.get("user"),
        "volumes": typed.get("volumes", []),
        "working_dir": typed.get("working_dir"),
    }
    if normalized != _expected_compose_contract():
        raise BoundedCompilerEmittedC11ProofError("C11 Compose security contract drift")
    return normalized


def _load_image_metadata() -> dict[str, object]:
    return _bounded_subprocess_json(
        ("docker", "image", "inspect", C11_IMAGE, "--format", "{{json .}}"),
        maximum_bytes=_MAX_INSPECT_BYTES,
        label="C11 image inspection",
    )


def _expected_labels() -> dict[str, str]:
    labels = {
        "io.tuc.c11-observation.contract": C11_PROOF_CONTRACT,
        "org.opencontainers.image.source": "https://github.com/kirchherr/TUC",
        "org.opencontainers.image.title": C11_IMAGE_TITLE,
        "org.opencontainers.image.version": C11_IMAGE_VERSION,
    }
    for _build_arg, label, path in _DIGEST_BINDINGS:
        labels[label] = _digest_file(path)
    return labels


def _validate_image_metadata(metadata: object) -> dict[str, object]:
    if type(metadata) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 image metadata rejected")
    typed = cast(dict[str, object], metadata)
    image_id = typed.get("Id")
    if not isinstance(image_id, str) or _DIGEST_RE.fullmatch(image_id) is None:
        raise BoundedCompilerEmittedC11ProofError("C11 image digest rejected")
    if typed.get("Architecture") != "amd64" or typed.get("Os") != "linux":
        raise BoundedCompilerEmittedC11ProofError("C11 image platform rejected")
    config = typed.get("Config")
    if type(config) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 image config missing")
    config_typed = cast(dict[str, object], config)
    labels = config_typed.get("Labels")
    if type(labels) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 image labels missing")
    label_map = cast(dict[str, object], labels)
    if any(label_map.get(key) != value for key, value in _expected_labels().items()):
        raise BoundedCompilerEmittedC11ProofError("C11 image provenance rejected")
    expected_config = {
        "Cmd": ["--preflight"],
        "Entrypoint": [C11_ENTRYPOINT],
        "User": "10001:10001",
        "WorkingDir": "/run/tuc",
    }
    if any(config_typed.get(key) != value for key, value in expected_config.items()):
        raise BoundedCompilerEmittedC11ProofError("C11 image runtime config rejected")
    image_environment = config_typed.get("Env")
    if image_environment != [
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ]:
        raise BoundedCompilerEmittedC11ProofError("C11 scratch image environment drift")
    return {
        "container_image_digest": image_id,
        "image_config_verified": True,
        "image_source_binding_verified": True,
    }


def _worker_command(mode: str, image_digest: str) -> tuple[str, ...]:
    if mode not in {"execute", "preflight"}:
        raise BoundedCompilerEmittedC11ProofError("C11 worker mode rejected")
    if _DIGEST_RE.fullmatch(image_digest) is None:
        raise BoundedCompilerEmittedC11ProofError("C11 worker image digest rejected")
    return (
        "docker",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--user=10001:10001",
        "--workdir=/run/tuc",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--pids-limit=8",
        "--memory=128m",
        "--memory-swap=128m",
        "--cpus=1",
        "--ipc=private",
        "--shm-size=4m",
        "--ulimit=core=0",
        "--ulimit=nofile=32:32",
        "--log-driver=none",
        "--env=LANG=C",
        "--env=LC_ALL=C",
        image_digest,
        f"--{mode}",
    )


def _read_bounded(handle: BinaryIO, maximum_bytes: int, label: str) -> bytes:
    handle.seek(0)
    payload = handle.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise BoundedCompilerEmittedC11ProofError(f"C11 worker {label} exceeds limit")
    return payload


def _run_worker(mode: str, image_digest: str) -> dict[str, object]:
    command = _worker_command(mode, image_digest)
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            process = subprocess.Popen(  # noqa: S603 - fixed image digest and mode
                command,
                cwd=REPOSITORY_ROOT,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                shell=False,
                close_fds=True,
            )
        except OSError as exc:
            raise BoundedCompilerEmittedC11ProofError("C11 worker failed closed") from exc
        deadline = time.monotonic() + _WORKER_TIMEOUT_SECONDS
        while process.poll() is None:
            if time.monotonic() >= deadline:
                process.kill()
                process.wait()
                raise BoundedCompilerEmittedC11ProofError("C11 worker exceeded deadline")
            if os.fstat(stdout_file.fileno()).st_size > _MAX_WORKER_BYTES or os.fstat(
                stderr_file.fileno()
            ).st_size > _MAX_DIAGNOSTIC_BYTES:
                process.kill()
                process.wait()
                raise BoundedCompilerEmittedC11ProofError("C11 worker output exceeded limit")
            time.sleep(0.01)
        stdout = _read_bounded(stdout_file, _MAX_WORKER_BYTES, "response")
        _read_bounded(stderr_file, _MAX_DIAGNOSTIC_BYTES, "diagnostics")
        response = _decode_json(stdout, "C11 worker response") if stdout else None
        if process.returncode != 0:
            reason = response.get("reason_code") if response is not None else None
            if not isinstance(reason, str) or reason not in _ALLOWED_FAILURE_REASONS:
                reason = "unclassified_failure"
            raise BoundedCompilerEmittedC11ProofError(
                f"C11 worker rejected observation: {reason}"
            )
        if response is None:
            raise BoundedCompilerEmittedC11ProofError("C11 worker response missing")
    return _validate_worker_response(response, mode)


def _expected_worker_response(mode: str) -> dict[str, object]:
    if mode not in {"execute", "preflight"}:
        raise BoundedCompilerEmittedC11ProofError("C11 worker mode rejected")
    execute = mode == "execute"
    return {
        "architecture": "x86_64",
        "binary_format": "elf64",
        "cuda_dependency": False,
        "device_access": False,
        "dtype": "float32",
        "environment_serialized": False,
        "generated_function_call_count": 2 if execute else 0,
        "generated_function_count": 2,
        "hardware_identifiers_serialized": False,
        "mode": mode,
        "operation_families": ["matmul", "elementwise"],
        "protocol": C11_WORKER_PROTOCOL,
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
        "source_language": "c11",
        "status": "PASS",
        "tensor_shape": [4, 2],
        "working_set_bytes": 256 if execute else 0,
        "workload_contract": COMPILER_EMISSION_WORKLOAD_CONTRACT,
        "workload_manifest_digest": _digest_file(C11_WORKLOAD_MANIFEST_PATH),
    }


def _validate_worker_response(response: object, mode: str) -> dict[str, object]:
    if type(response) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 worker response rejected")
    typed = cast(dict[str, object], response)
    security = typed.get("security")
    if frozenset(typed) != _WORKER_KEYS:
        raise BoundedCompilerEmittedC11ProofError("C11 worker response key drift")
    if type(security) is not dict or frozenset(security) != _WORKER_SECURITY_KEYS:
        raise BoundedCompilerEmittedC11ProofError("C11 worker security key drift")
    if typed != _expected_worker_response(mode):
        raise BoundedCompilerEmittedC11ProofError("C11 worker invariant drift")
    return typed


def _static_sections(
    artifacts: C11CompilerEmissionArtifacts,
) -> dict[str, dict[str, object]]:
    plan = artifacts.plan
    return {
        "claim_boundary": {
            "blocked_claims": list(C11_BLOCKED_CLAIMS),
            "device_access_gate_reinterpreted": False,
            "external_reproduction": "not_yet_supplied",
            "native_backend_gate_reinterpreted": False,
            "normal_executor_modified": False,
        },
        "emission": {
            "code_generated": True,
            "code_generation_phase": plan["code_generation_phase"],
            "cuda_dependency": False,
            "emission_contract": C11_EMISSION_CONTRACT,
            "emission_plan_verified": True,
            "generated_function_count": 2,
            "identifier_policy": plan["identifier_policy"],
            "operation_families": ["matmul", "elementwise"],
            "runtime_generated_code": False,
            "source_intent_accepted": True,
            "source_intent_schema_version": "source_intent.v0",
            "source_text_executed": False,
            "target_profile": C11_TARGET_PROFILE,
        },
        "execution": {
            "aot_binary_execution": True,
            "architecture": "x86_64",
            "binary_format": "elf64",
            "compiler_emitted_c11_execution": True,
            "controlled_host_execution": True,
            "device_access": False,
            "dynamic_linking": False,
            "generated_function_call_count": 2,
            "jit_execution": False,
            "performance_measurement_collected": False,
            "runtime_generated_code": False,
            "tuc_native_backend_admitted": False,
            "workload_working_set_bytes": 256,
        },
        "isolation": {
            "capabilities_dropped": True,
            "cpu_limit": 1,
            "effective_capabilities_zero": True,
            "memory_limit_bytes": 128 * 1024 * 1024,
            "network_access": False,
            "no_new_privileges": True,
            "non_root_gid": 10001,
            "non_root_uid": 10001,
            "pids_limit": 8,
            "repository_mount": False,
            "root_filesystem_read_only": True,
            "runtime_boundary": "docker_static_scratch_image",
            "seccomp_mode": 2,
        },
        "privacy": {
            "environment_serialized": False,
            "generated_source_serialized": False,
            "hardware_identifiers_serialized": False,
            "host_paths_serialized": False,
            "raw_tensor_values_serialized": False,
            "raw_timing_samples_serialized": False,
            "source_text_serialized": False,
        },
        "proof": {
            "claim": C11_PROOF_CLAIM,
            "contract": C11_PROOF_CONTRACT,
            "scope": "one_same_maintainer_fixed_non_cuda_aot_observation",
            "status": "PASS",
        },
        "workload": {
            "dtype": "float32",
            "elementwise_semantics": "relu",
            "input_policy": "fixed_public_non_sensitive_test_vector",
            "input_shapes": [[4, 8], [8, 2]],
            "operation_families": ["matmul", "elementwise"],
            "output_shape": [4, 2],
            "reference_correctness_passed": True,
            "semantic_origin": "accepted_triton_research_source_intent",
            "workload_contract": COMPILER_EMISSION_WORKLOAD_CONTRACT,
        },
    }


def _static_provenance(
    artifacts: C11CompilerEmissionArtifacts,
) -> dict[str, object]:
    plan = artifacts.plan
    return {
        "builder_image": C11_BUILDER_IMAGE,
        "dockerfile_digest": _digest_file(C11_DOCKERFILE_PATH),
        "emission_plan_file_digest": _digest_file(C11_EMISSION_PLAN_PATH),
        "emission_plan_payload_digest": plan["plan_digest"],
        "generated_header_digest": plan["generated_header_digest"],
        "generated_source_digest": plan["generated_source_digest"],
        "harness_digest": _digest_file(C11_HARNESS_PATH),
        "runtime_image": C11_RUNTIME_IMAGE,
        "source_intent_file_digest": _digest_file(C11_SOURCE_INTENT_PATH),
        "source_intent_payload_digest": plan["source_intent_digest"],
        "static_linkage_verified": True,
        "target_architecture": "x86_64",
        "workload_header_digest": plan["workload_header_digest"],
        "workload_manifest_file_digest": _digest_file(C11_WORKLOAD_MANIFEST_PATH),
        "workload_payload_digest": plan["workload_digest"],
    }


def build_compiler_emitted_c11_observation_report(
    response: object,
    compose_contract: object,
    image_metadata: object,
) -> dict[str, object]:
    """Bind deterministic C11 emission and one controlled host run."""

    artifacts = validate_compiler_emitted_c11_sources()
    worker = _validate_worker_response(response, "execute")
    compose = _validate_compose_config(compose_contract)
    image = _validate_image_metadata(image_metadata)
    sections = _static_sections(artifacts)
    provenance = _static_provenance(artifacts)
    provenance.update(
        {
            "compose_contract_digest": _digest_payload(compose),
            "container_image_digest": image["container_image_digest"],
            "image_config_verified": image["image_config_verified"],
            "image_source_binding_verified": image["image_source_binding_verified"],
            "worker_observation_digest": _digest_payload(worker),
        }
    )
    report: dict[str, object] = {
        **sections,
        "provenance": provenance,
        "schema_version": C11_SCHEMA_VERSION,
    }
    report["report_digest"] = _digest_payload(report)
    return assert_compiler_emitted_c11_observation_report(report)


def assert_compiler_emitted_c11_observation_report(
    report: object,
) -> dict[str, object]:
    """Fail closed unless evidence proves only the admitted C11 claim."""

    if type(report) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 report must be a plain object")
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise BoundedCompilerEmittedC11ProofError("C11 report key drift")
    digest_source = dict(typed)
    digest = digest_source.pop("report_digest", None)
    if digest != _digest_payload(digest_source):
        raise BoundedCompilerEmittedC11ProofError("C11 report digest mismatch")
    if typed.get("schema_version") != C11_SCHEMA_VERSION:
        raise BoundedCompilerEmittedC11ProofError("C11 report schema drift")
    artifacts = validate_compiler_emitted_c11_sources()
    for name, expected in _static_sections(artifacts).items():
        if typed.get(name) != expected:
            raise BoundedCompilerEmittedC11ProofError(f"C11 {name} invariant drift")
    provenance = typed.get("provenance")
    if type(provenance) is not dict:
        raise BoundedCompilerEmittedC11ProofError("C11 provenance missing")
    provenance_typed = cast(dict[str, object], provenance)
    expected_static = _static_provenance(artifacts)
    expected_keys = frozenset(
        {
            *expected_static,
            "compose_contract_digest",
            "container_image_digest",
            "image_config_verified",
            "image_source_binding_verified",
            "worker_observation_digest",
        }
    )
    if frozenset(provenance_typed) != expected_keys:
        raise BoundedCompilerEmittedC11ProofError("C11 provenance key drift")
    if any(provenance_typed.get(key) != value for key, value in expected_static.items()):
        raise BoundedCompilerEmittedC11ProofError("C11 provenance binding drift")
    expected_compose_digest = _digest_payload(
        _validate_compose_config(_synthetic_compose_config())
    )
    if provenance_typed.get("compose_contract_digest") != expected_compose_digest:
        raise BoundedCompilerEmittedC11ProofError("C11 Compose digest drift")
    if provenance_typed.get("worker_observation_digest") != _digest_payload(
        _expected_worker_response("execute")
    ):
        raise BoundedCompilerEmittedC11ProofError("C11 worker digest drift")
    if provenance_typed.get("image_config_verified") is not True or (
        provenance_typed.get("image_source_binding_verified") is not True
    ):
        raise BoundedCompilerEmittedC11ProofError("C11 image verification drift")
    image_digest = provenance_typed.get("container_image_digest")
    if not isinstance(image_digest, str) or _DIGEST_RE.fullmatch(image_digest) is None:
        raise BoundedCompilerEmittedC11ProofError("C11 image digest rejected")
    return typed


def dump_compiler_emitted_c11_observation_report(report: object) -> str:
    """Render deterministic metadata-only C11 observation evidence."""

    typed = assert_compiler_emitted_c11_observation_report(report)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise BoundedCompilerEmittedC11ProofError("C11 report exceeds limit")
    forbidden = (
        '"command"',
        '"cpu_model"',
        '"generated_source"',
        '"host_path"',
        '"raw_tensor_values"',
        '"source_text"',
        "C:\\Users\\",
        "/home/",
    )
    if any(fragment in rendered for fragment in forbidden):
        raise BoundedCompilerEmittedC11ProofError("C11 report leaks forbidden data")
    return rendered


def run_compiler_emitted_c11_observation(mode: str) -> dict[str, object]:
    """Run zero-call preflight or the exact non-CUDA AOT observation."""

    if mode not in {"execute", "preflight"}:
        raise BoundedCompilerEmittedC11ProofError("C11 mode rejected")
    artifacts = validate_compiler_emitted_c11_sources()
    compose_raw = _load_compose_config()
    _validate_compose_config(compose_raw)
    image_metadata = _load_image_metadata()
    image = _validate_image_metadata(image_metadata)
    response = _run_worker(mode, cast(str, image["container_image_digest"]))
    if mode == "preflight":
        return {
            "architecture": "x86_64",
            "compiler_emission_plan_digest": artifacts.plan["plan_digest"],
            "container_image_digest": image["container_image_digest"],
            "cuda_dependency": False,
            "device_access": False,
            "generated_function_call_count": 0,
            "generated_function_count": 2,
            "mode": "preflight",
            "proof_status": "NOT_EXECUTED",
            "sanitized": True,
            "schema_version": "tuc.bounded_compiler_emitted_c11_preflight.v0",
            "security_boundary_passed": True,
            "source_text_executed": False,
            "workload_manifest_digest": response["workload_manifest_digest"],
        }
    return build_compiler_emitted_c11_observation_report(
        response,
        compose_raw,
        image_metadata,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mode = "execute" if args.execute else "preflight"
    try:
        report = run_compiler_emitted_c11_observation(mode)
        if mode == "execute":
            sys.stdout.write(dump_compiler_emitted_c11_observation_report(report))
        else:
            sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except BoundedCompilerEmittedC11ProofError as exc:
        print(f"bounded compiler-emitted C11 proof rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
