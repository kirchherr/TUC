"""Emit research readiness evidence for the future Source-to-Intent parser."""

from __future__ import annotations

from tuc.frontend import (
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    SourceToIntentReadinessEvidence,
    SourceToIntentReadinessReport,
    build_source_to_intent_readiness_report,
    dump_source_to_intent_readiness_report,
)

RESEARCH_SOURCE_TO_INTENT_PROPOSAL_NAME = "research-source-to-intent-parser-proposal"
_PRESENT_RESEARCH_EVIDENCE = frozenset(
    {
        "parser_rfc",
        "parser_threat_model_update",
        "parser_budget_table",
        "source_intent_plain_data_golden",
        "source_intent_intake_report_golden",
        "source_intent_metadata_report_golden",
        "metadata_intake_report_golden",
        "hac_ir_golden",
        "runtime_plan_golden",
        "compiler_decision_report_golden",
        "hac_ir_neutrality_review",
        "source_intent_frontend_conformance_report",
        "source_intent_frontend_conformance_gate",
    }
)


def build_research_source_to_intent_evidence() -> (
    tuple[SourceToIntentReadinessEvidence, ...]
):
    """Return explicit evidence status for the research parser proposal."""

    return tuple(
        SourceToIntentReadinessEvidence(
            evidence_id=evidence_id,
            present=evidence_id in _PRESENT_RESEARCH_EVIDENCE,
        )
        for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    )


def build_research_source_to_intent_readiness_report() -> (
    SourceToIntentReadinessReport
):
    """Return the current research parser readiness report."""

    return build_source_to_intent_readiness_report(
        RESEARCH_SOURCE_TO_INTENT_PROPOSAL_NAME,
        build_research_source_to_intent_evidence(),
    )


def build_report() -> str:
    """Return stable Source-to-Intent research readiness evidence."""

    return dump_source_to_intent_readiness_report(
        build_research_source_to_intent_readiness_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
