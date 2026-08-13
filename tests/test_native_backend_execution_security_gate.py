from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.native_backend_execution_security_gate import (
    build_current_native_backend_execution_security_report,
)
from examples.native_backend_execution_security_gate import (
    build_report as build_example_report,
)
from tuc.frontend import (
    NATIVE_BACKEND_EXECUTION_SECURITY_ADMISSION_EFFECT,
    NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_EXECUTION_SURFACES,
    NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_OUTPUTS,
    NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE_POLICY,
    NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ARTIFACT_STATUS,
    NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT,
    NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ID,
    NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION,
    NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS,
    NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS,
    NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE,
    NATIVE_BACKEND_EXECUTION_SECURITY_SURFACE_ID,
    NativeBackendExecutionSecurityEvidence,
    NativeBackendExecutionSecurityReport,
    build_native_backend_execution_security_report,
    native_backend_execution_security_report_to_dict,
)

SCHEMA_PATH = Path(
    "schemas/native_backend_execution_security_gate_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/native_backend_execution_security_gate_report.json"
)


def test_native_backend_execution_security_gate_blocks_native_surfaces() -> None:
    report = build_current_native_backend_execution_security_report()
    payload = native_backend_execution_security_report_to_dict(report)

    assert (
        payload["schema_version"]
        == NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == (
        NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ARTIFACT_STATUS
    )
    assert payload["gate_contract"] == NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT
    assert payload["gate_id"] == NATIVE_BACKEND_EXECUTION_SECURITY_GATE_ID
    assert payload["surface_id"] == NATIVE_BACKEND_EXECUTION_SECURITY_SURFACE_ID
    assert payload["gate_status"] == NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS
    assert payload["admission_effect"] == (
        NATIVE_BACKEND_EXECUTION_SECURITY_ADMISSION_EFFECT
    )
    assert payload["evidence_policy"] == NATIVE_BACKEND_EXECUTION_SECURITY_EVIDENCE_POLICY
    assert payload["security_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 5
    assert payload["required_control_count"] == 20
    assert payload["required_evidence_ids"] == list(
        NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(
        NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_CONTROLS
    )
    assert payload["blocked_execution_surfaces"] == list(
        NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(
        NATIVE_BACKEND_EXECUTION_SECURITY_BLOCKED_OUTPUTS
    )
    assert payload["native_backend_execution"] is False
    assert payload["native_backend_loaded"] is False
    assert payload["native_plugin_abi_loading"] is False
    assert payload["backend_plugin_execution"] is False
    assert payload["native_backend_handle_emitted"] is False
    assert payload["symbol_resolution"] is False
    assert payload["ffi_call"] is False
    assert payload["unsafe_memory_access"] is False
    assert payload["dynamic_library_loading"] is False
    assert payload["generated_artifact_execution"] is False
    assert payload["executable_permission_granted"] is False
    assert payload["device_access"] is False
    assert payload["kernel_launch"] is False
    assert payload["subprocess_execution"] is False
    assert payload["capability_claims_from_native_code"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE
    )


def test_native_backend_execution_security_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_native_backend_execution_security_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/native_backend_execution_security_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "security_requirements_only"' in completed.stdout
    assert '"native_backend_execution": false' in completed.stdout
    assert '"native_plugin_abi_loading": false' in completed.stdout
    assert '"ffi_call": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "importlib" not in completed.stdout


def test_native_backend_execution_security_gate_report_omits_sensitive_artifacts() -> None:
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


def test_native_backend_execution_security_gate_rejects_missing_evidence() -> None:
    report = build_current_native_backend_execution_security_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_native_backend_execution_security_report(report.evidence[:-1])


def test_native_backend_execution_security_gate_rejects_reordered_evidence() -> None:
    report = build_current_native_backend_execution_security_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_native_backend_execution_security_report(tuple(reversed(report.evidence)))


def test_native_backend_execution_security_gate_rejects_duplicate_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_native_backend_execution_security_report(
            (
                NativeBackendExecutionSecurityEvidence(
                    "real_triton_integration_admission_gate",
                    digest,
                ),
                NativeBackendExecutionSecurityEvidence(
                    "generated_artifact_quarantine_gate",
                    digest,
                ),
                NativeBackendExecutionSecurityEvidence(
                    "device_access_sandbox_gate",
                    "sha256:" + "1" * 64,
                ),
                NativeBackendExecutionSecurityEvidence(
                    "backend_plugin_lifecycle_policy",
                    "sha256:" + "2" * 64,
                ),
                NativeBackendExecutionSecurityEvidence(
                    "native_backend_execution_security_model",
                    "sha256:" + "3" * 64,
                ),
            )
        )


def test_native_backend_execution_security_gate_rejects_optional_evidence() -> None:
    report = build_current_native_backend_execution_security_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_native_backend_execution_security_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        NativeBackendExecutionSecurityEvidence("../native.so", "sha256:" + "0" * 64)


def test_native_backend_execution_security_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        NativeBackendExecutionSecurityEvidence("dynamic_library", "sha256:" + "0" * 64)


def test_native_backend_execution_security_gate_rejects_contract_drift() -> None:
    report = build_current_native_backend_execution_security_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        NativeBackendExecutionSecurityReport(
            evidence=report.evidence,
            gate_contract="native_backend_execution_security_gate.execution_enabled.v0",
        )


def test_native_backend_execution_security_gate_rejects_control_drift() -> None:
    report = build_current_native_backend_execution_security_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        NativeBackendExecutionSecurityReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_native_backend_execution_security_gate_rejects_blocked_surface_drift() -> None:
    report = build_current_native_backend_execution_security_report()

    with pytest.raises(ValueError, match="blocked_execution_surfaces mismatch"):
        NativeBackendExecutionSecurityReport(
            evidence=report.evidence,
            blocked_execution_surfaces=tuple(reversed(report.blocked_execution_surfaces)),
        )


def test_native_backend_execution_security_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/native_backend_execution_security_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        NATIVE_BACKEND_EXECUTION_SECURITY_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS
    )
    assert schema["properties"]["native_backend_execution"]["const"] is False
    assert schema["properties"]["native_plugin_abi_loading"]["const"] is False
    assert schema["properties"]["ffi_call"]["const"] is False
    assert schema["properties"]["symbol_resolution"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 5
    assert schema["properties"]["required_controls"]["maxItems"] == 20


def test_native_backend_execution_security_gate_schema_fails_closed() -> None:
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
    assert "dynamic_library" in schema["$defs"]["report_text"]["not"]["enum"]


def test_native_backend_execution_security_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert (
        golden["schema_version"]
        == NATIVE_BACKEND_EXECUTION_SECURITY_GATE_REPORT_SCHEMA_VERSION
    )
    assert golden["gate_status"] == NATIVE_BACKEND_EXECUTION_SECURITY_GATE_STATUS
    assert golden["native_backend_execution"] is False
    assert golden["native_plugin_abi_loading"] is False
    assert golden["required_evidence_ids"] == list(
        NATIVE_BACKEND_EXECUTION_SECURITY_REQUIRED_EVIDENCE
    )


def test_native_backend_execution_security_gate_is_documented() -> None:
    schema_path = "schemas/native_backend_execution_security_gate_report.v0.schema.json"
    example_path = "examples/native_backend_execution_security_gate.py"
    doc_path = "docs/NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md"),
        Path("docs/NATIVE_BACKEND_EXECUTION_SECURITY_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0251-native-backend-execution-security-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/GENERATED_ARTIFACT_QUARANTINE_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0251-native-backend-execution-security-gate.md"),
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
