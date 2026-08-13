from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_runtime_matrix_report_contract,
    build_kernel_ingress_runtime_matrix_report,
    build_report,
)
from tuc.frontend import SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_runtime_matrix.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_runtime_matrix_report.v0.schema.json"
)


def test_kernel_ingress_runtime_matrix_report_shape() -> None:
    report = build_kernel_ingress_runtime_matrix_report()
    assert_kernel_ingress_runtime_matrix_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_REPORT_SCHEMA_VERSION
    )
    assert report["runtime_matrix_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
    )
    assert report["frontend_ingress_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["case_count"] == 5
    assert report["covered_operation_families"] == [
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ]
    assert report["backend_sequences"] == [
        "linear-sim->vector-sim",
        "vector-sim->vector-sim",
        "linear-sim->vector-sim->vector-sim->vector-sim",
    ]
    assert [case["status"] for case in report["cases"]] == ["runtime_bound"] * 5
    assert report["cases"][4]["trace_step_count"] == 4


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 1, "case_count"),
        ("runtime_matrix_contract", "other", "runtime_matrix_contract"),
        ("raw_source", "import triton", "top-level report"),
    ],
)
def test_kernel_ingress_runtime_matrix_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_runtime_matrix_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_runtime_matrix_report_contract(report)


def test_kernel_ingress_runtime_matrix_contract_rejects_case_drift() -> None:
    report = build_kernel_ingress_runtime_matrix_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["backend_sequence"] = ["reference-cpu", "vector-sim"]

    with pytest.raises(ValueError, match="backend_sequence drift"):
        assert_kernel_ingress_runtime_matrix_report_contract(report)


def test_kernel_ingress_runtime_matrix_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_runtime_matrix_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_runtime_matrix.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"runtime_matrix_contract"' in completed.stdout
    assert '"backend_sequences"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_runtime_matrix_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["runtime_matrix_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
    )
    assert schema["properties"]["frontend_ingress_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "kernel_ingress_digest" in schema["required"]


def test_kernel_ingress_runtime_matrix_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/source_to_intent_research_kernel_ingress_runtime_matrix.py"
    )
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
