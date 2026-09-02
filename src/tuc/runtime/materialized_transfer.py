"""Metadata-only evidence for trusted simulator transfer materialization."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, MemoryDomainKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, TensorRef
from tuc.runtime.backend_equivalence import RuntimeBackendEquivalenceReport
from tuc.runtime.executor import RuntimeExecutionResult
from tuc.runtime.materialized_layout_conversion import (
    RuntimeMaterializedLayoutConversionReport,
    build_runtime_materialized_layout_conversion_report,
    dump_runtime_materialized_layout_conversion_report,
)
from tuc.runtime.output_manifest import build_runtime_output_manifest_report
from tuc.runtime.partitioning import PartitionPlan
from tuc.runtime.plan import RuntimeTransferEdge
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
from tuc.runtime.transfer_executor import (
    MAX_RUNTIME_TRANSFER_EXECUTOR_ELEMENTS,
    RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_TRANSFER_EXECUTOR_CONTRACT,
    RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE,
    RUNTIME_TRANSFER_EXECUTOR_NAME,
    RUNTIME_TRANSFER_EXECUTOR_SEQUENCING,
    RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR,
    RuntimeTransferExecutionStep,
)

RUNTIME_MATERIALIZED_TRANSFER_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_materialized_transfer_report.v0"
)
RUNTIME_MATERIALIZED_TRANSFER_CONTRACT = (
    "runtime_transfer.materialized_trusted_simulator.v0"
)
RUNTIME_MATERIALIZED_TRANSFER_ARTIFACT_STATUS = "review_evidence"
RUNTIME_MATERIALIZED_TRANSFER_SCOPE = "trusted_simulator_domain_copy_only"
RUNTIME_MATERIALIZED_TRANSFER_POLICY = "trusted_simulator_transfer_executed"
RUNTIME_MATERIALIZED_TRANSFER_RESIDENCY_CLAIM = (
    "simulated_domains_not_physical_residency"
)
RUNTIME_MATERIALIZED_TRANSFER_PERFORMANCE_CLAIM = "not_measured"
RUNTIME_MATERIALIZED_TRANSFER_EXTERNAL_ARTIFACTS = "forbidden"
RUNTIME_MATERIALIZED_TRANSFER_RUNTIME_DTYPE = "float64"
RUNTIME_MATERIALIZED_TRANSFER_STATUS = "passed"
MAX_RUNTIME_MATERIALIZED_TRANSFERS = 64
MAX_RUNTIME_MATERIALIZED_TRANSFER_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_MATERIALIZED_TRANSFER_FIELD_BYTES = 256

_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeMaterializedTransferRecord:
    """Metadata for one executed trusted simulator-domain transfer."""

    tensor_name: str
    source_operation: str
    target_operation: str
    source_backend: str
    target_backend: str
    source_domain: MemoryDomainKind
    target_domain: MemoryDomainKind
    source_layout: LayoutKind
    target_layout: LayoutKind
    copy_input_layout: LayoutKind
    logical_shape: tuple[int, ...]
    planned_dtype: str
    runtime_dtype: str
    planned_bytes: int
    runtime_bytes: int
    element_count: int
    ownership_verification: str
    semantic_verification: str
    transfer_status: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.tensor_name, "tensor_name"),
            (self.source_operation, "source_operation"),
            (self.target_operation, "target_operation"),
            (self.source_backend, "source_backend"),
            (self.target_backend, "target_backend"),
            (self.planned_dtype, "planned_dtype"),
            (self.runtime_dtype, "runtime_dtype"),
            (self.ownership_verification, "ownership_verification"),
            (self.semantic_verification, "semantic_verification"),
            (self.transfer_status, "transfer_status"),
        ):
            _require_safe_text(value, label)
        if (self.source_domain, self.target_domain) != (
            RUNTIME_TRANSFER_EXECUTOR_SUPPORTED_DOMAIN_PAIR
        ):
            raise ValueError("materialized transfer evidence domain pair unsupported")
        for layout, label in (
            (self.source_layout, "source_layout"),
            (self.target_layout, "target_layout"),
            (self.copy_input_layout, "copy_input_layout"),
        ):
            if not isinstance(layout, LayoutKind):
                raise TypeError(f"{label} must be LayoutKind")
        if self.copy_input_layout is not self.target_layout:
            raise ValueError("materialized transfer evidence input is not target-ready")
        _require_positive_shape(self.logical_shape)
        _require_positive_int(self.planned_bytes, "planned_bytes")
        _require_positive_int(self.runtime_bytes, "runtime_bytes")
        _require_positive_int(self.element_count, "element_count")
        expected_elements = 1
        for dimension in self.logical_shape:
            expected_elements *= dimension
        if self.element_count != expected_elements:
            raise ValueError("materialized transfer evidence element count mismatch")
        if self.element_count > MAX_RUNTIME_TRANSFER_EXECUTOR_ELEMENTS:
            raise ValueError("materialized transfer evidence element limit exceeded")
        if self.planned_bytes != self.element_count * dtype_size_bytes(
            self.planned_dtype
        ):
            raise ValueError("materialized transfer evidence planned bytes mismatch")
        if self.runtime_dtype != RUNTIME_MATERIALIZED_TRANSFER_RUNTIME_DTYPE:
            raise ValueError("materialized transfer evidence runtime dtype mismatch")
        if self.runtime_bytes != self.element_count * 8:
            raise ValueError("materialized transfer evidence runtime bytes mismatch")
        if self.ownership_verification != "distinct_owned_buffer":
            raise ValueError("materialized transfer evidence ownership mismatch")
        if self.semantic_verification != "exact_logical_values":
            raise ValueError("materialized transfer evidence semantic check mismatch")
        if self.transfer_status != "executed_and_verified":
            raise ValueError("materialized transfer evidence status mismatch")


@dataclass(frozen=True)
class RuntimeMaterializedTransferReport:
    """Closed proof report for trusted simulator transfer execution."""

    graph_name: str
    baseline_run_id: str
    candidate_run_id: str
    materialized_trace_metadata_digest: str
    candidate_output_metadata_digest: str
    backend_equivalence_metadata_digest: str
    materialized_layout_conversion_metadata_digest: str
    operation_step_count: int
    layout_conversion_count: int
    transfers: tuple[RuntimeMaterializedTransferRecord, ...]
    evidence_contract: str = RUNTIME_MATERIALIZED_TRANSFER_CONTRACT
    artifact_status: str = RUNTIME_MATERIALIZED_TRANSFER_ARTIFACT_STATUS
    materialization_scope: str = RUNTIME_MATERIALIZED_TRANSFER_SCOPE
    materialization_policy: str = RUNTIME_MATERIALIZED_TRANSFER_POLICY
    transfer_executor_contract: str = RUNTIME_TRANSFER_EXECUTOR_CONTRACT
    transfer_executor_name: str = RUNTIME_TRANSFER_EXECUTOR_NAME
    transfer_execution_mode: str = RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE
    sequencing_policy: str = RUNTIME_TRANSFER_EXECUTOR_SEQUENCING
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    external_artifacts: str = RUNTIME_MATERIALIZED_TRANSFER_EXTERNAL_ARTIFACTS
    residency_claim_status: str = RUNTIME_MATERIALIZED_TRANSFER_RESIDENCY_CLAIM
    performance_claim_status: str = RUNTIME_MATERIALIZED_TRANSFER_PERFORMANCE_CLAIM
    backend_equivalence_passed: bool = True
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_MATERIALIZED_TRANSFER_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.graph_name, "graph_name"),
            (self.baseline_run_id, "baseline_run_id"),
            (self.candidate_run_id, "candidate_run_id"),
        ):
            _require_safe_text(value, label)
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError("materialized transfer run IDs must be distinct")
        for digest, label in (
            (self.materialized_trace_metadata_digest, "trace digest"),
            (self.candidate_output_metadata_digest, "output digest"),
            (self.backend_equivalence_metadata_digest, "equivalence digest"),
            (
                self.materialized_layout_conversion_metadata_digest,
                "layout conversion digest",
            ),
        ):
            if _DIGEST_RE.fullmatch(digest) is None:
                raise ValueError(f"materialized transfer {label} is invalid")
        _require_positive_int(self.operation_step_count, "operation_step_count")
        _require_positive_int(self.layout_conversion_count, "layout_conversion_count")
        if type(self.transfers) is not tuple or not self.transfers:
            raise ValueError("materialized transfer records must be a non-empty tuple")
        if len(self.transfers) > MAX_RUNTIME_MATERIALIZED_TRANSFERS:
            raise ValueError("materialized transfer record count exceeds limit")
        seen: set[tuple[str, str]] = set()
        for transfer in self.transfers:
            if not isinstance(transfer, RuntimeMaterializedTransferRecord):
                raise TypeError("materialized transfer entries must be records")
            key = (transfer.target_operation, transfer.tensor_name)
            if key in seen:
                raise ValueError("materialized transfer report contains duplicates")
            seen.add(key)
        expected_fields = (
            (self.evidence_contract, RUNTIME_MATERIALIZED_TRANSFER_CONTRACT),
            (self.artifact_status, RUNTIME_MATERIALIZED_TRANSFER_ARTIFACT_STATUS),
            (self.materialization_scope, RUNTIME_MATERIALIZED_TRANSFER_SCOPE),
            (self.materialization_policy, RUNTIME_MATERIALIZED_TRANSFER_POLICY),
            (self.transfer_executor_contract, RUNTIME_TRANSFER_EXECUTOR_CONTRACT),
            (self.transfer_executor_name, RUNTIME_TRANSFER_EXECUTOR_NAME),
            (self.transfer_execution_mode, RUNTIME_TRANSFER_EXECUTOR_EXECUTION_MODE),
            (self.sequencing_policy, RUNTIME_TRANSFER_EXECUTOR_SEQUENCING),
            (self.raw_value_policy, RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS),
            (
                self.external_artifacts,
                RUNTIME_MATERIALIZED_TRANSFER_EXTERNAL_ARTIFACTS,
            ),
            (
                self.residency_claim_status,
                RUNTIME_MATERIALIZED_TRANSFER_RESIDENCY_CLAIM,
            ),
            (
                self.performance_claim_status,
                RUNTIME_MATERIALIZED_TRANSFER_PERFORMANCE_CLAIM,
            ),
            (self.status, RUNTIME_MATERIALIZED_TRANSFER_STATUS),
        )
        if any(observed != expected for observed, expected in expected_fields):
            raise ValueError("materialized transfer report contract mismatch")
        if self.backend_equivalence_passed is not True:
            raise ValueError("materialized transfer requires backend equivalence PASS")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_TRANSFER_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("materialized transfer blocked surfaces changed")


def build_runtime_materialized_transfer_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    execution: RuntimeExecutionResult,
    equivalence: RuntimeBackendEquivalenceReport,
    layout_conversion: RuntimeMaterializedLayoutConversionReport,
) -> RuntimeMaterializedTransferReport:
    """Bind plan, transfer execution, layout conversion, and equivalence."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("materialized transfer graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("materialized transfer partition_plan must be PartitionPlan")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("materialized transfer execution must be RuntimeExecutionResult")
    if not isinstance(equivalence, RuntimeBackendEquivalenceReport):
        raise TypeError("materialized transfer equivalence must be report")
    if not isinstance(layout_conversion, RuntimeMaterializedLayoutConversionReport):
        raise TypeError("materialized transfer layout conversion must be report")
    if (
        partition_plan.graph_name != graph.name
        or execution.trace.graph_name != graph.name
        or equivalence.graph_name != graph.name
        or layout_conversion.graph_name != graph.name
    ):
        raise ValueError("materialized transfer graph linkage mismatch")
    if not equivalence.passed:
        raise ValueError("materialized transfer requires passing backend equivalence")
    if (
        layout_conversion.baseline_run_id != equivalence.baseline_run_id
        or layout_conversion.candidate_run_id != equivalence.candidate_run_id
        or layout_conversion.backend_equivalence_metadata_digest
        != equivalence.comparison_metadata_digest
    ):
        raise ValueError("materialized transfer layout-equivalence linkage mismatch")
    expected_layout_conversion = build_runtime_materialized_layout_conversion_report(
        graph,
        partition_plan,
        execution,
        equivalence,
    )
    if dump_runtime_materialized_layout_conversion_report(
        layout_conversion
    ) != dump_runtime_materialized_layout_conversion_report(
        expected_layout_conversion
    ):
        raise ValueError("materialized transfer layout report does not match execution")
    if len(execution.trace.transfer_steps) != len(partition_plan.transfer_edges):
        raise ValueError("materialized transfer plan and execution counts must match")
    if not execution.trace.transfer_steps:
        raise ValueError("materialized transfer evidence requires executed transfers")
    if len(execution.trace.layout_conversion_steps) != len(
        partition_plan.layout_conversions
    ):
        raise ValueError("materialized transfer requires all layout conversions")

    planned: dict[tuple[str, str], RuntimeTransferEdge] = {}
    for transfer in partition_plan.transfer_edges:
        if not isinstance(transfer, RuntimeTransferEdge):
            raise TypeError("materialized transfer plan entries must be transfer edges")
        planned[(transfer.target_operation, transfer.tensor_name)] = transfer
    if len(planned) != len(partition_plan.transfer_edges):
        raise ValueError("materialized transfer plan contains duplicates")
    tensors = {
        tensor.name: tensor
        for operation in graph.operations
        for tensor in operation.outputs
    }
    records = tuple(
        _record_from_step(step, planned, tensors)
        for step in execution.trace.transfer_steps
    )
    if {(record.target_operation, record.tensor_name) for record in records} != set(
        planned
    ):
        raise ValueError("materialized transfer executed set mismatch")

    conversion_keys = {
        (step.target_operation, step.tensor_name)
        for step in execution.trace.layout_conversion_steps
    }
    for record in records:
        if record.source_layout is not record.target_layout and (
            record.target_operation,
            record.tensor_name,
        ) not in conversion_keys:
            raise ValueError("materialized transfer is missing its layout conversion")

    output_manifest = build_runtime_output_manifest_report(graph, execution)
    if not output_manifest.passed:
        raise ValueError("materialized transfer output manifest must pass")
    candidate_runs = tuple(
        run for run in equivalence.runs if run.run_id == equivalence.candidate_run_id
    )
    if len(candidate_runs) != 1:
        raise ValueError("materialized transfer candidate equivalence run is missing")
    candidate_run = candidate_runs[0]
    expected_candidate_metadata = (
        graph.name,
        tuple(assignment.backend_name for assignment in partition_plan.assignments),
        tuple(output.tensor_name for output in output_manifest.expected_outputs),
        output_manifest.output_metadata_digest,
        len(execution.trace.steps),
        len(execution.records),
    )
    observed_candidate_metadata = (
        candidate_run.graph_name,
        candidate_run.planned_backend_sequence,
        candidate_run.output_tensor_names,
        candidate_run.output_metadata_digest,
        candidate_run.trace_step_count,
        candidate_run.tensor_record_count,
    )
    if observed_candidate_metadata != expected_candidate_metadata:
        raise ValueError("materialized transfer candidate equivalence run mismatch")

    trace_digest = _digest(execution.trace.dump())
    if (
        layout_conversion.materialized_trace_metadata_digest != trace_digest
        or layout_conversion.candidate_output_metadata_digest
        != output_manifest.output_metadata_digest
    ):
        raise ValueError("materialized transfer layout-execution linkage mismatch")
    layout_digest = _digest(
        dump_runtime_materialized_layout_conversion_report(layout_conversion)
    )
    return RuntimeMaterializedTransferReport(
        graph_name=graph.name,
        baseline_run_id=equivalence.baseline_run_id,
        candidate_run_id=equivalence.candidate_run_id,
        materialized_trace_metadata_digest=trace_digest,
        candidate_output_metadata_digest=output_manifest.output_metadata_digest,
        backend_equivalence_metadata_digest=equivalence.comparison_metadata_digest,
        materialized_layout_conversion_metadata_digest=layout_digest,
        operation_step_count=len(execution.trace.steps),
        layout_conversion_count=len(execution.trace.layout_conversion_steps),
        transfers=records,
    )


