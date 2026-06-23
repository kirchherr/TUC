from __future__ import annotations

from pathlib import Path


def test_minimal_walkthrough_and_equivalence_docs_are_discoverable() -> None:
    runtime_flow = Path("docs/RUNTIME_EVIDENCE_FLOW.md").read_text(
        encoding="utf-8"
    )
    backend_equivalence = Path("docs/RUNTIME_BACKEND_EQUIVALENCE.md").read_text(
        encoding="utf-8"
    )
    status = Path("docs/ROADMAP_STATUS.md").read_text(encoding="utf-8")

    assert "MINIMAL_TUC_WALKTHROUGH.md" in runtime_flow
    assert "PROOF_OF_BACKEND_EQUIVALENCE.md" in runtime_flow
    assert "PROOF_OF_BACKEND_EQUIVALENCE.md" in backend_equivalence

    for expected in (
        "MINIMAL_TUC_WALKTHROUGH.md",
        "PROOF_OF_BACKEND_EQUIVALENCE.md",
        "0212-runtime-layout-conversion-evidence.md",
        "without expanding the README",
        "hidden",
        "device-residency claims",
        "optional data-only",
    ):
        assert expected in status
