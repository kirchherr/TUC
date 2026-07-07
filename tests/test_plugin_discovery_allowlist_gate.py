from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.plugin_discovery_allowlist_gate import (
    build_current_plugin_discovery_allowlist_report,
)
from examples.plugin_discovery_allowlist_gate import build_report as build_example_report
from tuc.frontend import (
    PLUGIN_DISCOVERY_ALLOWLIST_ADMISSION_EFFECT,
    PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_EXECUTION_SURFACES,
    PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_OUTPUTS,
    PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE_POLICY,
    PLUGIN_DISCOVERY_ALLOWLIST_GATE_ARTIFACT_STATUS,
    PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT,
    PLUGIN_DISCOVERY_ALLOWLIST_GATE_ID,
    PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION,
    PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS,
    PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS,
    PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE,
    PLUGIN_DISCOVERY_ALLOWLIST_SURFACE_ID,
    PluginDiscoveryAllowlistEvidence,
    PluginDiscoveryAllowlistReport,
    build_plugin_discovery_allowlist_report,
    plugin_discovery_allowlist_report_to_dict,
)

SCHEMA_PATH = Path("schemas/plugin_discovery_allowlist_gate_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/plugin_discovery_allowlist_gate_report.json"
)


def test_plugin_discovery_allowlist_gate_blocks_discovery_surfaces() -> None:
    report = build_current_plugin_discovery_allowlist_report()
    payload = plugin_discovery_allowlist_report_to_dict(report)

    assert (
        payload["schema_version"]
        == PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == PLUGIN_DISCOVERY_ALLOWLIST_GATE_ARTIFACT_STATUS
    assert payload["gate_contract"] == PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT
    assert payload["gate_id"] == PLUGIN_DISCOVERY_ALLOWLIST_GATE_ID
    assert payload["surface_id"] == PLUGIN_DISCOVERY_ALLOWLIST_SURFACE_ID
    assert payload["gate_status"] == PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS
    assert payload["admission_effect"] == PLUGIN_DISCOVERY_ALLOWLIST_ADMISSION_EFFECT
    assert payload["evidence_policy"] == PLUGIN_DISCOVERY_ALLOWLIST_EVIDENCE_POLICY
    assert payload["allowlist_boundary_established"] is True
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 4
    assert payload["required_control_count"] == 18
    assert payload["required_evidence_ids"] == list(
        PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE
    )
    assert payload["required_controls"] == list(
        PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_CONTROLS
    )
    assert payload["blocked_execution_surfaces"] == list(
        PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_outputs"] == list(
        PLUGIN_DISCOVERY_ALLOWLIST_BLOCKED_OUTPUTS
    )
    assert payload["plugin_discovery"] is False
    assert payload["entrypoint_discovery"] is False
    assert payload["registry_scan"] is False
    assert payload["filesystem_scan"] is False
    assert payload["frontend_package_import"] is False
    assert payload["python_import"] is False
    assert payload["plugin_code_execution"] is False
    assert payload["plugin_loaded"] is False
    assert payload["capability_claims_from_code"] is False
    assert payload["network_access"] is False
    assert payload["subprocess_execution"] is False
    assert payload["dynamic_library_loading"] is False
    assert payload["device_access"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE
    )


def test_plugin_discovery_allowlist_gate_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_plugin_discovery_allowlist_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/plugin_discovery_allowlist_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_status": "allowlist_requirements_only"' in completed.stdout
    assert '"plugin_discovery": false' in completed.stdout
    assert '"entrypoint_discovery": false' in completed.stdout
    assert '"registry_scan": false' in completed.stdout
    assert "importlib" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_plugin_discovery_allowlist_gate_report_omits_sensitive_artifacts() -> None:
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


def test_plugin_discovery_allowlist_gate_rejects_missing_evidence() -> None:
    report = build_current_plugin_discovery_allowlist_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_plugin_discovery_allowlist_report(report.evidence[:-1])


def test_plugin_discovery_allowlist_gate_rejects_reordered_evidence() -> None:
    report = build_current_plugin_discovery_allowlist_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_plugin_discovery_allowlist_report(tuple(reversed(report.evidence)))


def test_plugin_discovery_allowlist_gate_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_plugin_discovery_allowlist_report(
            (
                PluginDiscoveryAllowlistEvidence(
                    "external_frontend_package_conformance",
                    digest,
                ),
                PluginDiscoveryAllowlistEvidence(
                    "package_import_sandbox_gate",
                    digest,
                ),
                PluginDiscoveryAllowlistEvidence(
                    "plugin_discovery_allowlist_model",
                    "sha256:" + "1" * 64,
                ),
                PluginDiscoveryAllowlistEvidence(
                    "real_triton_integration_admission_gate",
                    "sha256:" + "2" * 64,
                ),
            )
        )


def test_plugin_discovery_allowlist_gate_rejects_optional_evidence() -> None:
    report = build_current_plugin_discovery_allowlist_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_plugin_discovery_allowlist_gate_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        PluginDiscoveryAllowlistEvidence("../plugin.py", "sha256:" + "0" * 64)


def test_plugin_discovery_allowlist_gate_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        PluginDiscoveryAllowlistEvidence("plugin_entrypoint", "sha256:" + "0" * 64)


def test_plugin_discovery_allowlist_gate_rejects_contract_drift() -> None:
    report = build_current_plugin_discovery_allowlist_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        PluginDiscoveryAllowlistReport(
            evidence=report.evidence,
            gate_contract="plugin_discovery_allowlist_gate.discovery_enabled.v0",
        )


def test_plugin_discovery_allowlist_gate_rejects_control_drift() -> None:
    report = build_current_plugin_discovery_allowlist_report()

    with pytest.raises(ValueError, match="required_controls mismatch"):
        PluginDiscoveryAllowlistReport(
            evidence=report.evidence,
            required_controls=report.required_controls[:-1],
        )


def test_plugin_discovery_allowlist_gate_rejects_blocked_surface_drift() -> None:
    report = build_current_plugin_discovery_allowlist_report()

    with pytest.raises(ValueError, match="blocked_execution_surfaces mismatch"):
        PluginDiscoveryAllowlistReport(
            evidence=report.evidence,
            blocked_execution_surfaces=tuple(reversed(report.blocked_execution_surfaces)),
        )


def test_plugin_discovery_allowlist_gate_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/plugin_discovery_allowlist_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        PLUGIN_DISCOVERY_ALLOWLIST_GATE_CONTRACT
    )
    assert schema["properties"]["gate_status"]["const"] == (
        PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS
    )
    assert schema["properties"]["plugin_discovery"]["const"] is False
    assert schema["properties"]["entrypoint_discovery"]["const"] is False
    assert schema["properties"]["registry_scan"]["const"] is False
    assert schema["properties"]["frontend_package_import"]["const"] is False
    assert schema["properties"]["evidence"]["maxItems"] == 4
    assert schema["properties"]["required_controls"]["maxItems"] == 18


