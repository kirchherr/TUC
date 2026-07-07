from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from examples import source_to_intent_next_syntax_slice as next_syntax_example
from tuc.frontend import (
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_NEXT_SYNTAX_ARTIFACT_STATUS,
    SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT,
    SOURCE_TO_INTENT_NEXT_SYNTAX_GOLDEN_POLICY,
    SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES,
    SOURCE_TO_INTENT_NEXT_SYNTAX_RFC,
    SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentNextSyntaxCase,
    SourceToIntentNextSyntaxProperty,
    SourceToIntentNextSyntaxReport,
    SourceToIntentResearchParserError,
    build_source_to_intent_next_syntax_report,
    parse_triton_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_payload_digest,
    source_to_intent_next_syntax_report_to_dict,
)

REPORT_GOLDEN = Path("tests/golden/frontend/source_to_intent_next_syntax_report.json")
SOURCE_INTENT_GOLDEN = Path(
    "tests/golden/frontend/source_to_intent_next_syntax_source_intent.json"
)
SCHEMA_PATH = Path("schemas/source_to_intent_next_syntax_report.v0.schema.json")
SAFE_TEXT_RE = re.compile(r"^(sha256:[a-f0-9]{64}|[A-Za-z][A-Za-z0-9_.-]*)$")


def test_next_syntax_slice_maps_branched_multi_return_source() -> None:
    result = next_syntax_example.build_next_syntax_parse_result()
    report = next_syntax_example.build_next_syntax_report()
    payload = source_to_intent_next_syntax_report_to_dict(report)

    assert result.module.contract == SOURCE_INTENT_IR_CONTRACT
    assert tuple(tensor.name for tensor in result.module.tensors) == (
        "q",
        "k",
        "scores",
        "activated",
        "normalized",
        "row_sum",
    )
    assert tuple(operation.family for operation in result.module.operations) == (
        "matmul",
        "elementwise",
        "softmax",
        "reduction",
    )
    assert tuple(source_return.public_name for source_return in result.module.returns) == (
        "y",
        "z",
    )
    assert payload["schema_version"] == SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == SOURCE_TO_INTENT_NEXT_SYNTAX_ARTIFACT_STATUS
    assert payload["mapping_contract"] == SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT
    assert payload["syntax_slice"] == SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE
    assert payload["parser_rfc"] == SOURCE_TO_INTENT_NEXT_SYNTAX_RFC
    assert payload["golden_policy"] == SOURCE_TO_INTENT_NEXT_SYNTAX_GOLDEN_POLICY
    assert payload["parser_contract"] == SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    assert payload["parser_status"] == SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    assert payload["default_parser_status"] == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    )
    assert payload["parser_output_policy"] == (
        SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    )
    assert payload["direct_source_ingestion"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["case_count"] == 1
    assert payload["property_coverage_complete"] is True
    assert payload["property_count"] == len(SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES)
    assert payload["cases"][0]["return_count"] == 2
    assert payload["cases"][0]["operation_families"] == [
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ]
    assert "triton_jit_execution" in payload["blocked_execution_surfaces"]
    assert "compute_graph" in payload["blocked_compiler_outputs"]


def test_next_syntax_report_matches_golden() -> None:
    assert next_syntax_example.build_report() == REPORT_GOLDEN.read_text(
        encoding="utf-8"
    )


def test_next_syntax_source_intent_golden_matches_and_validates() -> None:
    text = next_syntax_example.build_source_intent_golden()
    payload = json.loads(text)
    module = source_intent_from_mapping(payload)

    assert text == SOURCE_INTENT_GOLDEN.read_text(encoding="utf-8")
    assert payload["schema_version"] == SOURCE_INTENT_SCHEMA_VERSION
    assert module.contract == SOURCE_INTENT_IR_CONTRACT
    assert source_intent_payload_digest(payload) == json.loads(
        REPORT_GOLDEN.read_text(encoding="utf-8")
    )["cases"][0]["source_intent_payload_digest"]


def test_next_syntax_examples_run() -> None:
    report_completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_next_syntax_slice.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    source_intent_completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_next_syntax_slice.py",
            "--source-intent",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert report_completed.stdout == REPORT_GOLDEN.read_text(encoding="utf-8")
    assert source_intent_completed.stdout == SOURCE_INTENT_GOLDEN.read_text(
        encoding="utf-8"
    )
    for text in (report_completed.stdout, source_intent_completed.stdout):
        assert "@triton.jit" not in text
        assert "tl.dot" not in text
        assert "tl.store" not in text
        assert "python_source" not in text
        assert "runtime_handle" not in text


def test_next_syntax_report_omits_raw_source_and_runtime_artifacts() -> None:
    encoded = next_syntax_example.build_report()

    assert "raw_source_text" not in encoded
    assert "source_text" not in encoded
    assert "generated_code" not in encoded
    assert "device_id" not in encoded
    assert "plugin_entrypoint" not in encoded
    assert "runtime_handle" not in encoded


def test_next_syntax_rejects_nonterminal_return_mapping() -> None:
    bad_source = """@triton.jit
def bad_nonterminal_return(q, k, y):
    scores = tl.dot(q, k)
    activated = tl.where(scores > 0.0, scores, 0.0)
    tl.store(y, scores)
"""

    with pytest.raises(SourceToIntentResearchParserError, match="terminal"):
        parse_triton_source_to_source_intent(
            bad_source,
            source_name="bad_nonterminal_return",
            tensor_shapes={"k": (8, 4), "q": (4, 8), "y": (4, 4)},
        )


def test_next_syntax_rejects_incomplete_property_coverage() -> None:
    report = next_syntax_example.build_next_syntax_report()

    with pytest.raises(ValueError, match="property coverage incomplete"):
        SourceToIntentNextSyntaxReport(
            cases=report.cases,
            properties=report.properties[:-1],
        )


def test_next_syntax_rejects_duplicate_payload_digests() -> None:
    report = next_syntax_example.build_next_syntax_report()
    case = report.cases[0]
    duplicate = replace(case, case_id="same_payload_other_case")

    with pytest.raises(ValueError, match="payload digests must be unique"):
        build_source_to_intent_next_syntax_report((case, duplicate))


@given(st.text(min_size=1, max_size=64))
@settings(max_examples=80, deadline=None)
def test_next_syntax_case_ids_fail_closed_for_non_report_safe_text(
    case_id: str,
) -> None:
    assume(not SAFE_TEXT_RE.fullmatch(case_id) or case_id == "python_source")
    good_case = next_syntax_example.build_next_syntax_report().cases[0]

    with pytest.raises(ValueError, match="report-safe text"):
        SourceToIntentNextSyntaxCase(
            case_id=case_id,
            source_name=good_case.source_name,
            source_digest=good_case.source_digest,
            source_bytes=good_case.source_bytes,
            syntax_features=good_case.syntax_features,
            operation_families=good_case.operation_families,
            tensor_count=good_case.tensor_count,
            operation_count=good_case.operation_count,
            return_count=good_case.return_count,
            source_intent_payload_digest=good_case.source_intent_payload_digest,
        )


def test_next_syntax_schema_matches_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["mapping_contract"]["const"] == (
        SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT
    )
    assert schema["properties"]["direct_source_ingestion"]["const"] is False
    assert schema["properties"]["triton_jit_execution"]["const"] is False
    assert schema["properties"]["property_coverage_complete"]["const"] is True
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert schema["$defs"]["property"]["additionalProperties"] is False


def test_next_syntax_golden_matches_schema_shape() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    golden = json.loads(REPORT_GOLDEN.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["direct_source_ingestion"] is False
    assert golden["triton_jit_execution"] is False
    assert golden["property_coverage_complete"] is True


def test_next_syntax_is_documented() -> None:
    schema_path = "schemas/source_to_intent_next_syntax_report.v0.schema.json"
    example_path = "examples/source_to_intent_next_syntax_slice.py"
    doc_path = "docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md"

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE.md"),
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0242-source-to-intent-next-syntax-slice.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("rfcs/0242-source-to-intent-next-syntax-slice.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")


def test_next_syntax_property_ids_are_fixed_and_sorted() -> None:
    assert tuple(
        sorted(SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES)
    ) == SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES
    assert tuple(
        item.property_id
        for item in next_syntax_example.build_next_syntax_report().properties
    ) == SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES

    with pytest.raises(ValueError, match="property unsupported"):
        SourceToIntentNextSyntaxProperty("not_a_property")
