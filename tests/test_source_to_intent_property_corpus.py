from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_corpus import build_source_to_intent_corpus_cases
from tuc.frontend import (
    SOURCE_TO_INTENT_CORPUS_CONTRACT,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_CATEGORIES,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES,
    SourceToIntentPropertyCorpusReport,
    SourceToIntentPropertyRequirement,
    build_source_to_intent_corpus_report,
    build_source_to_intent_property_corpus_report,
    dump_source_to_intent_property_corpus_report,
    source_to_intent_property_corpus_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_property_corpus_report.json"
)


def test_source_to_intent_property_corpus_binds_source_corpus() -> None:
    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    report = build_source_to_intent_property_corpus_report(source_corpus)

    assert report.property_contract == SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT
    assert report.raw_source_policy == SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY
    assert report.source_corpus_contract == SOURCE_TO_INTENT_CORPUS_CONTRACT
    assert report.source_corpus_case_count == 6
    assert report.accepted_source_case_count == 2
    assert report.rejected_source_case_count == 4
    assert report.source_corpus_digest.startswith("sha256:")
    assert report.property_count == len(SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES)
    assert tuple(item.property_id for item in report.properties) == (
        SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES
    )
    assert report.required_property_coverage_complete
    assert set(report.categories) == SOURCE_TO_INTENT_PROPERTY_CORPUS_CATEGORIES


def test_source_to_intent_property_corpus_dump_matches_golden() -> None:
    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    report = build_source_to_intent_property_corpus_report(source_corpus)

    assert dump_source_to_intent_property_corpus_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_source_to_intent_property_corpus_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_property_corpus.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"required_property_coverage_complete": true' in completed.stdout
    assert "arbitrary_decoded_bytes_fail_closed" in completed.stdout
    assert "triton_jit_execution" in completed.stdout
    assert '"source_text"' not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_source_to_intent_property_corpus_report_omits_source_text() -> None:
    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    payload = source_to_intent_property_corpus_report_to_dict(
        build_source_to_intent_property_corpus_report(source_corpus)
    )
    encoded = str(payload)

    assert payload["schema_version"] == (
        SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_SCHEMA_VERSION
    )
    assert payload["raw_source_policy"] == SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY
    assert "source_corpus_digest" in payload
    assert "@triton.jit" not in encoded
    assert "tl.dot" not in encoded
    assert "cuda" not in encoded


def test_source_to_intent_property_corpus_rejects_missing_required_property() -> None:
    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )

    with pytest.raises(ValueError, match="property count mismatch"):
        build_source_to_intent_property_corpus_report(
            source_corpus,
            (
                SourceToIntentPropertyRequirement(
                    property_id="accepted_corpus_emits_only_source_intent_plain_data",
                    category="artifact_boundary",
                    expectation="accepted_source_may_emit_only_source_intent_plain_data",
                ),
            ),
        )


def test_source_to_intent_property_corpus_rejects_unknown_category() -> None:
    with pytest.raises(ValueError, match="category unsupported"):
        SourceToIntentPropertyRequirement(
            property_id="bad_property",
            category="python_execution",
            expectation="must_not_exist",
        )


def test_source_to_intent_property_corpus_rejects_source_corpus_count_mismatch() -> None:
    source_corpus = build_source_to_intent_corpus_report(
        build_source_to_intent_corpus_cases()
    )
    report = build_source_to_intent_property_corpus_report(source_corpus)

    with pytest.raises(ValueError, match="counts must add up"):
        SourceToIntentPropertyCorpusReport(
            proposal_name=report.proposal_name,
            source_corpus_contract=report.source_corpus_contract,
            source_corpus_digest=report.source_corpus_digest,
            source_corpus_case_count=99,
            accepted_source_case_count=report.accepted_source_case_count,
            rejected_source_case_count=report.rejected_source_case_count,
            properties=report.properties,
        )
