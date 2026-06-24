"""Data-only policy for promoting layout-conversion evidence to a gate."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.layout_conversion_digest_binding import (
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID,
)
from tuc.runtime.layout_conversion_gate_readiness import (
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID,
    RuntimeLayoutConversionGateReadinessReport,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_layout_conversion_gate_promotion_policy_report.v0"
)
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT = (
    "runtime_layout_conversion_gate_promotion_policy.data_only.v0"
)
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS = "review_evidence"
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID = (
    "runtime_layout_conversion_gate_promotion_policy_mixed"
)
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS = "accepted_candidate_policy"
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE = "single_graph_candidate"
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS = "not_enforced"
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_NEXT_ACTION = (
    "separate_runtime_evidence_gate_requirement_change"
)
RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REQUIRED_GATE_CHANGE = (
    "add_layout_conversion_evidence_to_mixed_graph_required_kinds"
)
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ISSUES = 16
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_FIELD_BYTES = 512

_PROMOTION_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_PROMOTION_TEXT = frozenset(
    {
        "allocation_handle",
        "backend_artifact",
        "callable",
        "command",
        "command_line",
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
        "tensor_values",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeLayoutConversionGatePromotionPolicyIssue:
    """One derived issue blocking layout-conversion gate promotion policy."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_promotion_text(self.subject, "issue subject")
        _validate_promotion_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeLayoutConversionGatePromotionPolicyReport:
    """Policy artifact for a future layout-conversion gate requirement."""

    target_graph_id: str
    target_artifact_kind: str
    target_artifact_id: str
    source_readiness_contract: str
    source_readiness_schema_version: str
    source_readiness_ready: bool
    source_readiness_status: str
    source_readiness_metadata_digest: str
    source_readiness_target_gate_status: str
    source_digest_binding_artifact_id: str
    issues: tuple[RuntimeLayoutConversionGatePromotionPolicyIssue, ...]
    policy_id: str = RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID
    policy_contract: str = RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT
    policy_status: str = RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS
    artifact_status: str = (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS
    )
    promotion_scope: str = RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE
    enforcement_status: str = RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS
    required_gate_change: str = (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REQUIRED_GATE_CHANGE
    )
    next_action: str = RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_NEXT_ACTION
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.target_graph_id, "target_graph_id"),
            (self.target_artifact_kind, "target_artifact_kind"),
            (self.target_artifact_id, "target_artifact_id"),
            (self.source_readiness_status, "source_readiness_status"),
            (
                self.source_readiness_target_gate_status,
                "source_readiness_target_gate_status",
            ),
            (self.source_digest_binding_artifact_id, "source_digest_binding_artifact_id"),
            (self.policy_id, "policy_id"),
            (self.policy_status, "policy_status"),
            (self.artifact_status, "artifact_status"),
            (self.promotion_scope, "promotion_scope"),
            (self.enforcement_status, "enforcement_status"),
            (self.required_gate_change, "required_gate_change"),
            (self.next_action, "next_action"),
        ):
            _validate_promotion_text(value, label)
        if self.target_graph_id != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID:
            raise ValueError("runtime layout conversion promotion graph mismatch")
        if (
            self.target_artifact_kind
            != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
        ):
            raise ValueError("runtime layout conversion promotion artifact kind mismatch")
        if (
            self.target_artifact_id
            != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
        ):
            raise ValueError("runtime layout conversion promotion artifact id mismatch")
        if self.source_readiness_contract != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT:
            raise ValueError("runtime layout conversion promotion readiness contract mismatch")
        if self.source_readiness_schema_version != (
            RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("runtime layout conversion promotion readiness schema mismatch")
        if not isinstance(self.source_readiness_ready, bool):
            raise TypeError("source_readiness_ready must be bool")
        _validate_digest(
            self.source_readiness_metadata_digest,
            "source_readiness_metadata_digest",
        )
        if self.policy_contract != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT:
            raise ValueError("runtime layout conversion promotion policy contract mismatch")
        if self.policy_status != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS:
            raise ValueError("runtime layout conversion promotion policy status mismatch")
        if (
            self.artifact_status
            != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS
        ):
            raise ValueError("runtime layout conversion promotion artifact status mismatch")
        if self.promotion_scope != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE:
            raise ValueError("runtime layout conversion promotion scope mismatch")
        if (
            self.enforcement_status
            != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS
        ):
            raise ValueError("runtime layout conversion promotion enforcement mismatch")
        if (
            self.required_gate_change
            != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REQUIRED_GATE_CHANGE
        ):
            raise ValueError("runtime layout conversion promotion gate change mismatch")
        if self.next_action != RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_NEXT_ACTION:
            raise ValueError("runtime layout conversion promotion next action mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime layout conversion promotion must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime layout conversion promotion blocked surfaces changed")
        _validate_issues(self.issues)
        expected_issues = _derive_issues(self)
        if self.issues != expected_issues:
            raise ValueError("runtime layout conversion promotion issues must be derived")

    @property
    def policy_complete(self) -> bool:
        """Return whether the promotion policy is internally complete."""

        return not self.issues

    @property
    def promotion_ready(self) -> bool:
        """Return whether a separate gate-enforcement change can be proposed."""

        return self.policy_complete

    @property
    def policy_metadata_digest(self) -> str:
        """Return a digest over policy metadata only."""

        payload = {
            "enforcement_status": self.enforcement_status,
            "next_action": self.next_action,
            "policy_id": self.policy_id,
            "promotion_scope": self.promotion_scope,
            "required_gate_change": self.required_gate_change,
            "source_digest_binding_artifact_id": self.source_digest_binding_artifact_id,
            "source_readiness_metadata_digest": self.source_readiness_metadata_digest,
            "source_readiness_target_gate_status": (
                self.source_readiness_target_gate_status
            ),
            "target_artifact_id": self.target_artifact_id,
            "target_artifact_kind": self.target_artifact_kind,
            "target_graph_id": self.target_graph_id,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeLayoutConversionGatePromotionPolicyError(AssertionError):
    """Raised when layout-conversion gate promotion policy is incomplete."""


def build_runtime_layout_conversion_gate_promotion_policy_report(
    readiness: RuntimeLayoutConversionGateReadinessReport,
) -> RuntimeLayoutConversionGatePromotionPolicyReport:
    """Build the current layout-conversion gate-promotion policy report."""

    if not isinstance(readiness, RuntimeLayoutConversionGateReadinessReport):
        raise TypeError("layout conversion promotion policy requires readiness report")
    source_digest_binding_artifact_id = _digest_binding_artifact_id(readiness)
    issues = _derive_issues_from_values(
        target_graph_id=readiness.target_graph_id,
        target_artifact_kind=readiness.target_artifact_kind,
        target_artifact_id=readiness.target_artifact_id,
        source_readiness_ready=readiness.ready,
        source_readiness_status=readiness.readiness_status,
        source_readiness_target_gate_status=readiness.target_gate_status,
        source_digest_binding_artifact_id=source_digest_binding_artifact_id,
    )
    return RuntimeLayoutConversionGatePromotionPolicyReport(
        target_graph_id=readiness.target_graph_id,
        target_artifact_kind=readiness.target_artifact_kind,
        target_artifact_id=readiness.target_artifact_id,
        source_readiness_contract=readiness.readiness_contract,
        source_readiness_schema_version=(
            RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION
        ),
        source_readiness_ready=readiness.ready,
        source_readiness_status=readiness.readiness_status,
        source_readiness_metadata_digest=readiness.readiness_metadata_digest,
        source_readiness_target_gate_status=readiness.target_gate_status,
        source_digest_binding_artifact_id=source_digest_binding_artifact_id,
        issues=issues,
    )


def assert_runtime_layout_conversion_gate_promotion_policy(
    report: RuntimeLayoutConversionGatePromotionPolicyReport,
) -> RuntimeLayoutConversionGatePromotionPolicyReport:
    """Return the report or raise when promotion policy is incomplete."""

    if not isinstance(report, RuntimeLayoutConversionGatePromotionPolicyReport):
        raise TypeError("layout conversion gate promotion policy report required")
    if report.issues:
        lines = [
            "runtime layout conversion gate promotion policy incomplete for "
            f"{report.target_graph_id!r}:"
        ]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeLayoutConversionGatePromotionPolicyError("\n".join(lines))
    return report


def runtime_layout_conversion_gate_promotion_policy_report_to_dict(
    report: RuntimeLayoutConversionGatePromotionPolicyReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible promotion policy data."""

    if not isinstance(report, RuntimeLayoutConversionGatePromotionPolicyReport):
        raise TypeError("layout conversion gate promotion policy report required")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "enforcement_status": report.enforcement_status,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "next_action": report.next_action,
        "policy_complete": report.policy_complete,
        "policy_contract": report.policy_contract,
        "policy_id": report.policy_id,
        "policy_metadata_digest": report.policy_metadata_digest,
        "policy_status": report.policy_status,
        "promotion_ready": report.promotion_ready,
        "promotion_scope": report.promotion_scope,
        "raw_value_policy": report.raw_value_policy,
        "required_gate_change": report.required_gate_change,
        "schema_version": (
            RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_REPORT_SCHEMA_VERSION
        ),
        "source_digest_binding_artifact_id": report.source_digest_binding_artifact_id,
        "source_readiness_contract": report.source_readiness_contract,
        "source_readiness_metadata_digest": report.source_readiness_metadata_digest,
        "source_readiness_ready": report.source_readiness_ready,
        "source_readiness_schema_version": report.source_readiness_schema_version,
        "source_readiness_status": report.source_readiness_status,
        "source_readiness_target_gate_status": (
            report.source_readiness_target_gate_status
        ),
        "target_artifact_id": report.target_artifact_id,
        "target_artifact_kind": report.target_artifact_kind,
        "target_graph_id": report.target_graph_id,
    }


def dump_runtime_layout_conversion_gate_promotion_policy_report(
    report: RuntimeLayoutConversionGatePromotionPolicyReport,
) -> str:
    """Render stable data-only layout-conversion gate-promotion policy."""

    text = json.dumps(
        runtime_layout_conversion_gate_promotion_policy_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REPORT_BYTES
    ):
        raise ValueError("runtime layout conversion promotion report too large")
    return text + "\n"


def _digest_binding_artifact_id(
    readiness: RuntimeLayoutConversionGateReadinessReport,
) -> str:
    for check in readiness.checks:
        if check.check_name == "hs_ir_and_tensor_store_digest_binding":
            return check.evidence_id
    return "missing_hs_ir_tensor_store_digest_binding"


def _derive_issues(
    report: RuntimeLayoutConversionGatePromotionPolicyReport,
) -> tuple[RuntimeLayoutConversionGatePromotionPolicyIssue, ...]:
    return _derive_issues_from_values(
        target_graph_id=report.target_graph_id,
        target_artifact_kind=report.target_artifact_kind,
        target_artifact_id=report.target_artifact_id,
        source_readiness_ready=report.source_readiness_ready,
        source_readiness_status=report.source_readiness_status,
        source_readiness_target_gate_status=report.source_readiness_target_gate_status,
        source_digest_binding_artifact_id=report.source_digest_binding_artifact_id,
    )


def _derive_issues_from_values(
    *,
    target_graph_id: str,
    target_artifact_kind: str,
    target_artifact_id: str,
    source_readiness_ready: bool,
    source_readiness_status: str,
    source_readiness_target_gate_status: str,
    source_digest_binding_artifact_id: str,
) -> tuple[RuntimeLayoutConversionGatePromotionPolicyIssue, ...]:
    issues: list[RuntimeLayoutConversionGatePromotionPolicyIssue] = []
    if target_graph_id != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID:
        issues.append(_issue("target_graph_id", "target_graph_mismatch"))
    if target_artifact_kind != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND:
        issues.append(_issue("target_artifact_kind", "target_artifact_kind_mismatch"))
    if target_artifact_id != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID:
        issues.append(_issue("target_artifact_id", "target_artifact_id_mismatch"))
    if not source_readiness_ready or source_readiness_status != "ready":
        issues.append(_issue("source_readiness", "readiness_not_ready"))
    if (
        source_readiness_target_gate_status
        != RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS
    ):
        issues.append(_issue("source_readiness", "unexpected_gate_status"))
    if source_digest_binding_artifact_id != RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID:
        issues.append(_issue("source_digest_binding", "digest_binding_artifact_mismatch"))
    if len(issues) > MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ISSUES:
        raise ValueError("runtime layout conversion promotion issue limit exceeded")
    return tuple(dict.fromkeys(issues))


def _issue(
    subject: str,
    issue_code: str,
) -> RuntimeLayoutConversionGatePromotionPolicyIssue:
    return RuntimeLayoutConversionGatePromotionPolicyIssue(
        subject=subject,
        issue_code=issue_code,
    )


def _validate_issues(
    issues: tuple[RuntimeLayoutConversionGatePromotionPolicyIssue, ...],
) -> None:
    if type(issues) is not tuple:
        raise TypeError("runtime layout conversion promotion issues must be a tuple")
    if len(issues) > MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ISSUES:
        raise ValueError("runtime layout conversion promotion issue limit exceeded")
    for issue in issues:
        if not isinstance(issue, RuntimeLayoutConversionGatePromotionPolicyIssue):
            raise TypeError("runtime layout conversion promotion issues must be issue objects")


def _validate_promotion_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROMOTION_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe layout conversion promotion identifier")
    if len(value.encode("utf-8")) > (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_FIELD_BYTES
    ):
        raise ValueError(f"{label} exceeds layout conversion promotion field limit")
    if value in _FORBIDDEN_PROMOTION_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_FIELD_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ISSUES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REPORT_BYTES",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_NEXT_ACTION",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_REPORT_SCHEMA_VERSION",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REQUIRED_GATE_CHANGE",
    "RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE",
    "RuntimeLayoutConversionGatePromotionPolicyError",
    "RuntimeLayoutConversionGatePromotionPolicyIssue",
    "RuntimeLayoutConversionGatePromotionPolicyReport",
    "assert_runtime_layout_conversion_gate_promotion_policy",
    "build_runtime_layout_conversion_gate_promotion_policy_report",
    "dump_runtime_layout_conversion_gate_promotion_policy_report",
    "runtime_layout_conversion_gate_promotion_policy_report_to_dict",
]
