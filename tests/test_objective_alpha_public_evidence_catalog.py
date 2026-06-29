from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_evidence_extension_policy import (
    build_report_object as build_extension_policy_report_object,
)
from examples.objective_alpha_public_evidence_catalog import build_report, build_report_object
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
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_STATUS_PASS,
    ObjectiveAlphaPublicEvidenceCatalogEntry,
    ObjectiveAlphaPublicEvidenceCatalogError,
    build_objective_alpha_public_evidence_catalog_report,
    dump_objective_alpha_public_evidence_catalog_report,
    objective_alpha_public_evidence_catalog_report_to_dict,
)
from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

SCHEMA_PATH = Path("schemas/objective_alpha_public_evidence_catalog_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_public_evidence_catalog.json")


def test_objective_alpha_public_evidence_catalog_passes() -> None:
    report = build_report_object()
    payload = objective_alpha_public_evidence_catalog_report_to_dict(report)

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
    assert payload["issues"] == []
    assert len(str(payload["stable_bundle_metadata_digest"])) == 64
    assert len(str(payload["extension_policy_metadata_digest"])) == 64
    assert len(str(payload["catalog_metadata_digest"])) == 64


def test_objective_alpha_public_evidence_catalog_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert dump_objective_alpha_public_evidence_catalog_report(build_report_object()) == expected
    assert build_report() == expected


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
    assert '"catalog_entry_count": 1' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_objective_alpha_public_evidence_catalog_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="ObjectiveAlphaEvidenceExtensionPolicyReport"):
        build_objective_alpha_public_evidence_catalog_report(object())  # type: ignore[arg-type]


def test_objective_alpha_public_evidence_catalog_rejects_failed_policy() -> None:
    policy_report = build_extension_policy_report_object()
    failed_policy = replace(policy_report, issues=("extension_policy_issue",))

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="policy must pass"):
        build_objective_alpha_public_evidence_catalog_report(failed_policy)


def test_objective_alpha_public_evidence_catalog_rejects_entry_drift() -> None:
    report = build_report_object()
    entry = report.catalog_entries[0]
    drifted_entry = ObjectiveAlphaPublicEvidenceCatalogEntry(
        evidence_id="unexpected_extension_policy",
        entry_point=entry.entry_point,
        artifact_kind=entry.artifact_kind,
        metadata_digest=entry.metadata_digest,
        extension_tier=entry.extension_tier,
    )

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="evidence ids changed"):
        replace(report, catalog_entries=(drifted_entry,))


def test_objective_alpha_public_evidence_catalog_rejects_policy_digest_drift() -> None:
    report = build_report_object()

    with pytest.raises(ObjectiveAlphaPublicEvidenceCatalogError, match="policy digest mismatch"):
        replace(report, extension_policy_metadata_digest="a" * 64)


def test_objective_alpha_public_evidence_catalog_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = objective_alpha_public_evidence_catalog_report_to_dict(build_report_object())

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
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS)
    entry_schema = schema["properties"]["catalog_entries"]["prefixItems"][0]
    assert entry_schema["additionalProperties"] is False


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
