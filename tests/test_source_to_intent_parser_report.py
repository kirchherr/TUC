from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_corpus import build_source_to_intent_corpus_cases
from tuc.frontend import (
    SOURCE_TO_INTENT_PARSER_ALLOWED_FUTURE_OUTPUT,
    SOURCE_TO_INTENT_PARSER_IMPLEMENTATION_STATUS,
    SOURCE_TO_INTENT_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_PARSER_REPORT_CONTRACT,
    SOURCE_TO_INTENT_PARSER_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_PARSER_REPORT_STATUS,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY,
    SourceToIntentParserReport,
    build_source_to_intent_corpus_report,
    build_source_to_intent_parser_report,
    build_source_to_intent_property_corpus_report,
    dump_source_to_intent_parser_report,
    source_to_intent_parser_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/frontend/source_to_intent_parser_report.json")


def test_source_to_intent_parser_report_is_proposal_only() -> None:
    report = _build_parser_report()

    assert report.parser_report_contract == SOURCE_TO_INTENT_PARSER_REPORT_CONTRACT
    assert report.parser_status == SOURCE_TO_INTENT_PARSER_REPORT_STATUS
    assert report.implementation_status == SOURCE_TO_INTENT_PARSER_IMPLEMENTATION_STATUS
    assert report.parser_enabled is False
    assert report.parser_output_policy == SOURCE_TO_INTENT_PARSER_OUTPUT_POLICY
    assert report.allowed_future_output == SOURCE_TO_INTENT_PARSER_ALLOWED_FUTURE_OUTPUT
    assert report.raw_source_policy == SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY
    assert report.property_corpus_contract == SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT
    assert report.source_corpus_case_count == 6
    assert report.property_count == 8
    assert report.required_property_coverage_complete
    assert report.source_corpus_digest.startswith("sha256:")
    assert report.property_corpus_digest.startswith("sha256:")


def test_source_to_intent_parser_report_dump_matches_golden() -> None:
    assert dump_source_to_intent_parser_report(_build_parser_report()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_source_to_intent_parser_report_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_parser_report.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"parser_enabled": false' in completed.stdout
    assert '"parser_status": "proposal_only"' in completed.stdout
    assert '"implementation_status": "not_implemented"' in completed.stdout
    assert "source_intent.v0_plain_data_only" in completed.stdout
    assert "source_text" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_source_to_intent_parser_report_payload_shape() -> None:
    payload = source_to_intent_parser_report_to_dict(_build_parser_report())

    assert payload["schema_version"] == SOURCE_TO_INTENT_PARSER_REPORT_SCHEMA_VERSION
    assert payload["parser_enabled"] is False
    assert payload["parser_status"] == "proposal_only"
    assert payload["blocked_compiler_outputs"] == [
        "source_intent_payload",
        "source_intent_module",
        "metadata",
        "compute_graph",
        "tlir",
        "hac_ir",
        "hs_ir",
        "runtime_plan",
        "backend_decision",
    ]


def test_source_to_intent_parser_report_rejects_enabled_parser() -> None:
    report = _build_parser_report()

    with pytest.raises(ValueError, match="must keep parser disabled"):
        SourceToIntentParserReport(
            proposal_name=report.proposal_name,
            source_corpus_contract=report.source_corpus_contract,
            source_corpus_digest=report.source_corpus_digest,
            property_corpus_contract=report.property_corpus_contract,
            property_corpus_digest=report.property_corpus_digest,
            source_corpus_case_count=report.source_corpus_case_count,
            property_count=report.property_count,
            required_property_coverage_complete=(
                report.required_property_coverage_complete
            ),
            parser_enabled=True,
        )


def test_source_to_intent_parser_report_rejects_incomplete_properties() -> None:
    report = _build_parser_report()

    with pytest.raises(ValueError, match="property coverage incomplete"):
        SourceToIntentParserReport(
            proposal_name=report.proposal_name,
            source_corpus_contract=report.source_corpus_contract,
            source_corpus_digest=report.source_corpus_digest,
            property_corpus_contract=report.property_corpus_contract,
            property_corpus_digest=report.property_corpus_digest,
            source_corpus_case_count=report.source_corpus_case_count,
            property_count=report.property_count,
            required_property_coverage_complete=False,
        )


def _build_parser_report() -> SourceToIntentParserReport:
    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    property_corpus = build_source_to_intent_property_corpus_report(source_corpus)
    return build_source_to_intent_parser_report(property_corpus)
