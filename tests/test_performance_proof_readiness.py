from __future__ import annotations

from pathlib import Path

import pytest

from examples.performance_proof_readiness import (
    _has_benchmark_report_schema_evidence,
    _has_kernel_ingress_benchmark_artifact_manifest_evidence,
    _has_kernel_ingress_benchmark_methodology_evidence,
    _has_kernel_ingress_break_even_workload_size_evidence,
    _has_kernel_ingress_executable_security_review_evidence,
    _has_kernel_ingress_golden_digest_evidence,
    _has_kernel_ingress_leaky_abstraction_evidence,
    _has_kernel_ingress_native_baseline_comparison_evidence,
    _has_kernel_ingress_native_baseline_provenance_evidence,
    _has_kernel_ingress_performance_acceptance_criteria_evidence,
    _has_kernel_ingress_performance_proof_rfc_evidence,
    _has_kernel_ingress_performance_threshold_policy_evidence,
    _has_kernel_ingress_planner_overhead_evidence,
    _has_kernel_ingress_workload_scope_evidence,
    _has_versioned_toolchain_environment_evidence,
    build_current_performance_proof_readiness_evidence,
)
from tuc import (
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
    PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION,
    PERFORMANCE_PROOF_REQUIRED_EVIDENCE,
    PerformanceProofReadinessError,
    PerformanceProofReadinessEvidence,
    PerformanceProofReadinessReport,
    assert_performance_proof_readiness,
    build_performance_proof_readiness_report,
    dump_performance_proof_readiness_report,
)


def test_performance_proof_readiness_is_complete_for_current_kernel_ingress_evidence() -> None:
    report = build_performance_proof_readiness_report(
        "current-kernel-ingress-performance-proof-readiness",
        build_current_performance_proof_readiness_evidence(),
    )

    assert report.ready
    assert report.boundary_contract == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert len(report.checked_evidence) == len(PERFORMANCE_PROOF_REQUIRED_EVIDENCE)
    assert tuple(
        item.evidence_id for item in report.checked_evidence if item.present
    ) == (
        "performance_proof_rfc",
        "performance_claim_threshold_policy",
        "performance_acceptance_criteria",
        "benchmark_methodology",
        "native_baseline_provenance",
        "versioned_toolchain_environment",
        "workload_scope",
        "correctness_goldens",
        "native_baseline_comparison",
        "leaky_abstraction_report",
        "planner_overhead_report",
        "break_even_workload_size",
        "runtime_plan_goldens",
        "compiler_decision_report_goldens",
        "benchmark_report_schema",
        "benchmark_report_artifacts",
        "executable_backend_security_review",
    )
    expected_missing = tuple(
        evidence_id
        for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
        if evidence_id
        not in {
            "performance_proof_rfc",
            "performance_claim_threshold_policy",
            "performance_acceptance_criteria",
            "workload_scope",
            "benchmark_methodology",
            "native_baseline_provenance",
            "versioned_toolchain_environment",
            "native_baseline_comparison",
            "correctness_goldens",
            "leaky_abstraction_report",
            "planner_overhead_report",
            "break_even_workload_size",
            "runtime_plan_goldens",
            "compiler_decision_report_goldens",
            "benchmark_report_schema",
            "benchmark_report_artifacts",
            "executable_backend_security_review",
        }
    )
    assert expected_missing == ()
    assert tuple(issue.evidence_id for issue in report.issues) == expected_missing


