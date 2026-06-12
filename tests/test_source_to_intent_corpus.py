from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples import source_to_intent_corpus as corpus_example
from tuc.frontend import (
    SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_CORPUS_CONTRACT,
    SOURCE_TO_INTENT_CORPUS_OPERATION_FAMILIES,
    SOURCE_TO_INTENT_CORPUS_REPORT_SCHEMA_VERSION,
    SourceToIntentCorpusCase,
    SourceToIntentCorpusReport,
    build_source_to_intent_corpus_report,
    dump_source_to_intent_corpus_report,
    preflight_triton_source,
    source_to_intent_corpus_case_from_source,
    source_to_intent_corpus_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/frontend/source_to_intent_corpus_report.json")
CORPUS_DIR = Path("tests/corpus/source_to_intent_parser")
EXPECTED_CASE_FILES = {
    "accepted_matmul_elementwise": (
        CORPUS_DIR / "accepted" / "accepted_matmul_elementwise.tucsrc",
        corpus_example.ACCEPTED_MATMUL_ELEMENTWISE_SOURCE,
    ),
    "accepted_softmax_reduction": (
        CORPUS_DIR / "accepted" / "accepted_softmax_reduction.tucsrc",
        corpus_example.ACCEPTED_SOFTMAX_REDUCTION_SOURCE,
    ),
    "reject_ambiguous_softmax_axis": (
        CORPUS_DIR / "rejected" / "reject_ambiguous_softmax_axis.tucsrc",
        corpus_example.REJECT_AMBIGUOUS_SOFTMAX_AXIS_SOURCE,
    ),
    "reject_decorator_call": (
        CORPUS_DIR / "rejected" / "reject_decorator_call.tucsrc",
        corpus_example.REJECT_DECORATOR_CALL_SOURCE,
    ),
    "reject_hardware_hint": (
        CORPUS_DIR / "rejected" / "reject_hardware_hint.tucsrc",
        corpus_example.REJECT_HARDWARE_HINT_SOURCE,
    ),
    "reject_import_escape": (
        CORPUS_DIR / "rejected" / "reject_import_escape.tucsrc",
        corpus_example.REJECT_IMPORT_ESCAPE_SOURCE,
    ),
}


def test_source_to_intent_corpus_report_tracks_accepted_and_rejected_cases() -> None:
    report = build_source_to_intent_corpus_report(
        corpus_example.build_source_to_intent_corpus_cases()
    )

    assert report.corpus_contract == SOURCE_TO_INTENT_CORPUS_CONTRACT
    assert report.accepted_case_count == 2
    assert report.rejected_case_count == 4
    assert report.operation_family_coverage == tuple(
        sorted(SOURCE_TO_INTENT_CORPUS_OPERATION_FAMILIES)
    )
    assert report.mvp_operation_family_coverage_complete
    assert report.blocked_compiler_outputs == (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
    )
    assert report.blocked_execution_surfaces == (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
    )
    assert tuple(case.case_id for case in report.cases) == tuple(EXPECTED_CASE_FILES)


def test_source_to_intent_corpus_dump_matches_golden() -> None:
    report = build_source_to_intent_corpus_report(
        corpus_example.build_source_to_intent_corpus_cases()
    )

    assert dump_source_to_intent_corpus_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_source_to_intent_corpus_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_corpus.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"mvp_operation_family_coverage_complete": true' in completed.stdout
    assert "source_intent_payload" in completed.stdout
    assert "triton_jit_execution" in completed.stdout
    assert "python_source" not in completed.stdout
    assert "raw_source" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_source_to_intent_corpus_fixtures_match_example_sources() -> None:
    for path, expected_source in EXPECTED_CASE_FILES.values():
        assert path.read_text(encoding="utf-8") == expected_source


def test_source_to_intent_accepted_corpus_passes_preflight() -> None:
    report = build_source_to_intent_corpus_report(
        corpus_example.build_source_to_intent_corpus_cases()
    )
    accepted_cases = {
        case.case_id: case for case in report.cases if case.expectation == "accepted"
    }

    for case_id, (path, _) in EXPECTED_CASE_FILES.items():
        if case_id not in accepted_cases:
            continue
        preflight = preflight_triton_source(
            path.read_text(encoding="utf-8"),
            source_name=case_id,
        )
        assert preflight.accepted
        assert set(preflight.operation_families) <= set(
            accepted_cases[case_id].operation_families
        )


def test_source_to_intent_corpus_report_omits_source_text() -> None:
    payload = source_to_intent_corpus_report_to_dict(
        build_source_to_intent_corpus_report(
            corpus_example.build_source_to_intent_corpus_cases()
        )
    )
    encoded = str(payload)

    assert payload["schema_version"] == SOURCE_TO_INTENT_CORPUS_REPORT_SCHEMA_VERSION
    assert "source" not in payload["cases"][0]
    assert "@triton.jit" not in encoded
    assert "tl.dot" not in encoded
    assert "cuda" not in encoded


def test_source_to_intent_corpus_rejects_raw_source_like_case_id() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        source_to_intent_corpus_case_from_source(
            case_id="@triton.jit",
            expectation="accepted",
            source=corpus_example.ACCEPTED_MATMUL_ELEMENTWISE_SOURCE,
            operation_families=("elementwise", "matmul"),
        )


def test_source_to_intent_corpus_rejects_malformed_cases() -> None:
    with pytest.raises(ValueError, match="accepted corpus cases must not expect"):
        SourceToIntentCorpusCase(
            case_id="bad_accepted",
            expectation="accepted",
            source_bytes=1,
            source_digest="sha256:" + ("0" * 64),
            operation_families=("matmul",),
            expected_rejection_features=("import_statement",),
        )
    with pytest.raises(ValueError, match="must name rejection features"):
        SourceToIntentCorpusCase(
            case_id="bad_rejected",
            expectation="rejected",
            source_bytes=1,
            source_digest="sha256:" + ("1" * 64),
        )
    with pytest.raises(ValueError, match="operation_families must be sorted"):
        source_to_intent_corpus_case_from_source(
            case_id="bad_family_order",
            expectation="accepted",
            source=corpus_example.ACCEPTED_MATMUL_ELEMENTWISE_SOURCE,
            operation_families=("matmul", "elementwise"),
        )


def test_source_to_intent_corpus_report_requires_both_case_classes() -> None:
    accepted_only = corpus_example.build_source_to_intent_corpus_cases()[:2]

    with pytest.raises(ValueError, match="must contain rejected cases"):
        build_source_to_intent_corpus_report(accepted_only)


def test_source_to_intent_corpus_report_rejects_duplicate_digests() -> None:
    case = corpus_example.build_source_to_intent_corpus_cases()[0]

    with pytest.raises(ValueError, match="source digests must be unique"):
        SourceToIntentCorpusReport(
            proposal_name="duplicate_digest",
            cases=(
                case,
                SourceToIntentCorpusCase(
                    case_id="same_source_other_case",
                    expectation="rejected",
                    source_bytes=case.source_bytes,
                    source_digest=case.source_digest,
                    expected_rejection_features=("duplicate_source",),
                ),
            ),
        )
