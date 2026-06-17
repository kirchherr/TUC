from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_evidence_gate import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT,
    SourceToIntentResearchKernelIngressEvidenceGateError,
    assert_kernel_ingress_evidence_gate_report_contract,
    build_gate_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress_evidence_gate.txt"
)


def test_kernel_ingress_evidence_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == GOLDEN_PATH.read_text(encoding="utf-8")
    assert (
        f'gate_contract = "{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT}"'
        in report
    )
    assert 'kernel_ingress = "passed"' in report
    assert 'boundary_budget = "passed"' in report
    assert 'rejection_coverage = "passed"' in report
    assert 'diagnostics = "passed"' in report
    assert 'conformance_gate = "passed"' in report
    assert 'idiom_alignment = "passed"' in report
    assert 'proof_bundle = "passed"' in report
    assert 'covered_rejections = "7"' in report
    assert 'status = "PASS"' in report


def test_kernel_ingress_evidence_gate_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_evidence_gate.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "sha256:" in completed.stdout
    assert "kernel_ingress_digest" in completed.stdout
    assert "rejection_coverage_digest" in completed.stdout
    assert "proof_bundle_digest" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_evidence_gate_rejects_tampered_kernel_ingress() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="kernel ingress binding missing",
    ):
        build_gate_report(kernel_ingress_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_rejection_coverage() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="rejection coverage binding missing",
    ):
        build_gate_report(rejection_coverage_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_tampered_proof_bundle() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="proof bundle binding missing",
    ):
        build_gate_report(proof_bundle_text='{"status": "PASS"}\n')


def test_kernel_ingress_evidence_gate_rejects_source_leakage() -> None:
    leaky_conformance = (
        'source_intent_frontend_conformance = "passed"\n'
        'ingress_sources = "research_matmul_elementwise,research_softmax_reduction"\n'
        'kernel_names = "matmul_elementwise,softmax_reduction"\n'
        'status = "PASS"\n'
        "@triton.jit\n"
    )

    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="forbidden source fragment",
    ):
        build_gate_report(conformance_gate_text=leaky_conformance)


def test_kernel_ingress_evidence_gate_contract_rejects_drift() -> None:
    report = build_gate_report().replace('status = "PASS"', 'status = "WARN"')

    with pytest.raises(
        SourceToIntentResearchKernelIngressEvidenceGateError,
        match="required binding missing",
    ):
        assert_kernel_ingress_evidence_gate_report_contract(report)


def test_kernel_ingress_evidence_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_to_intent_research_kernel_ingress_evidence_gate.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0169-source-to-intent-research-kernel-ingress-proof-bundle.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0172-source-to-intent-research-kernel-ingress-evidence-gate.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
