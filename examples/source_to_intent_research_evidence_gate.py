"""Run the CI-facing Source-To-Intent Research Evidence Gate."""

from __future__ import annotations

from hashlib import sha256

try:
    from examples.source_to_intent_research_diagnostics import (
        build_source_to_intent_research_diagnostic_cases,
    )
    from examples.source_to_intent_research_execution_bridge import (
        build_report as build_execution_bridge_report,
    )
    from examples.source_to_intent_research_parser_conformance_gate import (
        REQUIRED_PARSER_SOURCE_NAMES,
    )
    from examples.source_to_intent_research_parser_conformance_gate import (
        build_gate_report as build_conformance_gate_report,
    )
    from examples.source_to_intent_research_readiness import (
        build_research_source_to_intent_readiness_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_diagnostics import (  # type: ignore[no-redef]
        build_source_to_intent_research_diagnostic_cases,
    )
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        build_report as build_execution_bridge_report,
    )
    from source_to_intent_research_parser_conformance_gate import (  # type: ignore[no-redef]
        REQUIRED_PARSER_SOURCE_NAMES,
    )
    from source_to_intent_research_parser_conformance_gate import (
        build_gate_report as build_conformance_gate_report,
    )
    from source_to_intent_research_readiness import (  # type: ignore[no-redef]
        build_research_source_to_intent_readiness_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
    SOURCE_TO_INTENT_REQUIRED_EVIDENCE,
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentReadinessReport,
    SourceToIntentResearchDiagnosticsReport,
    build_source_to_intent_research_diagnostics_report,
    dump_source_to_intent_readiness_report,
    dump_source_to_intent_research_diagnostics_report,
)

SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT = (
    "source_to_intent_research_evidence_gate.ci.v0"
)
RESEARCH_DIAGNOSTICS_EVIDENCE_ID = "source_to_intent_research_diagnostics"
FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID = "source_intent_frontend_conformance_gate"
FORBIDDEN_GATE_OUTPUT_FRAGMENTS = (
    "@triton.jit",
    "python_source",
    "raw_source",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)


class SourceToIntentResearchEvidenceGateError(AssertionError):
    """Raised when research parser evidence binding is incomplete."""


def build_gate_report(
    *,
    readiness_report: SourceToIntentReadinessReport | None = None,
    conformance_gate_text: str | None = None,
    diagnostics_report: SourceToIntentResearchDiagnosticsReport | None = None,
    execution_bridge_text: str | None = None,
) -> str:
    """Return stable CI-facing parser research evidence binding."""

    readiness = (
        build_research_source_to_intent_readiness_report()
        if readiness_report is None
        else readiness_report
    )
    conformance_text = (
        build_conformance_gate_report()
        if conformance_gate_text is None
        else conformance_gate_text
    )
    diagnostics = (
        build_source_to_intent_research_diagnostics_report(
            build_source_to_intent_research_diagnostic_cases()
        )
        if diagnostics_report is None
        else diagnostics_report
    )
    execution_bridge = (
        build_execution_bridge_report()
        if execution_bridge_text is None
        else execution_bridge_text
    )
    _assert_readiness_bound(readiness)
    _assert_conformance_gate_bound(conformance_text)
    _assert_diagnostics_bound(diagnostics)
    _assert_execution_bridge_bound(execution_bridge)
    return _render_gate_report(
        readiness,
        conformance_text,
        diagnostics,
        execution_bridge,
    )


def main() -> None:
    print(build_gate_report(), end="")


def _assert_readiness_bound(report: SourceToIntentReadinessReport) -> None:
    if not isinstance(report, SourceToIntentReadinessReport):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: not a readiness report"
        )
    if report.gate_contract != SOURCE_TO_INTENT_PARSER_GATE_CONTRACT:
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: parser gate mismatch"
        )
    if tuple(item.evidence_id for item in report.checked_evidence) != (
        SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    ):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: readiness evidence drifted"
        )
    if not report.ready:
        issues = ",".join(issue.evidence_id for issue in report.issues)
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: "
            f"readiness incomplete: {issues}"
        )
    present = {item.evidence_id: item.present for item in report.checked_evidence}
    if not present.get(FRONTEND_CONFORMANCE_GATE_EVIDENCE_ID):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: "
            "frontend conformance gate evidence missing"
        )
    if not present.get(RESEARCH_DIAGNOSTICS_EVIDENCE_ID):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: diagnostics evidence missing"
        )


