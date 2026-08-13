from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.package_import_sandbox_gate import (
    build_current_package_import_sandbox_report,
)
from examples.package_import_sandbox_gate import build_report as build_example_report
from tuc.frontend import (
    PACKAGE_IMPORT_SANDBOX_ADMISSION_EFFECT,
    PACKAGE_IMPORT_SANDBOX_BLOCKED_EXECUTION_SURFACES,
    PACKAGE_IMPORT_SANDBOX_BLOCKED_OUTPUTS,
    PACKAGE_IMPORT_SANDBOX_EVIDENCE_POLICY,
    PACKAGE_IMPORT_SANDBOX_GATE_ARTIFACT_STATUS,
    PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT,
    PACKAGE_IMPORT_SANDBOX_GATE_ID,
    PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION,
    PACKAGE_IMPORT_SANDBOX_GATE_STATUS,
    PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS,
    PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE,
    PACKAGE_IMPORT_SANDBOX_SURFACE_ID,
    PackageImportSandboxEvidence,
    PackageImportSandboxReport,
    build_package_import_sandbox_report,
    package_import_sandbox_report_to_dict,
)

SCHEMA_PATH = Path("schemas/package_import_sandbox_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/package_import_sandbox_gate_report.json")


def test_package_import_sandbox_gate_establishes_boundary_without_import() -> None:
    report = build_current_package_import_sandbox_report()
    payload = package_import_sandbox_report_to_dict(report)

    assert payload["schema_version"] == PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == PACKAGE_IMPORT_SANDBOX_GATE_ARTIFACT_STATUS
    assert payload["gate_contract"] == PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT
    assert payload["gate_id"] == PACKAGE_IMPORT_SANDBOX_GATE_ID
    assert payload["surface_id"] == PACKAGE_IMPORT_SANDBOX_SURFACE_ID
    assert payload["gate_status"] == PACKAGE_IMPORT_SANDBOX_GATE_STATUS
    assert payload["admission_effect"] == PACKAGE_IMPORT_SANDBOX_ADMISSION_EFFECT
    assert payload["evidence_policy"] == PACKAGE_IMPORT_SANDBOX_EVIDENCE_POLICY
    assert payload["sandbox_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 4
    assert payload["required_control_count"] == 16
    assert payload["required_evidence_ids"] == list(
        PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(PACKAGE_IMPORT_SANDBOX_REQUIRED_CONTROLS)
    assert payload["blocked_execution_surfaces"] == list(
        PACKAGE_IMPORT_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(PACKAGE_IMPORT_SANDBOX_BLOCKED_OUTPUTS)
    assert payload["frontend_package_import"] is False
    assert payload["python_import"] is False
    assert payload["package_code_execution"] is False
    assert payload["external_package_loaded"] is False
    assert payload["entrypoint_discovery"] is False
    assert payload["plugin_discovery"] is False
    assert payload["network_access"] is False
    assert payload["filesystem_access"] is False
    assert payload["environment_access"] is False
    assert payload["subprocess_execution"] is False
    assert payload["dynamic_library_loading"] is False
    assert payload["source_intent_from_import"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE
    )


def test_package_import_sandbox_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_package_import_sandbox_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/package_import_sandbox_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "sandbox_requirements_only"' in completed.stdout
    assert '"frontend_package_import": false' in completed.stdout
    assert '"python_import": false' in completed.stdout
    assert '"network_access": false' in completed.stdout
    assert "importlib" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_package_import_sandbox_gate_report_omits_sensitive_artifacts() -> None:
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


def test_package_import_sandbox_gate_rejects_missing_evidence() -> None:
    report = build_current_package_import_sandbox_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_package_import_sandbox_report(report.evidence[:-1])


def test_package_import_sandbox_gate_rejects_reordered_evidence() -> None:
    report = build_current_package_import_sandbox_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_package_import_sandbox_report(tuple(reversed(report.evidence)))


def test_package_import_sandbox_gate_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_package_import_sandbox_report(
            (
                PackageImportSandboxEvidence(
                    "external_frontend_package_conformance",
                    digest,
                ),
                PackageImportSandboxEvidence(
                    "package_import_sandbox_model",
                    digest,
                ),
                PackageImportSandboxEvidence(
                    "real_triton_integration_admission_gate",
                    "sha256:" + "1" * 64,
                ),
                PackageImportSandboxEvidence(
                    "source_ingestion_quarantine_gate",
                    "sha256:" + "2" * 64,
                ),
            )
        )


def test_package_import_sandbox_gate_rejects_optional_evidence() -> None:
    report = build_current_package_import_sandbox_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_package_import_sandbox_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        PackageImportSandboxEvidence("../package.py", "sha256:" + "0" * 64)


def test_package_import_sandbox_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        PackageImportSandboxEvidence("python_source", "sha256:" + "0" * 64)


def test_package_import_sandbox_gate_rejects_contract_drift() -> None:
    report = build_current_package_import_sandbox_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        PackageImportSandboxReport(
            evidence=report.evidence,
            gate_contract="package_import_sandbox_gate.import_enabled.v0",
        )


def test_package_import_sandbox_gate_rejects_control_drift() -> None:
    report = build_current_package_import_sandbox_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        PackageImportSandboxReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_package_import_sandbox_gate_rejects_blocked_surface_drift() -> None:
    report = build_current_package_import_sandbox_report()

    with pytest.raises(ValueError, match="blocked_execution_surfaces mismatch"):
        PackageImportSandboxReport(
            evidence=report.evidence,
            blocked_execution_surfaces=tuple(reversed(report.blocked_execution_surfaces)),
        )


def test_package_import_sandbox_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/package_import_sandbox_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        PACKAGE_IMPORT_SANDBOX_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        PACKAGE_IMPORT_SANDBOX_GATE_STATUS
    )
    assert schema["properties"]["frontend_package_import"]["const"] is False
    assert schema["properties"]["python_import"]["const"] is False
    assert schema["properties"]["network_access"]["const"] is False
    assert schema["properties"]["entrypoint_discovery"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 4
    assert schema["properties"]["required_controls"]["maxItems"] == 16


def test_package_import_sandbox_gate_schema_fails_closed() -> None:
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


def test_package_import_sandbox_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == PACKAGE_IMPORT_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    assert golden["gate_status"] == PACKAGE_IMPORT_SANDBOX_GATE_STATUS
    assert golden["frontend_package_import"] is False
    assert golden["python_import"] is False
    assert golden["required_evidence_ids"] == list(
        PACKAGE_IMPORT_SANDBOX_REQUIRED_EVIDENCE
    )


def test_package_import_sandbox_gate_is_documented() -> None:
    schema_path = "schemas/package_import_sandbox_gate_report.v0.schema.json"
    example_path = "examples/package_import_sandbox_gate.py"
    doc_path = "docs/PACKAGE_IMPORT_SANDBOX_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/PACKAGE_IMPORT_SANDBOX_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0246-package-import-sandbox-gate.md"),
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
        Path("rfcs/0246-package-import-sandbox-gate.md"),
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
