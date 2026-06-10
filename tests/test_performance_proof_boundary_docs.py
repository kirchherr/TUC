from __future__ import annotations

from pathlib import Path


def test_performance_proof_boundary_blocks_native_parity_claims() -> None:
    text = Path("docs/PERFORMANCE_PROOF_BOUNDARY.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "not a native performance parity claim",
        "does not currently claim native performance parity",
        "100 percent native performance",
        "fixed percentage of CUDA, HIP, vendor-library",
        "Leaky Abstraction Gate",
        "Planner Overhead Gate",
        "Break-Even Workload Size Gate",
        "Native Baseline Provenance Gate",
        "Native Baseline Comparison Gate",
        "Workload Scope Gate",
        "Benchmark Methodology Gate",
        "Toolchain Environment Gate",
        "Benchmark Artifact Manifest Gate",
        "Executable Backend Security Review Gate",
        "Performance Proof RFC Gate",
        "Planner overhead must not be hidden inside execution time",
        "If planning time is greater than execution time",
        "If a workload requires a hardware-specific optimization",
        "the performance parity claim fails",
        "schemas/native_baseline_provenance_report.v0.schema.json",
        "schemas/native_baseline_comparison_report.v0.schema.json",
        "schemas/break_even_workload_size_report.v0.schema.json",
        "schemas/workload_scope_report.v0.schema.json",
        "schemas/benchmark_methodology_report.v0.schema.json",
        "schemas/toolchain_environment_report.v0.schema.json",
        "schemas/benchmark_artifact_manifest_report.v0.schema.json",
        "schemas/executable_backend_security_review_report.v0.schema.json",
        "schemas/performance_proof_rfc_report.v0.schema.json",
        "hardware-specific performance knobs to HAC-IR",
        "Performance Proof RFC Report",
        "Performance Proof Readiness Report",
        "PERFORMANCE_PROOF_REQUIRED_EVIDENCE",
        "tests/golden/proofs/performance_proof_readiness_report.json",
        "does not run benchmarks",
        "does not access devices",
        "does not execute backend artifacts",
        "does not claim native performance parity",
        "must not include raw benchmark output",
        "The goal is to make performance a future proof",
    ):
        assert expected in text


def test_performance_proof_boundary_rfc_preserves_gates() -> None:
    text = Path("rfcs/0063-performance-proof-boundary.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "leaky abstraction risk",
        "runtime planner overhead",
        "does not add native benchmarks",
        "does not currently claim native performance parity",
        "Leaky Abstraction Gate",
        "Planner Overhead Gate",
        "Planner overhead must not be hidden inside execution timing",
        "Benchmark outputs, transfer-cost profiles",
        "must not become HAC-IR semantics",
        "Performance Proof Readiness Report",
        "does not run benchmarks",
        "does not access devices",
        "does not execute backend artifacts",
        "does not claim native performance parity",
        "must not include raw benchmark output",
        "Claim \"near native\" performance with no threshold",
        "Hide planning time inside execution time",
    ):
        assert expected in text


def test_performance_proof_readiness_doc_is_report_only() -> None:
    text = Path("docs/PERFORMANCE_PROOF_READINESS.md").read_text(encoding="utf-8")

    for expected in (
        "does not run benchmarks",
        "does not access devices",
        "does not execute backend artifacts",
        "does not claim native performance parity",
        "performance_proof_boundary.blocking.v0",
        "build_performance_proof_readiness_report(proposal_name, evidence)",
        "PERFORMANCE_PROOF_REQUIRED_EVIDENCE",
        "PERFORMANCE_PROOF_BLOCKED_CLAIMS",
        "tests/golden/proofs/performance_proof_readiness_report.json",
        "schemas/performance_proof_rfc_report.v0.schema.json",
        "not a performance proof RFC report",
        "Missing evidence keeps native performance claims blocked",
        "schemas/native_baseline_provenance_report.v0.schema.json",
        "schemas/native_baseline_comparison_report.v0.schema.json",
        "schemas/break_even_workload_size_report.v0.schema.json",
        "schemas/workload_scope_report.v0.schema.json",
        "schemas/benchmark_methodology_report.v0.schema.json",
        "schemas/toolchain_environment_report.v0.schema.json",
        "schemas/benchmark_artifact_manifest_report.v0.schema.json",
        "schemas/executable_backend_security_review_report.v0.schema.json",
        "must not include raw benchmark output",
        "Unknown evidence IDs and duplicate evidence IDs fail closed",
    ):
        assert expected in text


def test_performance_proof_readiness_rfc_is_report_only() -> None:
    text = Path("rfcs/0064-performance-proof-readiness-report.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "does not run benchmarks",
        "does not run subprocesses",
        "does not claim native performance parity",
        "performance_proof_boundary.blocking.v0",
        "tuc.performance_proof_readiness_report.v0",
        "leaky-abstraction and planner-overhead gaps",
        "Unknown evidence IDs and duplicate evidence IDs fail closed",
        "Performance measurements remain blocked",
        "raw benchmark results",
    ):
        assert expected in text


def test_benchmarking_doc_references_performance_boundary() -> None:
    text = Path("docs/BENCHMARKING.md").read_text(encoding="utf-8")

    for expected in (
        "This is not a performance claim",
        "Performance Proof Boundary",
        "Performance Proof RFC Report",
        "Performance Proof Readiness Report",
        "must not be used as a native performance parity claim",
        "does not run benchmarks",
        "planner-overhead evidence",
        "native baseline provenance",
        "Native Baseline Provenance Report",
        "Native Baseline Comparison Report",
        "Break-Even Workload Size Report",
        "Workload Scope Report",
        "Benchmark Methodology Report",
        "Toolchain Environment Report",
        "Benchmark Artifact Manifest Report",
        "Executable Backend Security Review Report",
    ):
        assert expected in text


def test_proof_review_doc_blocks_performance_claims() -> None:
    text = Path("docs/PROOF_ARTIFACT_REVIEW.md").read_text(encoding="utf-8")

    for expected in (
        "does not claim native performance parity",
        "100 percent native performance",
        "Performance Proof Boundary",
        "Performance Proof RFC Report",
        "Performance Proof Readiness Report",
        "Hidden planner overhead",
        "not performance evidence",
        "performance proof RFC report",
        "leaky-abstraction report",
        "native baseline provenance report",
        "native baseline comparison report",
        "break-even workload-size report",
        "workload scope report",
        "benchmark methodology report",
        "toolchain environment report",
        "benchmark artifact manifest",
        "planner-overhead report",
        "break-even workload-size report",
        "executable backend security review report",
    ):
        assert expected in text


def test_master_plan_and_roadmap_expose_performance_limits() -> None:
    master_plan = Path("TUC_MASTER_PLAN.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    status = Path("docs/ROADMAP_STATUS.md").read_text(encoding="utf-8")

    assert "Success means mathematical correctness, not performance" in master_plan
    assert "Native performance parity is a later proof class" in master_plan
    assert "Performance Proof Readiness report remains blocked" in master_plan
    assert "No native performance parity claim" in roadmap
    assert "Leaky Abstraction And Planner Overhead" in roadmap
    assert "Performance Proof RFC Report" in roadmap
    assert "Performance Proof Readiness Report" in roadmap
    assert "Performance Proof RFC Report" in status
    assert "Performance proof boundary" in status
