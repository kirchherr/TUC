"""Data-only lifecycle policy for future executable backend plugins."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.artifact_provenance import BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
from tuc.backends.fuzz_negative_tests import BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
from tuc.backends.resource_budget import BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
from tuc.backends.sandbox_model import (
    BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    BACKEND_PLUGIN_SANDBOX_MODEL_STATUS,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_PLUGIN_LIFECYCLE_POLICY_REPORT_SCHEMA_VERSION = (
    "tuc.backend_plugin_lifecycle_policy_report.v0"
)
BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT = (
    "backend_plugin_lifecycle_policy.blocking.v0"
)
BACKEND_PLUGIN_LIFECYCLE_POLICY_ID = "backend_plugin_lifecycle_policy_v0"
BACKEND_PLUGIN_LIFECYCLE_POLICY_STATUS = "accepted_blocking_policy"
BACKEND_PLUGIN_LIFECYCLE_EXECUTION_STATUS = "external_plugins_blocked"
BACKEND_PLUGIN_LIFECYCLE_SANDBOX_STATUS = BACKEND_PLUGIN_SANDBOX_MODEL_STATUS
BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS = (
    "capability_manifest_claim_review",
    "backend_author_evidence_gate",
    "trusted_executor_contract",
    "plugin_lifecycle_rfc",
    "sandbox_model",
    "artifact_provenance",
    "resource_budget",
    "fuzz_negative_tests",
    "maintainer_approval",
)
BACKEND_PLUGIN_LIFECYCLE_REQUIREMENT_STATUSES = frozenset(
    {"satisfied", "missing"}
)
BACKEND_PLUGIN_LIFECYCLE_POLICY_ISSUE_CODES = frozenset(
    {
        "artifact_execution_enabled",
        "external_plugins_enabled_before_requirements",
        "missing_required_requirement",
        "native_plugin_abi_enabled",
        "plugin_discovery_enabled",
        "sandbox_status_inconsistent",
    }
)
MAX_BACKEND_PLUGIN_LIFECYCLE_REQUIREMENTS = 16
MAX_BACKEND_PLUGIN_LIFECYCLE_POLICY_ISSUES = 32
MAX_BACKEND_PLUGIN_LIFECYCLE_REPORT_BYTES = 64 * 1024
MAX_BACKEND_PLUGIN_LIFECYCLE_FIELD_BYTES = 512

_POLICY_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_POLICY_TEXT = frozenset(
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
class BackendPluginLifecycleRequirement:
    """One requirement before external backend plugins may execute."""

    requirement_id: str
    status: str
    evidence_id: str
    required_before: str

    def __post_init__(self) -> None:
        _validate_policy_text(self.requirement_id, "requirement_id")
        _validate_policy_text(self.evidence_id, "evidence_id")
        _validate_policy_text(self.required_before, "required_before")
        if self.status not in BACKEND_PLUGIN_LIFECYCLE_REQUIREMENT_STATUSES:
            raise ValueError("backend plugin lifecycle requirement status unsupported")


@dataclass(frozen=True)
class BackendPluginLifecyclePolicyIssue:
    """One derived lifecycle-policy issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_policy_text(self.subject, "issue subject")
        _validate_policy_text(self.issue_code, "issue_code")
        if self.issue_code not in BACKEND_PLUGIN_LIFECYCLE_POLICY_ISSUE_CODES:
            raise ValueError("backend plugin lifecycle policy issue unsupported")


