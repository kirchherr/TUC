from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_proof_bundle import (
    SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REPORT_SCHEMA_VERSION,
    assert_proof_bundle_report_contract,
    build_proof_bundle_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_proof_bundle.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_proof_bundle_report.v0.schema.json"
)


def test_source_to_intent_research_proof_bundle_report_shape() -> None:
    report = build_proof_bundle_report()
    assert_proof_bundle_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert report["bundle_contract"] == SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT
    assert report["status"] == "PASS"
    assert report["artifact_count"] == 7
    assert report["claim"] == "safe_source_to_runtime_research_slice"
    assert report["blocked_claims"] == [
        "general_triton_source_ingestion",
        "native_performance_claim",
        "production_parser",
    ]
    assert report["review_claims"] == [
        "default_parser_blocked",
        "idiom_scope_bound",
        "preflight_gated",
        "runtime_execution_controlled",
        "source_intent_plain_data_only",
    ]
    assert [artifact["artifact_id"] for artifact in report["artifacts"]] == (
        report["required_artifacts"]
    )


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("artifact_count", 6, "artifact_count"),
        ("blocked_claims", [], "blocked_claims"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_source_to_intent_research_proof_bundle_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_proof_bundle_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_proof_bundle_report_contract(report)


def test_source_to_intent_research_proof_bundle_contract_rejects_artifact_drift() -> None:
    report = build_proof_bundle_report()
    artifacts = report["artifacts"]
    assert isinstance(artifacts, list)
    assert isinstance(artifacts[0], dict)
    artifacts[0]["digest"] = "sha256:" + "0" * 63

    with pytest.raises(ValueError, match="digest drift"):
        assert_proof_bundle_report_contract(report)


def test_source_to_intent_research_proof_bundle_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_research_proof_bundle_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_proof_bundle.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"artifact_count": 7' in completed.stdout
    assert "safe_source_to_runtime_research_slice" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_source_to_intent_research_proof_bundle_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["bundle_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE_CONTRACT
    )
    assert schema["properties"]["artifact_policy"]["const"] == (
        "digest_only_source_free"
    )
    assert schema["$defs"]["artifact"]["additionalProperties"] is False
    assert "blocked_claims" in schema["required"]


def test_source_to_intent_research_proof_bundle_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_proof_bundle.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0163-source-to-intent-research-proof-bundle.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("rfcs/0163-source-to-intent-research-proof-bundle.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
