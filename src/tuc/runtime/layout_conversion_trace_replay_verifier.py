"""Replay verifier for serialized layout-conversion trace evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime.layout_conversion_evidence import (
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE,
    RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY,
    RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS,
    RUNTIME_LAYOUT_CONVERSION_STATUS,
)
from tuc.runtime.layout_conversion_trace_index import (
    RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_SCOPE,
    RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_STATUS,
    RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_layout_conversion_trace_replay_verifier_report.v0"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT = (
    "runtime_layout_conversion_trace_replay_verifier.review.v0"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS = "review_verification"
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPLAY_MODE = "metadata_digest_replay_only"
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_POLICY = "serialized_json_reports_only"
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY = (
    "runtime_reexecution_not_required"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECK_STATUS = "verified"
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS = (
    "runtime_layout_conversion_evidence",
    "runtime_layout_conversion_trace_index",
)
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_BYTES = 192 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_FIELD_BYTES = 512
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECKS = 8
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ISSUES = 64

_REPLAY_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_REPLAY_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"allocation_handle"',
    '"backend_artifact"',
    '"command_line"',
    '"device_id"',
    '"device_pointer"',
    '"dynamic_library"',
    '"environment"',
    '"executable"',
    '"file_path"',
    '"generated_code"',
    '"host_path"',
    '"input_value"',
    '"jit_function"',
    '"memory_address"',
    '"network"',
    '"output_value"',
    '"plugin_entrypoint"',
    '"python_module"',
    '"python_source"',
    '"raw_benchmark_output"',
    '"raw_output_value"',
    '"raw_tensor_value"',
    '"raw_timing_samples"',
    '"reference_value"',
    '"source_text"',
    '"tensor_value"',
    '"tensor_values"',
    '"url"',
    "tl.store",
)


@dataclass(frozen=True)
class RuntimeLayoutConversionTraceReplayVerifierCheck:
    """One replayed layout-conversion trace binding check."""

    check_id: str
    subject: str
    observed: str
    expected: str
    row_status: str = RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECK_STATUS

    def __post_init__(self) -> None:
        _validate_text(self.check_id, "layout trace replay check_id")
        _validate_text(self.subject, "layout trace replay subject")
        _validate_observed_value(self.observed, "layout trace replay observed")
        _validate_observed_value(self.expected, "layout trace replay expected")
        if self.row_status != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECK_STATUS:
            raise ValueError("layout trace replay row status mismatch")


@dataclass(frozen=True)
class RuntimeLayoutConversionTraceReplayVerifierIssue:
    """One derived layout-conversion trace replay issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "layout trace replay issue subject")
        _validate_text(self.issue_code, "layout trace replay issue_code")


