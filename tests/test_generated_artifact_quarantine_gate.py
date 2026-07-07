from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.generated_artifact_quarantine_gate import (
    build_current_generated_artifact_quarantine_report,
)
from examples.generated_artifact_quarantine_gate import build_report as build_example_report
from tuc.frontend import (
    GENERATED_ARTIFACT_QUARANTINE_ADMISSION_EFFECT,
    GENERATED_ARTIFACT_QUARANTINE_BLOCKED_EXECUTION_SURFACES,
    GENERATED_ARTIFACT_QUARANTINE_BLOCKED_OUTPUTS,
    GENERATED_ARTIFACT_QUARANTINE_EVIDENCE_POLICY,
    GENERATED_ARTIFACT_QUARANTINE_GATE_ARTIFACT_STATUS,
    GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT,
    GENERATED_ARTIFACT_QUARANTINE_GATE_ID,
    GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION,
    GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS,
    GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS,
    GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE,
    GENERATED_ARTIFACT_QUARANTINE_SURFACE_ID,
    GeneratedArtifactQuarantineEvidence,
    GeneratedArtifactQuarantineReport,
    build_generated_artifact_quarantine_report,
    generated_artifact_quarantine_report_to_dict,
)

SCHEMA_PATH = Path(
    "schemas/generated_artifact_quarantine_gate_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/generated_artifact_quarantine_gate_report.json"
)


