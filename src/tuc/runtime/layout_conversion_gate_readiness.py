"""Data-only readiness for requiring runtime layout-conversion evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.layout_conversion_evidence import (
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION,
    RuntimeLayoutConversionEvidenceReport,
)

RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_layout_conversion_gate_readiness_report.v0"
)
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT = (
    "runtime_layout_conversion_gate_readiness.data_only.v0"
)
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS = "review_evidence"
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND = (
    "runtime_layout_conversion_evidence"
)
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID = (
    "runtime_layout_conversion_evidence_mixed"
)
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID = (
    "runtime_mixed_backend_equivalence"
)
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS = (
    "optional_matrix_inventory_not_gate_required"
)
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_STATUSES = ("passed", "blocked")
RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS = (
    "layout_conversion_evidence_report_passes",
    "layout_conversion_schema_and_golden_stable",
    "layout_conversion_negative_tests_present",
    "runtime_evidence_matrix_optional_inventory",
    "second_independent_layout_conversion_slice",
    "gate_exact_artifact_binding",
    "hs_ir_and_tensor_store_digest_binding",
)
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS = len(
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS
)
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ISSUES = (
    MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS
)
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_FIELD_BYTES = 512

_READINESS_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_READINESS_TEXT = frozenset(
    {
        "allocation_handle",
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "device_pointer",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "memory_address",
        "module",
        "network",
        "plugin_entrypoint",
        "pointer",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "runtime_handle",
        "source_text",
        "subprocess",
        "tensor_value",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeLayoutConversionGateReadinessCheck:
    """One bounded prerequisite for making layout-conversion evidence required."""

    check_name: str
    status: str
    evidence_id: str
    detail: str

    def __post_init__(self) -> None:
        _validate_text(self.check_name, "layout conversion readiness check_name")
        if self.check_name not in RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS:
            raise ValueError("unsupported runtime layout conversion readiness check")
        if self.status not in RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_STATUSES:
            raise ValueError("unsupported runtime layout conversion readiness status")
        _validate_text(self.evidence_id, "layout conversion readiness evidence_id")
        _validate_text(self.detail, "layout conversion readiness detail")


@dataclass(frozen=True)
class RuntimeLayoutConversionGateReadinessIssue:
    """One derived issue from an unmet readiness prerequisite."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "layout conversion readiness issue subject")
        _validate_text(self.issue_code, "layout conversion readiness issue_code")


