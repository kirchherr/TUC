from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/security.yml")


def test_scorecard_runs_only_for_default_branch_or_schedule() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "github.event_name == 'schedule'" in workflow
    assert "github.event_name == 'push'" in workflow
    assert "github.ref_name == github.event.repository.default_branch" in workflow
    assert "if: github.event_name != 'pull_request'" not in workflow
