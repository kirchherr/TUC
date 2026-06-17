from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ID,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_runtime_coverage_policy_report_contract,
    build_kernel_ingress_runtime_coverage_policy_report,
    build_report,
)
from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_runtime_coverage_policy.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0.schema.json"
)


def test_kernel_ingress_runtime_coverage_policy_report_shape() -> None:
    report = build_kernel_ingress_runtime_coverage_policy_report()
    assert_kernel_ingress_runtime_coverage_policy_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_REPORT_SCHEMA_VERSION
    )
    assert report["policy_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
    )
    assert report["policy_id"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ID
    )
    assert report["runtime_matrix_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["required_case_count"] == 3
    assert report["observed_case_count"] == 3
    assert report["required_backend_sequences"] == [
        "linear-sim->vector-sim",
        "vector-sim->vector-sim",
    ]
    assert report["required_terminal_outputs"] == [
        "activated",
        "row_sum",
        "column_sum",
    ]
    assert report["required_digest_fields"] == [
        "runtime_plan_digest",
        "execution_trace_digest",
        "reference_correctness_digest",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("required_case_count", 1, "required_case_count"),
        ("policy_contract", "other", "policy_contract"),
        ("raw_source", "import triton", "top-level report"),
    ],
)
def test_kernel_ingress_runtime_coverage_policy_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_runtime_coverage_policy_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_runtime_coverage_policy_report_contract(report)


def test_kernel_ingress_runtime_coverage_policy_rejects_case_drift() -> None:
    report = build_kernel_ingress_runtime_coverage_policy_report()
    cases = report["case_requirements"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["terminal_outputs"] = ["wrong"]

    with pytest.raises(ValueError, match="terminal_outputs drift"):
        assert_kernel_ingress_runtime_coverage_policy_report_contract(report)


def test_kernel_ingress_runtime_coverage_policy_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_runtime_coverage_policy_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            (
                "examples/"
                "source_to_intent_research_kernel_ingress_runtime_coverage_policy.py"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"policy_contract"' in completed.stdout
    assert '"runtime_matrix_digest"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_runtime_coverage_policy_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["policy_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
    )
    assert schema["properties"]["policy_id"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ID
    )
    assert schema["$defs"]["case_requirement"]["additionalProperties"] is False
    assert "runtime_matrix_digest" in schema["required"]


def test_kernel_ingress_runtime_coverage_policy_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy.py"
    )
    doc_path = (
        "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md"
    )

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md"),
        Path(
            "rfcs/"
            "0174-source-to-intent-research-kernel-ingress-runtime-coverage-policy.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0174-source-to-intent-research-kernel-ingress-runtime-coverage-policy.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
