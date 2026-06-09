"""Emit performance-proof readiness evidence for review."""

from tuc import (
    PerformanceProofReadinessEvidence,
    build_performance_proof_readiness_report,
    dump_performance_proof_readiness_report,
)


def build_blocked_performance_proof_evidence() -> (
    tuple[PerformanceProofReadinessEvidence, ...]
):
    """Return the current intentionally blocked performance-proof evidence set."""

    return ()


def main() -> None:
    report = build_performance_proof_readiness_report(
        "blocked-native-performance-proof-proposal",
        build_blocked_performance_proof_evidence(),
    )
    print(dump_performance_proof_readiness_report(report), end="")


if __name__ == "__main__":
    main()
