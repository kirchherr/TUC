from __future__ import annotations

from pathlib import Path


def test_proof_artifact_review_checklist_covers_contract_boundaries() -> None:
    text = Path("docs/PROOF_ARTIFACT_REVIEW.md").read_text(encoding="utf-8")

    for required in (
        "report_schema",
        "proof_id",
        "proof_version",
        "graph_family",
        "backend_set",
        "HAC-IR",
        "runtime-plan",
        "deterministic independent reference",
        "PASS",
    ):
        assert required in text


def test_proof_artifact_review_checklist_covers_security_boundaries() -> None:
    text = Path("docs/PROOF_ARTIFACT_REVIEW.md").read_text(encoding="utf-8")

    for forbidden_surface in (
        "Backend plugin discovery",
        "Dynamic imports",
        "Dynamic libraries",
        "Device access",
        "Network access",
        "Generated-artifact execution",
        "Host-path leakage",
        "Environment-variable-dependent proof behavior",
    ):
        assert forbidden_surface in text


def test_pr_template_links_proof_artifact_checklist() -> None:
    text = Path(".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")

    assert "## Proof Artifact Impact" in text
    assert "docs/PROOF_ARTIFACT_REVIEW.md" in text
