"""Metadata-only evidence for trusted simulator layout materialization."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.memory import LayoutKind, dtype_size_bytes
from tuc.ir.model import ComputeGraph, TensorRef
from tuc.runtime.backend_equivalence import RuntimeBackendEquivalenceReport
from tuc.runtime.executor import RuntimeExecutionResult
from tuc.runtime.layout_conversion_executor import (
    MAX_RUNTIME_LAYOUT_CONVERTER_PHYSICAL_ELEMENTS,
    RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_LAYOUT_CONVERTER_CONTRACT,
    RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE,
    RUNTIME_LAYOUT_CONVERTER_NAME,
    RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE,
    RuntimeLayoutConversionExecutionStep,
)
from tuc.runtime.output_manifest import build_runtime_output_manifest_report
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.plan import LayoutConversionCost
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_materialized_layout_conversion_report.v0"
)
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT = (
    "runtime_layout_conversion.materialized_trusted_simulator.v0"
)
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_ARTIFACT_STATUS = "review_evidence"
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_SCOPE = "trusted_simulator_only"
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_POLICY = (
    "trusted_simulator_conversion_executed"
)
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RESIDENCY_CLAIM = (
    "not_native_or_device_residency"
)
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_PERFORMANCE_CLAIM = "not_measured"
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_EXTERNAL_ARTIFACTS = "forbidden"
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_STATUS = "passed"
RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RUNTIME_DTYPE = "float64"
MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSIONS = 64
MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_FIELD_BYTES = 256

_SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class RuntimeMaterializedLayoutConversionRecord:
    """Metadata for one conversion executed by the trusted simulator converter."""

    tensor_name: str
    source_operation: str
    target_operation: str
    source_backend: str
    target_backend: str
    source_layout: LayoutKind
    target_layout: LayoutKind
    logical_shape: tuple[int, int]
    physical_shape: tuple[int, int, int, int]
    tile_shape: tuple[int, int]
    planned_dtype: str
    runtime_dtype: str
    planned_bytes: int
    runtime_logical_bytes: int
    runtime_physical_bytes: int
    logical_element_count: int
    physical_element_count: int
    padding_element_count: int
    temporary_storage_bytes: int
    semantic_verification: str
    conversion_status: str

    def __post_init__(self) -> None:
        for text_value, label in (
            (self.tensor_name, "tensor_name"),
            (self.source_operation, "source_operation"),
            (self.target_operation, "target_operation"),
            (self.source_backend, "source_backend"),
            (self.target_backend, "target_backend"),
            (self.planned_dtype, "planned_dtype"),
            (self.runtime_dtype, "runtime_dtype"),
            (self.semantic_verification, "semantic_verification"),
            (self.conversion_status, "conversion_status"),
        ):
            _require_safe_text(text_value, label)
        if self.source_layout is not LayoutKind.BLOCKED:
            raise ValueError("materialized evidence source layout must be blocked")
        if self.target_layout is not LayoutKind.ROW_MAJOR:
            raise ValueError("materialized evidence target layout must be row_major")
        _require_positive_shape(self.logical_shape, 2, "logical_shape")
        _require_positive_shape(self.physical_shape, 4, "physical_shape")
        if self.tile_shape != RUNTIME_LAYOUT_CONVERTER_TILE_SHAPE:
            raise ValueError("materialized evidence tile shape must be 2x2")
        if self.runtime_dtype != RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RUNTIME_DTYPE:
            raise ValueError("materialized evidence runtime dtype mismatch")
        for integer_value, label in (
            (self.planned_bytes, "planned_bytes"),
            (self.runtime_logical_bytes, "runtime_logical_bytes"),
            (self.runtime_physical_bytes, "runtime_physical_bytes"),
            (self.logical_element_count, "logical_element_count"),
            (self.physical_element_count, "physical_element_count"),
            (self.temporary_storage_bytes, "temporary_storage_bytes"),
        ):
            _require_positive_int(integer_value, label)
        if (
            not isinstance(self.padding_element_count, int)
            or isinstance(self.padding_element_count, bool)
            or self.padding_element_count < 0
        ):
            raise ValueError("padding_element_count must be a non-negative integer")
        rows, columns = self.logical_shape
        expected_physical_shape = ((rows + 1) // 2, (columns + 1) // 2, 2, 2)
        if self.physical_shape != expected_physical_shape:
            raise ValueError("materialized evidence physical shape mismatch")
        if self.logical_element_count != rows * columns:
            raise ValueError("materialized evidence logical element count mismatch")
        physical_elements = 1
        for dimension in self.physical_shape:
            physical_elements *= dimension
        if self.physical_element_count != physical_elements:
            raise ValueError("materialized evidence physical element count mismatch")
        if (
            self.physical_element_count
            > MAX_RUNTIME_LAYOUT_CONVERTER_PHYSICAL_ELEMENTS
        ):
            raise ValueError("materialized evidence physical element limit exceeded")
        if self.padding_element_count != physical_elements - self.logical_element_count:
            raise ValueError("materialized evidence padding count mismatch")
        if self.planned_bytes != (
            self.logical_element_count * dtype_size_bytes(self.planned_dtype)
        ):
            raise ValueError("materialized evidence planned byte count mismatch")
        if self.runtime_logical_bytes != self.logical_element_count * 8:
            raise ValueError("materialized evidence runtime logical bytes mismatch")
        if self.runtime_physical_bytes != self.physical_element_count * 8:
            raise ValueError("materialized evidence runtime physical bytes mismatch")
        if self.temporary_storage_bytes != (
            self.runtime_logical_bytes + self.runtime_physical_bytes
        ):
            raise ValueError("materialized evidence temporary storage mismatch")
        if self.semantic_verification != "exact_logical_values":
            raise ValueError("materialized evidence semantic verification mismatch")
        if self.conversion_status != "executed_and_verified":
            raise ValueError("materialized evidence conversion status mismatch")


@dataclass(frozen=True)
class RuntimeMaterializedLayoutConversionReport:
    """Closed proof report for trusted simulator layout conversion execution."""

    graph_name: str
    baseline_run_id: str
    candidate_run_id: str
    materialized_trace_metadata_digest: str
    candidate_output_metadata_digest: str
    backend_equivalence_metadata_digest: str
    operation_step_count: int
    conversions: tuple[RuntimeMaterializedLayoutConversionRecord, ...]
    evidence_contract: str = RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT
    artifact_status: str = RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_ARTIFACT_STATUS
    materialization_scope: str = RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_SCOPE
    materialization_policy: str = RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_POLICY
    converter_contract: str = RUNTIME_LAYOUT_CONVERTER_CONTRACT
    converter_name: str = RUNTIME_LAYOUT_CONVERTER_NAME
    converter_execution_mode: str = RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    external_artifacts: str = RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_EXTERNAL_ARTIFACTS
    residency_claim_status: str = (
        RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RESIDENCY_CLAIM
    )
    performance_claim_status: str = (
        RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_PERFORMANCE_CLAIM
    )
    backend_equivalence_passed: bool = True
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES
    )
    status: str = RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_STATUS

    def __post_init__(self) -> None:
        for value, label in (
            (self.graph_name, "graph_name"),
            (self.baseline_run_id, "baseline_run_id"),
            (self.candidate_run_id, "candidate_run_id"),
        ):
            _require_safe_text(value, label)
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError("materialized evidence run IDs must be distinct")
        for digest, label in (
            (self.materialized_trace_metadata_digest, "materialized trace digest"),
            (self.candidate_output_metadata_digest, "candidate output digest"),
            (
                self.backend_equivalence_metadata_digest,
                "backend equivalence metadata digest",
            ),
        ):
            if _DIGEST_RE.fullmatch(digest) is None:
                raise ValueError(f"{label} is invalid")
        _require_positive_int(self.operation_step_count, "operation_step_count")
        if type(self.conversions) is not tuple or not self.conversions:
            raise ValueError("materialized evidence conversions must be a non-empty tuple")
        if len(self.conversions) > MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSIONS:
            raise ValueError("materialized evidence conversion count exceeds limit")
        seen: set[tuple[str, str]] = set()
        for conversion in self.conversions:
            if not isinstance(conversion, RuntimeMaterializedLayoutConversionRecord):
                raise TypeError("materialized evidence conversions must be records")
            key = (conversion.target_operation, conversion.tensor_name)
            if key in seen:
                raise ValueError("materialized evidence contains duplicate conversions")
            seen.add(key)
        expected_fields = (
            (self.evidence_contract, RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT),
            (
                self.artifact_status,
                RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_ARTIFACT_STATUS,
            ),
            (self.materialization_scope, RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_SCOPE),
            (self.materialization_policy, RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_POLICY),
            (self.converter_contract, RUNTIME_LAYOUT_CONVERTER_CONTRACT),
            (self.converter_name, RUNTIME_LAYOUT_CONVERTER_NAME),
            (self.converter_execution_mode, RUNTIME_LAYOUT_CONVERTER_EXECUTION_MODE),
            (self.raw_value_policy, RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS),
            (
                self.external_artifacts,
                RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_EXTERNAL_ARTIFACTS,
            ),
            (
                self.residency_claim_status,
                RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RESIDENCY_CLAIM,
            ),
            (
                self.performance_claim_status,
                RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_PERFORMANCE_CLAIM,
            ),
            (self.status, RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_STATUS),
        )
        if any(observed != expected for observed, expected in expected_fields):
            raise ValueError("materialized layout conversion report contract mismatch")
        if self.backend_equivalence_passed is not True:
            raise ValueError("materialized evidence requires backend equivalence PASS")
        if (
            self.blocked_execution_surfaces
            != RUNTIME_LAYOUT_CONVERTER_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("materialized evidence blocked surfaces changed")


def build_runtime_materialized_layout_conversion_report(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    execution: RuntimeExecutionResult,
    equivalence: RuntimeBackendEquivalenceReport,
) -> RuntimeMaterializedLayoutConversionReport:
    """Bind plan, executed conversion trace, and backend equivalence evidence."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("materialized evidence graph must be ComputeGraph")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("materialized evidence partition plan must be PartitionPlan")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("materialized evidence execution must be RuntimeExecutionResult")
    if not isinstance(equivalence, RuntimeBackendEquivalenceReport):
        raise TypeError("materialized evidence equivalence must be report")
    if partition_plan.graph_name != graph.name or execution.trace.graph_name != graph.name:
        raise ValueError("materialized evidence graph linkage mismatch")
    if equivalence.graph_name != graph.name:
        raise ValueError("materialized evidence equivalence graph mismatch")
    if not equivalence.passed:
        raise ValueError("materialized evidence requires passing backend equivalence")
    steps = execution.trace.layout_conversion_steps
    if len(steps) != len(partition_plan.layout_conversions) or not steps:
        raise ValueError("materialized evidence plan and execution counts must match")

    planned: dict[tuple[str, str], LayoutConversionCost] = {}
    for conversion in partition_plan.layout_conversions:
        if not isinstance(conversion, LayoutConversionCost):
            raise TypeError("materialized evidence plan entries must be conversions")
        planned[(conversion.target_operation, conversion.tensor_name)] = conversion
    if len(planned) != len(partition_plan.layout_conversions):
        raise ValueError("materialized evidence plan contains duplicate conversions")
    assignments: dict[str, Assignment] = {}
    for assignment in partition_plan.assignments:
        if not isinstance(assignment, Assignment):
            raise TypeError("materialized evidence plan assignments must be Assignment")
        assignments[assignment.operation_name] = assignment
    tensors = {
        tensor.name: tensor
        for operation in graph.operations
        for tensor in operation.outputs
    }
    records = tuple(
        _record_from_step(step, planned, assignments, tensors) for step in steps
    )
    if {(record.target_operation, record.tensor_name) for record in records} != set(
        planned
    ):
        raise ValueError("materialized evidence executed conversion set mismatch")
    candidate_runs = tuple(
        run for run in equivalence.runs if run.run_id == equivalence.candidate_run_id
    )
    if len(candidate_runs) != 1:
        raise ValueError("materialized evidence candidate equivalence run is missing")
    candidate_run = candidate_runs[0]
    output_manifest = build_runtime_output_manifest_report(graph, execution)
    if not output_manifest.passed:
        raise ValueError("materialized evidence candidate output manifest must pass")
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
        raise ValueError("materialized evidence candidate equivalence run mismatch")
    trace_digest = f"sha256:{sha256(execution.trace.dump().encode('utf-8')).hexdigest()}"
    return RuntimeMaterializedLayoutConversionReport(
        graph_name=graph.name,
        baseline_run_id=equivalence.baseline_run_id,
        candidate_run_id=equivalence.candidate_run_id,
        materialized_trace_metadata_digest=trace_digest,
        candidate_output_metadata_digest=output_manifest.output_metadata_digest,
        backend_equivalence_metadata_digest=equivalence.comparison_metadata_digest,
        operation_step_count=len(execution.trace.steps),
        conversions=records,
    )


