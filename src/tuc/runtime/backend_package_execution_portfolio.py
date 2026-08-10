"""Multi-package trusted execution portfolio for heterogeneous proof graphs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256

from tuc.backends.base import BackendCapability
from tuc.ir.memory import LayoutKind
from tuc.ir.model import ComputeGraph, OperationKind
from tuc.runtime.backend_equivalence import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RuntimeBackendEquivalenceReport,
    assert_runtime_backend_equivalence,
)
from tuc.runtime.backend_package_execution import (
    BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
    BACKEND_PACKAGE_EXECUTION_MODE,
    BackendPackageExecutionAdmissionReport,
    trusted_backend_package_execution_bindings,
)
from tuc.runtime.dump import dump_partition_plan
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeExecutionResult,
    RuntimeValueRecord,
    execute_graph,
    runtime_execution_readiness_report,
)
from tuc.runtime.partitioning import PartitionPlan, partition_graph

BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_SCHEMA_VERSION = (
    "tuc.backend_package_execution_portfolio_report.v0"
)
BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT = (
    "backend_package_execution_portfolio.trusted_projection.v0"
)
BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY = (
    "all_assignments_package_bound_no_fallback"
)
BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_PASS = "PASS"
BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_BLOCKED = "BLOCKED"
BACKEND_PACKAGE_EXECUTION_PORTFOLIO_RAW_VALUE_POLICY = "omitted_by_policy"
BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REQUIRED_PACKAGE_IDS = frozenset(
    {
        "external-systolic-reference-package",
        "external-vector-reference-package",
    }
)
MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_ENTRIES = 16
MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_ISSUES = 64
MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_BYTES = 64 * 1024

_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ISSUE_CODES = frozenset(
    {
        "duplicate_binding_id",
        "duplicate_package_backend",
        "duplicate_package_id",
        "duplicate_trusted_executor",
        "overlapping_operation_scope",
        "package_admission_blocked",
        "portfolio_too_small",
        "required_package_set_mismatch",
    }
)


class BackendPackageExecutionPortfolioError(ValueError):
    """Raised when multi-package trusted execution cannot be admitted."""


@dataclass(frozen=True)
class BackendPackageExecutionPortfolioEntry:
    """One admitted package-to-executor identity in a portfolio."""

    package_id: str
    package_digest: str
    capability_manifest_digest: str
    package_backend_name: str
    binding_id: str
    trusted_executor_backend: str
    trusted_executor_contract_digest: str
    allowed_operations: tuple[OperationKind, ...]
    package_admission_status: str
    projection_execution_allowed: bool

    def __post_init__(self) -> None:
        for value, label in (
            (self.package_id, "package_id"),
            (self.package_backend_name, "package_backend_name"),
            (self.binding_id, "binding_id"),
            (self.trusted_executor_backend, "trusted_executor_backend"),
            (self.package_admission_status, "package_admission_status"),
        ):
            _validate_text(value, label)
        _validate_digest(self.package_digest, "package_digest")
        _validate_digest(
            self.capability_manifest_digest,
            "capability_manifest_digest",
        )
        _validate_digest(
            self.trusted_executor_contract_digest,
            "trusted_executor_contract_digest",
        )
        _validate_operation_tuple(self.allowed_operations, "allowed_operations")
        if not self.allowed_operations:
            raise ValueError("portfolio entry requires allowed operation")
        if type(self.projection_execution_allowed) is not bool:
            raise TypeError("portfolio entry projection flag must be bool")


@dataclass(frozen=True)
class BackendPackageExecutionPortfolioIssue:
    """One deterministic portfolio-admission issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "portfolio issue subject")
        _validate_text(self.issue_code, "portfolio issue code")
        if self.issue_code not in _ISSUE_CODES:
            raise ValueError("portfolio issue code unsupported")


