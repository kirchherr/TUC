from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.objective_beta_research_claim import (
    OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY,
    OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT,
    OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
    OBJECTIVE_BETA_RESEARCH_CLAIM_OPERATION_FAMILIES,
    OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID,
    OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION,
    OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE,
    OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS,
    ObjectiveBetaResearchClaimError,
    assert_objective_beta_research_claim_report_contract,
    build_objective_beta_research_claim_report,
    build_report,
)

SCHEMA_PATH = Path("schemas/objective_beta_research_claim_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_beta_research_claim.json")
DOC_PATH = Path("docs/OBJECTIVE_BETA_RESEARCH_CLAIM.md")
RFC_PATH = Path("rfcs/0279-objective-beta-research-claim.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_objective_beta_research_claim_report()


@lru_cache(maxsize=1)
def _cached_report_text() -> str:
    return build_report()


def test_objective_beta_research_claim_passes() -> None:
    report = _cached_report()

    assert_objective_beta_research_claim_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION
    assert report["claim_contract"] == OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT
    assert report["claim_id"] == OBJECTIVE_BETA_RESEARCH_CLAIM_ID
    assert report["claim_status"] == OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS
    assert report["claim_scope"] == OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE
    assert report["predecessor_claim_id"] == OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID
    assert report["artifact_policy"] == OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY
    assert report["claim_passed"] is True
    assert report["evidence_count"] == len(OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert report["kernel_ingress_artifact_count"] == 15
    assert report["accepted_kernel_count"] == 5
    assert report["realistic_ingress_case_count"] == 5
    assert report["first_real_path_status"] == "PASS"
    assert report["first_slice_portfolio_status"] == "PASS"
    assert (
        report["admission_readiness_status"]
        == "blocked_missing_maintainer_security_review_approval"
    )
    assert report["research_scope_gate_status"] == "PASS"
    assert report["external_approval_required"] is True
    assert report["admission_ready"] is False
    assert report["source_ingestion_admitted"] is False
    assert report["surface_opened"] is False
    assert report["native_performance_claim"] is False
    assert report["production_compiler_claim"] is False
    assert report["broad_source_parser_claim"] is False
    assert report["vendor_replacement_claim"] is False
    assert report["supported_claims"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS)
    assert report["blocked_claims"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS)
    assert report["required_invariants"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS)
    assert report["operation_families"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_OPERATION_FAMILIES)
    assert report["trusted_runtime_backends"] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS
    )
    assert [item["artifact_id"] for item in report["evidence"]] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert all(item["source_free"] is True for item in report["evidence"])
    assert all(len(item["digest"]) == 64 for item in report["evidence"])
    assert len(str(report["claim_metadata_digest"])) == 64


def test_objective_beta_research_claim_dump_matches_golden() -> None:
    assert _cached_report_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_objective_beta_research_claim_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_beta_research_claim.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "objective_beta.research_claim.digest_snapshot.v0" in completed.stdout
    assert '"claim_passed": true' in completed.stdout
    assert '"kernel_ingress_artifact_count": 15' in completed.stdout
    assert "real_triton_first_slice_maintainer_approval_request" in completed.stdout
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
        ("source_ingestion_admitted", True, "source_ingestion_admitted"),
        ("surface_opened", True, "surface_opened"),
        ("kernel_ingress_artifact_count", 14, "kernel_ingress_artifact_count"),
    ),
)
def test_objective_beta_research_claim_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(ObjectiveBetaResearchClaimError, match=match):
        assert_objective_beta_research_claim_report_contract(report)


def test_objective_beta_research_claim_rejects_evidence_order_drift() -> None:
    report = dict(_cached_report())
    evidence = list(report["evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["evidence"] = evidence

    with pytest.raises(ObjectiveBetaResearchClaimError, match="evidence ids"):
        assert_objective_beta_research_claim_report_contract(report)


def test_objective_beta_research_claim_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    evidence = [dict(item) for item in report["evidence"]]
    evidence[0]["digest"] = "a" * 64
    report["evidence"] = evidence

    with pytest.raises(ObjectiveBetaResearchClaimError, match="metadata digest drift"):
        assert_objective_beta_research_claim_report_contract(report)


def test_objective_beta_research_claim_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(ObjectiveBetaResearchClaimError, match="keys changed"):
        assert_objective_beta_research_claim_report_contract(report)


def test_objective_beta_research_claim_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["claim_contract"]["const"] == OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT
    assert schema["properties"]["evidence_count"]["const"] == len(
        OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert schema["properties"]["kernel_ingress_artifact_count"]["const"] == 15
    assert schema["properties"]["accepted_kernel_count"]["const"] == 5
    assert schema["properties"]["realistic_ingress_case_count"]["const"] == 5
    assert schema["properties"]["supported_claims"]["const"] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS
    )
    assert schema["properties"]["blocked_claims"]["const"] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS
    )


def test_objective_beta_research_claim_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
        "command",
        "device_id",
        "generated_code",
        "host_path",
        "module_source",
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
    for object_schema in _iter_object_schemas(schema):
        assert not (set(object_schema.get("properties", {})) & forbidden_properties)


def test_objective_beta_research_claim_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION
    assert golden["claim_passed"] is True
    assert golden["evidence_count"] == len(OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert golden["source_ingestion_admitted"] is False
    assert golden["native_performance_claim"] is False


def test_objective_beta_research_claim_docs_are_linked() -> None:
    schema_path = "schemas/objective_beta_research_claim_report.v0.schema.json"
    example_path = "examples/objective_beta_research_claim.py"
    golden_path = "tests/golden/proofs/objective_beta_research_claim.json"
    doc_path = "docs/OBJECTIVE_BETA_RESEARCH_CLAIM.md"
    rfc_path = "rfcs/0279-objective-beta-research-claim.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        DOC_PATH,
        RFC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert "OBJECTIVE_BETA_RESEARCH_CLAIM.md" in text or path == DOC_PATH
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
        assert rfc_path in text or path == RFC_PATH or path.name in {"README.md", "ROADMAP.md"}


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))


def _assert_objects_fail_closed(schema: Any) -> None:
    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False


def _iter_object_schemas(schema: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            found.append(schema)
        for value in schema.values():
            found.extend(_iter_object_schemas(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_iter_object_schemas(item))
    return found