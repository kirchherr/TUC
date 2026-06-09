"""Reusable conformance fixtures for Source Intent frontend authors.

This module checks schema-versioned plain data produced by an external
frontend. It does not read files, parse source text, import frontend modules,
discover plugins, lower backend code, or execute generated artifacts.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend.source_intent_intake import source_intent_from_mapping
from tuc.frontend.source_intent_metadata import source_intent_to_triton_metadata

SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION = (
    "tuc.source_intent_frontend_conformance_report.v0"
)
MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES = 128
MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_BYTES = 64 * 1024
MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_FIELD_BYTES = 512
MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_ISSUES = 128


@dataclass(frozen=True)
class SourceIntentFrontendConformanceCase:
    """One plain-data frontend conformance case."""

    name: str
    payload: object
    should_accept: bool = True


@dataclass(frozen=True)
class SourceIntentFrontendConformanceIssue:
    """One frontend conformance failure."""

    case_name: str
    message: str


@dataclass(frozen=True)
class SourceIntentFrontendConformanceReport:
    """Result of checking Source Intent frontend conformance cases."""

    frontend_name: str
    checked_cases: tuple[str, ...]
    accepted_case_count: int
    rejected_case_count: int
    issues: tuple[SourceIntentFrontendConformanceIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


class SourceIntentFrontendConformanceError(AssertionError):
    """Raised when a Source Intent frontend fails conformance checks."""


def run_source_intent_frontend_conformance(
    frontend_name: str,
    cases: Iterable[SourceIntentFrontendConformanceCase],
) -> SourceIntentFrontendConformanceReport:
    """Run reusable conformance fixtures against frontend-produced plain data."""

    _validate_report_text(frontend_name, "frontend_name")
    normalized_cases = tuple(cases)
    if len(normalized_cases) > MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES:
        raise ValueError("source-intent frontend conformance exceeds case limit")

    checked_cases: list[str] = []
    issues: list[SourceIntentFrontendConformanceIssue] = []
    accepted_case_count = 0
    rejected_case_count = 0

    for case in normalized_cases:
        _validate_case(case)
        checked_cases.append(case.name)
        if case.should_accept:
            accepted_case_count += 1
            issues.extend(_check_accepted_case(case))
        else:
            rejected_case_count += 1
            issues.extend(_check_rejected_case(case))

    if accepted_case_count == 0:
        issues.append(
            SourceIntentFrontendConformanceIssue(
                case_name="conformance_suite",
                message="conformance requires at least one accepted case",
            )
        )
    if rejected_case_count == 0:
        issues.append(
            SourceIntentFrontendConformanceIssue(
                case_name="conformance_suite",
                message="conformance requires at least one rejected case",
            )
        )

    return SourceIntentFrontendConformanceReport(
        frontend_name=frontend_name,
        checked_cases=tuple(checked_cases),
        accepted_case_count=accepted_case_count,
        rejected_case_count=rejected_case_count,
        issues=tuple(issues),
    )


def assert_source_intent_frontend_conformance(
    frontend_name: str,
    cases: Iterable[SourceIntentFrontendConformanceCase],
) -> SourceIntentFrontendConformanceReport:
    """Raise unless frontend-produced plain data satisfies conformance."""

    report = run_source_intent_frontend_conformance(frontend_name, cases)
    if report.issues:
        lines = [f"source-intent frontend {frontend_name!r} failed conformance:"]
        lines.extend(f"- {issue.case_name}: {issue.message}" for issue in report.issues)
        raise SourceIntentFrontendConformanceError("\n".join(lines))
    return report


def source_intent_frontend_conformance_report_to_dict(
    report: SourceIntentFrontendConformanceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible conformance report payload."""

    _validate_report(report)
    return {
        "accepted_case_count": report.accepted_case_count,
        "checked_cases": list(report.checked_cases),
        "frontend_name": report.frontend_name,
        "issues": [
            {
                "case_name": issue.case_name,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "rejected_case_count": report.rejected_case_count,
        "schema_version": SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION,
    }


def dump_source_intent_frontend_conformance_report(
    report: SourceIntentFrontendConformanceReport,
) -> str:
    """Render a stable review artifact for frontend conformance evidence."""

    text = json.dumps(
        source_intent_frontend_conformance_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_BYTES
    ):
        raise ValueError("source-intent frontend conformance report exceeds byte limit")
    return text + "\n"


def _check_accepted_case(
    case: SourceIntentFrontendConformanceCase,
) -> tuple[SourceIntentFrontendConformanceIssue, ...]:
    try:
        module = source_intent_from_mapping(case.payload)
    except Exception as exc:
        return (
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message=f"accepted case failed intake with {type(exc).__name__}",
            ),
        )

    try:
        metadata = source_intent_to_triton_metadata(module)
    except Exception as exc:
        return (
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message=(
                    "accepted case failed source-intent metadata conversion "
                    f"with {type(exc).__name__}"
                ),
            ),
        )

    try:
        graph = metadata.to_compute_graph()
        compiled = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
    except Exception as exc:
        return (
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message=f"accepted case failed neutral pipeline with {type(exc).__name__}",
            ),
        )

    issues: list[SourceIntentFrontendConformanceIssue] = []
    if not compiled.partition_plan.assignments:
        issues.append(
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message="accepted case produced an empty runtime partition plan",
            )
        )
    if compiled.hac_ir.graph.name != module.name:
        issues.append(
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message="accepted case changed graph identity during compilation",
            )
        )
    if "frontend.source_intent_contract" not in graph.metadata:
        issues.append(
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message="accepted case lost source-intent contract metadata",
            )
        )
    return tuple(issues)