def test_generated_artifact_quarantine_gate_blocks_artifact_surfaces() -> None:
    report = build_current_generated_artifact_quarantine_report()
    payload = generated_artifact_quarantine_report_to_dict(report)

    assert (
        payload["schema_version"]
        == GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == (
        GENERATED_ARTIFACT_QUARANTINE_GATE_ARTIFACT_STATUS
    )
    assert payload["gate_contract"] == GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT
    assert payload["gate_id"] == GENERATED_ARTIFACT_QUARANTINE_GATE_ID
    assert payload["surface_id"] == GENERATED_ARTIFACT_QUARANTINE_SURFACE_ID
    assert payload["gate_status"] == GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS
    assert payload["admission_effect"] == (
        GENERATED_ARTIFACT_QUARANTINE_ADMISSION_EFFECT
    )
    assert payload["evidence_policy"] == GENERATED_ARTIFACT_QUARANTINE_EVIDENCE_POLICY
    assert payload["quarantine_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 4
    assert payload["required_control_count"] == 20
    assert payload["required_evidence_ids"] == list(
        GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(
        GENERATED_ARTIFACT_QUARANTINE_REQUIRED_CONTROLS
    )
    assert payload["blocked_execution_surfaces"] == list(
        GENERATED_ARTIFACT_QUARANTINE_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(
        GENERATED_ARTIFACT_QUARANTINE_BLOCKED_OUTPUTS
    )
    assert payload["generated_artifact_execution"] is False
    assert payload["generated_artifact_emission"] is False
    assert payload["artifact_write"] is False
    assert payload["artifact_load"] is False
    assert payload["artifact_cache_access"] is False
    assert payload["artifact_provenance_verified"] is False
    assert payload["executable_permission_granted"] is False
    assert payload["backend_binary_emitted"] is False
    assert payload["compiled_kernel_emitted"] is False
    assert payload["file_system_access"] is False
    assert payload["device_access"] is False
    assert payload["kernel_launch"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["subprocess_execution"] is False
    assert payload["dynamic_library_loading"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE
    )


def test_generated_artifact_quarantine_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_generated_artifact_quarantine_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/generated_artifact_quarantine_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "quarantine_requirements_only"' in completed.stdout
    assert '"generated_artifact_execution": false' in completed.stdout
    assert '"executable_permission_granted": false' in completed.stdout
    assert '"artifact_write": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "importlib" not in completed.stdout


def test_generated_artifact_quarantine_gate_report_omits_sensitive_artifacts() -> None:
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
        "backend_artifact",
        "file_path",
    ):
        assert forbidden not in output


def test_generated_artifact_quarantine_gate_rejects_missing_evidence() -> None:
    report = build_current_generated_artifact_quarantine_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_generated_artifact_quarantine_report(report.evidence[:-1])


def test_generated_artifact_quarantine_gate_rejects_reordered_evidence() -> None:
    report = build_current_generated_artifact_quarantine_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_generated_artifact_quarantine_report(tuple(reversed(report.evidence)))


def test_generated_artifact_quarantine_gate_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_generated_artifact_quarantine_report(
            (
                GeneratedArtifactQuarantineEvidence(
                    "real_triton_integration_admission_gate",
                    digest,
                ),
                GeneratedArtifactQuarantineEvidence(
                    "triton_jit_execution_sandbox_gate",
                    digest,
                ),
                GeneratedArtifactQuarantineEvidence(
                    "device_access_sandbox_gate",
                    "sha256:" + "1" * 64,
                ),
                GeneratedArtifactQuarantineEvidence(
                    "generated_artifact_quarantine_model",
                    "sha256:" + "2" * 64,
                ),
            )
        )


def test_generated_artifact_quarantine_gate_rejects_optional_evidence() -> None:
    report = build_current_generated_artifact_quarantine_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_generated_artifact_quarantine_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        GeneratedArtifactQuarantineEvidence("../artifact.bin", "sha256:" + "0" * 64)


def test_generated_artifact_quarantine_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        GeneratedArtifactQuarantineEvidence("generated_code", "sha256:" + "0" * 64)


def test_generated_artifact_quarantine_gate_rejects_contract_drift() -> None:
    report = build_current_generated_artifact_quarantine_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        GeneratedArtifactQuarantineReport(
            evidence=report.evidence,
            gate_contract="generated_artifact_quarantine_gate.execution_enabled.v0",
        )


def test_generated_artifact_quarantine_gate_rejects_control_drift() -> None:
    report = build_current_generated_artifact_quarantine_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        GeneratedArtifactQuarantineReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_generated_artifact_quarantine_gate_rejects_blocked_surface_drift() -> None:
    report = build_current_generated_artifact_quarantine_report()

    with pytest.raises(ValueError, match="blocked_execution_surfaces mismatch"):
        GeneratedArtifactQuarantineReport(
            evidence=report.evidence,
            blocked_execution_surfaces=tuple(reversed(report.blocked_execution_surfaces)),
        )


def test_generated_artifact_quarantine_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/generated_artifact_quarantine_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        GENERATED_ARTIFACT_QUARANTINE_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS
    )
    assert schema["properties"]["generated_artifact_execution"]["const"] is False
    assert schema["properties"]["artifact_write"]["const"] is False
    assert schema["properties"]["executable_permission_granted"]["const"] is False
    assert schema["properties"]["backend_binary_emitted"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 4
    assert schema["properties"]["required_controls"]["maxItems"] == 20


def test_generated_artifact_quarantine_gate_schema_fails_closed() -> None:
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
        "backend_artifact",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["evidence"]["properties"]
    assert "generated_code" in schema["$defs"]["report_text"]["not"]["enum"]


def test_generated_artifact_quarantine_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert (
        golden["schema_version"]
        == GENERATED_ARTIFACT_QUARANTINE_GATE_REPORT_SCHEMA_VERSION
    )
    assert golden["gate_status"] == GENERATED_ARTIFACT_QUARANTINE_GATE_STATUS
    assert golden["generated_artifact_execution"] is False
    assert golden["artifact_write"] is False
    assert golden["required_evidence_ids"] == list(
        GENERATED_ARTIFACT_QUARANTINE_REQUIRED_EVIDENCE
    )


def test_generated_artifact_quarantine_gate_is_documented() -> None:
    schema_path = "schemas/generated_artifact_quarantine_gate_report.v0.schema.json"
    example_path = "examples/generated_artifact_quarantine_gate.py"
    doc_path = "docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/DEVICE_ACCESS_SANDBOX_GATE.md"),
        Path("docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0250-generated-artifact-quarantine-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/DEVICE_ACCESS_SANDBOX_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0250-generated-artifact-quarantine-gate.md"),
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
