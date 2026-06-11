from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.runtime_candidate_score_evidence import (
    build_profiled_candidate_score_evidence_report,
)
from examples.runtime_candidate_scoring_gate import (
    RuntimeCandidateScoringGateError,
    build_gate_report,
)
from tuc import (
    RuntimeCandidateScoreEvidenceIssue,
    RuntimeCandidateScoreEvidenceReport,
    RuntimeCandidateScoringConformanceIssue,
    RuntimeCandidateScoringConformanceReport,
    RuntimeCandidateScoringPolicyIssue,
    RuntimeCandidateScoringPolicyReport,
    build_runtime_candidate_scoring_policy_report,
    run_runtime_candidate_scoring_conformance,
)

_GOLDEN = Path("tests/golden/runtime_candidate_scoring_gate/current_gate.txt")


def test_runtime_candidate_scoring_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'candidate_score_evidence = "passed"' in report
    assert 'candidate_scoring_policy = "complete"' in report
    assert 'candidate_scoring_conformance = "passed"' in report
    assert report.rstrip().endswith('status = "PASS"\n}')


def test_runtime_candidate_scoring_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_candidate_scoring_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")


def test_runtime_candidate_scoring_gate_rejects_failed_score_evidence() -> None:
    evidence = build_profiled_candidate_score_evidence_report()
    failed = RuntimeCandidateScoreEvidenceReport(
        graph_name=evidence.graph_name,
        operation_count=evidence.operation_count,
        default_plan_candidate_score_count=1,
        compiler_decision_candidate_score_count=(
            evidence.compiler_decision_candidate_score_count
        ),
        compiler_decision_candidate_score_digest=(
            evidence.compiler_decision_candidate_score_digest
        ),
        candidate_scores=evidence.candidate_scores,
        issues=(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="default_plan_emitted_candidate_scores",
            ),
        ),
    )

    with pytest.raises(RuntimeCandidateScoringGateError, match="score evidence"):
        build_gate_report(score_evidence_report=failed)


def test_runtime_candidate_scoring_gate_rejects_incomplete_policy() -> None:
    policy = build_runtime_candidate_scoring_policy_report()
    failed = RuntimeCandidateScoringPolicyReport(
        components=tuple(reversed(policy.components)),
        issues=(
            RuntimeCandidateScoringPolicyIssue(
                component_name="policy",
                issue_code="active_component_order_mismatch",
            ),
            RuntimeCandidateScoringPolicyIssue(
                component_name="policy",
                issue_code="blocked_component_set_mismatch",
            ),
        ),
    )

    with pytest.raises(RuntimeCandidateScoringGateError, match="policy incomplete"):
        build_gate_report(policy_report=failed)


def test_runtime_candidate_scoring_gate_rejects_failed_conformance() -> None:
    conformance = run_runtime_candidate_scoring_conformance()
    failed_case = replace(conformance.cases[0], status="failed")
    failed = RuntimeCandidateScoringConformanceReport(
        cases=(failed_case, *conformance.cases[1:]),
        issues=(
            RuntimeCandidateScoringConformanceIssue(
                case_name=failed_case.case_name,
                issue_code=f"{failed_case.case_name}_not_passed",
            ),
        ),
    )

    with pytest.raises(RuntimeCandidateScoringGateError, match="conformance failed"):
        build_gate_report(conformance_report=failed)


def test_runtime_candidate_scoring_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/runtime_candidate_scoring_gate.py"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/RUNTIME_CANDIDATE_SCORING_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")
