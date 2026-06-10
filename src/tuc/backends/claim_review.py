"""Data-only review reports for backend capability manifest claims."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from tuc.backends.base import BackendCapability
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.manifests import ManifestError, load_backend_capability_manifest
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

MANIFEST_CLAIM_REVIEW_REPORT_SCHEMA_VERSION = (
    "tuc.manifest_claim_review_report.v0"
)
MANIFEST_CLAIM_REVIEW_CONTRACT = "manifest_claim_review.data_only.v0"
MAX_MANIFEST_CLAIM_REVIEW_CASES = 64
MAX_MANIFEST_CLAIM_REVIEW_ISSUES = 128
MAX_MANIFEST_CLAIM_REVIEW_REPORT_BYTES = 64 * 1024
MAX_MANIFEST_CLAIM_REVIEW_FIELD_BYTES = 512

MANIFEST_CLAIM_REVIEW_STATUSES = frozenset({"accepted", "blocked"})
MANIFEST_CLAIM_LOAD_STATUSES = frozenset({"loaded", "rejected"})

_REVIEW_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_REVIEW_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class ManifestClaimReviewInput:
    """One explicit manifest path and expected review outcome."""

    manifest_id: str
    path: Path
    expected_review_status: str

    def __post_init__(self) -> None:
        _validate_review_text(self.manifest_id, "manifest_id")
        if not isinstance(self.path, Path):
            raise TypeError("manifest claim review path must be Path")
        if self.expected_review_status not in MANIFEST_CLAIM_REVIEW_STATUSES:
            raise ValueError("expected review status is unsupported")


@dataclass(frozen=True)
class ManifestClaimReviewCase:
    """Observed review result for one backend capability manifest."""

    manifest_id: str
    source_label: str
    expected_review_status: str
    observed_review_status: str
    load_status: str
    backend_name: str
    supported_ops: tuple[OperationKind, ...]
    memory_domain: str
    produced_layouts: tuple[LayoutKind, ...]
    issue_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_review_text(self.manifest_id, "case manifest_id")
        _validate_source_label(self.source_label)
        if self.expected_review_status not in MANIFEST_CLAIM_REVIEW_STATUSES:
            raise ValueError("case expected review status is unsupported")
        if self.observed_review_status not in MANIFEST_CLAIM_REVIEW_STATUSES:
            raise ValueError("case observed review status is unsupported")
        if self.load_status not in MANIFEST_CLAIM_LOAD_STATUSES:
            raise ValueError("case load status is unsupported")
        _validate_review_text(self.backend_name, "case backend_name")
        _validate_operation_tuple(self.supported_ops, "case supported_ops")
        _validate_review_text(self.memory_domain, "case memory_domain")
        _validate_layout_tuple(self.produced_layouts, "case produced_layouts")
        if type(self.issue_codes) is not tuple:
            raise TypeError("case issue_codes must be a tuple")
        for issue_code in self.issue_codes:
            _validate_review_text(issue_code, "case issue_code")
        if self.observed_review_status == "accepted" and self.issue_codes:
            raise ValueError("accepted manifest claim review case must not have issues")
        if self.load_status == "rejected" and self.observed_review_status != "blocked":
            raise ValueError("rejected manifest loads must be blocked")


@dataclass(frozen=True)
class ManifestClaimReviewIssue:
    """One report-level mismatch between expected and observed review status."""

    manifest_id: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_review_text(self.manifest_id, "issue manifest_id")
        _validate_review_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class ManifestClaimReviewReport:
    """Deterministic capability-manifest claim review report."""

    cases: tuple[ManifestClaimReviewCase, ...]
    report_issues: tuple[ManifestClaimReviewIssue, ...]
    claim_review_contract: str = MANIFEST_CLAIM_REVIEW_CONTRACT
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.claim_review_contract != MANIFEST_CLAIM_REVIEW_CONTRACT:
            raise ValueError("manifest claim review contract mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("manifest claim review blocked execution surfaces changed")
        if type(self.cases) is not tuple:
            raise TypeError("manifest claim review cases must be a tuple")
        if not self.cases:
            raise ValueError("manifest claim review report must contain cases")
        if len(self.cases) > MAX_MANIFEST_CLAIM_REVIEW_CASES:
            raise ValueError("manifest claim review case count exceeds limit")
        manifest_ids: list[str] = []
        for case in self.cases:
            if not isinstance(case, ManifestClaimReviewCase):
                raise TypeError("manifest claim review cases must be case objects")
            manifest_ids.append(case.manifest_id)
        if len(manifest_ids) != len(set(manifest_ids)):
            raise ValueError("manifest claim review manifest_ids must be unique")
        if type(self.report_issues) is not tuple:
            raise TypeError("manifest claim review report_issues must be a tuple")
        if len(self.report_issues) > MAX_MANIFEST_CLAIM_REVIEW_ISSUES:
            raise ValueError("manifest claim review report issue count exceeds limit")
        for issue in self.report_issues:
            if not isinstance(issue, ManifestClaimReviewIssue):
                raise TypeError("manifest claim review issues must be issue objects")
        expected_issues = _derive_report_issues(self.cases)
        if self.report_issues != expected_issues:
            raise ValueError("manifest claim review report issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether all manifest cases matched their expected status."""

        return not self.report_issues