def runtime_materialized_layout_conversion_report_to_dict(
    report: RuntimeMaterializedLayoutConversionReport,
) -> dict[str, object]:
    """Return a deterministic metadata-only report mapping."""

    if not isinstance(report, RuntimeMaterializedLayoutConversionReport):
        raise TypeError("materialized layout conversion report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "backend_equivalence_metadata_digest": (
            report.backend_equivalence_metadata_digest
        ),
        "backend_equivalence_passed": report.backend_equivalence_passed,
        "baseline_run_id": report.baseline_run_id,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_run_id": report.candidate_run_id,
        "candidate_output_metadata_digest": report.candidate_output_metadata_digest,
        "conversion_count": len(report.conversions),
        "conversions": [_record_to_dict(record) for record in report.conversions],
        "converter_contract": report.converter_contract,
        "converter_execution_mode": report.converter_execution_mode,
        "converter_name": report.converter_name,
        "evidence_contract": report.evidence_contract,
        "external_artifacts": report.external_artifacts,
        "graph_name": report.graph_name,
        "materialization_policy": report.materialization_policy,
        "materialization_scope": report.materialization_scope,
        "materialized_trace_metadata_digest": report.materialized_trace_metadata_digest,
        "operation_step_count": report.operation_step_count,
        "performance_claim_status": report.performance_claim_status,
        "raw_value_policy": report.raw_value_policy,
        "residency_claim_status": report.residency_claim_status,
        "schema_version": RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_SCHEMA_VERSION,
        "status": report.status,
    }


