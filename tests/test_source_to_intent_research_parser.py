from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_parser import MATMUL_ELEMENTWISE_SOURCE
from tuc.frontend import (
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchParserError,
    dump_source_to_intent_research_parse_result,
    parse_triton_source_to_source_intent,
    source_to_intent_research_parse_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/frontend/source_to_intent_research_parser.json")
SCHEMA_PATH = Path("schemas/source_to_intent_research_parser_report.v0.schema.json")

SOFTMAX_REDUCTION_SOURCE = """@triton.jit
def softmax_reduction(x, y):
    normalized = tl.softmax(x, axis=1)
    row_sum = tl.sum(normalized, axis=1)
    tl.store(y, row_sum)
"""


def test_research_parser_emits_source_intent_plain_data() -> None:
    result = _parse_matmul_elementwise()

    assert result.module.name == "research_matmul_elementwise"
    assert result.module.contract == SOURCE_INTENT_IR_CONTRACT
    assert tuple(tensor.name for tensor in result.module.tensors) == (
        "a",
        "b",
        "projection",
        "activated",
    )
    assert tuple(operation.family for operation in result.module.operations) == (
        "matmul",
        "elementwise",
    )
    assert tuple(source_return.public_name for source_return in result.module.returns) == (
        "y",
    )
    assert result.source_intent_payload["schema_version"] == SOURCE_INTENT_SCHEMA_VERSION
    assert result.report.parser_contract == SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    assert result.report.parser_status == SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    assert result.report.default_parser_status == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    )
    assert result.report.output_policy == SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    assert result.report.operation_families == ("elementwise", "matmul")
    assert "metadata" in result.report.blocked_compiler_outputs
    assert "triton_jit_execution" in result.report.blocked_execution_surfaces


def test_research_parser_handles_softmax_reduction_subset() -> None:
    result = parse_triton_source_to_source_intent(
        SOFTMAX_REDUCTION_SOURCE,
        source_name="research_softmax_reduction",
        tensor_shapes={"x": (4, 8), "y": (4,)},
    )

    assert tuple(tensor.name for tensor in result.module.tensors) == (
        "x",
        "normalized",
        "row_sum",
    )
    assert tuple(tensor.shape for tensor in result.module.tensors) == (
        (4, 8),
        (4, 8),
        (4,),
    )
    assert tuple(operation.family for operation in result.module.operations) == (
        "softmax",
        "reduction",
    )
    assert result.source_intent_payload["operations"][0]["attributes"] == {"axis": 1}
    assert result.source_intent_payload["operations"][1]["attributes"] == {"axis": 1}
    assert result.module.returns[0].public_name == "y"
    assert result.module.returns[0].tensor_name == "row_sum"
    assert result.report.operation_families == ("reduction", "softmax")


def test_research_parser_dump_matches_golden() -> None:
    assert dump_source_to_intent_research_parse_result(_parse_matmul_elementwise()) == (
        GOLDEN_PATH.read_text(encoding="utf-8")
    )


def test_research_parser_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_parser.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout


def test_research_parser_report_payload_shape() -> None:
    payload = source_to_intent_research_parse_report_to_dict(
        _parse_matmul_elementwise().report
    )

    assert payload["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_SCHEMA_VERSION
    )
    assert payload["parser_status"] == "research_explicit_only"
    assert payload["default_parser_status"] == "default_parser_blocked"
    assert payload["output_policy"] == "source_intent.v0_plain_data_only"
    assert payload["source_digest"].startswith("sha256:")


def test_research_parser_report_schema_declares_version() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["parser_status"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    )
    assert schema["properties"]["default_parser_status"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    )


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "import os\n@triton.jit\ndef import_escape(x, y):\n    tl.store(y, x)\n",
            "preflight rejected",
        ),
        (
            "@triton.jit(num_warps=4)\ndef decorator_call(x, y):\n    tl.store(y, x)\n",
            "preflight rejected",
        ),
        (
            "@triton.jit\ndef ambiguous_softmax_axis(x, y):\n"
            "    normalized = tl.softmax(x)\n"
            "    tl.store(y, normalized)\n",
            "requires explicit axis",
        ),
        (
            "@triton.jit\ndef hardware_hint(x, y):\n"
            '    target = "cuda"\n'
            "    tl.store(y, x)\n",
            "assignment value must be a supported call",
        ),
        (
            "@triton.jit\ndef positional_only(x, /, y):\n"
            "    copied = tl.where(x > 0.0, x, 0.0)\n"
            "    tl.store(y, copied)\n",
            "simple positional arguments",
        ),
    ],
)
def test_research_parser_rejects_unsupported_or_hostile_source(
    source: str,
    message: str,
) -> None:
    with pytest.raises(SourceToIntentResearchParserError, match=message):
        parse_triton_source_to_source_intent(
            source,
            source_name="rejected_kernel",
            tensor_shapes={"x": (4, 8), "y": (4, 8)},
        )


def test_research_parser_rejects_shape_mismatch() -> None:
    with pytest.raises(SourceToIntentResearchParserError, match="target shape mismatch"):
        parse_triton_source_to_source_intent(
            MATMUL_ELEMENTWISE_SOURCE,
            source_name="shape_mismatch",
            tensor_shapes={
                "a": (4, 8),
                "b": (8, 2),
                "y": (4, 4),
            },
        )


def test_research_parser_rejects_unknown_shape_manifest_entries() -> None:
    with pytest.raises(
        SourceToIntentResearchParserError,
        match="shape manifest has unknown key",
    ):
        parse_triton_source_to_source_intent(
            MATMUL_ELEMENTWISE_SOURCE,
            source_name="unknown_manifest_entry",
            tensor_shapes={
                "a": (4, 8),
                "b": (8, 2),
                "extra": (1,),
                "y": (4, 2),
            },
        )


def test_research_parser_report_does_not_expose_compiler_artifacts() -> None:
    result = _parse_matmul_elementwise()

    assert not hasattr(result.report, "to_compute_graph")
    assert not hasattr(result.report, "dump_runtime_plan")
    assert "compute_graph" in result.report.blocked_compiler_outputs


def _parse_matmul_elementwise():
    return parse_triton_source_to_source_intent(
        MATMUL_ELEMENTWISE_SOURCE,
        source_name="research_matmul_elementwise",
        tensor_shapes={
            "a": (4, 8),
            "b": (8, 2),
            "y": (4, 2),
        },
    )
