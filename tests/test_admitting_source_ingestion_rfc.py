from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.admitting_source_ingestion_rfc import (
    ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_INPUTS,
    ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_OUTPUTS,
    ADMITTING_SOURCE_INGESTION_RFC_ARTIFACT_POLICY,
    ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_CLAIMS,
    ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_EXECUTION_SURFACES,
    ADMITTING_SOURCE_INGESTION_RFC_CONTRACT,
    ADMITTING_SOURCE_INGESTION_RFC_DENIED_OUTPUTS,
    ADMITTING_SOURCE_INGESTION_RFC_ID,
    ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS,
    ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_NAME,
    ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_STATUS,
    ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE,
    ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION,
    ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS,
    ADMITTING_SOURCE_INGESTION_RFC_TARGET_SLICE,
    ADMITTING_SOURCE_INGESTION_RFC_TARGET_SURFACE,
    AdmittingSourceIngestionRFCError,
    assert_admitting_source_ingestion_rfc_report_contract,
    build_admitting_source_ingestion_rfc_report,
    build_report,
)

SCHEMA_PATH = Path("schemas/admitting_source_ingestion_rfc_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/admitting_source_ingestion_rfc_report.json")
DOC_PATH = Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_admitting_source_ingestion_rfc_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_admitting_source_ingestion_rfc_passes() -> None:
    report = _cached_report()

    assert_admitting_source_ingestion_rfc_report_contract(report)
    assert report["schema_version"] == ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION
    assert report["rfc_contract"] == ADMITTING_SOURCE_INGESTION_RFC_CONTRACT
    assert report["rfc_id"] == ADMITTING_SOURCE_INGESTION_RFC_ID
    assert report["proposal_name"] == ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_NAME
    assert report["proposal_status"] == ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_STATUS
    assert report["implementation_status"] == (
        ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS
    )
    assert report["admission_status"] == "blocked"
    assert report["admitted"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["target_surface"] == ADMITTING_SOURCE_INGESTION_RFC_TARGET_SURFACE
    assert report["target_slice"] == ADMITTING_SOURCE_INGESTION_RFC_TARGET_SLICE
    assert report["artifact_policy"] == ADMITTING_SOURCE_INGESTION_RFC_ARTIFACT_POLICY
    assert report["allowed_inputs"] == list(ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_INPUTS)
    assert report["allowed_outputs"] == list(ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_OUTPUTS)
    assert report["denied_outputs"] == list(ADMITTING_SOURCE_INGESTION_RFC_DENIED_OUTPUTS)
    assert report["remaining_evidence"] == list(
        ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE
    )
    assert report["remaining_evidence_count"] == len(
        ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE
    )
    assert report["required_controls"] == list(
        ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS
    )
    assert report["required_controls_count"] == len(
        ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS
    )
    assert report["blocked_execution_surfaces"] == list(
        ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_EXECUTION_SURFACES
    )
    assert report["blocked_claims"] == list(ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_CLAIMS)
    assert report["issues"] == []
    assert len(str(report["rfc_digest"])) == 71


def test_admitting_source_ingestion_rfc_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_admitting_source_ingestion_rfc_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/admitting_source_ingestion_rfc.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"admitted": false' in completed.stdout
    assert '"implementation_status": "not_implemented"' in completed.stdout
    assert '"source_ingestion_admission_ready": false' in completed.stdout
    assert "source_free_diagnostics_admission_tests" in completed.stdout
    assert "parser_fuzz_negative_corpus_for_admitting_slice" not in completed.stdout
    assert "source_ingestion_sandbox_implementation" not in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("admitted", True, "admitted"),
        ("source_ingestion_admission_ready", True, "source_ingestion_admission_ready"),
        ("implementation_status", "implemented", "implementation_status"),
        ("proposal_status", "accepted_for_execution", "proposal_status"),
        ("remaining_evidence_count", 0, "remaining_evidence_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_admitting_source_ingestion_rfc_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(AdmittingSourceIngestionRFCError, match=match):
        assert_admitting_source_ingestion_rfc_report_contract(report)


def test_admitting_source_ingestion_rfc_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["rfc_digest"] = "sha256:" + "0" * 64

    with pytest.raises(AdmittingSourceIngestionRFCError, match="digest drift"):
        assert_admitting_source_ingestion_rfc_report_contract(report)


def test_admitting_source_ingestion_rfc_rejects_denied_output_drift() -> None:
    report = dict(_cached_report())
    report["denied_outputs"] = ["source_text"]

    with pytest.raises(AdmittingSourceIngestionRFCError, match="report-safe"):
        assert_admitting_source_ingestion_rfc_report_contract(report)


def test_admitting_source_ingestion_rfc_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["rfc_contract"]["const"] == (
        ADMITTING_SOURCE_INGESTION_RFC_CONTRACT
    )
    assert schema["properties"]["rfc_id"]["const"] == ADMITTING_SOURCE_INGESTION_RFC_ID
    assert schema["properties"]["proposal_status"]["const"] == (
        ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_STATUS
    )
    assert schema["properties"]["implementation_status"]["const"] == (
        ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS
    )
    assert schema["properties"]["admitted"]["const"] is False
    assert schema["properties"]["source_ingestion_admission_ready"]["const"] is False
    assert [
        item["const"] for item in schema["properties"]["remaining_evidence"]["prefixItems"]
    ] == list(ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE)
    assert [
        item["const"] for item in schema["properties"]["denied_outputs"]["prefixItems"]
    ] == list(ADMITTING_SOURCE_INGESTION_RFC_DENIED_OUTPUTS)


def test_admitting_source_ingestion_rfc_schema_fails_closed() -> None:
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
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
    }
    assert not (set(schema["properties"]) & forbidden_properties)


def test_admitting_source_ingestion_rfc_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION
    assert golden["admitted"] is False
    assert golden["implementation_status"] == ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS
    assert golden["source_ingestion_admission_ready"] is False


def test_admitting_source_ingestion_rfc_is_documented() -> None:
    schema_path = "schemas/admitting_source_ingestion_rfc_report.v0.schema.json"
    example_path = "examples/admitting_source_ingestion_rfc.py"
    golden_path = "tests/golden/frontend/admitting_source_ingestion_rfc_report.json"
    doc_path = "docs/ADMITTING_SOURCE_INGESTION_RFC.md"
    rfc_path = "rfcs/0258-admitting-source-ingestion-rfc.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
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