def test_plugin_discovery_allowlist_gate_schema_fails_closed() -> None:
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
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_plugin_discovery_allowlist_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert (
        golden["schema_version"]
        == PLUGIN_DISCOVERY_ALLOWLIST_GATE_REPORT_SCHEMA_VERSION
    )
    assert golden["gate_status"] == PLUGIN_DISCOVERY_ALLOWLIST_GATE_STATUS
    assert golden["plugin_discovery"] is False
    assert golden["entrypoint_discovery"] is False
    assert golden["required_evidence_ids"] == list(
        PLUGIN_DISCOVERY_ALLOWLIST_REQUIRED_EVIDENCE
    )


def test_plugin_discovery_allowlist_gate_is_documented() -> None:
    schema_path = "schemas/plugin_discovery_allowlist_gate_report.v0.schema.json"
    example_path = "examples/plugin_discovery_allowlist_gate.py"
    doc_path = "docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md"

    for path in (
        Path("README.md"),
        Path("docs/PACKAGE_IMPORT_SANDBOX_GATE.md"),
        Path("docs/PLUGIN_DISCOVERY_ALLOWLIST_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0247-plugin-discovery-allowlist-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/PACKAGE_IMPORT_SANDBOX_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0247-plugin-discovery-allowlist-gate.md"),
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