@dataclass(frozen=True)
class BackendPackageExecutionPortfolioAdmission:
    """Admission result for an exact heterogeneous package set."""

    entries: tuple[BackendPackageExecutionPortfolioEntry, ...]
    issues: tuple[BackendPackageExecutionPortfolioIssue, ...]
    portfolio_contract: str = BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT
    portfolio_policy: str = BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY
    package_admission_contract: str = BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT
    execution_mode: str = BACKEND_PACKAGE_EXECUTION_MODE
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    external_plugin_execution: bool = False
    package_backend_implementation_executed: bool = False
    physical_device_execution: bool = False
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.portfolio_contract != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT:
            raise ValueError("backend package portfolio contract mismatch")
        if self.portfolio_policy != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY:
            raise ValueError("backend package portfolio policy mismatch")
        if self.package_admission_contract != BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT:
            raise ValueError("backend package portfolio admission contract mismatch")
        if self.execution_mode != BACKEND_PACKAGE_EXECUTION_MODE:
            raise ValueError("backend package portfolio execution mode mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("backend package portfolio registry mismatch")
        for flag_name in (
            "external_plugin_execution",
            "package_backend_implementation_executed",
            "physical_device_execution",
        ):
            if type(getattr(self, flag_name)) is not bool or getattr(self, flag_name):
                raise ValueError(f"{flag_name} must remain false")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend package portfolio blocked surfaces changed")
        if type(self.entries) is not tuple:
            raise TypeError("backend package portfolio entries must be tuple")
        if len(self.entries) > MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_ENTRIES:
            raise ValueError("backend package portfolio entry count exceeds limit")
        for entry in self.entries:
            if not isinstance(entry, BackendPackageExecutionPortfolioEntry):
                raise TypeError("backend package portfolio entries must be entry objects")
        if type(self.issues) is not tuple:
            raise TypeError("backend package portfolio issues must be tuple")
        if len(self.issues) > MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_ISSUES:
            raise ValueError("backend package portfolio issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPackageExecutionPortfolioIssue):
                raise TypeError("backend package portfolio issues must be issue objects")
        if self.issues != _derive_portfolio_issues(self.entries):
            raise ValueError("backend package portfolio issues must be derived")

    @property
    def admitted(self) -> bool:
        """Return whether the exact package portfolio is admitted."""

        return not self.issues

    @property
    def portfolio_status(self) -> str:
        """Return stable PASS or BLOCKED status."""

        if self.admitted:
            return BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_PASS
        return BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_BLOCKED

    @property
    def admission_digest(self) -> str:
        """Return a digest over ordered source-free admission metadata."""

        payload = [
            {
                "allowed_operations": [item.value for item in entry.allowed_operations],
                "binding_id": entry.binding_id,
                "capability_manifest_digest": entry.capability_manifest_digest,
                "package_backend_name": entry.package_backend_name,
                "package_digest": entry.package_digest,
                "package_id": entry.package_id,
                "trusted_executor_backend": entry.trusted_executor_backend,
                "trusted_executor_contract_digest": (
                    entry.trusted_executor_contract_digest
                ),
            }
            for entry in self.entries
        ]
        return _digest_json(payload)


@dataclass(frozen=True)
class AdmittedBackendPackagePortfolioExecution:
    """Internal result retaining source and projected multi-package plans."""

    admission: BackendPackageExecutionPortfolioAdmission
    source_partition_plan: PartitionPlan
    projected_partition_plan: PartitionPlan
    execution: RuntimeExecutionResult

    def __post_init__(self) -> None:
        assert_backend_package_execution_portfolio(self.admission)
        if not isinstance(self.source_partition_plan, PartitionPlan):
            raise TypeError("portfolio source plan must be PartitionPlan")
        if not isinstance(self.projected_partition_plan, PartitionPlan):
            raise TypeError("portfolio projected plan must be PartitionPlan")
        if not isinstance(self.execution, RuntimeExecutionResult):
            raise TypeError("portfolio execution must be RuntimeExecutionResult")
        projected_sequence = tuple(
            assignment.backend_name
            for assignment in self.projected_partition_plan.assignments
        )
        trace_sequence = tuple(
            step.planned_backend for step in self.execution.trace.steps
        )
        if projected_sequence != trace_sequence:
            raise ValueError("portfolio execution trace does not match projected plan")


@dataclass(frozen=True)
class BackendPackageExecutionPortfolioLayoutConversion:
    """Metadata-only layout conversion retained by the projected plan."""

    tensor_name: str
    target_operation: str
    source_layout: LayoutKind
    target_layout: LayoutKind
    bytes_converted: int

    def __post_init__(self) -> None:
        _validate_text(self.tensor_name, "layout conversion tensor_name")
        _validate_text(self.target_operation, "layout conversion target_operation")
        if not isinstance(self.source_layout, LayoutKind):
            raise TypeError("portfolio source layout must be LayoutKind")
        if not isinstance(self.target_layout, LayoutKind):
            raise TypeError("portfolio target layout must be LayoutKind")
        if self.source_layout is self.target_layout:
            raise ValueError("portfolio layout conversion requires distinct layouts")
        _validate_positive_int(self.bytes_converted, "layout conversion bytes")


@dataclass(frozen=True)
class BackendPackageExecutionPortfolioReport:
    """Reviewable multi-package planning, execution, and equivalence proof."""

    entries: tuple[BackendPackageExecutionPortfolioEntry, ...]
    portfolio_admission_digest: str
    graph_name: str
    source_plan_digest: str
    projected_plan_digest: str
    source_backend_sequence: tuple[str, ...]
    projected_backend_sequence: tuple[str, ...]
    package_backend_count: int
    trusted_executor_count: int
    fallback_assignment_count: int
    projected_operation_count: int
    transfer_edge_count: int
    layout_conversions: tuple[BackendPackageExecutionPortfolioLayoutConversion, ...]
    execution_step_count: int
    output_tensor_names: tuple[str, ...]
    output_shapes: tuple[tuple[int, ...], ...]
    output_dtypes: tuple[str, ...]
    equivalence_comparison_metadata_digest: str
    equivalence_passed: bool
    portfolio_contract: str = BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT
    portfolio_policy: str = BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY
    portfolio_status: str = BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_PASS
    package_admission_contract: str = BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT
    execution_mode: str = BACKEND_PACKAGE_EXECUTION_MODE
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    equivalence_contract: str = RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    source_all_assignments_package_bound: bool = True
    raw_tensor_value_policy: str = BACKEND_PACKAGE_EXECUTION_PORTFOLIO_RAW_VALUE_POLICY
    external_plugin_execution: bool = False
    package_backend_implementation_executed: bool = False
    physical_device_execution: bool = False
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if type(self.entries) is not tuple or len(self.entries) < 2:
            raise ValueError("portfolio proof requires at least two package entries")
        for entry in self.entries:
            if not isinstance(entry, BackendPackageExecutionPortfolioEntry):
                raise TypeError("portfolio proof entries must be entry objects")
            if not entry.projection_execution_allowed:
                raise ValueError("portfolio proof entries must be admitted")
        for text_value, label in (
            (self.graph_name, "graph_name"),
            (self.portfolio_status, "portfolio_status"),
        ):
            _validate_text(text_value, label)
        for value, label in (
            (self.portfolio_admission_digest, "portfolio_admission_digest"),
            (self.source_plan_digest, "source_plan_digest"),
            (self.projected_plan_digest, "projected_plan_digest"),
            (
                self.equivalence_comparison_metadata_digest,
                "equivalence_comparison_metadata_digest",
            ),
        ):
            _validate_digest(value, label)
        _validate_text_tuple(self.source_backend_sequence, "source_backend_sequence")
        _validate_text_tuple(
            self.projected_backend_sequence,
            "projected_backend_sequence",
        )
        for count_value, label in (
            (self.package_backend_count, "package_backend_count"),
            (self.trusted_executor_count, "trusted_executor_count"),
            (self.projected_operation_count, "projected_operation_count"),
            (self.execution_step_count, "execution_step_count"),
        ):
            _validate_positive_int(count_value, label)
        _validate_non_negative_int(
            self.fallback_assignment_count,
            "fallback_assignment_count",
        )
        _validate_non_negative_int(self.transfer_edge_count, "transfer_edge_count")
        if self.fallback_assignment_count != 0:
            raise ValueError("portfolio candidate proof must contain no fallback")
        if self.projected_operation_count != len(self.source_backend_sequence):
            raise ValueError("portfolio projection count must match source sequence")
        if self.execution_step_count != len(self.projected_backend_sequence):
            raise ValueError("portfolio execution count must match projected sequence")
        if type(self.layout_conversions) is not tuple or not self.layout_conversions:
            raise ValueError("portfolio proof requires layout conversion evidence")
        for conversion in self.layout_conversions:
            if not isinstance(
                conversion,
                BackendPackageExecutionPortfolioLayoutConversion,
            ):
                raise TypeError("portfolio layout conversions must be evidence objects")
        _validate_text_tuple(self.output_tensor_names, "output_tensor_names")
        _validate_text_tuple(self.output_dtypes, "output_dtypes")
        if len(self.output_shapes) != len(self.output_tensor_names):
            raise ValueError("portfolio output shapes must match names")
        if len(self.output_dtypes) != len(self.output_tensor_names):
            raise ValueError("portfolio output dtypes must match names")
        _validate_shapes(self.output_shapes)
        if type(self.equivalence_passed) is not bool or not self.equivalence_passed:
            raise ValueError("portfolio proof requires backend equivalence")
        if self.portfolio_contract != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT:
            raise ValueError("portfolio proof contract mismatch")
        if self.portfolio_policy != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY:
            raise ValueError("portfolio proof policy mismatch")
        if self.portfolio_status != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_PASS:
            raise ValueError("portfolio proof status mismatch")
        if self.package_admission_contract != BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT:
            raise ValueError("portfolio proof package admission contract mismatch")
        if self.execution_mode != BACKEND_PACKAGE_EXECUTION_MODE:
            raise ValueError("portfolio proof execution mode mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("portfolio proof executor contract mismatch")
        if self.equivalence_contract != RUNTIME_BACKEND_EQUIVALENCE_CONTRACT:
            raise ValueError("portfolio proof equivalence contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("portfolio proof registry mismatch")
        if type(self.source_all_assignments_package_bound) is not bool:
            raise TypeError("source package-bound flag must be bool")
        if not self.source_all_assignments_package_bound:
            raise ValueError("portfolio source assignments must all be package-bound")
        if self.raw_tensor_value_policy != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_RAW_VALUE_POLICY:
            raise ValueError("portfolio proof must omit raw tensor values")
        for flag_name in (
            "external_plugin_execution",
            "package_backend_implementation_executed",
            "physical_device_execution",
        ):
            if type(getattr(self, flag_name)) is not bool or getattr(self, flag_name):
                raise ValueError(f"{flag_name} must remain false")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("portfolio proof blocked surfaces changed")
        source_names = {entry.package_backend_name for entry in self.entries}
        executor_names = {entry.trusted_executor_backend for entry in self.entries}
        if set(self.source_backend_sequence) != source_names:
            raise ValueError("portfolio source sequence must cover package backends")
        if set(self.projected_backend_sequence) != executor_names:
            raise ValueError("portfolio projected sequence must cover trusted executors")
        if source_names & set(self.projected_backend_sequence):
            raise ValueError("portfolio projection must remove package backend identities")


def build_backend_package_execution_portfolio_admission(
    reports: tuple[BackendPackageExecutionAdmissionReport, ...],
) -> BackendPackageExecutionPortfolioAdmission:
    """Compose exact single-package admissions into a heterogeneous portfolio."""

    if type(reports) is not tuple:
        raise TypeError("backend package portfolio reports must be tuple")
    if len(reports) > MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_ENTRIES:
        raise ValueError("backend package portfolio report count exceeds limit")
    entries = tuple(_entry_from_report(report) for report in reports)
    entries = tuple(sorted(entries, key=lambda entry: entry.package_id))
    return BackendPackageExecutionPortfolioAdmission(
        entries=entries,
        issues=_derive_portfolio_issues(entries),
    )


def assert_backend_package_execution_portfolio(
    admission: BackendPackageExecutionPortfolioAdmission,
) -> BackendPackageExecutionPortfolioAdmission:
    """Return an admitted portfolio or fail closed with structured reasons."""

    if not isinstance(admission, BackendPackageExecutionPortfolioAdmission):
        raise TypeError("backend package execution portfolio requires admission")
    if not admission.admitted:
        detail = ",".join(issue.issue_code for issue in admission.issues)
        raise BackendPackageExecutionPortfolioError(
            f"backend package execution portfolio blocked: {detail}"
        )
    return admission


def project_backend_package_execution_portfolio_plan(
    graph: ComputeGraph,
    source_plan: PartitionPlan,
    admission: BackendPackageExecutionPortfolioAdmission,
) -> PartitionPlan:
    """Project every package assignment onto its admitted trusted executor."""

    assert_backend_package_execution_portfolio(admission)
    if not isinstance(graph, ComputeGraph):
        raise TypeError("backend package portfolio graph must be ComputeGraph")
    if not isinstance(source_plan, PartitionPlan):
        raise TypeError("backend package portfolio source plan must be PartitionPlan")
    if graph.name != source_plan.graph_name:
        raise ValueError("backend package portfolio graph and plan names must match")
    operation_names = tuple(operation.name for operation in graph.operations)
    assignment_names = tuple(
        assignment.operation_name for assignment in source_plan.assignments
    )
    if operation_names != assignment_names:
        raise ValueError("backend package portfolio plan must match graph operations")
    if source_plan.override_effects:
        raise BackendPackageExecutionPortfolioError(
            "backend package portfolio does not admit runtime overrides"
        )
    if source_plan.candidate_scores:
        raise BackendPackageExecutionPortfolioError(
            "backend package portfolio does not admit candidate score payloads"
        )
    entries_by_backend = {
        entry.package_backend_name: entry for entry in admission.entries
    }
    operations = {operation.name: operation for operation in graph.operations}
    used_backends: set[str] = set()
    assignments = []
    for assignment in source_plan.assignments:
        entry = entries_by_backend.get(assignment.backend_name)
        if entry is None:
            raise BackendPackageExecutionPortfolioError(
                "backend package portfolio source plan contains fallback or unbound backend"
            )
        operation = operations[assignment.operation_name]
        if operation.kind not in entry.allowed_operations:
            raise BackendPackageExecutionPortfolioError(
                "backend package portfolio operation exceeds admitted package scope"
            )
        used_backends.add(entry.package_backend_name)
        assignments.append(
            replace(assignment, backend_name=entry.trusted_executor_backend)
        )
    if used_backends != set(entries_by_backend):
        raise BackendPackageExecutionPortfolioError(
            "backend package portfolio source plan does not use every admitted package"
        )
    _assert_canonical_source_plan(graph, source_plan, admission)
    projected_edges = tuple(
        replace(
            edge,
            source_backend=_project_backend_name(edge.source_backend, entries_by_backend),
            target_backend=_project_backend_name(edge.target_backend, entries_by_backend),
        )
        for edge in source_plan.transfer_edges
    )
    projected = PartitionPlan(
        graph_name=source_plan.graph_name,
        assignments=tuple(assignments),
        transfer_edges=projected_edges,
        layout_conversions=source_plan.layout_conversions,
    )
    runtime_execution_readiness_report(graph, projected)
    return projected


def execute_backend_package_execution_portfolio(
    graph: ComputeGraph,
    source_plan: PartitionPlan,
    inputs: Mapping[str, object],
    admission: BackendPackageExecutionPortfolioAdmission,
) -> AdmittedBackendPackagePortfolioExecution:
    """Execute a no-fallback package portfolio through trusted projection."""

    if type(inputs) is not dict:
        raise TypeError("backend package portfolio inputs must be plain mapping")
    projected = project_backend_package_execution_portfolio_plan(
        graph,
        source_plan,
        admission,
    )
    execution = execute_graph(graph, projected, inputs)
    return AdmittedBackendPackagePortfolioExecution(
        admission=admission,
        source_partition_plan=source_plan,
        projected_partition_plan=projected,
        execution=execution,
    )


def build_backend_package_execution_portfolio_report(
    graph: ComputeGraph,
    portfolio_execution: AdmittedBackendPackagePortfolioExecution,
    equivalence_report: RuntimeBackendEquivalenceReport,
) -> BackendPackageExecutionPortfolioReport:
    """Build the source-free multi-package execution and equivalence proof."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("backend package portfolio proof graph must be ComputeGraph")
    if not isinstance(
        portfolio_execution,
        AdmittedBackendPackagePortfolioExecution,
    ):
        raise TypeError("backend package portfolio proof requires execution")
    assert_backend_package_execution_portfolio(portfolio_execution.admission)
    assert_runtime_backend_equivalence(equivalence_report)
    source_plan = portfolio_execution.source_partition_plan
    projected_plan = portfolio_execution.projected_partition_plan
    if graph.name != source_plan.graph_name or graph.name != equivalence_report.graph_name:
        raise ValueError("backend package portfolio proof graph mismatch")
    projected_sequence = tuple(
        assignment.backend_name for assignment in projected_plan.assignments
    )
    candidate_run = next(
        run
        for run in equivalence_report.runs
        if run.run_id == equivalence_report.candidate_run_id
    )
    if candidate_run.planned_backend_sequence != projected_sequence:
        raise ValueError("portfolio equivalence candidate does not match projection")
    terminal_records = _terminal_output_records(graph, portfolio_execution.execution)
    conversions = tuple(
        BackendPackageExecutionPortfolioLayoutConversion(
            tensor_name=item.tensor_name,
            target_operation=item.target_operation,
            source_layout=item.source_layout,
            target_layout=item.target_layout,
            bytes_converted=item.bytes_converted,
        )
        for item in projected_plan.layout_conversions
    )
    source_sequence = tuple(
        assignment.backend_name for assignment in source_plan.assignments
    )
    package_names = {
        entry.package_backend_name for entry in portfolio_execution.admission.entries
    }
    return BackendPackageExecutionPortfolioReport(
        entries=portfolio_execution.admission.entries,
        portfolio_admission_digest=portfolio_execution.admission.admission_digest,
        graph_name=graph.name,
        source_plan_digest=_partition_plan_digest(source_plan),
        projected_plan_digest=_partition_plan_digest(projected_plan),
        source_backend_sequence=source_sequence,
        projected_backend_sequence=projected_sequence,
        package_backend_count=len(set(source_sequence)),
        trusted_executor_count=len(set(projected_sequence)),
        fallback_assignment_count=sum(
            1 for backend_name in source_sequence if backend_name not in package_names
        ),
        projected_operation_count=len(source_plan.assignments),
        transfer_edge_count=len(projected_plan.transfer_edges),
        layout_conversions=conversions,
        execution_step_count=len(portfolio_execution.execution.trace.steps),
        output_tensor_names=tuple(record.tensor_name for record in terminal_records),
        output_shapes=tuple(record.shape for record in terminal_records),
        output_dtypes=tuple(record.dtype for record in terminal_records),
        equivalence_comparison_metadata_digest=(
            equivalence_report.comparison_metadata_digest
        ),
        equivalence_passed=equivalence_report.passed,
    )


def backend_package_execution_portfolio_report_to_dict(
    report: BackendPackageExecutionPortfolioReport,
) -> dict[str, object]:
    """Return deterministic proof metadata without source or tensor values."""

    if not isinstance(report, BackendPackageExecutionPortfolioReport):
        raise TypeError("backend package portfolio serialization requires report")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "entries": [
            {
                "allowed_operations": [item.value for item in entry.allowed_operations],
                "binding_id": entry.binding_id,
                "capability_manifest_digest": entry.capability_manifest_digest,
                "package_admission_status": entry.package_admission_status,
                "package_backend_name": entry.package_backend_name,
                "package_digest": entry.package_digest,
                "package_id": entry.package_id,
                "projection_execution_allowed": entry.projection_execution_allowed,
                "trusted_executor_backend": entry.trusted_executor_backend,
                "trusted_executor_contract_digest": (
                    entry.trusted_executor_contract_digest
                ),
            }
            for entry in report.entries
        ],
        "equivalence_comparison_metadata_digest": (
            report.equivalence_comparison_metadata_digest
        ),
        "equivalence_contract": report.equivalence_contract,
        "equivalence_passed": report.equivalence_passed,
        "execution_mode": report.execution_mode,
        "execution_step_count": report.execution_step_count,
        "executor_contract": report.executor_contract,
        "external_plugin_execution": report.external_plugin_execution,
        "fallback_assignment_count": report.fallback_assignment_count,
        "graph_name": report.graph_name,
        "layout_conversion_count": len(report.layout_conversions),
        "layout_conversions": [
            {
                "bytes_converted": item.bytes_converted,
                "source_layout": item.source_layout.value,
                "target_layout": item.target_layout.value,
                "target_operation": item.target_operation,
                "tensor_name": item.tensor_name,
            }
            for item in report.layout_conversions
        ],
        "output_dtypes": list(report.output_dtypes),
        "output_shapes": [list(shape) for shape in report.output_shapes],
        "output_tensor_names": list(report.output_tensor_names),
        "package_admission_contract": report.package_admission_contract,
        "package_backend_count": report.package_backend_count,
        "package_backend_implementation_executed": (
            report.package_backend_implementation_executed
        ),
        "physical_device_execution": report.physical_device_execution,
        "portfolio_admission_digest": report.portfolio_admission_digest,
        "portfolio_contract": report.portfolio_contract,
        "portfolio_policy": report.portfolio_policy,
        "portfolio_status": report.portfolio_status,
        "projected_backend_sequence": list(report.projected_backend_sequence),
        "projected_operation_count": report.projected_operation_count,
        "projected_plan_digest": report.projected_plan_digest,
        "raw_tensor_value_policy": report.raw_tensor_value_policy,
        "schema_version": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_SCHEMA_VERSION,
        "source_all_assignments_package_bound": (
            report.source_all_assignments_package_bound
        ),
        "source_backend_sequence": list(report.source_backend_sequence),
        "source_plan_digest": report.source_plan_digest,
        "transfer_edge_count": report.transfer_edge_count,
        "trusted_executor_count": report.trusted_executor_count,
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_backend_package_execution_portfolio_report(
    report: BackendPackageExecutionPortfolioReport,
) -> str:
    """Render bounded deterministic multi-package execution proof evidence."""

    text = json.dumps(
        backend_package_execution_portfolio_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_BYTES:
        raise ValueError("backend package portfolio report exceeds limit")
    return text + "\n"


def _entry_from_report(
    report: BackendPackageExecutionAdmissionReport,
) -> BackendPackageExecutionPortfolioEntry:
    if not isinstance(report, BackendPackageExecutionAdmissionReport):
        raise TypeError("backend package portfolio requires admission reports")
    return BackendPackageExecutionPortfolioEntry(
        package_id=report.package_id,
        package_digest=report.package_digest,
        capability_manifest_digest=report.capability_manifest_digest,
        package_backend_name=report.package_backend_name,
        binding_id=report.binding_id,
        trusted_executor_backend=report.trusted_executor_backend,
        trusted_executor_contract_digest=report.trusted_executor_contract_digest,
        allowed_operations=report.allowed_operations,
        package_admission_status=report.admission_status,
        projection_execution_allowed=report.projection_execution_allowed,
    )


def _derive_portfolio_issues(
    entries: tuple[BackendPackageExecutionPortfolioEntry, ...],
) -> tuple[BackendPackageExecutionPortfolioIssue, ...]:
    issues: list[BackendPackageExecutionPortfolioIssue] = []
    if len(entries) < 2:
        issues.append(_issue("portfolio", "portfolio_too_small"))
    package_ids = tuple(entry.package_id for entry in entries)
    if frozenset(package_ids) != BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REQUIRED_PACKAGE_IDS:
        issues.append(_issue("portfolio", "required_package_set_mismatch"))
    _append_duplicate_issues(
        issues,
        package_ids,
        "duplicate_package_id",
    )
    _append_duplicate_issues(
        issues,
        tuple(entry.package_backend_name for entry in entries),
        "duplicate_package_backend",
    )
    _append_duplicate_issues(
        issues,
        tuple(entry.binding_id for entry in entries),
        "duplicate_binding_id",
    )
    _append_duplicate_issues(
        issues,
        tuple(entry.trusted_executor_backend for entry in entries),
        "duplicate_trusted_executor",
    )
    for entry in entries:
        if not entry.projection_execution_allowed:
            issues.append(_issue(entry.package_id, "package_admission_blocked"))
    operations_seen: dict[OperationKind, str] = {}
    for entry in entries:
        for operation in entry.allowed_operations:
            previous = operations_seen.get(operation)
            if previous is not None:
                issues.append(_issue(operation.value, "overlapping_operation_scope"))
            else:
                operations_seen[operation] = entry.package_id
    return tuple(issues)


def _append_duplicate_issues(
    issues: list[BackendPackageExecutionPortfolioIssue],
    values: tuple[str, ...],
    issue_code: str,
) -> None:
    duplicates = sorted({value for value in values if values.count(value) > 1})
    issues.extend(_issue(value, issue_code) for value in duplicates)


def _assert_canonical_source_plan(
    graph: ComputeGraph,
    source_plan: PartitionPlan,
    admission: BackendPackageExecutionPortfolioAdmission,
) -> None:
    bindings = {
        binding.binding_id: binding
        for binding in trusted_backend_package_execution_bindings()
    }
    capabilities: list[BackendCapability] = []
    for entry in admission.entries:
        binding = bindings.get(entry.binding_id)
        if binding is None:
            raise BackendPackageExecutionPortfolioError(
                "backend package portfolio binding is no longer trusted"
            )
        capabilities.append(
            BackendCapability(
                name=binding.package_backend_name,
                supported_ops=frozenset(binding.allowed_operations),
                preferred_for=frozenset(binding.allowed_operations),
                memory_domain=binding.expected_memory_domain,
                supported_layouts=frozenset(binding.expected_supported_layouts),
                produced_layouts=frozenset(binding.expected_produced_layouts),
            )
        )
    expected = partition_graph(graph, tuple(capabilities))
    if source_plan != expected:
        raise BackendPackageExecutionPortfolioError(
            "backend package portfolio source plan is not canonical"
        )


def _project_backend_name(
    backend_name: str,
    entries_by_backend: Mapping[str, BackendPackageExecutionPortfolioEntry],
) -> str:
    entry = entries_by_backend.get(backend_name)
    if entry is None:
        raise BackendPackageExecutionPortfolioError(
            "backend package portfolio transfer references unbound backend"
        )
    return entry.trusted_executor_backend


def _terminal_output_records(
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
) -> tuple[RuntimeValueRecord, ...]:
    consumed = {
        tensor.name for operation in graph.operations for tensor in operation.inputs
    }
    terminal_names = tuple(
        tensor.name
        for operation in graph.operations
        for tensor in operation.outputs
        if tensor.name not in consumed
    )
    if not terminal_names:
        raise ValueError("backend package portfolio requires terminal output")
    return tuple(execution.record_for(name) for name in terminal_names)


def _partition_plan_digest(plan: PartitionPlan) -> str:
    return f"sha256:{sha256(dump_partition_plan(plan).encode('utf-8')).hexdigest()}"


def _digest_json(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


def _issue(subject: str, issue_code: str) -> BackendPackageExecutionPortfolioIssue:
    return BackendPackageExecutionPortfolioIssue(subject=subject, issue_code=issue_code)


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _TEXT_RE.fullmatch(value):
        raise ValueError(f"backend package portfolio {label} must be safe text")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"backend package portfolio {label} must be SHA-256")


def _validate_operation_tuple(
    values: tuple[OperationKind, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"backend package portfolio {label} must be tuple")
    if len(values) != len(set(values)):
        raise ValueError(f"backend package portfolio {label} must be unique")
    if any(not isinstance(value, OperationKind) for value in values):
        raise TypeError(f"backend package portfolio {label} must contain operations")


def _validate_text_tuple(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple or not values:
        raise TypeError(f"backend package portfolio {label} must be non-empty tuple")
    for value in values:
        _validate_text(value, label)


def _validate_positive_int(value: int, label: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"backend package portfolio {label} must be positive")


def _validate_non_negative_int(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"backend package portfolio {label} must be non-negative")


def _validate_shapes(shapes: tuple[tuple[int, ...], ...]) -> None:
    if type(shapes) is not tuple or not shapes:
        raise TypeError("backend package portfolio output shapes must be tuple")
    for shape in shapes:
        if type(shape) is not tuple or not shape:
            raise TypeError("backend package portfolio output shape must be tuple")
        for dimension in shape:
            if type(dimension) is not int or dimension <= 0:
                raise ValueError("backend package portfolio dimensions must be positive")


__all__ = [
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT",
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY",
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_RAW_VALUE_POLICY",
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_SCHEMA_VERSION",
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REQUIRED_PACKAGE_IDS",
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_BLOCKED",
    "BACKEND_PACKAGE_EXECUTION_PORTFOLIO_STATUS_PASS",
    "AdmittedBackendPackagePortfolioExecution",
    "BackendPackageExecutionPortfolioAdmission",
    "BackendPackageExecutionPortfolioEntry",
    "BackendPackageExecutionPortfolioError",
    "BackendPackageExecutionPortfolioIssue",
    "BackendPackageExecutionPortfolioLayoutConversion",
    "BackendPackageExecutionPortfolioReport",
    "assert_backend_package_execution_portfolio",
    "backend_package_execution_portfolio_report_to_dict",
    "build_backend_package_execution_portfolio_admission",
    "build_backend_package_execution_portfolio_report",
    "dump_backend_package_execution_portfolio_report",
    "execute_backend_package_execution_portfolio",
    "project_backend_package_execution_portfolio_plan",
]
