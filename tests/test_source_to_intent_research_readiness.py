from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.source_to_intent_research_readiness import (
    RESEARCH_SOURCE_TO_INTENT_PROPOSAL_NAME,
    build_research_source_to_intent_readiness_report,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    dump_source_to_intent_readiness_report,
)

GOLDEN_PATH = Path("tests/golden/frontend/source_to_intent_research_readiness.json")
MISSING_RESEARCH_EVIDENCE = (
    "accepted_source_corpus",
    "rejected_source_corpus",
    "source_fuzz_or_property_corpus",
    "parser_report_golden",
)


def test_source_to_intent_research_readiness_is_partial_and_blocked() -> None:
    report = build_research_source_to_intent_readiness_report()
    present = tuple(
        item.evidence_id for item in report.checked_evidence if item.present
    )

    assert report.proposal_name == RESEARCH_SOURCE_TO_INTENT_PROPOSAL_NAME
    assert report.gate_contract == SOURCE_TO_INTENT_PARSER_GATE_CONTRACT
    assert tuple(item.evidence_id for item in report.checked_evidence) == (
        SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    )
    assert not report.ready
    assert tuple(issue.evidence_id for issue in report.issues) == (
        MISSING_RESEARCH_EVIDENCE
    )
    assert len(present) == len(SOURCE_TO_INTENT_REQUIRED_EVIDENCE) - len(
        MISSING_RESEARCH_EVIDENCE
    )


def test_source_to_intent_research_readiness_dump_matches_golden() -> None:
    report = build_research_source_to_intent_readiness_report()

    assert dump_source_to_intent_readiness_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_source_to_intent_research_readiness_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_readiness.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"ready": false' in completed.stdout
    assert "accepted_source_corpus" in completed.stdout
    assert "triton_jit_execution" in completed.stdout
    assert "raw_source" not in completed.stdout
    assert "python_source" not in completed.stdout
