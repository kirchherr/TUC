from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.research_scope_claim_gate import (
    build_current_research_scope_claim_gate_report_text,
)
from tuc.research_scope_claim_gate import (
    RESEARCH_SCOPE_ADOPTION_STATUS,
    RESEARCH_SCOPE_ARTIFACT_POLICY,
    RESEARCH_SCOPE_BLOCKED_CLAIMS,
    RESEARCH_SCOPE_BOUNDARY,
    RESEARCH_SCOPE_CLAIM_GATE_CONTRACT,
    RESEARCH_SCOPE_CLAIM_GATE_ID,
    RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION,
    RESEARCH_SCOPE_CLAIM_GATE_STATUS,
    RESEARCH_SCOPE_CLAIM_ID,
    RESEARCH_SCOPE_CLAIM_STATEMENT,
    RESEARCH_SCOPE_CLAIM_STATUS,
    RESEARCH_SCOPE_EVIDENCE_POLICY,
    RESEARCH_SCOPE_REQUIRED_EVIDENCE,
    RESEARCH_SCOPE_REQUIRED_INVARIANTS,
    RESEARCH_SCOPE_SUPPORTED_CLAIMS,
    RESEARCH_SCOPE_TIME_HORIZON_CLAIM,
    ResearchScopeClaimGateError,
    ResearchScopeEvidenceBinding,
    assert_research_scope_claim_gate_report_contract,
)

SCHEMA_PATH = Path("schemas/research_scope_claim_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/research_scope_claim_gate.json")
DOC_PATH = Path("docs/RESEARCH_SCOPE_CLAIM_GATE.md")


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_current_research_scope_claim_gate_report_text()


@lru_cache(maxsize=1)
def _cached_payload() -> dict[str, object]:
    return json.loads(_cached_text())


def test_research_scope_claim_gate_passes() -> None:
    payload = _cached_payload()

    assert_research_scope_claim_gate_report_contract(payload)
    assert payload["schema_version"] == RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION
    assert payload["gate_contract"] == RESEARCH_SCOPE_CLAIM_GATE_CONTRACT
    assert payload["gate_id"] == RESEARCH_SCOPE_CLAIM_GATE_ID
    assert payload["gate_status"] == RESEARCH_SCOPE_CLAIM_GATE_STATUS
    assert payload["gate_passed"] is True
    assert payload["claim_id"] == RESEARCH_SCOPE_CLAIM_ID
    assert payload["claim_statement"] == RESEARCH_SCOPE_CLAIM_STATEMENT
    assert payload["claim_status"] == RESEARCH_SCOPE_CLAIM_STATUS
    assert payload["scope_boundary"] == RESEARCH_SCOPE_BOUNDARY
    assert payload["adoption_status"] == RESEARCH_SCOPE_ADOPTION_STATUS
    assert payload["time_horizon_claim"] == RESEARCH_SCOPE_TIME_HORIZON_CLAIM
    assert payload["artifact_policy"] == RESEARCH_SCOPE_ARTIFACT_POLICY
    assert payload["evidence_policy"] == RESEARCH_SCOPE_EVIDENCE_POLICY
    assert payload["supported_claims"] == list(RESEARCH_SCOPE_SUPPORTED_CLAIMS)
    assert payload["blocked_claims"] == list(RESEARCH_SCOPE_BLOCKED_CLAIMS)
    assert payload["required_invariants"] == list(RESEARCH_SCOPE_REQUIRED_INVARIANTS)
    assert payload["evidence_count"] == len(RESEARCH_SCOPE_REQUIRED_EVIDENCE)
    assert payload["research_scope_claim"] is True
    assert payload["production_compiler_claim"] is False
    assert payload["cuda_replacement_claim"] is False
    assert payload["rocm_replacement_claim"] is False
    assert payload["xla_replacement_claim"] is False
    assert payload["tvm_replacement_claim"] is False
    assert payload["iree_replacement_claim"] is False
    assert payload["native_performance_claim"] is False
    assert payload["real_hardware_backend_execution_claim"] is False
    assert payload["arbitrary_source_ingestion_claim"] is False
    assert payload["arbitrary_third_party_backend_execution_claim"] is False
    assert payload["generated_artifact_execution_claim"] is False
    assert payload["external_plugin_execution_claim"] is False
    assert payload["source_ingestion_admitted"] is False
    assert payload["issues"] == []

    evidence = payload["evidence"]
    assert isinstance(evidence, list)
    assert [item["evidence_id"] for item in evidence] == [
        requirement.evidence_id for requirement in RESEARCH_SCOPE_REQUIRED_EVIDENCE
    ]
    assert [item["status"] for item in evidence] == [
        requirement.status for requirement in RESEARCH_SCOPE_REQUIRED_EVIDENCE
    ]


