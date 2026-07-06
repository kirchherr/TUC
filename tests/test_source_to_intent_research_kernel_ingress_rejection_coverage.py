from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_rejection_coverage import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_rejection_coverage_report_contract,
    build_kernel_ingress_rejection_coverage_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_rejection_coverage.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_rejection_coverage_report.v0.schema.json"
)


def test_kernel_ingress_rejection_coverage_report_shape() -> None:
    report = build_kernel_ingress_rejection_coverage_report()
    assert_kernel_ingress_rejection_coverage_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_REPORT_SCHEMA_VERSION
    )
    assert report["coverage_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["covered_rejection_count"] == 13
    assert report["required_coverage_sources"] == ["diagnostics", "boundary_budget"]
    assert report["diagnostics_rejection_reasons"] == [
        "decorator_call",
        "import_after_kernel_function",
        "import_from_statement",
        "kernel_name_mismatch",
        "missing_triton_jit_decorator",
        "multiple_kernel_functions",
        "top_level_side_effect",
        "unsupported_decorator",
        "unsupported_import",
    ]
    assert report["budget_rejection_reasons"] == [
        "module_byte_budget",
        "module_line_budget",
        "module_ast_node_budget",
        "module_ast_depth_budget",
    ]
    assert [item["case_id"] for item in report["coverage_matrix"]] == [
        "reject_unsupported_import",
        "reject_import_from_statement",
        "reject_import_after_kernel_function",
        "reject_missing_triton_jit_decorator",
        "reject_decorator_call",
        "reject_unsupported_decorator",
        "reject_multiple_kernel_functions",
        "reject_top_level_side_effect",
        "reject_kernel_name_mismatch",
        "module_byte_budget",
        "module_line_budget",
        "module_ast_node_budget",
        "module_ast_depth_budget",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("covered_rejection_count", 12, "covered_rejection_count"),
        ("coverage_policy", "best_effort", "coverage_policy"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_kernel_ingress_rejection_coverage_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_rejection_coverage_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_rejection_coverage_report_contract(report)


def test_kernel_ingress_rejection_coverage_contract_rejects_matrix_drift() -> None:
    report = build_kernel_ingress_rejection_coverage_report()
    matrix = report["coverage_matrix"]
    assert isinstance(matrix, list)
    assert isinstance(matrix[0], dict)
    matrix[0]["reason_id"] = "unsupported"

    with pytest.raises(ValueError, match="item drift"):
        assert_kernel_ingress_rejection_coverage_report_contract(report)


def test_kernel_ingress_rejection_coverage_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_rejection_coverage_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_rejection_coverage.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"covered_rejection_count": 13' in completed.stdout
    assert '"boundary_budget"' in completed.stdout
    assert '"diagnostics"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_rejection_coverage_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["coverage_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_CONTRACT
    )
    assert schema["properties"]["covered_rejection_count"]["const"] == 13
    assert schema["$defs"]["coverage_item"]["additionalProperties"] is False


def test_kernel_ingress_rejection_coverage_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_kernel_ingress_rejection_coverage.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0170-source-to-intent-research-kernel-ingress-boundary-budget.md"),
        Path("rfcs/0171-source-to-intent-research-kernel-ingress-rejection-coverage.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0171-source-to-intent-research-kernel-ingress-rejection-coverage.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
