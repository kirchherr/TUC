from __future__ import annotations

from pathlib import Path

import pytest

from examples.performance_proof_readiness import build_blocked_performance_proof_evidence
from tuc import (
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
    PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION,
    PERFORMANCE_PROOF_REQUIRED_EVIDENCE,
    PerformanceProofReadinessError,
    PerformanceProofReadinessEvidence,
    PerformanceProofReadinessReport,
    assert_performance_proof_readiness,
    build_performance_proof_readiness_report,
    dump_performance_proof_readiness_report,
)


def test_performance_proof_readiness_blocks_without_evidence() -> None:
    report = build_performance_proof_readiness_report(
        "blocked-native-performance-proof-proposal",
        build_blocked_performance_proof_evidence(),
    )

    assert not report.ready
    assert report.boundary_contract == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert len(report.checked_evidence) == len(PERFORMANCE_PROOF_REQUIRED_EVIDENCE)
    assert all(not item.present for item in report.checked_evidence)
    assert tuple(issue.evidence_id for issue in report.issues) == (
        PERFORMANCE_PROOF_REQUIRED_EVIDENCE
    )


def test_performance_proof_readiness_dump_matches_golden() -> None:
    report = build_performance_proof_readiness_report(
        "blocked-native-performance-proof-proposal",
        build_blocked_performance_proof_evidence(),
    )
    expected = (
        Path("tests/golden/proofs/performance_proof_readiness_report.json")
        .read_text(encoding="utf-8")
        .rstrip("\n")
    )

    assert dump_performance_proof_readiness_report(report) == expected + "\n"


def test_performance_proof_readiness_passes_with_all_required_evidence() -> None:
    report = build_performance_proof_readiness_report(
        "fully-evidenced-performance-proof",
        tuple(
            PerformanceProofReadinessEvidence(evidence_id=evidence_id, present=True)
            for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
        ),
    )

    assert report.ready
    assert report.issues == ()
    assert all(item.present for item in report.checked_evidence)


def test_performance_proof_readiness_rejects_unknown_evidence() -> None:
    with pytest.raises(ValueError, match="unsupported performance proof evidence id"):
        build_performance_proof_readiness_report(
            "bad-performance-proof",
            (
                PerformanceProofReadinessEvidence(
                    evidence_id="raw_cuda_benchmark_score",
                    present=True,
                ),
            ),
        )


def test_performance_proof_readiness_rejects_duplicate_evidence() -> None:
    with pytest.raises(ValueError, match="duplicate performance proof evidence id"):
        build_performance_proof_readiness_report(
            "duplicate-performance-proof",
            (
                PerformanceProofReadinessEvidence(
                    evidence_id="performance_proof_rfc",
                    present=True,
                ),
                PerformanceProofReadinessEvidence(
                    evidence_id="performance_proof_rfc",
                    present=True,
                ),
            ),
        )


def test_assert_performance_proof_readiness_raises_on_missing_evidence() -> None:
    with pytest.raises(PerformanceProofReadinessError):
        assert_performance_proof_readiness(
            "blocked-performance-proof",
            build_blocked_performance_proof_evidence(),
        )


def test_performance_proof_readiness_report_rejects_oversized_text() -> None:
    report = PerformanceProofReadinessReport(
        proposal_name="x" * 513,
        boundary_contract=PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        checked_evidence=(),
        blocked_claims=(),
        issues=(),
    )

    with pytest.raises(
        ValueError,
        match="proposal_name exceeds performance proof readiness field limit",
    ):
        dump_performance_proof_readiness_report(report)


def test_performance_proof_readiness_report_schema_version_is_stable() -> None:
    report = build_performance_proof_readiness_report(
        "blocked-native-performance-proof-proposal",
        build_blocked_performance_proof_evidence(),
    )

    assert (
        dump_performance_proof_readiness_report(report)
        .split('"schema_version": "', 1)[1]
        .split('"', 1)[0]
        == PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION
    )
