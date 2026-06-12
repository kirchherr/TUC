"""Run the CI-facing Source-To-Intent Research Parser Conformance Gate."""

try:
    from examples.source_to_intent_research_parser import (
        MATMUL_ELEMENTWISE_SOURCE,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_parser import (  # type: ignore[no-redef]
        MATMUL_ELEMENTWISE_SOURCE,
    )

from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceIntentFrontendConformanceCase,
    SourceIntentFrontendConformanceReport,
    SourceToIntentResearchParseResult,
    parse_triton_source_to_source_intent,
    run_source_intent_frontend_conformance,
)

SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE_CONTRACT = (
    "source_to_intent_research_parser_conformance_gate.ci.v0"
)
DEFAULT_FRONTEND_NAME = "source-to-intent-research-parser"
REQUIRED_ACCEPTED_CASES = (
    "research_parser_matmul_elementwise",
)
REQUIRED_REJECTED_CASES = (
    "reject_parser_backend_hint_escape",
    "reject_parser_source_text_escape",
)
REQUIRED_PARSER_SOURCE_NAMES = (
    "research_matmul_elementwise",
)


class SourceToIntentResearchParserConformanceGateError(AssertionError):
    """Raised when research parser conformance gate evidence is incomplete."""


def build_source_to_intent_research_parser_results() -> (
    tuple[SourceToIntentResearchParseResult, ...]
):
    """Return accepted explicit parser results for conformance checking."""

    return (
        parse_triton_source_to_source_intent(
            MATMUL_ELEMENTWISE_SOURCE,
            source_name="research_matmul_elementwise",
            tensor_shapes={
                "a": (4, 8),
                "b": (8, 2),
                "y": (4, 2),
            },
        ),
    )


def build_source_to_intent_research_parser_conformance_cases(
    parser_results: tuple[SourceToIntentResearchParseResult, ...] | None = None,
) -> tuple[SourceIntentFrontendConformanceCase, ...]:
    """Return conformance cases bound to explicit research parser output."""

    results = (
        build_source_to_intent_research_parser_results()
        if parser_results is None
        else parser_results
    )
    _assert_parser_results(results)
    return (
        SourceIntentFrontendConformanceCase(
            name="research_parser_matmul_elementwise",
            payload=results[0].source_intent_payload,
            should_accept=True,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_parser_backend_hint_escape",
            payload={
                "name": "bad_parser_payload",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "tensors": [{"name": "a", "shape": [1]}],
                "operations": [
                    {
                        "family": "elementwise",
                        "hints": {"backend": "gpu"},
                        "inputs": ["a"],
                        "name": "bad",
                        "outputs": ["a"],
                    }
                ],
            },
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_parser_source_text_escape",
            payload={
                "name": "bad_parser_payload",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "python_source": "@triton.jit\ndef kernel(): pass",
                "tensors": [],
                "operations": [],
            },
            should_accept=False,
        ),
    )


