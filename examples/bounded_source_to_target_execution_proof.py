"""Bind one inert Triton source case to two executed compiler targets."""

from __future__ import annotations

import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import cast

from examples import (
    bounded_compiler_target_equivalence_proof as target_proof,
    oci_source_ingestion_research_proof as oci_proof,
)
from examples.bounded_compiler_emission import _digest_payload
from examples.bounded_compiler_emitted_c11_proof import (
    BoundedCompilerEmittedC11ProofError,
    _decode_json,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "schemas/bounded_source_to_target_execution_proof.v0.schema.json"
)
GOLDEN_PATH = (
    REPOSITORY_ROOT
    / "tests/golden/proofs/bounded_source_to_target_execution_proof.json"
)
OCI_GOLDEN_PATH = oci_proof.GOLDEN_PATH
TARGET_EQUIVALENCE_GOLDEN_PATH = target_proof.TARGET_EQUIVALENCE_GOLDEN_PATH

SCHEMA_VERSION = "tuc.bounded_source_to_target_execution_proof.v0"
PROOF_CONTRACT = "bounded_source_to_target_execution.digest_bound.v0"
PROOF_CLAIM = (
    "one_fixed_inert_triton_source_case_lowers_to_the_same_source_intent_"
    "whose_compiler_emitted_cuda_sass_and_static_c11_targets_preserve_"
    "terminal_reference_semantics"
)
BLOCKED_CLAIMS = (
    "arbitrary_program_portability",
    "arbitrary_triton_source_ingestion",
    "cross_isa_portability",
    "cross_vendor_accelerator_execution",
    "general_native_backends",
    "general_triton_parser",
    "independent_reproduction",
    "native_performance_parity",
    "production_runtime_admission",
    "production_source_ingestion",
    "universal_hardware_proof",
    "vendor_replacement",
)

_MAX_INPUT_BYTES = 128 * 1024
_MAX_REPORT_BYTES = 64 * 1024
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REPORT_KEYS = frozenset(
    {
        "binding",
        "claim_boundary",
        "frontend",
        "proof",
        "report_digest",
        "schema_version",
        "target_execution",
    }
)


class BoundedSourceToTargetExecutionProofError(ValueError):
    """Raised when the source-to-target evidence chain fails closed."""


def _read_bounded_file(path: Path, label: str) -> bytes:
    if path.is_symlink():
        raise BoundedSourceToTargetExecutionProofError(f"{label} symbolic link rejected")
    try:
        before = path.stat()
        if not path.is_file() or not 0 < before.st_size <= _MAX_INPUT_BYTES:
            raise BoundedSourceToTargetExecutionProofError(f"{label} size rejected")
        raw = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise BoundedSourceToTargetExecutionProofError(f"{label} unavailable") from exc
    before_identity = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    after_identity = (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    )
    if len(raw) != before.st_size or before_identity != after_identity:
        raise BoundedSourceToTargetExecutionProofError(f"{label} changed while reading")
    return raw


def _load_report(path: Path, label: str) -> dict[str, object]:
    raw = _read_bounded_file(path, label)
    try:
        return _decode_json(raw, label)
    except BoundedCompilerEmittedC11ProofError as exc:
        raise BoundedSourceToTargetExecutionProofError(f"{label} JSON rejected") from exc


def _digest_file(path: Path, label: str) -> str:
    raw = _read_bounded_file(path, label)
    return f"sha256:{sha256(raw).hexdigest()}"


def _validate_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise BoundedSourceToTargetExecutionProofError(f"{label} digest invalid")
    return value


