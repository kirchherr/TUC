from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.real_triton_first_slice_evidence_portfolio import (
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BINDING_IDS,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BLOCKED_CLAIMS,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_CONTRACT,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_EVIDENCE_POLICY,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_ID,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_PROVEN_CLAIMS,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_REPORT_SCHEMA_VERSION,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SAFETY_INVARIANTS,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_STATUS,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SLICE,
    REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SURFACE,
    RealTritonFirstSliceEvidencePortfolioError,
    assert_real_triton_first_slice_evidence_portfolio_report_contract,
    build_real_triton_first_slice_evidence_portfolio_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json"
)
SCHEMA_PATH = Path(
    "schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json"
)
DOC_PATH = Path("docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md")
RFC_PATH = Path("rfcs/0274-real-triton-first-slice-evidence-portfolio.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_real_triton_first_slice_evidence_portfolio_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_real_triton_first_slice_evidence_portfolio_report_shape() -> None:
    report = _cached_report()

    assert_real_triton_first_slice_evidence_portfolio_report_contract(report)
    assert report["schema_version"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_REPORT_SCHEMA_VERSION
    )
    assert report["portfolio_contract"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_CONTRACT
    )
    assert report["portfolio_id"] == REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_ID
    assert report["portfolio_status"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_STATUS
    )
    assert report["target_surface"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SURFACE
    )
    assert report["target_slice"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SLICE
    )
    assert report["evidence_policy"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_EVIDENCE_POLICY
    )
    assert report["admission_status"] == "blocked"
    assert report["first_real_path_status"] == "PASS"
    assert report["admitted"] is False
    assert report["direct_source_ingestion"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["research_scope_claim"] is True
    assert report["production_compiler_claim"] is False
    assert report["native_performance_claim"] is False
    assert report["vendor_replacement_claim"] is False
    assert report["surface_opened"] is False
    assert report["triton_jit_execution"] is False
    assert report["device_access"] is False
    assert report["generated_artifact_execution"] is False
    assert report["runtime_handle_residency_claim"] is False
    assert report["proven_claims"] == list(
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_PROVEN_CLAIMS
    )
    assert report["blocked_claims"] == list(
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BLOCKED_CLAIMS
    )
    assert report["safety_invariants"] == list(
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_SAFETY_INVARIANTS
    )
    assert [item["artifact_id"] for item in report["evidence"]] == list(
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BINDING_IDS
    )


def test_real_triton_first_slice_evidence_portfolio_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_real_triton_first_slice_evidence_portfolio_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/real_triton_first_slice_evidence_portfolio.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"portfolio_status": "PASS"' in completed.stdout
    assert '"admission_status": "blocked"' in completed.stdout
    assert '"direct_source_ingestion": false' in completed.stdout
    assert '"first_real_path_status": "PASS"' in completed.stdout
    assert "first_real_triton_kernel_path" in completed.stdout
    assert "research_scope_claim_gate" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("admitted", True, "admitted"),
        ("direct_source_ingestion", True, "direct_source_ingestion"),
        ("source_ingestion_admission_ready", True, "source_ingestion"),
        ("first_real_path_status", "WARN", "first_real_path_status"),
        ("portfolio_status", "WARN", "portfolio_status"),
        ("native_performance_claim", True, "native_performance_claim"),
        ("surface_opened", True, "surface_opened"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_real_triton_first_slice_evidence_portfolio_rejects_top_level_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(RealTritonFirstSliceEvidencePortfolioError, match=match):
        assert_real_triton_first_slice_evidence_portfolio_report_contract(report)


def test_real_triton_first_slice_evidence_portfolio_rejects_evidence_order() -> None:
    report = dict(_cached_report())
    evidence = list(report["evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["evidence"] = evidence

    with pytest.raises(
        RealTritonFirstSliceEvidencePortfolioError,
        match="artifact_id",
    ):
        assert_real_triton_first_slice_evidence_portfolio_report_contract(report)


def test_real_triton_first_slice_evidence_portfolio_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    evidence = [dict(item) for item in report["evidence"]]
    evidence[0]["digest"] = "sha256:" + "0" * 63
    report["evidence"] = evidence

    with pytest.raises(RealTritonFirstSliceEvidencePortfolioError, match="digest"):
        assert_real_triton_first_slice_evidence_portfolio_report_contract(report)


def test_real_triton_first_slice_evidence_portfolio_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["portfolio_contract"]["const"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_CONTRACT
    )
    assert schema["properties"]["portfolio_id"]["const"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_ID
    )
    assert schema["properties"]["portfolio_status"]["const"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_STATUS
    )
    assert schema["properties"]["target_surface"]["const"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SURFACE
    )
    assert schema["properties"]["target_slice"]["const"] == (
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_TARGET_SLICE
    )
    assert schema["properties"]["evidence_count"]["const"] == len(
        REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO_BINDING_IDS
    )
    assert schema["$defs"]["binding"]["additionalProperties"] is False


def test_real_triton_first_slice_evidence_portfolio_schema_fails_closed() -> None:
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


def test_real_triton_first_slice_evidence_portfolio_is_documented_and_ci_bound() -> None:
    schema_path = "schemas/real_triton_first_slice_evidence_portfolio_report.v0.schema.json"
    example_path = "examples/real_triton_first_slice_evidence_portfolio.py"
    golden_path = (
        "tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json"
    )
    doc_path = "docs/REAL_TRITON_FIRST_SLICE_EVIDENCE_PORTFOLIO.md"
    rfc_path = "rfcs/0274-real-triton-first-slice-evidence-portfolio.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/MINIMAL_TUC_WALKTHROUGH.md"),
        Path("docs/FIRST_REAL_TRITON_KERNEL_PATH.md"),
        DOC_PATH,
        RFC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text
        if path != Path(".github/workflows/ci.yml"):
            assert schema_path in text
            assert golden_path in text
            assert doc_path in text or path == DOC_PATH
            assert rfc_path in text or path == RFC_PATH


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