def test_current_kernel_ingress_readiness_evidence_is_contract_checked() -> None:
    assert _has_kernel_ingress_performance_proof_rfc_evidence()
    assert _has_kernel_ingress_performance_threshold_policy_evidence()
    assert _has_kernel_ingress_performance_acceptance_criteria_evidence()
    assert _has_kernel_ingress_workload_scope_evidence()
    assert _has_kernel_ingress_break_even_workload_size_evidence()
    assert _has_kernel_ingress_benchmark_methodology_evidence()
    assert _has_kernel_ingress_native_baseline_provenance_evidence()
    assert _has_kernel_ingress_native_baseline_comparison_evidence()
    assert _has_versioned_toolchain_environment_evidence()
    assert _has_kernel_ingress_leaky_abstraction_evidence()
    assert _has_kernel_ingress_planner_overhead_evidence()
    assert _has_kernel_ingress_golden_digest_evidence("correctness_goldens")
    assert _has_kernel_ingress_golden_digest_evidence("runtime_plan_goldens")
    assert _has_kernel_ingress_golden_digest_evidence(
        "compiler_decision_report_goldens"
    )
    assert _has_benchmark_report_schema_evidence()
    assert _has_kernel_ingress_benchmark_artifact_manifest_evidence()
    assert _has_kernel_ingress_executable_security_review_evidence()


def test_performance_proof_readiness_dump_matches_golden() -> None:
    report = build_performance_proof_readiness_report(
        "current-kernel-ingress-performance-proof-readiness",
        build_current_performance_proof_readiness_evidence(),
    )
    expected = (
        Path("tests/golden/proofs/performance_proof_readiness_report.json")
        .read_text(encoding="utf-8")
        .rstrip("\n")
    )

    assert dump_performance_proof_readiness_report(report) == expected + "\n"


def test_performance_proof_readiness_passes_with_all_required_evidence() -> None:
    report = build_performance_proof_readiness_report(
        "fully-evidenced-performance-proof",
        tuple(
            PerformanceProofReadinessEvidence(evidence_id=evidence_id, present=True)
            for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
        ),
    )

    assert report.ready
    assert report.issues == ()
    assert all(item.present for item in report.checked_evidence)


def test_performance_proof_readiness_rejects_unknown_evidence() -> None:
    with pytest.raises(ValueError, match="unsupported performance proof evidence id"):
        build_performance_proof_readiness_report(
            "bad-performance-proof",
            (
                PerformanceProofReadinessEvidence(
                    evidence_id="raw_cuda_benchmark_score",
                    present=True,
                ),
            ),
        )


def test_performance_proof_readiness_rejects_duplicate_evidence() -> None:
    with pytest.raises(ValueError, match="duplicate performance proof evidence id"):
        build_performance_proof_readiness_report(
            "duplicate-performance-proof",
            (
                PerformanceProofReadinessEvidence(
                    evidence_id="performance_proof_rfc",
                    present=True,
                ),
                PerformanceProofReadinessEvidence(
                    evidence_id="performance_proof_rfc",
                    present=True,
                ),
            ),
        )


def test_assert_performance_proof_readiness_passes_current_evidence() -> None:
    report = assert_performance_proof_readiness(
        "current-kernel-ingress-performance-proof-readiness",
        build_current_performance_proof_readiness_evidence(),
    )

    assert report.ready


def test_assert_performance_proof_readiness_raises_on_missing_evidence() -> None:
    with pytest.raises(PerformanceProofReadinessError):
        assert_performance_proof_readiness(
            "blocked-performance-proof",
            (
                PerformanceProofReadinessEvidence(
                    evidence_id="performance_proof_rfc",
                    present=True,
                ),
            ),
        )


def test_performance_proof_readiness_report_rejects_oversized_text() -> None:
    report = PerformanceProofReadinessReport(
        proposal_name="x" * 513,
        boundary_contract=PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        checked_evidence=(),
        blocked_claims=(),
        issues=(),
    )

    with pytest.raises(
        ValueError,
        match="proposal_name exceeds performance proof readiness field limit",
    ):
        dump_performance_proof_readiness_report(report)


def test_performance_proof_readiness_report_schema_version_is_stable() -> None:
    report = build_performance_proof_readiness_report(
        "current-kernel-ingress-performance-proof-readiness",
        build_current_performance_proof_readiness_evidence(),
    )

    assert (
        dump_performance_proof_readiness_report(report)
        .split('"schema_version": "', 1)[1]
        .split('"', 1)[0]
        == PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION
    )
