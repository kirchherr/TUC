from __future__ import annotations

from pathlib import Path


def test_compiler_decision_report_docs_cover_inspectability_contract() -> None:
    text = Path("docs/COMPILER_DECISION_REPORT.md").read_text(encoding="utf-8")

    for required in (
        "assigned",
        "accepted",
        "rejected",
        "fallback",
        "runtime partition plan",
        "BackendRegistry.diagnose_operation_support",
    ):
        assert required in text


def test_compiler_decision_report_docs_cover_security_boundaries() -> None:
    text = Path("docs/COMPILER_DECISION_REPORT.md").read_text(encoding="utf-8")

    for forbidden_surface in (
        "execute backend code",
        "discover plugins",
        "import modules",
        "spawn subprocesses",
        "load dynamic libraries",
        "access devices",
        "execute generated artifacts",
        "touch the network",
    ):
        assert forbidden_surface in text
