"""Diagnostic evidence for the explicit Source-to-Intent research parser.

The report builder executes only the narrow, explicit research parser against
caller-provided source buffers. It emits deterministic metadata about accepted
and rejected cases without serializing raw source, Source Intent payloads,
metadata, graphs, runtime plans, backend decisions, or exception text.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent_intake import SOURCE_INTENT_SCHEMA_VERSION
from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchParserError,
    parse_triton_source_to_source_intent,
    source_to_intent_research_parse_report_to_dict,
)

SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_diagnostics_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT = (
    "source_to_intent_research_diagnostics.execution_free.v0"
)
SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASE_EXPECTATIONS = frozenset(
    {"accepted", "rejected"}
)
SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS = {
    "missing_axis_keyword": "requires explicit axis",
    "preflight_decorator_call": "decorator_call",
    "preflight_import_statement": "import_statement",
    "unsupported_assignment_value": "assignment value must be a supported call",
}
MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASES = 32
MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_BYTES = 128 * 1024
MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_SOURCE_BYTES = 64 * 1024
MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_FIELD_BYTES = 256

_DIAGNOSTIC_TEXT_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class SourceToIntentResearchDiagnosticCase:
    """One parser diagnostic input case.

    The source buffer is used only while building diagnostics and is never
    copied into the emitted report.
    """

    case_id: str
    expectation: str
    source: str
    source_name: str
    tensor_shapes: Mapping[str, Sequence[int]]
    expected_rejection_reason: str = ""

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_identifier(self.source_name, "source_name")
        if self.expectation not in SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASE_EXPECTATIONS:
            raise ValueError("source-to-intent research diagnostic expectation unsupported")
        if not isinstance(self.source, str) or not self.source:
            raise ValueError("source-to-intent research diagnostic source must be text")
        source_bytes = len(self.source.encode("utf-8"))
        if source_bytes > MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_SOURCE_BYTES:
            raise ValueError("source-to-intent research diagnostic source exceeds budget")
        if not isinstance(self.tensor_shapes, Mapping):
            raise TypeError("source-to-intent research diagnostic shapes must be a mapping")
        if self.expectation == "accepted" and self.expected_rejection_reason:
            raise ValueError("accepted diagnostic cases must not expect rejection")
        if self.expectation == "rejected":
            if not self.expected_rejection_reason:
                raise ValueError("rejected diagnostic cases must name a rejection reason")
            if (
                self.expected_rejection_reason
                not in SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS
            ):
                raise ValueError("source-to-intent research rejection reason unsupported")


@dataclass(frozen=True)
class SourceToIntentResearchDiagnosticResult:
    """One source-free diagnostic outcome."""

    case_id: str
    expectation: str
    outcome: str
    source_name: str
    source_bytes: int
    source_digest: str
    operation_families: tuple[str, ...] = ()
    parser_report_digest: str = ""
    rejection_reason: str = ""

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_identifier(self.source_name, "source_name")
        if self.expectation not in SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASE_EXPECTATIONS:
            raise ValueError("source-to-intent research diagnostic expectation unsupported")
        if self.outcome not in SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASE_EXPECTATIONS:
            raise ValueError("source-to-intent research diagnostic outcome unsupported")
        if self.expectation != self.outcome:
            raise ValueError("source-to-intent research diagnostic outcome mismatch")
        _validate_positive_int(self.source_bytes, "source_bytes")
        _validate_digest(self.source_digest, "source_digest")
        _validate_operation_families(self.operation_families)
        if self.outcome == "accepted":
            _validate_digest(self.parser_report_digest, "parser_report_digest")
            if self.rejection_reason:
                raise ValueError("accepted diagnostic result must not reject")
        else:
            if self.parser_report_digest:
                raise ValueError("rejected diagnostic result must not carry parser digest")
            if (
                self.rejection_reason
                not in SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS
            ):
                raise ValueError("source-to-intent research rejection reason unsupported")


@dataclass(frozen=True)
class SourceToIntentResearchDiagnosticsReport:
    """Source-free diagnostic report for the explicit research parser."""

    cases: tuple[SourceToIntentResearchDiagnosticResult, ...]
    diagnostics_contract: str = SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT
    parser_contract: str = SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    default_parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    output_policy: str = SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    raw_source_policy: str = SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY
    source_intent_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.diagnostics_contract != SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT:
            raise ValueError("source-to-intent research diagnostics contract mismatch")
        if self.parser_contract != SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT:
            raise ValueError("source-to-intent research diagnostics parser mismatch")
        if self.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise ValueError("source-to-intent research diagnostics status mismatch")
        if self.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
            raise ValueError("source-to-intent research diagnostics default status mismatch")
        if self.output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise ValueError("source-to-intent research diagnostics output policy mismatch")
        if self.raw_source_policy != (
            SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY
        ):
            raise ValueError("source-to-intent research diagnostics must omit raw source")
        if self.source_intent_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise ValueError("source-to-intent research diagnostics schema mismatch")
        if (
            self.blocked_compiler_outputs
            != SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("source-to-intent research diagnostics outputs changed")
        if (
            self.blocked_execution_surfaces
            != SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source-to-intent research diagnostics surfaces changed")
        if type(self.cases) is not tuple:
            raise TypeError("source-to-intent research diagnostic cases must be a tuple")
        if not self.cases:
            raise ValueError("source-to-intent research diagnostics require cases")
        if len(self.cases) > MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASES:
            raise ValueError("source-to-intent research diagnostic case limit exceeded")
        case_ids: list[str] = []
        digests: list[str] = []
        for case in self.cases:
            if not isinstance(case, SourceToIntentResearchDiagnosticResult):
                raise TypeError("source-to-intent research diagnostics need result cases")
            case_ids.append(case.case_id)
            digests.append(case.source_digest)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("source-to-intent research diagnostic case IDs must be unique")
        if len(digests) != len(set(digests)):
            raise ValueError("source-to-intent research diagnostic digests must be unique")
        if not self.accepted_case_count:
            raise ValueError("source-to-intent research diagnostics need accepted cases")
        if not self.rejected_case_count:
            raise ValueError("source-to-intent research diagnostics need rejected cases")

    @property
    def accepted_case_count(self) -> int:
        """Return accepted diagnostic case count."""

        return sum(1 for case in self.cases if case.outcome == "accepted")

    @property
    def rejected_case_count(self) -> int:
        """Return rejected diagnostic case count."""

        return sum(1 for case in self.cases if case.outcome == "rejected")

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        """Return sorted rejection reasons observed by the report."""

        return tuple(
            sorted(case.rejection_reason for case in self.cases if case.rejection_reason)
        )


def build_source_to_intent_research_diagnostics_report(
    cases: tuple[SourceToIntentResearchDiagnosticCase, ...],
) -> SourceToIntentResearchDiagnosticsReport:
    """Run explicit research parser diagnostics and return source-free evidence."""

    if type(cases) is not tuple:
        raise TypeError("source-to-intent research diagnostic cases must be a tuple")
    results = tuple(_run_diagnostic_case(case) for case in cases)
    return SourceToIntentResearchDiagnosticsReport(cases=results)


def source_to_intent_research_diagnostics_report_to_dict(
    report: SourceToIntentResearchDiagnosticsReport,
) -> dict[str, object]:
    """Return a JSON-compatible research parser diagnostics report."""

    if not isinstance(report, SourceToIntentResearchDiagnosticsReport):
        raise TypeError("source-to-intent research diagnostics report must be report")
    return {
        "accepted_case_count": report.accepted_case_count,
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "cases": [
            {
                "case_id": case.case_id,
                "expectation": case.expectation,
                "operation_families": list(case.operation_families),
                "outcome": case.outcome,
                "parser_report_digest": case.parser_report_digest,
                "rejection_reason": case.rejection_reason,
                "source_bytes": case.source_bytes,
                "source_digest": case.source_digest,
                "source_name": case.source_name,
            }
            for case in report.cases
        ],
        "default_parser_status": report.default_parser_status,
        "diagnostics_contract": report.diagnostics_contract,
        "output_policy": report.output_policy,
        "parser_contract": report.parser_contract,
        "parser_status": report.parser_status,
        "raw_source_policy": report.raw_source_policy,
        "rejected_case_count": report.rejected_case_count,
        "rejection_reasons": list(report.rejection_reasons),
        "schema_version": SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_SCHEMA_VERSION,
        "source_intent_schema_version": report.source_intent_schema_version,
    }


def dump_source_to_intent_research_diagnostics_report(
    report: SourceToIntentResearchDiagnosticsReport,
) -> str:
    """Render stable source-free research parser diagnostics evidence."""

    text = json.dumps(
        source_to_intent_research_diagnostics_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > (
        MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_BYTES
    ):
        raise ValueError("source-to-intent research diagnostics report exceeds budget")
    return text + "\n"


def _run_diagnostic_case(
    case: SourceToIntentResearchDiagnosticCase,
) -> SourceToIntentResearchDiagnosticResult:
    if not isinstance(case, SourceToIntentResearchDiagnosticCase):
        raise TypeError("source-to-intent research diagnostic case must be a case")
    source_bytes = case.source.encode("utf-8")
    source_digest = f"sha256:{sha256(source_bytes).hexdigest()}"
    try:
        result = parse_triton_source_to_source_intent(
            case.source,
            source_name=case.source_name,
            tensor_shapes=case.tensor_shapes,
        )
    except (SourceToIntentResearchParserError, TypeError, ValueError) as exc:
        if case.expectation != "rejected":
            raise ValueError("accepted diagnostic case was rejected") from exc
        _assert_expected_rejection(case.expected_rejection_reason, exc)
        return SourceToIntentResearchDiagnosticResult(
            case_id=case.case_id,
            expectation=case.expectation,
            outcome="rejected",
            source_name=case.source_name,
            source_bytes=len(source_bytes),
            source_digest=source_digest,
            rejection_reason=case.expected_rejection_reason,
        )
    if case.expectation != "accepted":
        raise ValueError("rejected diagnostic case unexpectedly accepted")
    parser_report_payload = json.dumps(
        source_to_intent_research_parse_report_to_dict(result.report),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return SourceToIntentResearchDiagnosticResult(
        case_id=case.case_id,
        expectation=case.expectation,
        outcome="accepted",
        source_name=case.source_name,
        source_bytes=len(source_bytes),
        source_digest=source_digest,
        operation_families=result.report.operation_families,
        parser_report_digest=f"sha256:{sha256(parser_report_payload).hexdigest()}",
    )


def _assert_expected_rejection(reason: str, exc: Exception) -> None:
    fragment = SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS[reason]
    if fragment not in str(exc):
        raise ValueError("source-to-intent research diagnostic reason mismatch") from exc


def _validate_operation_families(values: tuple[str, ...]) -> None:
    if type(values) is not tuple:
        raise TypeError("source-to-intent research diagnostic families must be a tuple")
    if tuple(sorted(values)) != values:
        raise ValueError("source-to-intent research diagnostic families must be sorted")
    if len(values) != len(set(values)):
        raise ValueError("source-to-intent research diagnostic families must be unique")
    for value in values:
        _validate_report_text(value, "operation_family")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"source-to-intent research diagnostic {label} must be positive")


def _validate_digest(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != len("sha256:") + 64
    ):
        raise ValueError(f"source-to-intent research diagnostic {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIAGNOSTIC_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"source-to-intent research diagnostic {label} must be report-safe text"
        )
    if (
        len(value.encode("utf-8"))
        > MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_FIELD_BYTES
    ):
        raise ValueError(f"source-to-intent research diagnostic {label} exceeds budget")


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"source-to-intent research diagnostic {label} invalid")
    if (
        len(value.encode("utf-8"))
        > MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_FIELD_BYTES
    ):
        raise ValueError(f"source-to-intent research diagnostic {label} exceeds budget")


__all__ = [
    "MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASES",
    "MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_BYTES",
    "MAX_SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_SOURCE_BYTES",
    "SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CASE_EXPECTATIONS",
    "SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT",
    "SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY",
    "SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REJECTION_REASONS",
    "SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_REPORT_SCHEMA_VERSION",
    "SourceToIntentResearchDiagnosticCase",
    "SourceToIntentResearchDiagnosticResult",
    "SourceToIntentResearchDiagnosticsReport",
    "build_source_to_intent_research_diagnostics_report",
    "dump_source_to_intent_research_diagnostics_report",
    "source_to_intent_research_diagnostics_report_to_dict",
]
