from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.first_real_triton_kernel_path import (
    build_report as build_first_real_triton_kernel_path_report,
)
from examples.objective_alpha_evidence_extension_policy import (
    build_report_object as build_extension_policy_report_object,
)
from examples.objective_alpha_public_evidence_catalog import build_report_object
from examples.oci_source_worker_release_provenance_readiness import (
    build_report as build_oci_source_worker_release_provenance_readiness_report,
)
from examples.real_triton_first_slice_evidence_portfolio import (
    build_report as build_real_triton_first_slice_evidence_portfolio_report,
)
from examples.runtime_backend_equivalence_portfolio import (
    build_backend_equivalence_portfolio_report,
)
from examples.source_intent_mixed_runtime_public_proof_bundle import (
    build_report as build_source_intent_mixed_runtime_public_proof_bundle_report,
)
from examples.source_to_intent_research_capability_claim_gate import (
    build_gate_report as build_capability_claim_gate_report,
)
from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
    build_report as build_kernel_ingress_proof_bundle_report,
)
from tuc.objective_alpha import (
    MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ISSUES,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ARTIFACT_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ENTRY_ADMISSION_PATTERN_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_DIGEST_SOURCES,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_RAW_OUTPUT_POLICIES,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS,
    ObjectiveAlphaEvidenceExtensionPolicyReport,
    ObjectiveAlphaPublicEvidenceCatalogEntry,
    ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec,
    ObjectiveAlphaPublicEvidenceCatalogError,
    ObjectiveAlphaPublicEvidenceCatalogReport,
    build_objective_alpha_public_evidence_catalog_report,
    dump_objective_alpha_public_evidence_catalog_report,
    objective_alpha_public_evidence_catalog_report_to_dict,
)
from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeBackendEquivalencePortfolioIssue,
    RuntimeBackendEquivalencePortfolioReport,
)

SCHEMA_PATH = Path("schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_public_evidence_catalog.json")


@lru_cache(maxsize=1)
def _cached_extension_policy_report() -> ObjectiveAlphaEvidenceExtensionPolicyReport:
    return build_extension_policy_report_object()


@lru_cache(maxsize=1)
def _cached_backend_equivalence_portfolio_report() -> RuntimeBackendEquivalencePortfolioReport:
    return build_backend_equivalence_portfolio_report()


@lru_cache(maxsize=1)
def _cached_kernel_ingress_proof_bundle_report() -> str:
    return build_kernel_ingress_proof_bundle_report()


@lru_cache(maxsize=1)
def _cached_source_intent_mixed_runtime_public_proof_bundle_report() -> str:
    return build_source_intent_mixed_runtime_public_proof_bundle_report()


@lru_cache(maxsize=1)
def _cached_capability_claim_gate_report() -> str:
    return build_capability_claim_gate_report()


@lru_cache(maxsize=1)
def _cached_first_real_triton_kernel_path_report() -> str:
    return build_first_real_triton_kernel_path_report()


@lru_cache(maxsize=1)
def _cached_real_triton_first_slice_evidence_portfolio_report() -> str:
    return build_real_triton_first_slice_evidence_portfolio_report()


@lru_cache(maxsize=1)
def _cached_oci_source_ingestion_research_proof_report() -> str:
    return Path(
        "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
    ).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _cached_oci_source_worker_release_provenance_readiness_report() -> str:
    return build_oci_source_worker_release_provenance_readiness_report()


@lru_cache(maxsize=1)
def _cached_catalog_report() -> ObjectiveAlphaPublicEvidenceCatalogReport:
    return build_report_object()


@lru_cache(maxsize=1)
def _cached_catalog_text() -> str:
    return dump_objective_alpha_public_evidence_catalog_report(_cached_catalog_report())


def _fresh_catalog_payload() -> dict[str, object]:
    return objective_alpha_public_evidence_catalog_report_to_dict(_cached_catalog_report())


