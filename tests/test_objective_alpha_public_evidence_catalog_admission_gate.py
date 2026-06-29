from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_public_evidence_catalog import (
    build_report_object as build_public_evidence_catalog_report_object,
)
from examples.objective_alpha_public_evidence_catalog_admission_gate import (
    build_report,
    build_report_object,
)
from tuc.objective_alpha import (
    MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ISSUES,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ARTIFACT_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_DIGEST_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_PASS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE,
    ObjectiveAlphaPublicEvidenceCatalogAdmissionGateError,
    build_objective_alpha_public_evidence_catalog_admission_gate_report,
    dump_objective_alpha_public_evidence_catalog_admission_gate_report,
    objective_alpha_public_evidence_catalog_admission_gate_report_to_dict,
)
from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

SCHEMA_PATH = Path(
    "schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/proofs/objective_alpha_public_evidence_catalog_admission_gate.json"
)


def test_objective_alpha_public_evidence_catalog_admission_gate_passes() -> None:
    report = build_report_object()
    payload = objective_alpha_public_evidence_catalog_admission_gate_report_to_dict(report)

    assert report.gate_passed is True
    assert report.gate_status == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_PASS
    assert payload["schema_version"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION
    )
    assert payload["gate_id"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID
    assert payload["gate_contract"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT
    )
    assert payload["artifact_status"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ARTIFACT_STATUS
    )
    assert payload["digest_policy"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_DIGEST_POLICY
    )
    assert payload["catalog_id"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID
    assert payload["catalog_contract"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_CONTRACT
    assert payload["catalog_scope"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_SCOPE
    assert payload["catalog_growth_policy"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_GROWTH_POLICY
    assert payload["catalog_digest_policy"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_DIGEST_POLICY
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
    assert payload["catalog_entry_digest_count"] == payload["catalog_entry_count"]
    assert payload["catalog_evidence_ids"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert payload["catalog_entry_points"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_POINTS
    )
    assert payload["catalog_artifact_kinds"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ARTIFACT_KINDS
    )
    assert payload["catalog_extension_tiers"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_EXTENSION_TIERS
    )
    assert payload["catalog_raw_output_policies"] == [
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY
    ] * len(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS)
    assert payload["catalog_evidence_ids"][1] == "runtime_backend_equivalence_portfolio"
    assert payload["catalog_extension_tiers"][1] == "runtime_proof"
    assert payload["required_invariants"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS
    )
    assert payload["required_controls"] == list(
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS
    )
    assert payload["blocked_changes"] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES)
    assert payload["blocked_claims"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS)
    assert payload["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["issues"] == []
    assert len(str(payload["catalog_metadata_digest"])) == 64
    assert len(str(payload["extension_policy_metadata_digest"])) == 64
    assert len(str(payload["runtime_backend_equivalence_portfolio_metadata_digest"])) == 64


def test_objective_alpha_public_evidence_catalog_admission_gate_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert (
        dump_objective_alpha_public_evidence_catalog_admission_gate_report(build_report_object())
        == expected
    )
    assert build_report() == expected


def test_objective_alpha_public_evidence_catalog_admission_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_public_evidence_catalog_admission_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert "objective_alpha.public_evidence_catalog_admission_gate.data_only.v0" in (
        completed.stdout
    )
    assert '"gate_passed": true' in completed.stdout
    assert '"catalog_entry_count": 2' in completed.stdout
    assert "runtime_backend_equivalence_portfolio" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_objective_alpha_public_evidence_catalog_admission_gate_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="ObjectiveAlphaPublicEvidenceCatalogReport"):
        build_objective_alpha_public_evidence_catalog_admission_gate_report(object())  # type: ignore[arg-type]


def test_objective_alpha_public_evidence_catalog_admission_gate_rejects_failed_catalog() -> None:
    catalog_report = build_public_evidence_catalog_report_object()
    failed_catalog = replace(catalog_report, issues=("catalog_issue",))

    with pytest.raises(
        ObjectiveAlphaPublicEvidenceCatalogAdmissionGateError,
        match="catalog must pass",
    ):
        build_objective_alpha_public_evidence_catalog_admission_gate_report(failed_catalog)


def test_objective_alpha_public_evidence_catalog_admission_gate_rejects_drift() -> None:
    report = build_report_object()

    with pytest.raises(ValueError, match="evidence ids changed"):
        replace(
            report,
            catalog_evidence_ids=(
                "unexpected_entry",
                *report.catalog_evidence_ids[1:],
            ),
        )

    with pytest.raises(ValueError, match="digest count mismatch"):
        replace(report, catalog_entry_digest_count=0)

    with pytest.raises(ValueError, match="growth policy mismatch"):
        replace(report, catalog_growth_policy="freeform_growth")


def test_objective_alpha_public_evidence_catalog_admission_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = objective_alpha_public_evidence_catalog_admission_gate_report_to_dict(
        build_report_object()
    )

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_id"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ID
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_CONTRACT
    )
    assert schema["properties"]["catalog_entry_capacity"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES
    )
    assert schema["properties"]["catalog_entry_count"]["const"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_ISSUES
    )
    assert [
        item["const"] for item in schema["properties"]["required_invariants"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_REQUIRED_INVARIANTS)
    assert [
        item["const"] for item in schema["properties"]["catalog_evidence_ids"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS)


def test_objective_alpha_public_evidence_catalog_admission_gate_schema_fails_closed() -> None:
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


def test_objective_alpha_public_evidence_catalog_admission_gate_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_SCHEMA_VERSION
    )
    assert golden["gate_passed"] is True
    assert (
        golden["gate_status"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE_STATUS_PASS
    )
    assert golden["catalog_entry_capacity"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_MAX_ENTRIES
    assert golden["catalog_entry_count"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert golden["issues"] == []


def test_objective_alpha_public_evidence_catalog_admission_gate_docs_are_linked() -> None:
    schema_path = (
        "schemas/objective_alpha_public_evidence_catalog_admission_gate_report.v0.schema.json"
    )
    example_path = "examples/objective_alpha_public_evidence_catalog_admission_gate.py"
    doc_path = "docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0234-objective-alpha-public-evidence-catalog-admission-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path.name == (
            "OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md"
        )


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