@dataclass(frozen=True)
class BackendPluginLifecyclePolicyReport:
    """Current data-only lifecycle policy for future executable backend plugins."""

    requirements: tuple[BackendPluginLifecycleRequirement, ...]
    policy_issues: tuple[BackendPluginLifecyclePolicyIssue, ...]
    policy_id: str = BACKEND_PLUGIN_LIFECYCLE_POLICY_ID
    policy_contract: str = BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT
    policy_status: str = BACKEND_PLUGIN_LIFECYCLE_POLICY_STATUS
    execution_status: str = BACKEND_PLUGIN_LIFECYCLE_EXECUTION_STATUS
    sandbox_model_status: str = BACKEND_PLUGIN_LIFECYCLE_SANDBOX_STATUS
    plugin_discovery_enabled: bool = False
    artifact_execution_enabled: bool = False
    native_plugin_abi_enabled: bool = False
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_policy_text(self.policy_id, "policy_id")
        if self.policy_contract != BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT:
            raise ValueError("backend plugin lifecycle policy contract mismatch")
        if self.policy_status != BACKEND_PLUGIN_LIFECYCLE_POLICY_STATUS:
            raise ValueError("backend plugin lifecycle policy status mismatch")
        if self.execution_status != BACKEND_PLUGIN_LIFECYCLE_EXECUTION_STATUS:
            raise ValueError("backend plugin lifecycle execution status mismatch")
        if self.sandbox_model_status != BACKEND_PLUGIN_LIFECYCLE_SANDBOX_STATUS:
            raise ValueError("backend plugin lifecycle sandbox status mismatch")
        for field_name in (
            "plugin_discovery_enabled",
            "artifact_execution_enabled",
            "native_plugin_abi_enabled",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"{field_name} must be bool")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin lifecycle blocked surfaces changed")
        if type(self.requirements) is not tuple:
            raise TypeError("backend plugin lifecycle requirements must be a tuple")
        if len(self.requirements) > MAX_BACKEND_PLUGIN_LIFECYCLE_REQUIREMENTS:
            raise ValueError("backend plugin lifecycle requirement count exceeds limit")
        for requirement in self.requirements:
            if not isinstance(requirement, BackendPluginLifecycleRequirement):
                raise TypeError("backend plugin lifecycle requirements must be objects")
        requirement_ids = tuple(item.requirement_id for item in self.requirements)
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("backend plugin lifecycle requirements must be unique")
        if type(self.policy_issues) is not tuple:
            raise TypeError("backend plugin lifecycle policy_issues must be a tuple")
        if len(self.policy_issues) > MAX_BACKEND_PLUGIN_LIFECYCLE_POLICY_ISSUES:
            raise ValueError("backend plugin lifecycle issue count exceeds limit")
        for issue in self.policy_issues:
            if not isinstance(issue, BackendPluginLifecyclePolicyIssue):
                raise TypeError("backend plugin lifecycle policy_issues must be objects")
        expected_issues = _derive_policy_issues(self)
        if self.policy_issues != expected_issues:
            raise ValueError("backend plugin lifecycle policy issues must be derived")

    @property
    def missing_requirement_count(self) -> int:
        """Return the number of requirements that are not satisfied yet."""

        return sum(1 for item in self.requirements if item.status != "satisfied")

    @property
    def ready_to_enable_plugins(self) -> bool:
        """Return whether external executable plugins may be proposed for enablement."""

        return self.missing_requirement_count == 0 and not self.policy_issues

    @property
    def policy_enforced(self) -> bool:
        """Return whether current executable plugin surfaces are still blocked."""

        return (
            not self.plugin_discovery_enabled
            and not self.artifact_execution_enabled
            and not self.native_plugin_abi_enabled
            and not self.policy_issues
        )


class BackendPluginLifecyclePolicyError(ValueError):
    """Raised when backend plugin lifecycle policy evidence fails."""


def build_backend_plugin_lifecycle_policy_report(
    requirements: tuple[BackendPluginLifecycleRequirement, ...] | None = None,
) -> BackendPluginLifecyclePolicyReport:
    """Build the current blocking policy report for executable backend plugins."""

    normalized_requirements = (
        _current_lifecycle_requirements() if requirements is None else requirements
    )
    report = BackendPluginLifecyclePolicyReport(
        requirements=normalized_requirements,
        policy_issues=(),
    )
    return BackendPluginLifecyclePolicyReport(
        requirements=normalized_requirements,
        policy_issues=_derive_policy_issues(report),
    )


