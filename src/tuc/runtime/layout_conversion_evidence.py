"""Data-only evidence for planned runtime layout conversions."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import (
    MAX_TENSOR_DIMENSION,
    MAX_TENSOR_RANK,
    ComputeGraph,
    ComputeOperation,
    TensorRef,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.plan import LayoutConversionCost
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_layout_conversion_evidence_report.v0"
)
RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT = (
    "runtime_layout_conversion_evidence.data_only.v0"
)
RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS = "review_evidence"
RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE = "planned_logical_layout_only"
RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY = "does_not_execute_conversions"
RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS = (
    "not_physical_residency_evidence"
)
RUNTIME_LAYOUT_CONVERSION_STATUS = "planned"
MAX_RUNTIME_LAYOUT_CONVERSION_RECORDS = 4096
MAX_RUNTIME_LAYOUT_CONVERSION_ISSUES = 256
MAX_RUNTIME_LAYOUT_CONVERSION_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_FIELD_BYTES = 512

_LAYOUT_EVIDENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_LAYOUT_EVIDENCE_TEXT = frozenset(
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
class RuntimeLayoutConversionRecord:
    """One planned layout transition derived from an accepted PartitionPlan."""

    conversion_id: str
    tensor_name: str
    source_operation: str
    target_operation: str
    from_backend: str
    to_backend: str
    from_memory_domain: MemoryDomainKind
    to_memory_domain: MemoryDomainKind
    from_layout: LayoutKind
    to_layout: LayoutKind
    planned_bytes: int
    planner_reason: str
    source_value_record_id: str
    consumer_input_id: str
    conversion_status: str = RUNTIME_LAYOUT_CONVERSION_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.conversion_id, "conversion_id"),
            (self.tensor_name, "tensor_name"),
            (self.source_operation, "source_operation"),
            (self.target_operation, "target_operation"),
            (self.from_backend, "from_backend"),
            (self.to_backend, "to_backend"),
            (self.planner_reason, "planner_reason"),
            (self.source_value_record_id, "source_value_record_id"),
            (self.consumer_input_id, "consumer_input_id"),
        ):
            _validate_layout_evidence_text(value, label)
        if not isinstance(self.from_memory_domain, MemoryDomainKind):
            raise TypeError("from_memory_domain must be MemoryDomainKind")
        if not isinstance(self.to_memory_domain, MemoryDomainKind):
            raise TypeError("to_memory_domain must be MemoryDomainKind")
        if not isinstance(self.from_layout, LayoutKind):
            raise TypeError("from_layout must be LayoutKind")
        if not isinstance(self.to_layout, LayoutKind):
            raise TypeError("to_layout must be LayoutKind")
        if self.from_layout is self.to_layout:
            raise ValueError("layout conversion evidence requires different layouts")
        _validate_positive_bytes(self.planned_bytes, "planned_bytes")
        if self.conversion_status != RUNTIME_LAYOUT_CONVERSION_STATUS:
            raise ValueError("layout conversion status must be planned")


@dataclass(frozen=True)
class RuntimeLayoutConversionIssue:
    """One derived layout-conversion evidence issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_layout_evidence_text(self.subject, "issue subject")
        _validate_layout_evidence_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeLayoutConversionEvidenceReport:
    """Deterministic, data-only report for planned layout transitions."""

    graph_name: str
    source_partition_plan_digest: str
    conversions: tuple[RuntimeLayoutConversionRecord, ...]
    issues: tuple[RuntimeLayoutConversionIssue, ...]
    evidence_contract: str = RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT
    artifact_status: str = RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS
    conversion_scope: str = RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE
    execution_policy: str = RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY
    residency_claim_status: str = RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_layout_evidence_text(self.graph_name, "graph_name")
        _validate_digest(self.source_partition_plan_digest, "source_partition_plan_digest")
        if self.evidence_contract != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT:
            raise ValueError("runtime layout conversion evidence contract mismatch")
        if self.artifact_status != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS:
            raise ValueError("runtime layout conversion artifact status mismatch")
        if self.conversion_scope != RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE:
            raise ValueError("runtime layout conversion scope mismatch")
        if self.execution_policy != RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY:
            raise ValueError("runtime layout conversion execution policy mismatch")
        if (
            self.residency_claim_status
            != RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
        ):
            raise ValueError("runtime layout conversion residency claim mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime layout conversion evidence must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime layout conversion blocked surfaces changed")
        _validate_conversion_records(self.conversions)
        if type(self.issues) is not tuple:
            raise TypeError("runtime layout conversion issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_LAYOUT_CONVERSION_ISSUES:
            raise ValueError("runtime layout conversion issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeLayoutConversionIssue):
                raise TypeError("runtime layout conversion issues must be issue objects")
        expected_issues = _derive_issues(self.conversions)
        if self.issues != expected_issues:
            raise ValueError("runtime layout conversion issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the layout-conversion evidence passed."""

        return not self.issues

    @property
    def total_planned_bytes(self) -> int:
        """Return total planned bytes across conversion records."""

        return sum(record.planned_bytes for record in self.conversions)

    @property
    def conversion_metadata_digest(self) -> str:
        """Return a digest over conversion metadata only."""

        encoded = json.dumps(
            [_conversion_record_to_dict(record) for record in self.conversions],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeLayoutConversionEvidenceError(AssertionError):
    """Raised when runtime layout-conversion evidence does not pass."""


def build_runtime_layout_conversion_evidence_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
) -> RuntimeLayoutConversionEvidenceReport:
    """Build data-only evidence for planned layout conversions in a PartitionPlan."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime layout conversion evidence graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError(
            "runtime layout conversion evidence partition_plan must be PartitionPlan"
        )
    _validate_graph_plan(graph, partition_plan)
    assignments = {
        assignment.operation_name: assignment for assignment in partition_plan.assignments
    }
    operations = {operation.name: operation for operation in graph.operations}
    producer_by_tensor = _producer_by_tensor(graph)
    records = tuple(
        _conversion_to_record(
            index=index,
            conversion=conversion,
            operations=operations,
            assignments=assignments,
            producer_by_tensor=producer_by_tensor,
        )
        for index, conversion in enumerate(partition_plan.layout_conversions)
    )
    return RuntimeLayoutConversionEvidenceReport(
        graph_name=graph.name,
        source_partition_plan_digest=_partition_plan_digest(partition_plan),
        conversions=records,
        issues=_derive_issues(records),
    )


def assert_runtime_layout_conversion_evidence(
    report: RuntimeLayoutConversionEvidenceReport,
) -> RuntimeLayoutConversionEvidenceReport:
    """Return the report or raise when layout-conversion evidence fails."""

    if not isinstance(report, RuntimeLayoutConversionEvidenceReport):
        raise TypeError("runtime layout conversion evidence report must be report object")
    if report.issues:
        lines = [f"runtime layout conversion evidence failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeLayoutConversionEvidenceError("\n".join(lines))
    return report


def runtime_layout_conversion_evidence_report_to_dict(
    report: RuntimeLayoutConversionEvidenceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible layout-conversion evidence report."""

    if not isinstance(report, RuntimeLayoutConversionEvidenceReport):
        raise TypeError("runtime layout conversion evidence report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "conversion_count": len(report.conversions),
        "conversion_metadata_digest": report.conversion_metadata_digest,
        "conversion_scope": report.conversion_scope,
        "conversions": [
            _conversion_record_to_dict(record) for record in report.conversions
        ],
        "evidence_contract": report.evidence_contract,
        "execution_policy": report.execution_policy,
        "graph_name": report.graph_name,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "residency_claim_status": report.residency_claim_status,
        "schema_version": RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION,
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "total_planned_bytes": report.total_planned_bytes,
    }


def dump_runtime_layout_conversion_evidence_report(
    report: RuntimeLayoutConversionEvidenceReport,
) -> str:
    """Render stable data-only runtime layout-conversion evidence."""

    text = json.dumps(
        runtime_layout_conversion_evidence_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_REPORT_BYTES:
        raise ValueError("runtime layout conversion evidence report exceeds byte limit")
    return text + "\n"


def _conversion_to_record(
    *,
    index: int,
    conversion: LayoutConversionCost,
    operations: dict[str, ComputeOperation],
    assignments: dict[str, Assignment],
    producer_by_tensor: dict[str, str],
) -> RuntimeLayoutConversionRecord:
    if not isinstance(conversion, LayoutConversionCost):
        raise TypeError("partition plan layout conversions must be LayoutConversionCost")
    target_operation = operations.get(conversion.target_operation)
    if target_operation is None:
        raise ValueError("layout conversion target operation must exist in graph")
    target_tensor = _target_input_tensor(target_operation, conversion.tensor_name)
    expected_source_operation = producer_by_tensor.get(conversion.tensor_name)
    source_operation = conversion.source_operation or "external_input"
    if expected_source_operation is None:
        if conversion.source_operation is not None:
            raise ValueError("external input layout conversion must not name a source op")
        source_assignment = None
    else:
        if conversion.source_operation != expected_source_operation:
            raise ValueError("layout conversion source operation mismatch")
        source_assignment = assignments[expected_source_operation]
    target_assignment = assignments[conversion.target_operation]
    expected_source_layout = (
        LayoutKind.ROW_MAJOR
        if source_assignment is None
        else source_assignment.produced_layout
    )
    if conversion.source_layout != expected_source_layout:
        raise ValueError("layout conversion source layout mismatch")
    expected_target_layout = _operation_layout(target_operation)
    if conversion.target_layout != expected_target_layout:
        raise ValueError("layout conversion target layout mismatch")
    expected_bytes = _tensor_nbytes(target_tensor)
    if conversion.bytes_converted != expected_bytes:
        raise ValueError("layout conversion byte count mismatch")

    from_backend = "external_input" if source_assignment is None else source_assignment.backend_name
    from_memory_domain = (
        MemoryDomainKind.HOST_RAM
        if source_assignment is None
        else source_assignment.memory_domain
    )
    return RuntimeLayoutConversionRecord(
        conversion_id=f"layout_conversion_{index:04d}",
        tensor_name=conversion.tensor_name,
        source_operation=source_operation,
        target_operation=conversion.target_operation,
        from_backend=from_backend,
        to_backend=target_assignment.backend_name,
        from_memory_domain=from_memory_domain,
        to_memory_domain=target_assignment.memory_domain,
        from_layout=conversion.source_layout,
        to_layout=conversion.target_layout,
        planned_bytes=conversion.bytes_converted,
        planner_reason=conversion.reason,
        source_value_record_id=f"{source_operation}:{conversion.tensor_name}",
        consumer_input_id=f"{conversion.target_operation}:{conversion.tensor_name}",
    )


def _conversion_record_to_dict(record: RuntimeLayoutConversionRecord) -> dict[str, object]:
    return {
        "consumer_input_id": record.consumer_input_id,
        "conversion_id": record.conversion_id,
        "conversion_status": record.conversion_status,
        "from_backend": record.from_backend,
        "from_layout": record.from_layout.value,
        "from_memory_domain": record.from_memory_domain.value,
        "planned_bytes": record.planned_bytes,
        "planner_reason": record.planner_reason,
        "source_operation": record.source_operation,
        "source_value_record_id": record.source_value_record_id,
        "target_operation": record.target_operation,
        "tensor_name": record.tensor_name,
        "to_backend": record.to_backend,
        "to_layout": record.to_layout.value,
        "to_memory_domain": record.to_memory_domain.value,
    }


def _partition_plan_digest(partition_plan: PartitionPlan) -> str:
    payload = {
        "assignments": [
            {
                "backend_name": assignment.backend_name,
                "layout_conversion_bytes": assignment.layout_conversion_bytes,
                "memory_domain": assignment.memory_domain.value,
                "operation_name": assignment.operation_name,
                "produced_layout": assignment.produced_layout.value,
                "transfer_bytes": assignment.transfer_bytes,
            }
            for assignment in partition_plan.assignments
        ],
        "conversions": [
            {
                "bytes_converted": conversion.bytes_converted,
                "reason": conversion.reason,
                "source_layout": conversion.source_layout.value,
                "source_operation": conversion.source_operation,
                "target_layout": conversion.target_layout.value,
                "target_operation": conversion.target_operation,
                "tensor_name": conversion.tensor_name,
            }
            for conversion in partition_plan.layout_conversions
        ],
        "graph_name": partition_plan.graph_name,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


def _derive_issues(
    conversions: tuple[RuntimeLayoutConversionRecord, ...],
) -> tuple[RuntimeLayoutConversionIssue, ...]:
    issues: list[RuntimeLayoutConversionIssue] = []
    seen: set[str] = set()
    for record in conversions:
        if record.conversion_id in seen:
            issues.append(
                RuntimeLayoutConversionIssue(
                    subject=record.conversion_id,
                    issue_code="duplicate_conversion_id",
                )
            )
        seen.add(record.conversion_id)
    return tuple(issues)


def _validate_conversion_records(
    records: tuple[RuntimeLayoutConversionRecord, ...],
) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime layout conversion records must be a tuple")
    if len(records) > MAX_RUNTIME_LAYOUT_CONVERSION_RECORDS:
        raise ValueError("runtime layout conversion record count exceeds limit")
    for record in records:
        if not isinstance(record, RuntimeLayoutConversionRecord):
            raise TypeError("runtime layout conversion records must be record objects")


def _validate_graph_plan(graph: ComputeGraph, partition_plan: PartitionPlan) -> None:
    if graph.name != partition_plan.graph_name:
        raise ValueError("runtime layout conversion graph and plan names must match")
    operation_names = tuple(operation.name for operation in graph.operations)
    assignment_names = tuple(
        assignment.operation_name for assignment in partition_plan.assignments
    )
    if operation_names != assignment_names:
        raise ValueError("runtime layout conversion plan must match graph operations")


def _producer_by_tensor(graph: ComputeGraph) -> dict[str, str]:
    producers: dict[str, str] = {}
    for operation in graph.operations:
        for tensor in operation.outputs:
            if tensor.name in producers:
                raise ValueError("runtime layout conversion tensor producers must be unique")
            producers[tensor.name] = operation.name
    return producers


def _target_input_tensor(operation: ComputeOperation, tensor_name: str) -> TensorRef:
    for tensor in operation.inputs:
        if tensor.name == tensor_name:
            return tensor
    raise ValueError("layout conversion tensor must be target operation input")


def _operation_layout(operation: ComputeOperation) -> LayoutKind:
    value = operation.attributes.get("tuc.layout")
    if value is None:
        return LayoutKind.ROW_MAJOR
    if isinstance(value, LayoutKind):
        return value
    if isinstance(value, str):
        try:
            return LayoutKind(value)
        except ValueError as exc:
            raise ValueError(f"unsupported operation layout: {value!r}") from exc
    raise TypeError("operation layout must be a LayoutKind or string")


def _tensor_nbytes(tensor: TensorRef) -> int:
    _validate_shape(tensor.shape, "tensor shape")
    return dtype_size_bytes(tensor.dtype) * _shape_product(tensor.shape)


def _shape_product(shape: tuple[int, ...]) -> int:
    total = 1
    for dimension in shape:
        total *= dimension
    return total


def _validate_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"{label} must be a non-empty tuple")
    if len(value) > MAX_TENSOR_RANK:
        raise ValueError(f"{label} exceeds tensor rank limit")
    for dimension in value:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_TENSOR_DIMENSION
        ):
            raise ValueError(f"{label} must contain bounded positive integers")


def _validate_positive_bytes(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _validate_layout_evidence_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _LAYOUT_EVIDENCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime layout evidence identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_LAYOUT_CONVERSION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime layout evidence field limit")
    if value in _FORBIDDEN_LAYOUT_EVIDENCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution, value, or handle surface")


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERSION_FIELD_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_ISSUES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_RECORDS",
    "MAX_RUNTIME_LAYOUT_CONVERSION_REPORT_BYTES",
    "RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT",
    "RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION",
    "RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE",
    "RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY",
    "RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_STATUS",
    "RuntimeLayoutConversionEvidenceError",
    "RuntimeLayoutConversionEvidenceReport",
    "RuntimeLayoutConversionIssue",
    "RuntimeLayoutConversionRecord",
    "assert_runtime_layout_conversion_evidence",
    "build_runtime_layout_conversion_evidence_report",
    "dump_runtime_layout_conversion_evidence_report",
    "runtime_layout_conversion_evidence_report_to_dict",
]
