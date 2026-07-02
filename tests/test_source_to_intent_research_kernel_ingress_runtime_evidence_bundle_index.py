from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    build_kernel_ingress_runtime_evidence_bundle_index_report,
    build_report,
)
from tuc.runtime import (
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index_report.v0.schema.json"
)


def test_kernel_ingress_runtime_evidence_bundle_index_report_shape() -> None:
    report = build_kernel_ingress_runtime_evidence_bundle_index_report()
    assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_REPORT_SCHEMA_VERSION
    )
    assert report["runtime_evidence_bundle_index_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT
    )
    assert report["runtime_evidence_bundle_contract"] == (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["case_count"] == 5
    assert report["runtime_evidence_sections"] == list(
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS
    )
    mvp_case = report["cases"][4]
    assert mvp_case["case_id"] == "research_module_mvp_pipeline"
    assert mvp_case["graph_name"] == "research_mvp_pipeline"
    assert mvp_case["operation_path"] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]
    assert mvp_case["passed"] is True
    assert mvp_case["step_count"] == 4
    assert mvp_case["tensor_store_record_count"] == 6
    assert mvp_case["execution_receipt_link_count"] == 6
    assert mvp_case["raw_value_policy"] == "omitted_by_policy"


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 4, "case_count"),
        (
            "runtime_evidence_bundle_index_contract",
            "other",
            "runtime_evidence_bundle_index_contract",
        ),
        ("raw_source", "@triton.jit", "top-level report"),
    ],
)
def test_kernel_ingress_runtime_evidence_bundle_index_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_runtime_evidence_bundle_index_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(report)


def test_kernel_ingress_runtime_evidence_bundle_index_rejects_case_drift() -> None:
    report = build_kernel_ingress_runtime_evidence_bundle_index_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[4], dict)
    cases[4]["operation_path"] = ["matmul", "elementwise"]

    with pytest.raises(ValueError, match="operation_path drift"):
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(report)


def test_kernel_ingress_runtime_evidence_bundle_index_rejects_bundle_drift() -> None:
    report = build_kernel_ingress_runtime_evidence_bundle_index_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["passed"] = False

    with pytest.raises(ValueError, match="passed drift"):
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(report)


def test_kernel_ingress_runtime_evidence_bundle_index_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_runtime_evidence_bundle_index_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"runtime_evidence_bundle_contract"' in completed.stdout
    assert '"bundle_report_digest"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_runtime_evidence_bundle_index_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["runtime_evidence_bundle_index_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT
    )
    assert schema["properties"]["runtime_evidence_bundle_contract"]["const"] == (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "runtime_step_trace_digest" in schema["required"]


def test_kernel_ingress_runtime_evidence_bundle_index_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.py"
    )
    doc_path = (
        "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md"
    )

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
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
        Path(
            "rfcs/"
            "0181-source-to-intent-research-kernel-ingress-runtime-evidence-bundle-index.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0181-source-to-intent-research-kernel-ingress-runtime-evidence-bundle-index.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
