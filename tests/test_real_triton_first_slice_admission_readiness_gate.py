from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.real_triton_first_slice_admission_readiness_gate import (
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_CLAIMS,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_EXECUTION_SURFACES,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKING_REASONS,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_DECISION,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_POLICY,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_CONTRACT,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_ID,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_STATUS,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REQUIRED_INVARIANTS,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SLICE,
    REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SURFACE,
    RealTritonFirstSliceAdmissionReadinessGateError,
    assert_real_triton_first_slice_admission_readiness_gate_report_contract,
    build_real_triton_first_slice_admission_readiness_gate_report,
    build_report,
)

SCHEMA_PATH = Path(
    "schemas/real_triton_first_slice_admission_readiness_gate_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json"
)
DOC_PATH = Path("docs/REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE.md")
RFC_PATH = Path("rfcs/0277-real-triton-first-slice-admission-readiness-gate.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_real_triton_first_slice_admission_readiness_gate_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_real_triton_first_slice_admission_readiness_gate_shape() -> None:
    report = _cached_report()

    assert_real_triton_first_slice_admission_readiness_gate_report_contract(report)
    assert report["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION
    )
    assert report["gate_contract"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_CONTRACT
    assert report["gate_id"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_ID
    assert report["gate_status"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_STATUS
    assert report["gate_passed"] is False
    assert report["admission_decision"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_DECISION
    assert report["admission_ready"] is False
    assert report["admitted"] is False
    assert report["target_surface"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SURFACE
    assert report["target_slice"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_TARGET_SLICE
    assert report["evidence_policy"] == REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_POLICY
    assert report["checked_evidence_count"] == len(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS
    )
    assert [item["artifact_id"] for item in report["checked_evidence"]] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS
    )
    assert report["already_satisfied"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED
    )
    assert report["remaining_external_evidence"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE
    )
    assert report["blocking_reasons"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKING_REASONS
    )
    assert report["blocked_claims"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_CLAIMS
    )
    assert report["blocked_execution_surfaces"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKED_EXECUTION_SURFACES
    )
    assert report["required_invariants"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REQUIRED_INVARIANTS
    )
    assert report["issues"] == []
    assert report["source_free"] is True
    assert report["surface_opened"] is False


def test_real_triton_first_slice_admission_readiness_gate_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_real_triton_first_slice_admission_readiness_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/real_triton_first_slice_admission_readiness_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "real_triton_first_slice_admission_readiness_gate.data_only.v0" in (
        completed.stdout
    )
    assert '"gate_passed": false' in completed.stdout
    assert "maintainer_security_review_approval_missing" in completed.stdout
    assert "source_ingestion_maintainer_approval_artifact" in completed.stdout
    assert "external_approval_not_supplied" in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout
    assert '"host_path":' not in completed.stdout
    assert '"device_id":' not in completed.stdout


def test_real_triton_first_slice_admission_readiness_gate_rejects_fake_approval() -> None:
    with pytest.raises(
        RealTritonFirstSliceAdmissionReadinessGateError,
        match="status drift",
    ):
        build_real_triton_first_slice_admission_readiness_gate_report(
            artifact_text_overrides={
                "source_ingestion_maintainer_approval_artifact": json.dumps(
                    {
                        "contract": "source_ingestion_maintainer_approval_artifact.absent.v0",
                        "status": "approved",
                    }
                )
            }
        )


def test_real_triton_first_slice_admission_readiness_gate_rejects_source_leakage() -> None:
    with pytest.raises(
        RealTritonFirstSliceAdmissionReadinessGateError,
        match="forbidden fragment",
    ):
        build_real_triton_first_slice_admission_readiness_gate_report(
            artifact_text_overrides={
                "first_real_triton_kernel_path": '{"source_text":"x"}'
            }
        )


def test_real_triton_first_slice_admission_readiness_gate_rejects_contract_drift() -> None:
    report = dict(_cached_report())
    report["admission_ready"] = True

    with pytest.raises(
        RealTritonFirstSliceAdmissionReadinessGateError,
        match="admission_ready",
    ):
        assert_real_triton_first_slice_admission_readiness_gate_report_contract(report)


def test_real_triton_first_slice_admission_readiness_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == (
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_ID
    )
    assert schema["properties"]["gate_status"]["const"] == (
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_STATUS
    )
    assert schema["properties"]["gate_passed"]["const"] is False
    assert schema["properties"]["checked_evidence_count"]["const"] == len(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_EVIDENCE_IDS
    )
    assert _prefix_consts(schema["properties"]["already_satisfied"]) == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_ALREADY_SATISFIED
    )
    assert _prefix_consts(schema["properties"]["remaining_external_evidence"]) == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE
    )
    assert _prefix_consts(schema["properties"]["blocking_reasons"]) == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_BLOCKING_REASONS
    )


def test_real_triton_first_slice_admission_readiness_gate_schema_fails_closed() -> None:
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
    for object_schema in _iter_object_schemas(schema):
        assert not (set(object_schema.get("properties", {})) & forbidden_properties)


def test_real_triton_first_slice_admission_readiness_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE_SCHEMA_VERSION
    )
    assert golden["gate_passed"] is False
    assert golden["admission_ready"] is False
    assert golden["admitted"] is False
    assert golden["surface_opened"] is False
    assert golden["remaining_external_evidence"] == list(
        REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_REMAINING_EXTERNAL_EVIDENCE
    )


def test_real_triton_first_slice_admission_readiness_gate_is_documented() -> None:
    schema_path = (
        "schemas/real_triton_first_slice_admission_readiness_gate_report.v0.schema.json"
    )
    example_path = "examples/real_triton_first_slice_admission_readiness_gate.py"
    golden_path = (
        "tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json"
    )
    doc_path = "docs/REAL_TRITON_FIRST_SLICE_ADMISSION_READINESS_GATE.md"
    rfc_path = "rfcs/0277-real-triton-first-slice-admission-readiness-gate.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        Path("docs/SOURCE_INGESTION_ADMISSION_GATE.md"),
        DOC_PATH,
        RFC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text
        assert schema_path in text
        assert golden_path in text
        assert doc_path in text or path == DOC_PATH
        assert rfc_path in text or path == RFC_PATH


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))


def _prefix_consts(schema: dict[str, Any]) -> list[str]:
    return [str(item["const"]) for item in schema["prefixItems"]]


def _assert_objects_fail_closed(schema: Any) -> None:
    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False


def _iter_object_schemas(schema: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            found.append(schema)
        for value in schema.values():
            found.extend(_iter_object_schemas(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_iter_object_schemas(item))
    return found
