"""Emit source-free diagnostics for the Source-to-Intent research parser."""

from __future__ import annotations

from examples.source_to_intent_corpus import (
    REJECT_AMBIGUOUS_SOFTMAX_AXIS_SOURCE,
    REJECT_DECORATOR_CALL_SOURCE,
    REJECT_HARDWARE_HINT_SOURCE,
    REJECT_IMPORT_ESCAPE_SOURCE,
)
from examples.source_to_intent_research_parser import (
    MATMUL_ELEMENTWISE_SOURCE,
    SOFTMAX_REDUCTION_SOURCE,
)
from tuc.frontend import (
    SourceToIntentResearchDiagnosticCase,
    build_source_to_intent_research_diagnostics_report,
    dump_source_to_intent_research_diagnostics_report,
)


def build_source_to_intent_research_diagnostic_cases() -> (
    tuple[SourceToIntentResearchDiagnosticCase, ...]
):
    """Return the accepted and rejected diagnostic source cases."""

    return (
        SourceToIntentResearchDiagnosticCase(
            case_id="accepted_matmul_elementwise",
            expectation="accepted",
            source=MATMUL_ELEMENTWISE_SOURCE,
            source_name="research_matmul_elementwise",
            tensor_shapes={
                "a": (4, 8),
                "b": (8, 2),
                "y": (4, 2),
            },
        ),
        SourceToIntentResearchDiagnosticCase(
            case_id="accepted_softmax_reduction",
            expectation="accepted",
            source=SOFTMAX_REDUCTION_SOURCE,
            source_name="research_softmax_reduction",
            tensor_shapes={
                "x": (4, 8),
                "y": (4,),
            },
        ),
        SourceToIntentResearchDiagnosticCase(
            case_id="reject_ambiguous_softmax_axis",
            expectation="rejected",
            source=REJECT_AMBIGUOUS_SOFTMAX_AXIS_SOURCE,
            source_name="reject_ambiguous_softmax_axis",
            tensor_shapes={
                "x": (4, 8),
                "y": (4, 8),
            },
            expected_rejection_reason="missing_axis_keyword",
        ),
        SourceToIntentResearchDiagnosticCase(
            case_id="reject_decorator_call",
            expectation="rejected",
            source=REJECT_DECORATOR_CALL_SOURCE,
            source_name="reject_decorator_call",
            tensor_shapes={
                "x": (4, 8),
                "y": (4, 8),
            },
            expected_rejection_reason="preflight_decorator_call",
        ),
        SourceToIntentResearchDiagnosticCase(
            case_id="reject_hardware_hint",
            expectation="rejected",
            source=REJECT_HARDWARE_HINT_SOURCE,
            source_name="reject_hardware_hint",
            tensor_shapes={
                "x": (4, 8),
                "y": (4, 8),
            },
            expected_rejection_reason="unsupported_assignment_value",
        ),
        SourceToIntentResearchDiagnosticCase(
            case_id="reject_import_escape",
            expectation="rejected",
            source=REJECT_IMPORT_ESCAPE_SOURCE,
            source_name="reject_import_escape",
            tensor_shapes={
                "x": (4, 8),
                "y": (4, 8),
            },
            expected_rejection_reason="preflight_import_statement",
        ),
    )


def build_report() -> str:
    """Return stable research parser diagnostics evidence."""

    return dump_source_to_intent_research_diagnostics_report(
        build_source_to_intent_research_diagnostics_report(
            build_source_to_intent_research_diagnostic_cases()
        )
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
