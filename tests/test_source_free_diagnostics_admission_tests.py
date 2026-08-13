from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.source_free_diagnostics_admission_tests import (
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION,
    SourceFreeDiagnosticsAdmissionReportError,
    assert_source_free_diagnostics_admission_report_contract,
    build_report,
    build_source_free_diagnostics_admission_tests_report,
)
from tuc.frontend.source_free_diagnostics_admission import (
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE,
    SourceFreeDiagnosticRecord,
    SourceFreeDiagnosticsAdmissionError,
    SourceFreeDiagnosticsAdmissionReport,
    build_source_free_diagnostics_admission_report,
    source_free_diagnostics_admission_report_to_dict,
)

SCHEMA_PATH = Path("schemas/source_free_diagnostics_admission_tests_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/source_free_diagnostics_admission_tests_report.json"
)
DOC_PATH = Path("docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_source_free_diagnostics_admission_tests_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_source_free_diagnostics_admission_builds_records() -> None:
    diagnostics = build_source_free_diagnostics_admission_report()
    payload = source_free_diagnostics_admission_report_to_dict(diagnostics)

    assert diagnostics.diagnostic_count == 8
    assert diagnostics.diagnostics_contract == SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT
    assert diagnostics.diagnostics_status == SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS
    assert diagnostics.target_slice == SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE
    assert diagnostics.artifact_policy == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY
    )
    assert diagnostics.message_policy == SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY
    assert diagnostics.location_policy == SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY
    assert diagnostics.payload_policy == SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY
    assert diagnostics.expected_outcome == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME
    )
    assert diagnostics.diagnostic_class_coverage == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES
    )
    assert diagnostics.reason_code_coverage == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES
    )
    assert diagnostics.message_template_coverage == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS
    )
    assert diagnostics.diagnostic_class_coverage_complete
    assert diagnostics.required_reason_coverage_complete
    assert diagnostics.message_template_coverage_complete
    assert payload["blocked_outputs"] == list(
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS
    )
    assert "source_text" not in json.dumps(payload, sort_keys=True)
    assert '"raw_source":' not in json.dumps(payload, sort_keys=True)


def test_source_free_diagnostics_admission_rejects_incomplete_reason_coverage() -> None:
    diagnostics = build_source_free_diagnostics_admission_report()

    with pytest.raises(SourceFreeDiagnosticsAdmissionError, match="reason coverage"):
        SourceFreeDiagnosticsAdmissionReport(diagnostics=diagnostics.diagnostics[:-1])


def test_source_free_diagnostics_admission_rejects_unsafe_record_text() -> None:
    with pytest.raises(SourceFreeDiagnosticsAdmissionError, match="report-safe"):
        SourceFreeDiagnosticRecord(
            case_id="source_text",
            source_digest="sha256:" + "1" * 64,
            diagnostic_code="TUC_SRC_DIAG_SYNTAX_ERROR",
            diagnostic_class="malformed_syntax",
            reason_code="syntax_error",
            message_template_id="diagnostic.syntax_error",
            expected_outcome=SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME,
            diagnostic_bytes=128,
        )


def test_source_free_diagnostics_admission_report_passes() -> None:
    report = _cached_report()

    assert_source_free_diagnostics_admission_report_contract(report)
    assert report["schema_version"] == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert report["evidence_id"] == SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID
    assert report["diagnostics_contract"] == SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT
    assert report["diagnostics_status"] == SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS
    assert report["target_slice"] == SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE
    assert report["diagnostic_count"] == 8
    assert report["diagnostic_class_coverage_complete"] is True
    assert report["required_reason_coverage_complete"] is True
    assert report["message_template_coverage_complete"] is True
    assert report["required_controls"] == list(
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS
    )
    assert report["blocked_outputs"] == list(
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS
    )
    assert report["blocked_execution_surfaces"] == list(
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES
    )
    assert report["source_to_intent_plain_data"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["issues"] == []


def test_source_free_diagnostics_admission_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_free_diagnostics_admission_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_free_diagnostics_admission_tests.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"diagnostics_status": "complete_non_admitting"' in completed.stdout
    assert '"required_reason_coverage_complete": true' in completed.stdout
    assert '"source_to_intent_plain_data": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import os" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_source":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("diagnostics_status", "admitting", "diagnostics_status"),
        ("source_to_intent_plain_data", True, "source_to_intent_plain_data"),
        ("source_to_hac_ir", True, "source_to_hac_ir"),
        ("diagnostic_count", 0, "diagnostic_count"),
        ("required_reason_coverage_complete", False, "required_reason"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_source_free_diagnostics_admission_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(SourceFreeDiagnosticsAdmissionReportError, match=match):
        assert_source_free_diagnostics_admission_report_contract(report)


def test_source_free_diagnostics_admission_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(SourceFreeDiagnosticsAdmissionReportError, match="digest drift"):
        assert_source_free_diagnostics_admission_report_contract(report)


def test_source_free_diagnostics_admission_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    diagnostics = [dict(item) for item in report["diagnostics"]]  # type: ignore[union-attr]
    diagnostics[0]["source_text"] = "@triton.jit\ndef kernel():\n    pass\n"
    report["diagnostics"] = diagnostics

    with pytest.raises(SourceFreeDiagnosticsAdmissionReportError, match="record keys"):
        assert_source_free_diagnostics_admission_report_contract(report)


def test_source_free_diagnostics_admission_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["diagnostics_contract"]["const"] == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT
    )
    assert schema["properties"]["diagnostics_status"]["const"] == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS
    )
    assert schema["properties"]["source_to_intent_plain_data"]["const"] is False
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS)
    assert [
        item["const"]
        for item in schema["properties"]["reason_code_coverage"]["prefixItems"]
    ] == list(SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES)


def test_source_free_diagnostics_admission_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "command_line",
        "device_id",
        "file_path",
        "generated_code",
        "host_path",
        "line_column_location",
        "plugin_entrypoint",
        "python_source",
        "raw_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_excerpt",
        "source_intent_payload",
        "source_text",
    }
    assert not (set(schema["properties"]) & forbidden_properties)
    assert not (
        set(schema["$defs"]["diagnostic_record"]["properties"])
        & forbidden_properties
    )


def test_source_free_diagnostics_admission_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert golden["diagnostics_status"] == SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS
    assert golden["diagnostic_count"] == 8
    assert golden["source_to_intent_plain_data"] is False


def test_source_free_diagnostics_admission_is_documented() -> None:
    schema_path = "schemas/source_free_diagnostics_admission_tests_report.v0.schema.json"
    example_path = "examples/source_free_diagnostics_admission_tests.py"
    golden_path = (
        "tests/golden/frontend/source_free_diagnostics_admission_tests_report.json"
    )
    doc_path = "docs/SOURCE_FREE_DIAGNOSTICS_ADMISSION_TESTS.md"
    rfc_path = "rfcs/0262-source-free-diagnostics-admission-tests.md"
    module_path = "src/tuc/frontend/source_free_diagnostics_admission.py"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        Path("docs/PARSER_FUZZ_NEGATIVE_CORPUS_FOR_ADMITTING_SLICE.md"),
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
