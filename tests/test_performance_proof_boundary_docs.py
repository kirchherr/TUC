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
        "Planner overhead must not be hidden inside execution time",
        "If planning time is greater than execution time",
        "If a workload requires a hardware-specific optimization",
        "the performance parity claim fails",
        "hardware-specific performance knobs to HAC-IR",
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
        "Claim \"near native\" performance with no threshold",
        "Hide planning time inside execution time",
    ):
        assert expected in text


def test_benchmarking_doc_references_performance_boundary() -> None:
    text = Path("docs/BENCHMARKING.md").read_text(encoding="utf-8")

    for expected in (
        "This is not a performance claim",
        "Performance Proof Boundary",
        "must not be used as a native performance parity claim",
        "planner-overhead evidence",
        "native baseline provenance",
    ):
        assert expected in text


def test_proof_review_doc_blocks_performance_claims() -> None:
    text = Path("docs/PROOF_ARTIFACT_REVIEW.md").read_text(encoding="utf-8")

    for expected in (
        "does not claim native performance parity",
        "100 percent native performance",
        "Performance Proof Boundary",
        "Hidden planner overhead",
        "not performance evidence",
        "leaky-abstraction report",
        "planner-overhead report",
    ):
        assert expected in text


def test_master_plan_and_roadmap_expose_performance_limits() -> None:
    master_plan = Path("TUC_MASTER_PLAN.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    status = Path("docs/ROADMAP_STATUS.md").read_text(encoding="utf-8")

    assert "Success means mathematical correctness, not performance" in master_plan
    assert "Native performance parity is a later proof class" in master_plan
    assert "No native performance parity claim" in roadmap
    assert "Leaky Abstraction And Planner Overhead" in roadmap
    assert "Performance proof boundary" in status
