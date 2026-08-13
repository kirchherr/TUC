from __future__ import annotations

from pathlib import Path


def test_external_review_triage_preserves_research_scope() -> None:
    text = Path("docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "research prototype",
        "It is not a CUDA, ROCm, XLA, TVM, IREE",
        "vendor compiler replacement claim",
        "Adopt Now",
        "Adopt Later",
        "Do Not Adopt",
        "Research Onboarding Slice",
        "Performance Evidence Path",
        "Real Hardware Integration",
        "native performance claims remain blocked",
        "no dynamic plugin discovery is introduced",
        "source, manifests, IR, evidence reports, and benchmark metadata remain",
    ):
        assert expected in text


def test_research_onboarding_slice_is_short_and_bounded() -> None:
    text = Path("docs/RESEARCH_ONBOARDING_SLICE.md").read_text(encoding="utf-8")

    for expected in (
        "Graph",
        "HAC-IR",
        "Runtime Plan",
        "reference-cpu",
        "systolic-sim",
        "vector-sim",
        "python examples/proof_of_execution.py",
        "python examples/runtime_evidence_matrix.py",
        "python examples/runtime_evidence_gate.py",
        "What This Proves",
        "What This Does Not Prove",
        "Native performance parity",
        "Broad source-code parsing",
        "Arbitrary third-party backend execution",
        "docs/EXTERNAL_REVIEW_TRIAGE_2026_06_22.md",
    ):
        assert expected in text


def test_review_triage_is_discoverable_from_project_surfaces() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    roadmap = Path("ROADMAP.md").read_text(encoding="utf-8")
    status = Path("docs/ROADMAP_STATUS.md").read_text(encoding="utf-8")
    rfc = Path("rfcs/0198-external-review-triage-and-onboarding.md").read_text(
        encoding="utf-8"
    )

    for text in (readme, roadmap, status, rfc):
        assert "EXTERNAL_REVIEW_TRIAGE_2026_06_22.md" in text

    assert "RESEARCH_ONBOARDING_SLICE.md" in readme
    assert "RESEARCH_ONBOARDING_SLICE.md" in roadmap
    assert "RESEARCH_ONBOARDING_SLICE.md" in status
