from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.source_ingestion_admission_gate import (
    SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION,
    SourceIngestionAdmissionGateReportError,
    assert_source_ingestion_admission_gate_report_contract,
    build_report,
    build_source_ingestion_admission_gate_report_payload,
)
from tuc.frontend.source_ingestion_admission_gate import (
    SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS,
    SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS,
    SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
    SOURCE_INGESTION_ADMISSION_GATE_DECISION,
    SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY,
    SOURCE_INGESTION_ADMISSION_GATE_ID,
    SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS,
    SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_ADMISSION_GATE_STATUS,
    SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE,
    SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE,
)

SCHEMA_PATH = Path("schemas/source_ingestion_admission_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/source_ingestion_admission_gate_report.json")
DOC_PATH = Path("docs/SOURCE_INGESTION_ADMISSION_GATE.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_source_ingestion_admission_gate_report_payload()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_source_ingestion_admission_gate_passes() -> None:
    report = _cached_report()

    assert_source_ingestion_admission_gate_report_contract(report)
    assert report["schema_version"] == SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION
    assert report["gate_id"] == SOURCE_INGESTION_ADMISSION_GATE_ID
    assert report["gate_contract"] == SOURCE_INGESTION_ADMISSION_GATE_CONTRACT
    assert report["gate_status"] == SOURCE_INGESTION_ADMISSION_GATE_STATUS
    assert report["admission_status"] == SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS
    assert report["approval_status"] == SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS
    assert report["approval_required"] is True
    assert report["approval_artifact_present"] is False
    assert report["admitted"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["direct_source_ingestion"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["target_surface"] == SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE
    assert report["target_slice"] == SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE
    assert report["decision"] == SOURCE_INGESTION_ADMISSION_GATE_DECISION
    assert report["evidence_policy"] == SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY
    assert report["required_external_evidence"] == list(
        SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE
    )
    assert report["required_controls"] == list(
        SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS
    )
    assert report["blocked_execution_surfaces"] == list(
        SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES
    )
    approval = report["maintainer_approval_artifact"]
    assert isinstance(approval, dict)
    assert approval["evidence_id"] == "source_ingestion_maintainer_approval_artifact"
    assert approval["status"] == "external_approval_not_supplied"
    assert approval["source_free"] is True
    assert approval["supports_gate"] is True
    packet = report["maintainer_review_packet"]
    assert isinstance(packet, dict)
    assert packet["evidence_id"] == "source_ingestion_maintainer_security_review_packet"
    assert packet["status"] == "ready_for_maintainer_review"
    assert packet["source_free"] is True
    assert packet["supports_gate"] is True
    assert report["issues"] == []


def test_source_ingestion_admission_gate_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_ingestion_admission_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_ingestion_admission_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "blocked_missing_maintainer_security_review_approval"' in (
        completed.stdout
    )
    assert '"admitted": false' in completed.stdout
    assert '"approval_artifact_present": false' in completed.stdout
    assert '"maintainer_approval_artifact"' in completed.stdout
    assert '"external_approval_not_supplied"' in completed.stdout
    assert '"source_ingestion_admission_ready": false' in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("admitted", True, "admitted"),
        ("approval_artifact_present", True, "approval_artifact_present"),
        ("approval_status", "approved", "approval_status"),
        ("source_ingestion_admission_ready", True, "source_ingestion_admission_ready"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_to_hac_ir", True, "source_to_hac_ir"),
        ("required_external_evidence_count", 0, "required_external_evidence_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_source_ingestion_admission_gate_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(SourceIngestionAdmissionGateReportError, match=match):
        assert_source_ingestion_admission_gate_report_contract(report)


def test_source_ingestion_admission_gate_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["gate_report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(SourceIngestionAdmissionGateReportError, match="digest drift"):
        assert_source_ingestion_admission_gate_report_contract(report)


def test_source_ingestion_admission_gate_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(SourceIngestionAdmissionGateReportError, match="top-level keys"):
        assert_source_ingestion_admission_gate_report_contract(report)


def test_source_ingestion_admission_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_id"]["const"] == SOURCE_INGESTION_ADMISSION_GATE_ID
    assert schema["properties"]["gate_contract"]["const"] == (
        SOURCE_INGESTION_ADMISSION_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        SOURCE_INGESTION_ADMISSION_GATE_STATUS
    )
    assert schema["properties"]["approval_artifact_present"]["const"] is False
    assert "maintainer_approval_artifact" in schema["properties"]
    assert schema["properties"]["admitted"]["const"] is False
    assert [
        item["const"]
        for item in schema["properties"]["required_external_evidence"]["prefixItems"]
    ] == list(SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE)


def test_source_ingestion_admission_gate_schema_fails_closed() -> None:
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


def test_source_ingestion_admission_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION
    assert golden["gate_status"] == SOURCE_INGESTION_ADMISSION_GATE_STATUS
    assert golden["admitted"] is False
    assert golden["approval_artifact_present"] is False
    assert golden["source_ingestion_admission_ready"] is False


def test_source_ingestion_admission_gate_is_documented() -> None:
    schema_path = "schemas/source_ingestion_admission_gate_report.v0.schema.json"
    example_path = "examples/source_ingestion_admission_gate.py"
    golden_path = "tests/golden/frontend/source_ingestion_admission_gate_report.json"
    module_path = "src/tuc/frontend/source_ingestion_admission_gate.py"
    approval_doc_path = "docs/SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT.md"
    approval_example_path = "examples/source_ingestion_maintainer_approval_artifact.py"
    approval_schema_path = (
        "schemas/source_ingestion_maintainer_approval_artifact_report.v0.schema.json"
    )
    doc_path = "docs/SOURCE_INGESTION_ADMISSION_GATE.md"
    rfc_path = "rfcs/0266-source-ingestion-admission-gate.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_INGESTION_MAINTAINER_SECURITY_REVIEW_PACKET.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
        assert approval_doc_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert approval_example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert approval_schema_path in text or path.name in {"README.md", "ROADMAP.md"}
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