def assert_backend_plugin_lifecycle_policy(
    report: BackendPluginLifecyclePolicyReport,
) -> BackendPluginLifecyclePolicyReport:
    """Return the report or raise when executable plugin surfaces are not blocked."""

    if not isinstance(report, BackendPluginLifecyclePolicyReport):
        raise TypeError("backend plugin lifecycle policy must be report object")
    if not report.policy_enforced:
        lines = ["backend plugin lifecycle policy failed:"]
        for issue in report.policy_issues:
            lines.append(f"- {issue.subject}: {issue.issue_code}")
        raise BackendPluginLifecyclePolicyError("\n".join(lines))
    return report


def backend_plugin_lifecycle_policy_report_to_dict(
    report: BackendPluginLifecyclePolicyReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible plugin lifecycle policy report."""

    if not isinstance(report, BackendPluginLifecyclePolicyReport):
        raise TypeError("backend plugin lifecycle policy must be report object")
    return {
        "artifact_execution_enabled": report.artifact_execution_enabled,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "execution_status": report.execution_status,
        "missing_requirement_count": report.missing_requirement_count,
        "native_plugin_abi_enabled": report.native_plugin_abi_enabled,
        "plugin_discovery_enabled": report.plugin_discovery_enabled,
        "policy_contract": report.policy_contract,
        "policy_enforced": report.policy_enforced,
        "policy_id": report.policy_id,
        "policy_issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.policy_issues
        ],
        "policy_status": report.policy_status,
        "ready_to_enable_plugins": report.ready_to_enable_plugins,
        "requirement_count": len(report.requirements),
        "requirements": [
            {
                "evidence_id": requirement.evidence_id,
                "required_before": requirement.required_before,
                "requirement_id": requirement.requirement_id,
                "status": requirement.status,
            }
            for requirement in report.requirements
        ],
        "sandbox_model_status": report.sandbox_model_status,
        "schema_version": BACKEND_PLUGIN_LIFECYCLE_POLICY_REPORT_SCHEMA_VERSION,
    }


def dump_backend_plugin_lifecycle_policy_report(
    report: BackendPluginLifecyclePolicyReport,
) -> str:
    """Render a stable plugin lifecycle policy report."""

    text = json.dumps(
        backend_plugin_lifecycle_policy_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PLUGIN_LIFECYCLE_REPORT_BYTES:
        raise ValueError("backend plugin lifecycle policy report exceeds byte limit")
    return text + "\n"


def _current_lifecycle_requirements() -> tuple[BackendPluginLifecycleRequirement, ...]:
    return (
        BackendPluginLifecycleRequirement(
            requirement_id="capability_manifest_claim_review",
            status="satisfied",
            evidence_id="manifest_claim_review.data_only.v0",
            required_before="backend_plugin_discovery",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="backend_author_evidence_gate",
            status="satisfied",
            evidence_id="backend_author_evidence_gate.ci.v0",
            required_before="backend_plugin_discovery",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="trusted_executor_contract",
            status="satisfied",
            evidence_id="runtime_executor.trusted_backend.v0",
            required_before="generated_artifact_execution",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="plugin_lifecycle_rfc",
            status="satisfied",
            evidence_id="rfc_0217_backend_plugin_lifecycle_policy",
            required_before="backend_plugin_discovery",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="sandbox_model",
            status="satisfied",
            evidence_id=BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
            required_before="generated_artifact_execution",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="artifact_provenance",
            status="satisfied",
            evidence_id=BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
            required_before="generated_artifact_execution",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="resource_budget",
            status="satisfied",
            evidence_id=BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT,
            required_before="device_access",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="fuzz_negative_tests",
            status="satisfied",
            evidence_id=BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT,
            required_before="dynamic_library_loading",
        ),
        BackendPluginLifecycleRequirement(
            requirement_id="maintainer_approval",
            status="missing",
            evidence_id="not_approved",
            required_before="backend_plugin_discovery",
        ),
    )


def _derive_policy_issues(
    report: BackendPluginLifecyclePolicyReport,
) -> tuple[BackendPluginLifecyclePolicyIssue, ...]:
    issues: list[BackendPluginLifecyclePolicyIssue] = []
    required_ids = frozenset(BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS)
    observed_ids = frozenset(item.requirement_id for item in report.requirements)
    for requirement_id in BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS:
        if requirement_id not in observed_ids:
            issues.append(
                BackendPluginLifecyclePolicyIssue(
                    subject=requirement_id,
                    issue_code="missing_required_requirement",
                )
            )
    if not observed_ids.issubset(required_ids):
        for requirement_id in sorted(observed_ids - required_ids):
            issues.append(
                BackendPluginLifecyclePolicyIssue(
                    subject=requirement_id,
                    issue_code="missing_required_requirement",
                )
            )
    if report.plugin_discovery_enabled:
        issues.append(
            BackendPluginLifecyclePolicyIssue(
                subject="backend_plugin_discovery",
                issue_code="plugin_discovery_enabled",
            )
        )
    if report.artifact_execution_enabled:
        issues.append(
            BackendPluginLifecyclePolicyIssue(
                subject="generated_artifact_execution",
                issue_code="artifact_execution_enabled",
            )
        )
    if report.native_plugin_abi_enabled:
        issues.append(
            BackendPluginLifecyclePolicyIssue(
                subject="native_plugin_abi",
                issue_code="native_plugin_abi_enabled",
            )
        )
    if report.missing_requirement_count and (
        report.execution_status != BACKEND_PLUGIN_LIFECYCLE_EXECUTION_STATUS
    ):
        issues.append(
            BackendPluginLifecyclePolicyIssue(
                subject="execution_status",
                issue_code="external_plugins_enabled_before_requirements",
            )
        )
    sandbox_requirement = next(
        (
            item
            for item in report.requirements
            if item.requirement_id == "sandbox_model"
        ),
        None,
    )
    if (
        sandbox_requirement is not None
        and sandbox_requirement.status == "missing"
        and report.sandbox_model_status != BACKEND_PLUGIN_LIFECYCLE_SANDBOX_STATUS
    ):
        issues.append(
            BackendPluginLifecyclePolicyIssue(
                subject="sandbox_model",
                issue_code="sandbox_status_inconsistent",
            )
        )
    return tuple(issues)


def _validate_policy_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _POLICY_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend plugin lifecycle identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_PLUGIN_LIFECYCLE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend plugin lifecycle field limit")
    if value in _FORBIDDEN_POLICY_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "BACKEND_PLUGIN_LIFECYCLE_EXECUTION_STATUS",
    "BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT",
    "BACKEND_PLUGIN_LIFECYCLE_POLICY_ID",
    "BACKEND_PLUGIN_LIFECYCLE_POLICY_ISSUE_CODES",
    "BACKEND_PLUGIN_LIFECYCLE_POLICY_REPORT_SCHEMA_VERSION",
    "BACKEND_PLUGIN_LIFECYCLE_POLICY_STATUS",
    "BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS",
    "BACKEND_PLUGIN_LIFECYCLE_REQUIREMENT_STATUSES",
    "BACKEND_PLUGIN_LIFECYCLE_SANDBOX_STATUS",
    "MAX_BACKEND_PLUGIN_LIFECYCLE_FIELD_BYTES",
    "MAX_BACKEND_PLUGIN_LIFECYCLE_POLICY_ISSUES",
    "MAX_BACKEND_PLUGIN_LIFECYCLE_REPORT_BYTES",
    "MAX_BACKEND_PLUGIN_LIFECYCLE_REQUIREMENTS",
    "BackendPluginLifecyclePolicyError",
    "BackendPluginLifecyclePolicyIssue",
    "BackendPluginLifecyclePolicyReport",
    "BackendPluginLifecycleRequirement",
    "assert_backend_plugin_lifecycle_policy",
    "backend_plugin_lifecycle_policy_report_to_dict",
    "build_backend_plugin_lifecycle_policy_report",
    "dump_backend_plugin_lifecycle_policy_report",
]
