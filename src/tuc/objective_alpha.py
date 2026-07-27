"""Digest-only public proof bundle for Objective Alpha."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeBackendEquivalencePortfolioReport,
    assert_runtime_backend_equivalence_portfolio,
    dump_runtime_backend_equivalence_portfolio_report,
)

OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION = "tuc.objective_alpha_public_proof_bundle.v0"
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
    "runtime_transfer_trace_index",
    "runtime_transfer_trace_replay_verifier",
    "runtime_backend_equivalence_transfer_binding",
    "runtime_layout_conversion_trace_index",
    "runtime_layout_conversion_trace_replay_verifier",
    "runtime_backend_equivalence_layout_binding",
    "runtime_allocation_reconciliation",
    "runtime_memory_planning_gate",
    "research_onboarding_evidence",
    "source_to_intent_research_proof_bundle",
    "source_to_intent_research_kernel_ingress_evidence_gate",
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS = (
    "python examples/proof_of_execution.py",
    "python examples/runtime_evidence_matrix.py",
    "python examples/runtime_evidence_gate.py",
    "python examples/proof_of_backend_equivalence.py",
    "python examples/runtime_execution_output_closure.py",
    "python examples/runtime_transfer_trace_index.py",
    "python examples/runtime_transfer_trace_replay_verifier.py",
    "python examples/runtime_backend_equivalence_transfer_binding.py",
    "python examples/runtime_layout_conversion_trace_index.py",
    "python examples/runtime_layout_conversion_trace_replay_verifier.py",
    "python examples/runtime_backend_equivalence_layout_binding.py",
    "python examples/runtime_allocation_reconciliation.py",
    "python examples/runtime_memory_planning_gate.py",
    "python examples/research_onboarding_evidence.py",
    "python examples/source_to_intent_research_proof_bundle.py",
    "python examples/source_to_intent_research_kernel_ingress_evidence_gate.py",
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS = (
    "deterministic_proof_output",
    "schema_versioned_matrix_report",
    "deterministic_gate_output",
    "schema_versioned_backend_equivalence_proof_report",
    "schema_versioned_output_closure_report",
    "schema_versioned_transfer_trace_index_report",
    "schema_versioned_transfer_trace_replay_verifier_report",
    "schema_versioned_backend_equivalence_transfer_binding_report",
    "schema_versioned_layout_conversion_trace_index_report",
    "schema_versioned_layout_conversion_trace_replay_verifier_report",
    "schema_versioned_backend_equivalence_layout_binding_report",
    "schema_versioned_allocation_reconciliation_report",
    "deterministic_memory_planning_gate_output",
    "schema_versioned_onboarding_report",
    "schema_versioned_source_to_intent_research_proof_bundle_report",
    "deterministic_source_to_intent_kernel_ingress_evidence_gate_output",
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
    "runtime_handle",
    "source_text",
    "subprocess",
)

_CATALOG_SERIALIZED_REPORT_DECLARED_TOKEN_EXCEPTIONS = {
    "source intent mixed runtime public proof bundle report": {
        "dynamic_library": ("blocked_execution_surfaces", "dynamic_library_loading"),
        "runtime_handle": ("blocked_claims", "runtime_handle_serialization"),
        "subprocess": ("blocked_execution_surfaces", "subprocess_execution"),
    },
    "first real Triton kernel path report": {
        "runtime_handle": ("blocked_claims", "runtime_handle_residency"),
    },
    "real Triton first slice evidence portfolio report": {
        "runtime_handle": (
            ("blocked_claims", "runtime_handle_residency"),
            ("runtime_handle_residency_claim", False),
        ),
    },
}
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ENTRY_ADMISSION_PATTERN_CONTRACT = (
    "objective_alpha.public_evidence_catalog_entry_admission_pattern.data_only.v0"
)


@dataclass(frozen=True)
class ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec:
    """One source-of-truth admission spec for a public evidence catalog entry."""

    evidence_id: str
    entry_point: str
    artifact_kind: str
    extension_tier: str
    digest_source: str
    raw_output_policy: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY

    def __post_init__(self) -> None:
        _validate_catalog_admission_spec_text(self.evidence_id, "catalog spec evidence_id")
        _validate_catalog_admission_spec_text(self.entry_point, "catalog spec entry_point")
        _validate_catalog_admission_spec_text(self.artifact_kind, "catalog spec artifact_kind")
        _validate_catalog_admission_spec_text(self.extension_tier, "catalog spec extension_tier")
        _validate_catalog_admission_spec_text(self.digest_source, "catalog spec digest_source")
        _validate_catalog_admission_spec_text(
            self.raw_output_policy,
            "catalog spec raw_output_policy",
        )
        if self.raw_output_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY:
            raise ValueError("catalog admission specs must stay digest-only")


def _validate_catalog_admission_spec_text(value: str, field_name: str) -> None:
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


def _catalog_admission_spec_values(
    specs: tuple[ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec, ...],
    field_name: str,
) -> tuple[str, ...]:
    if field_name == "evidence_id":
        return tuple(spec.evidence_id for spec in specs)
    if field_name == "entry_point":
        return tuple(spec.entry_point for spec in specs)
    if field_name == "artifact_kind":
        return tuple(spec.artifact_kind for spec in specs)
    if field_name == "extension_tier":
        return tuple(spec.extension_tier for spec in specs)
    if field_name == "digest_source":
        return tuple(spec.digest_source for spec in specs)
    if field_name == "raw_output_policy":
        return tuple(spec.raw_output_policy for spec in specs)
    raise ValueError(f"unknown catalog admission spec field: {field_name}")


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
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
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
                "evidence_entries": tuple(_entry_to_dict(entry) for entry in self.evidence_entries),
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
        "entry_capacity": OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES,
        "entry_count": len(bundle.evidence_entries),
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


OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION = (
    "tuc.objective_alpha_public_proof_bundle_gate_report.v0"
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT = (
    "objective_alpha.public_proof_bundle_gate.data_only.v0"
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID = "objective_alpha_public_proof_bundle_gate"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS = "review_evidence"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_PASS = "PASS"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_FAIL = "FAIL"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_DIGEST_POLICY = "sha256_hex_only"
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REQUIRED_INVARIANTS = (
    "fixed_evidence_ids",
    "fixed_entry_points",
    "fixed_artifact_kinds",
    "fixed_public_entry_capacity",
    "passed_entries_only",
    "digest_only_raw_output_policy",
    "sha256_metadata_digests",
    "direct_transfer_trace_index_public_entry",
    "direct_layout_conversion_trace_index_public_entry",
    "direct_source_to_intent_research_public_entry",
    "direct_kernel_ingress_evidence_gate_public_entry",
    "blocked_native_performance_claim",
    "blocked_vendor_replacement_claim",
    "blocked_broad_source_parser_claim",
)
MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ISSUES = 32
MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REPORT_BYTES = 64 * 1024


@dataclass(frozen=True)
class ObjectiveAlphaPublicProofBundleGateReport:
    """Data-only gate report for the Objective Alpha public proof bundle."""

    bundle_id: str
    bundle_contract: str
    bundle_claim_status: str
    bundle_raw_output_policy: str
    bundle_metadata_digest: str
    entry_count: int
    entry_capacity: int
    entry_digest_count: int
    evidence_ids: tuple[str, ...]
    entry_points: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    blocked_claims: tuple[str, ...]
    blocked_execution_surfaces: tuple[str, ...]
    native_performance_claim: bool
    broad_source_parser_claim: bool
    vendor_replacement_claim: bool
    issues: tuple[str, ...]
    schema_version: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION
    gate_id: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID
    gate_contract: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT
    artifact_status: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS
    digest_policy: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_DIGEST_POLICY
    required_invariants: tuple[str, ...] = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REQUIRED_INVARIANTS

    def __post_init__(self) -> None:
        _validate_bundle_text(self.gate_id, "objective alpha bundle gate_id")
        _validate_bundle_text(self.gate_contract, "objective alpha bundle gate_contract")
        _validate_bundle_text(self.artifact_status, "objective alpha bundle gate status")
        _validate_bundle_text(self.digest_policy, "objective alpha bundle digest_policy")
        _validate_bundle_text(self.bundle_id, "objective alpha bundle gate bundle_id")
        _validate_bundle_text(
            self.bundle_contract,
            "objective alpha bundle gate bundle_contract",
        )
        _validate_bundle_text(
            self.bundle_claim_status,
            "objective alpha bundle gate claim_status",
        )
        _validate_bundle_text(
            self.bundle_raw_output_policy,
            "objective alpha bundle gate raw_output_policy",
        )
        _validate_digest(self.bundle_metadata_digest, "objective alpha bundle digest")
        if self.schema_version != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION:
            raise ValueError("objective alpha bundle gate schema mismatch")
        if self.gate_id != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID:
            raise ValueError("objective alpha bundle gate id mismatch")
        if self.gate_contract != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT:
            raise ValueError("objective alpha bundle gate contract mismatch")
        if self.artifact_status != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS:
            raise ValueError("objective alpha bundle gate artifact status mismatch")
        if self.digest_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_DIGEST_POLICY:
            raise ValueError("objective alpha bundle gate digest policy mismatch")
        if self.required_invariants != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REQUIRED_INVARIANTS:
            raise ValueError("objective alpha bundle gate invariants changed")
        _validate_gate_tuple(self.evidence_ids, "evidence_id")
        _validate_gate_tuple(self.entry_points, "entry_point")
        _validate_gate_tuple(self.artifact_kinds, "artifact_kind")
        _validate_gate_tuple(self.blocked_claims, "blocked_claim")
        _validate_gate_tuple(self.blocked_execution_surfaces, "blocked_execution_surface")
        _validate_gate_tuple(self.issues, "issue")
        if self.entry_count != len(self.evidence_ids):
            raise ValueError("objective alpha bundle gate entry count mismatch")
        if self.entry_capacity != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES:
            raise ValueError("objective alpha bundle gate entry capacity changed")
        if self.entry_count != self.entry_capacity:
            raise ValueError("objective alpha bundle gate entry capacity mismatch")
        if self.entry_digest_count != self.entry_count:
            raise ValueError("objective alpha bundle gate digest count mismatch")
        if len(self.entry_points) != self.entry_count:
            raise ValueError("objective alpha bundle gate entry point count mismatch")
        if len(self.artifact_kinds) != self.entry_count:
            raise ValueError("objective alpha bundle gate artifact kind count mismatch")
        if self.evidence_ids != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS:
            raise ValueError("objective alpha bundle gate evidence ids changed")
        if self.entry_points != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS:
            raise ValueError("objective alpha bundle gate entry points changed")
        if self.artifact_kinds != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS:
            raise ValueError("objective alpha bundle gate artifact kinds changed")
        if self.blocked_claims != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS:
            raise ValueError("objective alpha bundle gate blocked claims changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("objective alpha bundle gate blocked surfaces changed")
        if len(self.issues) > MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ISSUES:
            raise ValueError("objective alpha bundle gate issue count exceeds limit")

    @property
    def gate_passed(self) -> bool:
        """Return whether all public bundle gate checks passed."""

        return not self.issues

    @property
    def gate_status(self) -> str:
        """Return the stable gate status token."""

        return (
            OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_PASS
            if self.gate_passed
            else OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_FAIL
        )


class ObjectiveAlphaPublicProofBundleGateError(ValueError):
    """Raised when the Objective Alpha public proof bundle gate fails."""


def build_objective_alpha_public_proof_bundle_gate_report(
    bundle: ObjectiveAlphaPublicProofBundle,
) -> ObjectiveAlphaPublicProofBundleGateReport:
    """Return a data-only gate report for a public proof bundle."""

    if not isinstance(bundle, ObjectiveAlphaPublicProofBundle):
        raise TypeError("expected ObjectiveAlphaPublicProofBundle")
    try:
        assert_objective_alpha_public_proof_bundle(bundle)
    except (TypeError, ValueError) as exc:
        raise ObjectiveAlphaPublicProofBundleGateError(
            "objective alpha public proof bundle did not pass validation"
        ) from exc
    entries = bundle.evidence_entries
    return ObjectiveAlphaPublicProofBundleGateReport(
        bundle_id=bundle.bundle_id,
        bundle_contract=bundle.bundle_contract,
        bundle_claim_status=bundle.claim_status,
        bundle_raw_output_policy=bundle.raw_output_policy,
        bundle_metadata_digest=bundle.bundle_metadata_digest,
        entry_count=len(entries),
        entry_capacity=OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES,
        entry_digest_count=sum(
            1 for entry in entries if _DIGEST_RE.fullmatch(entry.metadata_digest)
        ),
        evidence_ids=tuple(entry.evidence_id for entry in entries),
        entry_points=tuple(entry.entry_point for entry in entries),
        artifact_kinds=tuple(entry.artifact_kind for entry in entries),
        blocked_claims=bundle.blocked_claims,
        blocked_execution_surfaces=bundle.blocked_execution_surfaces,
        native_performance_claim=bundle.native_performance_claim,
        broad_source_parser_claim=bundle.broad_source_parser_claim,
        vendor_replacement_claim=bundle.vendor_replacement_claim,
        issues=(),
    )


def objective_alpha_public_proof_bundle_gate_report_to_dict(
    report: ObjectiveAlphaPublicProofBundleGateReport,
) -> dict[str, object]:
    """Return a stable JSON-compatible public proof bundle gate report."""

    if not isinstance(report, ObjectiveAlphaPublicProofBundleGateReport):
        raise TypeError("expected ObjectiveAlphaPublicProofBundleGateReport")
    return {
        "artifact_kinds": list(report.artifact_kinds),
        "artifact_status": report.artifact_status,
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "broad_source_parser_claim": report.broad_source_parser_claim,
        "bundle_claim_status": report.bundle_claim_status,
        "bundle_contract": report.bundle_contract,
        "bundle_id": report.bundle_id,
        "bundle_metadata_digest": report.bundle_metadata_digest,
        "bundle_raw_output_policy": report.bundle_raw_output_policy,
        "digest_policy": report.digest_policy,
        "entry_capacity": report.entry_capacity,
        "entry_count": report.entry_count,
        "entry_digest_count": report.entry_digest_count,
        "entry_points": list(report.entry_points),
        "evidence_ids": list(report.evidence_ids),
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_passed": report.gate_passed,
        "gate_status": report.gate_status,
        "issues": list(report.issues),
        "native_performance_claim": report.native_performance_claim,
        "required_invariants": list(report.required_invariants),
        "schema_version": report.schema_version,
        "vendor_replacement_claim": report.vendor_replacement_claim,
    }


def dump_objective_alpha_public_proof_bundle_gate_report(
    report: ObjectiveAlphaPublicProofBundleGateReport,
) -> str:
    """Serialize an Objective Alpha public proof bundle gate report."""

    text = json.dumps(
        objective_alpha_public_proof_bundle_gate_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REPORT_BYTES:
        raise ObjectiveAlphaPublicProofBundleGateError(
            "objective alpha public proof bundle gate report exceeds size limit"
        )
    return f"{text}\n"


OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION = (
    "tuc.objective_alpha_evidence_extension_policy_report.v0"
)
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT = (
    "objective_alpha.evidence_extension_policy.data_only.v0"
)
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID = "objective_alpha_evidence_extension_policy"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS = "review_policy"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_PASS = "PASS"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_FAIL = "FAIL"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_DIGEST_POLICY = "sha256_hex_only"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_KIND = "digest_only_source_free_review_evidence"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_SURFACE = (
    "separate_public_evidence_catalog_or_successor_objective_required"
)
OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GROWTH_STATUS = "blocked_without_rfc"
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_NEXT_DECISION = (
    "define_extension_catalog_or_successor_objective_before_new_public_entries"
)
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS = (
    "schema_versioned_extension_artifacts",
    "sha256_metadata_digests",
    "source_free_public_reports",
    "digest_only_public_links",
    "no_execution_handles",
    "no_device_access",
    "no_generated_artifact_execution",
    "no_native_performance_claim",
)
OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES = (
    "increase_public_bundle_capacity_without_rfc",
    "replace_public_bundle_entries_without_rfc",
    "add_source_buffers_to_public_artifacts",
    "add_tensor_values_to_public_artifacts",
    "authorize_execution_handles",
    "authorize_device_access",
    "authorize_generated_artifact_execution",
    "claim_native_performance",
)
MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ISSUES = 32
MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_REPORT_BYTES = 32 * 1024


@dataclass(frozen=True)
class ObjectiveAlphaEvidenceExtensionPolicyReport:
    """Data-only policy for growing Objective Alpha evidence after bundle capacity."""

    stable_entrypoint: str
    stable_entry_capacity: int
    stable_entry_count: int
    stable_bundle_metadata_digest: str
    stable_gate_contract: str
    issues: tuple[str, ...]
    schema_version: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION
    policy_id: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID
    policy_contract: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT
    artifact_status: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS
    digest_policy: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_DIGEST_POLICY
    extension_policy: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_KIND
    extension_surface: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_SURFACE
    public_bundle_growth_status: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GROWTH_STATUS
    next_required_decision: str = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_NEXT_DECISION
    required_controls: tuple[str, ...] = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS
    blocked_changes: tuple[str, ...] = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES
    blocked_claims: tuple[str, ...] = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        _validate_bundle_text(self.policy_id, "objective alpha extension policy_id")
        _validate_bundle_text(
            self.policy_contract,
            "objective alpha extension policy_contract",
        )
        _validate_bundle_text(
            self.artifact_status,
            "objective alpha extension artifact_status",
        )
        _validate_bundle_text(self.digest_policy, "objective alpha extension digest_policy")
        _validate_bundle_text(
            self.extension_policy,
            "objective alpha extension policy",
        )
        _validate_bundle_text(
            self.extension_surface,
            "objective alpha extension surface",
        )
        _validate_bundle_text(
            self.public_bundle_growth_status,
            "objective alpha public bundle growth_status",
        )
        _validate_bundle_text(
            self.next_required_decision,
            "objective alpha extension next_required_decision",
        )
        _validate_bundle_text(
            self.stable_entrypoint,
            "objective alpha extension stable_entrypoint",
        )
        _validate_digest(
            self.stable_bundle_metadata_digest,
            "objective alpha extension stable bundle digest",
        )
        _validate_bundle_text(
            self.stable_gate_contract,
            "objective alpha extension stable gate contract",
        )
        if self.schema_version != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION:
            raise ValueError("objective alpha extension policy schema mismatch")
        if self.policy_id != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID:
            raise ValueError("objective alpha extension policy id mismatch")
        if self.policy_contract != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT:
            raise ValueError("objective alpha extension policy contract mismatch")
        if self.artifact_status != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS:
            raise ValueError("objective alpha extension policy artifact status mismatch")
        if self.digest_policy != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_DIGEST_POLICY:
            raise ValueError("objective alpha extension policy digest policy mismatch")
        if self.extension_policy != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_KIND:
            raise ValueError("objective alpha extension policy kind mismatch")
        if self.extension_surface != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_SURFACE:
            raise ValueError("objective alpha extension surface mismatch")
        if self.public_bundle_growth_status != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GROWTH_STATUS:
            raise ValueError("objective alpha public bundle growth status mismatch")
        if self.next_required_decision != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_NEXT_DECISION:
            raise ValueError("objective alpha extension next decision mismatch")
        if self.required_controls != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS:
            raise ValueError("objective alpha extension controls changed")
        if self.blocked_changes != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES:
            raise ValueError("objective alpha extension blocked changes changed")
        if self.blocked_claims != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS:
            raise ValueError("objective alpha extension blocked claims changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("objective alpha extension blocked surfaces changed")
        if self.stable_entrypoint != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID:
            raise ValueError("objective alpha extension stable entrypoint mismatch")
        if self.stable_entry_capacity != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES:
            raise ValueError("objective alpha extension stable capacity changed")
        if self.stable_entry_count != self.stable_entry_capacity:
            raise ValueError("objective alpha extension stable bundle is not full")
        if self.stable_gate_contract != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT:
            raise ValueError("objective alpha extension stable gate contract mismatch")
        _validate_extension_policy_tuple(self.required_controls, "required_control")
        _validate_extension_policy_tuple(self.blocked_changes, "blocked_change")
        _validate_gate_tuple(self.blocked_claims, "blocked_claim")
        _validate_gate_tuple(self.blocked_execution_surfaces, "blocked_execution_surface")
        _validate_extension_policy_tuple(self.issues, "issue")
        if len(self.issues) > MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ISSUES:
            raise ValueError("objective alpha extension policy issue count exceeds limit")

    @property
    def policy_passed(self) -> bool:
        """Return whether the extension policy gate has no issues."""

        return not self.issues

    @property
    def policy_status(self) -> str:
        """Return the stable policy status token."""

        return (
            OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_PASS
            if self.policy_passed
            else OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_FAIL
        )


class ObjectiveAlphaEvidenceExtensionPolicyError(ValueError):
    """Raised when Objective Alpha evidence extension policy validation fails."""


def build_objective_alpha_evidence_extension_policy_report(
    gate_report: ObjectiveAlphaPublicProofBundleGateReport,
) -> ObjectiveAlphaEvidenceExtensionPolicyReport:
    """Build the policy for future Objective Alpha public evidence growth."""

    if not isinstance(gate_report, ObjectiveAlphaPublicProofBundleGateReport):
        raise TypeError("expected ObjectiveAlphaPublicProofBundleGateReport")
    if not gate_report.gate_passed:
        raise ObjectiveAlphaEvidenceExtensionPolicyError(
            "objective alpha public proof bundle gate must pass first"
        )
    return ObjectiveAlphaEvidenceExtensionPolicyReport(
        stable_entrypoint=gate_report.bundle_id,
        stable_entry_capacity=gate_report.entry_capacity,
        stable_entry_count=gate_report.entry_count,
        stable_bundle_metadata_digest=gate_report.bundle_metadata_digest,
        stable_gate_contract=gate_report.gate_contract,
        issues=(),
    )


def objective_alpha_evidence_extension_policy_report_to_dict(
    report: ObjectiveAlphaEvidenceExtensionPolicyReport,
) -> dict[str, object]:
    """Return a stable JSON-compatible evidence extension policy report."""

    if not isinstance(report, ObjectiveAlphaEvidenceExtensionPolicyReport):
        raise TypeError("expected ObjectiveAlphaEvidenceExtensionPolicyReport")
    return {
        "artifact_status": report.artifact_status,
        "blocked_changes": list(report.blocked_changes),
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "digest_policy": report.digest_policy,
        "extension_policy": report.extension_policy,
        "extension_surface": report.extension_surface,
        "issues": list(report.issues),
        "next_required_decision": report.next_required_decision,
        "policy_contract": report.policy_contract,
        "policy_id": report.policy_id,
        "policy_passed": report.policy_passed,
        "policy_status": report.policy_status,
        "public_bundle_growth_status": report.public_bundle_growth_status,
        "required_controls": list(report.required_controls),
        "schema_version": report.schema_version,
        "stable_bundle_metadata_digest": report.stable_bundle_metadata_digest,
        "stable_entry_capacity": report.stable_entry_capacity,
        "stable_entry_count": report.stable_entry_count,
        "stable_entrypoint": report.stable_entrypoint,
        "stable_gate_contract": report.stable_gate_contract,
    }


def dump_objective_alpha_evidence_extension_policy_report(
    report: ObjectiveAlphaEvidenceExtensionPolicyReport,
) -> str:
    """Serialize an Objective Alpha evidence extension policy report."""

    text = json.dumps(
        objective_alpha_evidence_extension_policy_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > (MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_REPORT_BYTES):
        raise ObjectiveAlphaEvidenceExtensionPolicyError(
            "objective alpha evidence extension policy report exceeds size limit"
        )
    return f"{text}\n"


OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION = (
    "tuc.objective_alpha_public_evidence_catalog_report.v0"
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT = (
    "objective_alpha.public_evidence_catalog.data_only.v0"
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID = "objective_alpha_public_evidence_catalog"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ARTIFACT_STATUS = "review_evidence_catalog"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS = "PASS"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_FAIL = "FAIL"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY = "sha256_hex_only"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY = "append_only_rfc_bound"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE = (
    "objective_alpha_extensions_after_public_bundle_capacity"
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES = 32
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS = (
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id=OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID,
        entry_point="python examples/objective_alpha_evidence_extension_policy.py",
        artifact_kind="schema_versioned_extension_policy_report",
        extension_tier="governance",
        digest_source="objective_alpha_evidence_extension_policy_report",
    ),
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id="runtime_backend_equivalence_portfolio",
        entry_point="python examples/runtime_backend_equivalence_portfolio.py",
        artifact_kind="schema_versioned_backend_equivalence_portfolio_report",
        extension_tier="runtime_proof",
        digest_source="runtime_backend_equivalence_portfolio_report",
    ),
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id="source_to_intent_research_kernel_ingress_proof_bundle",
        entry_point="python examples/source_to_intent_research_kernel_ingress_proof_bundle.py",
        artifact_kind="schema_versioned_source_to_intent_kernel_ingress_proof_bundle_report",
        extension_tier="frontend_runtime_proof",
        digest_source="source_to_intent_research_kernel_ingress_proof_bundle_report",
    ),
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id="source_intent_mixed_runtime_public_proof_bundle",
        entry_point="python examples/source_intent_mixed_runtime_public_proof_bundle.py",
        artifact_kind="schema_versioned_source_intent_mixed_runtime_public_proof_bundle_report",
        extension_tier="frontend_runtime_proof",
        digest_source="source_intent_mixed_runtime_public_proof_bundle_report",
    ),
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id="source_to_intent_research_capability_claim_gate",
        entry_point="python examples/source_to_intent_research_capability_claim_gate.py",
        artifact_kind="deterministic_source_to_intent_research_capability_claim_gate_output",
        extension_tier="claim_boundary",
        digest_source="source_to_intent_research_capability_claim_gate_report",
    ),
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id="first_real_triton_kernel_path",
        entry_point="python examples/first_real_triton_kernel_path.py",
        artifact_kind="schema_versioned_first_real_triton_kernel_path_report",
        extension_tier="frontend_runtime_proof",
        digest_source="first_real_triton_kernel_path_report",
    ),
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
        evidence_id="real_triton_first_slice_evidence_portfolio",
        entry_point="python examples/real_triton_first_slice_evidence_portfolio.py",
        artifact_kind="schema_versioned_real_triton_first_slice_evidence_portfolio_report",
        extension_tier="frontend_runtime_proof",
        digest_source="real_triton_first_slice_evidence_portfolio_report",
    ),
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS = _catalog_admission_spec_values(
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
    "evidence_id",
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS = _catalog_admission_spec_values(
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
    "entry_point",
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS = _catalog_admission_spec_values(
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
    "artifact_kind",
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS = _catalog_admission_spec_values(
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
    "extension_tier",
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS = (
    "governance",
    "runtime_proof",
    "frontend_runtime_proof",
    "claim_boundary",
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS = "complete"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_DIGEST_SOURCES = (
    _catalog_admission_spec_values(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
        "digest_source",
    )
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_RAW_OUTPUT_POLICIES = (
    _catalog_admission_spec_values(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
        "raw_output_policy",
    )
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS = (
    "stable_public_bundle_anchor",
    "passing_extension_policy_anchor",
    "fixed_initial_catalog_entries",
    "append_only_rfc_bound_growth",
    "digest_only_catalog_entries",
    "source_free_public_reports",
    "blocked_execution_surfaces_preserved",
    "blocked_claims_preserved",
)
MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ISSUES = 32
MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_INPUT_REPORT_BYTES = 64 * 1024
MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REPORT_BYTES = 64 * 1024


@dataclass(frozen=True)
class ObjectiveAlphaPublicEvidenceCatalogEntry:
    """Digest-only entry in the Objective Alpha public evidence catalog."""

    evidence_id: str
    entry_point: str
    artifact_kind: str
    metadata_digest: str
    extension_tier: str
    status: str = "passed"
    raw_output_policy: str = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY

    def __post_init__(self) -> None:
        _validate_bundle_text(self.evidence_id, "objective alpha catalog evidence_id")
        _validate_bundle_text(self.entry_point, "objective alpha catalog entry_point")
        _validate_bundle_text(self.artifact_kind, "objective alpha catalog artifact_kind")
        _validate_bundle_text(self.extension_tier, "objective alpha catalog extension_tier")
        _validate_bundle_text(self.status, "objective alpha catalog status")
        _validate_bundle_text(
            self.raw_output_policy,
            "objective alpha catalog raw_output_policy",
        )
        _validate_digest(self.metadata_digest, "objective alpha catalog metadata_digest")
        if self.status != "passed":
            raise ValueError("objective alpha catalog entries must be passed")
        if self.raw_output_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY:
            raise ValueError("objective alpha public evidence catalog must be digest-only")


def _catalog_entries_from_admission_specs(
    metadata_digests: tuple[str, ...],
) -> tuple[ObjectiveAlphaPublicEvidenceCatalogEntry, ...]:
    if len(metadata_digests) != len(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS):
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog digest source count mismatch")
    return tuple(
        ObjectiveAlphaPublicEvidenceCatalogEntry(
            evidence_id=spec.evidence_id,
            entry_point=spec.entry_point,
            artifact_kind=spec.artifact_kind,
            metadata_digest=metadata_digest,
            extension_tier=spec.extension_tier,
            raw_output_policy=spec.raw_output_policy,
        )
        for spec, metadata_digest in zip(
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
            metadata_digests,
            strict=True,
        )
    )


@dataclass(frozen=True)
class ObjectiveAlphaPublicEvidenceCatalogReport:
    """Data-only catalog for Objective Alpha evidence beyond the fixed bundle."""

    stable_entrypoint: str
    stable_entry_capacity: int
    stable_entry_count: int
    stable_bundle_metadata_digest: str
    extension_policy_contract: str
    extension_policy_metadata_digest: str
    runtime_backend_equivalence_portfolio_metadata_digest: str
    source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest: str
    source_intent_mixed_runtime_public_proof_bundle_metadata_digest: str
    source_to_intent_research_capability_claim_gate_metadata_digest: str
    first_real_triton_kernel_path_metadata_digest: str
    real_triton_first_slice_evidence_portfolio_metadata_digest: str
    catalog_entries: tuple[ObjectiveAlphaPublicEvidenceCatalogEntry, ...]
    issues: tuple[str, ...]
    schema_version: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION
    catalog_id: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID
    catalog_contract: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT
    artifact_status: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ARTIFACT_STATUS
    digest_policy: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY
    growth_policy: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY
    catalog_scope: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE
    catalog_entry_capacity: int = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES
    required_invariants: tuple[str, ...] = (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS
    )
    required_controls: tuple[str, ...] = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS
    blocked_changes: tuple[str, ...] = OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES
    blocked_claims: tuple[str, ...] = OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        _validate_bundle_text(self.catalog_id, "objective alpha catalog_id")
        _validate_bundle_text(self.catalog_contract, "objective alpha catalog_contract")
        _validate_bundle_text(self.artifact_status, "objective alpha catalog artifact_status")
        _validate_bundle_text(self.digest_policy, "objective alpha catalog digest_policy")
        _validate_bundle_text(self.growth_policy, "objective alpha catalog growth_policy")
        _validate_bundle_text(self.catalog_scope, "objective alpha catalog scope")
        _validate_bundle_text(self.stable_entrypoint, "objective alpha catalog stable_entrypoint")
        _validate_digest(
            self.stable_bundle_metadata_digest,
            "objective alpha catalog stable bundle digest",
        )
        _validate_bundle_text(
            self.extension_policy_contract,
            "objective alpha catalog extension_policy_contract",
        )
        _validate_digest(
            self.extension_policy_metadata_digest,
            "objective alpha catalog extension policy digest",
        )
        _validate_digest(
            self.runtime_backend_equivalence_portfolio_metadata_digest,
            "objective alpha catalog backend equivalence portfolio digest",
        )
        _validate_digest(
            self.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest,
            "objective alpha catalog source to intent kernel ingress proof bundle digest",
        )
        _validate_digest(
            self.source_intent_mixed_runtime_public_proof_bundle_metadata_digest,
            "objective alpha catalog source intent mixed runtime proof bundle digest",
        )
        _validate_digest(
            self.source_to_intent_research_capability_claim_gate_metadata_digest,
            "objective alpha catalog source to intent capability claim gate digest",
        )
        _validate_digest(
            self.first_real_triton_kernel_path_metadata_digest,
            "objective alpha catalog first real Triton kernel path digest",
        )
        _validate_digest(
            self.real_triton_first_slice_evidence_portfolio_metadata_digest,
            "objective alpha catalog real Triton first slice evidence portfolio digest",
        )
        if self.schema_version != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION:
            raise ValueError("objective alpha catalog schema mismatch")
        if self.catalog_id != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID:
            raise ValueError("objective alpha catalog id mismatch")
        if self.catalog_contract != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT:
            raise ValueError("objective alpha catalog contract mismatch")
        if self.artifact_status != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ARTIFACT_STATUS:
            raise ValueError("objective alpha catalog artifact status mismatch")
        if self.digest_policy != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY:
            raise ValueError("objective alpha catalog digest policy mismatch")
        if self.growth_policy != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY:
            raise ValueError("objective alpha catalog growth policy mismatch")
        if self.catalog_scope != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE:
            raise ValueError("objective alpha catalog scope mismatch")
        if self.catalog_entry_capacity != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES:
            raise ValueError("objective alpha catalog entry capacity changed")
        if self.required_invariants != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS:
            raise ValueError("objective alpha catalog invariants changed")
        if self.required_controls != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS:
            raise ValueError("objective alpha catalog controls changed")
        if self.blocked_changes != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES:
            raise ValueError("objective alpha catalog blocked changes changed")
        if self.blocked_claims != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS:
            raise ValueError("objective alpha catalog blocked claims changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("objective alpha catalog blocked surfaces changed")
        if self.stable_entrypoint != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID:
            raise ValueError("objective alpha catalog stable entrypoint mismatch")
        if self.stable_entry_capacity != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES:
            raise ValueError("objective alpha catalog stable capacity changed")
        if self.stable_entry_count != self.stable_entry_capacity:
            raise ValueError("objective alpha catalog stable bundle is not full")
        if self.extension_policy_contract != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT:
            raise ValueError("objective alpha catalog policy contract mismatch")
        _validate_catalog_entries(
            self.catalog_entries,
            (
                self.extension_policy_metadata_digest,
                self.runtime_backend_equivalence_portfolio_metadata_digest,
                self.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest,
                self.source_intent_mixed_runtime_public_proof_bundle_metadata_digest,
                self.source_to_intent_research_capability_claim_gate_metadata_digest,
                self.first_real_triton_kernel_path_metadata_digest,
                self.real_triton_first_slice_evidence_portfolio_metadata_digest,
            ),
        )
        if self.catalog_missing_extension_tiers:
            raise ValueError("objective alpha catalog extension tier coverage incomplete")
        _validate_extension_policy_tuple(self.required_invariants, "required_invariant")
        _validate_extension_policy_tuple(self.required_controls, "required_control")
        _validate_extension_policy_tuple(self.blocked_changes, "blocked_change")
        _validate_gate_tuple(self.blocked_claims, "blocked_claim")
        _validate_gate_tuple(self.blocked_execution_surfaces, "blocked_execution_surface")
        _validate_extension_policy_tuple(self.issues, "issue")
        if len(self.issues) > MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ISSUES:
            raise ValueError("objective alpha catalog issue count exceeds limit")

    @property
    def catalog_entry_count(self) -> int:
        """Return the number of current catalog entries."""

        return len(self.catalog_entries)

    @property
    def catalog_passed(self) -> bool:
        """Return whether the catalog validation has no issues."""

        return not self.issues

    @property
    def catalog_status(self) -> str:
        """Return the stable catalog status token."""

        return (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS
            if self.catalog_passed
            else OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_FAIL
        )

    @property
    def catalog_required_extension_tiers(self) -> tuple[str, ...]:
        """Return the extension-tier roles that must be represented."""

        return OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS

    @property
    def catalog_missing_extension_tiers(self) -> tuple[str, ...]:
        """Return required extension-tier roles not represented by catalog entries."""

        return _missing_catalog_extension_tiers(self.catalog_entries)

    @property
    def catalog_extension_tier_coverage_status(self) -> str:
        """Return the stable extension-tier coverage status token."""

        return OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS

    @property
    def catalog_metadata_digest(self) -> str:
        """Return a stable digest for the catalog contract and evidence links."""

        return _metadata_digest(
            {
                "catalog_entries": tuple(
                    _catalog_entry_to_dict(entry) for entry in self.catalog_entries
                ),
                "catalog_id": self.catalog_id,
                "extension_policy_metadata_digest": self.extension_policy_metadata_digest,
                "growth_policy": self.growth_policy,
                "runtime_backend_equivalence_portfolio_metadata_digest": (
                    self.runtime_backend_equivalence_portfolio_metadata_digest
                ),
                "source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest": (
                    self.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest
                ),
                "source_intent_mixed_runtime_public_proof_bundle_metadata_digest": (
                    self.source_intent_mixed_runtime_public_proof_bundle_metadata_digest
                ),
                "source_to_intent_research_capability_claim_gate_metadata_digest": (
                    self.source_to_intent_research_capability_claim_gate_metadata_digest
                ),
                "first_real_triton_kernel_path_metadata_digest": (
                    self.first_real_triton_kernel_path_metadata_digest
                ),
                "real_triton_first_slice_evidence_portfolio_metadata_digest": (
                    self.real_triton_first_slice_evidence_portfolio_metadata_digest
                ),
                "stable_bundle_metadata_digest": self.stable_bundle_metadata_digest,
            }
        )


class ObjectiveAlphaPublicEvidenceCatalogError(ValueError):
    """Raised when Objective Alpha public evidence catalog validation fails."""


def _catalog_forbidden_fragment_is_declared_token(
    serialized_report: str,
    field_name: str,
    fragment: str,
) -> bool:
    exception_map = _CATALOG_SERIALIZED_REPORT_DECLARED_TOKEN_EXCEPTIONS.get(field_name)
    if not isinstance(exception_map, dict):
        return False
    expected = exception_map.get(fragment)
    if expected is None:
        return False
    rules = _catalog_declared_token_rules(expected)
    if not rules:
        return False
    try:
        payload = json.loads(serialized_report)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    declared_match_count = sum(
        _catalog_declared_token_rule_match_count(payload, fragment, rule) for rule in rules
    )
    return (
        declared_match_count == len(rules)
        and serialized_report.lower().count(fragment) == declared_match_count
    )


def _catalog_declared_token_rules(expected: object) -> tuple[tuple[str, object], ...]:
    if not isinstance(expected, tuple):
        return ()
    if len(expected) == 2 and isinstance(expected[0], str):
        return ((expected[0], expected[1]),)

    rules: list[tuple[str, object]] = []
    for item in expected:
        if not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str):
            return ()
        rules.append((item[0], item[1]))
    return tuple(rules)


def _catalog_declared_token_rule_match_count(
    payload: dict[str, object],
    fragment: str,
    rule: tuple[str, object],
) -> int:
    expected_field, expected_value = rule
    declared_values = payload.get(expected_field)

    if isinstance(expected_value, str):
        if not isinstance(declared_values, list):
            return 0
        if not all(isinstance(value, str) for value in declared_values):
            return 0
        if declared_values.count(expected_value) != 1:
            return 0
        if fragment not in expected_value.lower():
            return 0
        return 1

    if isinstance(expected_value, bool):
        if not isinstance(declared_values, bool) or declared_values is not expected_value:
            return 0
        if fragment not in expected_field.lower():
            return 0
        return 1

    return 0


def _catalog_metadata_digest_from_serialized_report(
    serialized_report: str,
    field_name: str,
) -> str:
    if not isinstance(serialized_report, str):
        raise TypeError(f"{field_name} must be a serialized report string")
    if not serialized_report:
        raise ObjectiveAlphaPublicEvidenceCatalogError(f"{field_name} must not be empty")
    if (
        len(serialized_report.encode("utf-8"))
        > MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_INPUT_REPORT_BYTES
    ):
        raise ObjectiveAlphaPublicEvidenceCatalogError(f"{field_name} exceeds size limit")
    lowered = serialized_report.lower()
    for fragment in _FORBIDDEN_BUNDLE_TEXT:
        if fragment in lowered and not _catalog_forbidden_fragment_is_declared_token(
            serialized_report,
            field_name,
            fragment,
        ):
            raise ObjectiveAlphaPublicEvidenceCatalogError(
                f"{field_name} contains forbidden fragment: {fragment}"
            )
    return sha256(serialized_report.encode("utf-8")).hexdigest()


def build_objective_alpha_public_evidence_catalog_report(
    policy_report: ObjectiveAlphaEvidenceExtensionPolicyReport,
    runtime_backend_equivalence_portfolio_report: RuntimeBackendEquivalencePortfolioReport,
    source_to_intent_research_kernel_ingress_proof_bundle_report: str,
    source_intent_mixed_runtime_public_proof_bundle_report: str,
    source_to_intent_research_capability_claim_gate_report: str,
    first_real_triton_kernel_path_report: str,
    real_triton_first_slice_evidence_portfolio_report: str,
) -> ObjectiveAlphaPublicEvidenceCatalogReport:
    """Build the catalog for evidence beyond the fixed Objective Alpha bundle."""

    if not isinstance(policy_report, ObjectiveAlphaEvidenceExtensionPolicyReport):
        raise TypeError("expected ObjectiveAlphaEvidenceExtensionPolicyReport")
    if not isinstance(
        runtime_backend_equivalence_portfolio_report,
        RuntimeBackendEquivalencePortfolioReport,
    ):
        raise TypeError("expected RuntimeBackendEquivalencePortfolioReport")
    if not policy_report.policy_passed:
        raise ObjectiveAlphaPublicEvidenceCatalogError(
            "objective alpha evidence extension policy must pass first"
        )
    try:
        assert_runtime_backend_equivalence_portfolio(runtime_backend_equivalence_portfolio_report)
    except AssertionError as exc:
        raise ObjectiveAlphaPublicEvidenceCatalogError(
            "runtime backend equivalence portfolio must pass first"
        ) from exc
    policy_output = dump_objective_alpha_evidence_extension_policy_report(policy_report)
    policy_digest = sha256(policy_output.encode("utf-8")).hexdigest()
    portfolio_output = dump_runtime_backend_equivalence_portfolio_report(
        runtime_backend_equivalence_portfolio_report
    )
    portfolio_digest = sha256(portfolio_output.encode("utf-8")).hexdigest()
    kernel_ingress_proof_bundle_digest = _catalog_metadata_digest_from_serialized_report(
        source_to_intent_research_kernel_ingress_proof_bundle_report,
        "source to intent kernel ingress proof bundle report",
    )
    mixed_runtime_public_proof_bundle_digest = _catalog_metadata_digest_from_serialized_report(
        source_intent_mixed_runtime_public_proof_bundle_report,
        "source intent mixed runtime public proof bundle report",
    )
    capability_claim_gate_digest = _catalog_metadata_digest_from_serialized_report(
        source_to_intent_research_capability_claim_gate_report,
        "source to intent capability claim gate report",
    )
    first_real_triton_kernel_path_digest = _catalog_metadata_digest_from_serialized_report(
        first_real_triton_kernel_path_report,
        "first real Triton kernel path report",
    )
    real_triton_first_slice_evidence_portfolio_digest = (
        _catalog_metadata_digest_from_serialized_report(
            real_triton_first_slice_evidence_portfolio_report,
            "real Triton first slice evidence portfolio report",
        )
    )
    return ObjectiveAlphaPublicEvidenceCatalogReport(
        stable_entrypoint=policy_report.stable_entrypoint,
        stable_entry_capacity=policy_report.stable_entry_capacity,
        stable_entry_count=policy_report.stable_entry_count,
        stable_bundle_metadata_digest=policy_report.stable_bundle_metadata_digest,
        extension_policy_contract=policy_report.policy_contract,
        extension_policy_metadata_digest=policy_digest,
        runtime_backend_equivalence_portfolio_metadata_digest=portfolio_digest,
        source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest=(
            kernel_ingress_proof_bundle_digest
        ),
        source_intent_mixed_runtime_public_proof_bundle_metadata_digest=(
            mixed_runtime_public_proof_bundle_digest
        ),
        source_to_intent_research_capability_claim_gate_metadata_digest=(
            capability_claim_gate_digest
        ),
        first_real_triton_kernel_path_metadata_digest=(
            first_real_triton_kernel_path_digest
        ),
        real_triton_first_slice_evidence_portfolio_metadata_digest=(
            real_triton_first_slice_evidence_portfolio_digest
        ),
        catalog_entries=_catalog_entries_from_admission_specs(
            (
                policy_digest,
                portfolio_digest,
                kernel_ingress_proof_bundle_digest,
                mixed_runtime_public_proof_bundle_digest,
                capability_claim_gate_digest,
                first_real_triton_kernel_path_digest,
                real_triton_first_slice_evidence_portfolio_digest,
            )
        ),
        issues=(),
    )


def objective_alpha_public_evidence_catalog_report_to_dict(
    report: ObjectiveAlphaPublicEvidenceCatalogReport,
) -> dict[str, object]:
    """Return a stable JSON-compatible public evidence catalog report."""

    if not isinstance(report, ObjectiveAlphaPublicEvidenceCatalogReport):
        raise TypeError("expected ObjectiveAlphaPublicEvidenceCatalogReport")
    return {
        "artifact_status": report.artifact_status,
        "blocked_changes": list(report.blocked_changes),
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "catalog_contract": report.catalog_contract,
        "catalog_entries": [_catalog_entry_to_dict(entry) for entry in report.catalog_entries],
        "catalog_entry_capacity": report.catalog_entry_capacity,
        "catalog_entry_count": report.catalog_entry_count,
        "catalog_id": report.catalog_id,
        "catalog_metadata_digest": report.catalog_metadata_digest,
        "catalog_passed": report.catalog_passed,
        "catalog_extension_tier_coverage_status": (report.catalog_extension_tier_coverage_status),
        "catalog_missing_extension_tiers": list(report.catalog_missing_extension_tiers),
        "catalog_required_extension_tiers": list(report.catalog_required_extension_tiers),
        "catalog_scope": report.catalog_scope,
        "catalog_status": report.catalog_status,
        "digest_policy": report.digest_policy,
        "extension_policy_contract": report.extension_policy_contract,
        "extension_policy_metadata_digest": report.extension_policy_metadata_digest,
        "growth_policy": report.growth_policy,
        "issues": list(report.issues),
        "required_controls": list(report.required_controls),
        "required_invariants": list(report.required_invariants),
        "runtime_backend_equivalence_portfolio_metadata_digest": (
            report.runtime_backend_equivalence_portfolio_metadata_digest
        ),
        "source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest": (
            report.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest
        ),
        "source_intent_mixed_runtime_public_proof_bundle_metadata_digest": (
            report.source_intent_mixed_runtime_public_proof_bundle_metadata_digest
        ),
        "source_to_intent_research_capability_claim_gate_metadata_digest": (
            report.source_to_intent_research_capability_claim_gate_metadata_digest
        ),
        "first_real_triton_kernel_path_metadata_digest": (
            report.first_real_triton_kernel_path_metadata_digest
        ),
        "real_triton_first_slice_evidence_portfolio_metadata_digest": (
            report.real_triton_first_slice_evidence_portfolio_metadata_digest
        ),
        "schema_version": report.schema_version,
        "stable_bundle_metadata_digest": report.stable_bundle_metadata_digest,
        "stable_entry_capacity": report.stable_entry_capacity,
        "stable_entry_count": report.stable_entry_count,
        "stable_entrypoint": report.stable_entrypoint,
    }


def dump_objective_alpha_public_evidence_catalog_report(
    report: ObjectiveAlphaPublicEvidenceCatalogReport,
) -> str:
    """Serialize an Objective Alpha public evidence catalog report."""

    text = json.dumps(
        objective_alpha_public_evidence_catalog_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REPORT_BYTES:
        raise ObjectiveAlphaPublicEvidenceCatalogError(
            "objective alpha public evidence catalog report exceeds size limit"
        )
    return f"{text}\n"


def _catalog_entry_to_dict(
    entry: ObjectiveAlphaPublicEvidenceCatalogEntry,
) -> dict[str, str]:
    return {
        "artifact_kind": entry.artifact_kind,
        "entry_point": entry.entry_point,
        "evidence_id": entry.evidence_id,
        "extension_tier": entry.extension_tier,
        "metadata_digest": entry.metadata_digest,
        "raw_output_policy": entry.raw_output_policy,
        "status": entry.status,
    }


def _validate_catalog_entries(
    entries: tuple[ObjectiveAlphaPublicEvidenceCatalogEntry, ...],
    expected_metadata_digests: tuple[str, ...],
) -> None:
    if len(entries) > OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES:
        raise ObjectiveAlphaPublicEvidenceCatalogError("too many catalog entries")
    if not entries:
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog entries are required")
    if len(entries) != len(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS):
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog entry spec count mismatch")
    if len(expected_metadata_digests) != len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS
    ):
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog digest source count mismatch")
    evidence_ids = tuple(entry.evidence_id for entry in entries)
    entry_points = tuple(entry.entry_point for entry in entries)
    artifact_kinds = tuple(entry.artifact_kind for entry in entries)
    extension_tiers = tuple(entry.extension_tier for entry in entries)
    metadata_digests = tuple(entry.metadata_digest for entry in entries)
    if evidence_ids != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS:
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog evidence ids changed")
    if entry_points != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS:
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog entry points changed")
    if artifact_kinds != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS:
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog artifact kinds changed")
    if extension_tiers != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS:
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog extension tiers changed")
    if metadata_digests != expected_metadata_digests:
        raise ObjectiveAlphaPublicEvidenceCatalogError("catalog metadata digest mismatch")
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ObjectiveAlphaPublicEvidenceCatalogError("duplicate catalog evidence id")
    if len(set(entry_points)) != len(entry_points):
        raise ObjectiveAlphaPublicEvidenceCatalogError("duplicate catalog entry point")
    for entry in entries:
        if entry.status != "passed":
            raise ObjectiveAlphaPublicEvidenceCatalogError("catalog entry did not pass")
        if entry.raw_output_policy != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY:
            raise ObjectiveAlphaPublicEvidenceCatalogError("catalog entry is not digest-only")


def _missing_catalog_extension_tiers(
    entries: tuple[ObjectiveAlphaPublicEvidenceCatalogEntry, ...],
) -> tuple[str, ...]:
    observed = {entry.extension_tier for entry in entries}
    return tuple(
        extension_tier
        for extension_tier in OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS
        if extension_tier not in observed
    )


OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION = (
    "tuc.objective_alpha_public_evidence_catalog_admission_gate_report.v0"
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT = (
    "objective_alpha.public_evidence_catalog_admission_gate.data_only.v0"
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID = (
    "objective_alpha_public_evidence_catalog_admission_gate"
)
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ARTIFACT_STATUS = "review_gate"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_PASS = "PASS"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_FAIL = "FAIL"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_DIGEST_POLICY = "sha256_hex_only"
OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS = (
    "catalog_report_passed",
    "catalog_metadata_digest_bound",
    "stable_public_bundle_anchor",
    "stable_public_bundle_full",
    "extension_policy_contract_bound",
    "extension_policy_digest_entry_bound",
    "backend_equivalence_portfolio_digest_entry_bound",
    "first_non_governance_runtime_proof_entry_bound",
    "kernel_ingress_proof_bundle_digest_entry_bound",
    "source_intent_mixed_runtime_public_proof_bundle_digest_entry_bound",
    "capability_claim_gate_digest_entry_bound",
    "first_real_triton_kernel_path_digest_entry_bound",
    "real_triton_first_slice_evidence_portfolio_digest_entry_bound",
    "catalog_extension_tier_coverage_complete",
    "fixed_initial_catalog_entries",
    "append_only_rfc_bound_growth_policy",
    "digest_only_catalog_entries",
    "source_free_public_reports",
    "blocked_claims_preserved",
    "blocked_execution_surfaces_preserved",
)
MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ISSUES = 32
MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REPORT_BYTES = 64 * 1024


@dataclass(frozen=True)
class ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport:
    """Data-only admission gate for Objective Alpha public evidence catalog entries."""

    catalog_id: str
    catalog_contract: str
    catalog_scope: str
    catalog_growth_policy: str
    catalog_digest_policy: str
    catalog_metadata_digest: str
    stable_entrypoint: str
    stable_entry_capacity: int
    stable_entry_count: int
    extension_policy_contract: str
    extension_policy_metadata_digest: str
    runtime_backend_equivalence_portfolio_metadata_digest: str
    source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest: str
    source_intent_mixed_runtime_public_proof_bundle_metadata_digest: str
    source_to_intent_research_capability_claim_gate_metadata_digest: str
    first_real_triton_kernel_path_metadata_digest: str
    real_triton_first_slice_evidence_portfolio_metadata_digest: str
    catalog_entry_capacity: int
    catalog_entry_count: int
    catalog_entry_digest_count: int
    catalog_evidence_ids: tuple[str, ...]
    catalog_entry_points: tuple[str, ...]
    catalog_artifact_kinds: tuple[str, ...]
    catalog_extension_tiers: tuple[str, ...]
    catalog_required_extension_tiers: tuple[str, ...]
    catalog_missing_extension_tiers: tuple[str, ...]
    catalog_extension_tier_coverage_status: str
    catalog_raw_output_policies: tuple[str, ...]
    required_controls: tuple[str, ...]
    blocked_changes: tuple[str, ...]
    blocked_claims: tuple[str, ...]
    blocked_execution_surfaces: tuple[str, ...]
    issues: tuple[str, ...]
    schema_version: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION
    gate_id: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID
    gate_contract: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT
    artifact_status: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ARTIFACT_STATUS
    digest_policy: str = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_DIGEST_POLICY
    required_invariants: tuple[str, ...] = (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS
    )

    def __post_init__(self) -> None:
        _validate_bundle_text(self.gate_id, "objective alpha catalog gate_id")
        _validate_bundle_text(self.gate_contract, "objective alpha catalog gate_contract")
        _validate_bundle_text(self.artifact_status, "objective alpha catalog gate status")
        _validate_bundle_text(self.digest_policy, "objective alpha catalog gate digest_policy")
        _validate_bundle_text(self.catalog_id, "objective alpha catalog gate catalog_id")
        _validate_bundle_text(
            self.catalog_contract,
            "objective alpha catalog gate catalog_contract",
        )
        _validate_bundle_text(self.catalog_scope, "objective alpha catalog gate scope")
        _validate_bundle_text(
            self.catalog_growth_policy,
            "objective alpha catalog gate growth_policy",
        )
        _validate_bundle_text(
            self.catalog_digest_policy,
            "objective alpha catalog gate catalog_digest_policy",
        )
        _validate_digest(
            self.catalog_metadata_digest,
            "objective alpha catalog gate catalog digest",
        )
        _validate_bundle_text(
            self.stable_entrypoint,
            "objective alpha catalog gate stable_entrypoint",
        )
        _validate_bundle_text(
            self.extension_policy_contract,
            "objective alpha catalog gate extension_policy_contract",
        )
        _validate_digest(
            self.extension_policy_metadata_digest,
            "objective alpha catalog gate extension policy digest",
        )
        _validate_digest(
            self.runtime_backend_equivalence_portfolio_metadata_digest,
            "objective alpha catalog gate backend equivalence portfolio digest",
        )
        _validate_digest(
            self.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest,
            "objective alpha catalog gate source to intent kernel ingress proof bundle digest",
        )
        _validate_digest(
            self.source_intent_mixed_runtime_public_proof_bundle_metadata_digest,
            "objective alpha catalog gate source intent mixed runtime proof bundle digest",
        )
        _validate_digest(
            self.source_to_intent_research_capability_claim_gate_metadata_digest,
            "objective alpha catalog gate source to intent capability claim gate digest",
        )
        _validate_digest(
            self.first_real_triton_kernel_path_metadata_digest,
            "objective alpha catalog gate first real Triton kernel path digest",
        )
        _validate_digest(
            self.real_triton_first_slice_evidence_portfolio_metadata_digest,
            "objective alpha catalog gate real Triton first slice evidence portfolio digest",
        )
        if self.schema_version != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION
        ):
            raise ValueError("objective alpha catalog admission gate schema mismatch")
        if self.gate_id != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID:
            raise ValueError("objective alpha catalog admission gate id mismatch")
        if self.gate_contract != (OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT):
            raise ValueError("objective alpha catalog admission gate contract mismatch")
        if self.artifact_status != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ARTIFACT_STATUS
        ):
            raise ValueError("objective alpha catalog admission gate artifact status mismatch")
        if self.digest_policy != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_DIGEST_POLICY
        ):
            raise ValueError("objective alpha catalog admission gate digest policy mismatch")
        if self.required_invariants != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS
        ):
            raise ValueError("objective alpha catalog admission gate invariants changed")
        if self.catalog_id != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID:
            raise ValueError("objective alpha catalog admission gate catalog id mismatch")
        if self.catalog_contract != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT:
            raise ValueError("objective alpha catalog admission gate catalog contract mismatch")
        if self.catalog_scope != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE:
            raise ValueError("objective alpha catalog admission gate catalog scope mismatch")
        if self.catalog_growth_policy != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY:
            raise ValueError("objective alpha catalog admission gate growth policy mismatch")
        if self.catalog_digest_policy != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY:
            raise ValueError(
                "objective alpha catalog admission gate catalog digest policy mismatch"
            )
        if self.stable_entrypoint != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID:
            raise ValueError("objective alpha catalog admission gate stable entrypoint mismatch")
        if self.stable_entry_capacity != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES:
            raise ValueError("objective alpha catalog admission gate stable capacity changed")
        if self.stable_entry_count != self.stable_entry_capacity:
            raise ValueError("objective alpha catalog admission gate stable bundle is not full")
        if self.extension_policy_contract != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT:
            raise ValueError("objective alpha catalog admission gate policy contract mismatch")
        if self.catalog_entry_capacity != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES:
            raise ValueError("objective alpha catalog admission gate catalog capacity changed")
        if self.catalog_entry_count != len(self.catalog_evidence_ids):
            raise ValueError("objective alpha catalog admission gate entry count mismatch")
        if self.catalog_entry_digest_count != self.catalog_entry_count:
            raise ValueError("objective alpha catalog admission gate digest count mismatch")
        if len(self.catalog_entry_points) != self.catalog_entry_count:
            raise ValueError("objective alpha catalog admission gate entry point count mismatch")
        if len(self.catalog_artifact_kinds) != self.catalog_entry_count:
            raise ValueError("objective alpha catalog admission gate artifact kind count mismatch")
        if len(self.catalog_extension_tiers) != self.catalog_entry_count:
            raise ValueError("objective alpha catalog admission gate extension tier count mismatch")
        if len(self.catalog_raw_output_policies) != self.catalog_entry_count:
            raise ValueError("objective alpha catalog admission gate raw policy count mismatch")
        if self.catalog_evidence_ids != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS:
            raise ValueError("objective alpha catalog admission gate evidence ids changed")
        if (
            self.catalog_entry_points
            != OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS
        ):
            raise ValueError("objective alpha catalog admission gate entry points changed")
        if self.catalog_artifact_kinds != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS
        ):
            raise ValueError("objective alpha catalog admission gate artifact kinds changed")
        if self.catalog_extension_tiers != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS
        ):
            raise ValueError("objective alpha catalog admission gate extension tiers changed")
        if self.catalog_required_extension_tiers != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS
        ):
            raise ValueError(
                "objective alpha catalog admission gate required extension tiers changed"
            )
        if self.catalog_missing_extension_tiers:
            raise ValueError(
                "objective alpha catalog admission gate extension tier coverage incomplete"
            )
        if self.catalog_extension_tier_coverage_status != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS
        ):
            raise ValueError(
                "objective alpha catalog admission gate extension tier coverage status mismatch"
            )
        if self.catalog_raw_output_policies != (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_RAW_OUTPUT_POLICIES
        ):
            raise ValueError("objective alpha catalog admission gate raw output policy changed")
        _validate_extension_policy_tuple(self.required_invariants, "required_invariant")
        _validate_extension_policy_tuple(self.required_controls, "required_control")
        _validate_extension_policy_tuple(self.blocked_changes, "blocked_change")
        _validate_gate_tuple(self.blocked_claims, "blocked_claim")
        _validate_gate_tuple(self.blocked_execution_surfaces, "blocked_execution_surface")
        _validate_gate_tuple(self.catalog_evidence_ids, "catalog_evidence_id")
        _validate_gate_tuple(self.catalog_entry_points, "catalog_entry_point")
        _validate_gate_tuple(self.catalog_artifact_kinds, "catalog_artifact_kind")
        _validate_gate_tuple(self.catalog_extension_tiers, "catalog_extension_tier")
        _validate_gate_tuple(
            self.catalog_required_extension_tiers,
            "catalog_required_extension_tier",
        )
        _validate_gate_tuple(
            self.catalog_missing_extension_tiers,
            "catalog_missing_extension_tier",
        )
        _validate_bundle_text(
            self.catalog_extension_tier_coverage_status,
            "objective alpha catalog admission gate extension tier coverage status",
        )
        _validate_gate_tuple(self.catalog_raw_output_policies, "catalog_raw_output_policy")
        _validate_extension_policy_tuple(self.issues, "issue")
        if self.required_controls != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS:
            raise ValueError("objective alpha catalog admission gate controls changed")
        if self.blocked_changes != OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES:
            raise ValueError("objective alpha catalog admission gate blocked changes changed")
        if self.blocked_claims != OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS:
            raise ValueError("objective alpha catalog admission gate blocked claims changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("objective alpha catalog admission gate blocked surfaces changed")
        if len(self.issues) > (MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ISSUES):
            raise ValueError("objective alpha catalog admission gate issue count exceeds limit")

    @property
    def gate_passed(self) -> bool:
        """Return whether all catalog admission checks passed."""

        return not self.issues

    @property
    def gate_status(self) -> str:
        """Return the stable admission gate status token."""

        return (
            OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_PASS
            if self.gate_passed
            else OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_FAIL
        )


class ObjectiveAlphaPublicEvidenceCatalogAdmissionGateError(ValueError):
    """Raised when the Objective Alpha public evidence catalog gate fails."""


def build_objective_alpha_public_evidence_catalog_admission_gate_report(
    catalog_report: ObjectiveAlphaPublicEvidenceCatalogReport,
) -> ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport:
    """Return a data-only admission gate report for a public evidence catalog."""

    if not isinstance(catalog_report, ObjectiveAlphaPublicEvidenceCatalogReport):
        raise TypeError("expected ObjectiveAlphaPublicEvidenceCatalogReport")
    if not catalog_report.catalog_passed:
        raise ObjectiveAlphaPublicEvidenceCatalogAdmissionGateError(
            "objective alpha public evidence catalog must pass first"
        )
    entries = catalog_report.catalog_entries
    return ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport(
        catalog_id=catalog_report.catalog_id,
        catalog_contract=catalog_report.catalog_contract,
        catalog_scope=catalog_report.catalog_scope,
        catalog_growth_policy=catalog_report.growth_policy,
        catalog_digest_policy=catalog_report.digest_policy,
        catalog_metadata_digest=catalog_report.catalog_metadata_digest,
        stable_entrypoint=catalog_report.stable_entrypoint,
        stable_entry_capacity=catalog_report.stable_entry_capacity,
        stable_entry_count=catalog_report.stable_entry_count,
        extension_policy_contract=catalog_report.extension_policy_contract,
        extension_policy_metadata_digest=catalog_report.extension_policy_metadata_digest,
        runtime_backend_equivalence_portfolio_metadata_digest=(
            catalog_report.runtime_backend_equivalence_portfolio_metadata_digest
        ),
        source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest=(
            catalog_report.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest
        ),
        source_intent_mixed_runtime_public_proof_bundle_metadata_digest=(
            catalog_report.source_intent_mixed_runtime_public_proof_bundle_metadata_digest
        ),
        source_to_intent_research_capability_claim_gate_metadata_digest=(
            catalog_report.source_to_intent_research_capability_claim_gate_metadata_digest
        ),
        first_real_triton_kernel_path_metadata_digest=(
            catalog_report.first_real_triton_kernel_path_metadata_digest
        ),
        real_triton_first_slice_evidence_portfolio_metadata_digest=(
            catalog_report.real_triton_first_slice_evidence_portfolio_metadata_digest
        ),
        catalog_entry_capacity=catalog_report.catalog_entry_capacity,
        catalog_entry_count=catalog_report.catalog_entry_count,
        catalog_entry_digest_count=sum(
            1 for entry in entries if _DIGEST_RE.fullmatch(entry.metadata_digest)
        ),
        catalog_evidence_ids=tuple(entry.evidence_id for entry in entries),
        catalog_entry_points=tuple(entry.entry_point for entry in entries),
        catalog_artifact_kinds=tuple(entry.artifact_kind for entry in entries),
        catalog_extension_tiers=tuple(entry.extension_tier for entry in entries),
        catalog_required_extension_tiers=catalog_report.catalog_required_extension_tiers,
        catalog_missing_extension_tiers=catalog_report.catalog_missing_extension_tiers,
        catalog_extension_tier_coverage_status=(
            catalog_report.catalog_extension_tier_coverage_status
        ),
        catalog_raw_output_policies=tuple(entry.raw_output_policy for entry in entries),
        required_controls=catalog_report.required_controls,
        blocked_changes=catalog_report.blocked_changes,
        blocked_claims=catalog_report.blocked_claims,
        blocked_execution_surfaces=catalog_report.blocked_execution_surfaces,
        issues=(),
    )


def objective_alpha_public_evidence_catalog_admission_gate_report_to_dict(
    report: ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport,
) -> dict[str, object]:
    """Return a stable JSON-compatible public evidence catalog gate report."""

    if not isinstance(report, ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport):
        raise TypeError("expected ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport")
    return {
        "artifact_status": report.artifact_status,
        "blocked_changes": list(report.blocked_changes),
        "blocked_claims": list(report.blocked_claims),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "catalog_artifact_kinds": list(report.catalog_artifact_kinds),
        "catalog_contract": report.catalog_contract,
        "catalog_digest_policy": report.catalog_digest_policy,
        "catalog_entry_capacity": report.catalog_entry_capacity,
        "catalog_entry_count": report.catalog_entry_count,
        "catalog_entry_digest_count": report.catalog_entry_digest_count,
        "catalog_entry_points": list(report.catalog_entry_points),
        "catalog_evidence_ids": list(report.catalog_evidence_ids),
        "catalog_extension_tier_coverage_status": (report.catalog_extension_tier_coverage_status),
        "catalog_extension_tiers": list(report.catalog_extension_tiers),
        "catalog_growth_policy": report.catalog_growth_policy,
        "catalog_id": report.catalog_id,
        "catalog_metadata_digest": report.catalog_metadata_digest,
        "catalog_missing_extension_tiers": list(report.catalog_missing_extension_tiers),
        "catalog_raw_output_policies": list(report.catalog_raw_output_policies),
        "catalog_required_extension_tiers": list(report.catalog_required_extension_tiers),
        "catalog_scope": report.catalog_scope,
        "digest_policy": report.digest_policy,
        "extension_policy_contract": report.extension_policy_contract,
        "extension_policy_metadata_digest": report.extension_policy_metadata_digest,
        "gate_contract": report.gate_contract,
        "gate_id": report.gate_id,
        "gate_passed": report.gate_passed,
        "gate_status": report.gate_status,
        "issues": list(report.issues),
        "required_controls": list(report.required_controls),
        "required_invariants": list(report.required_invariants),
        "runtime_backend_equivalence_portfolio_metadata_digest": (
            report.runtime_backend_equivalence_portfolio_metadata_digest
        ),
        "source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest": (
            report.source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest
        ),
        "source_intent_mixed_runtime_public_proof_bundle_metadata_digest": (
            report.source_intent_mixed_runtime_public_proof_bundle_metadata_digest
        ),
        "source_to_intent_research_capability_claim_gate_metadata_digest": (
            report.source_to_intent_research_capability_claim_gate_metadata_digest
        ),
        "first_real_triton_kernel_path_metadata_digest": (
            report.first_real_triton_kernel_path_metadata_digest
        ),
        "real_triton_first_slice_evidence_portfolio_metadata_digest": (
            report.real_triton_first_slice_evidence_portfolio_metadata_digest
        ),
        "schema_version": report.schema_version,
        "stable_entry_capacity": report.stable_entry_capacity,
        "stable_entry_count": report.stable_entry_count,
        "stable_entrypoint": report.stable_entrypoint,
    }


def dump_objective_alpha_public_evidence_catalog_admission_gate_report(
    report: ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport,
) -> str:
    """Serialize an Objective Alpha public evidence catalog admission gate report."""

    text = json.dumps(
        objective_alpha_public_evidence_catalog_admission_gate_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > (
        MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REPORT_BYTES
    ):
        raise ObjectiveAlphaPublicEvidenceCatalogAdmissionGateError(
            "objective alpha public evidence catalog admission gate report exceeds size limit"
        )
    return f"{text}\n"


def _validate_extension_policy_tuple(values: tuple[str, ...], field_name: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"objective alpha extension {field_name} values must be tuple")
    for value in values:
        _validate_gate_blocked_name(value, f"objective alpha extension {field_name}")


def _validate_gate_tuple(values: tuple[str, ...], field_name: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"objective alpha bundle gate {field_name} values must be tuple")
    for value in values:
        if field_name in {"blocked_claim", "blocked_execution_surface"}:
            _validate_gate_blocked_name(
                value,
                f"objective alpha bundle gate {field_name}",
            )
        else:
            _validate_bundle_text(value, f"objective alpha bundle gate {field_name}")


def _validate_gate_blocked_name(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    if len(value.encode("utf-8")) > OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_FIELD_BYTES:
        raise ValueError(f"{field_name} exceeds size limit")
    if not _BUNDLE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{field_name} contains unsupported characters")
    if ".." in value or "\\" in value or "://" in value:
        raise ValueError(f"{field_name} contains unsafe path or URL syntax")


__all__ = [
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_DIGEST_POLICY",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REQUIRED_INVARIANTS",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_FAIL",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_PASS",
    "MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ISSUES",
    "MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ISSUES",
    "MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ISSUES",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ARTIFACT_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_DIGEST_POLICY",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_FAIL",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_PASS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ARTIFACT_STATUS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ENTRY_ADMISSION_PATTERN_CONTRACT",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_DIGEST_SOURCES",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_RAW_OUTPUT_POLICIES",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_FAIL",
    "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS",
    "MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ISSUES",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_NEXT_DECISION",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_DIGEST_POLICY",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_KIND",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_FAIL",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_PASS",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS",
    "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_SURFACE",
    "OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GROWTH_STATUS",
    "ObjectiveAlphaEvidenceExtensionPolicyError",
    "ObjectiveAlphaEvidenceExtensionPolicyReport",
    "ObjectiveAlphaPublicEvidenceCatalogAdmissionGateError",
    "ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport",
    "ObjectiveAlphaPublicEvidenceCatalogEntry",
    "ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec",
    "ObjectiveAlphaPublicEvidenceCatalogError",
    "ObjectiveAlphaPublicEvidenceCatalogReport",
    "ObjectiveAlphaPublicEvidenceEntry",
    "ObjectiveAlphaPublicProofBundle",
    "ObjectiveAlphaPublicProofBundleError",
    "ObjectiveAlphaPublicProofBundleGateError",
    "ObjectiveAlphaPublicProofBundleGateReport",
    "assert_objective_alpha_public_proof_bundle",
    "build_objective_alpha_evidence_extension_policy_report",
    "build_objective_alpha_public_evidence_catalog_report",
    "build_objective_alpha_public_evidence_catalog_admission_gate_report",
    "build_objective_alpha_public_proof_bundle",
    "build_objective_alpha_public_proof_bundle_gate_report",
    "dump_objective_alpha_evidence_extension_policy_report",
    "dump_objective_alpha_public_evidence_catalog_report",
    "dump_objective_alpha_public_evidence_catalog_admission_gate_report",
    "dump_objective_alpha_public_proof_bundle",
    "dump_objective_alpha_public_proof_bundle_gate_report",
    "objective_alpha_evidence_extension_policy_report_to_dict",
    "objective_alpha_public_evidence_catalog_report_to_dict",
    "objective_alpha_public_evidence_catalog_admission_gate_report_to_dict",
    "objective_alpha_public_proof_bundle_gate_report_to_dict",
    "objective_alpha_public_proof_bundle_to_dict",
]


