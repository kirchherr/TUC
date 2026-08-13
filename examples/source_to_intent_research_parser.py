"""Explicit Source-to-Intent research parser example."""

from tuc.frontend import (
    dump_source_to_intent_research_parse_result,
    parse_triton_source_to_source_intent,
)

MATMUL_ELEMENTWISE_SOURCE = """@triton.jit
def matmul_elementwise(a, b, y):
    projection = tl.dot(a, b)
    activated = tl.where(projection > 0.0, projection, 0.0)
    tl.store(y, activated)
"""

SOFTMAX_REDUCTION_SOURCE = """@triton.jit
def softmax_reduction(x, y):
    normalized = tl.softmax(x, axis=1)
    row_sum = tl.sum(normalized, axis=1)
    tl.store(y, row_sum)
"""


def main() -> None:
    result = parse_triton_source_to_source_intent(
        MATMUL_ELEMENTWISE_SOURCE,
        source_name="research_matmul_elementwise",
        tensor_shapes={
            "a": (4, 8),
            "b": (8, 2),
            "y": (4, 2),
        },
    )

    print(dump_source_to_intent_research_parse_result(result), end="")


if __name__ == "__main__":
    main()
