from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_idiom_alignment import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_idiom_alignment_report_contract,
    build_kernel_ingress_idiom_alignment_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_idiom_alignment.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_idiom_alignment_report.v0.schema.json"
)


def test_source_to_intent_research_kernel_ingress_idiom_alignment_report_shape() -> None:
    report = build_kernel_ingress_idiom_alignment_report()
    assert_kernel_ingress_idiom_alignment_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION
    )
    assert report["alignment_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["direct_general_triton_source_ingestion"] is False
    assert report["accepted_source_count"] == 5
    assert report["covered_operation_families"] == [
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ]
    assert report["unsupported_operation_families"] == []
    assert [case["case_id"] for case in report["cases"]] == [
        "research_matmul_elementwise",
        "research_softmax_reduction",
        "research_matmul_reduction",
        "research_softmax_elementwise",
        "research_mvp_pipeline",
    ]
    assert report["kernel_names"] == [
        "matmul_elementwise",
        "softmax_reduction",
        "matmul_reduction",
        "softmax_elementwise",
        "mvp_pipeline",
    ]
    assert report["cases"][4]["matched_idioms"] == [
        "metadata_elementwise_activation",
        "metadata_matmul_projection",
        "metadata_reduction_axis",
        "metadata_softmax_axis",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        (
            "direct_general_triton_source_ingestion",
            True,
            "direct_general_triton_source_ingestion",
        ),
        ("unsupported_operation_families", ["program_id"], "unsupported scope"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_source_to_intent_research_kernel_ingress_idiom_alignment_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_idiom_alignment_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_idiom_alignment_report_contract(report)


def test_source_to_intent_research_kernel_ingress_idiom_alignment_rejects_case_drift() -> None:
    report = build_kernel_ingress_idiom_alignment_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["matched_idioms"] = [
        "metadata_reduction_axis",
        "metadata_softmax_axis",
    ]

    with pytest.raises(ValueError, match="idiom drift"):
        assert_kernel_ingress_idiom_alignment_report_contract(report)


def test_source_to_intent_research_kernel_ingress_idiom_alignment_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_research_kernel_ingress_idiom_alignment_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_idiom_alignment.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"kernel_ingress_digest"' in completed.stdout
    assert '"kernel_ingress_conformance_gate_digest"' in completed.stdout
    assert '"coverage_report_digest"' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_idiom_alignment_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["alignment_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_CONTRACT
    )
    assert (
        schema["properties"]["direct_general_triton_source_ingestion"]["const"]
        is False
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "unsupported_operation_families" in schema["required"]


def test_source_to_intent_research_kernel_ingress_idiom_alignment_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/source_to_intent_research_kernel_ingress_idiom_alignment.py"
    )
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0168-source-to-intent-research-kernel-ingress-idiom-alignment.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0168-source-to-intent-research-kernel-ingress-idiom-alignment.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
