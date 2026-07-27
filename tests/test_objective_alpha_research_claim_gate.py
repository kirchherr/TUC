from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_research_claim import (
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
)
from examples.objective_alpha_research_claim import (
    build_report as build_research_claim_report,
)
from examples.objective_alpha_research_claim_gate import (
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_CONTRACT,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_ID,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS,
    ObjectiveAlphaResearchClaimGateError,
    assert_objective_alpha_research_claim_gate_report_contract,
    build_gate_report,
)

SCHEMA_PATH = Path("schemas/objective_alpha_research_claim_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_research_claim_gate.json")
DOC_PATH = Path("docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md")


@lru_cache(maxsize=1)
def _cached_gate_text() -> str:
    return build_gate_report()


@lru_cache(maxsize=1)
def _cached_gate_payload() -> dict[str, object]:
    return json.loads(_cached_gate_text())


def test_objective_alpha_research_claim_gate_passes() -> None:
    report = _cached_gate_payload()

    assert_objective_alpha_research_claim_gate_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION
    assert report["gate_contract"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_CONTRACT
    assert report["gate_id"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_ID
    assert report["gate_status"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS
    assert report["gate_passed"] is True
    assert report["claim_contract"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT
    assert report["claim_id"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID
    assert report["claim_status"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS
    assert report["claim_scope"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE
    assert report["artifact_policy"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY
    assert report["evidence_count"] == len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert report["evidence_ids"] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert report["supported_claims"] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS)
    assert report["blocked_claims"] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS)
    assert report["required_invariants"] == list(
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS
    )
    assert report["public_bundle_entry_count"] == 16
    assert report["catalog_entry_count"] == 6
    assert report["public_evidence_entry_count"] == 22
    assert report["backend_equivalence_passed"] is True
    assert report["reference_correctness_passed"] is True
    assert report["native_performance_claim"] is False
    assert report["broad_source_parser_claim"] is False
    assert report["vendor_replacement_claim"] is False
    assert report["issues"] == []
    assert len(str(report["claim_digest"])) == 64
    assert len(str(report["claim_metadata_digest"])) == 64


def test_objective_alpha_research_claim_gate_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert _cached_gate_text() == expected


def test_objective_alpha_research_claim_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_research_claim_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert "objective_alpha.research_claim_gate.ci.v0" in completed.stdout
    assert '"gate_passed": true' in completed.stdout
    assert '"public_evidence_entry_count": 22' in completed.stdout
    assert "source_intent_mixed_runtime_public_proof_bundle" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("native_performance_claim", True, "native_performance_claim"),
        ("broad_source_parser_claim", True, "broad_source_parser_claim"),
        ("vendor_replacement_claim", True, "vendor_replacement_claim"),
        ("public_bundle_entry_count", 15, "public_bundle_entry_count"),
        ("catalog_entry_count", 4, "catalog_entry_count"),
        ("backend_equivalence_passed", False, "backend_equivalence_passed"),
        ("gate_passed", False, "gate_passed"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_objective_alpha_research_claim_gate_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_gate_payload())
    report[field] = value

    with pytest.raises(ObjectiveAlphaResearchClaimGateError, match=match):
        assert_objective_alpha_research_claim_gate_report_contract(report)


def test_objective_alpha_research_claim_gate_rejects_claim_digest_drift() -> None:
    claim = build_research_claim_report()
    tampered_claim = json.dumps(json.loads(claim), indent=4, sort_keys=True) + "\n"

    with pytest.raises(ObjectiveAlphaResearchClaimGateError, match="digest drift"):
        build_gate_report(claim_text=tampered_claim)


def test_objective_alpha_research_claim_gate_rejects_source_leakage() -> None:
    claim = build_research_claim_report()
    tampered_claim = claim.replace(
        '"claim_scope":',
        '"source_text":',
        1,
    )

    with pytest.raises(ObjectiveAlphaResearchClaimGateError, match="forbidden fragment"):
        build_gate_report(claim_text=tampered_claim)


def test_objective_alpha_research_claim_gate_rejects_evidence_order_drift() -> None:
    report = dict(_cached_gate_payload())
    evidence_ids = list(report["evidence_ids"])
    evidence_ids[0], evidence_ids[1] = evidence_ids[1], evidence_ids[0]
    report["evidence_ids"] = evidence_ids

    with pytest.raises(ObjectiveAlphaResearchClaimGateError, match="evidence_ids"):
        assert_objective_alpha_research_claim_gate_report_contract(report)


def test_objective_alpha_research_claim_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_gate_payload()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_ID
    assert schema["properties"]["gate_status"]["const"] == (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS
    )
    assert schema["properties"]["claim_contract"]["const"] == (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT
    )
    assert schema["properties"]["evidence_count"]["const"] == len(
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert schema["properties"]["public_bundle_entry_count"]["const"] == 16
    assert schema["properties"]["catalog_entry_count"]["const"] == 6
    assert schema["properties"]["public_evidence_entry_count"]["const"] == 22
    assert [
        item["const"] for item in schema["properties"]["evidence_ids"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert [
        item["const"] for item in schema["properties"]["supported_claims"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS)
    assert [
        item["const"] for item in schema["properties"]["blocked_claims"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS)
    assert [
        item["const"] for item in schema["properties"]["required_invariants"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS)


def test_objective_alpha_research_claim_gate_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
        "command",
        "device_id",
        "generated_code",
        "host_path",
        "python_source",
        "raw_benchmark_output",
        "raw_source",
        "raw_tensor_value",
        "raw_timing_samples",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
        "tensor_value",
        "tensor_values",
    }
    assert not (set(schema["properties"]) & forbidden_properties)


def test_objective_alpha_research_claim_gate_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION
    assert golden["gate_passed"] is True
    assert golden["gate_status"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS
    assert golden["evidence_count"] == len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert golden["public_bundle_entry_count"] == 16
    assert golden["catalog_entry_count"] == 6
    assert golden["public_evidence_entry_count"] == 22


def test_objective_alpha_research_claim_gate_docs_are_linked() -> None:
    schema_path = "schemas/objective_alpha_research_claim_gate_report.v0.schema.json"
    example_path = "examples/objective_alpha_research_claim_gate.py"
    golden_path = "tests/golden/proofs/objective_alpha_research_claim_gate.json"
    doc_path = "docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md"
    rfc_path = "rfcs/0256-objective-alpha-research-claim-gate.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert "OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE.md" in text or path == DOC_PATH
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
        assert rfc_path in text or path.name in {"README.md", "ROADMAP.md"}


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

