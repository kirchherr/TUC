"""Emit Runtime Candidate Scoring Policy v0."""

from tuc import (
    RuntimeCandidateScoringPolicyReport,
    build_runtime_candidate_scoring_policy_report,
    dump_runtime_candidate_scoring_policy_report,
)


def build_current_runtime_candidate_scoring_policy() -> (
    RuntimeCandidateScoringPolicyReport
):
    """Build the current runtime candidate scoring policy report."""

    return build_runtime_candidate_scoring_policy_report()


def main() -> None:
    print(
        dump_runtime_candidate_scoring_policy_report(
            build_current_runtime_candidate_scoring_policy()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