def build_gate_report(
    *,
    conformance_report: SourceIntentFrontendConformanceReport | None = None,
    parser_results: tuple[SourceToIntentResearchParseResult, ...] | None = None,
) -> str:
    """Return stable CI-facing research parser conformance gate evidence."""

    results = (
        build_source_to_intent_research_parser_results()
        if parser_results is None
        else parser_results
    )
    _assert_parser_results(results)
    report = (
        run_source_intent_frontend_conformance(
            DEFAULT_FRONTEND_NAME,
            build_source_to_intent_research_parser_conformance_cases(results),
        )
        if conformance_report is None
        else conformance_report
    )
    _assert_conformance_passed(report)
    _assert_required_cases_covered(report)
    return _render_gate_report(report, results)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_parser_results(
    results: tuple[SourceToIntentResearchParseResult, ...],
) -> None:
    if type(results) is not tuple:
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance failed: parser results must be a tuple"
        )
    if len(results) != len(REQUIRED_PARSER_SOURCE_NAMES):
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance failed: parser result count mismatch"
        )
    source_names = tuple(result.report.source_name for result in results)
    if source_names != REQUIRED_PARSER_SOURCE_NAMES:
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance failed: parser source names changed"
        )
    for result in results:
        if not isinstance(result, SourceToIntentResearchParseResult):
            raise SourceToIntentResearchParserConformanceGateError(
                "research parser conformance failed: not a parser result"
            )
        report = result.report
        if report.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise SourceToIntentResearchParserConformanceGateError(
                "research parser conformance failed: parser status changed"
            )
        if report.default_parser_status != (
            SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
        ):
            raise SourceToIntentResearchParserConformanceGateError(
                "research parser conformance failed: default parser status changed"
            )
        if report.output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise SourceToIntentResearchParserConformanceGateError(
                "research parser conformance failed: output policy changed"
            )
        if (
            report.blocked_compiler_outputs
            != SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
        ):
            raise SourceToIntentResearchParserConformanceGateError(
                "research parser conformance failed: blocked compiler outputs changed"
            )
        if (
            report.blocked_execution_surfaces
            != SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
        ):
            raise SourceToIntentResearchParserConformanceGateError(
                "research parser conformance failed: blocked surfaces changed"
            )


def _assert_conformance_passed(
    report: SourceIntentFrontendConformanceReport,
) -> None:
    if not isinstance(report, SourceIntentFrontendConformanceReport):
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance failed: not a conformance report"
        )
    if not report.passed:
        issues = ",".join(
            f"{issue.case_name}:{issue.message}" for issue in report.issues
        )
        raise SourceToIntentResearchParserConformanceGateError(
            f"research parser conformance failed: {issues}"
        )
    if report.frontend_name != DEFAULT_FRONTEND_NAME:
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance failed: frontend name changed"
        )


def _assert_required_cases_covered(
    report: SourceIntentFrontendConformanceReport,
) -> None:
    checked_cases = frozenset(report.checked_cases)
    missing_cases = tuple(
        case_name
        for case_name in (*REQUIRED_ACCEPTED_CASES, *REQUIRED_REJECTED_CASES)
        if case_name not in checked_cases
    )
    if missing_cases:
        missing = ",".join(missing_cases)
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance coverage failed: "
            f"missing {missing}"
        )
    if report.accepted_case_count != len(REQUIRED_ACCEPTED_CASES):
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance coverage failed: accepted case count changed"
        )
    if report.rejected_case_count != len(REQUIRED_REJECTED_CASES):
        raise SourceToIntentResearchParserConformanceGateError(
            "research parser conformance coverage failed: rejected case count changed"
        )


def _render_gate_report(
    report: SourceIntentFrontendConformanceReport,
    results: tuple[SourceToIntentResearchParseResult, ...],
) -> str:
    lines = [
        "source_to_intent.research_parser_conformance_gate "
        "@source_to_intent_research_parser_conformance_gate_v0 {"
    ]
    lines.append(
        f'  gate_contract = "{SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE_CONTRACT}"'
    )
    lines.append(f'  parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS}"')
    lines.append(
        f'  default_parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS}"'
    )
    lines.append(
        f'  parser_output_policy = "{SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY}"'
    )
    lines.append('  source_intent_frontend_conformance = "passed"')
    lines.append(f'  frontend_name = "{report.frontend_name}"')
    lines.append(
        f'  parser_sources = "{",".join(result.report.source_name for result in results)}"'
    )
    lines.append(f'  accepted_cases = "{report.accepted_case_count}"')
    lines.append(f'  rejected_cases = "{report.rejected_case_count}"')
    lines.append(f'  checked_cases = "{len(report.checked_cases)}"')
    lines.append(
        f'  required_accepted_cases = "{",".join(REQUIRED_ACCEPTED_CASES)}"'
    )
    lines.append(
        f'  required_rejected_cases = "{",".join(REQUIRED_REJECTED_CASES)}"'
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


if __name__ == "__main__":
    main()
