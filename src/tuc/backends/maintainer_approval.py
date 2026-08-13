"""Data-only maintainer approval evidence for backend plugin proposals."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.artifact_provenance import BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
from tuc.backends.fuzz_negative_tests import BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
from tuc.backends.resource_budget import BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
from tuc.backends.sandbox_model import BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION = (
    "tuc.backend_plugin_maintainer_approval_report.v0"
)
BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT = "backend_plugin_maintainer_approval.data_only.v0"
BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY = "maintainer_approval.review_record.no_execution.v0"
BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS = "accepted_data_only_approval"
BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION = "not_granted"
BACKEND_PLUGIN_MAINTAINER_APPROVAL_DECISIONS = frozenset({"approved_for_proposal_gate"})
BACKEND_PLUGIN_MAINTAINER_APPROVAL_RECORD_STATUSES = frozenset({"reviewed_by_maintainers"})
BACKEND_PLUGIN_MAINTAINER_APPROVAL_SCOPES = frozenset({"lifecycle_evidence_gate"})
BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS = (
    "sandbox_model",
    "artifact_provenance",
    "resource_budget",
    "fuzz_negative_tests",
    "blocked_execution_surfaces",
    "implementation_rfc_required",
)
BACKEND_PLUGIN_MAINTAINER_APPROVAL_ISSUE_CODES = frozenset(
    {
        "approval_decision_invalid",
        "approval_execution_permission_granted",
        "approval_missing_required_binding",
        "approval_scope_invalid",
        "approval_status_invalid",
        "artifact_provenance_binding_mismatch",
        "duplicate_approval_id",
        "fuzz_negative_tests_binding_mismatch",
        "implementation_rfc_not_required",
        "resource_budget_binding_mismatch",
        "sandbox_binding_mismatch",
    }
)
MAX_BACKEND_PLUGIN_MAINTAINER_APPROVALS = 8
MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_ISSUES = 64
MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_BYTES = 64 * 1024
MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_FIELD_BYTES = 512

_APPROVAL_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_APPROVAL_TEXT = frozenset(
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
        "token",
        "url",
    }
)


@dataclass(frozen=True)
class BackendPluginMaintainerApprovalRecord:
    """One bounded maintainer approval record for the lifecycle evidence gate."""

    approval_id: str
    approval_scope: str
    review_record_id: str
    maintainer_group_id: str
    approval_decision: str
    approval_status: str
    sandbox_model_contract: str
    artifact_provenance_contract: str
    resource_budget_contract: str
    fuzz_negative_tests_contract: str
    implementation_rfc_required: bool

    def __post_init__(self) -> None:
        _validate_approval_text(self.approval_id, "approval_id")
        _validate_approval_text(self.approval_scope, "approval_scope")
        _validate_approval_text(self.review_record_id, "review_record_id")
        _validate_approval_text(self.maintainer_group_id, "maintainer_group_id")
        _validate_approval_text(self.approval_decision, "approval_decision")
        _validate_approval_text(self.approval_status, "approval_status")
        _validate_approval_text(
            self.sandbox_model_contract,
            "sandbox_model_contract",
        )
        _validate_approval_text(
            self.artifact_provenance_contract,
            "artifact_provenance_contract",
        )
        _validate_approval_text(
            self.resource_budget_contract,
            "resource_budget_contract",
        )
        _validate_approval_text(
            self.fuzz_negative_tests_contract,
            "fuzz_negative_tests_contract",
        )
        if type(self.implementation_rfc_required) is not bool:
            raise TypeError("implementation_rfc_required must be bool")
        if self.approval_scope not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_SCOPES:
            raise ValueError("backend plugin maintainer approval scope unsupported")
        if self.approval_decision not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_DECISIONS:
            raise ValueError("backend plugin maintainer approval decision unsupported")
        if self.approval_status not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_RECORD_STATUSES:
            raise ValueError("backend plugin maintainer approval status unsupported")


@dataclass(frozen=True)
class BackendPluginMaintainerApprovalIssue:
    """One derived maintainer approval issue."""

    approval_id: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_approval_text(self.approval_id, "approval issue approval_id")
        _validate_approval_text(self.issue_code, "approval issue_code")
        if self.issue_code not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_ISSUE_CODES:
            raise ValueError("backend plugin maintainer approval issue unsupported")


@dataclass(frozen=True)
class BackendPluginMaintainerApprovalReport:
    """Current data-only maintainer approval evidence."""

    approvals: tuple[BackendPluginMaintainerApprovalRecord, ...]
    issues: tuple[BackendPluginMaintainerApprovalIssue, ...]
    approval_contract: str = BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT
    approval_policy: str = BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY
    approval_status: str = BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS
    execution_permission: str = BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION
    required_bindings: tuple[str, ...] = BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        if self.approval_contract != BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT:
            raise ValueError("backend plugin maintainer approval contract mismatch")
        if self.approval_policy != BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY:
            raise ValueError("backend plugin maintainer approval policy mismatch")
        if self.approval_status != BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS:
            raise ValueError("backend plugin maintainer approval status mismatch")
        if self.execution_permission != BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION:
            raise ValueError("backend plugin maintainer approval permission mismatch")
        if self.required_bindings != BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS:
            raise ValueError("backend plugin maintainer approval required bindings changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin maintainer approval blocked surfaces changed")
        if type(self.approvals) is not tuple:
            raise TypeError("backend plugin maintainer approvals must be a tuple")
        if len(self.approvals) > MAX_BACKEND_PLUGIN_MAINTAINER_APPROVALS:
            raise ValueError("backend plugin maintainer approval count exceeds limit")
        for approval in self.approvals:
            if not isinstance(approval, BackendPluginMaintainerApprovalRecord):
                raise TypeError("backend plugin maintainer approvals must be records")
        if type(self.issues) is not tuple:
            raise TypeError("backend plugin maintainer approval issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_ISSUES:
            raise ValueError("backend plugin maintainer approval issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPluginMaintainerApprovalIssue):
                raise TypeError("backend plugin maintainer approval issues must be objects")
        expected_issues = _derive_approval_issues(self)
        if self.issues != expected_issues:
            raise ValueError("backend plugin maintainer approval issues must be derived")

    @property
    def approval_count(self) -> int:
        """Return the number of accepted approval records."""

        return len(self.approvals)

    @property
    def approval_ready(self) -> bool:
        """Return whether maintainer approval evidence is internally complete."""

        return bool(self.approvals) and not self.issues

    @property
    def execution_allowed(self) -> bool:
        """Return whether this approval evidence grants execution permission."""

        return False


class BackendPluginMaintainerApprovalError(ValueError):
    """Raised when backend plugin maintainer approval evidence fails."""


def build_backend_plugin_maintainer_approval_report(
    approvals: tuple[BackendPluginMaintainerApprovalRecord, ...] | None = None,
) -> BackendPluginMaintainerApprovalReport:
    """Build the current data-only maintainer approval report."""

    normalized_approvals = _current_approval_records() if approvals is None else approvals
    report = BackendPluginMaintainerApprovalReport(
        approvals=normalized_approvals,
        issues=(),
    )
    return BackendPluginMaintainerApprovalReport(
        approvals=normalized_approvals,
        issues=_derive_approval_issues(report),
    )


def assert_backend_plugin_maintainer_approval(
    report: BackendPluginMaintainerApprovalReport,
) -> BackendPluginMaintainerApprovalReport:
    """Return the report or raise when maintainer approval evidence is incomplete."""

    if not isinstance(report, BackendPluginMaintainerApprovalReport):
        raise TypeError("backend plugin maintainer approval must be report object")
    if not report.approval_ready:
        lines = ["backend plugin maintainer approval failed:"]
        for issue in report.issues:
            lines.append(f"- {issue.approval_id}: {issue.issue_code}")
        raise BackendPluginMaintainerApprovalError("\n".join(lines))
    return report


def backend_plugin_maintainer_approval_report_to_dict(
    report: BackendPluginMaintainerApprovalReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible maintainer approval report."""

    if not isinstance(report, BackendPluginMaintainerApprovalReport):
        raise TypeError("backend plugin maintainer approval must be report object")
    return {
        "approval_contract": report.approval_contract,
        "approval_count": report.approval_count,
        "approval_policy": report.approval_policy,
        "approval_ready": report.approval_ready,
        "approval_status": report.approval_status,
        "approvals": [
            {
                "approval_decision": approval.approval_decision,
                "approval_id": approval.approval_id,
                "approval_scope": approval.approval_scope,
                "approval_status": approval.approval_status,
                "artifact_provenance_contract": (approval.artifact_provenance_contract),
                "fuzz_negative_tests_contract": (approval.fuzz_negative_tests_contract),
                "implementation_rfc_required": approval.implementation_rfc_required,
                "maintainer_group_id": approval.maintainer_group_id,
                "resource_budget_contract": approval.resource_budget_contract,
                "review_record_id": approval.review_record_id,
                "sandbox_model_contract": approval.sandbox_model_contract,
            }
            for approval in report.approvals
        ],
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "execution_allowed": report.execution_allowed,
        "execution_permission": report.execution_permission,
        "issues": [
            {
                "approval_id": issue.approval_id,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "required_bindings": list(report.required_bindings),
        "schema_version": BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION,
    }


def dump_backend_plugin_maintainer_approval_report(
    report: BackendPluginMaintainerApprovalReport,
) -> str:
    """Render a stable backend plugin maintainer approval report."""

    text = json.dumps(
        backend_plugin_maintainer_approval_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_BYTES:
        raise ValueError("backend plugin maintainer approval report exceeds byte limit")
    return text + "\n"


def _current_approval_records() -> tuple[BackendPluginMaintainerApprovalRecord, ...]:
    return (
        BackendPluginMaintainerApprovalRecord(
            approval_id="backend_plugin_lifecycle_maintainer_approval",
            approval_scope="lifecycle_evidence_gate",
            review_record_id="rfc_0222_backend_plugin_maintainer_approval",
            maintainer_group_id="tuc_maintainers",
            approval_decision="approved_for_proposal_gate",
            approval_status="reviewed_by_maintainers",
            sandbox_model_contract=BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
            artifact_provenance_contract=BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
            resource_budget_contract=BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT,
            fuzz_negative_tests_contract=BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT,
            implementation_rfc_required=True,
        ),
    )


def _derive_approval_issues(
    report: BackendPluginMaintainerApprovalReport,
) -> tuple[BackendPluginMaintainerApprovalIssue, ...]:
    issues: list[BackendPluginMaintainerApprovalIssue] = []
    approval_ids = tuple(approval.approval_id for approval in report.approvals)
    duplicate_ids = {
        approval_id for approval_id in approval_ids if approval_ids.count(approval_id) > 1
    }
    for approval_id in sorted(duplicate_ids):
        issues.append(
            BackendPluginMaintainerApprovalIssue(
                approval_id=approval_id,
                issue_code="duplicate_approval_id",
            )
        )
    for approval in report.approvals:
        if approval.approval_scope not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_SCOPES:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="approval_scope_invalid",
                )
            )
        if approval.approval_decision not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_DECISIONS:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="approval_decision_invalid",
                )
            )
        if approval.approval_status not in BACKEND_PLUGIN_MAINTAINER_APPROVAL_RECORD_STATUSES:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="approval_status_invalid",
                )
            )
        if approval.sandbox_model_contract != BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="sandbox_binding_mismatch",
                )
            )
        if approval.artifact_provenance_contract != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="artifact_provenance_binding_mismatch",
                )
            )
        if approval.resource_budget_contract != BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="resource_budget_binding_mismatch",
                )
            )
        if approval.fuzz_negative_tests_contract != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="fuzz_negative_tests_binding_mismatch",
                )
            )
        if not approval.implementation_rfc_required:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="implementation_rfc_not_required",
                )
            )
        for binding in BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS:
            if not _approval_has_binding(report, approval, binding):
                issues.append(
                    BackendPluginMaintainerApprovalIssue(
                        approval_id=approval.approval_id,
                        issue_code="approval_missing_required_binding",
                    )
                )
    if report.execution_permission != BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION:
        for approval in report.approvals:
            issues.append(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=approval.approval_id,
                    issue_code="approval_execution_permission_granted",
                )
            )
    return tuple(issues)


