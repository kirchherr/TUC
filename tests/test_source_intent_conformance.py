from __future__ import annotations

from pathlib import Path

import pytest

from examples.source_intent_frontend_conformance import (
    build_source_intent_frontend_conformance_cases,
)
from examples.source_intent_intake import build_source_intent_data
from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    SourceIntentFrontendConformanceCase,
    SourceIntentFrontendConformanceError,
    SourceIntentFrontendConformanceIssue,
    SourceIntentFrontendConformanceReport,
    assert_source_intent_frontend_conformance,
    dump_source_intent_frontend_conformance_report,
    run_source_intent_frontend_conformance,
)


def test_source_intent_frontend_conformance_passes_example_cases() -> None:
    report = run_source_intent_frontend_conformance(
        "example-source-intent-frontend",
        build_source_intent_frontend_conformance_cases(),
    )

    assert report.passed
    assert report.accepted_case_count == 1
    assert report.rejected_case_count == 3
    assert report.checked_cases == (
        "valid_source_intent_mlp",
        "reject_source_text_escape",
        "reject_backend_hint_escape",
        "reject_unknown_tensor_reference",
    )


def test_source_intent_frontend_conformance_dump_matches_golden() -> None:
    report = run_source_intent_frontend_conformance(
        "example-source-intent-frontend",
        build_source_intent_frontend_conformance_cases(),
    )
    expected = (
        Path("tests/golden/frontend/source_intent_frontend_conformance_report.json")
        .read_text(encoding="utf-8")
        .rstrip("\n")
    )

    assert dump_source_intent_frontend_conformance_report(report) == expected + "\n"


def test_source_intent_frontend_conformance_detects_bad_positive_case() -> None:
    report = run_source_intent_frontend_conformance(
        "bad-positive-frontend",
        (
            SourceIntentFrontendConformanceCase(
                name="accepted_invalid_tensor_reference",
                payload=_unknown_tensor_payload(),
                should_accept=True,
            ),
            SourceIntentFrontendConformanceCase(
                name="rejected_source_text_escape",
                payload="@triton.jit\ndef kernel(): pass",
                should_accept=False,
            ),
        ),
    )

    assert not report.passed
    assert report.issues[0].case_name == "accepted_invalid_tensor_reference"
    assert report.issues[0].message == "accepted case failed intake with ValueError"


def test_source_intent_frontend_conformance_detects_bad_rejection_case() -> None:
    report = run_source_intent_frontend_conformance(
        "bad-negative-frontend",
        (
            SourceIntentFrontendConformanceCase(
                name="accepted_valid_mlp",
                payload=build_source_intent_data(),
                should_accept=True,
            ),
            SourceIntentFrontendConformanceCase(
                name="rejected_valid_mlp",
                payload=build_source_intent_data(),
                should_accept=False,
            ),
        ),
    )

    assert not report.passed
    assert report.issues == (
        SourceIntentFrontendConformanceIssue(
            case_name="rejected_valid_mlp",
            message="rejected case was accepted by source-intent intake",
        ),
    )


def test_source_intent_frontend_conformance_requires_both_case_kinds() -> None:
    report = run_source_intent_frontend_conformance(
        "missing-negative-suite",
        (
            SourceIntentFrontendConformanceCase(
                name="accepted_valid_mlp",
                payload=build_source_intent_data(),
                should_accept=True,
            ),
        ),
    )

    assert not report.passed
    assert report.issues[0].case_name == "conformance_suite"
    assert report.issues[0].message == "conformance requires at least one rejected case"


def test_assert_source_intent_frontend_conformance_raises_on_failure() -> None:
    with pytest.raises(SourceIntentFrontendConformanceError):
        assert_source_intent_frontend_conformance(
            "failing-frontend",
            (
                SourceIntentFrontendConformanceCase(
                    name="accepted_valid_mlp",
                    payload=build_source_intent_data(),
                    should_accept=True,
                ),
            ),
        )


def test_source_intent_frontend_conformance_report_rejects_oversized_text() -> None:
    report = SourceIntentFrontendConformanceReport(
        frontend_name="x" * 513,
        checked_cases=(),
        accepted_case_count=0,
        rejected_case_count=0,
        issues=(),
    )

    with pytest.raises(
        ValueError,
        match="frontend_name exceeds source-intent frontend conformance limit",
    ):
        dump_source_intent_frontend_conformance_report(report)


def _unknown_tensor_payload() -> dict[str, object]:
    return {
        "name": "bad",
        "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
        "tensors": [{"name": "a", "shape": [1]}],
        "operations": [
            {
                "name": "op",
                "family": "elementwise",
                "inputs": ["missing"],
                "outputs": ["a"],
            }
        ],
    }
