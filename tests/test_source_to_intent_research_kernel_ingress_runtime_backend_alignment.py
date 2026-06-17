from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_runtime_backend_alignment_report_contract,
    build_kernel_ingress_runtime_backend_alignment_report,
    build_report,
)
from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT,
)
from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
)
from tuc.runtime import (
    RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_runtime_backend_alignment.json"
)
SCHEMA_PATH = Path(
    "schemas/"
    "source_to_intent_research_kernel_ingress_runtime_backend_alignment_report.v0.schema.json"
)


def test_kernel_ingress_runtime_backend_alignment_report_shape() -> None:
    report = build_kernel_ingress_runtime_backend_alignment_report()
    assert_kernel_ingress_runtime_backend_alignment_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_REPORT_SCHEMA_VERSION
    )
    assert report["alignment_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT
    )
    assert report["runtime_matrix_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
    )
    assert report["runtime_coverage_policy_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
    )
    assert report["runtime_executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert report["runtime_executor_conformance_contract"] == (
        RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT
    )
    assert report["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert report["status"] == "PASS"
    assert report["required_backend_names"] == ["linear-sim", "vector-sim"]
    assert report["observed_backend_names"] == ["linear-sim", "vector-sim"]
    assert report["backend_support_matrix"] == [
        {
            "backend_name": "linear-sim",
            "status": "trusted_conformant",
            "supported_operation_families": ["matmul", "reduction"],
        },
        {
            "backend_name": "vector-sim",
            "status": "trusted_conformant",
            "supported_operation_families": ["elementwise", "reduction", "softmax"],
        },
    ]
    assert [case["status"] for case in report["case_alignments"]] == [
        "aligned",
        "aligned",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("required_backend_names", ["linear-sim"], "required_backend_names"),
        ("alignment_contract", "other", "alignment_contract"),
        ("raw_source", "import triton", "top-level report"),
    ],
)
def test_kernel_ingress_runtime_backend_alignment_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_runtime_backend_alignment_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_runtime_backend_alignment_report_contract(report)


def test_kernel_ingress_runtime_backend_alignment_rejects_case_drift() -> None:
    report = build_kernel_ingress_runtime_backend_alignment_report()
    cases = report["case_alignments"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["status"] = "drift"

    with pytest.raises(ValueError, match="status drift"):
        assert_kernel_ingress_runtime_backend_alignment_report_contract(report)


def test_kernel_ingress_runtime_backend_alignment_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_runtime_backend_alignment_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            (
                "examples/"
                "source_to_intent_research_kernel_ingress_runtime_backend_alignment.py"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"alignment_contract"' in completed.stdout
    assert '"runtime_executor_conformance_digest"' in completed.stdout
    assert TRUSTED_RUNTIME_EXECUTOR_REGISTRY in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_kernel_ingress_runtime_backend_alignment_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["alignment_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT_CONTRACT
    )
    assert schema["properties"]["trusted_executor_registry"]["const"] == (
        TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    )
    assert schema["additionalProperties"] is False
    first_backend = schema["properties"]["backend_support_matrix"]["prefixItems"][0]
    assert first_backend["additionalProperties"] is False
    assert "runtime_executor_conformance_digest" in schema["required"]


def test_kernel_ingress_runtime_backend_alignment_is_documented_and_in_ci() -> None:
    example_path = (
        "examples/"
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment.py"
    )
    doc_path = (
        "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md"
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
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path(
            "rfcs/"
            "0175-source-to-intent-research-kernel-ingress-runtime-backend-alignment.md"
        ),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
