from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_boundary_budget_report_contract,
    build_kernel_ingress_boundary_budget_report,
    build_report,
)
from tuc.frontend import MAX_TRITON_SOURCE_BYTES, MAX_TRITON_SOURCE_LINES

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_boundary_budget.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_boundary_budget_report.v0.schema.json"
)


def test_kernel_ingress_boundary_budget_report_shape() -> None:
    report = build_kernel_ingress_boundary_budget_report()
    assert_kernel_ingress_boundary_budget_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert report["boundary_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["accepted_case_count"] == 4
    assert report["budget_rejection_case_count"] == 2
    assert report["ingress_budget_limits"]["module_bytes"] == MAX_TRITON_SOURCE_BYTES
    assert report["ingress_budget_limits"]["module_lines"] == MAX_TRITON_SOURCE_LINES
    assert [case["case_id"] for case in report["budget_rejection_cases"]] == [
        "module_byte_budget",
        "module_line_budget",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("budget_policy", "best_effort", "budget_policy"),
        ("budget_rejection_case_count", 1, "budget_rejection_case_count"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_kernel_ingress_boundary_budget_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_boundary_budget_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_boundary_budget_report_contract(report)


def test_kernel_ingress_boundary_budget_contract_rejects_observation_drift() -> None:
    report = build_kernel_ingress_boundary_budget_report()
    observations = report["accepted_observations"]
    assert isinstance(observations, list)
    assert isinstance(observations[0], dict)
    observations[0]["module_bytes"] = MAX_TRITON_SOURCE_BYTES + 1

    with pytest.raises(ValueError, match="exceeded module bytes"):
        assert_kernel_ingress_boundary_budget_report_contract(report)


def test_kernel_ingress_boundary_budget_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_boundary_budget_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_boundary_budget.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"module_byte_budget"' in completed.stdout
    assert '"module_line_budget"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_boundary_budget_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["boundary_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT
    )
    assert schema["properties"]["ingress_budget_limits"]["properties"][
        "module_bytes"
    ]["const"] == MAX_TRITON_SOURCE_BYTES
    assert schema["$defs"]["observation"]["additionalProperties"] is False


def test_kernel_ingress_boundary_budget_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_kernel_ingress_boundary_budget.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0170-source-to-intent-research-kernel-ingress-boundary-budget.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0170-source-to-intent-research-kernel-ingress-boundary-budget.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
