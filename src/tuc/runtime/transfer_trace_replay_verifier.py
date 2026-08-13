"""Replay verifier for serialized runtime-transfer trace evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import cast

from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
from tuc.runtime.transfer_evidence import (
    RUNTIME_TRANSFER_COST_CLAIM_STATUS,
    RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_TRANSFER_EVIDENCE_CONTRACT,
    RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_TRANSFER_EVIDENCE_SCOPE,
    RUNTIME_TRANSFER_EXECUTION_POLICY,
    RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS,
)
from tuc.runtime.transfer_trace_index import (
    RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT,
    RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION,
    RUNTIME_TRANSFER_TRACE_INDEX_SCOPE,
    RUNTIME_TRANSFER_TRACE_INDEX_STATUS,
    RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
)

RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_transfer_trace_replay_verifier_report.v0"
)
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT = (
    "runtime_transfer_trace_replay_verifier.review.v0"
)
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS = "review_verification"
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE = "metadata_digest_replay_only"
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY = "serialized_json_reports_only"
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY = (
    "runtime_reexecution_not_required"
)
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS = "verified"
RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS = (
    "runtime_transfer_evidence",
    "runtime_transfer_trace_index",
)
MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_BYTES = 192 * 1024
MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_FIELD_BYTES = 512
MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECKS = 6
MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ISSUES = 64

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
class RuntimeTransferTraceReplayVerifierCheck:
    """One replayed transfer trace binding check."""

    check_id: str
    subject: str
    observed: str
    expected: str
    row_status: str = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS

    def __post_init__(self) -> None:
        _validate_text(self.check_id, "transfer trace replay check_id")
        _validate_text(self.subject, "transfer trace replay subject")
        _validate_observed_value(self.observed, "transfer trace replay observed")
        _validate_observed_value(self.expected, "transfer trace replay expected")
        if self.row_status != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS:
            raise ValueError("transfer trace replay row status mismatch")


@dataclass(frozen=True)
class RuntimeTransferTraceReplayVerifierIssue:
    """One derived transfer trace replay issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "transfer trace replay issue subject")
        _validate_text(self.issue_code, "transfer trace replay issue_code")


