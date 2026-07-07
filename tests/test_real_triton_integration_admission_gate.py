from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.real_triton_integration_admission_gate import (
    build_current_real_triton_integration_admission_report,
)
from examples.real_triton_integration_admission_gate import (
    build_report as build_example_report,
)
from tuc.frontend import (
    REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS,
    REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT,
    REAL_TRITON_INTEGRATION_ADMISSION_DECISION,
    REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE_POLICY,
    REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION,
    REAL_TRITON_INTEGRATION_ADMISSION_SCOPE,
    REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED,
    REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS,
    REAL_TRITON_INTEGRATION_BLOCKED_SURFACES,
    REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE,
    REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES,
    RealTritonIntegrationAdmissionReport,
    RealTritonIntegrationEvidence,
    RealTritonIntegrationSurface,
    build_real_triton_integration_admission_report,
    default_real_triton_integration_surfaces,
    real_triton_integration_admission_report_to_dict,
)

SCHEMA_PATH = Path(
    "schemas/real_triton_integration_admission_gate_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/real_triton_integration_admission_gate_report.json"
)


def test_real_triton_integration_admission_blocks_surfaces_but_binds_evidence() -> None:
    report = build_current_real_triton_integration_admission_report()
    payload = real_triton_integration_admission_report_to_dict(report)

    assert payload["schema_version"] == (
        REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS
    assert payload["admission_contract"] == REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT
    assert payload["integration_scope"] == REAL_TRITON_INTEGRATION_ADMISSION_SCOPE
    assert payload["evidence_policy"] == REAL_TRITON_INTEGRATION_ADMISSION_EVIDENCE_POLICY
    assert payload["admission_status"] == REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED
    assert payload["admission_decision"] == REAL_TRITON_INTEGRATION_ADMISSION_DECISION
    assert payload["admitted"] is False
    assert payload["all_required_evidence_present"] is True
    assert payload["evidence_count"] == 3
    assert payload["blocked_surface_count"] == 12
    assert payload["required_evidence_ids"] == list(REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE)
    assert payload["required_surface_gates"] == list(
        REAL_TRITON_INTEGRATION_REQUIRED_SURFACE_GATES
    )
    assert payload["blocked_claims"] == list(REAL_TRITON_INTEGRATION_BLOCKED_CLAIMS)
    assert payload["direct_source_ingestion"] is False
    assert payload["frontend_package_import"] is False
    assert payload["plugin_discovery"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["device_access"] is False
    assert payload["generated_artifact_execution"] is False
    assert payload["native_backend_execution"] is False
    assert [item["evidence_id"] for item in payload["evidence"]] == list(
        REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE
    )
    assert [item["surface_id"] for item in payload["surfaces"]] == list(
        REAL_TRITON_INTEGRATION_BLOCKED_SURFACES
    )


def test_real_triton_integration_admission_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_real_triton_integration_admission_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/real_triton_integration_admission_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"admitted": false' in completed.stdout
    assert '"admission_status": "blocked"' in completed.stdout
    assert '"triton_jit_execution": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout


def test_real_triton_integration_admission_report_omits_sensitive_artifacts() -> None:
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


def test_real_triton_integration_admission_rejects_missing_evidence() -> None:
    report = build_current_real_triton_integration_admission_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_real_triton_integration_admission_report(report.evidence[:-1])


def test_real_triton_integration_admission_rejects_reordered_evidence() -> None:
    report = build_current_real_triton_integration_admission_report()

    with pytest.raises(ValueError, match="required evidence mismatch"):
        build_real_triton_integration_admission_report(tuple(reversed(report.evidence)))


def test_real_triton_integration_admission_rejects_duplicate_evidence_digest() -> None:
    digest = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_real_triton_integration_admission_report(
            (
                RealTritonIntegrationEvidence(
                    "external_frontend_package_conformance",
                    digest,
                ),
                RealTritonIntegrationEvidence(
                    "real_triton_integration_threat_model",
                    digest,
                ),
                RealTritonIntegrationEvidence(
                    "triton_integration_readiness",
                    "sha256:" + "1" * 64,
                ),
            )
        )


def test_real_triton_integration_admission_rejects_unblocked_surface() -> None:
    surfaces = default_real_triton_integration_surfaces()

    with pytest.raises(ValueError, match="surface must remain blocked"):
        RealTritonIntegrationSurface(
            surfaces[0].surface_id,
            "review_ready",
            surfaces[0].required_gate,
        )


def test_real_triton_integration_admission_rejects_surface_gate_drift() -> None:
    surfaces = default_real_triton_integration_surfaces()

    with pytest.raises(ValueError, match="surface gate mismatch"):
        RealTritonIntegrationSurface(
            surfaces[0].surface_id,
            REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED,
            "package_import_sandbox_gate",
        )


def test_real_triton_integration_admission_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        RealTritonIntegrationEvidence("../source.py", "sha256:" + "0" * 64)


def test_real_triton_integration_admission_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        RealTritonIntegrationEvidence("python_source", "sha256:" + "0" * 64)


def test_real_triton_integration_admission_rejects_tampered_claims() -> None:
    report = build_current_real_triton_integration_admission_report()

    with pytest.raises(ValueError, match="blocked_claims mismatch"):
        RealTritonIntegrationAdmissionReport(
            evidence=report.evidence,
            surfaces=report.surfaces,
            blocked_claims=report.blocked_claims[:-1],
        )


def test_real_triton_integration_admission_rejects_tampered_surfaces() -> None:
    report = build_current_real_triton_integration_admission_report()

    with pytest.raises(ValueError, match="blocked surfaces mismatch"):
        RealTritonIntegrationAdmissionReport(
            evidence=report.evidence,
            surfaces=tuple(reversed(report.surfaces)),
        )


def test_real_triton_integration_admission_rejects_optional_evidence() -> None:
    report = build_current_real_triton_integration_admission_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.evidence[0], required=False)


def test_real_triton_integration_admission_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/real_triton_integration_admission_gate_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["admission_contract"]["const"] == (
        REAL_TRITON_INTEGRATION_ADMISSION_CONTRACT
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        REAL_TRITON_INTEGRATION_ADMISSION_ARTIFACT_STATUS
    )
    assert schema["properties"]["admission_status"]["const"] == (
        REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED
    )
    assert schema["properties"]["admitted"]["const"] is False
    assert schema["properties"]["triton_jit_execution"]["const"] is False
    assert schema["properties"]["device_access"]["const"] is False
    assert schema["properties"]["required_evidence_ids"]["maxItems"] == 3
    assert schema["properties"]["required_surface_gates"]["maxItems"] == 7
    assert schema["properties"]["surfaces"]["maxItems"] == 12


def test_real_triton_integration_admission_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["surface"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]


def test_real_triton_integration_admission_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        REAL_TRITON_INTEGRATION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert golden["admission_status"] == REAL_TRITON_INTEGRATION_ADMISSION_STATUS_BLOCKED
    assert golden["admitted"] is False
    assert golden["all_required_evidence_present"] is True
    assert golden["required_evidence_ids"] == list(REAL_TRITON_INTEGRATION_REQUIRED_EVIDENCE)
    assert len(golden["surfaces"]) == len(REAL_TRITON_INTEGRATION_BLOCKED_SURFACES)


def test_real_triton_integration_admission_is_documented() -> None:
    schema_path = "schemas/real_triton_integration_admission_gate_report.v0.schema.json"
    example_path = "examples/real_triton_integration_admission_gate.py"
    doc_path = "docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"
    threat_model_path = "docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"

    for path in (
        Path("README.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0244-real-triton-integration-admission-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0244-real-triton-integration-admission-gate.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert doc_path in text
        assert threat_model_path in text


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
