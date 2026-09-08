"""Bind CUDA/SASS and C11/x86_64 observations for one exact Source Intent."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

from examples.bounded_compiler_emission import _digest_payload
from examples.bounded_compiler_emitted_c11_proof import (
    C11_GOLDEN_PATH,
    BoundedCompilerEmittedC11ProofError,
    _decode_json,
    assert_compiler_emitted_c11_observation_report,
)
from examples.bounded_compiler_emitted_gpu_proof import (
    BoundedCompilerEmittedGpuProofError,
    assert_compiler_emitted_gpu_observation_report,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GPU_GOLDEN_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/proofs/bounded_compiler_emitted_gpu_observation_report.json"
)
TARGET_EQUIVALENCE_SCHEMA_PATH = (
    REPOSITORY_ROOT / "schemas/bounded_compiler_target_equivalence_proof.v0.schema.json"
)
TARGET_EQUIVALENCE_GOLDEN_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/proofs/bounded_compiler_target_equivalence_proof.json"
)

TARGET_EQUIVALENCE_SCHEMA_VERSION = "tuc.bounded_compiler_target_equivalence.v0"
TARGET_EQUIVALENCE_CONTRACT = "bounded_compiler_target_equivalence.v0"
TARGET_EQUIVALENCE_CLAIM = (
    "one_exact_source_intent_preserves_reference_semantics_across_compiler_"
    "emitted_cuda_sass_and_non_cuda_static_c11_targets"
)
TARGET_EQUIVALENCE_BLOCKED_CLAIMS = (
    "arbitrary_program_portability",
    "cross_isa_portability",
    "cross_vendor_accelerator_execution",
    "general_native_backends",
    "independent_reproduction",
    "native_performance_parity",
    "production_runtime_admission",
    "universal_hardware_proof",
    "vendor_replacement",
)
_MAX_INPUT_BYTES = 64 * 1024
_MAX_REPORT_BYTES = 64 * 1024
_REPORT_KEYS = frozenset(
    {
        "claim_boundary",
        "equivalence",
        "observations",
        "proof",
        "report_digest",
        "schema_version",
        "source_intent",
        "workload",
    }
)


class BoundedCompilerTargetEquivalenceError(ValueError):
    """Raised when cross-target compiler evidence fails closed."""


def _load_report(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise BoundedCompilerTargetEquivalenceError("target report symbolic link rejected")
    try:
        before = path.stat()
        if not path.is_file() or not 0 < before.st_size <= _MAX_INPUT_BYTES:
            raise BoundedCompilerTargetEquivalenceError("target report size rejected")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise BoundedCompilerTargetEquivalenceError("target report unavailable") from exc
    if len(raw) != before.st_size or before.st_size != after.st_size:
        raise BoundedCompilerTargetEquivalenceError("target report changed while reading")
    try:
        return _decode_json(raw, "compiler target observation")
    except BoundedCompilerEmittedC11ProofError as exc:
        raise BoundedCompilerTargetEquivalenceError("target report JSON rejected") from exc


def _summary(
    report: dict[str, object],
    *,
    target_family: str,
    generated_artifact_kind: str,
    execution_model: str,
) -> dict[str, object]:
    emission = cast(dict[str, object], report["emission"])
    provenance = cast(dict[str, object], report["provenance"])
    generated_count = emission.get("generated_kernel_count")
    if generated_count is None:
        generated_count = emission["generated_function_count"]
    return {
        "container_image_digest": provenance["container_image_digest"],
        "emission_plan_payload_digest": provenance["emission_plan_payload_digest"],
        "execution_model": execution_model,
        "generated_artifact_count": generated_count,
        "generated_artifact_kind": generated_artifact_kind,
        "reference_correctness_passed": True,
        "report_digest": report["report_digest"],
        "schema_version": report["schema_version"],
        "source_intent_payload_digest": provenance["source_intent_payload_digest"],
        "target_family": target_family,
        "workload_payload_digest": provenance["workload_payload_digest"],
    }


def _build_bounded_compiler_target_equivalence_proof_unchecked(
    gpu_observation: object,
    c11_observation: object,
) -> dict[str, object]:
    """Build the exact aggregate without recursively invoking its validator."""

    try:
        gpu = assert_compiler_emitted_gpu_observation_report(gpu_observation)
        c11 = assert_compiler_emitted_c11_observation_report(c11_observation)
    except (
        BoundedCompilerEmittedC11ProofError,
        BoundedCompilerEmittedGpuProofError,
    ) as exc:
        raise BoundedCompilerTargetEquivalenceError(
            "compiler target observation rejected"
        ) from exc
    gpu_provenance = cast(dict[str, object], gpu["provenance"])
    c11_provenance = cast(dict[str, object], c11["provenance"])
    if gpu["workload"] != c11["workload"]:
        raise BoundedCompilerTargetEquivalenceError("target workload semantics differ")
    if (
        gpu_provenance["source_intent_payload_digest"]
        != c11_provenance["source_intent_payload_digest"]
        or gpu_provenance["source_intent_file_digest"]
        != c11_provenance["source_intent_file_digest"]
    ):
        raise BoundedCompilerTargetEquivalenceError("target Source Intent differs")
    if (
        gpu_provenance["workload_payload_digest"]
        != c11_provenance["workload_payload_digest"]
        or gpu_provenance["workload_manifest_file_digest"]
        != c11_provenance["workload_manifest_file_digest"]
    ):
        raise BoundedCompilerTargetEquivalenceError("target workload provenance differs")

    report: dict[str, object] = {
        "claim_boundary": {
            "blocked_claims": list(TARGET_EQUIVALENCE_BLOCKED_CLAIMS),
            "compiler_target_count": 2,
            "hardware_interface_feasibility_strengthened": True,
            "independent_reproduction": "not_yet_supplied",
            "non_cuda_target_count": 1,
            "observation_ownership": "same_maintainer",
            "universal_compute_claim_proven": False,
        },
        "equivalence": {
            "cuda_dependency_absent_for_c11_target": True,
            "operation_families_equal": True,
            "raw_tensor_values_serialized": False,
            "reference_correctness_passed_all": True,
            "runtime_generated_code_all": False,
            "source_intent_payload_digest_equal": True,
            "target_specific_facts_outside_source_intent": True,
            "terminal_reference_semantics_equal": True,
            "tensor_shape_dtype_equal": True,
            "workload_payload_digest_equal": True,
        },
        "observations": [
            _summary(
                gpu,
                target_family="cuda_sass_sm86",
                generated_artifact_kind="cuda_kernel",
                execution_model="physical_gpu_aot_sass",
            ),
            _summary(
                c11,
                target_family="c11_static_elf_x86_64",
                generated_artifact_kind="c11_function",
                execution_model="controlled_host_aot_static_elf",
            ),
        ],
        "proof": {
            "claim": TARGET_EQUIVALENCE_CLAIM,
            "contract": TARGET_EQUIVALENCE_CONTRACT,
            "scope": "one_fixed_source_intent_two_same_maintainer_compiler_targets",
            "status": "PASS",
        },
        "schema_version": TARGET_EQUIVALENCE_SCHEMA_VERSION,
        "source_intent": {
            "payload_digest": gpu_provenance["source_intent_payload_digest"],
            "schema_version": "source_intent.v0",
        },
        "workload": gpu["workload"],
    }
    report["report_digest"] = _digest_payload(report)
    return report


def build_bounded_compiler_target_equivalence_proof(
    gpu_observation: object,
    c11_observation: object,
) -> dict[str, object]:
    """Build metadata-only equivalence over two independently bounded targets."""

    report = _build_bounded_compiler_target_equivalence_proof_unchecked(
        gpu_observation,
        c11_observation,
    )
    return assert_bounded_compiler_target_equivalence_proof(report)


def assert_bounded_compiler_target_equivalence_proof(
    report: object,
) -> dict[str, object]:
    """Fail closed unless the aggregate preserves the exact two-target claim."""

    if type(report) is not dict:
        raise BoundedCompilerTargetEquivalenceError("target equivalence must be an object")
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise BoundedCompilerTargetEquivalenceError("target equivalence key drift")
    expected = _build_bounded_compiler_target_equivalence_proof_unchecked(
        _load_report(GPU_GOLDEN_PATH),
        _load_report(C11_GOLDEN_PATH),
    )
    if typed != expected:
        raise BoundedCompilerTargetEquivalenceError("target equivalence invariant drift")
    digest_source = dict(typed)
    digest = digest_source.pop("report_digest", None)
    if digest != _digest_payload(digest_source):
        raise BoundedCompilerTargetEquivalenceError("target equivalence digest mismatch")
    return typed


def dump_bounded_compiler_target_equivalence_proof(report: object) -> str:
    """Render deterministic metadata-only target-equivalence evidence."""

    typed = assert_bounded_compiler_target_equivalence_proof(report)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise BoundedCompilerTargetEquivalenceError("target equivalence exceeds limit")
    forbidden = (
        '"command"',
        '"cpu_model"',
        '"device_uuid"',
        '"generated_source"',
        '"host_path"',
        '"raw_tensor_values"',
        "C:\\Users\\",
        "/home/",
    )
    if any(fragment in rendered for fragment in forbidden):
        raise BoundedCompilerTargetEquivalenceError(
            "target equivalence leaks forbidden data"
        )
    return rendered


def main() -> int:
    try:
        report = build_bounded_compiler_target_equivalence_proof(
            _load_report(GPU_GOLDEN_PATH),
            _load_report(C11_GOLDEN_PATH),
        )
        sys.stdout.write(dump_bounded_compiler_target_equivalence_proof(report))
    except BoundedCompilerTargetEquivalenceError as exc:
        print(f"bounded compiler target equivalence rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
