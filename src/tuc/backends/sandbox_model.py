"""Data-only sandbox model for future executable backend plugins."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_PLUGIN_SANDBOX_MODEL_REPORT_SCHEMA_VERSION = (
    "tuc.backend_plugin_sandbox_model_report.v0"
)
BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT = "backend_plugin_sandbox_model.data_only.v0"
BACKEND_PLUGIN_SANDBOX_MODEL_ID = "backend_plugin_sandbox_model_v0"
BACKEND_PLUGIN_SANDBOX_MODEL_STATUS = "accepted_data_only_model"
BACKEND_PLUGIN_SANDBOX_EXECUTION_PERMISSION = "not_granted"
BACKEND_PLUGIN_SANDBOX_ISOLATION_STRATEGY = (
    "separate_worker_process_or_container_required"
)
BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS = (
    "explicit_opt_in_enablement",
    "capability_manifest_pre_review",
    "content_digest_artifact_binding",
    "no_compile_time_plugin_execution",
    "deny_host_path_access",
    "deny_environment_secret_access",
    "deny_network_access",
    "deny_device_access_by_default",
    "deny_dynamic_library_loading_by_default",
    "bounded_resource_budget",
    "content_addressed_cache_scope",
    "metadata_only_diagnostics",
)
BACKEND_PLUGIN_SANDBOX_CONTROL_STATUSES = frozenset({"required"})
BACKEND_PLUGIN_SANDBOX_ISSUE_CODES = frozenset(
    {
        "execution_permission_granted",
        "missing_required_control",
        "sandbox_control_not_required",
        "sandbox_model_status_invalid",
    }
)
MAX_BACKEND_PLUGIN_SANDBOX_CONTROLS = 32
MAX_BACKEND_PLUGIN_SANDBOX_ISSUES = 64
MAX_BACKEND_PLUGIN_SANDBOX_REPORT_BYTES = 64 * 1024
MAX_BACKEND_PLUGIN_SANDBOX_FIELD_BYTES = 512

_SANDBOX_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_SANDBOX_TEXT = frozenset(
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
class BackendPluginSandboxControl:
    """One required control in the future executable backend sandbox."""

    control_id: str
    status: str
    protects_surface: str

    def __post_init__(self) -> None:
        _validate_sandbox_text(self.control_id, "control_id")
        _validate_sandbox_text(self.protects_surface, "protects_surface")
        if self.status not in BACKEND_PLUGIN_SANDBOX_CONTROL_STATUSES:
            raise ValueError("backend plugin sandbox control status unsupported")


@dataclass(frozen=True)
class BackendPluginSandboxIssue:
    """One derived sandbox model issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_sandbox_text(self.subject, "sandbox issue subject")
        _validate_sandbox_text(self.issue_code, "sandbox issue_code")
        if self.issue_code not in BACKEND_PLUGIN_SANDBOX_ISSUE_CODES:
            raise ValueError("backend plugin sandbox issue unsupported")


