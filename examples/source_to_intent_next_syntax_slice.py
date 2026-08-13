"""Emit next-syntax Source-to-Intent semantic mapping evidence."""

from __future__ import annotations

import json
import sys

from tuc.frontend import (
    build_source_to_intent_next_syntax_report,
    dump_source_to_intent_next_syntax_report,
    parse_triton_source_to_source_intent,
    source_to_intent_next_syntax_case_from_parse_result,
)

BRANCHED_MULTI_RETURN_SOURCE = """@triton.jit
def branched_multi_return(q, k, y, z):
    scores = tl.dot(q, k)
    activated = tl.where(scores > 0.0, scores, 0.0)
    normalized = tl.softmax(scores, axis=1)
    row_sum = tl.sum(normalized, axis=1)
    tl.store(y, activated)
    tl.store(z, row_sum)
"""

BRANCHED_MULTI_RETURN_SHAPES = {
    "k": (8, 4),
    "q": (4, 8),
    "y": (4, 4),
    "z": (4,),
}

BRANCHED_MULTI_RETURN_FEATURES = (
    "branched_dataflow",
    "elementwise_where_to_source_intent",
    "explicit_public_return_aliases",
    "fanout_value_reuse",
    "matmul_to_source_intent",
    "multiple_terminal_stores",
    "reduction_explicit_axis_to_source_intent",
    "softmax_explicit_axis_to_source_intent",
)


def build_next_syntax_parse_result():
    """Parse the next syntax slice through the explicit research parser."""

    return parse_triton_source_to_source_intent(
        BRANCHED_MULTI_RETURN_SOURCE,
        source_name="next_syntax_branched_multi_return",
        tensor_shapes=BRANCHED_MULTI_RETURN_SHAPES,
    )


def build_next_syntax_report():
    """Build data-only semantic mapping evidence for the next syntax slice."""

    result = build_next_syntax_parse_result()
    case = source_to_intent_next_syntax_case_from_parse_result(
        result,
        case_id="branched_multi_return_semantic_mapping",
        syntax_features=BRANCHED_MULTI_RETURN_FEATURES,
    )
    return build_source_to_intent_next_syntax_report((case,))


def build_report() -> str:
    """Return stable next-syntax semantic mapping evidence."""

    return dump_source_to_intent_next_syntax_report(build_next_syntax_report())


def build_source_intent_golden() -> str:
    """Return stable Source Intent plain-data golden for the next syntax slice."""

    payload = build_next_syntax_parse_result().source_intent_payload
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--source-intent"]:
        print(build_source_intent_golden(), end="")
        return
    if args:
        raise SystemExit("usage: source_to_intent_next_syntax_slice.py [--source-intent]")
    print(build_report(), end="")


if __name__ == "__main__":
    main()
