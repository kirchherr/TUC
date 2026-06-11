"""Versioned policy report for runtime candidate scoring semantics."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

RUNTIME_CANDIDATE_SCORING_POLICY_SCHEMA_VERSION = (
    "tuc.runtime_candidate_scoring_policy.v0"
)
RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT = (
    "runtime_candidate_scoring_policy.data_only.v0"
)
RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS = (
    "transfer_score",
    "layout_conversion_bytes",
    "transfer_bytes",
    "preferred_memory_domain_match",
    "backend_name_tiebreaker",
)
RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS = (
    "noise_penalty",
    "error_budget_margin",
    "calibration_confidence",
    "benchmark_score",
)
RUNTIME_CANDIDATE_SCORING_STATUSES = frozenset({"active", "blocked"})
RUNTIME_CANDIDATE_SCORING_ORDERINGS = frozenset(
    {"minimize", "prefer_true", "lexical_ascending", "blocked"}
)
MAX_RUNTIME_CANDIDATE_SCORING_COMPONENTS = 32
MAX_RUNTIME_CANDIDATE_SCORING_ISSUES = 64
MAX_RUNTIME_CANDIDATE_SCORING_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_CANDIDATE_SCORING_FIELD_BYTES = 512

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
class RuntimeCandidateScoringComponent:
    """One candidate scoring component in the runtime policy."""

    component_name: str
    status: str
    ordering: str
    evidence_source: str
    blocker: str

    def __post_init__(self) -> None:
        _validate_policy_text(self.component_name, "component_name")
        if self.status not in RUNTIME_CANDIDATE_SCORING_STATUSES:
            raise ValueError("runtime candidate scoring status is unsupported")
        if self.ordering not in RUNTIME_CANDIDATE_SCORING_ORDERINGS:
            raise ValueError("runtime candidate scoring ordering is unsupported")
        _validate_policy_text(self.evidence_source, "evidence_source")
        _validate_policy_text(self.blocker, "blocker")
        if self.status == "active" and self.ordering == "blocked":
            raise ValueError("active scoring component cannot use blocked ordering")
        if self.status == "active" and self.blocker != "none":
            raise ValueError("active scoring component must not have a blocker")
        if self.status == "blocked" and self.ordering != "blocked":
            raise ValueError("blocked scoring component must use blocked ordering")
        if self.status == "blocked" and self.blocker == "none":
            raise ValueError("blocked scoring component must have a blocker")


@dataclass(frozen=True)
class RuntimeCandidateScoringPolicyIssue:
    """One derived issue in runtime candidate scoring policy evidence."""

    component_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_policy_text(self.component_name, "issue component_name")
        _validate_policy_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeCandidateScoringPolicyReport:
    """Deterministic policy report for candidate scoring semantics."""

    components: tuple[RuntimeCandidateScoringComponent, ...]
    issues: tuple[RuntimeCandidateScoringPolicyIssue, ...]
    policy_contract: str = RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT
    automatic_global_optimization_enabled: bool = False
    noise_error_budget_components_enabled: bool = False
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.policy_contract != RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT:
            raise ValueError("runtime candidate scoring policy contract mismatch")
        if not isinstance(self.automatic_global_optimization_enabled, bool):
            raise TypeError("automatic_global_optimization_enabled must be bool")
        if self.automatic_global_optimization_enabled:
            raise ValueError("automatic global optimization is not enabled in policy v0")
        if not isinstance(self.noise_error_budget_components_enabled, bool):
            raise TypeError("noise_error_budget_components_enabled must be bool")
        if self.noise_error_budget_components_enabled:
            raise ValueError("noise/error-budget score components are blocked in policy v0")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError(
                "runtime candidate scoring policy blocked execution surfaces changed"
            )
        if type(self.components) is not tuple:
            raise TypeError("runtime candidate scoring components must be a tuple")
        if not self.components:
            raise ValueError("runtime candidate scoring policy must contain components")
        if len(self.components) > MAX_RUNTIME_CANDIDATE_SCORING_COMPONENTS:
            raise ValueError("runtime candidate scoring component count exceeds limit")
        for component in self.components:
            if not isinstance(component, RuntimeCandidateScoringComponent):
                raise TypeError(
                    "runtime candidate scoring components must be component objects"
                )
        if type(self.issues) is not tuple:
            raise TypeError("runtime candidate scoring issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_CANDIDATE_SCORING_ISSUES:
            raise ValueError("runtime candidate scoring issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeCandidateScoringPolicyIssue):
                raise TypeError(
                    "runtime candidate scoring issues must be issue objects"
                )
        expected_issues = _derive_policy_issues(self.components)
        if self.issues != expected_issues:
            raise ValueError("runtime candidate scoring policy issues must be derived")

    @property
    def policy_complete(self) -> bool:
        """Return whether the policy matches the current accepted scoring semantics."""

        return not self.issues

    @property
    def active_component_order(self) -> tuple[str, ...]:
        """Return active component order."""

        return tuple(
            component.component_name
            for component in self.components
            if component.status == "active"
        )

    @property
    def blocked_component_names(self) -> tuple[str, ...]:
        """Return blocked future component names."""

        return tuple(
            component.component_name
            for component in self.components
            if component.status == "blocked"
        )


class RuntimeCandidateScoringPolicyError(AssertionError):
    """Raised when candidate scoring policy evidence is incomplete."""


def build_runtime_candidate_scoring_policy_report() -> RuntimeCandidateScoringPolicyReport:
    """Build the current runtime candidate scoring policy report."""

    components = (
        RuntimeCandidateScoringComponent(
            component_name="transfer_score",
            status="active",
            ordering="minimize",
            evidence_source="CandidateScore.transfer_score",
            blocker="none",
        ),
        RuntimeCandidateScoringComponent(
            component_name="layout_conversion_bytes",
            status="active",
            ordering="minimize",
            evidence_source="CandidateScore.layout_conversion_bytes",
            blocker="none",
        ),
        RuntimeCandidateScoringComponent(
            component_name="transfer_bytes",
            status="active",
            ordering="minimize",
            evidence_source="CandidateScore.transfer_bytes",
            blocker="none",
        ),
        RuntimeCandidateScoringComponent(
            component_name="preferred_memory_domain_match",
            status="active",
            ordering="prefer_true",
            evidence_source="CandidateScore.preferred_memory_domain_match",
            blocker="none",
        ),
        RuntimeCandidateScoringComponent(
            component_name="backend_name_tiebreaker",
            status="active",
            ordering="lexical_ascending",
            evidence_source="CandidateScore.backend_name",
            blocker="none",
        ),
        RuntimeCandidateScoringComponent(
            component_name="noise_penalty",
            status="blocked",
            ordering="blocked",
            evidence_source="future_noise_model",
            blocker="noise_model_not_stable",
        ),
        RuntimeCandidateScoringComponent(
            component_name="error_budget_margin",
            status="blocked",
            ordering="blocked",
            evidence_source="future_error_budget_model",
            blocker="error_budget_model_not_stable",
        ),
        RuntimeCandidateScoringComponent(
            component_name="calibration_confidence",
            status="blocked",
            ordering="blocked",
            evidence_source="future_calibration_artifact",
            blocker="calibration_evidence_not_stable",
        ),
        RuntimeCandidateScoringComponent(
            component_name="benchmark_score",
            status="blocked",
            ordering="blocked",
            evidence_source="future_benchmark_artifact",
            blocker="performance_claim_boundary",
        ),
    )
    return RuntimeCandidateScoringPolicyReport(
        components=components,
        issues=_derive_policy_issues(components),
    )


def assert_runtime_candidate_scoring_policy(
    report: RuntimeCandidateScoringPolicyReport,
) -> RuntimeCandidateScoringPolicyReport:
    """Return the report or raise when candidate scoring policy evidence fails."""

    if not isinstance(report, RuntimeCandidateScoringPolicyReport):
        raise TypeError("runtime candidate scoring policy report must be report object")
    if report.issues:
        lines = ["runtime candidate scoring policy is incomplete:"]
        lines.extend(
            f"- {issue.component_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeCandidateScoringPolicyError("\n".join(lines))
    return report


def runtime_candidate_scoring_policy_report_to_dict(
    report: RuntimeCandidateScoringPolicyReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible scoring policy report."""

    if not isinstance(report, RuntimeCandidateScoringPolicyReport):
        raise TypeError("runtime candidate scoring policy report must be report object")
    return {
        "active_component_order": list(report.active_component_order),
        "automatic_global_optimization_enabled": (
            report.automatic_global_optimization_enabled
        ),
        "blocked_component_names": list(report.blocked_component_names),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "component_count": len(report.components),
        "components": [
            {
                "blocker": component.blocker,
                "component_name": component.component_name,
                "evidence_source": component.evidence_source,
                "ordering": component.ordering,
                "status": component.status,
            }
            for component in report.components
        ],
        "issues": [
            {
                "component_name": issue.component_name,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "noise_error_budget_components_enabled": (
            report.noise_error_budget_components_enabled
        ),
        "policy_complete": report.policy_complete,
        "policy_contract": report.policy_contract,
        "schema_version": RUNTIME_CANDIDATE_SCORING_POLICY_SCHEMA_VERSION,
    }


def dump_runtime_candidate_scoring_policy_report(
    report: RuntimeCandidateScoringPolicyReport,
) -> str:
    """Render a stable runtime candidate scoring policy report."""

    text = json.dumps(
        runtime_candidate_scoring_policy_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_CANDIDATE_SCORING_REPORT_BYTES:
        raise ValueError("runtime candidate scoring policy report exceeds byte limit")
    return text + "\n"


def _derive_policy_issues(
    components: tuple[RuntimeCandidateScoringComponent, ...],
) -> tuple[RuntimeCandidateScoringPolicyIssue, ...]:
    issues: list[RuntimeCandidateScoringPolicyIssue] = []
    names = tuple(component.component_name for component in components)
    if len(names) != len(set(names)):
        issues.append(
            RuntimeCandidateScoringPolicyIssue(
                component_name="policy",
                issue_code="component_names_not_unique",
            )
        )

    active = tuple(
        component.component_name
        for component in components
        if component.status == "active"
    )
    if active != RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS:
        issues.append(
            RuntimeCandidateScoringPolicyIssue(
                component_name="policy",
                issue_code="active_component_order_mismatch",
            )
        )

    blocked = tuple(
        component.component_name
        for component in components
        if component.status == "blocked"
    )
    if blocked != RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS:
        issues.append(
            RuntimeCandidateScoringPolicyIssue(
                component_name="policy",
                issue_code="blocked_component_set_mismatch",
            )
        )

    for component in components:
        if (
            component.component_name in RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS
            and component.status != "blocked"
        ):
            issues.append(
                RuntimeCandidateScoringPolicyIssue(
                    component_name=component.component_name,
                    issue_code="blocked_component_enabled",
                )
            )

    return tuple(issues)


def _validate_policy_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _POLICY_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime scoring policy identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_CANDIDATE_SCORING_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime scoring policy field limit")
    if value in _FORBIDDEN_POLICY_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "MAX_RUNTIME_CANDIDATE_SCORING_COMPONENTS",
    "MAX_RUNTIME_CANDIDATE_SCORING_FIELD_BYTES",
    "MAX_RUNTIME_CANDIDATE_SCORING_ISSUES",
    "MAX_RUNTIME_CANDIDATE_SCORING_REPORT_BYTES",
    "RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS",
    "RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS",
    "RUNTIME_CANDIDATE_SCORING_ORDERINGS",
    "RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT",
    "RUNTIME_CANDIDATE_SCORING_POLICY_SCHEMA_VERSION",
    "RUNTIME_CANDIDATE_SCORING_STATUSES",
    "RuntimeCandidateScoringComponent",
    "RuntimeCandidateScoringPolicyError",
    "RuntimeCandidateScoringPolicyIssue",
    "RuntimeCandidateScoringPolicyReport",
    "assert_runtime_candidate_scoring_policy",
    "build_runtime_candidate_scoring_policy_report",
    "dump_runtime_candidate_scoring_policy_report",
    "runtime_candidate_scoring_policy_report_to_dict",
]
