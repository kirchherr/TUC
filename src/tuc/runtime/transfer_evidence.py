"""Data-only evidence for planned runtime transfer edges."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite

from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import (
    MAX_TENSOR_DIMENSION,
    MAX_TENSOR_RANK,
    ComputeGraph,
    ComputeOperation,
    TensorRef,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.partitioning import PartitionPlan
from tuc.runtime.plan import RuntimeTransferEdge
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION = "tuc.runtime_transfer_evidence_report.v0"
RUNTIME_TRANSFER_EVIDENCE_CONTRACT = "runtime_transfer_evidence.data_only.v0"
RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS = "review_evidence"
RUNTIME_TRANSFER_EVIDENCE_SCOPE = "planned_logical_transfer_only"
RUNTIME_TRANSFER_EXECUTION_POLICY = "does_not_execute_transfers"
RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS = "not_physical_residency_evidence"
RUNTIME_TRANSFER_COST_CLAIM_STATUS = "planning_estimate_not_measurement"
RUNTIME_TRANSFER_STATUS = "planned"
MAX_RUNTIME_TRANSFER_EVIDENCE_RECORDS = 4096
MAX_RUNTIME_TRANSFER_EVIDENCE_ISSUES = 256
MAX_RUNTIME_TRANSFER_EVIDENCE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_TRANSFER_EVIDENCE_FIELD_BYTES = 512

_TRANSFER_EVIDENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_TRANSFER_EVIDENCE_TEXT = frozenset(
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
class RuntimeTransferEvidenceRecord:
    """One planned transfer derived from an accepted PartitionPlan."""

    transfer_id: str
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
    estimated_latency_ns: float
    estimated_energy_pj: float
    cost_model: str
    source_value_record_id: str
    consumer_input_id: str
    transfer_status: str = RUNTIME_TRANSFER_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.transfer_id, "transfer_id"),
            (self.tensor_name, "tensor_name"),
            (self.source_operation, "source_operation"),
            (self.target_operation, "target_operation"),
            (self.from_backend, "from_backend"),
            (self.to_backend, "to_backend"),
            (self.cost_model, "cost_model"),
            (self.source_value_record_id, "source_value_record_id"),
            (self.consumer_input_id, "consumer_input_id"),
            (self.transfer_status, "transfer_status"),
        ):
            _validate_transfer_evidence_text(value, label)
        if not isinstance(self.from_memory_domain, MemoryDomainKind):
            raise TypeError("from_memory_domain must be MemoryDomainKind")
        if not isinstance(self.to_memory_domain, MemoryDomainKind):
            raise TypeError("to_memory_domain must be MemoryDomainKind")
        if self.from_memory_domain is self.to_memory_domain:
            raise ValueError("runtime transfer evidence requires different memory domains")
        if not isinstance(self.from_layout, LayoutKind):
            raise TypeError("from_layout must be LayoutKind")
        if not isinstance(self.to_layout, LayoutKind):
            raise TypeError("to_layout must be LayoutKind")
        _validate_positive_bytes(self.planned_bytes, "planned_bytes")
        _validate_non_negative_finite_float(
            self.estimated_latency_ns,
            "estimated_latency_ns",
        )
        _validate_non_negative_finite_float(self.estimated_energy_pj, "estimated_energy_pj")
        if self.transfer_status != RUNTIME_TRANSFER_STATUS:
            raise ValueError("runtime transfer status must be planned")


@dataclass(frozen=True)
class RuntimeTransferEvidenceIssue:
    """One derived transfer-evidence issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_transfer_evidence_text(self.subject, "issue subject")
        _validate_transfer_evidence_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeTransferEvidenceReport:
    """Deterministic, data-only report for planned runtime transfers."""

    graph_name: str
    source_partition_plan_digest: str
    transfers: tuple[RuntimeTransferEvidenceRecord, ...]
    issues: tuple[RuntimeTransferEvidenceIssue, ...]
    evidence_contract: str = RUNTIME_TRANSFER_EVIDENCE_CONTRACT
    artifact_status: str = RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS
    transfer_scope: str = RUNTIME_TRANSFER_EVIDENCE_SCOPE
    execution_policy: str = RUNTIME_TRANSFER_EXECUTION_POLICY
    residency_claim_status: str = RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS
    cost_claim_status: str = RUNTIME_TRANSFER_COST_CLAIM_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        _validate_transfer_evidence_text(self.graph_name, "graph_name")
        _validate_digest(self.source_partition_plan_digest, "source_partition_plan_digest")
        if self.evidence_contract != RUNTIME_TRANSFER_EVIDENCE_CONTRACT:
            raise ValueError("runtime transfer evidence contract mismatch")
        if self.artifact_status != RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS:
            raise ValueError("runtime transfer artifact status mismatch")
        if self.transfer_scope != RUNTIME_TRANSFER_EVIDENCE_SCOPE:
            raise ValueError("runtime transfer scope mismatch")
        if self.execution_policy != RUNTIME_TRANSFER_EXECUTION_POLICY:
            raise ValueError("runtime transfer execution policy mismatch")
        if self.residency_claim_status != RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS:
            raise ValueError("runtime transfer residency claim mismatch")
        if self.cost_claim_status != RUNTIME_TRANSFER_COST_CLAIM_STATUS:
            raise ValueError("runtime transfer cost claim mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime transfer evidence must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime transfer blocked surfaces changed")
        _validate_transfer_records(self.transfers)
        if type(self.issues) is not tuple:
            raise TypeError("runtime transfer issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_TRANSFER_EVIDENCE_ISSUES:
            raise ValueError("runtime transfer issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeTransferEvidenceIssue):
                raise TypeError("runtime transfer issues must be issue objects")
        expected_issues = _derive_issues(self.transfers)
        if self.issues != expected_issues:
            raise ValueError("runtime transfer issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the transfer evidence passed."""

        return not self.issues

    @property
    def total_planned_bytes(self) -> int:
        """Return total planned bytes across transfer records."""

        return sum(record.planned_bytes for record in self.transfers)

    @property
    def total_estimated_latency_ns(self) -> float:
        """Return total deterministic transfer latency estimate."""

        return sum(record.estimated_latency_ns for record in self.transfers)

    @property
    def total_estimated_energy_pj(self) -> float:
        """Return total deterministic transfer energy estimate."""

        return sum(record.estimated_energy_pj for record in self.transfers)

    @property
    def transfer_metadata_digest(self) -> str:
        """Return a digest over transfer metadata only."""

        encoded = json.dumps(
            [_transfer_record_to_dict(record) for record in self.transfers],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeTransferEvidenceError(AssertionError):
    """Raised when runtime transfer evidence does not pass."""


def build_runtime_transfer_evidence_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
) -> RuntimeTransferEvidenceReport:
    """Build data-only evidence for planned transfer edges in a PartitionPlan."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime transfer evidence graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("runtime transfer evidence partition_plan must be PartitionPlan")
    _validate_graph_plan(graph, partition_plan)
    operations = {operation.name: operation for operation in graph.operations}
    producer_by_tensor = _producer_by_tensor(graph)
    records = tuple(
        _transfer_to_record(
            index=index,
            transfer=transfer,
            operations=operations,
            producer_by_tensor=producer_by_tensor,
        )
        for index, transfer in enumerate(partition_plan.transfer_edges)
    )
    return RuntimeTransferEvidenceReport(
        graph_name=graph.name,
        source_partition_plan_digest=_partition_plan_digest(partition_plan),
        transfers=records,
        issues=_derive_issues(records),
    )


def assert_runtime_transfer_evidence(
    report: RuntimeTransferEvidenceReport,
) -> RuntimeTransferEvidenceReport:
    """Return the report or raise when runtime transfer evidence fails."""

    if not isinstance(report, RuntimeTransferEvidenceReport):
        raise TypeError("runtime transfer evidence report must be report object")
    if report.issues:
        lines = [f"runtime transfer evidence failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeTransferEvidenceError("\n".join(lines))
    return report


def runtime_transfer_evidence_report_to_dict(
    report: RuntimeTransferEvidenceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible transfer evidence report."""

    if not isinstance(report, RuntimeTransferEvidenceReport):
        raise TypeError("runtime transfer evidence report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "cost_claim_status": report.cost_claim_status,
        "evidence_contract": report.evidence_contract,
        "execution_policy": report.execution_policy,
        "graph_name": report.graph_name,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject} for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "residency_claim_status": report.residency_claim_status,
        "schema_version": RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION,
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "total_estimated_energy_pj": report.total_estimated_energy_pj,
        "total_estimated_latency_ns": report.total_estimated_latency_ns,
        "total_planned_bytes": report.total_planned_bytes,
        "transfer_count": len(report.transfers),
        "transfer_metadata_digest": report.transfer_metadata_digest,
        "transfer_scope": report.transfer_scope,
        "transfers": [_transfer_record_to_dict(record) for record in report.transfers],
    }


def dump_runtime_transfer_evidence_report(report: RuntimeTransferEvidenceReport) -> str:
    """Render stable data-only runtime transfer evidence."""

    text = json.dumps(
        runtime_transfer_evidence_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_TRANSFER_EVIDENCE_REPORT_BYTES:
        raise ValueError("runtime transfer evidence report exceeds byte limit")
    return text + "\n"


def _transfer_to_record(
    *,
    index: int,
    transfer: RuntimeTransferEdge,
    operations: dict[str, ComputeOperation],
    producer_by_tensor: dict[str, str],
) -> RuntimeTransferEvidenceRecord:
    if not isinstance(transfer, RuntimeTransferEdge):
        raise TypeError("partition plan transfer edges must be RuntimeTransferEdge")
    target_operation = operations.get(transfer.target_operation)
    if target_operation is None:
        raise ValueError("runtime transfer target operation must exist in graph")
    expected_source_operation = producer_by_tensor.get(transfer.tensor_name)
    if expected_source_operation is None:
        raise ValueError("runtime transfer source tensor must be produced in graph")
    if transfer.source_operation != expected_source_operation:
        raise ValueError("runtime transfer source operation mismatch")
    target_tensor = _target_input_tensor(target_operation, transfer.tensor_name)
    expected_bytes = _tensor_nbytes(target_tensor)
    if transfer.bytes_moved != expected_bytes:
        raise ValueError("runtime transfer byte count mismatch")
    cost_estimate = transfer.cost_estimate
    if cost_estimate is None:
        raise ValueError("runtime transfer evidence requires cost estimate")
    if cost_estimate.bytes_moved != transfer.bytes_moved:
        raise ValueError("runtime transfer cost byte count mismatch")

    return RuntimeTransferEvidenceRecord(
        transfer_id=f"runtime_transfer_{index:04d}",
        tensor_name=transfer.tensor_name,
        source_operation=transfer.source_operation,
        target_operation=transfer.target_operation,
        from_backend=transfer.source_backend,
        to_backend=transfer.target_backend,
        from_memory_domain=transfer.source_domain,
        to_memory_domain=transfer.target_domain,
        from_layout=transfer.source_layout,
        to_layout=transfer.target_layout,
        planned_bytes=transfer.bytes_moved,
        estimated_latency_ns=cost_estimate.estimated_latency_ns,
        estimated_energy_pj=cost_estimate.estimated_energy_pj,
        cost_model="prototype_transfer_cost_profile",
        source_value_record_id=f"{transfer.source_operation}:{transfer.tensor_name}",
        consumer_input_id=f"{transfer.target_operation}:{transfer.tensor_name}",
    )


def _transfer_record_to_dict(record: RuntimeTransferEvidenceRecord) -> dict[str, object]:
    return {
        "consumer_input_id": record.consumer_input_id,
        "cost_model": record.cost_model,
        "estimated_energy_pj": record.estimated_energy_pj,
        "estimated_latency_ns": record.estimated_latency_ns,
        "from_backend": record.from_backend,
        "from_layout": record.from_layout.value,
        "from_memory_domain": record.from_memory_domain.value,
        "planned_bytes": record.planned_bytes,
        "source_operation": record.source_operation,
        "source_value_record_id": record.source_value_record_id,
        "target_operation": record.target_operation,
        "tensor_name": record.tensor_name,
        "to_backend": record.to_backend,
        "to_layout": record.to_layout.value,
        "to_memory_domain": record.to_memory_domain.value,
        "transfer_id": record.transfer_id,
        "transfer_status": record.transfer_status,
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
        "graph_name": partition_plan.graph_name,
        "transfers": [
            {
                "bytes_moved": transfer.bytes_moved,
                "source_backend": transfer.source_backend,
                "source_domain": transfer.source_domain.value,
                "source_layout": transfer.source_layout.value,
                "source_operation": transfer.source_operation,
                "target_backend": transfer.target_backend,
                "target_domain": transfer.target_domain.value,
                "target_layout": transfer.target_layout.value,
                "target_operation": transfer.target_operation,
                "tensor_name": transfer.tensor_name,
            }
            for transfer in partition_plan.transfer_edges
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _derive_issues(
    transfers: tuple[RuntimeTransferEvidenceRecord, ...],
) -> tuple[RuntimeTransferEvidenceIssue, ...]:
    issues: list[RuntimeTransferEvidenceIssue] = []
    seen: set[str] = set()
    for record in transfers:
        if record.transfer_id in seen:
            issues.append(
                RuntimeTransferEvidenceIssue(
                    subject=record.transfer_id,
                    issue_code="duplicate_transfer_id",
                )
            )
        seen.add(record.transfer_id)
    return tuple(issues)


def _validate_transfer_records(
    records: tuple[RuntimeTransferEvidenceRecord, ...],
) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime transfer records must be a tuple")
    if len(records) > MAX_RUNTIME_TRANSFER_EVIDENCE_RECORDS:
        raise ValueError("runtime transfer record count exceeds limit")
    for record in records:
        if not isinstance(record, RuntimeTransferEvidenceRecord):
            raise TypeError("runtime transfer records must be record objects")


def _validate_graph_plan(graph: ComputeGraph, partition_plan: PartitionPlan) -> None:
    if graph.name != partition_plan.graph_name:
        raise ValueError("runtime transfer graph and plan names must match")
    operation_names = tuple(operation.name for operation in graph.operations)
    assignment_names = tuple(assignment.operation_name for assignment in partition_plan.assignments)
    if operation_names != assignment_names:
        raise ValueError("runtime transfer plan must match graph operations")


def _producer_by_tensor(graph: ComputeGraph) -> dict[str, str]:
    producers: dict[str, str] = {}
    for operation in graph.operations:
        for tensor in operation.outputs:
            if tensor.name in producers:
                raise ValueError("runtime transfer tensor producers must be unique")
            producers[tensor.name] = operation.name
    return producers


def _target_input_tensor(operation: ComputeOperation, tensor_name: str) -> TensorRef:
    for tensor in operation.inputs:
        if tensor.name == tensor_name:
            return tensor
    raise ValueError("runtime transfer tensor must be target operation input")


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


def _validate_non_negative_finite_float(value: float, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{label} must be a number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _validate_transfer_evidence_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _TRANSFER_EVIDENCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime transfer evidence identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_TRANSFER_EVIDENCE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime transfer evidence field limit")
    if value in _FORBIDDEN_TRANSFER_EVIDENCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution, value, or handle surface")


__all__ = [
    "MAX_RUNTIME_TRANSFER_EVIDENCE_FIELD_BYTES",
    "MAX_RUNTIME_TRANSFER_EVIDENCE_ISSUES",
    "MAX_RUNTIME_TRANSFER_EVIDENCE_RECORDS",
    "MAX_RUNTIME_TRANSFER_EVIDENCE_REPORT_BYTES",
    "RUNTIME_TRANSFER_COST_CLAIM_STATUS",
    "RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS",
    "RUNTIME_TRANSFER_EVIDENCE_CONTRACT",
    "RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION",
    "RUNTIME_TRANSFER_EVIDENCE_SCOPE",
    "RUNTIME_TRANSFER_EXECUTION_POLICY",
    "RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS",
    "RUNTIME_TRANSFER_STATUS",
    "RuntimeTransferEvidenceError",
    "RuntimeTransferEvidenceIssue",
    "RuntimeTransferEvidenceRecord",
    "RuntimeTransferEvidenceReport",
    "assert_runtime_transfer_evidence",
    "build_runtime_transfer_evidence_report",
    "dump_runtime_transfer_evidence_report",
    "runtime_transfer_evidence_report_to_dict",
]
