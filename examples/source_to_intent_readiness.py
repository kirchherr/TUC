"""Emit Source-To-Intent parser-gate readiness evidence for review."""

from tuc.frontend import (
    SourceToIntentReadinessEvidence,
    build_source_to_intent_readiness_report,
    dump_source_to_intent_readiness_report,
)


def build_blocked_source_to_intent_evidence() -> (
    tuple[SourceToIntentReadinessEvidence, ...]
):
    """Return the current intentionally blocked parser evidence set."""

    return ()


def main() -> None:
    report = build_source_to_intent_readiness_report(
        "blocked-source-to-intent-parser-proposal",
        build_blocked_source_to_intent_evidence(),
    )
    print(dump_source_to_intent_readiness_report(report), end="")


if __name__ == "__main__":
    main()