def _build_unchecked(
    frontend_report: object,
    target_equivalence_report: object,
) -> dict[str, object]:
    try:
        frontend = oci_proof.assert_oci_source_ingestion_research_proof_report(
            frontend_report
        )
        target = target_proof.assert_bounded_compiler_target_equivalence_proof(
            target_equivalence_report
        )
    except (TypeError, ValueError) as exc:
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target child evidence rejected"
        ) from exc

    _, expected_worker_request_digest = oci_proof._build_worker_request()
    expected_source_intent_digest = oci_proof._digest_payload(
        oci_proof.EXPECTED_SOURCE_INTENT
    )
    target_source_intent = cast(dict[str, object], target["source_intent"])
    target_workload = cast(dict[str, object], target["workload"])
    target_equivalence = cast(dict[str, object], target["equivalence"])
    observations = cast(list[object], target["observations"])

    if frontend["worker_request_digest"] != expected_worker_request_digest:
        raise BoundedSourceToTargetExecutionProofError(
            "canonical source request binding drift"
        )
    if frontend["source_intent_digest"] != expected_source_intent_digest:
        raise BoundedSourceToTargetExecutionProofError(
            "canonical frontend Source Intent drift"
        )
    if target_source_intent["payload_digest"] != expected_source_intent_digest:
        raise BoundedSourceToTargetExecutionProofError(
            "frontend and target Source Intent differ"
        )
    if sorted(cast(list[str], frontend["operation_families"])) != sorted(
        cast(list[str], target_workload["operation_families"])
    ):
        raise BoundedSourceToTargetExecutionProofError(
            "frontend and target operation families differ"
        )
    if len(observations) != 2:
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof requires exactly two targets"
        )

    target_families: list[str] = []
    execution_models: list[str] = []
    for observation in observations:
        if type(observation) is not dict:
            raise BoundedSourceToTargetExecutionProofError(
                "target observation must be an object"
            )
        typed_observation = cast(dict[str, object], observation)
        target_family = typed_observation.get("target_family")
        execution_model = typed_observation.get("execution_model")
        if not isinstance(target_family, str) or not isinstance(execution_model, str):
            raise BoundedSourceToTargetExecutionProofError(
                "target observation identity invalid"
            )
        target_families.append(target_family)
        execution_models.append(execution_model)

    report: dict[str, object] = {
        "binding": {
            "compiler_artifacts_ahead_of_time": True,
            "operation_families_equal": True,
            "raw_source_serialized": False,
            "raw_tensor_values_serialized": False,
            "source_intent_digest_equal": True,
            "source_request_matches_canonical_module": True,
            "source_text_executed": False,
            "target_specific_facts_outside_source_intent": True,
            "terminal_reference_semantics_preserved": True,
        },
        "claim_boundary": {
            "blocked_claims": list(BLOCKED_CLAIMS),
            "compiler_target_count": 2,
            "default_source_ingestion_admitted": False,
            "hardware_interface_feasibility_strengthened": True,
            "independent_reproduction": "not_yet_supplied",
            "observation_ownership": "same_maintainer",
            "source_case_count": 1,
            "source_ingestion_mode": "explicit_research_worker_only",
            "universal_compute_claim_proven": False,
        },
        "frontend": {
            "child_report_digest": frontend["report_digest"],
            "child_report_file_digest": _digest_file(
                OCI_GOLDEN_PATH,
                "OCI frontend report",
            ),
            "isolation_contract": frontend["proof_contract"],
            "kernel_name": oci_proof.KERNEL_NAME,
            "malicious_source_rejected": True,
            "module_digest": oci_proof._digest_text(oci_proof.MODULE_SOURCE),
            "schema_version": frontend["schema_version"],
            "source_intent_digest": frontend["source_intent_digest"],
            "source_name": oci_proof.SOURCE_NAME,
            "worker_protocol": frontend["worker_protocol"],
            "worker_request_digest": frontend["worker_request_digest"],
            "worker_source_digest": frontend["worker_source_digest"],
        },
        "proof": {
            "claim": PROOF_CLAIM,
            "contract": PROOF_CONTRACT,
            "scope": "one_fixed_same_maintainer_source_case_two_same_maintainer_targets",
            "status": "PASS",
        },
        "schema_version": SCHEMA_VERSION,
        "target_execution": {
            "child_report_digest": target["report_digest"],
            "child_report_file_digest": _digest_file(
                TARGET_EQUIVALENCE_GOLDEN_PATH,
                "target equivalence report",
            ),
            "compiler_target_count": 2,
            "execution_models": execution_models,
            "reference_correctness_passed_all": target_equivalence[
                "reference_correctness_passed_all"
            ],
            "runtime_generated_code_all": target_equivalence[
                "runtime_generated_code_all"
            ],
            "schema_version": target["schema_version"],
            "source_intent_digest": target_source_intent["payload_digest"],
            "target_families": target_families,
            "terminal_reference_semantics_equal": target_equivalence[
                "terminal_reference_semantics_equal"
            ],
            "workload_contract": target_workload["workload_contract"],
        },
    }
    report["report_digest"] = _digest_payload(report)
    return report


def build_bounded_source_to_target_execution_proof(
    frontend_report: object,
    target_equivalence_report: object,
) -> dict[str, object]:
    """Build the closed source-to-target aggregate from accepted child evidence."""

    return assert_bounded_source_to_target_execution_proof(
        _build_unchecked(frontend_report, target_equivalence_report)
    )


def assert_bounded_source_to_target_execution_proof(
    report: object,
) -> dict[str, object]:
    """Fail closed unless the exact vertical research claim is preserved."""

    if type(report) is not dict:
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof must be an object"
        )
    typed = cast(dict[str, object], report)
    if frozenset(typed) != _REPORT_KEYS:
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof key drift"
        )
    expected = _build_unchecked(
        _load_report(OCI_GOLDEN_PATH, "OCI frontend report"),
        _load_report(TARGET_EQUIVALENCE_GOLDEN_PATH, "target equivalence report"),
    )
    if typed != expected:
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof invariant drift"
        )
    digest_source = dict(typed)
    digest = digest_source.pop("report_digest", None)
    if digest != _digest_payload(digest_source):
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof digest mismatch"
        )
    _validate_digest(digest, "source-to-target proof")
    return typed


def dump_bounded_source_to_target_execution_proof(report: object) -> str:
    """Render deterministic metadata-only vertical proof evidence."""

    typed = assert_bounded_source_to_target_execution_proof(report)
    rendered = json.dumps(typed, indent=2, sort_keys=True) + "\n"
    if len(rendered.encode("utf-8")) > _MAX_REPORT_BYTES:
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof exceeds limit"
        )
    forbidden = (
        '"command"',
        '"cpu_model"',
        '"device_uuid"',
        '"generated_source"',
        '"host_path"',
        '"module_source"',
        '"raw_tensor_values"',
        '"source_intent_payload"',
        "@triton.jit",
        "C:\\Users\\",
        "import triton",
        "/home/",
    )
    if any(fragment in rendered for fragment in forbidden):
        raise BoundedSourceToTargetExecutionProofError(
            "source-to-target proof leaks forbidden data"
        )
    return rendered


def main() -> int:
    try:
        report = build_bounded_source_to_target_execution_proof(
            _load_report(OCI_GOLDEN_PATH, "OCI frontend report"),
            _load_report(
                TARGET_EQUIVALENCE_GOLDEN_PATH,
                "target equivalence report",
            ),
        )
        sys.stdout.write(dump_bounded_source_to_target_execution_proof(report))
    except BoundedSourceToTargetExecutionProofError as exc:
        print(f"bounded source-to-target proof rejected: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