def test_research_scope_claim_gate_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_research_scope_claim_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/research_scope_claim_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"scope_boundary": "research_proof_not_compiler_replacement"' in (
        completed.stdout
    )
    assert '"production_compiler_claim": false' in completed.stdout
    assert '"native_performance_claim": false' in completed.stdout
    assert '"source_ingestion_admitted": false' in completed.stdout
    assert "objective_alpha_research_claim_gate" in completed.stdout
    assert "performance_proof_interpretation" in completed.stdout
    assert "source_ingestion_maintainer_approval_artifact" in completed.stdout
    assert "source_ingestion_admission_gate" in completed.stdout
    assert "source_ingestion_preclaim_evidence_graph_acyclicity_gate" in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_tensor_value":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout
    assert '"host_path":' not in completed.stdout
    assert '"device_id":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("research_scope_claim", False, "research_scope_claim"),
        ("production_compiler_claim", True, "production_compiler_claim"),
        ("cuda_replacement_claim", True, "cuda_replacement_claim"),
        ("rocm_replacement_claim", True, "rocm_replacement_claim"),
        ("xla_replacement_claim", True, "xla_replacement_claim"),
        ("tvm_replacement_claim", True, "tvm_replacement_claim"),
        ("iree_replacement_claim", True, "iree_replacement_claim"),
        ("native_performance_claim", True, "native_performance_claim"),
        (
            "real_hardware_backend_execution_claim",
            True,
            "real_hardware_backend_execution_claim",
        ),
        ("arbitrary_source_ingestion_claim", True, "arbitrary_source_ingestion_claim"),
        ("source_ingestion_admitted", True, "source_ingestion_admitted"),
        ("time_horizon_claim", "two_years", "time_horizon_claim"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_research_scope_claim_gate_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    payload = dict(_cached_payload())
    payload[field] = value

    with pytest.raises(ResearchScopeClaimGateError, match=match):
        assert_research_scope_claim_gate_report_contract(payload)


def test_research_scope_claim_gate_rejects_digest_drift() -> None:
    payload = dict(_cached_payload())
    payload["scope_report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(ResearchScopeClaimGateError, match="digest drift"):
        assert_research_scope_claim_gate_report_contract(payload)


def test_research_scope_claim_gate_rejects_evidence_order_drift() -> None:
    payload = dict(_cached_payload())
    evidence = list(payload["evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    payload["evidence"] = evidence

    with pytest.raises(ResearchScopeClaimGateError, match="evidence_id"):
        assert_research_scope_claim_gate_report_contract(payload)


def test_research_scope_claim_gate_rejects_source_leakage() -> None:
    payload = dict(_cached_payload())
    payload["source_text"] = "x"

    with pytest.raises(ResearchScopeClaimGateError, match="top-level keys"):
        assert_research_scope_claim_gate_report_contract(payload)


def test_research_scope_evidence_binding_rejects_claim_expansion() -> None:
    with pytest.raises(ResearchScopeClaimGateError, match="source-free"):
        ResearchScopeEvidenceBinding(
            evidence_id="objective_alpha_research_claim_gate",
            contract="objective_alpha.research_claim_gate.ci.v0",
            status="PASS",
            digest="sha256:" + "1" * 64,
            source_free=False,
        )


def test_research_scope_claim_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    payload = _cached_payload()

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        RESEARCH_SCOPE_CLAIM_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == RESEARCH_SCOPE_CLAIM_GATE_ID
    assert schema["properties"]["gate_status"]["const"] == RESEARCH_SCOPE_CLAIM_GATE_STATUS
    assert schema["properties"]["claim_id"]["const"] == RESEARCH_SCOPE_CLAIM_ID
    assert schema["properties"]["scope_boundary"]["const"] == RESEARCH_SCOPE_BOUNDARY
    assert schema["properties"]["evidence_count"]["const"] == len(
        RESEARCH_SCOPE_REQUIRED_EVIDENCE
    )
    assert schema["properties"]["production_compiler_claim"]["const"] is False
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["source_ingestion_admitted"]["const"] is False
    assert [
        item["const"] for item in schema["properties"]["supported_claims"]["prefixItems"]
    ] == list(RESEARCH_SCOPE_SUPPORTED_CLAIMS)
    assert [
        item["const"] for item in schema["properties"]["blocked_claims"]["prefixItems"]
    ] == list(RESEARCH_SCOPE_BLOCKED_CLAIMS)
    assert [
        item["const"]
        for item in schema["properties"]["required_invariants"]["prefixItems"]
    ] == list(RESEARCH_SCOPE_REQUIRED_INVARIANTS)
    assert [
        item["properties"]["evidence_id"]["const"]
        for item in schema["properties"]["evidence"]["prefixItems"]
    ] == [requirement.evidence_id for requirement in RESEARCH_SCOPE_REQUIRED_EVIDENCE]


def test_research_scope_claim_gate_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library_path",
        "file_path",
        "generated_code",
        "host_path",
        "native_source",
        "plugin_entrypoint",
        "python_source",
        "raw_benchmark_output",
        "raw_source_text",
        "raw_tensor_value",
        "raw_timing_samples",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
    }
    assert not (set(schema["properties"]) & forbidden_properties)


def test_research_scope_claim_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RESEARCH_SCOPE_CLAIM_GATE_REPORT_SCHEMA_VERSION
    assert golden["scope_boundary"] == RESEARCH_SCOPE_BOUNDARY
    assert golden["production_compiler_claim"] is False
    assert golden["native_performance_claim"] is False
    assert golden["source_ingestion_admitted"] is False


def test_research_scope_claim_gate_is_bound_in_ci_and_review_policy() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    pr_template = Path(".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    review_policy = Path("docs/REVIEW_POLICY.md").read_text(encoding="utf-8")
    proof_review = Path("docs/PROOF_ARTIFACT_REVIEW.md").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert "python examples/research_scope_claim_gate.py" in workflow
    assert "python examples/research_scope_claim_gate.py" in pr_template
    assert "Research Scope Claim Gate" in proof_review
    assert "src/tuc/research_scope_claim_gate.py" in proof_review
    assert "python examples/research_scope_claim_gate.py" in proof_review
    assert "python examples/research_scope_claim_gate.py" in review_policy
    assert "production compiler" in review_policy
    assert "native performance" in review_policy
    assert "missing source-ingestion approval" in review_policy
    assert "missing source-ingestion approval artifact" in proof_review

def test_research_scope_claim_gate_is_documented() -> None:
    schema_path = "schemas/research_scope_claim_gate_report.v0.schema.json"
    example_path = "examples/research_scope_claim_gate.py"
    golden_path = "tests/golden/proofs/research_scope_claim_gate.json"
    module_path = "src/tuc/research_scope_claim_gate.py"
    doc_path = "docs/RESEARCH_SCOPE_CLAIM_GATE.md"
    rfc_path = "rfcs/0267-research-scope-claim-gate.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
        assert (
            rfc_path in text
            or path == Path(rfc_path)
            or path.name in {"README.md", "ROADMAP.md"}
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
