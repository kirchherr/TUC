"""Run the CI-facing Source-To-Intent Parser Block Gate."""

try:
    from examples.source_to_intent_readiness import (
        build_blocked_source_to_intent_evidence,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_readiness import (  # type: ignore[no-redef]
        build_blocked_source_to_intent_evidence,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    SourceToIntentReadinessReport,
    build_source_to_intent_readiness_report,
)

SOURCE_TO_INTENT_PARSER_BLOCK_GATE_CONTRACT = (
    "source_to_intent_parser_block_gate.ci.v0"
)
DEFAULT_BLOCKED_PROPOSAL_NAME = "blocked-source-to-intent-parser-proposal"
FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID = "source_intent_frontend_conformance_gate"


class SourceToIntentParserBlockGateError(AssertionError):
    """Raised when the current source-to-intent parser block is not intact."""


def build_gate_report(
    *,
    readiness_report: SourceToIntentReadinessReport | None = None,
) -> str:
    """Return the stable CI-facing source-to-intent parser block gate report."""

    report = (
        build_source_to_intent_readiness_report(
            DEFAULT_BLOCKED_PROPOSAL_NAME,
            build_blocked_source_to_intent_evidence(),
        )
        if readiness_report is None
        else readiness_report
    )
    _assert_parser_remains_blocked(report)
    return _render_gate_report(report)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_parser_remains_blocked(report: SourceToIntentReadinessReport) -> None:
    if not isinstance(report, SourceToIntentReadinessReport):
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: not a readiness report"
        )
    if report.gate_contract != SOURCE_TO_INTENT_PARSER_GATE_CONTRACT:
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: gate contract mismatch"
        )
    if tuple(item.evidence_id for item in report.checked_evidence) != (
        SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    ):
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: evidence set drifted"
        )
    if (
        tuple(report.blocked_execution_surfaces)
        != SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES
    ):
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: blocked surfaces changed"
        )
    if report.ready:
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: readiness unexpectedly ready"
        )
    present_evidence = tuple(
        item.evidence_id for item in report.checked_evidence if item.present
    )
    if present_evidence:
        present = ",".join(present_evidence)
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: "
            f"default blocked evidence changed: {present}"
        )
    missing_evidence = frozenset(issue.evidence_id for issue in report.issues)
    if missing_evidence != frozenset(SOURCE_TO_INTENT_REQUIRED_EVIDENCE):
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: missing evidence mismatch"
        )
    if FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID not in missing_evidence:
        raise SourceToIntentParserBlockGateError(
            "source-to-intent parser block gate failed: "
            "frontend conformance gate is not blocking parser readiness"
        )


def _render_gate_report(report: SourceToIntentReadinessReport) -> str:
    lines = [
        "source_to_intent.parser_block_gate "
        "@source_to_intent_parser_block_gate_v0 {"
    ]
    lines.append(
        f'  gate_contract = "{SOURCE_TO_INTENT_PARSER_BLOCK_GATE_CONTRACT}"'
    )
    lines.append(f'  parser_gate_contract = "{report.gate_contract}"')
    lines.append('  parser_status = "blocked"')
    lines.append('  readiness_status = "blocked"')
    lines.append(f'  proposal_name = "{report.proposal_name}"')
    lines.append(f'  required_evidence_count = "{len(report.checked_evidence)}"')
    lines.append(f'  missing_evidence_count = "{len(report.issues)}"')
    lines.append('  frontend_conformance_gate_evidence = "missing"')
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(report.blocked_execution_surfaces)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
