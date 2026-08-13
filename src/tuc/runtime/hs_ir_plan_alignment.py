"""Data-only evidence that HS-IR, runtime plans, and traces align."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.dialect import validate_hs_module_contract
from tuc.ir.model import ComputeOperation
from tuc.ir.modules import IRModule, IRStage
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeExecutionResult,
    RuntimeExecutionStep,
    trusted_runtime_executor_registry,
)
from tuc.runtime.partitioning import Assignment, PartitionPlan
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_hs_ir_plan_alignment_report.v0"
)
RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT = "runtime_hs_ir_plan_alignment.data_only.v0"
RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS = "review_evidence"
MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_STEPS = 64
MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_ISSUES = 128
MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_FIELD_BYTES = 512

_ALIGNMENT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_STEP_STATUSES = frozenset({"aligned", "failed"})
_TRUSTED_EXECUTOR_STATUSES = frozenset(
    {"trusted", "backend_missing", "operation_unsupported"}
)
_FORBIDDEN_ALIGNMENT_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "command_line",
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
        "output_value",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "reference_value",
        "runtime_handle",
        "source_text",
        "subprocess",
        "tensor_value",
        "tensor_values",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeHsIrPlanAlignmentStep:
    """One operation-level HS-IR, plan, and trace alignment check."""

    operation_name: str
    operation_kind: str
    hs_ir_backend: str
    partition_backend: str
    execution_trace_backend: str
    hs_ir_produced_layout: str
    partition_produced_layout: str
    transfer_bytes: int
    layout_conversion_bytes: int
    trusted_executor_status: str
    alignment_status: str

    def __post_init__(self) -> None:
        _validate_alignment_text(self.operation_name, "operation_name")
        _validate_alignment_text(self.operation_kind, "operation_kind")
        _validate_alignment_text(self.hs_ir_backend, "hs_ir_backend")
        _validate_alignment_text(self.partition_backend, "partition_backend")
        _validate_alignment_text(
            self.execution_trace_backend,
            "execution_trace_backend",
        )
        _validate_alignment_text(self.hs_ir_produced_layout, "hs_ir_produced_layout")
        _validate_alignment_text(
            self.partition_produced_layout,
            "partition_produced_layout",
        )
        _validate_non_negative_int(self.transfer_bytes, "transfer_bytes")
        _validate_non_negative_int(
            self.layout_conversion_bytes,
            "layout_conversion_bytes",
        )
        if self.trusted_executor_status not in _TRUSTED_EXECUTOR_STATUSES:
            raise ValueError("runtime HS-IR alignment trusted executor status invalid")
        if self.alignment_status not in _STEP_STATUSES:
            raise ValueError("runtime HS-IR alignment step status invalid")


@dataclass(frozen=True)
class RuntimeHsIrPlanAlignmentIssue:
    """One derived HS-IR/runtime-plan alignment issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_alignment_text(self.subject, "issue subject")
        _validate_alignment_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeHsIrPlanAlignmentReport:
    """Deterministic report binding HS-IR to plan and execution trace."""

    graph_name: str
    partition_plan_graph_name: str
    execution_trace_graph_name: str
    hs_ir_backend_sequence: tuple[str, ...]
    partition_backend_sequence: tuple[str, ...]
    execution_trace_backend_sequence: tuple[str, ...]
    hs_ir_transfer_edge_count: int
    partition_transfer_edge_count: int
    hs_ir_total_transfer_bytes: int
    partition_total_transfer_bytes: int
    hs_ir_layout_conversion_count: int
    partition_layout_conversion_count: int
    hs_ir_total_layout_conversion_bytes: int
    partition_total_layout_conversion_bytes: int
    hs_ir_total_data_movement_bytes: int
    partition_total_data_movement_bytes: int
    steps: tuple[RuntimeHsIrPlanAlignmentStep, ...]
    issues: tuple[RuntimeHsIrPlanAlignmentIssue, ...]
    alignment_contract: str = RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    artifact_status: str = RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_alignment_text(self.graph_name, "graph_name")
        _validate_alignment_text(
            self.partition_plan_graph_name,
            "partition_plan_graph_name",
        )
        _validate_alignment_text(
            self.execution_trace_graph_name,
            "execution_trace_graph_name",
        )
        _validate_text_sequence(self.hs_ir_backend_sequence, "hs_ir_backend_sequence")
        _validate_text_sequence(
            self.partition_backend_sequence,
            "partition_backend_sequence",
        )
        _validate_text_sequence(
            self.execution_trace_backend_sequence,
            "execution_trace_backend_sequence",
        )
        _validate_non_negative_int(
            self.hs_ir_transfer_edge_count,
            "hs_ir_transfer_edge_count",
        )
        _validate_non_negative_int(
            self.partition_transfer_edge_count,
            "partition_transfer_edge_count",
        )
        _validate_non_negative_int(
            self.hs_ir_total_transfer_bytes,
            "hs_ir_total_transfer_bytes",
        )
        _validate_non_negative_int(
            self.partition_total_transfer_bytes,
            "partition_total_transfer_bytes",
        )
        _validate_non_negative_int(
            self.hs_ir_layout_conversion_count,
            "hs_ir_layout_conversion_count",
        )
        _validate_non_negative_int(
            self.partition_layout_conversion_count,
            "partition_layout_conversion_count",
        )
        _validate_non_negative_int(
            self.hs_ir_total_layout_conversion_bytes,
            "hs_ir_total_layout_conversion_bytes",
        )
        _validate_non_negative_int(
            self.partition_total_layout_conversion_bytes,
            "partition_total_layout_conversion_bytes",
        )
        _validate_non_negative_int(
            self.hs_ir_total_data_movement_bytes,
            "hs_ir_total_data_movement_bytes",
        )
        _validate_non_negative_int(
            self.partition_total_data_movement_bytes,
            "partition_total_data_movement_bytes",
        )
        if self.alignment_contract != RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT:
            raise ValueError("runtime HS-IR plan alignment contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime HS-IR plan alignment executor contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("runtime HS-IR plan alignment trusted registry mismatch")
        if self.artifact_status != RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS:
            raise ValueError("runtime HS-IR plan alignment artifact status mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime HS-IR plan alignment must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime HS-IR plan alignment blocked surfaces changed")
        _validate_steps(self.steps)
        _validate_issues(self.issues)
        expected_issues = _derive_issues(self)
        if self.issues != expected_issues:
            raise ValueError("runtime HS-IR plan alignment issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether HS-IR, plan, and trace align."""

        return not self.issues

    @property
    def step_count(self) -> int:
        """Return the number of checked operations."""

        return len(self.steps)

    @property
    def alignment_metadata_digest(self) -> str:
        """Return a digest over alignment metadata only."""

        payload = {
            "execution_trace_backend_sequence": list(
                self.execution_trace_backend_sequence
            ),
            "graph_name": self.graph_name,
            "hs_ir_backend_sequence": list(self.hs_ir_backend_sequence),
            "partition_backend_sequence": list(self.partition_backend_sequence),
            "steps": [
                {
                    "execution_trace_backend": step.execution_trace_backend,
                    "hs_ir_backend": step.hs_ir_backend,
                    "hs_ir_produced_layout": step.hs_ir_produced_layout,
                    "layout_conversion_bytes": step.layout_conversion_bytes,
                    "operation_kind": step.operation_kind,
                    "operation_name": step.operation_name,
                    "partition_backend": step.partition_backend,
                    "partition_produced_layout": step.partition_produced_layout,
                    "transfer_bytes": step.transfer_bytes,
                    "trusted_executor_status": step.trusted_executor_status,
                }
                for step in self.steps
            ],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeHsIrPlanAlignmentError(AssertionError):
    """Raised when HS-IR/runtime-plan alignment evidence fails."""


def build_runtime_hs_ir_plan_alignment_report(
    hs_ir: IRModule,
    partition_plan: PartitionPlan,
    execution: RuntimeExecutionResult,
) -> RuntimeHsIrPlanAlignmentReport:
    """Build data-only evidence that HS-IR, PartitionPlan, and trace align."""

    if not isinstance(hs_ir, IRModule):
        raise TypeError("runtime HS-IR plan alignment requires an IRModule")
    if hs_ir.stage is not IRStage.HS_IR:
        raise ValueError("runtime HS-IR plan alignment requires HS-IR")
    if not isinstance(partition_plan, PartitionPlan):
        raise TypeError("runtime HS-IR plan alignment requires PartitionPlan")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("runtime HS-IR plan alignment requires RuntimeExecutionResult")
    validate_hs_module_contract(hs_ir)

    assignments = {
        assignment.operation_name: assignment
        for assignment in partition_plan.assignments
    }
    trace_steps = {
        step.operation_name: step
        for step in execution.trace.steps
    }
    steps = tuple(
        _build_step(
            operation,
            assignments.get(operation.name),
            trace_steps.get(operation.name),
        )
        for operation in hs_ir.graph.operations
    )
    summary = _runtime_transfer_summary(hs_ir.graph.metadata)
    hs_ir_backend_sequence = tuple(step.hs_ir_backend for step in steps)
    partition_backend_sequence = tuple(step.partition_backend for step in steps)
    execution_trace_backend_sequence = tuple(
        step.execution_trace_backend for step in steps
    )
    hs_ir_transfer_edge_count = _summary_int(summary, "transfer_edge_count")
    partition_transfer_edge_count = len(partition_plan.transfer_edges)
    hs_ir_total_transfer_bytes = _summary_int(summary, "total_transfer_bytes")
    partition_total_transfer_bytes = partition_plan.total_transfer_bytes()
    hs_ir_layout_conversion_count = _summary_int(summary, "layout_conversion_count")
    partition_layout_conversion_count = len(partition_plan.layout_conversions)
    hs_ir_total_layout_conversion_bytes = _summary_int(
        summary,
        "total_layout_conversion_bytes",
    )
    partition_total_layout_conversion_bytes = (
        partition_plan.total_layout_conversion_bytes()
    )
    hs_ir_total_data_movement_bytes = _summary_int(
        summary,
        "total_data_movement_bytes",
    )
    partition_total_data_movement_bytes = partition_plan.total_data_movement_bytes()
    return RuntimeHsIrPlanAlignmentReport(
        graph_name=hs_ir.graph.name,
        partition_plan_graph_name=partition_plan.graph_name,
        execution_trace_graph_name=execution.trace.graph_name,
        hs_ir_backend_sequence=hs_ir_backend_sequence,
        partition_backend_sequence=partition_backend_sequence,
        execution_trace_backend_sequence=execution_trace_backend_sequence,
        hs_ir_transfer_edge_count=hs_ir_transfer_edge_count,
        partition_transfer_edge_count=partition_transfer_edge_count,
        hs_ir_total_transfer_bytes=hs_ir_total_transfer_bytes,
        partition_total_transfer_bytes=partition_total_transfer_bytes,
        hs_ir_layout_conversion_count=hs_ir_layout_conversion_count,
        partition_layout_conversion_count=partition_layout_conversion_count,
        hs_ir_total_layout_conversion_bytes=hs_ir_total_layout_conversion_bytes,
        partition_total_layout_conversion_bytes=(
            partition_total_layout_conversion_bytes
        ),
        hs_ir_total_data_movement_bytes=hs_ir_total_data_movement_bytes,
        partition_total_data_movement_bytes=partition_total_data_movement_bytes,
        steps=steps,
        issues=_derive_issues_from_values(
            graph_name=hs_ir.graph.name,
            partition_plan_graph_name=partition_plan.graph_name,
            execution_trace_graph_name=execution.trace.graph_name,
            hs_ir_backend_sequence=hs_ir_backend_sequence,
            partition_backend_sequence=partition_backend_sequence,
            execution_trace_backend_sequence=execution_trace_backend_sequence,
            hs_ir_transfer_edge_count=hs_ir_transfer_edge_count,
            partition_transfer_edge_count=partition_transfer_edge_count,
            hs_ir_total_transfer_bytes=hs_ir_total_transfer_bytes,
            partition_total_transfer_bytes=partition_total_transfer_bytes,
            hs_ir_layout_conversion_count=hs_ir_layout_conversion_count,
            partition_layout_conversion_count=partition_layout_conversion_count,
            hs_ir_total_layout_conversion_bytes=hs_ir_total_layout_conversion_bytes,
            partition_total_layout_conversion_bytes=(
                partition_total_layout_conversion_bytes
            ),
            hs_ir_total_data_movement_bytes=hs_ir_total_data_movement_bytes,
            partition_total_data_movement_bytes=partition_total_data_movement_bytes,
            steps=steps,
        ),
    )


def assert_runtime_hs_ir_plan_alignment(
    report: RuntimeHsIrPlanAlignmentReport,
) -> RuntimeHsIrPlanAlignmentReport:
    """Return the report or raise when HS-IR/runtime-plan alignment fails."""

    if not isinstance(report, RuntimeHsIrPlanAlignmentReport):
        raise TypeError("runtime HS-IR plan alignment report required")
    if report.issues:
        lines = [f"runtime HS-IR plan alignment failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeHsIrPlanAlignmentError("\n".join(lines))
    return report


def runtime_hs_ir_plan_alignment_report_to_dict(
    report: RuntimeHsIrPlanAlignmentReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible HS-IR plan alignment evidence."""

    if not isinstance(report, RuntimeHsIrPlanAlignmentReport):
        raise TypeError("runtime HS-IR plan alignment report required")
    return {
        "alignment_contract": report.alignment_contract,
        "alignment_metadata_digest": report.alignment_metadata_digest,
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "execution_trace_backend_sequence": list(
            report.execution_trace_backend_sequence
        ),
        "execution_trace_graph_name": report.execution_trace_graph_name,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "hs_ir_backend_sequence": list(report.hs_ir_backend_sequence),
        "hs_ir_layout_conversion_count": report.hs_ir_layout_conversion_count,
        "hs_ir_total_data_movement_bytes": report.hs_ir_total_data_movement_bytes,
        "hs_ir_total_layout_conversion_bytes": (
            report.hs_ir_total_layout_conversion_bytes
        ),
        "hs_ir_total_transfer_bytes": report.hs_ir_total_transfer_bytes,
        "hs_ir_transfer_edge_count": report.hs_ir_transfer_edge_count,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "partition_backend_sequence": list(report.partition_backend_sequence),
        "partition_layout_conversion_count": report.partition_layout_conversion_count,
        "partition_plan_graph_name": report.partition_plan_graph_name,
        "partition_total_data_movement_bytes": (
            report.partition_total_data_movement_bytes
        ),
        "partition_total_layout_conversion_bytes": (
            report.partition_total_layout_conversion_bytes
        ),
        "partition_total_transfer_bytes": report.partition_total_transfer_bytes,
        "partition_transfer_edge_count": report.partition_transfer_edge_count,
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "schema_version": RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION,
        "step_count": report.step_count,
        "steps": [
            {
                "alignment_status": step.alignment_status,
                "execution_trace_backend": step.execution_trace_backend,
                "hs_ir_backend": step.hs_ir_backend,
                "hs_ir_produced_layout": step.hs_ir_produced_layout,
                "layout_conversion_bytes": step.layout_conversion_bytes,
                "operation_kind": step.operation_kind,
                "operation_name": step.operation_name,
                "partition_backend": step.partition_backend,
                "partition_produced_layout": step.partition_produced_layout,
                "transfer_bytes": step.transfer_bytes,
                "trusted_executor_status": step.trusted_executor_status,
            }
            for step in report.steps
        ],
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_hs_ir_plan_alignment_report(
    report: RuntimeHsIrPlanAlignmentReport,
) -> str:
    """Render stable data-only HS-IR/runtime-plan alignment evidence."""

    text = json.dumps(
        runtime_hs_ir_plan_alignment_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_BYTES:
        raise ValueError("runtime HS-IR plan alignment report exceeds byte limit")
    return text + "\n"


def _build_step(
    operation: ComputeOperation,
    assignment: Assignment | None,
    trace_step: RuntimeExecutionStep | None,
) -> RuntimeHsIrPlanAlignmentStep:
    operation_name = operation.name
    operation_kind = operation.kind.value
    attributes = operation.attributes
    hs_ir_backend = str(attributes.get("tuc.assigned_backend", "missing"))
    hs_ir_layout = str(attributes.get("tuc.produced_layout", "missing"))
    partition_backend = assignment.backend_name if assignment is not None else "missing"
    partition_layout = (
        assignment.produced_layout.value if assignment is not None else "missing"
    )
    trace_backend = (
        trace_step.planned_backend if trace_step is not None else "missing"
    )
    trusted_status = _trusted_executor_status(partition_backend, operation_kind)
    partial = RuntimeHsIrPlanAlignmentStep(
        operation_name=operation_name,
        operation_kind=operation_kind,
        hs_ir_backend=hs_ir_backend,
        partition_backend=partition_backend,
        execution_trace_backend=trace_backend,
        hs_ir_produced_layout=hs_ir_layout,
        partition_produced_layout=partition_layout,
        transfer_bytes=assignment.transfer_bytes if assignment is not None else 0,
        layout_conversion_bytes=(
            assignment.layout_conversion_bytes if assignment is not None else 0
        ),
        trusted_executor_status=trusted_status,
        alignment_status="failed",
    )
    return RuntimeHsIrPlanAlignmentStep(
        operation_name=partial.operation_name,
        operation_kind=partial.operation_kind,
        hs_ir_backend=partial.hs_ir_backend,
        partition_backend=partial.partition_backend,
        execution_trace_backend=partial.execution_trace_backend,
        hs_ir_produced_layout=partial.hs_ir_produced_layout,
        partition_produced_layout=partial.partition_produced_layout,
        transfer_bytes=partial.transfer_bytes,
        layout_conversion_bytes=partial.layout_conversion_bytes,
        trusted_executor_status=partial.trusted_executor_status,
        alignment_status="failed" if _step_issue_codes(partial) else "aligned",
    )


def _trusted_executor_status(partition_backend: str, operation_kind: str) -> str:
    registry = trusted_runtime_executor_registry()
    executor = registry.get(partition_backend)
    if executor is None:
        return "backend_missing"
    if operation_kind not in {kind.value for kind in executor.supported_ops}:
        return "operation_unsupported"
    return "trusted"


def _runtime_transfer_summary(metadata: Mapping[str, object]) -> Mapping[str, object]:
    value = metadata.get("runtime_transfer_summary")
    if not isinstance(value, Mapping):
        raise TypeError("HS-IR runtime_transfer_summary must be mapping")
    return value


def _summary_int(summary: Mapping[str, object], key: str) -> int:
    value = summary.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"HS-IR runtime_transfer_summary.{key} must be an integer")
    if value < 0:
        raise ValueError(f"HS-IR runtime_transfer_summary.{key} must be non-negative")
    return value


def _derive_issues(
    report: RuntimeHsIrPlanAlignmentReport,
) -> tuple[RuntimeHsIrPlanAlignmentIssue, ...]:
    return _derive_issues_from_values(
        graph_name=report.graph_name,
        partition_plan_graph_name=report.partition_plan_graph_name,
        execution_trace_graph_name=report.execution_trace_graph_name,
        hs_ir_backend_sequence=report.hs_ir_backend_sequence,
        partition_backend_sequence=report.partition_backend_sequence,
        execution_trace_backend_sequence=report.execution_trace_backend_sequence,
        hs_ir_transfer_edge_count=report.hs_ir_transfer_edge_count,
        partition_transfer_edge_count=report.partition_transfer_edge_count,
        hs_ir_total_transfer_bytes=report.hs_ir_total_transfer_bytes,
        partition_total_transfer_bytes=report.partition_total_transfer_bytes,
        hs_ir_layout_conversion_count=report.hs_ir_layout_conversion_count,
        partition_layout_conversion_count=report.partition_layout_conversion_count,
        hs_ir_total_layout_conversion_bytes=report.hs_ir_total_layout_conversion_bytes,
        partition_total_layout_conversion_bytes=(
            report.partition_total_layout_conversion_bytes
        ),
        hs_ir_total_data_movement_bytes=report.hs_ir_total_data_movement_bytes,
        partition_total_data_movement_bytes=report.partition_total_data_movement_bytes,
        steps=report.steps,
    )


def _derive_issues_from_values(
    *,
    graph_name: str,
    partition_plan_graph_name: str,
    execution_trace_graph_name: str,
    hs_ir_backend_sequence: tuple[str, ...],
    partition_backend_sequence: tuple[str, ...],
    execution_trace_backend_sequence: tuple[str, ...],
    hs_ir_transfer_edge_count: int,
    partition_transfer_edge_count: int,
    hs_ir_total_transfer_bytes: int,
    partition_total_transfer_bytes: int,
    hs_ir_layout_conversion_count: int,
    partition_layout_conversion_count: int,
    hs_ir_total_layout_conversion_bytes: int,
    partition_total_layout_conversion_bytes: int,
    hs_ir_total_data_movement_bytes: int,
    partition_total_data_movement_bytes: int,
    steps: tuple[RuntimeHsIrPlanAlignmentStep, ...],
) -> tuple[RuntimeHsIrPlanAlignmentIssue, ...]:
    issues: list[RuntimeHsIrPlanAlignmentIssue] = []
    if graph_name != partition_plan_graph_name:
        issues.append(_issue("graph", "partition_plan_graph_mismatch"))
    if graph_name != execution_trace_graph_name:
        issues.append(_issue("graph", "execution_trace_graph_mismatch"))
    if hs_ir_backend_sequence != partition_backend_sequence:
        issues.append(_issue("backend_sequence", "hs_ir_partition_backend_mismatch"))
    if partition_backend_sequence != execution_trace_backend_sequence:
        issues.append(_issue("backend_sequence", "partition_trace_backend_mismatch"))
    if hs_ir_transfer_edge_count != partition_transfer_edge_count:
        issues.append(_issue("runtime_transfer_summary", "transfer_edge_count_mismatch"))
    if hs_ir_total_transfer_bytes != partition_total_transfer_bytes:
        issues.append(_issue("runtime_transfer_summary", "transfer_bytes_mismatch"))
    if hs_ir_layout_conversion_count != partition_layout_conversion_count:
        issues.append(
            _issue("runtime_transfer_summary", "layout_conversion_count_mismatch")
        )
    if (
        hs_ir_total_layout_conversion_bytes
        != partition_total_layout_conversion_bytes
    ):
        issues.append(
            _issue("runtime_transfer_summary", "layout_conversion_bytes_mismatch")
        )
    if hs_ir_total_data_movement_bytes != partition_total_data_movement_bytes:
        issues.append(
            _issue("runtime_transfer_summary", "data_movement_bytes_mismatch")
        )
    for step in steps:
        issues.extend(_issue(step.operation_name, code) for code in _step_issue_codes(step))
    if len(issues) > MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_ISSUES:
        raise ValueError("runtime HS-IR plan alignment issue count exceeds limit")
    return tuple(dict.fromkeys(issues))


def _step_issue_codes(step: RuntimeHsIrPlanAlignmentStep) -> tuple[str, ...]:
    issues: list[str] = []
    if step.partition_backend == "missing":
        issues.append("partition_assignment_missing")
    if step.execution_trace_backend == "missing":
        issues.append("execution_trace_step_missing")
    if step.hs_ir_backend != step.partition_backend:
        issues.append("hs_ir_partition_backend_mismatch")
    if step.partition_backend != step.execution_trace_backend:
        issues.append("partition_trace_backend_mismatch")
    if step.hs_ir_produced_layout != step.partition_produced_layout:
        issues.append("produced_layout_mismatch")
    if step.trusted_executor_status != "trusted":
        issues.append(step.trusted_executor_status)
    return tuple(issues)


def _issue(subject: str, issue_code: str) -> RuntimeHsIrPlanAlignmentIssue:
    return RuntimeHsIrPlanAlignmentIssue(subject=subject, issue_code=issue_code)


def _validate_steps(steps: tuple[RuntimeHsIrPlanAlignmentStep, ...]) -> None:
    if type(steps) is not tuple:
        raise TypeError("runtime HS-IR plan alignment steps must be a tuple")
    if not steps:
        raise ValueError("runtime HS-IR plan alignment requires steps")
    if len(steps) > MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_STEPS:
        raise ValueError("runtime HS-IR plan alignment step count exceeds limit")
    for step in steps:
        if not isinstance(step, RuntimeHsIrPlanAlignmentStep):
            raise TypeError("runtime HS-IR plan alignment steps must be step objects")
        if (step.alignment_status == "aligned") != (not _step_issue_codes(step)):
            raise ValueError("runtime HS-IR plan alignment step status mismatch")


def _validate_issues(issues: tuple[RuntimeHsIrPlanAlignmentIssue, ...]) -> None:
    if type(issues) is not tuple:
        raise TypeError("runtime HS-IR plan alignment issues must be a tuple")
    if len(issues) > MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_ISSUES:
        raise ValueError("runtime HS-IR plan alignment issue count exceeds limit")
    for issue in issues:
        if not isinstance(issue, RuntimeHsIrPlanAlignmentIssue):
            raise TypeError("runtime HS-IR plan alignment issues must be issue objects")


def _validate_alignment_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ALIGNMENT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime alignment identifier")
    if value in _FORBIDDEN_ALIGNMENT_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")
    if len(value.encode("utf-8")) > MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime alignment field limit")


def _validate_text_sequence(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    if not values:
        raise ValueError(f"{label} must not be empty")
    for value in values:
        _validate_alignment_text(value, label)


def _validate_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


__all__ = [
    "MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_FIELD_BYTES",
    "MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_ISSUES",
    "MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_BYTES",
    "MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_STEPS",
    "RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS",
    "RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT",
    "RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION",
    "RuntimeHsIrPlanAlignmentError",
    "RuntimeHsIrPlanAlignmentIssue",
    "RuntimeHsIrPlanAlignmentReport",
    "RuntimeHsIrPlanAlignmentStep",
    "assert_runtime_hs_ir_plan_alignment",
    "build_runtime_hs_ir_plan_alignment_report",
    "dump_runtime_hs_ir_plan_alignment_report",
    "runtime_hs_ir_plan_alignment_report_to_dict",
]