def _check_rejected_case(
    case: SourceIntentFrontendConformanceCase,
) -> tuple[SourceIntentFrontendConformanceIssue, ...]:
    try:
        source_intent_from_mapping(case.payload)
    except (TypeError, ValueError):
        return ()
    except Exception as exc:
        return (
            SourceIntentFrontendConformanceIssue(
                case_name=case.name,
                message=f"rejected case failed with unexpected {type(exc).__name__}",
            ),
        )

    return (
        SourceIntentFrontendConformanceIssue(
            case_name=case.name,
            message="rejected case was accepted by source-intent intake",
        ),
    )


def _validate_case(case: SourceIntentFrontendConformanceCase) -> None:
    if not isinstance(case, SourceIntentFrontendConformanceCase):
        raise TypeError(
            "source-intent frontend conformance cases must be "
            "SourceIntentFrontendConformanceCase"
        )
    _validate_report_text(case.name, "case name")
    if type(case.should_accept) is not bool:
        raise TypeError("source-intent frontend case should_accept must be bool")


def _validate_report(report: SourceIntentFrontendConformanceReport) -> None:
    if not isinstance(report, SourceIntentFrontendConformanceReport):
        raise TypeError(
            "source-intent frontend conformance report must be "
            "SourceIntentFrontendConformanceReport"
        )
    _validate_report_text(report.frontend_name, "frontend_name")
    if len(report.checked_cases) > MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES:
        raise ValueError("source-intent frontend conformance exceeds case limit")
    for case_name in report.checked_cases:
        _validate_report_text(case_name, "checked case")
    if report.accepted_case_count < 0 or report.rejected_case_count < 0:
        raise ValueError("source-intent frontend case counts must be non-negative")
    if (
        report.accepted_case_count + report.rejected_case_count
        != len(report.checked_cases)
    ):
        raise ValueError("source-intent frontend case counts must match checked cases")
    if len(report.issues) > MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_ISSUES:
        raise ValueError("source-intent frontend conformance exceeds issue limit")
    for issue in report.issues:
        if not isinstance(issue, SourceIntentFrontendConformanceIssue):
            raise TypeError(
                "source-intent frontend conformance issues must be issue objects"
            )
        _validate_report_text(issue.case_name, "issue case_name")
        _validate_report_text(issue.message, "issue message")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds source-intent frontend conformance limit")


__all__ = [
    "MAX_SOURCE_INTENT_FRONTEND_CONFORMANCE_CASES",
    "SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION",
    "SourceIntentFrontendConformanceCase",
    "SourceIntentFrontendConformanceError",
    "SourceIntentFrontendConformanceIssue",
    "SourceIntentFrontendConformanceReport",
    "assert_source_intent_frontend_conformance",
    "dump_source_intent_frontend_conformance_report",
    "run_source_intent_frontend_conformance",
    "source_intent_frontend_conformance_report_to_dict",
]
