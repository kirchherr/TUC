from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.source_ingestion_quarantine_gate import (
    build_current_source_ingestion_quarantine_report,
)
from examples.source_ingestion_quarantine_gate import (
    build_report as build_example_report,
)
from tuc.frontend import (
    SOURCE_INGESTION_QUARANTINE_ADMISSION_EFFECT,
    SOURCE_INGESTION_QUARANTINE_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_QUARANTINE_BLOCKED_OUTPUTS,
    SOURCE_INGESTION_QUARANTINE_EVIDENCE_POLICY,
    SOURCE_INGESTION_QUARANTINE_GATE_ARTIFACT_STATUS,
    SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT,
    SOURCE_INGESTION_QUARANTINE_GATE_ID,
    SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION,
    SOURCE_INGESTION_QUARANTINE_GATE_STATUS,
    SOURCE_INGESTION_QUARANTINE_REQUIRED_CONTROLS,
    SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE,
    SOURCE_INGESTION_QUARANTINE_SURFACE_ID,
    SourceIngestionQuarantineEvidence,
    SourceIngestionQuarantineReport,
    build_source_ingestion_quarantine_report,
    source_ingestion_quarantine_report_to_dict,
)

SCHEMA_PATH = Path("schemas/source_ingestion_quarantine_gate_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/source_ingestion_quarantine_gate_report.json"
)


def test_source_ingestion_quarantine_gate_establishes_boundary_without_admission() -> None:
    report = build_current_source_ingestion_quarantine_report()
    payload = source_ingestion_quarantine_report_to_dict(report)

    assert payload["schema_version"] == (
        SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == SOURCE_INGESTION_QUARANTINE_GATE_ARTIFACT_STATUS
    assert payload["gate_contract"] == SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT
    assert payload["gate_id"] == SOURCE_INGESTION_QUARANTINE_GATE_ID
    assert payload["surface_id"] == SOURCE_INGESTION_QUARANTINE_SURFACE_ID
    assert payload["gate_status"] == SOURCE_INGESTION_QUARANTINE_GATE_STATUS
    assert payload["admission_effect"] == SOURCE_INGESTION_QUARANTINE_ADMISSION_EFFECT
    assert payload["evidence_policy"] == SOURCE_INGESTION_QUARANTINE_EVIDENCE_POLICY
    assert payload["quarantine_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 4
    assert payload["required_control_count"] == 14
    assert payload["required_evidence_ids"] == list(
        SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(
        SOURCE_INGESTION_QUARANTINE_REQUIRED_CONTROLS
    )
    assert payload["blocked_execution_surfaces"] == list(
        SOURCE_INGESTION_QUARANTINE_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(SOURCE_INGESTION_QUARANTINE_BLOCKED_OUTPUTS)
    assert payload["direct_source_ingestion"] is False
    assert payload["source_to_compute_graph"] is False
    assert payload["source_to_hac_ir"] is False
    assert payload["source_to_runtime_plan"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["python_import"] is False
    assert payload["function_object_inspection"] is False
    assert payload["raw_source_serialization"] is False
    assert payload["generated_artifact_execution"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE
    )


def test_source_ingestion_quarantine_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_ingestion_quarantine_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_ingestion_quarantine_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "quarantine_only"' in completed.stdout
    assert '"direct_source_ingestion": false' in completed.stdout
    assert '"source_to_compute_graph": false' in completed.stdout
    assert '"triton_jit_execution": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout


def test_source_ingestion_quarantine_gate_report_omits_sensitive_artifacts() -> None:
    output = build_example_report()

    for forbidden in (
        "python_source",
        "raw_source_text",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "runtime_handle",
        "raw_timing_samples",
    ):
        assert forbidden not in output


def test_source_ingestion_quarantine_gate_rejects_missing_evidence() -> None:
    report = build_current_source_ingestion_quarantine_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_source_ingestion_quarantine_report(report.evidence[:-1])


def test_source_ingestion_quarantine_gate_rejects_reordered_evidence() -> None:
    report = build_current_source_ingestion_quarantine_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_source_ingestion_quarantine_report(tuple(reversed(report.evidence)))


def test_source_ingestion_quarantine_gate_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_source_ingestion_quarantine_report(
            (
                SourceIngestionQuarantineEvidence(
                    "real_triton_integration_admission_gate",
                    digest,
                ),
                SourceIngestionQuarantineEvidence(
                    "source_to_intent_parser_gate",
                    digest,
                ),
                SourceIngestionQuarantineEvidence(
                    "triton_source_preflight",
                    "sha256:" + "1" * 64,
                ),
                SourceIngestionQuarantineEvidence(
                    "triton_source_threat_model",
                    "sha256:" + "2" * 64,
                ),
            )
        )


def test_source_ingestion_quarantine_gate_rejects_optional_evidence() -> None:
    report = build_current_source_ingestion_quarantine_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_source_ingestion_quarantine_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        SourceIngestionQuarantineEvidence("../source.py", "sha256:" + "0" * 64)


def test_source_ingestion_quarantine_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        SourceIngestionQuarantineEvidence("python_source", "sha256:" + "0" * 64)


def test_source_ingestion_quarantine_gate_rejects_contract_drift() -> None:
    report = build_current_source_ingestion_quarantine_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        SourceIngestionQuarantineReport(
            evidence=report.evidence,
            gate_contract="source_ingestion_quarantine_gate.execution_enabled.v0",
        )


def test_source_ingestion_quarantine_gate_rejects_control_drift() -> None:
    report = build_current_source_ingestion_quarantine_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        SourceIngestionQuarantineReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_source_ingestion_quarantine_gate_rejects_blocked_output_drift() -> None:
    report = build_current_source_ingestion_quarantine_report()

    with pytest.raises(ValueError, match="blocked_outputs mismatch"):
        SourceIngestionQuarantineReport(
            evidence=report.evidence,
            blocked_outputs=tuple(reversed(report.blocked_outputs)),
        )


def test_source_ingestion_quarantine_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/source_ingestion_quarantine_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        SOURCE_INGESTION_QUARANTINE_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        SOURCE_INGESTION_QUARANTINE_GATE_STATUS
    )
    assert schema["properties"]["direct_source_ingestion"]["const"] is False
    assert schema["properties"]["source_to_compute_graph"]["const"] is False
    assert schema["properties"]["source_to_hac_ir"]["const"] is False
    assert schema["properties"]["source_to_runtime_plan"]["const"] is False
    assert schema["properties"]["triton_jit_execution"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 4
    assert schema["properties"]["required_controls"]["maxItems"] == 14


def test_source_ingestion_quarantine_gate_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "raw_timing_samples",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["evidence"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]


def test_source_ingestion_quarantine_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_INGESTION_QUARANTINE_GATE_REPORT_SCHEMA_VERSION
    )
    assert golden["gate_status"] == SOURCE_INGESTION_QUARANTINE_GATE_STATUS
    assert golden["direct_source_ingestion"] is False
    assert golden["source_to_compute_graph"] is False
    assert golden["required_evidence_ids"] == list(
        SOURCE_INGESTION_QUARANTINE_REQUIRED_EVIDENCE
    )


def test_source_ingestion_quarantine_gate_is_documented() -> None:
    schema_path = "schemas/source_ingestion_quarantine_gate_report.v0.schema.json"
    example_path = "examples/source_ingestion_quarantine_gate.py"
    doc_path = "docs/SOURCE_INGESTION_QUARANTINE_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_INGESTION_QUARANTINE_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0245-source-ingestion-quarantine-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0245-source-ingestion-quarantine-gate.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")


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