def _assert_conformance_gate_bound(text: str) -> None:
    if not isinstance(text, str):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: conformance gate not text"
        )
    required_fragments = (
        'source_intent_frontend_conformance = "passed"',
        f'parser_sources = "{",".join(REQUIRED_PARSER_SOURCE_NAMES)}"',
        'status = "PASS"',
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise SourceToIntentResearchEvidenceGateError(
                "source-to-intent research evidence gate failed: "
                "conformance gate binding missing"
            )
    _assert_gate_text_is_source_free(text)


def _assert_diagnostics_bound(report: SourceToIntentResearchDiagnosticsReport) -> None:
    if not isinstance(report, SourceToIntentResearchDiagnosticsReport):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: not a diagnostics report"
        )
    if report.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: parser status changed"
        )
    if report.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: default status changed"
        )
    if report.output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: output policy changed"
        )
    if report.raw_source_policy != SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY:
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: diagnostics leaked source"
        )
    if (
        tuple(report.blocked_compiler_outputs)
        != SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
    ):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: blocked outputs changed"
        )
    if (
        tuple(report.blocked_execution_surfaces)
        != SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
    ):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: blocked surfaces changed"
        )
    accepted_sources = tuple(
        case.source_name for case in report.cases if case.outcome == "accepted"
    )
    if accepted_sources != REQUIRED_PARSER_SOURCE_NAMES:
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: parser source binding changed"
        )
    if report.rejection_reasons != tuple(
        sorted(SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS)
    ):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: rejection coverage changed"
        )


def _assert_execution_bridge_bound(text: str) -> None:
    if not isinstance(text, str):
        raise SourceToIntentResearchEvidenceGateError(
            "source-to-intent research evidence gate failed: execution bridge not text"
        )
    required_fragments = (
        '"bridge_contract": "source_to_intent_research_execution_bridge.explicit.v0"',
        '"source_boundary": "source_intent.v0_plain_data_reintake"',
        '"status": "PASS"',
        '"research_matmul_elementwise"',
        '"research_softmax_reduction"',
        '"raw_value_policy": "omitted_by_policy"',
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise SourceToIntentResearchEvidenceGateError(
                "source-to-intent research evidence gate failed: "
                "execution bridge binding missing"
            )
    _assert_gate_text_is_source_free(text)


def _render_gate_report(
    readiness: SourceToIntentReadinessReport,
    conformance_text: str,
    diagnostics: SourceToIntentResearchDiagnosticsReport,
    execution_bridge_text: str,
) -> str:
    readiness_text = dump_source_to_intent_readiness_report(readiness)
    diagnostics_text = dump_source_to_intent_research_diagnostics_report(diagnostics)
    lines = [
        "source_to_intent.research_evidence_gate "
        "@source_to_intent_research_evidence_gate_v0 {"
    ]
    lines.append(
        f'  gate_contract = "{SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE_CONTRACT}"'
    )
    lines.append('  readiness = "ready"')
    lines.append(f'  readiness_digest = "{_digest(readiness_text)}"')
    lines.append('  conformance_gate = "passed"')
    lines.append(f'  conformance_gate_digest = "{_digest(conformance_text)}"')
    lines.append('  diagnostics = "passed"')
    lines.append(f'  diagnostics_digest = "{_digest(diagnostics_text)}"')
    lines.append('  execution_bridge = "passed"')
    lines.append(f'  execution_bridge_digest = "{_digest(execution_bridge_text)}"')
    lines.append(f'  diagnostics_evidence = "{RESEARCH_DIAGNOSTICS_EVIDENCE_ID}"')
    lines.append(
        f'  parser_sources = "{",".join(REQUIRED_PARSER_SOURCE_NAMES)}"'
    )
    lines.append(f'  accepted_diagnostic_cases = "{diagnostics.accepted_case_count}"')
    lines.append(f'  rejected_diagnostic_cases = "{diagnostics.rejected_case_count}"')
    lines.append(f'  rejection_reasons = "{",".join(diagnostics.rejection_reasons)}"')
    lines.append(f'  parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS}"')
    lines.append(
        f'  default_parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS}"'
    )
    lines.append(
        f'  parser_output_policy = "{SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY}"'
    )
    lines.append(
        "  blocked_compiler_outputs = "
        f'"{",".join(SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS)}"'
    )
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _assert_gate_text_is_source_free(text: str) -> None:
    for fragment in FORBIDDEN_GATE_OUTPUT_FRAGMENTS:
        if fragment in text:
            raise SourceToIntentResearchEvidenceGateError(
                "source-to-intent research evidence gate failed: "
                "gate output contains forbidden source fragment"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