def build_manifest_claim_review_report(
    inputs: tuple[ManifestClaimReviewInput, ...],
) -> ManifestClaimReviewReport:
    """Review explicit capability manifests without executing backend code."""

    if type(inputs) is not tuple:
        raise TypeError("manifest claim review inputs must be a tuple")
    cases = tuple(_review_manifest_claim(item) for item in inputs)
    return ManifestClaimReviewReport(
        cases=cases,
        report_issues=_derive_report_issues(cases),
    )


def manifest_claim_review_report_to_dict(
    report: ManifestClaimReviewReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible claim review report."""

    if not isinstance(report, ManifestClaimReviewReport):
        raise TypeError("manifest claim review report must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "case_count": len(report.cases),
        "cases": [
            {
                "backend_name": case.backend_name,
                "expected_review_status": case.expected_review_status,
                "issue_codes": list(case.issue_codes),
                "load_status": case.load_status,
                "manifest_id": case.manifest_id,
                "memory_domain": case.memory_domain,
                "observed_review_status": case.observed_review_status,
                "produced_layouts": [layout.value for layout in case.produced_layouts],
                "source_label": case.source_label,
                "supported_ops": [operation.value for operation in case.supported_ops],
            }
            for case in report.cases
        ],
        "claim_review_contract": report.claim_review_contract,
        "passed": report.passed,
        "report_issues": [
            {
                "issue_code": issue.issue_code,
                "manifest_id": issue.manifest_id,
            }
            for issue in report.report_issues
        ],
        "schema_version": MANIFEST_CLAIM_REVIEW_REPORT_SCHEMA_VERSION,
    }


def dump_manifest_claim_review_report(report: ManifestClaimReviewReport) -> str:
    """Render a stable capability-manifest claim review report."""

    text = json.dumps(
        manifest_claim_review_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_MANIFEST_CLAIM_REVIEW_REPORT_BYTES:
        raise ValueError("manifest claim review report exceeds byte limit")
    return text + "\n"


def _review_manifest_claim(item: ManifestClaimReviewInput) -> ManifestClaimReviewCase:
    _validate_review_input(item)
    source_label = item.path.name
    try:
        capability = load_backend_capability_manifest(item.path)
    except (ManifestError, ValueError, TypeError):
        return ManifestClaimReviewCase(
            manifest_id=item.manifest_id,
            source_label=source_label,
            expected_review_status=item.expected_review_status,
            observed_review_status="blocked",
            load_status="rejected",
            backend_name="unloaded",
            supported_ops=(),
            memory_domain="unloaded",
            produced_layouts=(),
            issue_codes=("manifest_loader_rejected_claim",),
        )

    issue_codes = _review_capability(capability)
    return ManifestClaimReviewCase(
        manifest_id=item.manifest_id,
        source_label=source_label,
        expected_review_status=item.expected_review_status,
        observed_review_status="blocked" if issue_codes else "accepted",
        load_status="loaded",
        backend_name=capability.name,
        supported_ops=tuple(sorted(capability.supported_ops, key=lambda item: item.value)),
        memory_domain=capability.memory_domain.value,
        produced_layouts=tuple(
            sorted(capability.produced_layouts, key=lambda item: item.value)
        ),
        issue_codes=issue_codes,
    )


def _review_capability(capability: BackendCapability) -> tuple[str, ...]:
    issue_codes: list[str] = []
    all_operation_kinds = frozenset(OperationKind)

    if (
        capability.name != "reference-cpu"
        and capability.supported_ops == all_operation_kinds
    ):
        issue_codes.append("non_reference_backend_claims_all_mvp_ops")
    if capability.name == "reference-cpu" and (
        capability.memory_domain is not MemoryDomainKind.HOST_RAM
    ):
        issue_codes.append("reference_cpu_must_use_host_ram")
    if capability.supports_noise_model and capability.max_error_budget is None:
        issue_codes.append("noise_model_requires_explicit_error_budget")
    if capability.supports_calibration and capability.max_error_budget is None:
        issue_codes.append("calibration_claim_requires_error_budget")
    if (
        capability.memory_domain is MemoryDomainKind.HOST_RAM
        and LayoutKind.BLOCKED in capability.produced_layouts
        and capability.name != "reference-cpu"
    ):
        issue_codes.append("host_backend_claims_specialized_blocked_layout")

    return tuple(issue_codes)


def _derive_report_issues(
    cases: tuple[ManifestClaimReviewCase, ...],
) -> tuple[ManifestClaimReviewIssue, ...]:
    issues: list[ManifestClaimReviewIssue] = []
    for case in cases:
        if case.expected_review_status != case.observed_review_status:
            issues.append(
                ManifestClaimReviewIssue(
                    manifest_id=case.manifest_id,
                    issue_code="manifest_claim_review_status_mismatch",
                )
            )
    return tuple(issues)


def _validate_review_input(item: ManifestClaimReviewInput) -> None:
    if not isinstance(item, ManifestClaimReviewInput):
        raise TypeError("manifest claim review input must be input object")
    _validate_source_label(item.path.name)


def _validate_source_label(value: str) -> None:
    _validate_review_text(value, "source_label")
    if "/" in value or "\\" in value:
        raise ValueError("source_label must not contain path separators")


def _validate_review_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REVIEW_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe manifest claim review identifier")
    if len(value.encode("utf-8")) > MAX_MANIFEST_CLAIM_REVIEW_FIELD_BYTES:
        raise ValueError(f"{label} exceeds manifest claim review field limit")
    if value in _FORBIDDEN_REVIEW_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_operation_tuple(value: tuple[OperationKind, ...], label: str) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    for item in value:
        if not isinstance(item, OperationKind):
            raise TypeError(f"{label} must contain OperationKind values")


def _validate_layout_tuple(value: tuple[LayoutKind, ...], label: str) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    for item in value:
        if not isinstance(item, LayoutKind):
            raise TypeError(f"{label} must contain LayoutKind values")


__all__ = [
    "MANIFEST_CLAIM_LOAD_STATUSES",
    "MANIFEST_CLAIM_REVIEW_CONTRACT",
    "MANIFEST_CLAIM_REVIEW_REPORT_SCHEMA_VERSION",
    "MANIFEST_CLAIM_REVIEW_STATUSES",
    "MAX_MANIFEST_CLAIM_REVIEW_CASES",
    "MAX_MANIFEST_CLAIM_REVIEW_FIELD_BYTES",
    "MAX_MANIFEST_CLAIM_REVIEW_ISSUES",
    "MAX_MANIFEST_CLAIM_REVIEW_REPORT_BYTES",
    "ManifestClaimReviewCase",
    "ManifestClaimReviewInput",
    "ManifestClaimReviewIssue",
    "ManifestClaimReviewReport",
    "build_manifest_claim_review_report",
    "dump_manifest_claim_review_report",
    "manifest_claim_review_report_to_dict",
]