def test_objective_alpha_public_evidence_catalog_passes() -> None:
    report = _cached_catalog_report()
    payload = _fresh_catalog_payload()

    assert report.catalog_passed is True
    assert report.catalog_status == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS
    assert payload["schema_version"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION
    assert payload["catalog_id"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID
    assert payload["catalog_contract"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT
    assert payload["artifact_status"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ARTIFACT_STATUS
    assert payload["digest_policy"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY
    assert payload["growth_policy"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY
    assert payload["catalog_scope"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE
    assert payload["stable_entrypoint"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID
    assert payload["stable_entry_capacity"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    assert payload["stable_entry_count"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    assert (
        payload["extension_policy_contract"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT
    )
    assert payload["catalog_entry_capacity"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES
    assert payload["catalog_entry_count"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert payload["required_invariants"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS
    )
    assert payload["catalog_required_extension_tiers"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS
    )
    assert payload["catalog_missing_extension_tiers"] == []
    assert (
        payload["catalog_extension_tier_coverage_status"]
        == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS
    )
    assert payload["required_controls"] == list(
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS
    )
    assert payload["blocked_changes"] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES)
    assert payload["blocked_claims"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS)
    assert payload["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert [entry["evidence_id"] for entry in payload["catalog_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert [entry["entry_point"] for entry in payload["catalog_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS
    )
    assert [entry["artifact_kind"] for entry in payload["catalog_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS
    )
    assert [entry["extension_tier"] for entry in payload["catalog_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS
    )
    assert (
        payload["catalog_entries"][0]["metadata_digest"]
        == payload["extension_policy_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][1]["metadata_digest"]
        == payload["runtime_backend_equivalence_portfolio_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][2]["metadata_digest"]
        == payload["source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][3]["metadata_digest"]
        == payload["source_intent_mixed_runtime_public_proof_bundle_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][4]["metadata_digest"]
        == payload["source_to_intent_research_capability_claim_gate_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][5]["metadata_digest"]
        == payload["first_real_triton_kernel_path_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][6]["metadata_digest"]
        == payload["real_triton_first_slice_evidence_portfolio_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][7]["metadata_digest"]
        == payload["oci_source_ingestion_research_proof_metadata_digest"]
    )
    assert (
        payload["catalog_entries"][8]["metadata_digest"]
        == payload["oci_source_worker_release_provenance_readiness_metadata_digest"]
    )
    assert payload["catalog_entries"][1]["evidence_id"] == ("runtime_backend_equivalence_portfolio")
    assert payload["catalog_entries"][1]["extension_tier"] == "runtime_proof"
    assert payload["catalog_entries"][2]["evidence_id"] == (
        "source_to_intent_research_kernel_ingress_proof_bundle"
    )
    assert payload["catalog_entries"][2]["extension_tier"] == "frontend_runtime_proof"
    assert payload["catalog_entries"][3]["evidence_id"] == (
        "source_intent_mixed_runtime_public_proof_bundle"
    )
    assert payload["catalog_entries"][3]["extension_tier"] == "frontend_runtime_proof"
    assert payload["catalog_entries"][4]["evidence_id"] == (
        "source_to_intent_research_capability_claim_gate"
    )
    assert payload["catalog_entries"][4]["extension_tier"] == "claim_boundary"
    assert payload["catalog_entries"][5]["evidence_id"] == "first_real_triton_kernel_path"
    assert payload["catalog_entries"][5]["extension_tier"] == "frontend_runtime_proof"
    assert payload["catalog_entries"][6]["evidence_id"] == (
        "real_triton_first_slice_evidence_portfolio"
    )
    assert payload["catalog_entries"][6]["extension_tier"] == "frontend_runtime_proof"
    assert payload["catalog_entries"][7]["evidence_id"] == (
        "oci_source_ingestion_research_proof"
    )
    assert payload["catalog_entries"][7]["extension_tier"] == "isolation_proof"
    assert payload["catalog_entries"][8]["evidence_id"] == (
        "oci_source_worker_release_provenance_readiness"
    )
    assert payload["catalog_entries"][8]["extension_tier"] == "supply_chain_readiness"
    assert payload["issues"] == []
    assert len(str(payload["stable_bundle_metadata_digest"])) == 64
    assert len(str(payload["extension_policy_metadata_digest"])) == 64
    assert len(str(payload["runtime_backend_equivalence_portfolio_metadata_digest"])) == 64
    assert (
        len(str(payload["source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest"]))
        == 64
    )
    assert (
        len(str(payload["source_intent_mixed_runtime_public_proof_bundle_metadata_digest"]))
        == 64
    )
    assert (
        len(str(payload["source_to_intent_research_capability_claim_gate_metadata_digest"]))
        == 64
    )
    assert len(str(payload["first_real_triton_kernel_path_metadata_digest"])) == 64
    assert len(str(payload["real_triton_first_slice_evidence_portfolio_metadata_digest"])) == 64
    assert len(str(payload["oci_source_ingestion_research_proof_metadata_digest"])) == 64
    assert (
        len(str(payload["oci_source_worker_release_provenance_readiness_metadata_digest"]))
        == 64
    )
    assert len(str(payload["catalog_metadata_digest"])) == 64


def test_objective_alpha_public_evidence_catalog_entry_admission_pattern_drives_contract() -> None:
    specs = OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_SPECS

    assert OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ENTRY_ADMISSION_PATTERN_CONTRACT == (
        "objective_alpha.public_evidence_catalog_entry_admission_pattern.data_only.v0"
    )
    assert tuple(spec.evidence_id for spec in specs) == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert tuple(spec.entry_point for spec in specs) == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS
    )
    assert tuple(spec.artifact_kind for spec in specs) == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS
    )
    assert tuple(spec.extension_tier for spec in specs) == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS
    )
    assert tuple(spec.digest_source for spec in specs) == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_DIGEST_SOURCES
    )
    assert tuple(spec.raw_output_policy for spec in specs) == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_RAW_OUTPUT_POLICIES
    )
    assert OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_DIGEST_SOURCES == (
        "objective_alpha_evidence_extension_policy_report",
        "runtime_backend_equivalence_portfolio_report",
        "source_to_intent_research_kernel_ingress_proof_bundle_report",
        "source_intent_mixed_runtime_public_proof_bundle_report",
        "source_to_intent_research_capability_claim_gate_report",
        "first_real_triton_kernel_path_report",
        "real_triton_first_slice_evidence_portfolio_report",
        "oci_source_ingestion_research_proof_report",
        "oci_source_worker_release_provenance_readiness_report",
    )
    assert len(set(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS)) == len(specs)
    assert len(set(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS)) == len(specs)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("evidence_id", "source_text"),
        ("entry_point", "../unsafe"),
        ("artifact_kind", "raw_tensor_value"),
        ("digest_source", "runtime_handle"),
    ),
)
def test_objective_alpha_public_evidence_catalog_entry_admission_spec_rejects_unsafe_text(
    field: str,
    value: str,
) -> None:
    kwargs = {
        "evidence_id": "safe_evidence",
        "entry_point": "python examples/safe.py",
        "artifact_kind": "schema_versioned_safe_report",
        "extension_tier": "runtime_proof",
        "digest_source": "safe_report",
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(**kwargs)


def test_objective_alpha_public_evidence_catalog_entry_admission_spec_rejects_raw_policy() -> None:
    with pytest.raises(ValueError, match="digest-only"):
        ObjectiveAlphaPublicEvidenceCatalogEntryAdmissionSpec(
            evidence_id="safe_evidence",
            entry_point="python examples/safe.py",
            artifact_kind="schema_versioned_safe_report",
            extension_tier="runtime_proof",
            digest_source="safe_report",
            raw_output_policy="metadata_only",
        )


def test_objective_alpha_public_evidence_catalog_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert _cached_catalog_text() == expected


def test_objective_alpha_public_evidence_catalog_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_public_evidence_catalog.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert "objective_alpha.public_evidence_catalog.data_only.v0" in completed.stdout
    assert '"catalog_passed": true' in completed.stdout
    assert '"catalog_entry_count": 9' in completed.stdout
    assert "runtime_backend_equivalence_portfolio" in completed.stdout
    assert "source_to_intent_research_kernel_ingress_proof_bundle" in completed.stdout
    assert "source_intent_mixed_runtime_public_proof_bundle" in completed.stdout
    assert "source_to_intent_research_capability_claim_gate" in completed.stdout
    assert "first_real_triton_kernel_path" in completed.stdout
    assert "real_triton_first_slice_evidence_portfolio" in completed.stdout
    assert "oci_source_ingestion_research_proof" in completed.stdout
    assert "oci_source_worker_release_provenance_readiness" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_objective_alpha_public_evidence_catalog_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="ObjectiveAlphaEvidenceExtensionPolicyReport"):
        build_objective_alpha_public_evidence_catalog_report(
            object(),  # type: ignore[arg-type]
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )
    with pytest.raises(TypeError, match="RuntimeBackendEquivalencePortfolioReport"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            object(),  # type: ignore[arg-type]
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )
    with pytest.raises(TypeError, match="serialized report string"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            _cached_backend_equivalence_portfolio_report(),
            object(),  # type: ignore[arg-type]
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )
    with pytest.raises(TypeError, match="serialized report string"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            object(),  # type: ignore[arg-type]
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )
    with pytest.raises(TypeError, match="serialized report string"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            object(),  # type: ignore[arg-type]
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )
    with pytest.raises(TypeError, match="serialized report string"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            object(),  # type: ignore[arg-type]
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )
    with pytest.raises(TypeError, match="serialized report string"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            object(),  # type: ignore[arg-type]
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )


def test_objective_alpha_public_evidence_catalog_rejects_extra_blocked_surface_tokens() -> None:
    tampered_report = _cached_source_intent_mixed_runtime_public_proof_bundle_report().replace(
        '  "status": "PASS",',
        '  "status": "PASS",\n  "unexpected_note": "subprocess",',
        1,
    )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="forbidden fragment"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            tampered_report,
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )


def test_objective_alpha_public_evidence_catalog_rejects_failed_policy() -> None:
    policy_report = _cached_extension_policy_report()
    failed_policy = replace(policy_report, issues=("extension_policy_issue",))

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="policy must pass"):
        build_objective_alpha_public_evidence_catalog_report(
            failed_policy,
            _cached_backend_equivalence_portfolio_report(),
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )


def test_objective_alpha_public_evidence_catalog_rejects_failed_portfolio() -> None:
    portfolio_report = _cached_backend_equivalence_portfolio_report()
    failed_slice = replace(portfolio_report.slices[0], passed=False)
    failed_portfolio = RuntimeBackendEquivalencePortfolioReport(
        portfolio_id=portfolio_report.portfolio_id,
        slices=(failed_slice, *portfolio_report.slices[1:]),
        issues=(
            RuntimeBackendEquivalencePortfolioIssue(
                slice_id=failed_slice.slice_id,
                issue_code="equivalence_report_failed",
            ),
        ),
    )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="portfolio must pass"):
        build_objective_alpha_public_evidence_catalog_report(
            _cached_extension_policy_report(),
            failed_portfolio,
            _cached_kernel_ingress_proof_bundle_report(),
            _cached_source_intent_mixed_runtime_public_proof_bundle_report(),
            _cached_capability_claim_gate_report(),
            _cached_first_real_triton_kernel_path_report(),
            _cached_real_triton_first_slice_evidence_portfolio_report(),
            _cached_oci_source_ingestion_research_proof_report(),
            _cached_oci_source_worker_release_provenance_readiness_report(),
        )


def test_objective_alpha_public_evidence_catalog_rejects_entry_drift() -> None:
    report = _cached_catalog_report()
    entry = report.catalog_entries[0]
    drifted_entry = ObjectiveAlphaPublicEvidenceCatalogEntry(
        evidence_id="unexpected_extension_policy",
        entry_point=entry.entry_point,
        artifact_kind=entry.artifact_kind,
        metadata_digest=entry.metadata_digest,
        extension_tier=entry.extension_tier,
    )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="evidence ids changed"):
        replace(report, catalog_entries=(drifted_entry, *report.catalog_entries[1:]))


def test_objective_alpha_public_evidence_catalog_rejects_policy_digest_drift() -> None:
    report = _cached_catalog_report()

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(report, extension_policy_metadata_digest="a" * 64)

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(report, runtime_backend_equivalence_portfolio_metadata_digest="b" * 64)

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(
            report,
            source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest="c" * 64,
        )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(
            report,
            source_intent_mixed_runtime_public_proof_bundle_metadata_digest="d" * 64,
        )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(
            report,
            source_to_intent_research_capability_claim_gate_metadata_digest="e" * 64,
        )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(
            report,
            first_real_triton_kernel_path_metadata_digest="f" * 64,
        )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(
            report,
            oci_source_ingestion_research_proof_metadata_digest="a" * 64,
        )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="metadata digest mismatch"):
        replace(
            report,
            oci_source_worker_release_provenance_readiness_metadata_digest="b" * 64,
        )


def test_objective_alpha_public_evidence_catalog_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = _fresh_catalog_payload()

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION
    )
    assert schema["properties"]["catalog_id"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID
    )
    assert schema["properties"]["catalog_contract"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT
    )
    assert schema["properties"]["catalog_entry_capacity"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES
    )
    assert schema["properties"]["catalog_entry_count"]["const"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ISSUES
    )
    assert [
        item["const"] for item in schema["properties"]["required_invariants"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS)
    assert [
        item["const"]
        for item in schema["properties"]["catalog_required_extension_tiers"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS)
    assert schema["properties"]["catalog_missing_extension_tiers"]["maxItems"] == 0
    assert schema["properties"]["catalog_extension_tier_coverage_status"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS
    )
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS)
    assert (
        schema["properties"][
            "source_to_intent_research_kernel_ingress_proof_bundle_metadata_digest"
        ]["pattern"]
        == "^[a-f0-9]{64}$"
    )
    assert (
        schema["properties"][
            "source_intent_mixed_runtime_public_proof_bundle_metadata_digest"
        ]["pattern"]
        == "^[a-f0-9]{64}$"
    )
    assert (
        schema["properties"][
            "source_to_intent_research_capability_claim_gate_metadata_digest"
        ]["pattern"]
        == "^[a-f0-9]{64}$"
    )
    assert (
        schema["properties"]["first_real_triton_kernel_path_metadata_digest"]["pattern"]
        == "^[a-f0-9]{64}$"
    )
    assert (
        schema["properties"]["real_triton_first_slice_evidence_portfolio_metadata_digest"][
            "pattern"
        ]
        == "^[a-f0-9]{64}$"
    )
    assert (
        schema["properties"]["oci_source_ingestion_research_proof_metadata_digest"][
            "pattern"
        ]
        == "^[a-f0-9]{64}$"
    )
    assert (
        schema["properties"][
            "oci_source_worker_release_provenance_readiness_metadata_digest"
        ]["pattern"]
        == "^[a-f0-9]{64}$"
    )
    catalog_entry_schemas = schema["properties"]["catalog_entries"]["prefixItems"]
    assert len(catalog_entry_schemas) == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert catalog_entry_schemas[0]["additionalProperties"] is False
    assert catalog_entry_schemas[1]["additionalProperties"] is False
    assert catalog_entry_schemas[2]["additionalProperties"] is False
    assert catalog_entry_schemas[3]["additionalProperties"] is False
    assert catalog_entry_schemas[4]["additionalProperties"] is False
    assert catalog_entry_schemas[5]["additionalProperties"] is False
    assert catalog_entry_schemas[6]["additionalProperties"] is False
    assert catalog_entry_schemas[7]["additionalProperties"] is False
    assert catalog_entry_schemas[8]["additionalProperties"] is False
    assert catalog_entry_schemas[1]["properties"]["evidence_id"]["const"] == (
        "runtime_backend_equivalence_portfolio"
    )
    assert catalog_entry_schemas[2]["properties"]["evidence_id"]["const"] == (
        "source_to_intent_research_kernel_ingress_proof_bundle"
    )
    assert catalog_entry_schemas[3]["properties"]["evidence_id"]["const"] == (
        "source_intent_mixed_runtime_public_proof_bundle"
    )
    assert catalog_entry_schemas[4]["properties"]["evidence_id"]["const"] == (
        "source_to_intent_research_capability_claim_gate"
    )
    assert catalog_entry_schemas[5]["properties"]["evidence_id"]["const"] == (
        "first_real_triton_kernel_path"
    )
    assert catalog_entry_schemas[6]["properties"]["evidence_id"]["const"] == (
        "real_triton_first_slice_evidence_portfolio"
    )
    assert catalog_entry_schemas[7]["properties"]["evidence_id"]["const"] == (
        "oci_source_ingestion_research_proof"
    )
    assert catalog_entry_schemas[8]["properties"]["evidence_id"]["const"] == (
        "oci_source_worker_release_provenance_readiness"
    )


def test_objective_alpha_public_evidence_catalog_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "raw_benchmark_output",
        "raw_timing_samples",
        "raw_tensor_value",
        "host_path",
        "device_id",
        "plugin_entrypoint",
        "dynamic_library",
        "generated_code",
        "source_text",
    ):
        assert forbidden not in schema["properties"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_objective_alpha_public_evidence_catalog_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION
    assert golden["catalog_passed"] is True
    assert golden["catalog_status"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS
    assert golden["catalog_entry_capacity"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES
    assert golden["catalog_entry_count"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert golden["catalog_required_extension_tiers"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_EXTENSION_TIERS
    )
    assert golden["catalog_missing_extension_tiers"] == []
    assert golden["catalog_extension_tier_coverage_status"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXTENSION_TIER_COVERAGE_STATUS_PASS
    )
    assert golden["issues"] == []


def test_objective_alpha_public_evidence_catalog_docs_are_linked() -> None:
    schema_path = "schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json"
    example_path = "examples/objective_alpha_public_evidence_catalog.py"
    doc_path = "docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0233-objective-alpha-public-evidence-catalog.md"),
        Path("rfcs/0235-objective-alpha-backend-equivalence-portfolio-catalog-entry.md"),
        Path("rfcs/0236-objective-alpha-catalog-entry-admission-pattern.md"),
        Path("rfcs/0237-objective-alpha-kernel-ingress-proof-bundle-catalog-entry.md"),
        Path("rfcs/0238-objective-alpha-catalog-extension-tier-coverage.md"),
        Path("rfcs/0240-objective-alpha-capability-claim-gate-catalog-entry.md"),
        Path("rfcs/0254-objective-alpha-source-intent-mixed-runtime-public-proof-catalog-entry.md"),
        Path("rfcs/0273-objective-alpha-first-real-triton-kernel-path-catalog-entry.md"),
        Path("rfcs/0275-objective-alpha-real-triton-first-slice-portfolio-catalog-entry.md"),
        Path("rfcs/0290-oci-source-worker-release-provenance.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path.name == "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md"


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)

