from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.first_real_triton_kernel_path import (
    FIRST_REAL_TRITON_KERNEL_PATH_BACKEND_SEQUENCE,
    FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID,
    FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT,
    FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID,
    FIRST_REAL_TRITON_KERNEL_PATH_KERNEL_NAME,
    FIRST_REAL_TRITON_KERNEL_PATH_OPERATION_FAMILIES,
    FIRST_REAL_TRITON_KERNEL_PATH_REPORT_SCHEMA_VERSION,
    FIRST_REAL_TRITON_KERNEL_PATH_TRACE_STEP_COUNT,
    FirstRealTritonKernelPathError,
    assert_first_real_triton_kernel_path_report_contract,
    build_first_real_triton_kernel_path_report,
    build_report,
)

GOLDEN_PATH = Path("tests/golden/frontend/first_real_triton_kernel_path.json")
SCHEMA_PATH = Path("schemas/first_real_triton_kernel_path_report.v0.schema.json")
DOC_PATH = Path("docs/FIRST_REAL_TRITON_KERNEL_PATH.md")
RFC_PATH = Path("rfcs/0272-first-real-triton-kernel-path.md")


def test_first_real_triton_kernel_path_report_shape() -> None:
    report = build_first_real_triton_kernel_path_report()
    assert_first_real_triton_kernel_path_report_contract(report)

    assert report["schema_version"] == FIRST_REAL_TRITON_KERNEL_PATH_REPORT_SCHEMA_VERSION
    assert report["path_contract"] == FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT
    assert report["proof_id"] == FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID
    assert report["status"] == "PASS"
    assert report["case_id"] == FIRST_REAL_TRITON_KERNEL_PATH_CASE_ID
    assert report["kernel_name"] == FIRST_REAL_TRITON_KERNEL_PATH_KERNEL_NAME
    assert report["backend_sequence"] == list(FIRST_REAL_TRITON_KERNEL_PATH_BACKEND_SEQUENCE)
    assert report["operation_families"] == list(
        FIRST_REAL_TRITON_KERNEL_PATH_OPERATION_FAMILIES
    )
    assert report["trace_step_count"] == FIRST_REAL_TRITON_KERNEL_PATH_TRACE_STEP_COUNT
    assert report["terminal_outputs"] == ["stable"]
    assert report["evidence_binding_count"] == 7
    assert [binding["artifact_id"] for binding in report["evidence_bindings"]] == [
        "source_to_intent_research_kernel_ingress",
        "source_to_intent_research_kernel_ingress_runtime_matrix",
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles",
        "source_to_intent_research_kernel_ingress_proof_bundle",
        "source_to_intent_research_kernel_ingress_evidence_gate",
        "source_ingestion_preclaim_acyclicity_gate",
        "source_ingestion_admission_gate",
    ]


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("status", "WARN", "status"),
        ("case_id", "other_case", "case_id"),
        ("backend_sequence", ["gpu"], "backend_sequence"),
        ("trace_step_count", 3, "trace_step_count"),
        ("blocked_claims", [], "blocked_claims"),
        ("raw_source", "def kernel(): pass", "top-level keys"),
    ),
)
def test_first_real_triton_kernel_path_rejects_top_level_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = build_first_real_triton_kernel_path_report()
    report[field] = value

    with pytest.raises(FirstRealTritonKernelPathError, match=match):
        assert_first_real_triton_kernel_path_report_contract(report)


def test_first_real_triton_kernel_path_rejects_binding_drift() -> None:
    report = build_first_real_triton_kernel_path_report()
    bindings = report["evidence_bindings"]
    assert isinstance(bindings, list)
    assert isinstance(bindings[0], dict)
    bindings[0]["digest"] = "sha256:" + "0" * 63

    with pytest.raises(FirstRealTritonKernelPathError, match="digest drift"):
        assert_first_real_triton_kernel_path_report_contract(report)


def test_first_real_triton_kernel_path_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_first_real_triton_kernel_path_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/first_real_triton_kernel_path.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"kernel_name": "mvp_pipeline"' in completed.stdout
    assert "linear-sim" in completed.stdout
    assert "vector-sim" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout


def test_first_real_triton_kernel_path_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        FIRST_REAL_TRITON_KERNEL_PATH_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["path_contract"]["const"] == (
        FIRST_REAL_TRITON_KERNEL_PATH_CONTRACT
    )
    assert schema["properties"]["proof_id"]["const"] == (
        FIRST_REAL_TRITON_KERNEL_PATH_EVIDENCE_ID
    )
    assert schema["properties"]["evidence_binding_count"]["const"] == 7
    assert schema["$defs"]["binding"]["additionalProperties"] is False


def test_first_real_triton_kernel_path_is_documented_and_ci_bound() -> None:
    example_path = "examples/first_real_triton_kernel_path.py"
    schema_path = "schemas/first_real_triton_kernel_path_report.v0.schema.json"
    golden_path = "tests/golden/frontend/first_real_triton_kernel_path.json"
    doc_path = "docs/FIRST_REAL_TRITON_KERNEL_PATH.md"
    rfc_path = "rfcs/0272-first-real-triton-kernel-path.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/MINIMAL_TUC_WALKTHROUGH.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
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
