from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.device_access_sandbox_gate import (
    build_current_device_access_sandbox_report,
)
from examples.device_access_sandbox_gate import build_report as build_example_report
from tuc.frontend import (
    DEVICE_ACCESS_SANDBOX_ADMISSION_EFFECT,
    DEVICE_ACCESS_SANDBOX_BLOCKED_EXECUTION_SURFACES,
    DEVICE_ACCESS_SANDBOX_BLOCKED_OUTPUTS,
    DEVICE_ACCESS_SANDBOX_EVIDENCE_POLICY,
    DEVICE_ACCESS_SANDBOX_GATE_ARTIFACT_STATUS,
    DEVICE_ACCESS_SANDBOX_GATE_CONTRACT,
    DEVICE_ACCESS_SANDBOX_GATE_ID,
    DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION,
    DEVICE_ACCESS_SANDBOX_GATE_STATUS,
    DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS,
    DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE,
    DEVICE_ACCESS_SANDBOX_SURFACE_ID,
    DeviceAccessSandboxEvidence,
    DeviceAccessSandboxReport,
    build_device_access_sandbox_report,
    device_access_sandbox_report_to_dict,
)

SCHEMA_PATH = Path("schemas/device_access_sandbox_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/device_access_sandbox_gate_report.json")


def test_device_access_sandbox_gate_blocks_device_surfaces() -> None:
    report = build_current_device_access_sandbox_report()
    payload = device_access_sandbox_report_to_dict(report)

    assert payload["schema_version"] == DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == DEVICE_ACCESS_SANDBOX_GATE_ARTIFACT_STATUS
    assert payload["gate_contract"] == DEVICE_ACCESS_SANDBOX_GATE_CONTRACT
    assert payload["gate_id"] == DEVICE_ACCESS_SANDBOX_GATE_ID
    assert payload["surface_id"] == DEVICE_ACCESS_SANDBOX_SURFACE_ID
    assert payload["gate_status"] == DEVICE_ACCESS_SANDBOX_GATE_STATUS
    assert payload["admission_effect"] == DEVICE_ACCESS_SANDBOX_ADMISSION_EFFECT
    assert payload["evidence_policy"] == DEVICE_ACCESS_SANDBOX_EVIDENCE_POLICY
    assert payload["sandbox_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 3
    assert payload["required_control_count"] == 20
    assert payload["required_evidence_ids"] == list(
        DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(DEVICE_ACCESS_SANDBOX_REQUIRED_CONTROLS)
    assert payload["blocked_execution_surfaces"] == list(
        DEVICE_ACCESS_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(DEVICE_ACCESS_SANDBOX_BLOCKED_OUTPUTS)
    assert payload["device_access"] is False
    assert payload["device_discovery"] is False
    assert payload["device_enumeration"] is False
    assert payload["device_handle_emitted"] is False
    assert payload["device_memory_allocation"] is False
    assert payload["device_memory_mapping"] is False
    assert payload["direct_memory_access"] is False
    assert payload["driver_api_call"] is False
    assert payload["hardware_fingerprint_serialized"] is False
    assert payload["kernel_launch"] is False
    assert payload["generated_artifact_execution"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["subprocess_execution"] is False
    assert payload["dynamic_library_loading"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE
    )


def test_device_access_sandbox_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_device_access_sandbox_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/device_access_sandbox_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "sandbox_requirements_only"' in completed.stdout
    assert '"device_access": false' in completed.stdout
    assert '"device_discovery": false' in completed.stdout
    assert '"driver_api_call": false' in completed.stdout
    assert "importlib" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_device_access_sandbox_gate_report_omits_sensitive_artifacts() -> None:
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
    ):
        assert forbidden not in output


def test_device_access_sandbox_gate_rejects_missing_evidence() -> None:
    report = build_current_device_access_sandbox_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_device_access_sandbox_report(report.evidence[:-1])


def test_device_access_sandbox_gate_rejects_reordered_evidence() -> None:
    report = build_current_device_access_sandbox_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_device_access_sandbox_report(tuple(reversed(report.evidence)))


def test_device_access_sandbox_gate_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_device_access_sandbox_report(
            (
                DeviceAccessSandboxEvidence(
                    "real_triton_integration_admission_gate",
                    digest,
                ),
                DeviceAccessSandboxEvidence(
                    "triton_jit_execution_sandbox_gate",
                    digest,
                ),
                DeviceAccessSandboxEvidence(
                    "device_access_sandbox_model",
                    "sha256:" + "1" * 64,
                ),
            )
        )


def test_device_access_sandbox_gate_rejects_optional_evidence() -> None:
    report = build_current_device_access_sandbox_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_device_access_sandbox_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        DeviceAccessSandboxEvidence("../device.py", "sha256:" + "0" * 64)


def test_device_access_sandbox_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        DeviceAccessSandboxEvidence("device_id", "sha256:" + "0" * 64)


def test_device_access_sandbox_gate_rejects_contract_drift() -> None:
    report = build_current_device_access_sandbox_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        DeviceAccessSandboxReport(
            evidence=report.evidence,
            gate_contract="device_access_sandbox_gate.devices_enabled.v0",
        )


def test_device_access_sandbox_gate_rejects_control_drift() -> None:
    report = build_current_device_access_sandbox_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        DeviceAccessSandboxReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_device_access_sandbox_gate_rejects_blocked_surface_drift() -> None:
    report = build_current_device_access_sandbox_report()

    with pytest.raises(ValueError, match="blocked_execution_surfaces mismatch"):
        DeviceAccessSandboxReport(
            evidence=report.evidence,
            blocked_execution_surfaces=tuple(reversed(report.blocked_execution_surfaces)),
        )


def test_device_access_sandbox_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/device_access_sandbox_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        DEVICE_ACCESS_SANDBOX_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        DEVICE_ACCESS_SANDBOX_GATE_STATUS
    )
    assert schema["properties"]["device_access"]["const"] is False
    assert schema["properties"]["device_discovery"]["const"] is False
    assert schema["properties"]["driver_api_call"]["const"] is False
    assert schema["properties"]["kernel_launch"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 3
    assert schema["properties"]["required_controls"]["maxItems"] == 20


def test_device_access_sandbox_gate_schema_fails_closed() -> None:
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
    assert "device_id" in schema["$defs"]["report_text"]["not"]["enum"]


def test_device_access_sandbox_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == DEVICE_ACCESS_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    assert golden["gate_status"] == DEVICE_ACCESS_SANDBOX_GATE_STATUS
    assert golden["device_access"] is False
    assert golden["device_discovery"] is False
    assert golden["required_evidence_ids"] == list(
        DEVICE_ACCESS_SANDBOX_REQUIRED_EVIDENCE
    )


def test_device_access_sandbox_gate_is_documented() -> None:
    schema_path = "schemas/device_access_sandbox_gate_report.v0.schema.json"
    example_path = "examples/device_access_sandbox_gate.py"
    doc_path = "docs/DEVICE_ACCESS_SANDBOX_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md"),
        Path("docs/DEVICE_ACCESS_SANDBOX_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0249-device-access-sandbox-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0249-device-access-sandbox-gate.md"),
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