def runtime_materialized_transfer_report_to_dict(
    report: RuntimeMaterializedTransferReport,
) -> dict[str, object]:
    """Return a deterministic metadata-only report mapping."""

    if not isinstance(report, RuntimeMaterializedTransferReport):
        raise TypeError("materialized transfer report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "backend_equivalence_metadata_digest": (
            report.backend_equivalence_metadata_digest
        ),
        "backend_equivalence_passed": report.backend_equivalence_passed,
        "baseline_run_id": report.baseline_run_id,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_output_metadata_digest": report.candidate_output_metadata_digest,
        "candidate_run_id": report.candidate_run_id,
        "evidence_contract": report.evidence_contract,
        "external_artifacts": report.external_artifacts,
        "graph_name": report.graph_name,
        "layout_conversion_count": report.layout_conversion_count,
        "materialization_policy": report.materialization_policy,
        "materialization_scope": report.materialization_scope,
        "materialized_layout_conversion_metadata_digest": (
            report.materialized_layout_conversion_metadata_digest
        ),
        "materialized_trace_metadata_digest": report.materialized_trace_metadata_digest,
        "operation_step_count": report.operation_step_count,
        "performance_claim_status": report.performance_claim_status,
        "raw_value_policy": report.raw_value_policy,
        "residency_claim_status": report.residency_claim_status,
        "schema_version": RUNTIME_MATERIALIZED_TRANSFER_REPORT_SCHEMA_VERSION,
        "sequencing_policy": report.sequencing_policy,
        "status": report.status,
        "transfer_count": len(report.transfers),
        "transfer_execution_mode": report.transfer_execution_mode,
        "transfer_executor_contract": report.transfer_executor_contract,
        "transfer_executor_name": report.transfer_executor_name,
        "transfers": [_record_to_dict(record) for record in report.transfers],
    }


