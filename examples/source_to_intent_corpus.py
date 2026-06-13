"""Emit Source-to-Intent parser corpus evidence for the research proposal."""

from __future__ import annotations

from tuc.frontend import (
    SourceToIntentCorpusCase,
    build_source_to_intent_corpus_report,
    dump_source_to_intent_corpus_report,
    source_to_intent_corpus_case_from_source,
)

ACCEPTED_MATMUL_ELEMENTWISE_SOURCE = """@triton.jit
def matmul_elementwise(a, b, y):
    projection = tl.dot(a, b)
    activated = tl.where(projection > 0.0, projection, 0.0)
    tl.store(y, activated)
"""

ACCEPTED_SOFTMAX_REDUCTION_SOURCE = """@triton.jit
def softmax_reduction(x, y):
    normalized = tl.softmax(x, axis=1)
    row_sum = tl.sum(normalized, axis=1)
    tl.store(y, row_sum)
"""

REJECT_IMPORT_ESCAPE_SOURCE = """import os

@triton.jit
def import_escape(x, y):
    tl.store(y, x)
"""

REJECT_DECORATOR_CALL_SOURCE = """@triton.jit(num_warps=4)
def decorator_call(x, y):
    tl.store(y, x)
"""

REJECT_AMBIGUOUS_SOFTMAX_AXIS_SOURCE = """@triton.jit
def ambiguous_softmax_axis(x, y):
    normalized = tl.softmax(x)
    tl.store(y, normalized)
"""

REJECT_HARDWARE_HINT_SOURCE = """@triton.jit
def hardware_hint(x, y):
    target = "cuda"
    tl.store(y, x)
"""


def build_source_to_intent_corpus_cases() -> tuple[SourceToIntentCorpusCase, ...]:
    """Return the current source corpus cases without retaining raw source."""

    return (
        source_to_intent_corpus_case_from_source(
            case_id="accepted_matmul_elementwise",
            expectation="accepted",
            source=ACCEPTED_MATMUL_ELEMENTWISE_SOURCE,
            operation_families=("elementwise", "matmul"),
        ),
        source_to_intent_corpus_case_from_source(
            case_id="accepted_softmax_reduction",
            expectation="accepted",
            source=ACCEPTED_SOFTMAX_REDUCTION_SOURCE,
            operation_families=("reduction", "softmax"),
        ),
        source_to_intent_corpus_case_from_source(
            case_id="reject_ambiguous_softmax_axis",
            expectation="rejected",
            source=REJECT_AMBIGUOUS_SOFTMAX_AXIS_SOURCE,
            expected_rejection_features=("ambiguous_softmax_axis",),
        ),
        source_to_intent_corpus_case_from_source(
            case_id="reject_decorator_call",
            expectation="rejected",
            source=REJECT_DECORATOR_CALL_SOURCE,
            expected_rejection_features=("decorator_call",),
        ),
        source_to_intent_corpus_case_from_source(
            case_id="reject_hardware_hint",
            expectation="rejected",
            source=REJECT_HARDWARE_HINT_SOURCE,
            expected_rejection_features=("hardware_specific_source_hint",),
        ),
        source_to_intent_corpus_case_from_source(
            case_id="reject_import_escape",
            expectation="rejected",
            source=REJECT_IMPORT_ESCAPE_SOURCE,
            expected_rejection_features=("import_statement",),
        ),
    )


def build_report() -> str:
    """Return stable Source-to-Intent corpus evidence."""

    return dump_source_to_intent_corpus_report(
        build_source_to_intent_corpus_report(build_source_to_intent_corpus_cases())
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
