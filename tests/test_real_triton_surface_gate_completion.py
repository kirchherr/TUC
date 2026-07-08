from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.real_triton_surface_gate_completion import (
    build_current_real_triton_surface_gate_completion_report,
)
from examples.real_triton_surface_gate_completion import build_report as build_example_report
from examples.source_ingestion_quarantine_gate import (
    build_current_source_ingestion_quarantine_report,
)
from tuc.frontend import (
    REAL_TRITON_SURFACE_GATE_COMPLETION_ADMISSION_EFFECT,
    REAL_TRITON_SURFACE_GATE_COMPLETION_ARTIFACT_STATUS,
    REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT,
    REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE_POLICY,
    REAL_TRITON_SURFACE_GATE_COMPLETION_EXPECTATIONS,
    REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION,
    REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES,
    REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS,
    RealTritonSurfaceGateCompletionReport,
    RealTritonSurfaceGateEvidence,
    build_real_triton_surface_gate_completion_report,
    real_triton_surface_gate_completion_report_to_dict,
    real_triton_surface_gate_evidence_from_payload,
    source_ingestion_quarantine_report_to_dict,
)

SCHEMA_PATH = Path("schemas/real_triton_surface_gate_completion_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/frontend/real_triton_surface_gate_completion_report.json"
)


def test_real_triton_surface_gate_completion_binds_all_gates() -> None:
    report = build_current_real_triton_surface_gate_completion_report()
    payload = real_triton_surface_gate_completion_report_to_dict(report)

    assert payload["schema_version"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_ARTIFACT_STATUS
    )
    assert payload["completion_contract"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT
    )
    assert payload["completion_status"] == REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS
    assert payload["admission_status"] == "blocked"
    assert payload["admission_effect"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_ADMISSION_EFFECT
    )
    assert payload["admitted"] is False
    assert payload["evidence_policy"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_EVIDENCE_POLICY
    )
    assert payload["security_boundary_established"] is True
    assert payload["all_required_surface_gates_present"] is True
    assert payload["all_surface_gates_non_admitting"] is True
    assert payload["expected_surface_gate_count"] == 7
    assert payload["surface_gate_count"] == 7
    assert payload["missing_surface_gate_ids"] == []
    assert payload["required_surface_gate_ids"] == list(
        REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES
    )
    assert [item["gate_id"] for item in payload["surface_gates"]] == list(
        REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES
    )
    assert all(
        item["admission_effect"].startswith("does_not_admit_")
        for item in payload["surface_gates"]
    )


def test_real_triton_surface_gate_completion_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_real_triton_surface_gate_completion_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/real_triton_surface_gate_completion.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"completion_status": "complete"' in completed.stdout
    assert '"admitted": false' in completed.stdout
    assert '"all_surface_gates_non_admitting": true' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "importlib" not in completed.stdout


def test_real_triton_surface_gate_completion_omits_sensitive_artifacts() -> None:
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


def test_real_triton_surface_gate_completion_rejects_missing_gate() -> None:
    report = build_current_real_triton_surface_gate_completion_report()

    with pytest.raises(ValueError, match="required surface gate mismatch"):
        build_real_triton_surface_gate_completion_report(
            report.admission_gate_digest,
            report.surface_gate_evidence[:-1],
        )


def test_real_triton_surface_gate_completion_rejects_reordered_gates() -> None:
    report = build_current_real_triton_surface_gate_completion_report()

    with pytest.raises(ValueError, match="required surface gate mismatch"):
        build_real_triton_surface_gate_completion_report(
            report.admission_gate_digest,
            tuple(reversed(report.surface_gate_evidence)),
        )


def test_real_triton_surface_gate_completion_rejects_duplicate_digest() -> None:
    duplicate = "sha256:" + "0" * 64
    evidence = tuple(
        RealTritonSurfaceGateEvidence(
            gate_id=expectation.gate_id,
            surface_id=expectation.surface_id,
            gate_status=expectation.gate_status,
            admission_effect=expectation.admission_effect,
            evidence_digest=duplicate if index < 2 else f"sha256:{index:064x}",
        )
        for index, expectation in enumerate(
            REAL_TRITON_SURFACE_GATE_COMPLETION_EXPECTATIONS
        )
    )

    with pytest.raises(ValueError, match="evidence digests must be unique"):
        build_real_triton_surface_gate_completion_report("sha256:" + "f" * 64, evidence)


