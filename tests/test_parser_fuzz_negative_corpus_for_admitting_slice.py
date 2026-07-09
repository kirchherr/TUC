from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
    PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION,
    ParserFuzzNegativeCorpusReportError,
    assert_parser_fuzz_negative_corpus_report_contract,
    build_parser_fuzz_negative_corpus_for_admitting_slice_report,
    build_report,
)
from tuc.frontend.parser_fuzz_negative_corpus import (
    PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY,
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES,
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS,
    PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
    PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME,
    PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES,
    PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY,
    PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES,
    PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS,
    PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
    PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE,
    ParserFuzzNegativeCorpusError,
    ParserFuzzNegativeCorpusSeed,
    build_parser_fuzz_negative_corpus_report,
    default_parser_fuzz_negative_corpus_seeds,
    parser_fuzz_negative_corpus_report_to_dict,
)

SCHEMA_PATH = Path(
    "schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/parser_fuzz_negative_corpus_for_admitting_slice_report.json"
)
DOC_PATH = Path("docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_parser_fuzz_negative_corpus_for_admitting_slice_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_parser_fuzz_negative_corpus_builds_source_free_cases() -> None:
    corpus = build_parser_fuzz_negative_corpus_report(
        default_parser_fuzz_negative_corpus_seeds()
    )
    payload = parser_fuzz_negative_corpus_report_to_dict(corpus)

    assert corpus.case_count == 8
    assert corpus.corpus_contract == PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT
    assert corpus.corpus_status == PARSER_FUZZ_NEGATIVE_CORPUS_STATUS
    assert corpus.target_slice == PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE
    assert corpus.artifact_policy == PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY
    assert corpus.raw_source_policy == PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY
    assert corpus.expected_outcome == PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME
    assert corpus.rejection_category_coverage == (
        PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES
    )
    assert corpus.mutation_family_coverage == (
        PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES
    )
    assert corpus.required_rejection_coverage_complete
    assert corpus.mutation_family_coverage_complete
    assert payload["blocked_outputs"] == list(PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS)
    assert "source_text" not in json.dumps(payload, sort_keys=True)
    assert '"raw_source":' not in json.dumps(payload, sort_keys=True)


def test_parser_fuzz_negative_corpus_rejects_incomplete_category_coverage() -> None:
    seeds = tuple(
        seed
        for seed in default_parser_fuzz_negative_corpus_seeds()
        if seed.expected_rejection_category != "hardware_specific_source"
    )

    with pytest.raises(ParserFuzzNegativeCorpusError, match="coverage incomplete"):
        build_parser_fuzz_negative_corpus_report(seeds)


def test_parser_fuzz_negative_corpus_rejects_unsafe_public_seed_ids() -> None:
    with pytest.raises(ParserFuzzNegativeCorpusError, match="report-safe"):
        ParserFuzzNegativeCorpusSeed(
            case_id="source_text",
            source="x = 1\n",
            declared_shape_profile={"x": (1,)},
            expected_rejection_category="malformed_syntax",
            expected_reason_code="syntax_error",
            mutation_family="syntax_boundary",
        )


def test_parser_fuzz_negative_corpus_report_passes() -> None:
    report = _cached_report()

    assert_parser_fuzz_negative_corpus_report_contract(report)
    assert report["schema_version"] == PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION
    assert report["evidence_id"] == PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID
    assert report["corpus_contract"] == PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT
    assert report["corpus_status"] == PARSER_FUZZ_NEGATIVE_CORPUS_STATUS
    assert report["target_slice"] == PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE
    assert report["case_count"] == 8
    assert report["required_rejection_coverage_complete"] is True
    assert report["mutation_family_coverage_complete"] is True
    assert report["required_controls"] == list(PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS)
    assert report["blocked_outputs"] == list(PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS)
    assert report["blocked_execution_surfaces"] == list(
        PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES
    )
    assert report["source_to_intent_plain_data"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["issues"] == []


def test_parser_fuzz_negative_corpus_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_parser_fuzz_negative_corpus_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/parser_fuzz_negative_corpus_for_admitting_slice.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"corpus_status": "complete_non_admitting"' in completed.stdout
    assert '"required_rejection_coverage_complete": true' in completed.stdout
    assert '"source_to_intent_plain_data": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import os" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_source":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("corpus_status", "admitting", "corpus_status"),
        ("source_to_intent_plain_data", True, "source_to_intent_plain_data"),
        ("source_to_hac_ir", True, "source_to_hac_ir"),
        ("case_count", 0, "case_count"),
        ("required_rejection_coverage_complete", False, "required_rejection"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_parser_fuzz_negative_corpus_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(ParserFuzzNegativeCorpusReportError, match=match):
        assert_parser_fuzz_negative_corpus_report_contract(report)


def test_parser_fuzz_negative_corpus_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(ParserFuzzNegativeCorpusReportError, match="digest drift"):
        assert_parser_fuzz_negative_corpus_report_contract(report)


def test_parser_fuzz_negative_corpus_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    cases = [dict(item) for item in report["cases"]]  # type: ignore[union-attr]
    cases[0]["source_text"] = "@triton.jit\ndef kernel():\n    pass\n"
    report["cases"] = cases

    with pytest.raises(ParserFuzzNegativeCorpusReportError, match="case keys"):
        assert_parser_fuzz_negative_corpus_report_contract(report)


def test_parser_fuzz_negative_corpus_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["corpus_contract"]["const"] == (
        PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT
    )
    assert schema["properties"]["corpus_status"]["const"] == (
        PARSER_FUZZ_NEGATIVE_CORPUS_STATUS
    )
    assert schema["properties"]["source_to_intent_plain_data"]["const"] is False
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS)
    assert [
        item["const"] for item in schema["properties"]["rejection_category_coverage"]["prefixItems"]
    ] == list(PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES)


def test_parser_fuzz_negative_corpus_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "command_line",
        "device_id",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_text",
    }
    assert not (set(schema["properties"]) & forbidden_properties)
    assert not (set(schema["$defs"]["corpus_case"]["properties"]) & forbidden_properties)


def test_parser_fuzz_negative_corpus_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION
    assert golden["corpus_status"] == PARSER_FUZZ_NEGATIVE_CORPUS_STATUS
    assert golden["case_count"] == 8
    assert golden["source_to_intent_plain_data"] is False


def test_parser_fuzz_negative_corpus_is_documented() -> None:
    schema_path = "schemas/parser_fuzz_negative_corpus_for_admitting_slice_report.v0.schema.json"
    example_path = "examples/parser_fuzz_negative_corpus_for_admitting_slice.py"
    golden_path = (
        "tests/golden/frontend/"
        "parser_fuzz_negative_corpus_for_admitting_slice_report.json"
    )
    doc_path = "docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md"
    rfc_path = "rfcs/0261-parser-fuzz-negative-corpus-for-admitting-slice.md"
    module_path = "src/tuc/frontend/parser_fuzz_negative_corpus.py"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        Path("docs/SOURCE_INGESTION_SANDBOX_IMPLEMENTATION.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert doc_path in text or path == DOC_PATH
        assert module_path in text or path.name in {
            "README.md",
            "ROADMAP.md",
            "ROADMAP_STATUS.md",
        }
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert rfc_path in text or path.name in {"README.md", "ROADMAP.md"}


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)