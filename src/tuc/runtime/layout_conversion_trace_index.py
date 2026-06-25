"""Trace index evidence for planned runtime layout conversions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeExecutionStep,
    RuntimeExecutionTrace,
    dump_execution_trace,
)
from tuc.runtime.layout_conversion_evidence import (
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE,
    RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY,
    RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS,
    RuntimeLayoutConversionEvidenceReport,
    RuntimeLayoutConversionRecord,
    assert_runtime_layout_conversion_evidence,
    dump_runtime_layout_conversion_evidence_report,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_layout_conversion_trace_index_report.v0"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_CONTRACT = (
    "runtime_layout_conversion_trace_index.data_only.v0"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_SCOPE = (
    "planned_conversion_trace_alignment_only"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY = (
    "conversion_not_materialized_as_runtime_step"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_STATUS = "PASS"
RUNTIME_LAYOUT_CONVERSION_TRACE_RECORD_STATUS = "planned_not_executed"
RUNTIME_LAYOUT_CONVERSION_TRACE_ALIGNMENT_STATUS = "producer_before_consumer"
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_RECORDS = 4096
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_ISSUES = 256
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_BYTES = 96 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_FIELD_BYTES = 512

_TRACE_INDEX_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_TRACE_INDEX_TEXT = frozenset(
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
class RuntimeLayoutConversionTraceIndexRecord:
    """One planned layout conversion aligned to producer and consumer trace steps."""

    conversion_id: str
    tensor_name: str
    producer_operation: str
    consumer_operation: str
    producer_operation_kind: str
    consumer_operation_kind: str
    producer_step_index: int
    consumer_step_index: int
    producer_planned_backend: str
    producer_executor_backend: str
    consumer_planned_backend: str
    consumer_executor_backend: str
    producer_output_tensors: tuple[str, ...]
    consumer_input_tensors: tuple[str, ...]
    from_memory_domain: MemoryDomainKind
    to_memory_domain: MemoryDomainKind
    from_layout: LayoutKind
    to_layout: LayoutKind
    planned_bytes: int
    planner_reason: str
    conversion_status: str = RUNTIME_LAYOUT_CONVERSION_TRACE_RECORD_STATUS
    trace_alignment_status: str = RUNTIME_LAYOUT_CONVERSION_TRACE_ALIGNMENT_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.conversion_id, "conversion_id"),
            (self.tensor_name, "tensor_name"),
            (self.producer_operation, "producer_operation"),
            (self.consumer_operation, "consumer_operation"),
            (self.producer_operation_kind, "producer_operation_kind"),
            (self.consumer_operation_kind, "consumer_operation_kind"),
            (self.producer_planned_backend, "producer_planned_backend"),
            (self.producer_executor_backend, "producer_executor_backend"),
            (self.consumer_planned_backend, "consumer_planned_backend"),
            (self.consumer_executor_backend, "consumer_executor_backend"),
            (self.planner_reason, "planner_reason"),
            (self.conversion_status, "conversion_status"),
            (self.trace_alignment_status, "trace_alignment_status"),
        ):
            _validate_trace_index_text(value, label)
        _validate_name_sequence(self.producer_output_tensors, "producer_output_tensors")
        _validate_name_sequence(self.consumer_input_tensors, "consumer_input_tensors")
        _validate_step_index(self.producer_step_index, "producer_step_index")
        _validate_step_index(self.consumer_step_index, "consumer_step_index")
        if self.producer_step_index >= self.consumer_step_index:
            raise ValueError("layout conversion producer step must precede consumer step")
        if not isinstance(self.from_memory_domain, MemoryDomainKind):
            raise TypeError("from_memory_domain must be MemoryDomainKind")
        if not isinstance(self.to_memory_domain, MemoryDomainKind):
            raise TypeError("to_memory_domain must be MemoryDomainKind")
        if not isinstance(self.from_layout, LayoutKind):
            raise TypeError("from_layout must be LayoutKind")
        if not isinstance(self.to_layout, LayoutKind):
            raise TypeError("to_layout must be LayoutKind")
        if self.from_layout is self.to_layout:
            raise ValueError("layout conversion trace index requires different layouts")
        if self.planned_bytes <= 0:
            raise ValueError("planned_bytes must be positive")
        if self.conversion_status != RUNTIME_LAYOUT_CONVERSION_TRACE_RECORD_STATUS:
            raise ValueError("layout conversion trace record status mismatch")
        if self.trace_alignment_status != RUNTIME_LAYOUT_CONVERSION_TRACE_ALIGNMENT_STATUS:
            raise ValueError("layout conversion trace alignment status mismatch")


@dataclass(frozen=True)
class RuntimeLayoutConversionTraceIndexIssue:
    """One derived trace-index issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_trace_index_text(self.subject, "issue subject")
        _validate_trace_index_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeLayoutConversionTraceIndexReport:
    """Deterministic, data-only index from layout conversions to trace steps."""

    graph_name: str
    source_partition_plan_digest: str
    source_layout_conversion_evidence_digest: str
    execution_trace_digest: str
    trace_step_count: int
    records: tuple[RuntimeLayoutConversionTraceIndexRecord, ...]
    issues: tuple[RuntimeLayoutConversionTraceIndexIssue, ...]
    schema_version: str = RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_SCHEMA_VERSION
    trace_index_contract: str = RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_CONTRACT
    artifact_status: str = RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS
    source_evidence_contract: str = RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT
    conversion_scope: str = RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE
    trace_index_scope: str = RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_SCOPE
    trace_materialization_policy: str = (
        RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    execution_policy: str = RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY
    residency_claim_status: str = RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_STATUS

    def __post_init__(self) -> None:
        _validate_trace_index_text(self.graph_name, "graph_name")
        _validate_digest(self.source_partition_plan_digest, "source_partition_plan_digest")
        _validate_digest(
            self.source_layout_conversion_evidence_digest,
            "source_layout_conversion_evidence_digest",
        )
        _validate_digest(self.execution_trace_digest, "execution_trace_digest")
        if self.schema_version != RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_SCHEMA_VERSION:
            raise ValueError("runtime layout conversion trace index schema mismatch")
        if self.trace_index_contract != RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_CONTRACT:
            raise ValueError("runtime layout conversion trace index contract mismatch")
        if self.artifact_status != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS:
            raise ValueError("runtime layout conversion trace index artifact mismatch")
        if self.source_evidence_contract != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT:
            raise ValueError("runtime layout conversion source evidence mismatch")
        if self.conversion_scope != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE:
            raise ValueError("runtime layout conversion scope mismatch")
        if self.trace_index_scope != RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_SCOPE:
            raise ValueError("runtime layout conversion trace index scope mismatch")
        if (
            self.trace_materialization_policy
            != RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
        ):
            raise ValueError("runtime layout conversion trace materialization mismatch")
        if self.execution_policy != RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY:
            raise ValueError("runtime layout conversion execution policy mismatch")
        if (
            self.residency_claim_status
            != RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
        ):
            raise ValueError("runtime layout conversion residency claim mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime layout conversion trace index must omit values")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime layout conversion executor contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("runtime layout conversion executor registry mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime layout conversion blocked surfaces changed")
        if self.status != RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_STATUS:
            raise ValueError("runtime layout conversion trace index status mismatch")
        if self.trace_step_count <= 0:
            raise ValueError("trace_step_count must be positive")
        _validate_records(self.records)
        if type(self.issues) is not tuple:
            raise TypeError("runtime layout conversion trace issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_ISSUES:
            raise ValueError("runtime layout conversion trace issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeLayoutConversionTraceIndexIssue):
                raise TypeError("runtime layout conversion trace issues must be issues")
        expected_issues = _derive_issues(self.records)
        if self.issues != expected_issues:
            raise ValueError("runtime layout conversion trace issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the trace index passed."""

        return not self.issues

    @property
    def conversion_count(self) -> int:
        """Return the indexed conversion count."""

        return len(self.records)


class RuntimeLayoutConversionTraceIndexError(AssertionError):
    """Raised when runtime layout-conversion trace-index evidence does not pass."""


def build_runtime_layout_conversion_trace_index_report(
    evidence_report: RuntimeLayoutConversionEvidenceReport,
    execution_trace: RuntimeExecutionTrace,
) -> RuntimeLayoutConversionTraceIndexReport:
    """Build a data-only trace index for planned layout conversions."""

    assert_runtime_layout_conversion_evidence(evidence_report)
    if not isinstance(execution_trace, RuntimeExecutionTrace):
        raise TypeError("runtime layout conversion trace index requires execution trace")
    if execution_trace.graph_name != evidence_report.graph_name:
        raise ValueError("runtime layout conversion trace graph mismatch")
    step_positions = _step_positions_by_operation(execution_trace)
    records = tuple(
        _record_from_conversion(
            conversion=conversion,
            step_positions=step_positions,
        )
        for conversion in evidence_report.conversions
    )
    return RuntimeLayoutConversionTraceIndexReport(
        graph_name=evidence_report.graph_name,
        source_partition_plan_digest=evidence_report.source_partition_plan_digest,
        source_layout_conversion_evidence_digest=_digest_text(
            dump_runtime_layout_conversion_evidence_report(evidence_report)
        ),
        execution_trace_digest=_digest_text(dump_execution_trace(execution_trace)),
        trace_step_count=len(execution_trace.steps),
        records=records,
        issues=_derive_issues(records),
    )


def assert_runtime_layout_conversion_trace_index(
    report: RuntimeLayoutConversionTraceIndexReport,
) -> RuntimeLayoutConversionTraceIndexReport:
    """Return the report or raise when trace-index evidence fails."""

    if not isinstance(report, RuntimeLayoutConversionTraceIndexReport):
        raise TypeError("runtime layout conversion trace index must be a report")
    if report.issues:
        lines = [
            f"runtime layout conversion trace index failed for {report.graph_name!r}:"
        ]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeLayoutConversionTraceIndexError("\n".join(lines))
    return report


def runtime_layout_conversion_trace_index_report_to_dict(
    report: RuntimeLayoutConversionTraceIndexReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible trace-index report."""

    if not isinstance(report, RuntimeLayoutConversionTraceIndexReport):
        raise TypeError("runtime layout conversion trace index must be a report")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "conversion_count": report.conversion_count,
        "conversion_scope": report.conversion_scope,
        "execution_policy": report.execution_policy,
        "execution_trace_digest": report.execution_trace_digest,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "records": [_record_to_dict(record) for record in report.records],
        "residency_claim_status": report.residency_claim_status,
        "schema_version": report.schema_version,
        "source_evidence_contract": report.source_evidence_contract,
        "source_layout_conversion_evidence_digest": (
            report.source_layout_conversion_evidence_digest
        ),
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "status": report.status,
        "trace_index_contract": report.trace_index_contract,
        "trace_index_scope": report.trace_index_scope,
        "trace_materialization_policy": report.trace_materialization_policy,
        "trace_step_count": report.trace_step_count,
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_layout_conversion_trace_index_report(
    report: RuntimeLayoutConversionTraceIndexReport,
) -> str:
    """Render stable data-only runtime layout-conversion trace-index evidence."""

    text = json.dumps(
        runtime_layout_conversion_trace_index_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_BYTES:
        raise ValueError("runtime layout conversion trace index report exceeds byte limit")
    return text + "\n"


def _record_from_conversion(
    *,
    conversion: RuntimeLayoutConversionRecord,
    step_positions: dict[str, tuple[int, RuntimeExecutionStep]],
) -> RuntimeLayoutConversionTraceIndexRecord:
    if conversion.source_operation == "external_input":
        raise ValueError(
            "runtime layout conversion trace index v0 requires operation producers"
        )
    producer_index, producer_step = _required_step(
        step_positions,
        conversion.source_operation,
        "producer",
    )
    consumer_index, consumer_step = _required_step(
        step_positions,
        conversion.target_operation,
        "consumer",
    )
    if conversion.tensor_name not in producer_step.output_tensors:
        raise ValueError("layout conversion trace producer output mismatch")
    if conversion.tensor_name not in consumer_step.input_tensors:
        raise ValueError("layout conversion trace consumer input mismatch")
    if producer_step.planned_backend != conversion.from_backend:
        raise ValueError("layout conversion trace producer backend mismatch")
    if consumer_step.planned_backend != conversion.to_backend:
        raise ValueError("layout conversion trace consumer backend mismatch")
    return RuntimeLayoutConversionTraceIndexRecord(
        conversion_id=conversion.conversion_id,
        tensor_name=conversion.tensor_name,
        producer_operation=conversion.source_operation,
        consumer_operation=conversion.target_operation,
        producer_operation_kind=producer_step.operation_kind.value,
        consumer_operation_kind=consumer_step.operation_kind.value,
        producer_step_index=producer_index,
        consumer_step_index=consumer_index,
        producer_planned_backend=producer_step.planned_backend,
        producer_executor_backend=producer_step.executor_backend,
        consumer_planned_backend=consumer_step.planned_backend,
        consumer_executor_backend=consumer_step.executor_backend,
        producer_output_tensors=producer_step.output_tensors,
        consumer_input_tensors=consumer_step.input_tensors,
        from_memory_domain=conversion.from_memory_domain,
        to_memory_domain=conversion.to_memory_domain,
        from_layout=conversion.from_layout,
        to_layout=conversion.to_layout,
        planned_bytes=conversion.planned_bytes,
        planner_reason=conversion.planner_reason,
    )


def _record_to_dict(record: RuntimeLayoutConversionTraceIndexRecord) -> dict[str, object]:
    return {
        "consumer_executor_backend": record.consumer_executor_backend,
        "consumer_input_tensors": list(record.consumer_input_tensors),
        "consumer_operation": record.consumer_operation,
        "consumer_operation_kind": record.consumer_operation_kind,
        "consumer_planned_backend": record.consumer_planned_backend,
        "consumer_step_index": record.consumer_step_index,
        "conversion_id": record.conversion_id,
        "conversion_status": record.conversion_status,
        "from_layout": record.from_layout.value,
        "from_memory_domain": record.from_memory_domain.value,
        "planned_bytes": record.planned_bytes,
        "planner_reason": record.planner_reason,
        "producer_executor_backend": record.producer_executor_backend,
        "producer_operation": record.producer_operation,
        "producer_operation_kind": record.producer_operation_kind,
        "producer_output_tensors": list(record.producer_output_tensors),
        "producer_planned_backend": record.producer_planned_backend,
        "producer_step_index": record.producer_step_index,
        "tensor_name": record.tensor_name,
        "to_layout": record.to_layout.value,
        "to_memory_domain": record.to_memory_domain.value,
        "trace_alignment_status": record.trace_alignment_status,
    }


def _step_positions_by_operation(
    trace: RuntimeExecutionTrace,
) -> dict[str, tuple[int, RuntimeExecutionStep]]:
    step_positions: dict[str, tuple[int, RuntimeExecutionStep]] = {}
    for index, step in enumerate(trace.steps):
        if step.operation_name in step_positions:
            raise ValueError("runtime layout conversion trace step names must be unique")
        step_positions[step.operation_name] = (index, step)
    return step_positions


def _required_step(
    step_positions: dict[str, tuple[int, RuntimeExecutionStep]],
    operation_name: str,
    role: str,
) -> tuple[int, RuntimeExecutionStep]:
    step = step_positions.get(operation_name)
    if step is None:
        raise ValueError(f"layout conversion trace {role} operation missing")
    return step


def _derive_issues(
    records: tuple[RuntimeLayoutConversionTraceIndexRecord, ...],
) -> tuple[RuntimeLayoutConversionTraceIndexIssue, ...]:
    issues: list[RuntimeLayoutConversionTraceIndexIssue] = []
    seen: set[str] = set()
    for record in records:
        if record.conversion_id in seen:
            issues.append(
                RuntimeLayoutConversionTraceIndexIssue(
                    subject=record.conversion_id,
                    issue_code="duplicate_conversion_id",
                )
            )
        seen.add(record.conversion_id)
    return tuple(issues)


def _validate_records(
    records: tuple[RuntimeLayoutConversionTraceIndexRecord, ...],
) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime layout conversion trace records must be a tuple")
    if len(records) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_RECORDS:
        raise ValueError("runtime layout conversion trace record count exceeds limit")
    for record in records:
        if not isinstance(record, RuntimeLayoutConversionTraceIndexRecord):
            raise TypeError("runtime layout conversion trace records must be records")


def _validate_name_sequence(value: tuple[str, ...], label: str) -> None:
    if type(value) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    if not value:
        raise ValueError(f"{label} must not be empty")
    for item in value:
        _validate_trace_index_text(item, label)


def _validate_step_index(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer")
    if value < 0:
        raise ValueError(f"{label} must be non-negative")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be a sha256 digest")


def _validate_trace_index_text(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if len(value.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_FIELD_BYTES:
        raise ValueError(f"{label} is too large")
    if not _TRACE_INDEX_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} contains unsupported characters")
    if value in _FORBIDDEN_TRACE_INDEX_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_FIELD_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_ISSUES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_RECORDS",
    "MAX_RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_BYTES",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_ALIGNMENT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_CONTRACT",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_REPORT_SCHEMA_VERSION",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_SCOPE",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY",
    "RUNTIME_LAYOUT_CONVERSION_TRACE_RECORD_STATUS",
    "RuntimeLayoutConversionTraceIndexError",
    "RuntimeLayoutConversionTraceIndexIssue",
    "RuntimeLayoutConversionTraceIndexRecord",
    "RuntimeLayoutConversionTraceIndexReport",
    "assert_runtime_layout_conversion_trace_index",
    "build_runtime_layout_conversion_trace_index_report",
    "dump_runtime_layout_conversion_trace_index_report",
    "runtime_layout_conversion_trace_index_report_to_dict",
]
