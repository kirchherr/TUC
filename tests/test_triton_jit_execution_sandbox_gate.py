from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.triton_jit_execution_sandbox_gate import (
    build_current_triton_jit_execution_sandbox_report,
)
from examples.triton_jit_execution_sandbox_gate import build_report as build_example_report
from tuc.frontend import (
    TRITON_JIT_EXECUTION_SANDBOX_ADMISSION_EFFECT,
    TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_EXECUTION_SURFACES,
    TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_OUTPUTS,
    TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE_POLICY,
    TRITON_JIT_EXECUTION_SANDBOX_GATE_ARTIFACT_STATUS,
    TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT,
    TRITON_JIT_EXECUTION_SANDBOX_GATE_ID,
    TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION,
    TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS,
    TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS,
    TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE,
    TRITON_JIT_EXECUTION_SANDBOX_SURFACE_ID,
    TritonJitExecutionSandboxEvidence,
    TritonJitExecutionSandboxReport,
    build_triton_jit_execution_sandbox_report,
    triton_jit_execution_sandbox_report_to_dict,
)

SCHEMA_PATH = Path("schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/triton_jit_execution_sandbox_gate_report.json"
)


def test_triton_jit_execution_sandbox_gate_blocks_jit_surfaces() -> None:
    report = build_current_triton_jit_execution_sandbox_report()
    payload = triton_jit_execution_sandbox_report_to_dict(report)

    assert (
        payload["schema_version"]
        == TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == TRITON_JIT_EXECUTION_SANDBOX_GATE_ARTIFACT_STATUS
    assert payload["gate_contract"] == TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT
    assert payload["gate_id"] == TRITON_JIT_EXECUTION_SANDBOX_GATE_ID
    assert payload["surface_id"] == TRITON_JIT_EXECUTION_SANDBOX_SURFACE_ID
    assert payload["gate_status"] == TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS
    assert payload["admission_effect"] == TRITON_JIT_EXECUTION_SANDBOX_ADMISSION_EFFECT
    assert payload["evidence_policy"] == TRITON_JIT_EXECUTION_SANDBOX_EVIDENCE_POLICY
    assert payload["sandbox_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 5
    assert payload["required_control_count"] == 20
    assert payload["required_evidence_ids"] == list(
        TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(
        TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_CONTROLS
    )
    assert payload["blocked_execution_surfaces"] == list(
        TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(
        TRITON_JIT_EXECUTION_SANDBOX_BLOCKED_OUTPUTS
    )
    assert payload["triton_jit_execution"] is False
    assert payload["kernel_launch"] is False
    assert payload["generated_artifact_execution"] is False
    assert payload["device_access"] is False
    assert payload["kernel_cache_access"] is False
    assert payload["backend_binary_emitted"] is False
    assert payload["compiled_kernel_emitted"] is False
    assert payload["source_executed"] is False
    assert payload["frontend_package_import"] is False
    assert payload["python_import"] is False
    assert payload["plugin_discovery"] is False
    assert payload["network_access"] is False
    assert payload["subprocess_execution"] is False
    assert payload["dynamic_library_loading"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE
    )


def test_triton_jit_execution_sandbox_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_triton_jit_execution_sandbox_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/triton_jit_execution_sandbox_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "sandbox_requirements_only"' in completed.stdout
    assert '"triton_jit_execution": false' in completed.stdout
    assert '"kernel_launch": false' in completed.stdout
    assert '"device_access": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "importlib" not in completed.stdout


def test_triton_jit_execution_sandbox_gate_report_omits_sensitive_artifacts() -> None:
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


def test_triton_jit_execution_sandbox_gate_rejects_missing_evidence() -> None:
    report = build_current_triton_jit_execution_sandbox_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_triton_jit_execution_sandbox_report(report.evidence[:-1])


def test_triton_jit_execution_sandbox_gate_rejects_reordered_evidence() -> None:
    report = build_current_triton_jit_execution_sandbox_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_triton_jit_execution_sandbox_report(tuple(reversed(report.evidence)))


def test_triton_jit_execution_sandbox_gate_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_triton_jit_execution_sandbox_report(
            (
                TritonJitExecutionSandboxEvidence(
                    "package_import_sandbox_gate",
                    digest,
                ),
                TritonJitExecutionSandboxEvidence(
                    "plugin_discovery_allowlist_gate",
                    digest,
                ),
                TritonJitExecutionSandboxEvidence(
                    "real_triton_integration_admission_gate",
                    "sha256:" + "1" * 64,
                ),
                TritonJitExecutionSandboxEvidence(
                    "source_ingestion_quarantine_gate",
                    "sha256:" + "2" * 64,
                ),
                TritonJitExecutionSandboxEvidence(
                    "triton_jit_execution_sandbox_model",
                    "sha256:" + "3" * 64,
                ),
            )
        )


def test_triton_jit_execution_sandbox_gate_rejects_optional_evidence() -> None:
    report = build_current_triton_jit_execution_sandbox_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_triton_jit_execution_sandbox_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        TritonJitExecutionSandboxEvidence("../jit.py", "sha256:" + "0" * 64)


def test_triton_jit_execution_sandbox_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        TritonJitExecutionSandboxEvidence("generated_code", "sha256:" + "0" * 64)


def test_triton_jit_execution_sandbox_gate_rejects_contract_drift() -> None:
    report = build_current_triton_jit_execution_sandbox_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        TritonJitExecutionSandboxReport(
            evidence=report.evidence,
            gate_contract="triton_jit_execution_sandbox_gate.jit_enabled.v0",
        )


def test_triton_jit_execution_sandbox_gate_rejects_control_drift() -> None:
    report = build_current_triton_jit_execution_sandbox_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        TritonJitExecutionSandboxReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_triton_jit_execution_sandbox_gate_rejects_blocked_surface_drift() -> None:
    report = build_current_triton_jit_execution_sandbox_report()

    with pytest.raises(ValueError, match="blocked_execution_surfaces mismatch"):
        TritonJitExecutionSandboxReport(
            evidence=report.evidence,
            blocked_execution_surfaces=tuple(reversed(report.blocked_execution_surfaces)),
        )


def test_triton_jit_execution_sandbox_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        TRITON_JIT_EXECUTION_SANDBOX_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS
    )
    assert schema["properties"]["triton_jit_execution"]["const"] is False
    assert schema["properties"]["kernel_launch"]["const"] is False
    assert schema["properties"]["device_access"]["const"] is False
    assert schema["properties"]["generated_artifact_execution"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 5
    assert schema["properties"]["required_controls"]["maxItems"] == 20


def test_triton_jit_execution_sandbox_gate_schema_fails_closed() -> None:
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
    assert "generated_code" in schema["$defs"]["report_text"]["not"]["enum"]


def test_triton_jit_execution_sandbox_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert (
        golden["schema_version"]
        == TRITON_JIT_EXECUTION_SANDBOX_GATE_REPORT_SCHEMA_VERSION
    )
    assert golden["gate_status"] == TRITON_JIT_EXECUTION_SANDBOX_GATE_STATUS
    assert golden["triton_jit_execution"] is False
    assert golden["kernel_launch"] is False
    assert golden["required_evidence_ids"] == list(
        TRITON_JIT_EXECUTION_SANDBOX_REQUIRED_EVIDENCE
    )


def test_triton_jit_execution_sandbox_gate_is_documented() -> None:
    schema_path = "schemas/triton_jit_execution_sandbox_gate_report.v0.schema.json"
    example_path = "examples/triton_jit_execution_sandbox_gate.py"
    doc_path = "docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md"),
        Path("docs/TRITON_JIT_EXECUTION_SANDBOX_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0248-triton-jit-execution-sandbox-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0248-triton-jit-execution-sandbox-gate.md"),
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
