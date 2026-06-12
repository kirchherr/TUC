from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_parser_block_gate import (
    FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID,
    SourceToIntentParserBlockGateError,
    build_gate_report,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    SourceToIntentReadinessEvidence,
    build_source_to_intent_readiness_report,
)

_GOLDEN = Path("tests/golden/frontend/source_to_intent_parser_block_gate.txt")


def test_source_to_intent_parser_block_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'parser_status = "blocked"' in report
    assert 'readiness_status = "blocked"' in report
    assert 'frontend_conformance_gate_evidence = "missing"' in report
    assert report.rstrip().endswith('status = "PASS"\n}')


def test_source_to_intent_parser_block_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_parser_block_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")


def test_source_to_intent_parser_block_gate_rejects_ready_report() -> None:
    ready = build_source_to_intent_readiness_report(
        "fully-evidenced-parser-proposal",
        tuple(
            SourceToIntentReadinessEvidence(evidence_id=evidence_id, present=True)
            for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
        ),
    )

    with pytest.raises(
        SourceToIntentParserBlockGateError,
        match="readiness unexpectedly ready",
    ):
        build_gate_report(readiness_report=ready)


def test_source_to_intent_parser_block_gate_rejects_partial_default_evidence() -> None:
    partial = build_source_to_intent_readiness_report(
        "blocked-source-to-intent-parser-proposal",
        (
            SourceToIntentReadinessEvidence(
                evidence_id=FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID,
                present=True,
            ),
        ),
    )

    with pytest.raises(
        SourceToIntentParserBlockGateError,
        match="default blocked evidence changed",
    ):
        build_gate_report(readiness_report=partial)


def test_source_to_intent_parser_block_gate_rejects_non_report() -> None:
    with pytest.raises(
        SourceToIntentParserBlockGateError,
        match="not a readiness report",
    ):
        build_gate_report(readiness_report="not_a_report")  # type: ignore[arg-type]


def test_source_to_intent_parser_block_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_to_intent_parser_block_gate.py"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_PARSER_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_READINESS.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0123-source-to-intent-parser-block-gate.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")
