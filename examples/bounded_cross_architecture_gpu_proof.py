"""Combine two bounded GPU observations without widening their claims."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from examples.bounded_gpu_observation_proof import (
    GPU_SM70_PROFILE,
    GPU_SM86_PROFILE,
    GpuObservationError,
    _digest_payload,
    assert_bounded_gpu_observation_report,
)

CROSS_ARCHITECTURE_SCHEMA_VERSION = (
    "tuc.bounded_cross_architecture_gpu_proof.v0"
)
CROSS_ARCHITECTURE_PROOF_CONTRACT = (
    "bounded_cross_architecture_gpu_equivalence.v0"
)
CROSS_ARCHITECTURE_PROOF_CLAIM = (
    "same_fixed_neutral_compute_intent_executes_on_two_nvidia_architectures_"
    "and_matches_cpu_reference"
)
CROSS_ARCHITECTURE_BLOCKED_CLAIMS = (
    "arbitrary_program_portability",
    "cross_vendor_execution",
    "general_native_backend",
    "independent_reproduction",
    "native_performance_parity",
    "production_device_admission",
    "universal_hardware_proof",
    "vendor_replacement",
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SM70_OBSERVATION_PATH = (
    REPOSITORY_ROOT / "tests/golden/proofs/bounded_gpu_observation_report.json"
)
SM86_OBSERVATION_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/proofs/bounded_gpu_sm86_observation_report.json"
)
_MAX_INPUT_BYTES = 64 * 1024
_MAX_REPORT_BYTES = 32 * 1024
_REPORT_KEYS = frozenset(
    {
        "claim_boundary",
        "equivalence",
        "observations",
        "proof",
        "report_digest",
        "schema_version",
        "workload",
    }
)


def _load_observation(path: Path) -> dict[str, object]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise GpuObservationError("cross-architecture observation unavailable") from exc
    if size <= 0 or size > _MAX_INPUT_BYTES:
        raise GpuObservationError("cross-architecture observation size rejected")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GpuObservationError("cross-architecture observation JSON rejected") from exc
    if type(payload) is not dict:
        raise GpuObservationError("cross-architecture observation must be an object")
    return cast(dict[str, object], payload)


def _observation_summary(report: dict[str, object]) -> dict[str, object]:
    execution = cast(dict[str, object], report["execution"])
    provenance = cast(dict[str, object], report["provenance"])
    return {
        "accelerator_class": execution["accelerator_class"],
        "container_image_digest": provenance["container_image_digest"],
        "kernel_launch_count": execution["kernel_launch_count"],
        "report_digest": report["report_digest"],
        "sass_target": provenance["sass_target"],
        "schema_version": report["schema_version"],
        "workload_manifest_digest": provenance["workload_manifest_digest"],
    }


def build_bounded_cross_architecture_gpu_proof(
    sm70_observation: object,
    sm86_observation: object,
) -> dict[str, object]:
    """Bind two exact physical observations into a metadata-only proof."""

    sm70 = assert_bounded_gpu_observation_report(
        sm70_observation,
        profile=GPU_SM70_PROFILE,
    )
    sm86 = assert_bounded_gpu_observation_report(
        sm86_observation,
        profile=GPU_SM86_PROFILE,
    )
    sm70_workload = cast(dict[str, object], sm70["workload"])
    sm86_workload = cast(dict[str, object], sm86["workload"])
    sm70_provenance = cast(dict[str, object], sm70["provenance"])
    sm86_provenance = cast(dict[str, object], sm86["provenance"])
    if sm70_workload != sm86_workload:
        raise GpuObservationError("cross-architecture workload semantics differ")
    if (
        sm70_provenance["workload_manifest_digest"]
        != sm86_provenance["workload_manifest_digest"]
    ):
        raise GpuObservationError("cross-architecture workload provenance differs")

    report: dict[str, object] = {
        "claim_boundary": {
            "architecture_count": 2,
            "blocked_claims": list(CROSS_ARCHITECTURE_BLOCKED_CLAIMS),
            "independent_reproduction": "not_yet_supplied",
            "observation_ownership": "same_maintainer",
            "universal_compute_claim_proven": False,
            "vendor_count": 1,
        },
        "equivalence": {
            "cpu_reference_match_all": True,
            "fixed_kernel_count_equal": True,
            "operation_families_equal": True,
            "ptx_jit_disabled_all": True,
            "raw_tensor_values_serialized": False,
            "runtime_generated_code_all": False,
            "tensor_shape_dtype_equal": True,
            "workload_manifest_digest_equal": True,
        },
        "observations": [
            _observation_summary(sm70),
            _observation_summary(sm86),
        ],
        "proof": {
            "claim": CROSS_ARCHITECTURE_PROOF_CLAIM,
            "contract": CROSS_ARCHITECTURE_PROOF_CONTRACT,
            "scope": "two_same_maintainer_fixed_hardware_observations",
            "status": "PASS",
        },
        "schema_version": CROSS_ARCHITECTURE_SCHEMA_VERSION,
        "workload": sm70_workload,
    }
    report["report_digest"] = _digest_payload(report)
    return assert_bounded_cross_architecture_gpu_proof(report)


def assert_bounded_cross_architecture_gpu_proof(
    report: object,
) -> dict[str, object]:
    """Fail closed unless the aggregate remains a narrow two-profile claim."""

    if type(report) is not dict:
        raise GpuObservationError("cross-architecture proof must be an object")
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise GpuObservationError("cross-architecture proof key drift")
    if typed.get("schema_version") != CROSS_ARCHITECTURE_SCHEMA_VERSION:
        raise GpuObservationError("cross-architecture proof schema drift")

    expected_claim_boundary = {
        "architecture_count": 2,
        "blocked_claims": list(CROSS_ARCHITECTURE_BLOCKED_CLAIMS),
        "independent_reproduction": "not_yet_supplied",
        "observation_ownership": "same_maintainer",
        "universal_compute_claim_proven": False,
        "vendor_count": 1,
    }
    expected_equivalence = {
        "cpu_reference_match_all": True,
        "fixed_kernel_count_equal": True,
        "operation_families_equal": True,
        "ptx_jit_disabled_all": True,
        "raw_tensor_values_serialized": False,
        "runtime_generated_code_all": False,
        "tensor_shape_dtype_equal": True,
        "workload_manifest_digest_equal": True,
    }
    expected_proof = {
        "claim": CROSS_ARCHITECTURE_PROOF_CLAIM,
        "contract": CROSS_ARCHITECTURE_PROOF_CONTRACT,
        "scope": "two_same_maintainer_fixed_hardware_observations",
        "status": "PASS",
    }
    if typed.get("claim_boundary") != expected_claim_boundary:
        raise GpuObservationError("cross-architecture claim boundary drift")
    if typed.get("equivalence") != expected_equivalence:
        raise GpuObservationError("cross-architecture equivalence drift")
    if typed.get("proof") != expected_proof:
        raise GpuObservationError("cross-architecture proof claim drift")

    observations = typed.get("observations")
    if type(observations) is not list or len(observations) != 2:
        raise GpuObservationError("cross-architecture observations drift")
    expected_pairs = (
        (GPU_SM70_PROFILE, observations[0]),
        (GPU_SM86_PROFILE, observations[1]),
    )
    manifest_digests: set[object] = set()
    for profile, observation in expected_pairs:
        if type(observation) is not dict:
            raise GpuObservationError("cross-architecture observation shape drift")
        item = cast(dict[str, object], observation)
        expected_keys = {
            "accelerator_class",
            "container_image_digest",
            "kernel_launch_count",
            "report_digest",
            "sass_target",
            "schema_version",
            "workload_manifest_digest",
        }
        if set(item) != expected_keys:
            raise GpuObservationError("cross-architecture observation key drift")
        if (
            item["accelerator_class"] != profile.accelerator_class
            or item["kernel_launch_count"] != 2
            or item["sass_target"] != profile.sass_target
            or item["schema_version"] != profile.schema_version
        ):
            raise GpuObservationError("cross-architecture observation identity drift")
        for field in (
            "container_image_digest",
            "report_digest",
            "workload_manifest_digest",
        ):
            value = item[field]
            if (
                not isinstance(value, str)
                or len(value) != 71
                or not value.startswith("sha256:")
                or any(character not in "0123456789abcdef" for character in value[7:])
            ):
                raise GpuObservationError(
                    "cross-architecture observation digest rejected"
                )
        manifest_digests.add(item["workload_manifest_digest"])
    if len(manifest_digests) != 1:
        raise GpuObservationError("cross-architecture workload digest drift")

    workload = typed.get("workload")
    if workload != {
        "dtype": "float64",
        "input_policy": "fixed_public_non_sensitive_test_vector",
        "operation_families": ["matmul", "elementwise"],
        "reference_correctness_passed": True,
        "semantic_origin": "objective_delta_portable_compute_v0",
        "shape": [2, 2],
        "workload_contract": "objective_delta_matmul_elementwise_2x2_f64.v0",
    }:
        raise GpuObservationError("cross-architecture workload contract drift")

    report_digest = typed.get("report_digest")
    digest_source = dict(typed)
    digest_source.pop("report_digest", None)
    if report_digest != _digest_payload(digest_source):
        raise GpuObservationError("cross-architecture proof digest mismatch")
    return typed


def dump_bounded_cross_architecture_gpu_proof(report: object) -> str:
    """Render deterministic metadata-only aggregate evidence."""

    typed = assert_bounded_cross_architecture_gpu_proof(report)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise GpuObservationError("cross-architecture proof exceeds size limit")
    forbidden_fragments = (
        '"command"',
        '"device_uuid"',
        '"driver_version"',
        '"host_path"',
        '"pci_bus_id"',
        '"raw_tensor_values"',
        '"serial_number"',
        "C:\\\\Users\\\\",
        "/home/",
    )
    if any(fragment in rendered for fragment in forbidden_fragments):
        raise GpuObservationError("cross-architecture proof leaks forbidden data")
    return rendered


def main() -> int:
    try:
        report = build_bounded_cross_architecture_gpu_proof(
            _load_observation(SM70_OBSERVATION_PATH),
            _load_observation(SM86_OBSERVATION_PATH),
        )
        sys.stdout.write(dump_bounded_cross_architecture_gpu_proof(report))
    except GpuObservationError as exc:
        print(f"cross-architecture GPU proof rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
