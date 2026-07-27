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
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_OPERATION_FAMILIES,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS,
    ObjectiveAlphaResearchClaimError,
    assert_objective_alpha_research_claim_report_contract,
    build_objective_alpha_research_claim_report,
    build_report,
)

SCHEMA_PATH = Path("schemas/objective_alpha_research_claim_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_research_claim.json")
DOC_PATH = Path("docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_objective_alpha_research_claim_report()


@lru_cache(maxsize=1)
def _cached_report_text() -> str:
    return build_report()


def test_objective_alpha_research_claim_passes() -> None:
    report = _cached_report()

    assert_objective_alpha_research_claim_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION
    assert report["claim_contract"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT
    assert report["claim_id"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID
    assert report["claim_status"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS
    assert report["claim_scope"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE
    assert report["artifact_policy"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY
    assert report["claim_passed"] is True
    assert report["evidence_count"] == len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert report["public_bundle_entry_count"] == 16
    assert report["catalog_entry_count"] == 7
    assert report["public_evidence_entry_count"] == 23
    assert report["backend_equivalence_passed"] is True
    assert report["reference_correctness_passed"] is True
    assert report["native_performance_claim"] is False
    assert report["broad_source_parser_claim"] is False
    assert report["vendor_replacement_claim"] is False
    assert report["supported_claims"] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS)
    assert report["blocked_claims"] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS)
    assert report["required_invariants"] == list(
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS
    )
    assert report["operation_families"] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_OPERATION_FAMILIES)
    assert report["trusted_runtime_backends"] == list(
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS
    )
    assert [item["artifact_id"] for item in report["evidence"]] == list(
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert all(item["status"] == "accepted" for item in report["evidence"])
    assert all(len(item["digest"]) == 64 for item in report["evidence"])
    assert len(str(report["claim_metadata_digest"])) == 64


def test_objective_alpha_research_claim_dump_matches_golden() -> None:
    expected = GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    assert _cached_report_text() == expected


def test_objective_alpha_research_claim_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_research_claim.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    assert "objective_alpha.research_claim.digest_snapshot.v0" in completed.stdout
    assert '"claim_passed": true' in completed.stdout
    assert '"public_evidence_entry_count": 23' in completed.stdout
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
    ),
)
def test_objective_alpha_research_claim_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(ObjectiveAlphaResearchClaimError, match=match):
        assert_objective_alpha_research_claim_report_contract(report)


def test_objective_alpha_research_claim_rejects_evidence_order_drift() -> None:
    report = dict(_cached_report())
    evidence = list(report["evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["evidence"] = evidence

    with pytest.raises(ObjectiveAlphaResearchClaimError, match="evidence ids"):
        assert_objective_alpha_research_claim_report_contract(report)


def test_objective_alpha_research_claim_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    evidence = [dict(item) for item in report["evidence"]]
    evidence[0]["digest"] = "a" * 64
    report["evidence"] = evidence

    with pytest.raises(ObjectiveAlphaResearchClaimError, match="metadata digest drift"):
        assert_objective_alpha_research_claim_report_contract(report)


def test_objective_alpha_research_claim_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["claim_contract"]["const"] == (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT
    )
    assert schema["properties"]["evidence_count"]["const"] == len(
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert schema["properties"]["public_bundle_entry_count"]["const"] == 16
    assert schema["properties"]["catalog_entry_count"]["const"] == 7
    assert schema["properties"]["public_evidence_entry_count"]["const"] == 23
    assert [
        item["const"] for item in schema["properties"]["supported_claims"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS)
    assert [
        item["const"] for item in schema["properties"]["blocked_claims"]["prefixItems"]
    ] == list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS)
    evidence_items = schema["properties"]["evidence"]["prefixItems"]
    assert len(evidence_items) == len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)


def test_objective_alpha_research_claim_schema_fails_closed() -> None:
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


def test_objective_alpha_research_claim_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION
    assert golden["claim_passed"] is True
    assert golden["evidence_count"] == len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert golden["public_bundle_entry_count"] == 16
    assert golden["catalog_entry_count"] == 7
    assert golden["public_evidence_entry_count"] == 23


def test_objective_alpha_research_claim_docs_are_linked() -> None:
    schema_path = "schemas/objective_alpha_research_claim_report.v0.schema.json"
    example_path = "examples/objective_alpha_research_claim.py"
    golden_path = "tests/golden/proofs/objective_alpha_research_claim.json"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_ALPHA_RESEARCH_CLAIM.md"),
        Path("rfcs/0255-objective-alpha-research-claim.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "OBJECTIVE_ALPHA_RESEARCH_CLAIM.md" in text or path == DOC_PATH
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}


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
