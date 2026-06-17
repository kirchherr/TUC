from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.source_to_intent_research_kernel_ingress_conformance_gate import (
    REQUIRED_ACCEPTED_CASES,
    SourceToIntentResearchKernelIngressConformanceGateError,
    build_gate_report,
    build_source_to_intent_research_kernel_ingress_conformance_cases,
    build_source_to_intent_research_kernel_ingress_results,
)
from tuc.frontend import (
    SourceIntentFrontendConformanceIssue,
    SourceIntentFrontendConformanceReport,
    run_source_intent_frontend_conformance,
)

_GOLDEN = Path(
    "tests/golden/frontend/"
    "source_to_intent_research_kernel_ingress_conformance_gate.txt"
)


def test_kernel_ingress_conformance_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'parser_status = "research_explicit_only"' in report
    assert 'default_parser_status = "default_parser_blocked"' in report
    assert 'source_intent_frontend_conformance = "passed"' in report
    assert 'input_policy = "single_triton_module_source_buffer_only"' in report
    assert report.rstrip().endswith('status = "PASS"\n}')


def test_kernel_ingress_conformance_gate_example_runs() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "examples/source_to_intent_research_kernel_ingress_conformance_gate.py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_kernel_ingress_conformance_cases_pass_reusable_conformance() -> None:
    report = run_source_intent_frontend_conformance(
        "source-to-intent-research-kernel-ingress",
        build_source_to_intent_research_kernel_ingress_conformance_cases(),
    )

    assert report.passed
    assert report.accepted_case_count == 3
    assert report.rejected_case_count == 2
    assert report.checked_cases == (
        "research_kernel_ingress_matmul_elementwise",
        "research_kernel_ingress_softmax_reduction",
        "research_kernel_ingress_matmul_reduction",
        "reject_kernel_ingress_backend_hint_escape",
        "reject_kernel_ingress_source_text_escape",
    )


def test_kernel_ingress_conformance_gate_rejects_failed_report() -> None:
    failed = SourceIntentFrontendConformanceReport(
        frontend_name="source-to-intent-research-kernel-ingress",
        checked_cases=("research_kernel_ingress_matmul_elementwise",),
        accepted_case_count=1,
        rejected_case_count=0,
        issues=(
            SourceIntentFrontendConformanceIssue(
                case_name="research_kernel_ingress_matmul_elementwise",
                message="accepted case failed intake with ValueError",
            ),
        ),
    )

    with pytest.raises(
        SourceToIntentResearchKernelIngressConformanceGateError,
        match="conformance failed",
    ):
        build_gate_report(conformance_report=failed)


def test_kernel_ingress_conformance_gate_requires_case_coverage() -> None:
    report = run_source_intent_frontend_conformance(
        "source-to-intent-research-kernel-ingress",
        build_source_to_intent_research_kernel_ingress_conformance_cases(),
    )
    missing_case = replace(
        report,
        checked_cases=tuple(
            case_name
            for case_name in report.checked_cases
            if case_name != REQUIRED_ACCEPTED_CASES[0]
        ),
        accepted_case_count=report.accepted_case_count - 1,
    )

    with pytest.raises(
        SourceToIntentResearchKernelIngressConformanceGateError,
        match="conformance coverage",
    ):
        build_gate_report(conformance_report=missing_case)


def test_kernel_ingress_conformance_gate_rejects_tampered_source_name() -> None:
    results = build_source_to_intent_research_kernel_ingress_results()
    tampered_report = replace(results[0].report, source_name="wrong_source")
    tampered_result = replace(results[0], report=tampered_report)

    with pytest.raises(
        SourceToIntentResearchKernelIngressConformanceGateError,
        match="ingress source names changed",
    ):
        build_gate_report(ingress_results=(tampered_result, *results[1:]))


def test_kernel_ingress_conformance_gate_rejects_tampered_kernel_name() -> None:
    results = build_source_to_intent_research_kernel_ingress_results()
    tampered_report = replace(results[0].report, kernel_name="wrong_kernel")
    tampered_result = replace(results[0], report=tampered_report)

    with pytest.raises(
        SourceToIntentResearchKernelIngressConformanceGateError,
        match="kernel names changed",
    ):
        build_gate_report(ingress_results=(tampered_result, *results[1:]))


def test_kernel_ingress_conformance_gate_rejects_non_report() -> None:
    with pytest.raises(
        SourceToIntentResearchKernelIngressConformanceGateError,
        match="not a conformance report",
    ):
        build_gate_report(conformance_report="not_a_report")  # type: ignore[arg-type]


def test_kernel_ingress_conformance_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_to_intent_research_kernel_ingress_conformance_gate.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0165-source-to-intent-research-kernel-ingress.md"),
        Path("rfcs/0167-source-to-intent-research-kernel-ingress-conformance-gate.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("rfcs/0167-source-to-intent-research-kernel-ingress-conformance-gate.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
