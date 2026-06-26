"""Digest-only public proof bundle for Objective Alpha."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION = (
    "tuc.objective_alpha_public_proof_bundle.v0"
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT = "objective_alpha.public_proof_bundle.v0"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS = "review_evidence"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS = "correctness_and_inspectability_only"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID = "objective_alpha_public_proof_bundle"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY = "digest_only"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS = (
    "proof_of_execution",
    "runtime_evidence_matrix",
    "runtime_evidence_gate",
    "proof_of_backend_equivalence",
    "runtime_execution_output_closure",
    "runtime_transfer_trace_replay_verifier",
    "runtime_backend_equivalence_transfer_binding",
    "runtime_layout_conversion_trace_replay_verifier",
    "runtime_backend_equivalence_layout_binding",
    "runtime_allocation_reconciliation",
    "runtime_memory_planning_gate",
    "research_onboarding_evidence",
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS = (
    "python examples/proof_of_execution.py",
    "python examples/runtime_evidence_matrix.py",
    "python examples/runtime_evidence_gate.py",
    "python examples/proof_of_backend_equivalence.py",
    "python examples/runtime_execution_output_closure.py",
    "python examples/runtime_transfer_trace_replay_verifier.py",
    "python examples/runtime_backend_equivalence_transfer_binding.py",
    "python examples/runtime_layout_conversion_trace_replay_verifier.py",
    "python examples/runtime_backend_equivalence_layout_binding.py",
    "python examples/runtime_allocation_reconciliation.py",
    "python examples/runtime_memory_planning_gate.py",
    "python examples/research_onboarding_evidence.py",
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS = (
    "deterministic_proof_output",
    "schema_versioned_matrix_report",
    "deterministic_gate_output",
    "schema_versioned_backend_equivalence_proof_report",
    "schema_versioned_output_closure_report",
    "schema_versioned_transfer_trace_replay_verifier_report",
    "schema_versioned_backend_equivalence_transfer_binding_report",
    "schema_versioned_layout_conversion_trace_replay_verifier_report",
    "schema_versioned_backend_equivalence_layout_binding_report",
    "schema_versioned_allocation_reconciliation_report",
    "deterministic_memory_planning_gate_output",
    "schema_versioned_onboarding_report",
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS = (
    "native_performance_parity",
    "vendor_compiler_replacement",
    "broad_source_code_parsing",
    "arbitrary_third_party_backend_execution",
    "device_access",
    "generated_artifact_execution",
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES = 16
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_FIELD_BYTES = 256
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_REPORT_BYTES = 64 * 1024

_BUNDLE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/ -]*$")
_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
_FORBIDDEN_BUNDLE_TEXT = (
    "..",
    "\\",
    "://",
    "backend_artifact",
    "device_id",
    "dynamic_library",
    "generated_code",
    "host_path",
    "plugin_entrypoint",
    "python_source",
    "raw_benchmark_output",
    "raw_tensor_value",
    "raw_timing_samples",
    "source_text",
    "subprocess",
)


@dataclass(frozen=True)
class ObjectiveAlphaPublicEvidenceEntry:
    """One digest-only evidence entry in the Objective Alpha public bundle."""

    evidence_id: str
    entry_point: str
    artifact_kind: str
    metadata_digest: str
    status: str = "passed"
    raw_output_policy: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY

    def __post_init__(self) -> None:
        _validate_bundle_text(self.evidence_id, "objective alpha evidence_id")
        _validate_bundle_text(self.entry_point, "objective alpha entry_point")
        _validate_bundle_text(self.artifact_kind, "objective alpha artifact_kind")
        _validate_bundle_text(self.status, "objective alpha status")
        _validate_bundle_text(self.raw_output_policy, "objective alpha raw_output_policy")
        _validate_digest(self.metadata_digest, "objective alpha metadata_digest")
        if self.status != "passed":
            raise ValueError("objective alpha evidence entries must be passed")
        if self.raw_output_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY:
            raise ValueError("objective alpha public bundle must be digest-only")


@dataclass(frozen=True)
class ObjectiveAlphaPublicProofBundle:
    """Digest-only bundle of the first public Objective Alpha proof path."""

    bundle_id: str
    evidence_entries: tuple[ObjectiveAlphaPublicEvidenceEntry, ...]
    bundle_contract: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT
    artifact_status: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS
    claim_status: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS
    raw_output_policy: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY
    blocked_claims: tuple[str, ...] = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    native_performance_claim: bool = False
    broad_source_parser_claim: bool = False
    vendor_replacement_claim: bool = False

    def __post_init__(self) -> None:
        _validate_bundle_text(self.bundle_id, "objective alpha bundle_id")
        if self.bundle_id != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID:
            raise ValueError("unexpected objective alpha public bundle id")
        if self.bundle_contract != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT:
            raise ValueError("objective alpha public bundle contract mismatch")
        if self.artifact_status != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS:
            raise ValueError("objective alpha public bundle artifact status mismatch")
        if self.claim_status != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS:
            raise ValueError("objective alpha public bundle claim status mismatch")
        if self.raw_output_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY:
            raise ValueError("objective alpha public bundle must stay digest-only")
        if self.blocked_claims != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS:
            raise ValueError("objective alpha blocked claims changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("objective alpha blocked execution surfaces changed")
        if self.native_performance_claim:
            raise ValueError("objective alpha bundle must not claim native performance")
        if self.broad_source_parser_claim:
            raise ValueError("objective alpha bundle must not claim broad source parsing")
        if self.vendor_replacement_claim:
            raise ValueError("objective alpha bundle must not claim vendor replacement")
        _validate_entries(self.evidence_entries)

    @property
    def bundle_metadata_digest(self) -> str:
        """Return a stable digest for the bundle contract and evidence links."""

        return _metadata_digest(
            {
                "blocked_claims": self.blocked_claims,
                "blocked_execution_surfaces": self.blocked_execution_surfaces,
                "bundle_id": self.bundle_id,
                "evidence_entries": tuple(
                    _entry_to_dict(entry) for entry in self.evidence_entries
                ),
                "raw_output_policy": self.raw_output_policy,
            }
        )


class ObjectiveAlphaPublicProofBundleError(ValueError):
    """Raised when Objective Alpha public proof evidence is incomplete."""


def build_objective_alpha_public_proof_bundle(
    evidence_entries: tuple[ObjectiveAlphaPublicEvidenceEntry, ...],
) -> ObjectiveAlphaPublicProofBundle:
    """Build the Objective Alpha public proof bundle from digest entries."""

    return ObjectiveAlphaPublicProofBundle(
        bundle_id=OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
        evidence_entries=evidence_entries,
    )


def objective_alpha_public_proof_bundle_to_dict(
    bundle: ObjectiveAlphaPublicProofBundle,
) -> dict[str, object]:
    """Return the stable JSON-compatible mapping for a public proof bundle."""

    assert_objective_alpha_public_proof_bundle(bundle)
    return {
        "artifact_status": bundle.artifact_status,
        "blocked_claims": list(bundle.blocked_claims),
        "blocked_execution_surfaces": list(bundle.blocked_execution_surfaces),
        "broad_source_parser_claim": bundle.broad_source_parser_claim,
        "bundle_contract": bundle.bundle_contract,
        "bundle_id": bundle.bundle_id,
        "bundle_metadata_digest": bundle.bundle_metadata_digest,
        "claim_status": bundle.claim_status,
        "evidence_entries": [_entry_to_dict(entry) for entry in bundle.evidence_entries],
        "native_performance_claim": bundle.native_performance_claim,
        "raw_output_policy": bundle.raw_output_policy,
        "schema_version": OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION,
        "vendor_replacement_claim": bundle.vendor_replacement_claim,
    }


def dump_objective_alpha_public_proof_bundle(
    bundle: ObjectiveAlphaPublicProofBundle,
) -> str:
    """Serialize an Objective Alpha public proof bundle deterministically."""

    text = json.dumps(
        objective_alpha_public_proof_bundle_to_dict(bundle),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_REPORT_BYTES:
        raise ObjectiveAlphaPublicProofBundleError(
            "objective alpha public bundle exceeds size limit"
        )
    return f"{text}\n"


def assert_objective_alpha_public_proof_bundle(
    bundle: ObjectiveAlphaPublicProofBundle,
) -> None:
    """Fail closed when a public proof bundle drifts beyond Objective Alpha."""

    if not isinstance(bundle, ObjectiveAlphaPublicProofBundle):
        raise TypeError("expected ObjectiveAlphaPublicProofBundle")
    if bundle.bundle_id != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID:
        raise ObjectiveAlphaPublicProofBundleError("unexpected objective alpha bundle id")
    _validate_entries(bundle.evidence_entries)
    if bundle.native_performance_claim:
        raise ObjectiveAlphaPublicProofBundleError("native performance claim is blocked")
    if bundle.broad_source_parser_claim:
        raise ObjectiveAlphaPublicProofBundleError("broad source parser claim is blocked")
    if bundle.vendor_replacement_claim:
        raise ObjectiveAlphaPublicProofBundleError("vendor replacement claim is blocked")


def _entry_to_dict(entry: ObjectiveAlphaPublicEvidenceEntry) -> dict[str, str]:
    return {
        "artifact_kind": entry.artifact_kind,
        "entry_point": entry.entry_point,
        "evidence_id": entry.evidence_id,
        "metadata_digest": entry.metadata_digest,
        "raw_output_policy": entry.raw_output_policy,
        "status": entry.status,
    }


def _validate_entries(entries: tuple[ObjectiveAlphaPublicEvidenceEntry, ...]) -> None:
    if len(entries) > OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES:
        raise ObjectiveAlphaPublicProofBundleError("too many objective alpha entries")
    if not entries:
        raise ObjectiveAlphaPublicProofBundleError("objective alpha entries are required")
    evidence_ids = tuple(entry.evidence_id for entry in entries)
    entry_points = tuple(entry.entry_point for entry in entries)
    artifact_kinds = tuple(entry.artifact_kind for entry in entries)
    if evidence_ids != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS:
        raise ObjectiveAlphaPublicProofBundleError("objective alpha evidence ids changed")
    if entry_points != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS:
        raise ObjectiveAlphaPublicProofBundleError("objective alpha entry points changed")
    if artifact_kinds != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS:
        raise ObjectiveAlphaPublicProofBundleError("objective alpha artifact kinds changed")
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ObjectiveAlphaPublicProofBundleError("duplicate objective alpha evidence id")
    if len(set(entry_points)) != len(entry_points):
        raise ObjectiveAlphaPublicProofBundleError("duplicate objective alpha entry point")
    for entry in entries:
        if entry.status != "passed":
            raise ObjectiveAlphaPublicProofBundleError("objective alpha entry did not pass")
        if entry.raw_output_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY:
            raise ObjectiveAlphaPublicProofBundleError("objective alpha entry is not digest-only")


def _validate_bundle_text(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value.encode("utf-8")) > OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_FIELD_BYTES:
        raise ValueError(f"{field_name} exceeds size limit")
    if not _BUNDLE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{field_name} contains unsupported characters")
    lowered = value.lower()
    for fragment in _FORBIDDEN_BUNDLE_TEXT:
        if fragment in lowered:
            raise ValueError(f"{field_name} contains forbidden fragment: {fragment}")


def _validate_digest(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a sha256 digest")


def _metadata_digest(payload: object) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


__all__ = [
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION",
    "ObjectiveAlphaPublicEvidenceEntry",
    "ObjectiveAlphaPublicProofBundle",
    "ObjectiveAlphaPublicProofBundleError",
    "assert_objective_alpha_public_proof_bundle",
    "build_objective_alpha_public_proof_bundle",
    "dump_objective_alpha_public_proof_bundle",
    "objective_alpha_public_proof_bundle_to_dict",
]