def dump_runtime_materialized_transfer_report(
    report: RuntimeMaterializedTransferReport,
) -> str:
    """Render stable JSON without runtime tensor values."""

    text = json.dumps(
        runtime_materialized_transfer_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_MATERIALIZED_TRANSFER_REPORT_BYTES:
        raise ValueError("materialized transfer report exceeds byte limit")
    return text + "\n"


def _record_from_step(
    step: RuntimeTransferExecutionStep,
    planned: dict[tuple[str, str], RuntimeTransferEdge],
    tensors: dict[str, TensorRef],
) -> RuntimeMaterializedTransferRecord:
    key = (step.target_operation, step.tensor_name)
    transfer = planned.get(key)
    if not isinstance(transfer, RuntimeTransferEdge):
        raise ValueError("materialized transfer execution step is not planned")
    expected_step = (
        transfer.source_operation,
        transfer.source_backend,
        transfer.target_backend,
        transfer.source_domain,
        transfer.target_domain,
        transfer.source_layout,
        transfer.target_layout,
        transfer.bytes_moved,
    )
    observed_step = (
        step.source_operation,
        step.source_backend,
        step.target_backend,
        step.source_domain,
        step.target_domain,
        step.source_layout,
        step.target_layout,
        step.planned_bytes,
    )
    if observed_step != expected_step:
        raise ValueError("materialized transfer execution step does not match plan")
    tensor = tensors.get(step.tensor_name)
    if not isinstance(tensor, TensorRef):
        raise ValueError("materialized transfer tensor is not a graph output")
    return RuntimeMaterializedTransferRecord(
        tensor_name=step.tensor_name,
        source_operation=step.source_operation,
        target_operation=step.target_operation,
        source_backend=step.source_backend,
        target_backend=step.target_backend,
        source_domain=step.source_domain,
        target_domain=step.target_domain,
        source_layout=step.source_layout,
        target_layout=step.target_layout,
        copy_input_layout=step.copy_input_layout,
        logical_shape=step.logical_shape,
        planned_dtype=tensor.dtype,
        runtime_dtype=RUNTIME_MATERIALIZED_TRANSFER_RUNTIME_DTYPE,
        planned_bytes=step.planned_bytes,
        runtime_bytes=step.runtime_bytes,
        element_count=step.element_count,
        ownership_verification=step.ownership_verification,
        semantic_verification=step.semantic_verification,
        transfer_status=step.status,
    )


def _record_to_dict(record: RuntimeMaterializedTransferRecord) -> dict[str, object]:
    return {
        "copy_input_layout": record.copy_input_layout.value,
        "element_count": record.element_count,
        "logical_shape": list(record.logical_shape),
        "ownership_verification": record.ownership_verification,
        "planned_bytes": record.planned_bytes,
        "planned_dtype": record.planned_dtype,
        "runtime_bytes": record.runtime_bytes,
        "runtime_dtype": record.runtime_dtype,
        "semantic_verification": record.semantic_verification,
        "source_backend": record.source_backend,
        "source_domain": record.source_domain.value,
        "source_layout": record.source_layout.value,
        "source_operation": record.source_operation,
        "target_backend": record.target_backend,
        "target_domain": record.target_domain.value,
        "target_layout": record.target_layout.value,
        "target_operation": record.target_operation,
        "tensor_name": record.tensor_name,
        "transfer_status": record.transfer_status,
    }


def _digest(value: str) -> str:
    return f"sha256:{sha256(value.encode('utf-8')).hexdigest()}"


def _require_safe_text(value: str, label: str) -> None:
    if not isinstance(value, str) or _SAFE_TEXT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be safe bounded metadata")
    if len(value.encode("utf-8")) > MAX_RUNTIME_MATERIALIZED_TRANSFER_FIELD_BYTES:
        raise ValueError(f"{label} exceeds metadata byte limit")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_positive_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise ValueError("logical_shape must be non-empty")
    for dimension in value:
        _require_positive_int(dimension, "logical_shape dimension")


__all__ = [
    "MAX_RUNTIME_MATERIALIZED_TRANSFER_FIELD_BYTES",
    "MAX_RUNTIME_MATERIALIZED_TRANSFER_REPORT_BYTES",
    "MAX_RUNTIME_MATERIALIZED_TRANSFERS",
    "RUNTIME_MATERIALIZED_TRANSFER_ARTIFACT_STATUS",
    "RUNTIME_MATERIALIZED_TRANSFER_CONTRACT",
    "RUNTIME_MATERIALIZED_TRANSFER_EXTERNAL_ARTIFACTS",
    "RUNTIME_MATERIALIZED_TRANSFER_PERFORMANCE_CLAIM",
    "RUNTIME_MATERIALIZED_TRANSFER_POLICY",
    "RUNTIME_MATERIALIZED_TRANSFER_REPORT_SCHEMA_VERSION",
    "RUNTIME_MATERIALIZED_TRANSFER_RESIDENCY_CLAIM",
    "RUNTIME_MATERIALIZED_TRANSFER_RUNTIME_DTYPE",
    "RUNTIME_MATERIALIZED_TRANSFER_SCOPE",
    "RUNTIME_MATERIALIZED_TRANSFER_STATUS",
    "RuntimeMaterializedTransferRecord",
    "RuntimeMaterializedTransferReport",
    "build_runtime_materialized_transfer_report",
    "dump_runtime_materialized_transfer_report",
    "runtime_materialized_transfer_report_to_dict",
]