@dataclass(frozen=True)
class RuntimeLayoutConversionTraceReplayVerifierReport:
    """Metadata-only replay verification over serialized layout-conversion reports."""

    graph_name: str
    layout_conversion_evidence_report_digest: str
    layout_conversion_trace_index_report_digest: str
    source_partition_plan_digest: str
    source_layout_conversion_evidence_digest: str
    conversion_metadata_digest: str
    trace_index_conversion_metadata_digest: str
    checks: tuple[RuntimeLayoutConversionTraceReplayVerifierCheck, ...]
    issues: tuple[RuntimeLayoutConversionTraceReplayVerifierIssue, ...]
    replay_contract: str = RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT
    artifact_status: str = RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS
    replay_mode: str = RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPLAY_MODE
    input_policy: str = RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_POLICY
    reexecution_policy: str = RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY
    trace_materialization_policy: str = (
        RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    execution_policy: str = RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    required_inputs: tuple[str, ...] = (
        RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "layout trace replay graph_name")
        if self.replay_contract != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT:
            raise ValueError("layout trace replay verifier contract mismatch")
        if self.artifact_status != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS:
            raise ValueError("layout trace replay verifier artifact status mismatch")
        if self.replay_mode != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPLAY_MODE:
            raise ValueError("layout trace replay verifier mode mismatch")
        if self.input_policy != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_POLICY:
            raise ValueError("layout trace replay verifier input policy mismatch")
        if (
            self.reexecution_policy
            != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY
        ):
            raise ValueError("layout trace replay verifier reexecution policy mismatch")
        if (
            self.trace_materialization_policy
            != RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
        ):
            raise ValueError("layout trace replay verifier materialization mismatch")
        if self.execution_policy != RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY:
            raise ValueError("layout trace replay verifier execution policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("layout trace replay verifier must omit raw values")
        if self.required_inputs != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS:
            raise ValueError("layout trace replay verifier required inputs changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("layout trace replay verifier blocked surfaces changed")
        for digest, label in (
            (
                self.layout_conversion_evidence_report_digest,
                "layout_conversion_evidence_report_digest",
            ),
            (
                self.layout_conversion_trace_index_report_digest,
                "layout_conversion_trace_index_report_digest",
            ),
            (self.source_partition_plan_digest, "source_partition_plan_digest"),
            (
                self.source_layout_conversion_evidence_digest,
                "source_layout_conversion_evidence_digest",
            ),
            (self.conversion_metadata_digest, "conversion_metadata_digest"),
            (
                self.trace_index_conversion_metadata_digest,
                "trace_index_conversion_metadata_digest",
            ),
        ):
            _validate_digest(digest, label)
        _validate_checks(self.checks)
        if type(self.issues) is not tuple:
            raise TypeError("layout trace replay verifier issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ISSUES:
            raise ValueError("layout trace replay verifier issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeLayoutConversionTraceReplayVerifierIssue):
                raise TypeError("layout trace replay verifier issues mismatch")
        if self.issues != _derive_issues(self.checks):
            raise ValueError("layout trace replay verifier issues must be derived")

    @property
    def check_count(self) -> int:
        """Return the number of replay checks."""

        return len(self.checks)

    @property
    def passed(self) -> bool:
        """Return whether all replay checks passed."""

        return not self.issues

    @property
    def replay_metadata_digest(self) -> str:
        """Return a digest over replay bindings and check results."""

        return _metadata_digest(
            {
                "checks": [
                    {
                        "check_id": check.check_id,
                        "expected": check.expected,
                        "observed": check.observed,
                        "row_status": check.row_status,
                        "subject": check.subject,
                    }
                    for check in self.checks
                ],
                "conversion_metadata_digest": self.conversion_metadata_digest,
                "graph_name": self.graph_name,
                "source_layout_conversion_evidence_digest": (
                    self.source_layout_conversion_evidence_digest
                ),
                "source_partition_plan_digest": self.source_partition_plan_digest,
                "trace_index_conversion_metadata_digest": (
                    self.trace_index_conversion_metadata_digest
                ),
            }
        )


class RuntimeLayoutConversionTraceReplayVerifierError(AssertionError):
    """Raised when serialized layout-conversion trace replay verification fails."""


def build_runtime_layout_conversion_trace_replay_verifier_report(
    layout_conversion_evidence_report_text: str,
    layout_conversion_trace_index_report_text: str,
) -> RuntimeLayoutConversionTraceReplayVerifierReport:
    """Build a replay verifier from serialized layout-conversion reports."""

    evidence = _load_json_report(
        layout_conversion_evidence_report_text,
        "runtime layout conversion evidence",
    )
    trace_index = _load_json_report(
        layout_conversion_trace_index_report_text,
        "runtime layout conversion trace index",
    )
    _validate_layout_conversion_evidence_shape(evidence)
    _validate_trace_index_shape(trace_index)

    graph_name = _expect_text(evidence, "graph_name")
    trace_index_graph_name = _expect_text(trace_index, "graph_name")
    if trace_index_graph_name != graph_name:
        trace_index_graph_name = "graph_name_mismatch"

    evidence_report_digest = _text_digest(layout_conversion_evidence_report_text)
    trace_index_evidence_digest = _expect_digest(
        trace_index,
        "source_layout_conversion_evidence_digest",
    )
    evidence_partition_digest = _expect_digest(
        evidence,
        "source_partition_plan_digest",
    )
    evidence_conversion_digest = _expect_digest(evidence, "conversion_metadata_digest")
    trace_index_conversion_digest = _trace_index_conversion_metadata_digest(trace_index)

    checks = (
        _check(
            "graph_name_match",
            "runtime_layout_conversion_trace_index",
            trace_index_graph_name,
            graph_name,
        ),
        _check(
            "layout_conversion_evidence_digest_replayed",
            "runtime_layout_conversion_evidence",
            evidence_report_digest,
            trace_index_evidence_digest,
        ),
        _check(
            "partition_plan_digest_bound",
            "runtime_layout_conversion_trace_index",
            _expect_digest(trace_index, "source_partition_plan_digest"),
            evidence_partition_digest,
        ),
        _check(
            "conversion_count_bound",
            "runtime_layout_conversion_trace_index",
            str(_expect_int(trace_index, "conversion_count")),
            str(_expect_int(evidence, "conversion_count")),
        ),
        _check(
            "conversion_metadata_digest_replayed",
            "runtime_layout_conversion_trace_index",
            trace_index_conversion_digest,
            evidence_conversion_digest,
        ),
        _check(
            "trace_materialization_policy_bound",
            "runtime_layout_conversion_trace_index",
            _expect_text(trace_index, "trace_materialization_policy"),
            RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
        ),
    )
    return RuntimeLayoutConversionTraceReplayVerifierReport(
        graph_name=graph_name,
        layout_conversion_evidence_report_digest=evidence_report_digest,
        layout_conversion_trace_index_report_digest=_text_digest(
            layout_conversion_trace_index_report_text
        ),
        source_partition_plan_digest=evidence_partition_digest,
        source_layout_conversion_evidence_digest=trace_index_evidence_digest,
        conversion_metadata_digest=evidence_conversion_digest,
        trace_index_conversion_metadata_digest=trace_index_conversion_digest,
        checks=checks,
        issues=_derive_issues(checks),
    )


def assert_runtime_layout_conversion_trace_replay_verifier(
    report: RuntimeLayoutConversionTraceReplayVerifierReport,
) -> RuntimeLayoutConversionTraceReplayVerifierReport:
    """Return the verifier report or raise when replay checks fail."""

    if not isinstance(report, RuntimeLayoutConversionTraceReplayVerifierReport):
        raise TypeError("layout trace replay verifier must be report object")
    if report.issues:
        lines = [f"layout conversion trace replay verifier failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeLayoutConversionTraceReplayVerifierError("\n".join(lines))
    return report


def runtime_layout_conversion_trace_replay_verifier_report_to_dict(
    report: RuntimeLayoutConversionTraceReplayVerifierReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible replay verifier evidence."""

    if not isinstance(report, RuntimeLayoutConversionTraceReplayVerifierReport):
        raise TypeError("layout trace replay verifier must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "check_count": report.check_count,
        "checks": [
            {
                "check_id": check.check_id,
                "expected": check.expected,
                "observed": check.observed,
                "row_status": check.row_status,
                "subject": check.subject,
            }
            for check in report.checks
        ],
        "conversion_metadata_digest": report.conversion_metadata_digest,
        "execution_policy": report.execution_policy,
        "graph_name": report.graph_name,
        "input_policy": report.input_policy,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject} for issue in report.issues
        ],
        "layout_conversion_evidence_report_digest": (
            report.layout_conversion_evidence_report_digest
        ),
        "layout_conversion_trace_index_report_digest": (
            report.layout_conversion_trace_index_report_digest
        ),
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "reexecution_policy": report.reexecution_policy,
        "replay_contract": report.replay_contract,
        "replay_metadata_digest": report.replay_metadata_digest,
        "replay_mode": report.replay_mode,
        "required_inputs": list(report.required_inputs),
        "schema_version": (RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION),
        "source_layout_conversion_evidence_digest": (
            report.source_layout_conversion_evidence_digest
        ),
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "trace_index_conversion_metadata_digest": (report.trace_index_conversion_metadata_digest),
        "trace_materialization_policy": report.trace_materialization_policy,
    }


def dump_runtime_layout_conversion_trace_replay_verifier_report(
    report: RuntimeLayoutConversionTraceReplayVerifierReport,
) -> str:
    """Render stable serialized layout-conversion trace replay verification."""

    text = json.dumps(
        runtime_layout_conversion_trace_replay_verifier_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_BYTES:
        raise ValueError("layout trace replay verifier report exceeds byte limit")
    return text + "\n"


def _load_json_report(text: str, label: str) -> dict[str, object]:
    if not isinstance(text, str):
        raise TypeError(f"{label} text must be string")
    if len(text.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_BYTES:
        raise ValueError(f"{label} text exceeds replay verifier byte limit")
    _assert_source_free_text(text, label)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} text must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} JSON must be object")
    return parsed


def _validate_layout_conversion_evidence_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(report, "evidence_contract", RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT)
    _expect_value(
        report,
        "artifact_status",
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS,
    )
    _expect_value(report, "conversion_scope", RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE)
    _expect_value(
        report,
        "execution_policy",
        RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY,
    )
    _expect_value(
        report,
        "residency_claim_status",
        RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS,
    )
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(
        report,
        "blocked_execution_surfaces",
        list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
    )
    conversions = _expect_list(report, "conversions")
    if report.get("conversion_count") != len(conversions):
        raise ValueError("layout conversion evidence conversion_count mismatch")
    if report.get("total_planned_bytes") != sum(
        _expect_record_int(record, "planned_bytes") for record in conversions
    ):
        raise ValueError("layout conversion evidence total_planned_bytes mismatch")


def _validate_trace_index_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_SCHEMA_VERSION,
    )
    _expect_value(
        report,
        "trace_index_contract",
        RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_CONTRACT,
    )
    _expect_value(report, "source_evidence_contract", RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT)
    _expect_value(
        report,
        "artifact_status",
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS,
    )
    _expect_value(report, "conversion_scope", RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE)
    _expect_value(report, "trace_index_scope", RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_SCOPE)
    _expect_value(
        report,
        "trace_materialization_policy",
        RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
    )
    _expect_value(
        report,
        "execution_policy",
        RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY,
    )
    _expect_value(
        report,
        "residency_claim_status",
        RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS,
    )
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(report, "executor_contract", RUNTIME_EXECUTOR_CONTRACT)
    _expect_value(report, "trusted_executor_registry", TRUSTED_RUNTIME_EXECUTOR_REGISTRY)
    _expect_value(report, "status", RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_STATUS)
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(
        report,
        "blocked_execution_surfaces",
        list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
    )
    records = _expect_list(report, "records")
    if report.get("conversion_count") != len(records):
        raise ValueError("layout conversion trace index conversion_count mismatch")
    if _expect_int(report, "trace_step_count") < 1:
        raise ValueError("layout conversion trace index trace_step_count mismatch")


def _trace_index_conversion_metadata_digest(report: dict[str, object]) -> str:
    records = _expect_list(report, "records")
    payload = []
    for record in records:
        record_mapping = _expect_mapping_value(record, "layout trace record")
        payload.append(
            {
                "consumer_input_id": (
                    f"{_expect_mapping_text(record_mapping, 'consumer_operation')}:"
                    f"{_expect_mapping_text(record_mapping, 'tensor_name')}"
                ),
                "conversion_id": record_mapping["conversion_id"],
                "conversion_status": RUNTIME_LAYOUT_CONVERSION_STATUS,
                "from_backend": record_mapping["producer_planned_backend"],
                "from_layout": record_mapping["from_layout"],
                "from_memory_domain": record_mapping["from_memory_domain"],
                "planned_bytes": record_mapping["planned_bytes"],
                "planner_reason": record_mapping["planner_reason"],
                "source_operation": record_mapping["producer_operation"],
                "source_value_record_id": (
                    f"{_expect_mapping_text(record_mapping, 'producer_operation')}:"
                    f"{_expect_mapping_text(record_mapping, 'tensor_name')}"
                ),
                "target_operation": record_mapping["consumer_operation"],
                "tensor_name": record_mapping["tensor_name"],
                "to_backend": record_mapping["consumer_planned_backend"],
                "to_layout": record_mapping["to_layout"],
                "to_memory_domain": record_mapping["to_memory_domain"],
            }
        )
    return _metadata_digest(payload)


def _derive_issues(
    checks: tuple[RuntimeLayoutConversionTraceReplayVerifierCheck, ...],
) -> tuple[RuntimeLayoutConversionTraceReplayVerifierIssue, ...]:
    issues: list[RuntimeLayoutConversionTraceReplayVerifierIssue] = []
    seen: set[str] = set()
    for check in checks:
        if check.check_id in seen:
            issues.append(
                RuntimeLayoutConversionTraceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code="duplicate_check_id",
                )
            )
        seen.add(check.check_id)
        if check.observed != check.expected:
            issues.append(
                RuntimeLayoutConversionTraceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code=f"{check.check_id}_mismatch",
                )
            )
        if check.row_status != RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECK_STATUS:
            issues.append(
                RuntimeLayoutConversionTraceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code=f"{check.check_id}_row_status_mismatch",
                )
            )
    return tuple(issues)


def _check(
    check_id: str,
    subject: str,
    observed: str,
    expected: str,
) -> RuntimeLayoutConversionTraceReplayVerifierCheck:
    return RuntimeLayoutConversionTraceReplayVerifierCheck(
        check_id=check_id,
        subject=subject,
        observed=observed,
        expected=expected,
    )


def _expect_list(report: dict[str, object], key: str) -> list[object]:
    value = report.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be list")
    return value


def _expect_mapping_value(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be object")
    return value


def _expect_text(report: dict[str, object], key: str) -> str:
    value = report.get(key)
    _validate_text(value, key)
    return cast(str, value)


def _expect_mapping_text(report: dict[str, object], key: str) -> str:
    value = report.get(key)
    _validate_text(value, key)
    return cast(str, value)


def _expect_digest(report: dict[str, object], key: str) -> str:
    value = report.get(key)
    _validate_digest(value, key)
    return cast(str, value)


def _expect_int(report: dict[str, object], key: str) -> int:
    value = report.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be integer")
    if value < 0:
        raise ValueError(f"{key} must be non-negative")
    return value


def _expect_record_int(record: object, key: str) -> int:
    record_mapping = _expect_mapping_value(record, "layout conversion record")
    return _expect_int(record_mapping, key)


def _expect_value(report: dict[str, object], key: str, expected: object) -> None:
    if report.get(key) != expected:
        raise ValueError(f"{key} mismatch")


def _validate_checks(
    checks: tuple[RuntimeLayoutConversionTraceReplayVerifierCheck, ...],
) -> None:
    if type(checks) is not tuple:
        raise TypeError("layout trace replay verifier checks must be tuple")
    if len(checks) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECKS:
        raise ValueError("layout trace replay verifier check count exceeds limit")
    for check in checks:
        if not isinstance(check, RuntimeLayoutConversionTraceReplayVerifierCheck):
            raise TypeError("layout trace replay verifier checks mismatch")


def _validate_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not _REPLAY_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be safe layout trace replay verifier text")
    if len(value.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_FIELD_BYTES:
        raise ValueError(f"{label} exceeds layout trace replay verifier field limit")


def _validate_observed_value(value: object, label: str) -> None:
    if isinstance(value, str) and _DIGEST_RE.fullmatch(value):
        return
    _validate_text(value, label)


def _validate_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _assert_source_free_text(text: str, label: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_REPLAY_FRAGMENTS:
        if fragment.lower() in lowered:
            raise ValueError(f"{label} contains forbidden layout trace replay verifier fragment")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _text_digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECKS",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_FIELD_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ISSUES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_BYTES",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CHECK_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_POLICY",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPLAY_MODE",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS",
    "RuntimeLayoutConversionTraceReplayVerifierCheck",
    "RuntimeLayoutConversionTraceReplayVerifierError",
    "RuntimeLayoutConversionTraceReplayVerifierIssue",
    "RuntimeLayoutConversionTraceReplayVerifierReport",
    "assert_runtime_layout_conversion_trace_replay_verifier",
    "build_runtime_layout_conversion_trace_replay_verifier_report",
    "dump_runtime_layout_conversion_trace_replay_verifier_report",
    "runtime_layout_conversion_trace_replay_verifier_report_to_dict",
]
