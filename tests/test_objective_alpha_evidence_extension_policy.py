from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_evidence_extension_policy import build_report, build_report_object
from examples.objective_alpha_public_proof_bundle_gate import (
    build_report_object as build_public_bundle_gate_report_object,
)
from tuc.objective_alpha import (
    MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ISSUES,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_NEXT_DECISION,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_DIGEST_POLICY,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_KIND,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_PASS,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS,
    OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_SURFACE,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GROWTH_STATUS,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID,
    OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES,
    ObjectiveAlphaEvidenceExtensionPolicyError,
    build_objective_alpha_evidence_extension_policy_report,
    dump_objective_alpha_evidence_extension_policy_report,
    objective_alpha_evidence_extension_policy_report_to_dict,
)
from tuc.runtime import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

SCHEMA_PATH = Path("schemas/objective_alpha_evidence_extension_policy_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_evidence_extension_policy.json")


def test_objective_alpha_evidence_extension_policy_passes() -> None:
    report = build_report_object()
    payload = objective_alpha_evidence_extension_policy_report_to_dict(report)

    assert report.policy_passed is True
    assert report.policy_status == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_PASS
    assert payload["schema_version"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION
    assert payload["policy_id"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID
    assert payload["policy_contract"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT
    assert payload["artifact_status"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS
    assert payload["digest_policy"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_DIGEST_POLICY
    assert payload["extension_policy"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_KIND
    assert payload["extension_surface"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_SURFACE
    assert payload["public_bundle_growth_status"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GROWTH_STATUS
    assert payload["next_required_decision"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_NEXT_DECISION
    assert payload["stable_entrypoint"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_ID
    assert payload["stable_entry_capacity"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    assert payload["stable_entry_count"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    assert payload["stable_gate_contract"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_GATE_CONTRACT
    assert payload["required_controls"] == list(
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS
    )
    assert payload["blocked_changes"] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES)
    assert payload["blocked_claims"] == list(OBJECTIVE_ALPHA_PUBLIC_BUNDLE_BLOCKED_CLAIMS)
    assert payload["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["issues"] == []
    assert len(str(payload["stable_bundle_metadata_digest"])) == 64


def test_objective_alpha_evidence_extension_policy_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert dump_objective_alpha_evidence_extension_policy_report(build_report_object()) == expected
    assert build_report() == expected


def test_objective_alpha_evidence_extension_policy_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_evidence_extension_policy.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert "objective_alpha.evidence_extension_policy.data_only.v0" in completed.stdout
    assert '"policy_passed": true' in completed.stdout
    assert '"stable_entry_count": 16' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_objective_alpha_evidence_extension_policy_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="ObjectiveAlphaPublicProofBundleGateReport"):
        build_objective_alpha_evidence_extension_policy_report(object())  # type: ignore[arg-type]


def test_objective_alpha_evidence_extension_policy_rejects_failed_gate() -> None:
    gate_report = build_public_bundle_gate_report_object()
    failed_gate = replace(gate_report, issues=("public_bundle_issue",))

    with pytest.raises(ObjectiveAlphaEvidenceExtensionPolicyError, match="gate must pass"):
        build_objective_alpha_evidence_extension_policy_report(failed_gate)


def test_objective_alpha_evidence_extension_policy_rejects_capacity_drift() -> None:
    report = build_report_object()

    with pytest.raises(ValueError, match="stable bundle is not full"):
        replace(report, stable_entry_count=report.stable_entry_count - 1)

    with pytest.raises(ValueError, match="stable capacity changed"):
        replace(report, stable_entry_capacity=report.stable_entry_capacity + 1)


def test_objective_alpha_evidence_extension_policy_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = objective_alpha_evidence_extension_policy_report_to_dict(build_report_object())

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION
    )
    assert schema["properties"]["policy_id"]["const"] == (
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ID
    )
    assert schema["properties"]["policy_contract"]["const"] == (
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_CONTRACT
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ARTIFACT_STATUS
    )
    assert schema["properties"]["stable_entry_capacity"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    )
    assert schema["properties"]["stable_entry_count"]["const"] == (
        OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_ISSUES
    )
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_REQUIRED_CONTROLS)
    assert [
        item["const"] for item in schema["properties"]["blocked_changes"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_BLOCKED_CHANGES)


def test_objective_alpha_evidence_extension_policy_schema_fails_closed() -> None:
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


def test_objective_alpha_evidence_extension_policy_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_SCHEMA_VERSION
    assert golden["policy_passed"] is True
    assert golden["policy_status"] == OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY_STATUS_PASS
    assert golden["stable_entry_capacity"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    assert golden["stable_entry_count"] == OBJECTIVE_ALPHA_PUBLIC_BUNDLE_MAX_ENTRIES
    assert golden["issues"] == []


def test_objective_alpha_evidence_extension_policy_docs_are_linked() -> None:
    schema_path = "schemas/objective_alpha_evidence_extension_policy_report.v0.schema.json"
    example_path = "examples/objective_alpha_evidence_extension_policy.py"
    doc_path = "docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_PROOF_BUNDLE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0232-objective-alpha-evidence-extension-policy.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path.name == "OBJECTIVE_ALPHA_EVIDENCE_EXTENSION_POLICY.md"


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
