"""Diagnostic Triton idiom coverage report.

The report records which Triton-like idioms are already covered by the
schema-versioned metadata path. It is data-only: it never parses source text,
imports Triton, executes JIT code, discovers plugins, or creates compiler
artifacts by itself.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

from tuc.ir.model import OperationKind

TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION = (
    "tuc.triton_idiom_coverage_report.v0"
)
TRITON_IDIOM_COVERAGE_CONTRACT = "triton_idiom_coverage.execution_free.v0"
TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS = "diagnostic_only"
TRITON_IDIOM_COVERAGE_PARSER_STATUS = "direct_triton_source_ingestion_blocked"
TRITON_IDIOM_COVERAGE_STATUSES = (
    "metadata_golden_covered",
    "documented_not_covered",
)
TRITON_IDIOM_COVERAGE_DEFAULT_ISSUES = (
    "triton_idiom_coverage_not_supplied",
)
TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES = (
    "bytecode_inspection",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "source_parsing",
    "subprocess_execution",
)
MAX_TRITON_IDIOM_COVERAGE_ITEMS = 128
MAX_TRITON_IDIOM_COVERAGE_FIELD_BYTES = 512
MAX_TRITON_IDIOM_COVERAGE_REPORT_BYTES = 64 * 1024

_REPORT_TEXT_RE = re.compile(r"^(not_supplied|[A-Za-z][A-Za-z0-9_.-]*)$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "bytecode",
        "callable",
        "command",
        "device_path",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_artifact",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class TritonIdiomCoverage:
    """One Triton-like idiom covered through metadata and golden evidence."""

    idiom_id: str
    operation_family: str
    metadata_example_id: str
    intake_golden_id: str
    hac_ir_golden_id: str
    runtime_plan_golden_id: str
    compiler_decision_golden_id: str
    coverage_status: str = "metadata_golden_covered"


@dataclass(frozen=True)
class TritonIdiomCoverageReport:
    """Diagnostic coverage report for the safe Triton metadata path."""

    proposal_name: str
    coverages: tuple[TritonIdiomCoverage, ...]
    issues: tuple[str, ...]

    @property
    def triton_idiom_coverage_ready(self) -> bool:
        coverage_issues = tuple(
            issue for issue in self.issues if issue.startswith("triton_idiom_coverage")
        )
        return bool(self.coverages) and not coverage_issues


def build_triton_idiom_coverage_report(
    proposal_name: str,
    coverages: Iterable[TritonIdiomCoverage] = (),
) -> TritonIdiomCoverageReport:
    """Build a bounded report for Triton metadata idiom coverage."""

    _validate_report_text(proposal_name, "proposal_name")
    normalized_coverages = _normalize_coverages(coverages)
    issues = list(TRITON_IDIOM_COVERAGE_DEFAULT_ISSUES)
    if normalized_coverages:
        issues.remove("triton_idiom_coverage_not_supplied")
    if any(
        item.coverage_status != "metadata_golden_covered"
        for item in normalized_coverages
    ):
        issues.append("triton_idiom_coverage_not_golden_covered")
    if any(_coverage_has_missing_evidence(item) for item in normalized_coverages):
        issues.append("triton_idiom_coverage_evidence_not_supplied")
    return TritonIdiomCoverageReport(
        proposal_name=proposal_name,
        coverages=normalized_coverages,
        issues=tuple(issues),
    )


def triton_idiom_coverage_report_to_dict(
    report: TritonIdiomCoverageReport,
) -> dict[str, object]:
    """Return a stable mapping for JSON serialization."""

    _validate_report(report)
    return {
        "artifact_status": TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS,
        "blocked_execution_surfaces": list(
            TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES
        ),
        "coverage_contract": TRITON_IDIOM_COVERAGE_CONTRACT,
        "coverages": [
            {
                "compiler_decision_golden_id": item.compiler_decision_golden_id,
                "coverage_status": item.coverage_status,
                "hac_ir_golden_id": item.hac_ir_golden_id,
                "idiom_id": item.idiom_id,
                "intake_golden_id": item.intake_golden_id,
                "metadata_example_id": item.metadata_example_id,
                "operation_family": item.operation_family,
                "runtime_plan_golden_id": item.runtime_plan_golden_id,
            }
            for item in report.coverages
        ],
        "direct_triton_source_ingestion": False,
        "issues": list(report.issues),
        "parser_status": TRITON_IDIOM_COVERAGE_PARSER_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION,
        "triton_idiom_coverage_ready": report.triton_idiom_coverage_ready,
    }


def dump_triton_idiom_coverage_report(
    report: TritonIdiomCoverageReport,
) -> str:
    """Render a stable JSON Triton idiom coverage report."""

    text = json.dumps(
        triton_idiom_coverage_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_TRITON_IDIOM_COVERAGE_REPORT_BYTES:
        raise ValueError("triton idiom coverage report exceeds byte limit")
    return f"{text}\n"


def _normalize_coverages(
    coverages: Iterable[TritonIdiomCoverage],
) -> tuple[TritonIdiomCoverage, ...]:
    normalized = tuple(coverages)
    if len(normalized) > MAX_TRITON_IDIOM_COVERAGE_ITEMS:
        raise ValueError("triton idiom coverage count exceeds limit")
    seen: set[str] = set()
    for item in normalized:
        if not isinstance(item, TritonIdiomCoverage):
            raise TypeError("coverage entries must be TritonIdiomCoverage")
        _validate_report_text(item.idiom_id, "idiom_id")
        if item.idiom_id in seen:
            raise ValueError("duplicate triton idiom coverage id")
        seen.add(item.idiom_id)
        _validate_operation_family(item.operation_family)
        _validate_report_text(item.metadata_example_id, "metadata_example_id")
        _validate_report_text(item.intake_golden_id, "intake_golden_id")
        _validate_report_text(item.hac_ir_golden_id, "hac_ir_golden_id")
        _validate_report_text(item.runtime_plan_golden_id, "runtime_plan_golden_id")
        _validate_report_text(
            item.compiler_decision_golden_id,
            "compiler_decision_golden_id",
        )
        if item.coverage_status not in TRITON_IDIOM_COVERAGE_STATUSES:
            raise ValueError("unsupported triton idiom coverage status")
    return normalized


def _coverage_has_missing_evidence(item: TritonIdiomCoverage) -> bool:
    return "not_supplied" in {
        item.metadata_example_id,
        item.intake_golden_id,
        item.hac_ir_golden_id,
        item.runtime_plan_golden_id,
        item.compiler_decision_golden_id,
    }


def _validate_report(report: TritonIdiomCoverageReport) -> None:
    if not isinstance(report, TritonIdiomCoverageReport):
        raise TypeError("triton idiom coverage report must be report object")
    _validate_report_text(report.proposal_name, "proposal_name")
    _normalize_coverages(report.coverages)
    for issue in report.issues:
        _validate_report_text(issue, "issue")


def _validate_operation_family(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("operation_family must be a string")
    try:
        OperationKind(value)
    except ValueError as exc:
        raise ValueError(f"unsupported triton idiom operation family: {value}") from exc


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe triton idiom coverage identifier")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"{label} must be a safe triton idiom coverage identifier")
    if len(value.encode("utf-8")) > MAX_TRITON_IDIOM_COVERAGE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds triton idiom coverage limit")


__all__ = [
    "MAX_TRITON_IDIOM_COVERAGE_FIELD_BYTES",
    "MAX_TRITON_IDIOM_COVERAGE_ITEMS",
    "MAX_TRITON_IDIOM_COVERAGE_REPORT_BYTES",
    "TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS",
    "TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES",
    "TRITON_IDIOM_COVERAGE_CONTRACT",
    "TRITON_IDIOM_COVERAGE_DEFAULT_ISSUES",
    "TRITON_IDIOM_COVERAGE_PARSER_STATUS",
    "TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION",
    "TRITON_IDIOM_COVERAGE_STATUSES",
    "TritonIdiomCoverage",
    "TritonIdiomCoverageReport",
    "build_triton_idiom_coverage_report",
    "dump_triton_idiom_coverage_report",
    "triton_idiom_coverage_report_to_dict",
]
