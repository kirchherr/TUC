from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.source_ingestion_approval_criteria import (
    SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION,
    SOURCE_INGESTION_APPROVAL_CRITERIA_WORKFLOW_STEP,
    SourceIngestionApprovalCriteriaReportError,
    assert_source_ingestion_approval_criteria_report_contract,
    build_report,
    build_source_ingestion_approval_criteria_report_payload,
)
from tuc.frontend.source_ingestion_approval_criteria import (
    SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS,
    SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS,
    SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT,
    SOURCE_INGESTION_APPROVAL_CRITERIA_ID,
    SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA,
    SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS,
    SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE,
    SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE,
)

SCHEMA_PATH = Path("schemas/source_ingestion_approval_criteria_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/source_ingestion_approval_criteria_report.json"
)
DOC_PATH = Path("docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_source_ingestion_approval_criteria_report_payload()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_source_ingestion_approval_criteria_passes() -> None:
    report = _cached_report()

    assert_source_ingestion_approval_criteria_report_contract(report)
    assert report["schema_version"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION
    )
    assert report["evidence_id"] == SOURCE_INGESTION_APPROVAL_CRITERIA_ID
    assert report["criteria_id"] == SOURCE_INGESTION_APPROVAL_CRITERIA_ID
    assert report["criteria_contract"] == SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT
    assert report["criteria_status"] == SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS
    assert report["approval_status"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS
    )
    assert report["approval_required"] is True
    assert report["approval_artifact_present"] is False
    assert report["criteria_ready"] is True
    assert report["admitted"] is False
    assert report["direct_source_ingestion"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["target_surface"] == SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE
    assert report["target_slice"] == SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE
    assert report["remaining_external_evidence"] == list(
        SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE
    )
    assert report["required_criteria"] == list(
        SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA
    )
    assert report["blocked_claims"] == list(
        SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS
    )
    assert report["blocked_execution_surfaces"] == list(
        SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES
    )
    assert report["execution_permission"] == "not_granted"
    assert report["issues"] == []


def test_source_ingestion_approval_criteria_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_ingestion_approval_criteria_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_ingestion_approval_criteria.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"criteria_status": "criteria_defined_not_approved"' in completed.stdout
    assert '"approval_status": "not_approved"' in completed.stdout
    assert '"admitted": false' in completed.stdout
    assert '"source_ingestion_admission_ready": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


def test_source_ingestion_approval_criteria_is_bound_in_workflow() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert SOURCE_INGESTION_APPROVAL_CRITERIA_WORKFLOW_STEP in workflow


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("criteria_status", "approved", "criteria_status"),
        ("approval_status", "approved", "approval_status"),
        ("approval_artifact_present", True, "approval_artifact_present"),
        ("admitted", True, "admitted"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_to_compute_graph", True, "source_to_compute_graph"),
        ("execution_permission", "granted", "execution_permission"),
        ("remaining_external_evidence_count", 0, "remaining_external_evidence_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_source_ingestion_approval_criteria_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(SourceIngestionApprovalCriteriaReportError, match=match):
        assert_source_ingestion_approval_criteria_report_contract(report)


def test_source_ingestion_approval_criteria_rejects_criteria_order_drift() -> None:
    report = dict(_cached_report())
    criteria = list(report["required_criteria"])
    criteria[0], criteria[1] = criteria[1], criteria[0]
    report["required_criteria"] = criteria

    with pytest.raises(SourceIngestionApprovalCriteriaReportError, match="criteria"):
        assert_source_ingestion_approval_criteria_report_contract(report)


def test_source_ingestion_approval_criteria_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(SourceIngestionApprovalCriteriaReportError, match="digest drift"):
        assert_source_ingestion_approval_criteria_report_contract(report)


def test_source_ingestion_approval_criteria_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(SourceIngestionApprovalCriteriaReportError, match="top-level"):
        assert_source_ingestion_approval_criteria_report_contract(report)


def test_source_ingestion_approval_criteria_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_id"]["const"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_ID
    )
    assert schema["properties"]["criteria_contract"]["const"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT
    )
    assert schema["properties"]["criteria_status"]["const"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS
    )
    assert schema["properties"]["required_criteria_count"]["const"] == len(
        SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA
    )
    assert [
        item["const"]
        for item in schema["properties"]["required_criteria"]["prefixItems"]
    ] == list(SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA)


def test_source_ingestion_approval_criteria_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
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


def test_source_ingestion_approval_criteria_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION
    )
    assert golden["criteria_status"] == SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS
    assert golden["approval_status"] == "not_approved"
    assert golden["admitted"] is False
    assert golden["source_ingestion_admission_ready"] is False


def test_source_ingestion_approval_criteria_is_documented() -> None:
    schema_path = "schemas/source_ingestion_approval_criteria_report.v0.schema.json"
    example_path = "examples/source_ingestion_approval_criteria.py"
    golden_path = (
        "tests/golden/frontend/source_ingestion_approval_criteria_report.json"
    )
    module_path = "src/tuc/frontend/source_ingestion_approval_criteria.py"
    doc_path = "docs/SOURCE_INGESTION_APPROVAL_CRITERIA.md"
    rfc_path = "rfcs/0268-source-ingestion-approval-criteria.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        Path("docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md"),
        Path("docs/SOURCE_INGESTION_ADMISSION_GATE.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        if path != Path(".github/workflows/ci.yml"):
            assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert doc_path in text or path == DOC_PATH
            assert (
                rfc_path in text
                or path == Path(rfc_path)
                or path.name in {"README.md", "ROADMAP.md"}
            )


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
