from __future__ import annotations

from pathlib import Path

import pytest

from examples.source_to_intent_readiness import build_blocked_source_to_intent_evidence
from tuc.frontend import (
    SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    SOURCE_TO_INTENT_READINESS_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    SourceToIntentReadinessError,
    SourceToIntentReadinessEvidence,
    SourceToIntentReadinessIssue,
    SourceToIntentReadinessReport,
    assert_source_to_intent_readiness,
    build_source_to_intent_readiness_report,
    dump_source_to_intent_readiness_report,
)


def test_source_to_intent_readiness_blocks_without_evidence() -> None:
    report = build_source_to_intent_readiness_report(
        "blocked-source-to-intent-parser-proposal",
        build_blocked_source_to_intent_evidence(),
    )

    assert not report.ready
    assert report.gate_contract == SOURCE_TO_INTENT_PARSER_GATE_CONTRACT
    assert len(report.checked_evidence) == len(SOURCE_TO_INTENT_REQUIRED_EVIDENCE)
    assert all(not item.present for item in report.checked_evidence)
    assert tuple(issue.evidence_id for issue in report.issues) == (
        SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    )


def test_source_to_intent_readiness_dump_matches_golden() -> None:
    report = build_source_to_intent_readiness_report(
        "blocked-source-to-intent-parser-proposal",
        build_blocked_source_to_intent_evidence(),
    )
    expected = (
        Path("tests/golden/frontend/source_to_intent_readiness_report.json")
        .read_text(encoding="utf-8")
        .rstrip("\n")
    )

    assert dump_source_to_intent_readiness_report(report) == expected + "\n"


def test_source_to_intent_readiness_passes_with_all_required_evidence() -> None:
    report = build_source_to_intent_readiness_report(
        "fully-evidenced-parser-proposal",
        tuple(
            SourceToIntentReadinessEvidence(evidence_id=evidence_id, present=True)
            for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
        ),
    )

    assert report.ready
    assert report.issues == ()
    assert all(item.present for item in report.checked_evidence)


def test_source_to_intent_readiness_requires_frontend_conformance_gate() -> None:
    report = build_source_to_intent_readiness_report(
        "missing-frontend-conformance-gate",
        tuple(
            SourceToIntentReadinessEvidence(evidence_id=evidence_id, present=True)
            for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
            if evidence_id != "source_intent_frontend_conformance_gate"
        ),
    )

    assert not report.ready
    assert report.issues == (
        SourceToIntentReadinessIssue(
            evidence_id="source_intent_frontend_conformance_gate",
            message="required source-to-intent parser gate evidence is missing",
        ),
    )


def test_source_to_intent_readiness_requires_research_diagnostics() -> None:
    report = build_source_to_intent_readiness_report(
        "missing-research-diagnostics",
        tuple(
            SourceToIntentReadinessEvidence(evidence_id=evidence_id, present=True)
            for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
            if evidence_id != "source_to_intent_research_diagnostics"
        ),
    )

    assert not report.ready
    assert report.issues == (
        SourceToIntentReadinessIssue(
            evidence_id="source_to_intent_research_diagnostics",
            message="required source-to-intent parser gate evidence is missing",
        ),
    )


def test_source_to_intent_readiness_rejects_unknown_evidence() -> None:
    with pytest.raises(ValueError, match="unsupported source-to-intent evidence id"):
        build_source_to_intent_readiness_report(
            "bad-parser-proposal",
            (
                SourceToIntentReadinessEvidence(
                    evidence_id="parser_imports_user_modules",
                    present=True,
                ),
            ),
        )


def test_source_to_intent_readiness_rejects_duplicate_evidence() -> None:
    with pytest.raises(ValueError, match="duplicate source-to-intent evidence id"):
        build_source_to_intent_readiness_report(
            "duplicate-parser-proposal",
            (
                SourceToIntentReadinessEvidence(
                    evidence_id="parser_rfc",
                    present=True,
                ),
                SourceToIntentReadinessEvidence(
                    evidence_id="parser_rfc",
                    present=True,
                ),
            ),
        )


def test_assert_source_to_intent_readiness_raises_on_missing_evidence() -> None:
    with pytest.raises(SourceToIntentReadinessError):
        assert_source_to_intent_readiness(
            "blocked-parser-proposal",
            build_blocked_source_to_intent_evidence(),
        )


def test_source_to_intent_readiness_report_rejects_oversized_text() -> None:
    report = SourceToIntentReadinessReport(
        proposal_name="x" * 513,
        gate_contract=SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
        checked_evidence=(),
        blocked_execution_surfaces=(),
        issues=(),
    )

    with pytest.raises(
        ValueError,
        match="proposal_name exceeds source-to-intent readiness field limit",
    ):
        dump_source_to_intent_readiness_report(report)


def test_source_to_intent_readiness_report_schema_version_is_stable() -> None:
    report = build_source_to_intent_readiness_report(
        "blocked-source-to-intent-parser-proposal",
        build_blocked_source_to_intent_evidence(),
    )

    assert (
        dump_source_to_intent_readiness_report(report)
        .split('"schema_version": "', 1)[1]
        .split('"', 1)[0]
        == SOURCE_TO_INTENT_READINESS_REPORT_SCHEMA_VERSION
    )
