from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.real_triton_first_slice_plan import (
    REAL_TRITON_FIRST_SLICE_PLAN_ALREADY_SATISFIED,
    REAL_TRITON_FIRST_SLICE_PLAN_BLOCKED_CLAIMS,
    REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT,
    REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS,
    REAL_TRITON_FIRST_SLICE_PLAN_ID,
    REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE,
    REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION,
    REAL_TRITON_FIRST_SLICE_PLAN_REQUIRED_INVARIANTS,
    REAL_TRITON_FIRST_SLICE_PLAN_STATUS,
    REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED,
    REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SLICE,
    REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SURFACE,
    RealTritonFirstSlicePlanError,
    assert_real_triton_first_slice_plan_report_contract,
    build_real_triton_first_slice_plan_report,
    build_report,
)

SCHEMA_PATH = Path("schemas/real_triton_first_slice_plan_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/real_triton_first_slice_plan_report.json")
DOC_PATH = Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_real_triton_first_slice_plan_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_real_triton_first_slice_plan_passes() -> None:
    report = _cached_report()

    assert_real_triton_first_slice_plan_report_contract(report)
    assert report["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION
    )
    assert report["plan_contract"] == REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT
    assert report["plan_id"] == REAL_TRITON_FIRST_SLICE_PLAN_ID
    assert report["plan_status"] == REAL_TRITON_FIRST_SLICE_PLAN_STATUS
    assert report["target_surface"] == REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SURFACE
    assert report["target_slice"] == REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SLICE
    assert report["admission_status"] == "blocked"
    assert report["admitted"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["evidence_count"] == len(REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS)
    assert [item["evidence_id"] for item in report["evidence"]] == list(
        REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS
    )
    assert report["already_satisfied_prerequisites"] == list(
        REAL_TRITON_FIRST_SLICE_PLAN_ALREADY_SATISFIED
    )
    assert report["missing_admission_evidence"] == list(
        REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE
    )
    assert report["surfaces_remaining_blocked"] == list(
        REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED
    )
    assert report["blocked_claims"] == list(REAL_TRITON_FIRST_SLICE_PLAN_BLOCKED_CLAIMS)
    assert report["required_invariants"] == list(
        REAL_TRITON_FIRST_SLICE_PLAN_REQUIRED_INVARIANTS
    )
    assert report["issues"] == []


def test_real_triton_first_slice_plan_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_real_triton_first_slice_plan_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/real_triton_first_slice_plan.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"admitted": false' in completed.stdout
    assert '"source_ingestion_admission_ready": false' in completed.stdout
    assert "source_ingestion_sandbox_implementation" in completed.stdout
    assert "source_ingestion_approval_criteria" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("admitted", True, "admitted"),
        ("source_ingestion_admission_ready", True, "source_ingestion_admission_ready"),
        ("plan_status", "ready", "plan_status"),
        ("missing_admission_evidence_count", 0, "missing_admission_evidence_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_real_triton_first_slice_plan_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(RealTritonFirstSlicePlanError, match=match):
        assert_real_triton_first_slice_plan_report_contract(report)


def test_real_triton_first_slice_plan_avoids_downstream_evidence_cycle() -> None:
    report = _cached_report()
    evidence_ids = {item["evidence_id"] for item in report["evidence"]}

    assert "source_ingestion_approval_criteria" in evidence_ids
    assert "source_ingestion_maintainer_security_review_packet" not in evidence_ids
    assert "source_ingestion_maintainer_approval_artifact" not in evidence_ids
    assert "source_ingestion_admission_gate" not in evidence_ids


def test_real_triton_first_slice_plan_rejects_evidence_order_drift() -> None:
    report = dict(_cached_report())
    evidence = list(report["evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["evidence"] = evidence

    with pytest.raises(RealTritonFirstSlicePlanError, match="evidence IDs"):
        assert_real_triton_first_slice_plan_report_contract(report)


def test_real_triton_first_slice_plan_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["missing_admission_evidence"] = ["source_text"]

    with pytest.raises(RealTritonFirstSlicePlanError, match="report-safe"):
        assert_real_triton_first_slice_plan_report_contract(report)


def test_real_triton_first_slice_plan_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["plan_contract"]["const"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_CONTRACT
    )
    assert schema["properties"]["plan_id"]["const"] == REAL_TRITON_FIRST_SLICE_PLAN_ID
    assert schema["properties"]["plan_status"]["const"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_STATUS
    )
    assert schema["properties"]["target_surface"]["const"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SURFACE
    )
    assert schema["properties"]["target_slice"]["const"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_TARGET_SLICE
    )
    assert schema["properties"]["evidence_count"]["const"] == len(
        REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS
    )
    assert [
        item["const"]
        for item in schema["properties"]["missing_admission_evidence"]["prefixItems"]
    ] == list(REAL_TRITON_FIRST_SLICE_PLAN_MISSING_ADMISSION_EVIDENCE)
    assert [
        item["const"]
        for item in schema["properties"]["surfaces_remaining_blocked"]["prefixItems"]
    ] == list(REAL_TRITON_FIRST_SLICE_PLAN_SURFACES_REMAINING_BLOCKED)


def test_real_triton_first_slice_plan_schema_fails_closed() -> None:
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
    assert not (set(schema["properties"]) & forbidden_properties)


def test_real_triton_first_slice_plan_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_PLAN_REPORT_SCHEMA_VERSION
    )
    assert golden["admitted"] is False
    assert golden["source_ingestion_admission_ready"] is False
    assert golden["evidence_count"] == len(REAL_TRITON_FIRST_SLICE_PLAN_EVIDENCE_IDS)


def test_real_triton_first_slice_plan_is_documented() -> None:
    schema_path = "schemas/real_triton_first_slice_plan_report.v0.schema.json"
    example_path = "examples/real_triton_first_slice_plan.py"
    golden_path = "tests/golden/frontend/real_triton_first_slice_plan_report.json"
    doc_path = "docs/REAL_TRITON_FIRST_SLICE_PLAN.md"
    rfc_path = "rfcs/0257-real-triton-first-slice-plan.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/REAL_TRITON_INTEGRATION_ADMISSION_GATE.md"),
        Path("docs/REAL_TRITON_SURFACE_GATE_COMPLETION.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert example_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
        assert doc_path in text or path == DOC_PATH
        assert rfc_path in text or path.name in {"README.md", "ROADMAP.md"}


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
