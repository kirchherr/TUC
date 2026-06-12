from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.source_to_intent_research_diagnostics import (
    build_source_to_intent_research_diagnostic_cases,
)
from examples.source_to_intent_research_evidence_gate import (
    FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID,
    RESEARCH_DIAGNOSTICS_EVIDENCE_ID,
    SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT,
    SourceToIntentResearchEvidenceGateError,
    build_gate_report,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    SourceToIntentReadinessEvidence,
    SourceToIntentReadinessReport,
    build_source_to_intent_research_diagnostics_report,
)

_GOLDEN = Path("tests/golden/frontend/source_to_intent_research_evidence_gate.txt")


def test_source_to_intent_research_evidence_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert (
        f'gate_contract = "{SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT}"'
        in report
    )
    assert 'readiness = "ready"' in report
    assert 'conformance_gate = "passed"' in report
    assert 'diagnostics = "passed"' in report
    assert 'status = "PASS"' in report


def test_source_to_intent_research_evidence_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_evidence_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")
    assert "sha256:" in completed.stdout
    assert RESEARCH_DIAGNOSTICS_EVIDENCE_ID in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_source_to_intent_research_evidence_gate_rejects_incomplete_readiness() -> None:
    readiness = SourceToIntentReadinessReport(
        proposal_name="research-source-to-intent-parser-proposal",
        gate_contract=SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
        checked_evidence=tuple(
            SourceToIntentReadinessEvidence(
                evidence_id=evidence_id,
                present=evidence_id != RESEARCH_DIAGNOSTICS_EVIDENCE_ID,
            )
            for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
        ),
        blocked_execution_surfaces=SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES,
        issues=(),
    )

    with pytest.raises(
        SourceToIntentResearchEvidenceGateError,
        match="diagnostics evidence missing",
    ):
        build_gate_report(readiness_report=readiness)


def test_source_to_intent_research_evidence_gate_requires_frontend_conformance() -> None:
    readiness = SourceToIntentReadinessReport(
        proposal_name="research-source-to-intent-parser-proposal",
        gate_contract=SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
        checked_evidence=tuple(
            SourceToIntentReadinessEvidence(
                evidence_id=evidence_id,
                present=evidence_id != FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID,
            )
            for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
        ),
        blocked_execution_surfaces=SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES,
        issues=(),
    )

    with pytest.raises(
        SourceToIntentResearchEvidenceGateError,
        match="frontend conformance gate evidence missing",
    ):
        build_gate_report(readiness_report=readiness)


def test_source_to_intent_research_evidence_gate_rejects_tampered_conformance() -> None:
    with pytest.raises(
        SourceToIntentResearchEvidenceGateError,
        match="conformance gate binding missing",
    ):
        build_gate_report(conformance_gate_text='status = "PASS"\n')


def test_source_to_intent_research_evidence_gate_rejects_source_leakage() -> None:
    leaky_conformance = (
        'source_intent_frontend_conformance = "passed"\n'
        'parser_sources = "research_matmul_elementwise,research_softmax_reduction"\n'
        'status = "PASS"\n'
        "@triton.jit\n"
    )

    with pytest.raises(
        SourceToIntentResearchEvidenceGateError,
        match="forbidden source fragment",
    ):
        build_gate_report(conformance_gate_text=leaky_conformance)


def test_source_to_intent_research_evidence_gate_rejects_source_binding_drift() -> None:
    diagnostics = build_source_to_intent_research_diagnostics_report(
        build_source_to_intent_research_diagnostic_cases()
    )
    tampered_case = replace(diagnostics.cases[0], source_name="wrong_source")
    tampered_report = replace(
        diagnostics,
        cases=(tampered_case, *diagnostics.cases[1:]),
    )

    with pytest.raises(
        SourceToIntentResearchEvidenceGateError,
        match="parser source binding changed",
    ):
        build_gate_report(diagnostics_report=tampered_report)


def test_source_to_intent_research_evidence_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_to_intent_research_evidence_gate.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_READINESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0159-source-to-intent-research-evidence-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert gate_path in text
    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_READINESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md"),
        Path("rfcs/0159-source-to-intent-research-evidence-gate.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