@dataclass(frozen=True)
class RuntimeLayoutConversionGateReadinessReport:
    """Data-only report for the future layout-conversion gate transition."""

    proposal_name: str
    source_graph_name: str
    source_evidence_contract: str
    source_evidence_schema_version: str
    source_evidence_issue_count: int
    source_conversion_count: int
    source_conversion_metadata_digest: str
    source_partition_plan_digest: str
    checks: tuple[RuntimeLayoutConversionGateReadinessCheck, ...]
    issues: tuple[RuntimeLayoutConversionGateReadinessIssue, ...]
    readiness_contract: str = RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT
    artifact_status: str = RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS
    target_artifact_kind: str = (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
    )
    target_artifact_id: str = (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
    )
    target_graph_id: str = RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID
    target_gate_status: str = (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.proposal_name, "layout conversion readiness proposal_name")
        _validate_text(self.source_graph_name, "layout conversion source_graph_name")
        if self.source_evidence_contract != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT:
            raise ValueError("layout conversion readiness source contract mismatch")
        if (
            self.source_evidence_schema_version
            != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("layout conversion readiness source schema mismatch")
        _require_non_negative_int(
            self.source_evidence_issue_count,
            "source_evidence_issue_count",
        )
        _require_non_negative_int(self.source_conversion_count, "source_conversion_count")
        _validate_digest(
            self.source_conversion_metadata_digest,
            "source_conversion_metadata_digest",
        )
        _validate_digest(
            self.source_partition_plan_digest,
            "source_partition_plan_digest",
        )
        if self.readiness_contract != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT:
            raise ValueError("runtime layout conversion readiness contract mismatch")
        if (
            self.artifact_status
            != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS
        ):
            raise ValueError("runtime layout conversion readiness status mismatch")
        if (
            self.target_artifact_kind
            != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
        ):
            raise ValueError("runtime layout conversion target artifact kind mismatch")
        if (
            self.target_artifact_id
            != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
        ):
            raise ValueError("runtime layout conversion target artifact id mismatch")
        if self.target_graph_id != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID:
            raise ValueError("runtime layout conversion target graph mismatch")
        if (
            self.target_gate_status
            != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS
        ):
            raise ValueError("runtime layout conversion target gate status mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime layout conversion blocked surfaces changed")
        _validate_checks(self.checks)
        if self.source_evidence_issue_count and _check_status(
            self.checks,
            "layout_conversion_evidence_report_passes",
        ) == "passed":
            raise ValueError("layout conversion source issues cannot be marked passed")
        if self.source_conversion_count < 1 and _check_status(
            self.checks,
            "layout_conversion_evidence_report_passes",
        ) == "passed":
            raise ValueError("layout conversion source evidence must include records")
        if type(self.issues) is not tuple:
            raise TypeError("runtime layout conversion readiness issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ISSUES:
            raise ValueError("runtime layout conversion readiness issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeLayoutConversionGateReadinessIssue):
                raise TypeError(
                    "runtime layout conversion readiness issues must be issue objects"
                )
        expected_issues = _derive_issues(self.checks)
        if self.issues != expected_issues:
            raise ValueError("runtime layout conversion readiness issues must be derived")

    @property
    def ready(self) -> bool:
        """Return whether layout-conversion evidence can become gate-required."""

        return not self.issues

    @property
    def readiness_status(self) -> str:
        """Return the stable readiness status label."""

        return "ready" if self.ready else "blocked"

    @property
    def readiness_metadata_digest(self) -> str:
        """Return a digest over the readiness metadata only."""

        payload = {
            "checks": [_check_to_dict(check) for check in self.checks],
            "proposal_name": self.proposal_name,
            "source_conversion_count": self.source_conversion_count,
            "source_conversion_metadata_digest": (
                self.source_conversion_metadata_digest
            ),
            "source_evidence_issue_count": self.source_evidence_issue_count,
            "source_graph_name": self.source_graph_name,
            "source_partition_plan_digest": self.source_partition_plan_digest,
            "target_artifact_id": self.target_artifact_id,
            "target_artifact_kind": self.target_artifact_kind,
            "target_gate_status": self.target_gate_status,
            "target_graph_id": self.target_graph_id,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeLayoutConversionGateReadinessError(AssertionError):
    """Raised when layout-conversion gate readiness is not ready."""


def build_runtime_layout_conversion_gate_readiness_report(
    source_evidence: RuntimeLayoutConversionEvidenceReport,
    checks: tuple[RuntimeLayoutConversionGateReadinessCheck, ...],
    *,
    proposal_name: str = "runtime_layout_conversion_gate_required_evidence",
) -> RuntimeLayoutConversionGateReadinessReport:
    """Build a bounded data-only readiness report from explicit checks."""

    if not isinstance(source_evidence, RuntimeLayoutConversionEvidenceReport):
        raise TypeError("layout conversion readiness source must be evidence report")
    return RuntimeLayoutConversionGateReadinessReport(
        proposal_name=proposal_name,
        source_graph_name=source_evidence.graph_name,
        source_evidence_contract=source_evidence.evidence_contract,
        source_evidence_schema_version=(
            RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION
        ),
        source_evidence_issue_count=len(source_evidence.issues),
        source_conversion_count=len(source_evidence.conversions),
        source_conversion_metadata_digest=source_evidence.conversion_metadata_digest,
        source_partition_plan_digest=source_evidence.source_partition_plan_digest,
        checks=checks,
        issues=_derive_issues(checks),
    )


def assert_runtime_layout_conversion_gate_readiness(
    report: RuntimeLayoutConversionGateReadinessReport,
) -> RuntimeLayoutConversionGateReadinessReport:
    """Return the report or raise when gate readiness is still blocked."""

    if not isinstance(report, RuntimeLayoutConversionGateReadinessReport):
        raise TypeError("layout conversion readiness report must be report object")
    if report.issues:
        lines = [
            f"runtime layout conversion gate readiness blocked for "
            f"{report.proposal_name!r}:"
        ]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeLayoutConversionGateReadinessError("\n".join(lines))
    return report


def runtime_layout_conversion_gate_readiness_report_to_dict(
    report: RuntimeLayoutConversionGateReadinessReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible layout-conversion readiness data."""

    if not isinstance(report, RuntimeLayoutConversionGateReadinessReport):
        raise TypeError("layout conversion readiness report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "checks": [_check_to_dict(check) for check in report.checks],
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "proposal_name": report.proposal_name,
        "readiness_contract": report.readiness_contract,
        "readiness_metadata_digest": report.readiness_metadata_digest,
        "readiness_status": report.readiness_status,
        "ready": report.ready,
        "schema_version": (
            RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION
        ),
        "source_conversion_count": report.source_conversion_count,
        "source_conversion_metadata_digest": (
            report.source_conversion_metadata_digest
        ),
        "source_evidence_contract": report.source_evidence_contract,
        "source_evidence_issue_count": report.source_evidence_issue_count,
        "source_evidence_schema_version": report.source_evidence_schema_version,
        "source_graph_name": report.source_graph_name,
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "target_artifact_id": report.target_artifact_id,
        "target_artifact_kind": report.target_artifact_kind,
        "target_gate_status": report.target_gate_status,
        "target_graph_id": report.target_graph_id,
    }


def dump_runtime_layout_conversion_gate_readiness_report(
    report: RuntimeLayoutConversionGateReadinessReport,
) -> str:
    """Render stable data-only runtime layout-conversion gate readiness."""

    text = json.dumps(
        runtime_layout_conversion_gate_readiness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_BYTES
    ):
        raise ValueError(
            "runtime layout conversion gate readiness report exceeds byte limit"
        )
    return text + "\n"


def _check_to_dict(
    check: RuntimeLayoutConversionGateReadinessCheck,
) -> dict[str, str]:
    return {
        "check_name": check.check_name,
        "detail": check.detail,
        "evidence_id": check.evidence_id,
        "status": check.status,
    }


def _validate_checks(
    checks: tuple[RuntimeLayoutConversionGateReadinessCheck, ...],
) -> None:
    if type(checks) is not tuple:
        raise TypeError("runtime layout conversion readiness checks must be a tuple")
    if len(checks) > MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS:
        raise ValueError("runtime layout conversion readiness check count exceeds limit")
    if tuple(check.check_name for check in checks) != (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS
    ):
        raise ValueError("runtime layout conversion readiness checks are out of order")
    for check in checks:
        if not isinstance(check, RuntimeLayoutConversionGateReadinessCheck):
            raise TypeError(
                "runtime layout conversion readiness checks must be check objects"
            )


def _derive_issues(
    checks: tuple[RuntimeLayoutConversionGateReadinessCheck, ...],
) -> tuple[RuntimeLayoutConversionGateReadinessIssue, ...]:
    _validate_checks(checks)
    return tuple(
        RuntimeLayoutConversionGateReadinessIssue(
            subject=check.check_name,
            issue_code="readiness_check_not_passed",
        )
        for check in checks
        if check.status != "passed"
    )


def _check_status(
    checks: tuple[RuntimeLayoutConversionGateReadinessCheck, ...],
    check_name: str,
) -> str:
    for check in checks:
        if check.check_name == check_name:
            return check.status
    raise ValueError("runtime layout conversion readiness check missing")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _READINESS_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe layout conversion identifier")
    if len(value.encode("utf-8")) > (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_FIELD_BYTES
    ):
        raise ValueError(f"{label} exceeds layout conversion readiness field limit")
    if value in _FORBIDDEN_READINESS_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _require_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS",
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_FIELD_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ISSUES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_BYTES",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_STATUSES",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID",
    "RuntimeLayoutConversionGateReadinessCheck",
    "RuntimeLayoutConversionGateReadinessError",
    "RuntimeLayoutConversionGateReadinessIssue",
    "RuntimeLayoutConversionGateReadinessReport",
    "assert_runtime_layout_conversion_gate_readiness",
    "build_runtime_layout_conversion_gate_readiness_report",
    "dump_runtime_layout_conversion_gate_readiness_report",
    "runtime_layout_conversion_gate_readiness_report_to_dict",
]
