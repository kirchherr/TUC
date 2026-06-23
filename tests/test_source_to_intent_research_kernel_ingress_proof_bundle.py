from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REPORT_SCHEMA_VERSION,
    assert_kernel_ingress_proof_bundle_report_contract,
    build_kernel_ingress_proof_bundle_report,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_proof_bundle.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_kernel_ingress_proof_bundle_report.v0.schema.json"
)


def test_kernel_ingress_proof_bundle_report_shape() -> None:
    report = build_kernel_ingress_proof_bundle_report()
    assert_kernel_ingress_proof_bundle_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert report["bundle_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["artifact_count"] == 15
    assert report["claim"] == "realistic_triton_module_ingress_research_slice"
    assert report["accepted_source_names"] == [
        "research_matmul_elementwise",
        "research_softmax_reduction",
        "research_matmul_reduction",
        "research_mvp_pipeline",
    ]
    assert report["accepted_kernel_names"] == [
        "matmul_elementwise",
        "softmax_reduction",
        "matmul_reduction",
        "mvp_pipeline",
    ]
    assert [artifact["artifact_id"] for artifact in report["artifacts"]] == (
        report["required_artifacts"]
    )


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("artifact_count", 14, "artifact_count"),
        ("blocked_claims", [], "blocked_claims"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_kernel_ingress_proof_bundle_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_kernel_ingress_proof_bundle_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_kernel_ingress_proof_bundle_report_contract(report)


def test_kernel_ingress_proof_bundle_contract_rejects_artifact_drift() -> None:
    report = build_kernel_ingress_proof_bundle_report()
    artifacts = report["artifacts"]
    assert isinstance(artifacts, list)
    assert isinstance(artifacts[0], dict)
    artifacts[0]["digest"] = "sha256:" + "0" * 63

    with pytest.raises(ValueError, match="digest drift"):
        assert_kernel_ingress_proof_bundle_report_contract(report)


def test_kernel_ingress_proof_bundle_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_kernel_ingress_proof_bundle_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_proof_bundle.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"artifact_count": 15' in completed.stdout
    assert "realistic_triton_module_ingress_research_slice" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_proof_bundle_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["bundle_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE_CONTRACT
    )
    assert schema["properties"]["artifact_count"]["const"] == 15
    assert schema["$defs"]["artifact"]["additionalProperties"] is False
    assert "blocked_claims" in schema["required"]


def test_kernel_ingress_proof_bundle_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_kernel_ingress_proof_bundle.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_BACKEND_ALIGNMENT.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0170-source-to-intent-research-kernel-ingress-boundary-budget.md"),
        Path("rfcs/0171-source-to-intent-research-kernel-ingress-rejection-coverage.md"),
        Path("rfcs/0173-source-to-intent-research-kernel-ingress-runtime-matrix.md"),
        Path(
            "rfcs/"
            "0180-source-to-intent-research-kernel-ingress-runtime-step-trace.md"
        ),
        Path(
            "rfcs/"
            "0181-source-to-intent-research-kernel-ingress-runtime-evidence-bundle-index.md"
        ),
        Path(
            "rfcs/"
            "0209-source-to-intent-research-kernel-ingress-runtime-output-closure-index.md"
        ),
        Path(
            "rfcs/"
            "0211-source-to-intent-research-kernel-ingress-runtime-replay-verifier-index.md"
        ),
        Path(
            "rfcs/"
            "0182-source-to-intent-research-kernel-ingress-backend-equivalence.md"
        ),
        Path(
            "rfcs/"
            "0183-source-to-intent-research-kernel-ingress-backend-equivalence-shape-profiles.md"
        ),
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
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
