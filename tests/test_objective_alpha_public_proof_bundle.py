from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_public_proof_bundle import build_bundle, build_report
from tuc import (
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION,
    ObjectiveAlphaPublicEvidenceEntry,
    ObjectiveAlphaPublicProofBundle,
    ObjectiveAlphaPublicProofBundleError,
    dump_objective_alpha_public_proof_bundle,
    objective_alpha_public_proof_bundle_to_dict,
)
from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

SCHEMA_PATH = Path("schemas/objective_alpha_public_proof_bundle.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_public_proof_bundle.json")


def test_objective_alpha_public_bundle_binds_expected_evidence() -> None:
    bundle = build_bundle()
    payload = objective_alpha_public_proof_bundle_to_dict(bundle)

    assert payload["schema_version"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION
    assert payload["bundle_id"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID
    assert payload["bundle_contract"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT
    assert payload["artifact_status"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS
    assert payload["claim_status"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS
    assert payload["raw_output_policy"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY
    assert payload["blocked_claims"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS)
    assert payload["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["native_performance_claim"] is False
    assert payload["broad_source_parser_claim"] is False
    assert payload["vendor_replacement_claim"] is False
    assert [entry["evidence_id"] for entry in payload["evidence_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS
    )
    assert [entry["entry_point"] for entry in payload["evidence_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS
    )
    assert [entry["artifact_kind"] for entry in payload["evidence_entries"]] == list(
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS
    )
    evidence_ids = [entry["evidence_id"] for entry in payload["evidence_entries"]]
    assert "proof_of_backend_equivalence" in evidence_ids
    assert "runtime_transfer_trace_index" in evidence_ids
    assert "runtime_transfer_trace_replay_verifier" in evidence_ids
    assert "runtime_backend_equivalence_transfer_binding" in evidence_ids
    assert "runtime_layout_conversion_trace_index" in evidence_ids
    assert "runtime_layout_conversion_trace_replay_verifier" in evidence_ids
    assert "runtime_backend_equivalence_layout_binding" in evidence_ids
    assert "runtime_allocation_reconciliation" in evidence_ids
    assert len(str(payload["bundle_metadata_digest"])) == 64


def test_objective_alpha_public_bundle_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n")

    assert dump_objective_alpha_public_proof_bundle(build_bundle()) == expected + "\n"
    assert build_report() == expected + "\n"


def test_objective_alpha_public_bundle_rejects_unexpected_entry_point() -> None:
    with pytest.raises(ValueError, match="unsupported characters|forbidden"):
        ObjectiveAlphaPublicEvidenceEntry(
            evidence_id="bad_entry",
            entry_point="https://example.invalid/proof",
            artifact_kind="deterministic_proof_output",
            metadata_digest="a" * 64,
        )


def test_objective_alpha_public_bundle_rejects_entry_order_drift() -> None:
    bundle = build_bundle()
    entries = (bundle.evidence_entries[1], bundle.evidence_entries[0], *bundle.evidence_entries[2:])

    with pytest.raises(ObjectiveAlphaPublicProofBundleError, match="evidence ids changed"):
        ObjectiveAlphaPublicProofBundle(
            bundle_id=OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
            evidence_entries=entries,
        )


def test_objective_alpha_public_bundle_rejects_claim_expansion() -> None:
    bundle = build_bundle()

    with pytest.raises(ValueError, match="native performance"):
        ObjectiveAlphaPublicProofBundle(
            bundle_id=bundle.bundle_id,
            evidence_entries=bundle.evidence_entries,
            native_performance_claim=True,
        )

    with pytest.raises(ValueError, match="broad source parsing"):
        ObjectiveAlphaPublicProofBundle(
            bundle_id=bundle.bundle_id,
            evidence_entries=bundle.evidence_entries,
            broad_source_parser_claim=True,
        )

    with pytest.raises(ValueError, match="vendor replacement"):
        ObjectiveAlphaPublicProofBundle(
            bundle_id=bundle.bundle_id,
            evidence_entries=bundle.evidence_entries,
            vendor_replacement_claim=True,
        )


def test_objective_alpha_public_bundle_rejects_bad_digest() -> None:
    with pytest.raises(ValueError, match="sha256 digest"):
        ObjectiveAlphaPublicEvidenceEntry(
            evidence_id="proof_of_execution",
            entry_point="python examples/proof_of_execution.py",
            artifact_kind="deterministic_proof_output",
            metadata_digest="not-a-digest",
        )


def test_objective_alpha_public_bundle_rejects_raw_output_policy_change() -> None:
    bundle = build_bundle()
    entry = bundle.evidence_entries[0]

    with pytest.raises(ValueError, match="digest-only"):
        ObjectiveAlphaPublicEvidenceEntry(
            evidence_id=entry.evidence_id,
            entry_point=entry.entry_point,
            artifact_kind=entry.artifact_kind,
            metadata_digest=entry.metadata_digest,
            raw_output_policy="embedded_output",
        )


def test_objective_alpha_public_bundle_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = objective_alpha_public_proof_bundle_to_dict(build_bundle())

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ARTIFACT_STATUS
    )
    assert schema["properties"]["raw_output_policy"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["broad_source_parser_claim"]["const"] is False
    assert schema["properties"]["vendor_replacement_claim"]["const"] is False
    assert schema["properties"]["evidence_entries"]["minItems"] == 14
    assert schema["properties"]["evidence_entries"]["maxItems"] == 14


def test_objective_alpha_public_bundle_schema_fails_closed() -> None:
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
        "subprocess",
    ):
        assert forbidden not in json.dumps(schema)


def test_objective_alpha_public_bundle_docs_are_linked() -> None:
    schema_path = "schemas/objective_alpha_public_proof_bundle.v0.schema.json"
    golden_path = "tests/golden/proofs/objective_alpha_public_proof_bundle.json"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md"),
        Path("rfcs/0200-objective-alpha-public-proof-bundle.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md" in text or path.name == (
            "OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md"
        )

    evidence_doc = Path("docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md").read_text(
        encoding="utf-8"
    )
    assert schema_path in evidence_doc
    assert golden_path in evidence_doc


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