@dataclass(frozen=True)
class BackendPluginSandboxModelReport:
    """Current sandbox model for future executable backend plugins."""

    controls: tuple[BackendPluginSandboxControl, ...]
    issues: tuple[BackendPluginSandboxIssue, ...]
    sandbox_model_id: str = BACKEND_PLUGIN_SANDBOX_MODEL_ID
    sandbox_contract: str = BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    sandbox_model_status: str = BACKEND_PLUGIN_SANDBOX_MODEL_STATUS
    execution_permission: str = BACKEND_PLUGIN_SANDBOX_EXECUTION_PERMISSION
    isolation_strategy: str = BACKEND_PLUGIN_SANDBOX_ISOLATION_STRATEGY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_sandbox_text(self.sandbox_model_id, "sandbox_model_id")
        if self.sandbox_contract != BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT:
            raise ValueError("backend plugin sandbox contract mismatch")
        if self.sandbox_model_status != BACKEND_PLUGIN_SANDBOX_MODEL_STATUS:
            raise ValueError("backend plugin sandbox model status mismatch")
        if self.execution_permission != BACKEND_PLUGIN_SANDBOX_EXECUTION_PERMISSION:
            raise ValueError("backend plugin sandbox execution permission mismatch")
        if self.isolation_strategy != BACKEND_PLUGIN_SANDBOX_ISOLATION_STRATEGY:
            raise ValueError("backend plugin sandbox isolation strategy mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin sandbox blocked surfaces changed")
        if type(self.controls) is not tuple:
            raise TypeError("backend plugin sandbox controls must be a tuple")
        if len(self.controls) > MAX_BACKEND_PLUGIN_SANDBOX_CONTROLS:
            raise ValueError("backend plugin sandbox control count exceeds limit")
        for control in self.controls:
            if not isinstance(control, BackendPluginSandboxControl):
                raise TypeError("backend plugin sandbox controls must be objects")
        control_ids = tuple(control.control_id for control in self.controls)
        if len(control_ids) != len(set(control_ids)):
            raise ValueError("backend plugin sandbox controls must be unique")
        if type(self.issues) is not tuple:
            raise TypeError("backend plugin sandbox issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_PLUGIN_SANDBOX_ISSUES:
            raise ValueError("backend plugin sandbox issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPluginSandboxIssue):
                raise TypeError("backend plugin sandbox issues must be objects")
        expected_issues = _derive_sandbox_issues(self)
        if self.issues != expected_issues:
            raise ValueError("backend plugin sandbox issues must be derived")

    @property
    def model_ready(self) -> bool:
        """Return whether the sandbox model evidence is internally complete."""

        return not self.issues

    @property
    def execution_allowed(self) -> bool:
        """Return whether this data-only model grants execution permission."""

        return False


class BackendPluginSandboxModelError(ValueError):
    """Raised when backend plugin sandbox model evidence fails."""


def build_backend_plugin_sandbox_model_report(
    controls: tuple[BackendPluginSandboxControl, ...] | None = None,
) -> BackendPluginSandboxModelReport:
    """Build the current data-only sandbox model report."""

    normalized_controls = _current_sandbox_controls() if controls is None else controls
    report = BackendPluginSandboxModelReport(
        controls=normalized_controls,
        issues=(),
    )
    return BackendPluginSandboxModelReport(
        controls=normalized_controls,
        issues=_derive_sandbox_issues(report),
    )


def assert_backend_plugin_sandbox_model(
    report: BackendPluginSandboxModelReport,
) -> BackendPluginSandboxModelReport:
    """Return the report or raise when the sandbox model is incomplete."""

    if not isinstance(report, BackendPluginSandboxModelReport):
        raise TypeError("backend plugin sandbox model must be report object")
    if not report.model_ready:
        lines = ["backend plugin sandbox model failed:"]
        for issue in report.issues:
            lines.append(f"- {issue.subject}: {issue.issue_code}")
        raise BackendPluginSandboxModelError("\n".join(lines))
    return report


def backend_plugin_sandbox_model_report_to_dict(
    report: BackendPluginSandboxModelReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible sandbox model report."""

    if not isinstance(report, BackendPluginSandboxModelReport):
        raise TypeError("backend plugin sandbox model must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "control_count": len(report.controls),
        "controls": [
            {
                "control_id": control.control_id,
                "protects_surface": control.protects_surface,
                "status": control.status,
            }
            for control in report.controls
        ],
        "execution_allowed": report.execution_allowed,
        "execution_permission": report.execution_permission,
        "isolation_strategy": report.isolation_strategy,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "model_ready": report.model_ready,
        "sandbox_contract": report.sandbox_contract,
        "sandbox_model_id": report.sandbox_model_id,
        "sandbox_model_status": report.sandbox_model_status,
        "schema_version": BACKEND_PLUGIN_SANDBOX_MODEL_REPORT_SCHEMA_VERSION,
    }


def dump_backend_plugin_sandbox_model_report(
    report: BackendPluginSandboxModelReport,
) -> str:
    """Render a stable backend plugin sandbox model report."""

    text = json.dumps(
        backend_plugin_sandbox_model_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PLUGIN_SANDBOX_REPORT_BYTES:
        raise ValueError("backend plugin sandbox model report exceeds byte limit")
    return text + "\n"


def _current_sandbox_controls() -> tuple[BackendPluginSandboxControl, ...]:
    return (
        BackendPluginSandboxControl(
            control_id="explicit_opt_in_enablement",
            status="required",
            protects_surface="backend_plugin_discovery",
        ),
        BackendPluginSandboxControl(
            control_id="capability_manifest_pre_review",
            status="required",
            protects_surface="backend_plugin_discovery",
        ),
        BackendPluginSandboxControl(
            control_id="content_digest_artifact_binding",
            status="required",
            protects_surface="generated_artifact_execution",
        ),
        BackendPluginSandboxControl(
            control_id="no_compile_time_plugin_execution",
            status="required",
            protects_surface="dynamic_import",
        ),
        BackendPluginSandboxControl(
            control_id="deny_host_path_access",
            status="required",
            protects_surface="generated_artifact_execution",
        ),
        BackendPluginSandboxControl(
            control_id="deny_environment_secret_access",
            status="required",
            protects_surface="subprocess_execution",
        ),
        BackendPluginSandboxControl(
            control_id="deny_network_access",
            status="required",
            protects_surface="network_access",
        ),
        BackendPluginSandboxControl(
            control_id="deny_device_access_by_default",
            status="required",
            protects_surface="device_access",
        ),
        BackendPluginSandboxControl(
            control_id="deny_dynamic_library_loading_by_default",
            status="required",
            protects_surface="dynamic_library_loading",
        ),
        BackendPluginSandboxControl(
            control_id="bounded_resource_budget",
            status="required",
            protects_surface="generated_artifact_execution",
        ),
        BackendPluginSandboxControl(
            control_id="content_addressed_cache_scope",
            status="required",
            protects_surface="generated_artifact_execution",
        ),
        BackendPluginSandboxControl(
            control_id="metadata_only_diagnostics",
            status="required",
            protects_surface="generated_artifact_execution",
        ),
    )


def _derive_sandbox_issues(
    report: BackendPluginSandboxModelReport,
) -> tuple[BackendPluginSandboxIssue, ...]:
    issues: list[BackendPluginSandboxIssue] = []
    required_ids = frozenset(BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS)
    observed_ids = frozenset(control.control_id for control in report.controls)
    for control_id in BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS:
        if control_id not in observed_ids:
            issues.append(
                BackendPluginSandboxIssue(
                    subject=control_id,
                    issue_code="missing_required_control",
                )
            )
    if not observed_ids.issubset(required_ids):
        for control_id in sorted(observed_ids - required_ids):
            issues.append(
                BackendPluginSandboxIssue(
                    subject=control_id,
                    issue_code="missing_required_control",
                )
            )
    for control in report.controls:
        if control.status != "required":
            issues.append(
                BackendPluginSandboxIssue(
                    subject=control.control_id,
                    issue_code="sandbox_control_not_required",
                )
            )
    if report.sandbox_model_status != BACKEND_PLUGIN_SANDBOX_MODEL_STATUS:
        issues.append(
            BackendPluginSandboxIssue(
                subject="sandbox_model_status",
                issue_code="sandbox_model_status_invalid",
            )
        )
    if report.execution_permission != BACKEND_PLUGIN_SANDBOX_EXECUTION_PERMISSION:
        issues.append(
            BackendPluginSandboxIssue(
                subject="execution_permission",
                issue_code="execution_permission_granted",
            )
        )
    return tuple(issues)


def _validate_sandbox_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SANDBOX_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend plugin sandbox identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_PLUGIN_SANDBOX_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend plugin sandbox field limit")
    if value in _FORBIDDEN_SANDBOX_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "BACKEND_PLUGIN_SANDBOX_CONTROL_STATUSES",
    "BACKEND_PLUGIN_SANDBOX_EXECUTION_PERMISSION",
    "BACKEND_PLUGIN_SANDBOX_ISOLATION_STRATEGY",
    "BACKEND_PLUGIN_SANDBOX_ISSUE_CODES",
    "BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT",
    "BACKEND_PLUGIN_SANDBOX_MODEL_ID",
    "BACKEND_PLUGIN_SANDBOX_MODEL_REPORT_SCHEMA_VERSION",
    "BACKEND_PLUGIN_SANDBOX_MODEL_STATUS",
    "BACKEND_PLUGIN_SANDBOX_REQUIRED_CONTROLS",
    "MAX_BACKEND_PLUGIN_SANDBOX_CONTROLS",
    "MAX_BACKEND_PLUGIN_SANDBOX_FIELD_BYTES",
    "MAX_BACKEND_PLUGIN_SANDBOX_ISSUES",
    "MAX_BACKEND_PLUGIN_SANDBOX_REPORT_BYTES",
    "BackendPluginSandboxControl",
    "BackendPluginSandboxIssue",
    "BackendPluginSandboxModelError",
    "BackendPluginSandboxModelReport",
    "assert_backend_plugin_sandbox_model",
    "backend_plugin_sandbox_model_report_to_dict",
    "build_backend_plugin_sandbox_model_report",
    "dump_backend_plugin_sandbox_model_report",
]