def _approval_has_binding(
    report: BackendPluginMaintainerApprovalReport,
    approval: BackendPluginMaintainerApprovalRecord,
    binding: str,
) -> bool:
    if binding == "sandbox_model":
        return approval.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    if binding == "artifact_provenance":
        return approval.artifact_provenance_contract == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    if binding == "resource_budget":
        return approval.resource_budget_contract == BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    if binding == "fuzz_negative_tests":
        return approval.fuzz_negative_tests_contract == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
    if binding == "blocked_execution_surfaces":
        return report.blocked_execution_surfaces == RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    if binding == "implementation_rfc_required":
        return approval.implementation_rfc_required
    return False


def _validate_approval_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _APPROVAL_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend approval identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend approval field limit")
    if value in _FORBIDDEN_APPROVAL_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_DECISIONS",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_ISSUE_CODES",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_RECORD_STATUSES",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_SCOPES",
    "BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS",
    "MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_FIELD_BYTES",
    "MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_ISSUES",
    "MAX_BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_BYTES",
    "MAX_BACKEND_PLUGIN_MAINTAINER_APPROVALS",
    "BackendPluginMaintainerApprovalError",
    "BackendPluginMaintainerApprovalIssue",
    "BackendPluginMaintainerApprovalRecord",
    "BackendPluginMaintainerApprovalReport",
    "assert_backend_plugin_maintainer_approval",
    "backend_plugin_maintainer_approval_report_to_dict",
    "build_backend_plugin_maintainer_approval_report",
    "dump_backend_plugin_maintainer_approval_report",
]
