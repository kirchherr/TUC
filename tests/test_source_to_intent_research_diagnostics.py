from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.source_to_intent_research_diagnostics import (
    build_source_to_intent_research_diagnostic_cases,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS,
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchDiagnosticCase,
    SourceToIntentResearchDiagnosticResult,
    SourceToIntentResearchDiagnosticsReport,
    build_source_to_intent_research_diagnostics_report,
    dump_source_to_intent_research_diagnostics_report,
    source_to_intent_research_diagnostics_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_diagnostics_report.json"
)
SCHEMA_PATH = Path("schemas/source_to_intent_research_diagnostics_report.v0.schema.json")


def test_research_diagnostics_report_tracks_accepted_and_rejected_cases() -> None:
    report = build_source_to_intent_research_diagnostics_report(
        build_source_to_intent_research_diagnostic_cases()
    )

    assert report.diagnostics_contract == SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT
    assert report.parser_contract == SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    assert report.parser_status == SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    assert report.default_parser_status == SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    assert report.output_policy == SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    assert report.raw_source_policy == SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY
    assert report.accepted_case_count == 2
    assert report.rejected_case_count == 4
    assert report.rejection_reasons == tuple(
        sorted(SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS)
    )
    assert tuple(case.case_id for case in report.cases) == (
        "accepted_matmul_elementwise",
        "accepted_softmax_reduction",
        "reject_ambiguous_softmax_axis",
        "reject_decorator_call",
        "reject_hardware_hint",
        "reject_import_escape",
    )


def test_research_diagnostics_dump_matches_golden() -> None:
    report = build_source_to_intent_research_diagnostics_report(
        build_source_to_intent_research_diagnostic_cases()
    )

    assert dump_source_to_intent_research_diagnostics_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_research_diagnostics_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_diagnostics.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"raw_source_policy": "omitted_by_policy"' in completed.stdout
    assert '"missing_axis_keyword"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "cuda" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_research_diagnostics_report_omits_source_and_compiler_artifacts() -> None:
    payload = source_to_intent_research_diagnostics_report_to_dict(
        build_source_to_intent_research_diagnostics_report(
            build_source_to_intent_research_diagnostic_cases()
        )
    )
    encoded = str(payload)

    assert payload["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_SCHEMA_VERSION
    )
    assert "source" not in payload["cases"][0]
    assert "@triton.jit" not in encoded
    assert "tl.store" not in encoded
    assert "cuda" not in encoded
    assert "source_intent_payload" not in encoded
    assert "compute_graph" in payload["blocked_compiler_outputs"]


def test_research_diagnostics_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["diagnostics_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT
    )
    assert schema["properties"]["raw_source_policy"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY
    )
    assert set(schema["properties"]["rejection_reasons"]["items"]["enum"]) == set(
        SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False


def test_research_diagnostics_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_diagnostics.py"
    doc_path = "docs/SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PARSER.md"),
        Path("rfcs/0158-source-to-intent-research-diagnostics.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("rfcs/0158-source-to-intent-research-diagnostics.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
    for path in (
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PARSER.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PARSER_CONFORMANCE_GATE.md"),
    ):
        assert Path(doc_path).name in path.read_text(encoding="utf-8")


def test_research_diagnostics_rejects_unexpected_acceptance() -> None:
    accepted = build_source_to_intent_research_diagnostic_cases()[0]
    tampered = SourceToIntentResearchDiagnosticCase(
        case_id="accepted_marked_rejected",
        expectation="rejected",
        source=accepted.source,
        source_name=accepted.source_name,
        tensor_shapes=accepted.tensor_shapes,
        expected_rejection_reason="missing_axis_keyword",
    )

    with pytest.raises(ValueError, match="unexpectedly accepted"):
        build_source_to_intent_research_diagnostics_report((tampered,))


def test_research_diagnostics_rejects_reason_mismatch() -> None:
    rejected = build_source_to_intent_research_diagnostic_cases()[2]
    tampered = replace(
        rejected,
        expected_rejection_reason="preflight_import_statement",
    )

    with pytest.raises(ValueError, match="reason mismatch"):
        build_source_to_intent_research_diagnostics_report((tampered,))


def test_research_diagnostics_report_rejects_malformed_cases() -> None:
    accepted = build_source_to_intent_research_diagnostics_report(
        build_source_to_intent_research_diagnostic_cases()
    ).cases[0]

    with pytest.raises(ValueError, match="must not reject"):
        SourceToIntentResearchDiagnosticResult(
            case_id="bad_accepted",
            expectation="accepted",
            outcome="accepted",
            source_name="bad_accepted",
            source_bytes=1,
            source_digest="sha256:" + ("0" * 64),
            parser_report_digest="sha256:" + ("1" * 64),
            rejection_reason="missing_axis_keyword",
        )
    with pytest.raises(ValueError, match="case IDs must be unique"):
        SourceToIntentResearchDiagnosticsReport(cases=(accepted, accepted))
