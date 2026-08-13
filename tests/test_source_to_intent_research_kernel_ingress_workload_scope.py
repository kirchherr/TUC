from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT,
)
from examples.source_to_intent_research_kernel_ingress_workload_scope import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_workload_scope_report_contract,
    build_kernel_ingress_workload_scope_report,
    build_report,
)
from tuc import WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_workload_scope.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_workload_scope_report.v0.schema.json"
)


def test_kernel_ingress_workload_scope_report_shape() -> None:
    report = build_kernel_ingress_workload_scope_report()
    assert_kernel_ingress_workload_scope_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    )
    assert report["binding_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CONTRACT
    )
    assert report["source_evidence_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
    )
    assert report["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert report["workload_scope_schema_version"] == WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    assert report["status"] == "PASS"
    assert report["native_performance_claim"] is False
    assert report["performance_claim_status"] == "blocked"
    assert report["case_count"] == 10
    assert report["profile_count"] == 2
    assert report["profile_ids"] == ["base", "alternate"]
    assert report["scope_count"] == 24
    assert report["workload_scope_ready"] is True
    assert report["issues"] == ["native_performance_claim_blocked"]

    mvp_alternate_scopes = [
        scope
        for scope in report["scopes"]
        if scope["shape_profile_id"] == "kernel_ingress_mvp_pipeline_alternate"
    ]
    assert mvp_alternate_scopes == [
        {
            "correctness_reference_id": "kernel_ingress_reference_correctness",
            "dtype_policy_id": "float64_reference",
            "operation_family": "elementwise",
            "problem_size_max": 3,
            "problem_size_min": 3,
            "scope_id": "kernel_ingress_mvp_pipeline_alternate_elementwise",
            "shape_profile_id": "kernel_ingress_mvp_pipeline_alternate",
        },
        {
            "correctness_reference_id": "kernel_ingress_reference_correctness",
            "dtype_policy_id": "float64_reference",
            "operation_family": "matmul",
            "problem_size_max": 45,
            "problem_size_min": 45,
            "scope_id": "kernel_ingress_mvp_pipeline_alternate_matmul",
            "shape_profile_id": "kernel_ingress_mvp_pipeline_alternate",
        },
        {
            "correctness_reference_id": "kernel_ingress_reference_correctness",
            "dtype_policy_id": "float64_reference",
            "operation_family": "reduction",
            "problem_size_max": 9,
            "problem_size_min": 9,
            "scope_id": "kernel_ingress_mvp_pipeline_alternate_reduction",
            "shape_profile_id": "kernel_ingress_mvp_pipeline_alternate",
        },
        {
            "correctness_reference_id": "kernel_ingress_reference_correctness",
            "dtype_policy_id": "float64_reference",
            "operation_family": "softmax",
            "problem_size_max": 9,
            "problem_size_min": 9,
            "scope_id": "kernel_ingress_mvp_pipeline_alternate_softmax",
            "shape_profile_id": "kernel_ingress_mvp_pipeline_alternate",
        },
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("scope_count", 23, "scope_count"),
        ("case_count", 9, "case_count"),
        ("native_performance_claim", True, "native_performance_claim"),
        ("raw_source", "@triton.jit", "top-level report"),
    ],
)
def test_kernel_ingress_workload_scope_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_workload_scope_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_workload_scope_report_contract(report)


def test_kernel_ingress_workload_scope_rejects_scope_drift() -> None:
    report = build_kernel_ingress_workload_scope_report()
    scopes = report["scopes"]
    assert isinstance(scopes, list)
    assert isinstance(scopes[-1], dict)
    scopes[-1]["problem_size_max"] = 999

    with pytest.raises(ValueError, match="scopes drift"):
        assert_kernel_ingress_workload_scope_report_contract(report)


def test_kernel_ingress_workload_scope_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_workload_scope_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_workload_scope.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"scope_count": 24' in completed.stdout
    assert '"workload_scope_ready": true' in completed.stdout
    assert '"native_performance_claim": false' in completed.stdout
    assert "source_evidence_digest" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_workload_scope_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["binding_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE_CONTRACT
    )
    assert schema["properties"]["source_evidence_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES_CONTRACT
    )
    assert schema["properties"]["workload_scope_schema_version"]["const"] == (
        WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["scope_count"]["const"] == 24
    assert schema["$defs"]["workload_scope"]["additionalProperties"] is False
    assert "source_evidence_digest" in schema["required"]


def test_kernel_ingress_workload_scope_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/source_to_intent_research_kernel_ingress_workload_scope.py"
    )
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/WORKLOAD_SCOPE_REPORT.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_WORKLOAD_SCOPE.md"),
        Path("rfcs/0070-workload-scope-report.md"),
        Path(
            "rfcs/"
            "0184-source-to-intent-research-kernel-ingress-workload-scope.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/WORKLOAD_SCOPE_REPORT.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0184-source-to-intent-research-kernel-ingress-workload-scope.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
