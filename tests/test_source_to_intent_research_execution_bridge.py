from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.source_to_intent_research_execution_bridge import (
    SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_REPORT_SCHEMA_VERSION,
    build_execution_bridge_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_execution_bridge.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_execution_bridge_report.v0.schema.json"
)


def test_source_to_intent_research_execution_bridge_report_shape() -> None:
    report = build_execution_bridge_report()

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_REPORT_SCHEMA_VERSION
    )
    assert report["bridge_contract"] == SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT
    assert report["status"] == "PASS"
    assert report["case_count"] == 2
    assert report["parser_sources"] == [
        "research_matmul_elementwise",
        "research_softmax_reduction",
    ]
    assert report["source_boundary"] == "source_intent.v0_plain_data_reintake"
    assert report["raw_value_policy"] == "omitted_by_policy"
    assert [case["case_id"] for case in report["cases"]] == [
        "research_matmul_elementwise",
        "research_softmax_reduction",
    ]
    assert report["cases"][0]["backend_sequence"] == ["linear-sim", "vector-sim"]
    assert report["cases"][1]["backend_sequence"] == ["vector-sim", "vector-sim"]
    assert all(case["trace_step_count"] == 2 for case in report["cases"])


def test_source_to_intent_research_execution_bridge_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_research_execution_bridge_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_execution_bridge.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"reference_correctness_digest"' in completed.stdout
    assert '"plain_data_digest"' in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_source_to_intent_research_execution_bridge_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["bridge_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT
    )
    assert schema["properties"]["source_boundary"]["const"] == (
        "source_intent.v0_plain_data_reintake"
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "plain_data_digest" in schema["$defs"]["case"]["properties"]


def test_source_to_intent_research_execution_bridge_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_execution_bridge.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE.md"),
        Path("rfcs/0160-source-to-intent-research-execution-bridge.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0160-source-to-intent-research-execution-bridge.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
