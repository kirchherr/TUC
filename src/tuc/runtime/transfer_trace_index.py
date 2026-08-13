"""Trace index evidence for planned runtime transfer edges."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeExecutionStep,
    RuntimeExecutionTrace,
    dump_execution_trace,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
from tuc.runtime.transfer_evidence import (
    RUNTIME_TRANSFER_COST_CLAIM_STATUS,
    RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_TRANSFER_EVIDENCE_CONTRACT,
    RUNTIME_TRANSFER_EVIDENCE_SCOPE,
    RUNTIME_TRANSFER_EXECUTION_POLICY,
    RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS,
    RUNTIME_TRANSFER_STATUS,
    RuntimeTransferEvidenceRecord,
    RuntimeTransferEvidenceReport,
    assert_runtime_transfer_evidence,
    dump_runtime_transfer_evidence_report,
)

RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_transfer_trace_index_report.v0"
)
RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT = "runtime_transfer_trace_index.data_only.v0"
RUNTIME_TRANSFER_TRACE_INDEX_SCOPE = "planned_transfer_trace_alignment_only"
RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY = (
    "transfer_not_materialized_as_runtime_step"
)
RUNTIME_TRANSFER_TRACE_INDEX_STATUS = "PASS"
RUNTIME_TRANSFER_TRACE_RECORD_STATUS = "planned_not_executed"
RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS = "producer_before_consumer"
MAX_RUNTIME_TRANSFER_TRACE_INDEX_RECORDS = 4096
MAX_RUNTIME_TRANSFER_TRACE_INDEX_ISSUES = 256
MAX_RUNTIME_TRANSFER_TRACE_INDEX_REPORT_BYTES = 96 * 1024
MAX_RUNTIME_TRANSFER_TRACE_INDEX_FIELD_BYTES = 512

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
class RuntimeTransferTraceIndexRecord:
    """One planned transfer aligned to producer and consumer trace steps."""

    transfer_id: str
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
    estimated_latency_ns: float
    estimated_energy_pj: float
    cost_model: str
    source_value_record_id: str
    consumer_input_id: str
    source_transfer_status: str = RUNTIME_TRANSFER_STATUS
    trace_record_status: str = RUNTIME_TRANSFER_TRACE_RECORD_STATUS
    trace_alignment_status: str = RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.transfer_id, "transfer_id"),
            (self.tensor_name, "tensor_name"),
            (self.producer_operation, "producer_operation"),
            (self.consumer_operation, "consumer_operation"),
            (self.producer_operation_kind, "producer_operation_kind"),
            (self.consumer_operation_kind, "consumer_operation_kind"),
            (self.producer_planned_backend, "producer_planned_backend"),
            (self.producer_executor_backend, "producer_executor_backend"),
            (self.consumer_planned_backend, "consumer_planned_backend"),
            (self.consumer_executor_backend, "consumer_executor_backend"),
            (self.cost_model, "cost_model"),
            (self.source_value_record_id, "source_value_record_id"),
            (self.consumer_input_id, "consumer_input_id"),
            (self.source_transfer_status, "source_transfer_status"),
            (self.trace_record_status, "trace_record_status"),
            (self.trace_alignment_status, "trace_alignment_status"),
        ):
            _validate_trace_index_text(value, label)
        _validate_name_sequence(self.producer_output_tensors, "producer_output_tensors")
        _validate_name_sequence(self.consumer_input_tensors, "consumer_input_tensors")
        _validate_step_index(self.producer_step_index, "producer_step_index")
        _validate_step_index(self.consumer_step_index, "consumer_step_index")
        if self.producer_step_index >= self.consumer_step_index:
            raise ValueError("runtime transfer producer step must precede consumer step")
        if not isinstance(self.from_memory_domain, MemoryDomainKind):
            raise TypeError("from_memory_domain must be MemoryDomainKind")
        if not isinstance(self.to_memory_domain, MemoryDomainKind):
            raise TypeError("to_memory_domain must be MemoryDomainKind")
        if self.from_memory_domain is self.to_memory_domain:
            raise ValueError("runtime transfer trace index requires different domains")
        if not isinstance(self.from_layout, LayoutKind):
            raise TypeError("from_layout must be LayoutKind")
        if not isinstance(self.to_layout, LayoutKind):
            raise TypeError("to_layout must be LayoutKind")
        _validate_positive_bytes(self.planned_bytes, "planned_bytes")
        _validate_non_negative_finite_float(
            self.estimated_latency_ns,
            "estimated_latency_ns",
        )
        _validate_non_negative_finite_float(
            self.estimated_energy_pj,
            "estimated_energy_pj",
        )
        if self.source_transfer_status != RUNTIME_TRANSFER_STATUS:
            raise ValueError("runtime transfer trace source status mismatch")
        if self.trace_record_status != RUNTIME_TRANSFER_TRACE_RECORD_STATUS:
            raise ValueError("runtime transfer trace record status mismatch")
        if self.trace_alignment_status != RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS:
            raise ValueError("runtime transfer trace alignment status mismatch")


@dataclass(frozen=True)
class RuntimeTransferTraceIndexIssue:
    """One derived transfer-trace-index issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_trace_index_text(self.subject, "issue subject")
        _validate_trace_index_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeTransferTraceIndexReport:
    """Deterministic, data-only index from planned transfers to trace steps."""

    graph_name: str
    source_partition_plan_digest: str
    source_transfer_evidence_digest: str
    execution_trace_digest: str
    trace_step_count: int
    records: tuple[RuntimeTransferTraceIndexRecord, ...]
    issues: tuple[RuntimeTransferTraceIndexIssue, ...]
    schema_version: str = RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION
    trace_index_contract: str = RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT
    artifact_status: str = RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS
    source_evidence_contract: str = RUNTIME_TRANSFER_EVIDENCE_CONTRACT
    transfer_scope: str = RUNTIME_TRANSFER_EVIDENCE_SCOPE
    trace_index_scope: str = RUNTIME_TRANSFER_TRACE_INDEX_SCOPE
    trace_materialization_policy: str = (
        RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    execution_policy: str = RUNTIME_TRANSFER_EXECUTION_POLICY
    residency_claim_status: str = RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS
    cost_claim_status: str = RUNTIME_TRANSFER_COST_CLAIM_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_TRANSFER_TRACE_INDEX_STATUS

    def __post_init__(self) -> None:
        _validate_trace_index_text(self.graph_name, "graph_name")
        _validate_digest(self.source_partition_plan_digest, "source_partition_plan_digest")
        _validate_digest(
            self.source_transfer_evidence_digest,
            "source_transfer_evidence_digest",
        )
        _validate_digest(self.execution_trace_digest, "execution_trace_digest")
        if self.schema_version != RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION:
            raise ValueError("runtime transfer trace index schema mismatch")
        if self.trace_index_contract != RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT:
            raise ValueError("runtime transfer trace index contract mismatch")
        if self.artifact_status != RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS:
            raise ValueError("runtime transfer trace index artifact mismatch")
        if self.source_evidence_contract != RUNTIME_TRANSFER_EVIDENCE_CONTRACT:
            raise ValueError("runtime transfer trace index source evidence mismatch")
        if self.transfer_scope != RUNTIME_TRANSFER_EVIDENCE_SCOPE:
            raise ValueError("runtime transfer trace index transfer scope mismatch")
        if self.trace_index_scope != RUNTIME_TRANSFER_TRACE_INDEX_SCOPE:
            raise ValueError("runtime transfer trace index scope mismatch")
        if (
            self.trace_materialization_policy
            != RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
        ):
            raise ValueError("runtime transfer trace materialization mismatch")
        if self.execution_policy != RUNTIME_TRANSFER_EXECUTION_POLICY:
            raise ValueError("runtime transfer trace execution policy mismatch")
        if self.residency_claim_status != RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS:
            raise ValueError("runtime transfer trace residency claim mismatch")
        if self.cost_claim_status != RUNTIME_TRANSFER_COST_CLAIM_STATUS:
            raise ValueError("runtime transfer trace cost claim mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime transfer trace index must omit values")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime transfer trace index executor contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("runtime transfer trace index executor registry mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime transfer trace index blocked surfaces changed")
        if self.status != RUNTIME_TRANSFER_TRACE_INDEX_STATUS:
            raise ValueError("runtime transfer trace index status mismatch")
        if self.trace_step_count <= 0:
            raise ValueError("trace_step_count must be positive")
        _validate_records(self.records)
        if type(self.issues) is not tuple:
            raise TypeError("runtime transfer trace issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_TRANSFER_TRACE_INDEX_ISSUES:
            raise ValueError("runtime transfer trace issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeTransferTraceIndexIssue):
                raise TypeError("runtime transfer trace issues must be issues")
        expected_issues = _derive_issues(self.records)
        if self.issues != expected_issues:
            raise ValueError("runtime transfer trace issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the trace index passed."""

        return not self.issues

    @property
    def transfer_count(self) -> int:
        """Return the indexed transfer count."""

        return len(self.records)

    @property
    def total_planned_bytes(self) -> int:
        """Return total planned bytes across indexed transfers."""

        return sum(record.planned_bytes for record in self.records)

    @property
    def total_estimated_latency_ns(self) -> float:
        """Return total deterministic transfer latency estimate."""

        return sum(record.estimated_latency_ns for record in self.records)

    @property
    def total_estimated_energy_pj(self) -> float:
        """Return total deterministic transfer energy estimate."""

        return sum(record.estimated_energy_pj for record in self.records)


class RuntimeTransferTraceIndexError(AssertionError):
    """Raised when runtime transfer trace-index evidence does not pass."""


def build_runtime_transfer_trace_index_report(
    evidence_report: RuntimeTransferEvidenceReport,
    execution_trace: RuntimeExecutionTrace,
) -> RuntimeTransferTraceIndexReport:
    """Build a data-only trace index for planned runtime transfer edges."""

    assert_runtime_transfer_evidence(evidence_report)
    if not isinstance(execution_trace, RuntimeExecutionTrace):
        raise TypeError("runtime transfer trace index requires execution trace")
    if execution_trace.graph_name != evidence_report.graph_name:
        raise ValueError("runtime transfer trace graph mismatch")
    step_positions = _step_positions_by_operation(execution_trace)
    records = tuple(
        _record_from_transfer(
            transfer=transfer,
            step_positions=step_positions,
        )
        for transfer in evidence_report.transfers
    )
    return RuntimeTransferTraceIndexReport(
        graph_name=evidence_report.graph_name,
        source_partition_plan_digest=evidence_report.source_partition_plan_digest,
        source_transfer_evidence_digest=_digest_text(
            dump_runtime_transfer_evidence_report(evidence_report)
        ),
        execution_trace_digest=_digest_text(dump_execution_trace(execution_trace)),
        trace_step_count=len(execution_trace.steps),
        records=records,
        issues=_derive_issues(records),
    )


def assert_runtime_transfer_trace_index(
    report: RuntimeTransferTraceIndexReport,
) -> RuntimeTransferTraceIndexReport:
    """Return the report or raise when trace-index evidence fails."""

    if not isinstance(report, RuntimeTransferTraceIndexReport):
        raise TypeError("runtime transfer trace index must be a report")
    if report.issues:
        lines = [f"runtime transfer trace index failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeTransferTraceIndexError("\n".join(lines))
    return report


def runtime_transfer_trace_index_report_to_dict(
    report: RuntimeTransferTraceIndexReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible transfer trace-index report."""

    if not isinstance(report, RuntimeTransferTraceIndexReport):
        raise TypeError("runtime transfer trace index must be a report")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "cost_claim_status": report.cost_claim_status,
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
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "source_transfer_evidence_digest": report.source_transfer_evidence_digest,
        "status": report.status,
        "total_estimated_energy_pj": report.total_estimated_energy_pj,
        "total_estimated_latency_ns": report.total_estimated_latency_ns,
        "total_planned_bytes": report.total_planned_bytes,
        "trace_index_contract": report.trace_index_contract,
        "trace_index_scope": report.trace_index_scope,
        "trace_materialization_policy": report.trace_materialization_policy,
        "trace_step_count": report.trace_step_count,
        "transfer_count": report.transfer_count,
        "transfer_scope": report.transfer_scope,
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_transfer_trace_index_report(
    report: RuntimeTransferTraceIndexReport,
) -> str:
    """Render stable data-only runtime transfer trace-index evidence."""

    text = json.dumps(
        runtime_transfer_trace_index_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_TRANSFER_TRACE_INDEX_REPORT_BYTES:
        raise ValueError("runtime transfer trace index report exceeds byte limit")
    return text + "\n"


def _record_from_transfer(
    *,
    transfer: RuntimeTransferEvidenceRecord,
    step_positions: dict[str, tuple[int, RuntimeExecutionStep]],
) -> RuntimeTransferTraceIndexRecord:
    if transfer.source_operation == "external_input":
        raise ValueError("runtime transfer trace index v0 requires operation producers")
    producer_index, producer_step = _required_step(
        step_positions,
        transfer.source_operation,
        "producer",
    )
    consumer_index, consumer_step = _required_step(
        step_positions,
        transfer.target_operation,
        "consumer",
    )
    if transfer.tensor_name not in producer_step.output_tensors:
        raise ValueError("runtime transfer trace producer output mismatch")
    if transfer.tensor_name not in consumer_step.input_tensors:
        raise ValueError("runtime transfer trace consumer input mismatch")
    if producer_step.planned_backend != transfer.from_backend:
        raise ValueError("runtime transfer trace producer backend mismatch")
    if consumer_step.planned_backend != transfer.to_backend:
        raise ValueError("runtime transfer trace consumer backend mismatch")
    return RuntimeTransferTraceIndexRecord(
        transfer_id=transfer.transfer_id,
        tensor_name=transfer.tensor_name,
        producer_operation=transfer.source_operation,
        consumer_operation=transfer.target_operation,
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
        from_memory_domain=transfer.from_memory_domain,
        to_memory_domain=transfer.to_memory_domain,
        from_layout=transfer.from_layout,
        to_layout=transfer.to_layout,
        planned_bytes=transfer.planned_bytes,
        estimated_latency_ns=transfer.estimated_latency_ns,
        estimated_energy_pj=transfer.estimated_energy_pj,
        cost_model=transfer.cost_model,
        source_value_record_id=transfer.source_value_record_id,
        consumer_input_id=transfer.consumer_input_id,
    )


def _record_to_dict(record: RuntimeTransferTraceIndexRecord) -> dict[str, object]:
    return {
        "consumer_executor_backend": record.consumer_executor_backend,
        "consumer_input_id": record.consumer_input_id,
        "consumer_input_tensors": list(record.consumer_input_tensors),
        "consumer_operation": record.consumer_operation,
        "consumer_operation_kind": record.consumer_operation_kind,
        "consumer_planned_backend": record.consumer_planned_backend,
        "consumer_step_index": record.consumer_step_index,
        "cost_model": record.cost_model,
        "estimated_energy_pj": record.estimated_energy_pj,
        "estimated_latency_ns": record.estimated_latency_ns,
        "from_layout": record.from_layout.value,
        "from_memory_domain": record.from_memory_domain.value,
        "planned_bytes": record.planned_bytes,
        "producer_executor_backend": record.producer_executor_backend,
        "producer_operation": record.producer_operation,
        "producer_operation_kind": record.producer_operation_kind,
        "producer_output_tensors": list(record.producer_output_tensors),
        "producer_planned_backend": record.producer_planned_backend,
        "producer_step_index": record.producer_step_index,
        "source_transfer_status": record.source_transfer_status,
        "source_value_record_id": record.source_value_record_id,
        "tensor_name": record.tensor_name,
        "to_layout": record.to_layout.value,
        "to_memory_domain": record.to_memory_domain.value,
        "trace_alignment_status": record.trace_alignment_status,
        "trace_record_status": record.trace_record_status,
        "transfer_id": record.transfer_id,
    }


def _step_positions_by_operation(
    trace: RuntimeExecutionTrace,
) -> dict[str, tuple[int, RuntimeExecutionStep]]:
    step_positions: dict[str, tuple[int, RuntimeExecutionStep]] = {}
    for index, step in enumerate(trace.steps):
        if step.operation_name in step_positions:
            raise ValueError("runtime transfer trace step names must be unique")
        step_positions[step.operation_name] = (index, step)
    return step_positions


def _required_step(
    step_positions: dict[str, tuple[int, RuntimeExecutionStep]],
    operation_name: str,
    role: str,
) -> tuple[int, RuntimeExecutionStep]:
    step = step_positions.get(operation_name)
    if step is None:
        raise ValueError(f"runtime transfer trace {role} operation missing")
    return step


def _derive_issues(
    records: tuple[RuntimeTransferTraceIndexRecord, ...],
) -> tuple[RuntimeTransferTraceIndexIssue, ...]:
    issues: list[RuntimeTransferTraceIndexIssue] = []
    seen: set[str] = set()
    for record in records:
        if record.transfer_id in seen:
            issues.append(
                RuntimeTransferTraceIndexIssue(
                    subject=record.transfer_id,
                    issue_code="duplicate_transfer_id",
                )
            )
        seen.add(record.transfer_id)
    return tuple(issues)


def _validate_records(
    records: tuple[RuntimeTransferTraceIndexRecord, ...],
) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime transfer trace records must be a tuple")
    if len(records) > MAX_RUNTIME_TRANSFER_TRACE_INDEX_RECORDS:
        raise ValueError("runtime transfer trace record count exceeds limit")
    for record in records:
        if not isinstance(record, RuntimeTransferTraceIndexRecord):
            raise TypeError("runtime transfer trace records must be records")


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


def _validate_positive_bytes(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _validate_non_negative_finite_float(value: float, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{label} must be a number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be a sha256 digest")


def _validate_trace_index_text(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if len(value.encode("utf-8")) > MAX_RUNTIME_TRANSFER_TRACE_INDEX_FIELD_BYTES:
        raise ValueError(f"{label} is too large")
    if not _TRACE_INDEX_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} contains unsupported characters")
    if value in _FORBIDDEN_TRACE_INDEX_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_TRANSFER_TRACE_INDEX_FIELD_BYTES",
    "MAX_RUNTIME_TRANSFER_TRACE_INDEX_ISSUES",
    "MAX_RUNTIME_TRANSFER_TRACE_INDEX_RECORDS",
    "MAX_RUNTIME_TRANSFER_TRACE_INDEX_REPORT_BYTES",
    "RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS",
    "RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT",
    "RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION",
    "RUNTIME_TRANSFER_TRACE_INDEX_SCOPE",
    "RUNTIME_TRANSFER_TRACE_INDEX_STATUS",
    "RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY",
    "RUNTIME_TRANSFER_TRACE_RECORD_STATUS",
    "RuntimeTransferTraceIndexError",
    "RuntimeTransferTraceIndexIssue",
    "RuntimeTransferTraceIndexRecord",
    "RuntimeTransferTraceIndexReport",
    "assert_runtime_transfer_trace_index",
    "build_runtime_transfer_trace_index_report",
    "dump_runtime_transfer_trace_index_report",
    "runtime_transfer_trace_index_report_to_dict",
]