@dataclass(frozen=True)
class RuntimeTransferTraceReplayVerifierReport:
    """Metadata-only replay verification over serialized transfer reports."""

    graph_name: str
    transfer_evidence_report_digest: str
    transfer_trace_index_report_digest: str
    source_partition_plan_digest: str
    source_transfer_evidence_digest: str
    transfer_metadata_digest: str
    trace_index_transfer_metadata_digest: str
    checks: tuple[RuntimeTransferTraceReplayVerifierCheck, ...]
    issues: tuple[RuntimeTransferTraceReplayVerifierIssue, ...]
    replay_contract: str = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT
    artifact_status: str = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS
    replay_mode: str = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE
    input_policy: str = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY
    reexecution_policy: str = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY
    trace_materialization_policy: str = (
        RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    execution_policy: str = RUNTIME_TRANSFER_EXECUTION_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    required_inputs: tuple[str, ...] = RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "transfer trace replay graph_name")
        if self.replay_contract != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT:
            raise ValueError("transfer trace replay verifier contract mismatch")
        if self.artifact_status != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS:
            raise ValueError("transfer trace replay verifier artifact status mismatch")
        if self.replay_mode != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE:
            raise ValueError("transfer trace replay verifier mode mismatch")
        if self.input_policy != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY:
            raise ValueError("transfer trace replay verifier input policy mismatch")
        if self.reexecution_policy != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY:
            raise ValueError("transfer trace replay verifier reexecution policy mismatch")
        if (
            self.trace_materialization_policy
            != RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
        ):
            raise ValueError("transfer trace replay verifier materialization mismatch")
        if self.execution_policy != RUNTIME_TRANSFER_EXECUTION_POLICY:
            raise ValueError("transfer trace replay verifier execution policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("transfer trace replay verifier must omit raw values")
        if self.required_inputs != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS:
            raise ValueError("transfer trace replay verifier required inputs changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("transfer trace replay verifier blocked surfaces changed")
        for digest, label in (
            (self.transfer_evidence_report_digest, "transfer_evidence_report_digest"),
            (self.transfer_trace_index_report_digest, "transfer_trace_index_report_digest"),
            (self.source_partition_plan_digest, "source_partition_plan_digest"),
            (self.source_transfer_evidence_digest, "source_transfer_evidence_digest"),
            (self.transfer_metadata_digest, "transfer_metadata_digest"),
            (
                self.trace_index_transfer_metadata_digest,
                "trace_index_transfer_metadata_digest",
            ),
        ):
            _validate_digest(digest, label)
        _validate_checks(self.checks)
        if type(self.issues) is not tuple:
            raise TypeError("transfer trace replay verifier issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ISSUES:
            raise ValueError("transfer trace replay verifier issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeTransferTraceReplayVerifierIssue):
                raise TypeError("transfer trace replay verifier issues mismatch")
        if self.issues != _derive_issues(self.checks):
            raise ValueError("transfer trace replay verifier issues must be derived")

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
                "graph_name": self.graph_name,
                "source_partition_plan_digest": self.source_partition_plan_digest,
                "source_transfer_evidence_digest": self.source_transfer_evidence_digest,
                "trace_index_transfer_metadata_digest": (
                    self.trace_index_transfer_metadata_digest
                ),
                "transfer_metadata_digest": self.transfer_metadata_digest,
            }
        )


class RuntimeTransferTraceReplayVerifierError(AssertionError):
    """Raised when serialized transfer trace replay verification fails."""


def build_runtime_transfer_trace_replay_verifier_report(
    transfer_evidence_report_text: str,
    transfer_trace_index_report_text: str,
) -> RuntimeTransferTraceReplayVerifierReport:
    """Build a replay verifier from serialized runtime-transfer reports."""

    evidence = _load_json_report(
        transfer_evidence_report_text,
        "runtime transfer evidence",
    )
    trace_index = _load_json_report(
        transfer_trace_index_report_text,
        "runtime transfer trace index",
    )
    _validate_transfer_evidence_shape(evidence)
    _validate_trace_index_shape(trace_index)

    graph_name = _expect_text(evidence, "graph_name")
    trace_index_graph_name = _expect_text(trace_index, "graph_name")
    if trace_index_graph_name != graph_name:
        trace_index_graph_name = "graph_name_mismatch"

    evidence_report_digest = _text_digest(transfer_evidence_report_text)
    trace_index_evidence_digest = _expect_digest(
        trace_index,
        "source_transfer_evidence_digest",
    )
    evidence_partition_digest = _expect_digest(
        evidence,
        "source_partition_plan_digest",
    )
    evidence_transfer_digest = _expect_digest(evidence, "transfer_metadata_digest")
    trace_index_transfer_digest = _trace_index_transfer_metadata_digest(trace_index)

    checks = (
        _check(
            "graph_name_match",
            "runtime_transfer_trace_index",
            trace_index_graph_name,
            graph_name,
        ),
        _check(
            "transfer_evidence_digest_replayed",
            "runtime_transfer_evidence",
            evidence_report_digest,
            trace_index_evidence_digest,
        ),
        _check(
            "partition_plan_digest_bound",
            "runtime_transfer_trace_index",
            _expect_digest(trace_index, "source_partition_plan_digest"),
            evidence_partition_digest,
        ),
        _check(
            "transfer_count_bound",
            "runtime_transfer_trace_index",
            str(_expect_int(trace_index, "transfer_count")),
            str(_expect_int(evidence, "transfer_count")),
        ),
        _check(
            "transfer_metadata_digest_replayed",
            "runtime_transfer_trace_index",
            trace_index_transfer_digest,
            evidence_transfer_digest,
        ),
        _check(
            "trace_materialization_policy_bound",
            "runtime_transfer_trace_index",
            _expect_text(trace_index, "trace_materialization_policy"),
            RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
        ),
    )
    return RuntimeTransferTraceReplayVerifierReport(
        graph_name=graph_name,
        transfer_evidence_report_digest=evidence_report_digest,
        transfer_trace_index_report_digest=_text_digest(transfer_trace_index_report_text),
        source_partition_plan_digest=evidence_partition_digest,
        source_transfer_evidence_digest=trace_index_evidence_digest,
        transfer_metadata_digest=evidence_transfer_digest,
        trace_index_transfer_metadata_digest=trace_index_transfer_digest,
        checks=checks,
        issues=_derive_issues(checks),
    )


def assert_runtime_transfer_trace_replay_verifier(
    report: RuntimeTransferTraceReplayVerifierReport,
) -> RuntimeTransferTraceReplayVerifierReport:
    """Return the verifier report or raise when replay checks fail."""

    if not isinstance(report, RuntimeTransferTraceReplayVerifierReport):
        raise TypeError("transfer trace replay verifier must be report object")
    if report.issues:
        lines = [f"transfer trace replay verifier failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeTransferTraceReplayVerifierError("\n".join(lines))
    return report


def runtime_transfer_trace_replay_verifier_report_to_dict(
    report: RuntimeTransferTraceReplayVerifierReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible replay verifier evidence."""

    if not isinstance(report, RuntimeTransferTraceReplayVerifierReport):
        raise TypeError("transfer trace replay verifier must be report object")
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
        "execution_policy": report.execution_policy,
        "graph_name": report.graph_name,
        "input_policy": report.input_policy,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject} for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "reexecution_policy": report.reexecution_policy,
        "replay_contract": report.replay_contract,
        "replay_metadata_digest": report.replay_metadata_digest,
        "replay_mode": report.replay_mode,
        "required_inputs": list(report.required_inputs),
        "schema_version": RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "source_transfer_evidence_digest": report.source_transfer_evidence_digest,
        "trace_index_transfer_metadata_digest": report.trace_index_transfer_metadata_digest,
        "trace_materialization_policy": report.trace_materialization_policy,
        "transfer_evidence_report_digest": report.transfer_evidence_report_digest,
        "transfer_metadata_digest": report.transfer_metadata_digest,
        "transfer_trace_index_report_digest": report.transfer_trace_index_report_digest,
    }


def dump_runtime_transfer_trace_replay_verifier_report(
    report: RuntimeTransferTraceReplayVerifierReport,
) -> str:
    """Render stable serialized transfer trace replay verification."""

    text = json.dumps(
        runtime_transfer_trace_replay_verifier_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_BYTES:
        raise ValueError("transfer trace replay verifier report exceeds byte limit")
    return text + "\n"


def _load_json_report(text: str, label: str) -> dict[str, object]:
    if not isinstance(text, str):
        raise TypeError(f"{label} text must be string")
    if len(text.encode("utf-8")) > MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_BYTES:
        raise ValueError(f"{label} text exceeds replay verifier byte limit")
    _assert_source_free_text(text, label)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} text must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} JSON must be object")
    return parsed


def _validate_transfer_evidence_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(report, "evidence_contract", RUNTIME_TRANSFER_EVIDENCE_CONTRACT)
    _expect_value(report, "artifact_status", RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS)
    _expect_value(report, "transfer_scope", RUNTIME_TRANSFER_EVIDENCE_SCOPE)
    _expect_value(report, "execution_policy", RUNTIME_TRANSFER_EXECUTION_POLICY)
    _expect_value(
        report,
        "residency_claim_status",
        RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS,
    )
    _expect_value(report, "cost_claim_status", RUNTIME_TRANSFER_COST_CLAIM_STATUS)
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(
        report,
        "blocked_execution_surfaces",
        list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
    )
    transfers = _expect_list(report, "transfers")
    if report.get("transfer_count") != len(transfers):
        raise ValueError("runtime transfer evidence transfer_count mismatch")
    if report.get("total_planned_bytes") != sum(
        _expect_record_int(record, "planned_bytes") for record in transfers
    ):
        raise ValueError("runtime transfer evidence total_planned_bytes mismatch")
    if _expect_digest(report, "transfer_metadata_digest") != _transfer_metadata_digest(
        transfers
    ):
        raise ValueError("runtime transfer evidence metadata digest mismatch")


def _validate_trace_index_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION,
    )
    _expect_value(report, "trace_index_contract", RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT)
    _expect_value(report, "source_evidence_contract", RUNTIME_TRANSFER_EVIDENCE_CONTRACT)
    _expect_value(report, "artifact_status", RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS)
    _expect_value(report, "transfer_scope", RUNTIME_TRANSFER_EVIDENCE_SCOPE)
    _expect_value(report, "trace_index_scope", RUNTIME_TRANSFER_TRACE_INDEX_SCOPE)
    _expect_value(
        report,
        "trace_materialization_policy",
        RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
    )
    _expect_value(report, "execution_policy", RUNTIME_TRANSFER_EXECUTION_POLICY)
    _expect_value(
        report,
        "residency_claim_status",
        RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS,
    )
    _expect_value(report, "cost_claim_status", RUNTIME_TRANSFER_COST_CLAIM_STATUS)
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(report, "executor_contract", RUNTIME_EXECUTOR_CONTRACT)
    _expect_value(report, "trusted_executor_registry", TRUSTED_RUNTIME_EXECUTOR_REGISTRY)
    _expect_value(report, "status", RUNTIME_TRANSFER_TRACE_INDEX_STATUS)
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(
        report,
        "blocked_execution_surfaces",
        list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
    )
    records = _expect_list(report, "records")
    if report.get("transfer_count") != len(records):
        raise ValueError("runtime transfer trace index transfer_count mismatch")
    if _expect_int(report, "trace_step_count") < 1:
        raise ValueError("runtime transfer trace index trace_step_count mismatch")
    if report.get("total_planned_bytes") != sum(
        _expect_record_int(record, "planned_bytes") for record in records
    ):
        raise ValueError("runtime transfer trace index total_planned_bytes mismatch")


def _trace_index_transfer_metadata_digest(report: dict[str, object]) -> str:
    records = _expect_list(report, "records")
    payload = []
    for record in records:
        record_mapping = _expect_mapping_value(record, "transfer trace record")
        payload.append(
            {
                "consumer_input_id": record_mapping["consumer_input_id"],
                "cost_model": record_mapping["cost_model"],
                "estimated_energy_pj": record_mapping["estimated_energy_pj"],
                "estimated_latency_ns": record_mapping["estimated_latency_ns"],
                "from_backend": record_mapping["producer_planned_backend"],
                "from_layout": record_mapping["from_layout"],
                "from_memory_domain": record_mapping["from_memory_domain"],
                "planned_bytes": record_mapping["planned_bytes"],
                "source_operation": record_mapping["producer_operation"],
                "source_value_record_id": record_mapping["source_value_record_id"],
                "target_operation": record_mapping["consumer_operation"],
                "tensor_name": record_mapping["tensor_name"],
                "to_backend": record_mapping["consumer_planned_backend"],
                "to_layout": record_mapping["to_layout"],
                "to_memory_domain": record_mapping["to_memory_domain"],
                "transfer_id": record_mapping["transfer_id"],
                "transfer_status": record_mapping["source_transfer_status"],
            }
        )
    return _metadata_digest(payload)


def _transfer_metadata_digest(records: list[object]) -> str:
    payload: list[dict[str, object]] = []
    for record in records:
        record_mapping = _expect_mapping_value(record, "transfer evidence record")
        payload.append(
            {
                "consumer_input_id": _expect_mapping_text(
                    record_mapping,
                    "consumer_input_id",
                ),
                "cost_model": _expect_mapping_text(record_mapping, "cost_model"),
                "estimated_energy_pj": _expect_mapping_number(
                    record_mapping,
                    "estimated_energy_pj",
                ),
                "estimated_latency_ns": _expect_mapping_number(
                    record_mapping,
                    "estimated_latency_ns",
                ),
                "from_backend": _expect_mapping_text(record_mapping, "from_backend"),
                "from_layout": _expect_mapping_text(record_mapping, "from_layout"),
                "from_memory_domain": _expect_mapping_text(
                    record_mapping,
                    "from_memory_domain",
                ),
                "planned_bytes": _expect_mapping_int(record_mapping, "planned_bytes"),
                "source_operation": _expect_mapping_text(
                    record_mapping,
                    "source_operation",
                ),
                "source_value_record_id": _expect_mapping_text(
                    record_mapping,
                    "source_value_record_id",
                ),
                "target_operation": _expect_mapping_text(
                    record_mapping,
                    "target_operation",
                ),
                "tensor_name": _expect_mapping_text(record_mapping, "tensor_name"),
                "to_backend": _expect_mapping_text(record_mapping, "to_backend"),
                "to_layout": _expect_mapping_text(record_mapping, "to_layout"),
                "to_memory_domain": _expect_mapping_text(
                    record_mapping,
                    "to_memory_domain",
                ),
                "transfer_id": _expect_mapping_text(record_mapping, "transfer_id"),
                "transfer_status": _expect_mapping_text(
                    record_mapping,
                    "transfer_status",
                ),
            }
        )
    return _metadata_digest(payload)


def _derive_issues(
    checks: tuple[RuntimeTransferTraceReplayVerifierCheck, ...],
) -> tuple[RuntimeTransferTraceReplayVerifierIssue, ...]:
    issues: list[RuntimeTransferTraceReplayVerifierIssue] = []
    seen: set[str] = set()
    for check in checks:
        if check.check_id in seen:
            issues.append(
                RuntimeTransferTraceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code="duplicate_check_id",
                )
            )
        seen.add(check.check_id)
        if check.observed != check.expected:
            issues.append(
                RuntimeTransferTraceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code=f"{check.check_id}_mismatch",
                )
            )
        if check.row_status != RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS:
            issues.append(
                RuntimeTransferTraceReplayVerifierIssue(
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
) -> RuntimeTransferTraceReplayVerifierCheck:
    return RuntimeTransferTraceReplayVerifierCheck(
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


def _expect_mapping_int(report: dict[str, object], key: str) -> int:
    value = report.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be non-negative integer")
    return value


def _expect_mapping_number(report: dict[str, object], key: str) -> int | float:
    value = report.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{key} must be number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{key} must be finite non-negative number")
    return value


def _expect_record_int(record: object, key: str) -> int:
    record_mapping = _expect_mapping_value(record, "transfer record")
    return _expect_mapping_int(record_mapping, key)


def _expect_value(report: dict[str, object], key: str, expected: object) -> None:
    if report.get(key) != expected:
        raise ValueError(f"{key} mismatch")


def _validate_checks(
    checks: tuple[RuntimeTransferTraceReplayVerifierCheck, ...],
) -> None:
    if type(checks) is not tuple:
        raise TypeError("transfer trace replay verifier checks must be tuple")
    if len(checks) > MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECKS:
        raise ValueError("transfer trace replay verifier check count exceeds limit")
    for check in checks:
        if not isinstance(check, RuntimeTransferTraceReplayVerifierCheck):
            raise TypeError("transfer trace replay verifier checks mismatch")


def _validate_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not _REPLAY_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be safe transfer trace replay verifier text")
    if len(value.encode("utf-8")) > MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_FIELD_BYTES:
        raise ValueError(f"{label} exceeds transfer trace replay verifier field limit")


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
            raise ValueError(f"{label} contains forbidden transfer trace replay fragment")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _text_digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECKS",
    "MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_FIELD_BYTES",
    "MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_BYTES",
    "MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ISSUES",
    "MAX_RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_BYTES",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION",
    "RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REQUIRED_INPUTS",
    "RuntimeTransferTraceReplayVerifierCheck",
    "RuntimeTransferTraceReplayVerifierError",
    "RuntimeTransferTraceReplayVerifierIssue",
    "RuntimeTransferTraceReplayVerifierReport",
    "assert_runtime_transfer_trace_replay_verifier",
    "build_runtime_transfer_trace_replay_verifier_report",
    "dump_runtime_transfer_trace_replay_verifier_report",
    "runtime_transfer_trace_replay_verifier_report_to_dict",
]
