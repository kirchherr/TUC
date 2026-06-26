from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_public_proof_bundle_gate import build_report, build_report_object
from tuc.objective_alpha import (
    MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ISSUES,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_DIGEST_POLICY,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_PASS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY,
    build_objective_alpha_public_proof_bundle_gate_report,
    dump_objective_alpha_public_proof_bundle_gate_report,
    objective_alpha_public_proof_bundle_gate_report_to_dict,
)
from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

SCHEMA_PATH = Path("schemas/objective_alpha_public_proof_bundle_gate_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/proofs/objective_alpha_public_proof_bundle_gate_report.json"
)


def test_objective_alpha_public_proof_bundle_gate_passes() -> None:
    report = build_report_object()
    payload = objective_alpha_public_proof_bundle_gate_report_to_dict(report)

    assert report.gate_passed is True
    assert report.gate_status == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_PASS
    assert payload["schema_version"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION
    assert payload["gate_id"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID
    assert payload["gate_contract"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT
    assert payload["artifact_status"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS
    assert payload["bundle_id"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID
    assert payload["bundle_contract"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CONTRACT
    assert payload["bundle_claim_status"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_CLAIM_STATUS
    assert payload["bundle_raw_output_policy"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_RAW_OUTPUT_POLICY
    assert payload["digest_policy"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_DIGEST_POLICY
    assert payload["entry_count"] == len(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS)
    assert payload["entry_digest_count"] == len(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS)
    assert payload["evidence_ids"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS)
    assert payload["entry_points"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS)
    assert payload["artifact_kinds"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS)
    assert payload["blocked_claims"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS)
    assert payload["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["required_invariants"] == list(
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_REQUIRED_INVARIANTS
    )
    assert payload["native_performance_claim"] is False
    assert payload["broad_source_parser_claim"] is False
    assert payload["vendor_replacement_claim"] is False
    assert payload["issues"] == []
    assert len(str(payload["bundle_metadata_digest"])) == 64


def test_objective_alpha_public_proof_bundle_gate_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert dump_objective_alpha_public_proof_bundle_gate_report(build_report_object()) == expected
    assert build_report() == expected


def test_objective_alpha_public_proof_bundle_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_public_proof_bundle_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert "objective_alpha.public_proof_bundle_gate.data_only.v0" in completed.stdout
    assert '"gate_passed": true' in completed.stdout
    assert '"entry_count": 14' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "host_path" not in completed.stdout


def test_objective_alpha_public_proof_bundle_gate_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="ObjectiveAlphaPublicProofBundle"):
        build_objective_alpha_public_proof_bundle_gate_report(object())  # type: ignore[arg-type]


def test_objective_alpha_public_proof_bundle_gate_rejects_entry_drift() -> None:
    report = build_report_object()

    drifted_ids = ("runtime_evidence_gate", *report.evidence_ids[1:])
    with pytest.raises(ValueError, match="evidence ids changed"):
        replace(report, evidence_ids=drifted_ids)


def test_objective_alpha_public_proof_bundle_gate_rejects_digest_count_drift() -> None:
    report = build_report_object()

    with pytest.raises(ValueError, match="digest count mismatch"):
        replace(report, entry_digest_count=report.entry_digest_count - 1)


def test_objective_alpha_public_proof_bundle_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = objective_alpha_public_proof_bundle_gate_report_to_dict(build_report_object())

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_id"]["const"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ID
    assert schema["properties"]["gate_contract"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ARTIFACT_STATUS
    )
    assert schema["properties"]["bundle_id"]["const"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID
    assert schema["properties"]["entry_count"]["const"] == len(
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS
    )
    assert schema["properties"]["entry_digest_count"]["const"] == len(
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_ISSUES
    )
    assert [
        item["const"] for item in schema["properties"]["evidence_ids"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS)
    assert [
        item["const"] for item in schema["properties"]["entry_points"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_POINTS)
    assert [
        item["const"] for item in schema["properties"]["artifact_kinds"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ARTIFACT_KINDS)


def test_objective_alpha_public_proof_bundle_gate_schema_fails_closed() -> None:
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
        assert forbidden not in schema["properties"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_objective_alpha_public_proof_bundle_gate_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_SCHEMA_VERSION
    assert golden["gate_passed"] is True
    assert golden["gate_status"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_STATUS_PASS
    assert golden["entry_count"] == len(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS)
    assert golden["entry_digest_count"] == len(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_EXPECTED_ENTRY_IDS)
    assert golden["issues"] == []


def test_objective_alpha_public_proof_bundle_gate_docs_are_linked() -> None:
    schema_path = "schemas/objective_alpha_public_proof_bundle_gate_report.v0.schema.json"
    example_path = "examples/objective_alpha_public_proof_bundle_gate.py"
    doc_path = "docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0230-objective-alpha-public-proof-bundle-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path.name == "OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md"


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