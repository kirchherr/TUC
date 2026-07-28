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
    OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID,
    OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE,
    OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
)
from examples.objective_beta_research_claim import build_report as build_claim_report
from examples.objective_beta_research_claim_gate import (
    OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_CONTRACT,
    OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID,
    OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION,
    OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS,
    ObjectiveBetaResearchClaimGateError,
    assert_objective_beta_research_claim_gate_report_contract,
    build_gate_report,
)

SCHEMA_PATH = Path("schemas/objective_beta_research_claim_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_beta_research_claim_gate.json")
DOC_PATH = Path("docs/OBJECTIVE_BETA_RESEARCH_CLAIM_GATE.md")
RFC_PATH = Path("rfcs/0280-objective-beta-research-claim-gate.md")


@lru_cache(maxsize=1)
def _cached_gate_text() -> str:
    return build_gate_report()


@lru_cache(maxsize=1)
def _cached_gate_payload() -> dict[str, object]:
    return json.loads(_cached_gate_text())


def test_objective_beta_research_claim_gate_passes() -> None:
    report = _cached_gate_payload()

    assert_objective_beta_research_claim_gate_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION
    assert report["gate_contract"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_CONTRACT
    assert report["gate_id"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID
    assert report["gate_status"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS
    assert report["gate_passed"] is True
    assert report["claim_contract"] == OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT
    assert report["claim_id"] == OBJECTIVE_BETA_RESEARCH_CLAIM_ID
    assert report["claim_status"] == OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS
    assert report["claim_scope"] == OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE
    assert report["predecessor_claim_id"] == OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID
    assert report["artifact_policy"] == OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY
    assert report["evidence_count"] == len(OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert report["evidence_ids"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert report["supported_claims"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS)
    assert report["blocked_claims"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS)
    assert report["required_invariants"] == list(OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS)
    assert report["kernel_ingress_artifact_count"] == 15
    assert report["accepted_kernel_count"] == 5
    assert report["realistic_ingress_case_count"] == 5
    assert report["source_ingestion_admitted"] is False
    assert report["admission_ready"] is False
    assert report["surface_opened"] is False
    assert report["native_performance_claim"] is False
    assert report["production_compiler_claim"] is False
    assert report["vendor_replacement_claim"] is False
    assert report["issues"] == []
    assert len(str(report["claim_digest"])) == 64
    assert len(str(report["claim_metadata_digest"])) == 64


def test_objective_beta_research_claim_gate_dump_matches_golden() -> None:
    assert _cached_gate_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_objective_beta_research_claim_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_beta_research_claim_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "objective_beta.research_claim_gate.ci.v0" in completed.stdout
    assert '"gate_passed": true' in completed.stdout
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
        ("gate_passed", False, "gate_passed"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_objective_beta_research_claim_gate_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_gate_payload())
    report[field] = value

    with pytest.raises(ObjectiveBetaResearchClaimGateError, match=match):
        assert_objective_beta_research_claim_gate_report_contract(report)


def test_objective_beta_research_claim_gate_rejects_claim_digest_drift() -> None:
    claim = build_claim_report()
    tampered_claim = json.dumps(json.loads(claim), indent=4, sort_keys=True) + "\n"

    with pytest.raises(ObjectiveBetaResearchClaimGateError, match="digest drift"):
        build_gate_report(claim_text=tampered_claim)


def test_objective_beta_research_claim_gate_rejects_source_leakage() -> None:
    claim = build_claim_report()
    tampered_claim = claim.replace('"claim_scope":', '"source_text":', 1)

    with pytest.raises(ObjectiveBetaResearchClaimGateError, match="forbidden fragment"):
        build_gate_report(claim_text=tampered_claim)


def test_objective_beta_research_claim_gate_rejects_evidence_order_drift() -> None:
    report = dict(_cached_gate_payload())
    evidence_ids = list(report["evidence_ids"])
    evidence_ids[0], evidence_ids[1] = evidence_ids[1], evidence_ids[0]
    report["evidence_ids"] = evidence_ids

    with pytest.raises(ObjectiveBetaResearchClaimGateError, match="evidence_ids"):
        assert_objective_beta_research_claim_gate_report_contract(report)


def test_objective_beta_research_claim_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_gate_payload()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID
    assert (
        schema["properties"]["gate_status"]["const"]
        == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS
    )
    assert schema["properties"]["claim_contract"]["const"] == OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT
    assert schema["properties"]["evidence_count"]["const"] == len(
        OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert schema["properties"]["evidence_ids"]["const"] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS
    )
    assert schema["properties"]["supported_claims"]["const"] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS
    )
    assert schema["properties"]["blocked_claims"]["const"] == list(
        OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS
    )


def test_objective_beta_research_claim_gate_schema_fails_closed() -> None:
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


def test_objective_beta_research_claim_gate_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION
    assert golden["gate_passed"] is True
    assert golden["gate_status"] == OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS
    assert golden["evidence_count"] == len(OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS)
    assert golden["source_ingestion_admitted"] is False
    assert golden["native_performance_claim"] is False


def test_objective_beta_research_claim_gate_docs_are_linked() -> None:
    schema_path = "schemas/objective_beta_research_claim_gate_report.v0.schema.json"
    example_path = "examples/objective_beta_research_claim_gate.py"
    golden_path = "tests/golden/proofs/objective_beta_research_claim_gate.json"
    doc_path = "docs/OBJECTIVE_BETA_RESEARCH_CLAIM_GATE.md"
    rfc_path = "rfcs/0280-objective-beta-research-claim-gate.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_BETA_RESEARCH_CLAIM.md"),
        DOC_PATH,
        RFC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert "OBJECTIVE_BETA_RESEARCH_CLAIM_GATE.md" in text or path == DOC_PATH
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