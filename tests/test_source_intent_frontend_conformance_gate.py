from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.source_intent_frontend_conformance import (
    build_source_intent_frontend_conformance_cases,
)
from examples.source_intent_frontend_conformance_gate import (
    REQUIRED_RETURN_CONFORMANCE_CASES,
    SourceIntentFrontendConformanceGateError,
    build_gate_report,
)
from tuc.frontend import (
    SourceIntentFrontendConformanceIssue,
    SourceIntentFrontendConformanceReport,
    run_source_intent_frontend_conformance,
)

_GOLDEN = Path("tests/golden/frontend/source_intent_frontend_conformance_gate.txt")


def test_source_intent_frontend_conformance_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'frontend_conformance = "passed"' in report
    assert 'return_conformance = "covered"' in report
    assert report.rstrip().endswith('status = "PASS"\n}')


def test_source_intent_frontend_conformance_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_intent_frontend_conformance_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")


def test_source_intent_frontend_conformance_gate_rejects_failed_report() -> None:
    failed = SourceIntentFrontendConformanceReport(
        frontend_name="candidate",
        checked_cases=("bad_case",),
        accepted_case_count=1,
        rejected_case_count=0,
        issues=(
            SourceIntentFrontendConformanceIssue(
                case_name="bad_case",
                message="accepted case failed intake with ValueError",
            ),
        ),
    )

    with pytest.raises(
        SourceIntentFrontendConformanceGateError,
        match="conformance failed",
    ):
        build_gate_report(conformance_report=failed)


def test_source_intent_frontend_conformance_gate_requires_return_cases() -> None:
    report = run_source_intent_frontend_conformance(
        "example-source-intent-frontend",
        build_source_intent_frontend_conformance_cases(),
    )
    missing_return_case = replace(
        report,
        checked_cases=tuple(
            case_name
            for case_name in report.checked_cases
            if case_name != REQUIRED_RETURN_CONFORMANCE_CASES[0]
        ),
        accepted_case_count=report.accepted_case_count - 1,
    )

    with pytest.raises(
        SourceIntentFrontendConformanceGateError,
        match="return conformance coverage",
    ):
        build_gate_report(conformance_report=missing_return_case)


def test_source_intent_frontend_conformance_gate_rejects_non_report() -> None:
    with pytest.raises(
        SourceIntentFrontendConformanceGateError,
        match="not a report object",
    ):
        build_gate_report(conformance_report="not_a_report")  # type: ignore[arg-type]


def test_source_intent_frontend_conformance_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_intent_frontend_conformance_gate.py"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/SOURCE_INTENT_FRONTEND_CONFORMANCE.md"),
        Path("docs/SOURCE_INTENT_FRONTEND_CONFORMANCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0121-source-intent-frontend-conformance-gate.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")
