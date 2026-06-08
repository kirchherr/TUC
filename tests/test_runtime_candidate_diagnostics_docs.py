from __future__ import annotations

from pathlib import Path


def test_runtime_plan_docs_cover_candidate_score_diagnostics() -> None:
    text = Path("docs/RUNTIME_PLAN.md").read_text(encoding="utf-8")

    for required in (
        "Candidate Score Diagnostics",
        "include_candidate_scores=True",
        "candidate_scores",
        "selection stage",
        "transfer score and unit",
        "layout conversion bytes",
        "preferred memory-domain match",
        "not automatic global optimization",
    ):
        assert required in text


def test_compiler_decision_report_docs_cover_candidate_scores() -> None:
    text = Path("docs/COMPILER_DECISION_REPORT.md").read_text(encoding="utf-8")

    for required in (
        "candidate_scores",
        "include_candidate_scores=True",
        "review evidence",
        "not a global optimizer",
    ):
        assert required in text


def test_candidate_score_rfc_covers_security_boundaries() -> None:
    text = Path("rfcs/0044-runtime-candidate-score-diagnostics.md").read_text(
        encoding="utf-8"
    )

    for forbidden_surface in (
        "execute backend code",
        "discover plugins",
        "import modules",
        "spawn subprocesses",
        "load dynamic libraries",
        "access devices",
        "execute generated artifacts",
        "touch the network",
        "read host paths",
        "read environment variables",
        "change HAC-IR",
    ):
        assert forbidden_surface in text


def test_candidate_score_docs_link_golden_evidence() -> None:
    text = Path("rfcs/0044-runtime-candidate-score-diagnostics.md").read_text(
        encoding="utf-8"
    )

    assert "tests/golden/runtime_plans/candidate_scores.txt" in text
    assert "tests/golden/compiler_decisions/candidate_scores.txt" in text