def dump_runtime_materialized_layout_conversion_report(
    report: RuntimeMaterializedLayoutConversionReport,
) -> str:
    """Render stable JSON without runtime tensor values."""

    text = json.dumps(
        runtime_materialized_layout_conversion_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_BYTES:
        raise ValueError("materialized layout conversion report exceeds byte limit")
    return text + "\n"


def _record_from_step(
    step: RuntimeLayoutConversionExecutionStep,
    planned: dict[tuple[str, str], LayoutConversionCost],
    assignments: dict[str, Assignment],
    tensors: dict[str, TensorRef],
) -> RuntimeMaterializedLayoutConversionRecord:
    key = (step.target_operation, step.tensor_name)
    conversion = planned.get(key)
    if not isinstance(conversion, LayoutConversionCost):
        raise ValueError("materialized evidence execution step is not planned")
    if (
        conversion.source_operation != step.source_operation
        or conversion.source_layout is not step.source_layout
        or conversion.target_layout is not step.target_layout
        or conversion.bytes_converted != step.planned_bytes
    ):
        raise ValueError("materialized evidence execution step does not match plan")
    tensor = tensors.get(step.tensor_name)
    source_assignment = assignments.get(step.source_operation)
    target_assignment = assignments.get(step.target_operation)
    if not isinstance(tensor, TensorRef):
        raise ValueError("materialized evidence tensor is not a graph output")
    if not isinstance(source_assignment, Assignment) or not isinstance(
        target_assignment, Assignment
    ):
        raise ValueError("materialized evidence assignment linkage is incomplete")
    return RuntimeMaterializedLayoutConversionRecord(
        tensor_name=step.tensor_name,
        source_operation=step.source_operation,
        target_operation=step.target_operation,
        source_backend=source_assignment.backend_name,
        target_backend=target_assignment.backend_name,
        source_layout=step.source_layout,
        target_layout=step.target_layout,
        logical_shape=(step.logical_shape[0], step.logical_shape[1]),
        physical_shape=(
            step.physical_shape[0],
            step.physical_shape[1],
            step.physical_shape[2],
            step.physical_shape[3],
        ),
        tile_shape=step.tile_shape,
        planned_dtype=tensor.dtype,
        runtime_dtype=RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RUNTIME_DTYPE,
        planned_bytes=step.planned_bytes,
        runtime_logical_bytes=step.runtime_logical_bytes,
        runtime_physical_bytes=step.runtime_physical_bytes,
        logical_element_count=step.logical_element_count,
        physical_element_count=step.physical_element_count,
        padding_element_count=step.padding_element_count,
        temporary_storage_bytes=step.temporary_storage_bytes,
        semantic_verification=step.semantic_verification,
        conversion_status=step.status,
    )


def _record_to_dict(
    record: RuntimeMaterializedLayoutConversionRecord,
) -> dict[str, object]:
    return {
        "conversion_status": record.conversion_status,
        "logical_element_count": record.logical_element_count,
        "logical_shape": list(record.logical_shape),
        "padding_element_count": record.padding_element_count,
        "physical_element_count": record.physical_element_count,
        "physical_shape": list(record.physical_shape),
        "planned_bytes": record.planned_bytes,
        "planned_dtype": record.planned_dtype,
        "runtime_dtype": record.runtime_dtype,
        "runtime_logical_bytes": record.runtime_logical_bytes,
        "runtime_physical_bytes": record.runtime_physical_bytes,
        "semantic_verification": record.semantic_verification,
        "source_backend": record.source_backend,
        "source_layout": record.source_layout.value,
        "source_operation": record.source_operation,
        "target_backend": record.target_backend,
        "target_layout": record.target_layout.value,
        "target_operation": record.target_operation,
        "temporary_storage_bytes": record.temporary_storage_bytes,
        "tensor_name": record.tensor_name,
        "tile_shape": list(record.tile_shape),
    }


def _require_safe_text(value: str, label: str) -> None:
    if not isinstance(value, str) or _SAFE_TEXT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be safe bounded metadata")
    if (
        len(value.encode("utf-8"))
        > MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_FIELD_BYTES
    ):
        raise ValueError(f"{label} exceeds metadata byte limit")


def _require_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _require_positive_shape(value: tuple[int, ...], rank: int, label: str) -> None:
    if type(value) is not tuple or len(value) != rank:
        raise ValueError(f"{label} must be positive rank-{rank}")
    for dimension in value:
        _require_positive_int(dimension, label)


__all__ = [
    "MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_FIELD_BYTES",
    "MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_BYTES",
    "MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSIONS",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_ARTIFACT_STATUS",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_EXTERNAL_ARTIFACTS",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_PERFORMANCE_CLAIM",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_POLICY",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_SCHEMA_VERSION",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RESIDENCY_CLAIM",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_RUNTIME_DTYPE",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_SCOPE",
    "RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_STATUS",
    "RuntimeMaterializedLayoutConversionRecord",
    "RuntimeMaterializedLayoutConversionReport",
    "build_runtime_materialized_layout_conversion_report",
    "dump_runtime_materialized_layout_conversion_report",
    "runtime_materialized_layout_conversion_report_to_dict",
]
