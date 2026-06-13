"""Readiness reporting for future source-to-intent parser proposals.

This module does not parse source text, inspect preflight reports, load files,
import frontend modules, discover plugins, or produce compiler artifacts. It
only turns explicit evidence flags into a bounded, deterministic review report.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

SOURCE_TO_INTENT_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_readiness_report.v0"
)
SOURCE_TO_INTENT_PARSER_GATE_CONTRACT = "source_to_intent_parser_gate.blocking.v0"
SOURCE_TO_INTENT_REQUIRED_EVIDENCE = (
    "parser_rfc",
    "parser_threat_model_update",
    "parser_budget_table",
    "accepted_source_corpus",
    "rejected_source_corpus",
    "source_fuzz_or_property_corpus",
    "parser_report_golden",
    "source_intent_plain_data_golden",
    "source_intent_intake_report_golden",
    "source_intent_metadata_report_golden",
    "source_to_intent_research_diagnostics",
    "metadata_intake_report_golden",
    "hac_ir_golden",
    "runtime_plan_golden",
    "compiler_decision_report_golden",
    "hac_ir_neutrality_review",
    "source_intent_frontend_conformance_report",
    "source_intent_frontend_conformance_gate",
)
SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES = (
    "backend_artifact_execution",
    "bytecode_compilation",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "environment_dependent_behavior",
    "frontend_module_import",
    "generated_artifact_execution",
    "host_file_read_after_source_buffer",
    "network_access",
    "plugin_discovery",
    "python_function_inspection",
    "subprocess_execution",
    "triton_jit_execution",
)
MAX_SOURCE_TO_INTENT_READINESS_REPORT_BYTES = 64 * 1024
MAX_SOURCE_TO_INTENT_READINESS_FIELD_BYTES = 512
MAX_SOURCE_TO_INTENT_READINESS_ISSUES = 128


@dataclass(frozen=True)
class SourceToIntentReadinessEvidence:
    """One explicit evidence flag for the source-to-intent parser gate."""

    evidence_id: str
    present: bool


@dataclass(frozen=True)
class SourceToIntentReadinessIssue:
    """One missing or invalid parser-readiness evidence item."""

    evidence_id: str
    message: str


@dataclass(frozen=True)
class SourceToIntentReadinessReport:
    """Review report for a future source-to-intent parser proposal."""

    proposal_name: str
    gate_contract: str
    checked_evidence: tuple[SourceToIntentReadinessEvidence, ...]
    blocked_execution_surfaces: tuple[str, ...]
    issues: tuple[SourceToIntentReadinessIssue, ...]

    @property
    def ready(self) -> bool:
        return not self.issues


class SourceToIntentReadinessError(AssertionError):
    """Raised when a source-to-intent parser proposal is not ready."""


def build_source_to_intent_readiness_report(
    proposal_name: str,
    evidence: Iterable[SourceToIntentReadinessEvidence],
) -> SourceToIntentReadinessReport:
    """Build a bounded review report for parser-gate readiness evidence."""

    _validate_report_text(proposal_name, "proposal_name")
    evidence_by_id = _normalize_evidence(evidence)
    checked_evidence = tuple(
        SourceToIntentReadinessEvidence(
            evidence_id=evidence_id,
            present=evidence_by_id.get(evidence_id, False),
        )
        for evidence_id in SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    )
    issues = tuple(
        SourceToIntentReadinessIssue(
            evidence_id=item.evidence_id,
            message="required source-to-intent parser gate evidence is missing",
        )
        for item in checked_evidence
        if not item.present
    )
    return SourceToIntentReadinessReport(
        proposal_name=proposal_name,
        gate_contract=SOURCE_TO_INTENT_PARSER_GATE_CONTRACT,
        checked_evidence=checked_evidence,
        blocked_execution_surfaces=SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES,
        issues=issues,
    )


def assert_source_to_intent_readiness(
    proposal_name: str,
    evidence: Iterable[SourceToIntentReadinessEvidence],
) -> SourceToIntentReadinessReport:
    """Raise unless a parser proposal satisfies every gate evidence item."""

    report = build_source_to_intent_readiness_report(proposal_name, evidence)
    if report.issues:
        lines = [f"source-to-intent parser proposal {proposal_name!r} is blocked:"]
        lines.extend(f"- {issue.evidence_id}: {issue.message}" for issue in report.issues)
        raise SourceToIntentReadinessError("\n".join(lines))
    return report


def source_to_intent_readiness_report_to_dict(
    report: SourceToIntentReadinessReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible readiness report payload."""

    _validate_report(report)
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "checked_evidence": [
            {
                "evidence_id": item.evidence_id,
                "present": item.present,
            }
            for item in report.checked_evidence
        ],
        "gate_contract": report.gate_contract,
        "issues": [
            {
                "evidence_id": issue.evidence_id,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "proposal_name": report.proposal_name,
        "ready": report.ready,
        "schema_version": SOURCE_TO_INTENT_READINESS_REPORT_SCHEMA_VERSION,
    }


def dump_source_to_intent_readiness_report(
    report: SourceToIntentReadinessReport,
) -> str:
    """Render a stable review artifact for parser-gate readiness evidence."""

    text = json.dumps(
        source_to_intent_readiness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_TO_INTENT_READINESS_REPORT_BYTES:
        raise ValueError("source-to-intent readiness report exceeds byte limit")
    return text + "\n"


def _normalize_evidence(
    evidence: Iterable[SourceToIntentReadinessEvidence],
) -> dict[str, bool]:
    evidence_by_id: dict[str, bool] = {}
    allowed_ids = frozenset(SOURCE_TO_INTENT_REQUIRED_EVIDENCE)
    for item in tuple(evidence):
        if not isinstance(item, SourceToIntentReadinessEvidence):
            raise TypeError(
                "source-to-intent readiness evidence must be "
                "SourceToIntentReadinessEvidence"
            )
        _validate_report_text(item.evidence_id, "evidence_id")
        if item.evidence_id not in allowed_ids:
            raise ValueError(f"unsupported source-to-intent evidence id: {item.evidence_id}")
        if item.evidence_id in evidence_by_id:
            raise ValueError(f"duplicate source-to-intent evidence id: {item.evidence_id}")
        if type(item.present) is not bool:
            raise TypeError("source-to-intent evidence present must be bool")
        evidence_by_id[item.evidence_id] = item.present
    return evidence_by_id


def _validate_report(report: SourceToIntentReadinessReport) -> None:
    if not isinstance(report, SourceToIntentReadinessReport):
        raise TypeError("source-to-intent readiness report must be report object")
    _validate_report_text(report.proposal_name, "proposal_name")
    if report.gate_contract != SOURCE_TO_INTENT_PARSER_GATE_CONTRACT:
        raise ValueError(
            "source-to-intent readiness report gate contract must be "
            f"{SOURCE_TO_INTENT_PARSER_GATE_CONTRACT!r}"
        )
    expected_evidence = SOURCE_TO_INTENT_REQUIRED_EVIDENCE
    if tuple(item.evidence_id for item in report.checked_evidence) != expected_evidence:
        raise ValueError("source-to-intent readiness evidence order must match gate")
    for item in report.checked_evidence:
        if not isinstance(item, SourceToIntentReadinessEvidence):
            raise TypeError("source-to-intent checked evidence must be evidence objects")
        if type(item.present) is not bool:
            raise TypeError("source-to-intent checked evidence present must be bool")
    if (
        tuple(report.blocked_execution_surfaces)
        != SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES
    ):
        raise ValueError("source-to-intent blocked surfaces must match gate")
    if len(report.issues) > MAX_SOURCE_TO_INTENT_READINESS_ISSUES:
        raise ValueError("source-to-intent readiness report exceeds issue limit")
    for issue in report.issues:
        if not isinstance(issue, SourceToIntentReadinessIssue):
            raise TypeError("source-to-intent readiness issues must be issue objects")
        _validate_report_text(issue.evidence_id, "issue evidence_id")
        _validate_report_text(issue.message, "issue message")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_SOURCE_TO_INTENT_READINESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds source-to-intent readiness field limit")


__all__ = [
    "MAX_SOURCE_TO_INTENT_READINESS_ISSUES",
    "SOURCE_TO_INTENT_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_TO_INTENT_PARSER_GATE_CONTRACT",
    "SOURCE_TO_INTENT_READINESS_REPORT_SCHEMA_VERSION",
    "SOURCE_TO_INTENT_REQUIRED_EVIDENCE",
    "SourceToIntentReadinessError",
    "SourceToIntentReadinessEvidence",
    "SourceToIntentReadinessIssue",
    "SourceToIntentReadinessReport",
    "assert_source_to_intent_readiness",
    "build_source_to_intent_readiness_report",
    "dump_source_to_intent_readiness_report",
    "source_to_intent_readiness_report_to_dict",
]
