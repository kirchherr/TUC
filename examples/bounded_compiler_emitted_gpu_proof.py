"""Prove one exact compiler-emitted Source Intent slice on one physical GPU."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import cast

from examples.bounded_compiler_emission import (
    COMPILER_EMISSION_CONTRACT,
    COMPILER_EMISSION_WORKLOAD_CONTRACT,
    BoundedCompilerEmissionError,
    CompilerEmissionArtifacts,
    validate_checked_in_compiler_emission,
)
from examples.bounded_gpu_observation_proof import (
    GPU_COMPILER_EMITTED_SM86_PROFILE,
    GPU_OBSERVATION_DEVEL_IMAGE,
    GPU_OBSERVATION_RUNTIME_IMAGE,
    GpuObservationError,
    GpuObservationProfile,
    _digest_file,
    _digest_payload,
    _load_compose_config,
    _load_image_metadata,
    _read_text_bounded,
    _run_worker,
    _validate_compose_config,
    _validate_image_metadata,
    _validate_profile_build_surface,
    _validate_worker_response,
)

COMPILER_EMITTED_GPU_SCHEMA_VERSION = (
    "tuc.bounded_compiler_emitted_gpu_observation_report.v0"
)
COMPILER_EMITTED_GPU_PROOF_CLAIM = (
    "one_admitted_source_intent_lowers_to_reviewed_cuda_and_executes_on_one_"
    "physical_gpu_with_cpu_reference_equivalence"
)
COMPILER_EMITTED_GPU_BLOCKED_CLAIMS = (
    "arbitrary_source_programs",
    "cross_vendor_execution",
    "dynamic_shapes_or_inputs",
    "general_cuda_backend",
    "independent_reproduction",
    "native_performance_parity",
    "production_device_admission",
)

PROFILE = GPU_COMPILER_EMITTED_SM86_PROFILE
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "schemas/bounded_compiler_emitted_gpu_observation_report.v0.schema.json"
)

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
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
_MAX_REPORT_BYTES = 64 * 1024


class BoundedCompilerEmittedGpuProofError(ValueError):
    """Raised when the bounded compiler-emitted GPU claim fails closed."""


def _require_profile(profile: GpuObservationProfile) -> GpuObservationProfile:
    if profile is not PROFILE:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU profile rejected"
        )
    return profile


def _validate_emitted_cuda_surface(artifacts: CompilerEmissionArtifacts) -> None:
    surface_paths = (
        PROFILE.cuda_source_path,
        PROFILE.dockerfile_path,
        PROFILE.workload_header_path,
        PROFILE.workload_manifest_path,
        *(path for _build_arg, _label, path in PROFILE.extra_digest_bindings),
    )
    if any(path.is_symlink() for path in surface_paths):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU symbolic link rejected"
        )
    harness = _read_text_bounded(PROFILE.cuda_source_path, max_bytes=64 * 1024)
    kernel_header = artifacts.kernel_header
    dockerfile = _read_text_bounded(PROFILE.dockerfile_path, max_bytes=64 * 1024)

    required_harness_fragments = (
        '#include "compiler_emitted_workload.hpp"',
        '#include "generated_compiler_emitted_sm86_kernels.cuh"',
        "tuc::compiler_emitted_gpu::tuc_projection_matmul_4x8x2_f32",
        "tuc::compiler_emitted_gpu::tuc_activated_relu_4x2_f32",
        "tuc.bounded_compiler_emitted_gpu_observation_worker.v0",
        '"nvidia_cuda_sm86"',
        "kWorkloadAllocationBytes == 256",
    )
    if any(fragment not in harness for fragment in required_harness_fragments):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU harness contract drift"
        )
    forbidden_harness_fragments = (
        "__global__",
        "dlopen(",
        "exec(",
        "popen(",
        "system(",
    )
    if any(fragment in harness for fragment in forbidden_harness_fragments):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU harness execution surface rejected"
        )
    kernel_symbols = (
        "tuc_projection_matmul_4x8x2_f32",
        "tuc_activated_relu_4x2_f32",
    )
    if kernel_header.count("__global__ void") != 2 or any(
        kernel_header.count(symbol) != 1 for symbol in kernel_symbols
    ):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU kernel surface drift"
        )
    forbidden_kernel_fragments = ("asm(", "#include <filesystem>", "#include <fstream>")
    if any(fragment in kernel_header for fragment in forbidden_kernel_fragments):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU kernel capability rejected"
        )

    required_dockerfile_fragments = (
        "TUC_GPU_OBSERVATION_SOURCE_INTENT_DIGEST",
        "TUC_GPU_OBSERVATION_EMITTED_KERNEL_DIGEST",
        "TUC_GPU_OBSERVATION_EMISSION_PLAN_DIGEST",
        "test \"$(grep -c '__global__ void'",
        "test -z \"$(grep '__global__'",
        "cuobjdump --list-ptx",
    )
    if any(fragment not in dockerfile for fragment in required_dockerfile_fragments):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU build binding drift"
        )


def validate_compiler_emitted_gpu_sources(
    profile: GpuObservationProfile = PROFILE,
) -> CompilerEmissionArtifacts:
    """Validate deterministic emission and its fixed, non-interpreting harness."""

    _require_profile(profile)
    try:
        artifacts = validate_checked_in_compiler_emission()
        _validate_profile_build_surface(profile)
    except (BoundedCompilerEmissionError, GpuObservationError) as exc:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU static validation rejected"
        ) from exc
    _validate_emitted_cuda_surface(artifacts)
    return artifacts


def _static_sections(
    artifacts: CompilerEmissionArtifacts,
) -> dict[str, dict[str, object]]:
    plan = artifacts.plan
    return {
        "claim_boundary": {
            "blocked_claims": list(COMPILER_EMITTED_GPU_BLOCKED_CLAIMS),
            "device_access_gate_reinterpreted": False,
            "driver_security_review": "operator_attested_current_vendor_update",
            "external_reproduction": "not_yet_supplied",
            "native_backend_gate_reinterpreted": False,
            "normal_executor_modified": False,
            "shared_display_risk_acknowledged": True,
        },
        "emission": {
            "code_generated": True,
            "code_generation_phase": plan["code_generation_phase"],
            "emission_contract": COMPILER_EMISSION_CONTRACT,
            "emission_plan_verified": True,
            "generated_kernel_count": 2,
            "identifier_policy": plan["identifier_policy"],
            "operation_families": ["matmul", "elementwise"],
            "runtime_generated_code": False,
            "source_intent_accepted": True,
            "source_intent_schema_version": "source_intent.v0",
            "source_text_executed": False,
            "target_profile": PROFILE.profile_id,
        },
        "execution": {
            "accelerator_class": PROFILE.accelerator_class,
            "compiler_emitted_cuda_execution": True,
            "device_access": True,
            "driver_api_called": True,
            "jit_execution": False,
            "kernel_launch_count": 2,
            "performance_measurement_collected": False,
            "physical_device_execution": True,
            "runtime_generated_code": False,
            "tuc_native_backend_admitted": False,
            "visible_device_count": 1,
            "workload_device_allocation_bytes": PROFILE.workload_allocation_bytes,
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
            "pids_limit": PROFILE.pids_limit,
            "repository_mount": False,
            "root_filesystem_read_only": True,
            "runtime_boundary": "docker_compose_nvidia_device_request",
            "seccomp_mode": 2,
        },
        "privacy": {
            "device_name_serialized": False,
            "driver_version_serialized": False,
            "environment_serialized": False,
            "generated_source_serialized": False,
            "hardware_identifiers_serialized": False,
            "host_paths_serialized": False,
            "raw_tensor_values_serialized": False,
            "raw_timing_samples_serialized": False,
            "source_text_serialized": False,
        },
        "proof": {
            "claim": COMPILER_EMITTED_GPU_PROOF_CLAIM,
            "contract": PROFILE.proof_contract,
            "scope": PROFILE.proof_scope,
            "status": "PASS",
        },
        "workload": {
            "dtype": PROFILE.dtype,
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


def _static_provenance(artifacts: CompilerEmissionArtifacts) -> dict[str, object]:
    plan = artifacts.plan
    return {
        "builder_image": GPU_OBSERVATION_DEVEL_IMAGE,
        "cuda_harness_digest": _digest_file(PROFILE.cuda_source_path),
        "dockerfile_digest": _digest_file(PROFILE.dockerfile_path),
        "emission_plan_file_digest": _digest_file(
            next(
                path
                for build_arg, _label, path in PROFILE.extra_digest_bindings
                if build_arg == "TUC_GPU_OBSERVATION_EMISSION_PLAN_DIGEST"
            )
        ),
        "emission_plan_payload_digest": plan["plan_digest"],
        "emitted_kernel_digest": plan["emitted_kernel_digest"],
        "ptx_jit_disabled": True,
        "runtime_image": GPU_OBSERVATION_RUNTIME_IMAGE,
        "sass_target": PROFILE.sass_target,
        "source_intent_file_digest": _digest_file(
            next(
                path
                for build_arg, _label, path in PROFILE.extra_digest_bindings
                if build_arg == "TUC_GPU_OBSERVATION_SOURCE_INTENT_DIGEST"
            )
        ),
        "source_intent_payload_digest": plan["source_intent_digest"],
        "workload_header_digest": plan["workload_header_digest"],
        "workload_manifest_file_digest": _digest_file(PROFILE.workload_manifest_path),
        "workload_payload_digest": plan["workload_digest"],
    }


def build_compiler_emitted_gpu_observation_report(
    response: object,
    compose_contract: object,
    image_metadata: object,
    *,
    driver_security_reviewed: bool,
    shared_display_risk_acknowledged: bool,
    profile: GpuObservationProfile = PROFILE,
) -> dict[str, object]:
    """Bind deterministic lowering and one exact physical run into evidence."""

    _require_profile(profile)
    if not driver_security_reviewed:
        raise BoundedCompilerEmittedGpuProofError(
            "current vendor driver security update not attested"
        )
    if not shared_display_risk_acknowledged:
        raise BoundedCompilerEmittedGpuProofError(
            "shared display GPU risk not acknowledged"
        )
    artifacts = validate_compiler_emitted_gpu_sources(profile)
    try:
        worker = _validate_worker_response(response, mode="execute", profile=profile)
        compose = _validate_compose_config(compose_contract, profile)
        image = _validate_image_metadata(image_metadata, profile)
    except GpuObservationError as exc:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU runtime evidence rejected"
        ) from exc
    sections = _static_sections(artifacts)
    isolation = sections["isolation"]
    isolation["cpu_limit"] = compose["cpus"]
    isolation["memory_limit_bytes"] = compose["mem_limit"]
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
        "schema_version": COMPILER_EMITTED_GPU_SCHEMA_VERSION,
    }
    report["report_digest"] = _digest_payload(report)
    return assert_compiler_emitted_gpu_observation_report(report, profile=profile)


def assert_compiler_emitted_gpu_observation_report(
    report: object,
    *,
    profile: GpuObservationProfile = PROFILE,
) -> dict[str, object]:
    """Fail closed unless a report proves exactly the admitted research claim."""

    _require_profile(profile)
    if type(report) is not dict:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU report must be a plain object"
        )
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU report key drift"
        )
    digest = typed.get("report_digest")
    digest_source = dict(typed)
    digest_source.pop("report_digest", None)
    if digest != _digest_payload(digest_source):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU report digest mismatch"
        )
    artifacts = validate_compiler_emitted_gpu_sources(profile)
    expected_sections = _static_sections(artifacts)
    if typed.get("schema_version") != COMPILER_EMITTED_GPU_SCHEMA_VERSION:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU report schema drift"
        )
    for name, expected in expected_sections.items():
        if typed.get(name) != expected:
            raise BoundedCompilerEmittedGpuProofError(
                f"compiler-emitted GPU {name} invariant drift"
            )

    provenance = typed.get("provenance")
    if type(provenance) is not dict:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU provenance missing"
        )
    provenance_typed = cast(dict[str, object], provenance)
    expected_static_provenance = _static_provenance(artifacts)
    expected_provenance_keys = frozenset(
        {
            *expected_static_provenance,
            "compose_contract_digest",
            "container_image_digest",
            "image_config_verified",
            "image_source_binding_verified",
            "worker_observation_digest",
        }
    )
    if frozenset(provenance_typed) != expected_provenance_keys:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU provenance key drift"
        )
    if any(
        provenance_typed.get(key) != value
        for key, value in expected_static_provenance.items()
    ):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU provenance binding drift"
        )
    if provenance_typed.get("compose_contract_digest") != _digest_payload(
        _validate_compose_config(_synthetic_compose_config(profile), profile)
    ):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU Compose digest drift"
        )
    if provenance_typed.get("worker_observation_digest") != _digest_payload(
        _expected_execution_worker(profile)
    ):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU worker digest drift"
        )
    if provenance_typed.get("image_config_verified") is not True or (
        provenance_typed.get("image_source_binding_verified") is not True
    ):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU image verification drift"
        )
    image_digest = provenance_typed.get("container_image_digest")
    if not isinstance(image_digest, str) or _DIGEST_RE.fullmatch(image_digest) is None:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU image digest rejected"
        )
    return typed


def _expected_execution_worker(profile: GpuObservationProfile) -> dict[str, object]:
    from examples.bounded_gpu_observation_proof import _expected_worker_response

    return _expected_worker_response("execute", profile)


def _synthetic_compose_config(profile: GpuObservationProfile) -> dict[str, object]:
    from examples.bounded_gpu_observation_proof import _expected_compose_contract

    expected = _expected_compose_contract(profile)
    return {
        "services": {
            profile.service: {
                "build": {
                    "args": expected["build_args"],
                    "context": str(profile.build_context_path.resolve()),
                    "dockerfile": profile.dockerfile_path.name,
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


def dump_compiler_emitted_gpu_observation_report(
    report: object,
    *,
    profile: GpuObservationProfile = PROFILE,
) -> str:
    """Return deterministic metadata-only evidence for the admitted proof."""

    typed = assert_compiler_emitted_gpu_observation_report(report, profile=profile)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU report exceeds limit"
        )
    forbidden_fragments = (
        '"command"',
        '"device_uuid"',
        '"host_path"',
        '"raw_tensor_values"',
        '"source_text"',
        "C:\\Users\\",
        "/home/",
    )
    if any(fragment in rendered for fragment in forbidden_fragments):
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU report leaks forbidden data"
        )
    return rendered


def run_compiler_emitted_gpu_observation(
    mode: str,
    *,
    driver_security_reviewed: bool = False,
    shared_display_risk_acknowledged: bool = False,
    profile: GpuObservationProfile = PROFILE,
) -> dict[str, object]:
    """Run a zero-kernel preflight or the explicitly acknowledged physical proof."""

    _require_profile(profile)
    if mode not in {"execute", "preflight"}:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU mode rejected"
        )
    if mode == "execute" and not driver_security_reviewed:
        raise BoundedCompilerEmittedGpuProofError(
            "current vendor driver security update not attested"
        )
    if mode == "execute" and not shared_display_risk_acknowledged:
        raise BoundedCompilerEmittedGpuProofError(
            "shared display GPU risk not acknowledged"
        )
    artifacts = validate_compiler_emitted_gpu_sources(profile)
    try:
        compose_raw = _load_compose_config(profile)
        _validate_compose_config(compose_raw, profile)
        image_metadata = _load_image_metadata(profile)
        image = _validate_image_metadata(image_metadata, profile)
        response = _run_worker(
            mode,
            cast(str, image["container_image_digest"]),
            profile,
        )
    except GpuObservationError as exc:
        raise BoundedCompilerEmittedGpuProofError(
            "compiler-emitted GPU runtime rejected"
        ) from exc
    if mode == "preflight":
        return {
            "accelerator_class": response["accelerator_class"],
            "compiler_emission_plan_digest": artifacts.plan["plan_digest"],
            "container_image_digest": image["container_image_digest"],
            "device_access": True,
            "generated_kernel_count": 2,
            "kernel_launch_count": 0,
            "mode": "preflight",
            "proof_status": "NOT_EXECUTED",
            "sanitized": True,
            "schema_version": profile.preflight_schema_version,
            "security_boundary_passed": True,
            "source_text_executed": False,
            "visible_device_count": 1,
            "workload_manifest_digest": response["workload_manifest_digest"],
        }
    return build_compiler_emitted_gpu_observation_report(
        response,
        compose_raw,
        image_metadata,
        driver_security_reviewed=driver_security_reviewed,
        shared_display_risk_acknowledged=shared_display_risk_acknowledged,
        profile=profile,
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
        report = run_compiler_emitted_gpu_observation(
            mode,
            driver_security_reviewed=args.attest_current_driver_security_update,
            shared_display_risk_acknowledged=args.acknowledge_shared_display_risk,
        )
        if mode == "execute":
            sys.stdout.write(dump_compiler_emitted_gpu_observation_report(report))
        else:
            sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except BoundedCompilerEmittedGpuProofError as exc:
        print(f"bounded compiler-emitted GPU proof rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
