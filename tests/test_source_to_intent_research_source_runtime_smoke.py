from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_source_runtime_smoke import (
    SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_REPORT_SCHEMA_VERSION,
    assert_source_runtime_smoke_report_contract,
    build_report,
    build_source_runtime_smoke_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_source_runtime_smoke.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_source_runtime_smoke_report.v0.schema.json"
)


def test_source_to_intent_research_source_runtime_smoke_report_shape() -> None:
    report = build_source_runtime_smoke_report()
    assert_source_runtime_smoke_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_REPORT_SCHEMA_VERSION
    )
    assert report["smoke_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["case_count"] == 2
    assert report["input_policy"] == "accepted_research_source_buffers_only"
    assert report["source_boundary"] == (
        "caller_provided_source_buffer_to_runtime_via_research_parser"
    )
    assert report["blocked_claims"] == [
        "general_triton_source_ingestion",
        "native_performance_claim",
        "production_parser",
    ]
    assert [case["case_id"] for case in report["cases"]] == [
        "research_matmul_elementwise",
        "research_softmax_reduction",
    ]
    assert report["cases"][0]["backend_sequence"] == ["linear-sim", "vector-sim"]
    assert report["cases"][1]["backend_sequence"] == ["vector-sim", "vector-sim"]
    assert all(case["preflight_status"] == "accepted" for case in report["cases"])


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("source_boundary", "direct_triton_runtime", "source_boundary"),
        ("blocked_claims", [], "blocked_claims"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_source_to_intent_research_source_runtime_smoke_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_source_runtime_smoke_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_source_runtime_smoke_report_contract(report)


def test_source_to_intent_research_source_runtime_smoke_contract_rejects_case_drift() -> None:
    report = build_source_runtime_smoke_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["preflight_status"] = "rejected"

    with pytest.raises(ValueError, match="preflight drift"):
        assert_source_runtime_smoke_report_contract(report)


def test_source_to_intent_research_source_runtime_smoke_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_research_source_runtime_smoke_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_source_runtime_smoke.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"preflight_status": "accepted"' in completed.stdout
    assert '"source_digest"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_source_to_intent_research_source_runtime_smoke_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["smoke_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_CONTRACT
    )
    assert schema["properties"]["input_policy"]["const"] == (
        "accepted_research_source_buffers_only"
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "blocked_claims" in schema["required"]


def test_source_to_intent_research_source_runtime_smoke_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_source_runtime_smoke.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE.md"),
        Path("rfcs/0164-source-to-intent-research-source-runtime-smoke.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0164-source-to-intent-research-source-runtime-smoke.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
