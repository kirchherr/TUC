from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_preflight_bridge import (
    SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_REPORT_SCHEMA_VERSION,
    assert_preflight_bridge_report_contract,
    build_preflight_bridge_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_preflight_bridge.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_preflight_bridge_report.v0.schema.json"
)


def test_source_to_intent_research_preflight_bridge_report_shape() -> None:
    report = build_preflight_bridge_report()
    assert_preflight_bridge_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_REPORT_SCHEMA_VERSION
    )
    assert report["bridge_contract"] == SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_CONTRACT
    assert report["status"] == "PASS"
    assert report["accepted_case_count"] == 2
    assert report["rejected_case_count"] == 4
    assert report["preflight_accepted_count"] == 4
    assert report["preflight_reject_count"] == 2
    assert report["parser_semantic_reject_count"] == 2
    assert [case["bridge_stage"] for case in report["cases"]] == [
        "accepted_pipeline",
        "accepted_pipeline",
        "parser_semantic_reject",
        "preflight_reject",
        "parser_semantic_reject",
        "preflight_reject",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("preflight_reject_count", 0, "preflight_reject_count"),
        ("parser_semantic_reject_count", 0, "parser_semantic_reject_count"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_source_to_intent_research_preflight_bridge_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_preflight_bridge_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_preflight_bridge_report_contract(report)


def test_source_to_intent_research_preflight_bridge_contract_rejects_case_drift() -> None:
    report = build_preflight_bridge_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[3], dict)
    cases[3]["preflight_rejected_features"] = ["import_statement"]

    with pytest.raises(ValueError, match="rejection drift"):
        assert_preflight_bridge_report_contract(report)


def test_source_to_intent_research_preflight_bridge_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_research_preflight_bridge_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_preflight_bridge.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"preflight_reject_count": 2' in completed.stdout
    assert '"parser_semantic_reject_count": 2' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_source_to_intent_research_preflight_bridge_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["bridge_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_CONTRACT
    )
    assert schema["properties"]["preflight_contract"]["const"] == (
        "triton_source_preflight.execution_free.v0"
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "parser_semantic_reject_count" in schema["required"]


def test_source_to_intent_research_preflight_bridge_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_preflight_bridge.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE.md"),
        Path("rfcs/0162-source-to-intent-research-preflight-bridge.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0162-source-to-intent-research-preflight-bridge.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