def test_real_triton_surface_gate_completion_rejects_optional_evidence() -> None:
    report = build_current_real_triton_surface_gate_completion_report()

    with pytest.raises(ValueError, match="cannot be optional"):
        replace(report.surface_gate_evidence[0], required=False)


def test_real_triton_surface_gate_completion_rejects_payload_drift() -> None:
    source_report = build_current_source_ingestion_quarantine_report()
    payload = source_ingestion_quarantine_report_to_dict(source_report)
    payload["gate_status"] = "admitted"

    with pytest.raises(ValueError, match="gate_status mismatch"):
        real_triton_surface_gate_evidence_from_payload(
            "source_ingestion_quarantine_gate",
            payload,
        )


def test_real_triton_surface_gate_completion_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        RealTritonSurfaceGateEvidence(
            gate_id="../gate",
            surface_id="direct_source_ingestion",
            gate_status="quarantine_only",
            admission_effect="does_not_admit_direct_source_ingestion",
            evidence_digest="sha256:" + "0" * 64,
        )


def test_real_triton_surface_gate_completion_rejects_sensitive_ids() -> None:
    with pytest.raises(ValueError, match="report-safe text"):
        RealTritonSurfaceGateEvidence(
            gate_id="dynamic_library",
            surface_id="direct_source_ingestion",
            gate_status="quarantine_only",
            admission_effect="does_not_admit_direct_source_ingestion",
            evidence_digest="sha256:" + "0" * 64,
        )


def test_real_triton_surface_gate_completion_rejects_contract_drift() -> None:
    report = build_current_real_triton_surface_gate_completion_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        RealTritonSurfaceGateCompletionReport(
            admission_gate_digest=report.admission_gate_digest,
            surface_gate_evidence=report.surface_gate_evidence,
            completion_contract="real_triton_surface_gate_completion.execution.v0",
        )


def test_real_triton_surface_gate_completion_rejects_required_gate_drift() -> None:
    report = build_current_real_triton_surface_gate_completion_report()

    with pytest.raises(ValueError, match="required_surface_gate_ids mismatch"):
        RealTritonSurfaceGateCompletionReport(
            admission_gate_digest=report.admission_gate_digest,
            surface_gate_evidence=report.surface_gate_evidence,
            required_surface_gate_ids=tuple(reversed(report.required_surface_gate_ids)),
        )


def test_real_triton_surface_gate_completion_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/real_triton_surface_gate_completion_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["completion_contract"]["const"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_CONTRACT
    )
    assert schema["properties"]["completion_status"]["const"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS
    )
    assert schema["properties"]["admitted"]["const"] is False
    assert schema["properties"]["surface_gate_count"]["const"] == 7
    assert schema["properties"]["expected_surface_gate_count"]["const"] == 7


def test_real_triton_surface_gate_completion_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["surface_gate_evidence"]["properties"]
    assert "dynamic_library" in schema["$defs"]["report_text"]["not"]["enum"]


def test_real_triton_surface_gate_completion_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        REAL_TRITON_SURFACE_GATE_COMPLETION_REPORT_SCHEMA_VERSION
    )
    assert golden["completion_status"] == REAL_TRITON_SURFACE_GATE_COMPLETION_STATUS
    assert golden["admitted"] is False
    assert golden["required_surface_gate_ids"] == list(
        REAL_TRITON_SURFACE_GATE_COMPLETION_REQUIRED_SURFACE_GATES
    )
    assert golden["surface_gate_count"] == len(golden["surface_gates"]) == 7


def test_real_triton_surface_gate_completion_is_documented() -> None:
    schema_path = "schemas/real_triton_surface_gate_completion_report.v0.schema.json"
    example_path = "examples/real_triton_surface_gate_completion.py"
    doc_path = "docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md"

    for path in (
        Path("README.md"),
        Path("docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_INTEGRATION_THREAT_MODEL.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0252-real-triton-surface-gate-completion.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text
        assert doc_path in text


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