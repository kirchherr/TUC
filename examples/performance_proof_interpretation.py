"""Emit the current performance-proof interpretation gate report."""

from examples.performance_proof_readiness import (
    build_current_performance_proof_readiness_evidence,
)
from tuc import (
    PerformanceProofInterpretationReport,
    build_performance_proof_interpretation_report,
    build_performance_proof_readiness_report,
    dump_performance_proof_interpretation_report,
)

_READINESS_PROPOSAL_NAME = "current-kernel-ingress-performance-proof-readiness"
_INTERPRETATION_PROPOSAL_NAME = "current-kernel-ingress-performance-proof-interpretation"


def build_current_performance_proof_interpretation_report() -> (
    PerformanceProofInterpretationReport
):
    """Build the current data-only performance interpretation report."""

    readiness = build_performance_proof_readiness_report(
        _READINESS_PROPOSAL_NAME,
        build_current_performance_proof_readiness_evidence(),
    )
    return build_performance_proof_interpretation_report(
        _INTERPRETATION_PROPOSAL_NAME,
        readiness,
    )


def main() -> None:
    report = build_current_performance_proof_interpretation_report()
    print(dump_performance_proof_interpretation_report(report), end="")


if __name__ == "__main__":
    main()
