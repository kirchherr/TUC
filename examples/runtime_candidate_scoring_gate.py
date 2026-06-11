"""Run the CI-facing Runtime Candidate Scoring Gate."""

try:
    from examples.runtime_candidate_score_evidence import (
        build_profiled_candidate_score_evidence_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_candidate_score_evidence import (  # type: ignore[no-redef]
        build_profiled_candidate_score_evidence_report,
    )

from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeCandidateScoreEvidenceReport,
    RuntimeCandidateScoringConformanceReport,
    RuntimeCandidateScoringPolicyReport,
    assert_runtime_candidate_score_evidence,
    assert_runtime_candidate_scoring_conformance,
    assert_runtime_candidate_scoring_policy,
    build_runtime_candidate_scoring_policy_report,
    run_runtime_candidate_scoring_conformance,
)


class RuntimeCandidateScoringGateError(AssertionError):
    """Raised when runtime candidate scoring evidence is incomplete."""


def build_gate_report(
    *,
    score_evidence_report: RuntimeCandidateScoreEvidenceReport | None = None,
    policy_report: RuntimeCandidateScoringPolicyReport | None = None,
    conformance_report: RuntimeCandidateScoringConformanceReport | None = None,
) -> str:
    """Return the stable CI-facing runtime candidate scoring gate report."""

    score_evidence = (
        build_profiled_candidate_score_evidence_report()
        if score_evidence_report is None
        else score_evidence_report
    )
    policy = (
        build_runtime_candidate_scoring_policy_report()
        if policy_report is None
        else policy_report
    )
    conformance = (
        run_runtime_candidate_scoring_conformance()
        if conformance_report is None
        else conformance_report
    )
    _assert_score_evidence_passed(score_evidence)
    _assert_policy_complete(policy)
    _assert_conformance_passed(conformance)
    return _render_gate_report(score_evidence, policy, conformance)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_score_evidence_passed(
    report: RuntimeCandidateScoreEvidenceReport,
) -> None:
    try:
        assert_runtime_candidate_score_evidence(report)
    except AssertionError as exc:
        raise RuntimeCandidateScoringGateError(
            f"runtime candidate score evidence failed: {exc}"
        ) from exc


def _assert_policy_complete(report: RuntimeCandidateScoringPolicyReport) -> None:
    try:
        assert_runtime_candidate_scoring_policy(report)
    except AssertionError as exc:
        raise RuntimeCandidateScoringGateError(
            f"runtime candidate scoring policy incomplete: {exc}"
        ) from exc


def _assert_conformance_passed(
    report: RuntimeCandidateScoringConformanceReport,
) -> None:
    try:
        assert_runtime_candidate_scoring_conformance(report)
    except AssertionError as exc:
        raise RuntimeCandidateScoringGateError(
            f"runtime candidate scoring conformance failed: {exc}"
        ) from exc


def _render_gate_report(
    score_evidence: RuntimeCandidateScoreEvidenceReport,
    policy: RuntimeCandidateScoringPolicyReport,
    conformance: RuntimeCandidateScoringConformanceReport,
) -> str:
    lines = ["runtime.candidate_scoring_gate @runtime_candidate_scoring_gate_v0 {"]
    lines.append('  candidate_score_evidence = "passed"')
    lines.append(f'  candidate_score_count = "{len(score_evidence.candidate_scores)}"')
    lines.append('  candidate_scoring_policy = "complete"')
    lines.append(
        '  candidate_scoring_policy_active_components = '
        f'"{len(policy.active_component_order)}"'
    )
    lines.append(
        '  candidate_scoring_policy_blocked_components = '
        f'"{len(policy.blocked_component_names)}"'
    )
    lines.append('  candidate_scoring_conformance = "passed"')
    lines.append(f'  candidate_scoring_conformance_cases = "{len(conformance.cases)}"')
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
