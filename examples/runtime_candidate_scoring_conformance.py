"""Emit Runtime Candidate Scoring Conformance v0."""

from tuc import (
    RuntimeCandidateScoringConformanceReport,
    dump_runtime_candidate_scoring_conformance_report,
    run_runtime_candidate_scoring_conformance,
)


def build_current_runtime_candidate_scoring_conformance() -> (
    RuntimeCandidateScoringConformanceReport
):
    """Build the current runtime candidate scoring conformance report."""

    return run_runtime_candidate_scoring_conformance()


def main() -> None:
    print(
        dump_runtime_candidate_scoring_conformance_report(
            build_current_runtime_candidate_scoring_conformance()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
