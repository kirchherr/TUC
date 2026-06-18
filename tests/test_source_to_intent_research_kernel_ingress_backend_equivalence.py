from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_backend_equivalence import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_backend_equivalence_report_contract,
    build_kernel_ingress_backend_equivalence_report,
    build_report,
)
from tuc.runtime import RUNTIME_BACKEND_EQUIVALENCE_CONTRACT

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_backend_equivalence.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_backend_equivalence_report.v0.schema.json"
)


def test_kernel_ingress_backend_equivalence_report_shape() -> None:
    report = build_kernel_ingress_backend_equivalence_report()
    assert_kernel_ingress_backend_equivalence_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
    )
    assert report["kernel_ingress_backend_equivalence_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert report["equivalence_contract"] == RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    assert report["status"] == "PASS"
    assert report["case_count"] == 4
    assert report["comparison_count"] == 4
    assert report["baseline_backend_sequences"] == [
        "reference-cpu->reference-cpu",
        "reference-cpu->reference-cpu->reference-cpu->reference-cpu",
    ]
    assert report["candidate_backend_sequences"] == [
        "linear-sim->vector-sim",
        "vector-sim->vector-sim",
        "linear-sim->vector-sim->vector-sim->vector-sim",
    ]
    assert report["trusted_runtime_backends"] == [
        "linear-sim",
        "reference-cpu",
        "vector-sim",
    ]

    mvp_case = report["cases"][3]
    assert mvp_case["case_id"] == "research_module_mvp_pipeline"
    assert mvp_case["graph_name"] == "research_mvp_pipeline"
    assert mvp_case["baseline_backend_sequence"] == [
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
    ]
    assert mvp_case["candidate_backend_sequence"] == [
        "linear-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    ]
    assert mvp_case["terminal_outputs"] == ["stable"]
    assert mvp_case["comparison_count"] == 1
    assert mvp_case["passed"] is True
    assert mvp_case["raw_value_policy"] == "omitted_by_policy"


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 3, "case_count"),
        ("comparison_count", 3, "comparison_count"),
        (
            "kernel_ingress_backend_equivalence_contract",
            "other",
            "kernel_ingress_backend_equivalence_contract",
        ),
        ("raw_source", "@triton.jit", "top-level report"),
    ],
)
def test_kernel_ingress_backend_equivalence_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_backend_equivalence_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_backend_equivalence_report_contract(report)


def test_kernel_ingress_backend_equivalence_rejects_case_drift() -> None:
    report = build_kernel_ingress_backend_equivalence_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[3], dict)
    cases[3]["candidate_backend_sequence"] = ["vector-sim", "vector-sim"]

    with pytest.raises(ValueError, match="candidate_backend_sequence drift"):
        assert_kernel_ingress_backend_equivalence_report_contract(report)


def test_kernel_ingress_backend_equivalence_rejects_failed_comparison() -> None:
    report = build_kernel_ingress_backend_equivalence_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["passed"] = False

    with pytest.raises(ValueError, match="passed drift"):
        assert_kernel_ingress_backend_equivalence_report_contract(report)


def test_kernel_ingress_backend_equivalence_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_backend_equivalence_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_backend_equivalence.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"equivalence_contract"' in completed.stdout
    assert '"comparison_metadata_digest"' in completed.stdout
    assert "reference-cpu" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_backend_equivalence_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["kernel_ingress_backend_equivalence_contract"][
        "const"
    ] == SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
    assert schema["properties"]["equivalence_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "comparison_metadata_digest" in schema["$defs"]["case"]["required"]


def test_kernel_ingress_backend_equivalence_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_backend_equivalence.py"
    )
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md"

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
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
        Path(
            "rfcs/"
            "0182-source-to-intent-research-kernel-ingress-backend-equivalence.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0182-source-to-intent-research-kernel-ingress-backend-equivalence.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
