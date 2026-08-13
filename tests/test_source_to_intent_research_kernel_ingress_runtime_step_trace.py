from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_runtime_step_trace_report_contract,
    build_kernel_ingress_runtime_step_trace_report,
    build_report,
)
from tuc.frontend import SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_runtime_step_trace.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_runtime_step_trace_report.v0.schema.json"
)


def test_kernel_ingress_runtime_step_trace_report_shape() -> None:
    report = build_kernel_ingress_runtime_step_trace_report()
    assert_kernel_ingress_runtime_step_trace_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_REPORT_SCHEMA_VERSION
    )
    assert report["runtime_step_trace_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
    )
    assert report["frontend_ingress_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["case_count"] == 5
    mvp_case = report["cases"][4]
    assert mvp_case["case_id"] == "research_module_mvp_pipeline"
    assert mvp_case["backend_sequence"] == [
        "linear-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    ]
    assert mvp_case["operation_path"] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]
    assert mvp_case["step_count"] == 4
    assert [step["operation_name"] for step in mvp_case["steps"]] == [
        "projection",
        "normalized",
        "row_sum",
        "stable",
    ]
    assert [
        step["planned_backend"] == step["executor_backend"]
        for step in mvp_case["steps"]
    ] == [True, True, True, True]
    assert report["raw_source_policy"] == "omitted_by_policy"
    assert report["raw_value_policy"] == "omitted_by_policy"


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 4, "case_count"),
        ("runtime_step_trace_contract", "other", "runtime_step_trace_contract"),
        ("raw_source", "@triton.jit", "top-level report"),
    ],
)
def test_kernel_ingress_runtime_step_trace_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_runtime_step_trace_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_runtime_step_trace_report_contract(report)


def test_kernel_ingress_runtime_step_trace_contract_rejects_case_drift() -> None:
    report = build_kernel_ingress_runtime_step_trace_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[4], dict)
    cases[4]["operation_path"] = ["matmul", "elementwise"]

    with pytest.raises(ValueError, match="operation_path drift"):
        assert_kernel_ingress_runtime_step_trace_report_contract(report)


def test_kernel_ingress_runtime_step_trace_contract_rejects_step_drift() -> None:
    report = build_kernel_ingress_runtime_step_trace_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[4], dict)
    steps = cases[4]["steps"]
    assert isinstance(steps, list)
    assert isinstance(steps[1], dict)
    steps[1]["executor_backend"] = "linear-sim"

    with pytest.raises(ValueError, match="backend mismatch"):
        assert_kernel_ingress_runtime_step_trace_report_contract(report)


def test_kernel_ingress_runtime_step_trace_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_runtime_step_trace_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"runtime_step_trace_contract"' in completed.stdout
    assert '"operation_path"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_runtime_step_trace_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["runtime_step_trace_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
    )
    assert schema["properties"]["frontend_ingress_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert schema["$defs"]["step"]["additionalProperties"] is False
    assert "runtime_matrix_digest" in schema["required"]


def test_kernel_ingress_runtime_step_trace_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/source_to_intent_research_kernel_ingress_runtime_step_trace.py"
    )
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md"
        ),
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
        Path(
            "rfcs/"
            "0175-source-to-intent-research-kernel-ingress-runtime-backend-alignment.md"
        ),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
        Path(
            "rfcs/"
            "0180-source-to-intent-research-kernel-ingress-runtime-step-trace.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("rfcs/0180-source-to-intent-research-kernel-ingress-runtime-step-trace.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
