"""Digest-bound execution admission for data-only backend integration packages.

This module never imports or executes code supplied by a package. It can only
project an allowlisted package backend onto an executor already present in the
fixed trusted runtime registry.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from hashlib import sha256

from tuc.backends.base import BackendCapability
from tuc.backends.integration_package import (
    BACKEND_INTEGRATION_PACKAGE_STATUS_PASS,
    BackendIntegrationPackageReport,
    evaluate_backend_integration_package,
)
from tuc.backends.simulator import VectorSimulatorBackend
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeGraph, OperationKind
from tuc.runtime.backend_equivalence import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RuntimeBackendEquivalenceReport,
    assert_runtime_backend_equivalence,
)
from tuc.runtime.dump import dump_partition_plan
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeBackendExecutorContract,
    RuntimeExecutionResult,
    RuntimeValueRecord,
    execute_graph,
    runtime_execution_readiness_report,
    trusted_runtime_executor_registry,
)
from tuc.runtime.partitioning import PartitionPlan

BACKEND_PACKAGE_EXECUTION_ADMISSION_REPORT_SCHEMA_VERSION = (
    "tuc.backend_package_execution_admission_report.v0"
)
BACKEND_PACKAGE_EXECUTION_PROOF_REPORT_SCHEMA_VERSION = (
    "tuc.backend_package_execution_proof_report.v0"
)
BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT = (
    "backend_package_execution_admission.trusted_projection.v0"
)
BACKEND_PACKAGE_EXECUTION_PROOF_CONTRACT = (
    "backend_package_execution_proof.trusted_projection.v0"
)
BACKEND_PACKAGE_EXECUTION_POLICY = "digest_bound_pre_registered_executor_only"
BACKEND_PACKAGE_EXECUTION_MODE = "trusted_reference_projection_only"
BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED = "ADMITTED"
BACKEND_PACKAGE_EXECUTION_STATUS_BLOCKED = "BLOCKED"
BACKEND_PACKAGE_EXECUTION_PROOF_STATUS = "PASS"
BACKEND_PACKAGE_EXECUTION_RAW_VALUE_POLICY = "omitted_by_policy"
BACKEND_PACKAGE_EXECUTION_UNBOUND_DIGEST = "sha256:" + ("0" * 64)
MAX_BACKEND_PACKAGE_EXECUTION_BINDINGS = 16
MAX_BACKEND_PACKAGE_EXECUTION_ISSUES = 32
MAX_BACKEND_PACKAGE_EXECUTION_REPORT_BYTES = 64 * 1024

_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ISSUE_CODES = frozenset(
    {
        "backend_name_mismatch",
        "binding_id_mismatch",
        "capability_digest_mismatch",
        "capability_operation_scope_mismatch",
        "integration_report_failed",
        "integration_report_mismatch",
        "memory_domain_mismatch",
        "package_digest_mismatch",
        "package_not_allowlisted",
        "produced_layout_mismatch",
        "supported_layout_mismatch",
        "trusted_executor_binding_mismatch",
        "trusted_executor_capability_mismatch",
        "trusted_executor_contract_mismatch",
        "trusted_executor_missing",
    }
)


class BackendPackageExecutionAdmissionError(ValueError):
    """Raised when a backend package is not admitted for trusted projection."""


@dataclass(frozen=True)
class TrustedBackendPackageExecutionBinding:
    """One maintainer-owned binding from package identity to trusted executor."""

    binding_id: str
    package_id: str
    package_digest: str
    capability_manifest_digest: str
    package_backend_name: str
    trusted_executor_backend: str
    trusted_executor_contract_digest: str
    allowed_operations: tuple[OperationKind, ...]
    expected_memory_domain: MemoryDomainKind
    expected_supported_layouts: tuple[LayoutKind, ...]
    expected_produced_layouts: tuple[LayoutKind, ...]
    approval_rfc_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.binding_id, "binding_id"),
            (self.package_id, "package_id"),
            (self.package_backend_name, "package_backend_name"),
            (self.trusted_executor_backend, "trusted_executor_backend"),
            (self.approval_rfc_id, "approval_rfc_id"),
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
            raise ValueError("trusted package binding requires allowed operations")
        if not isinstance(self.expected_memory_domain, MemoryDomainKind):
            raise TypeError("trusted package binding memory domain is invalid")
        _validate_layout_tuple(
            self.expected_supported_layouts,
            "expected_supported_layouts",
        )
        _validate_layout_tuple(
            self.expected_produced_layouts,
            "expected_produced_layouts",
        )


@dataclass(frozen=True)
class BackendPackageExecutionAdmissionIssue:
    """One deterministic package-admission rejection reason."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "admission issue subject")
        _validate_text(self.issue_code, "admission issue code")
        if self.issue_code not in _ISSUE_CODES:
            raise ValueError("backend package admission issue code unsupported")


@dataclass(frozen=True)
class BackendPackageExecutionAdmissionReport:
    """Fail-closed admission result for one integration package report."""

    package_id: str
    package_version: str
    package_digest: str
    capability_manifest_digest: str
    package_backend_name: str
    integration_status: str
    integration_report_matches: bool
    declared_operations: tuple[OperationKind, ...]
    memory_domain: MemoryDomainKind
    supported_layouts: tuple[LayoutKind, ...]
    produced_layouts: tuple[LayoutKind, ...]
    binding_id: str
    trusted_executor_backend: str
    trusted_executor_contract_digest: str
    allowed_operations: tuple[OperationKind, ...]
    issues: tuple[BackendPackageExecutionAdmissionIssue, ...]
    admission_contract: str = BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT
    admission_policy: str = BACKEND_PACKAGE_EXECUTION_POLICY
    execution_mode: str = BACKEND_PACKAGE_EXECUTION_MODE
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    external_plugin_execution: bool = False
    package_backend_implementation_executed: bool = False
    physical_device_execution: bool = False
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.package_id, "package_id"),
            (self.package_version, "package_version"),
            (self.package_backend_name, "package_backend_name"),
            (self.integration_status, "integration_status"),
            (self.binding_id, "binding_id"),
            (self.trusted_executor_backend, "trusted_executor_backend"),
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
        if type(self.integration_report_matches) is not bool:
            raise TypeError("integration_report_matches must be bool")
        _validate_operation_tuple(self.declared_operations, "declared_operations")
        _validate_operation_tuple(self.allowed_operations, "allowed_operations")
        if not isinstance(self.memory_domain, MemoryDomainKind):
            raise TypeError("backend package admission memory domain is invalid")
        _validate_layout_tuple(self.supported_layouts, "supported_layouts")
        _validate_layout_tuple(self.produced_layouts, "produced_layouts")
        if self.admission_contract != BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT:
            raise ValueError("backend package admission contract mismatch")
        if self.admission_policy != BACKEND_PACKAGE_EXECUTION_POLICY:
            raise ValueError("backend package admission policy mismatch")
        if self.execution_mode != BACKEND_PACKAGE_EXECUTION_MODE:
            raise ValueError("backend package execution mode mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("backend package trusted executor registry mismatch")
        for flag_name in (
            "external_plugin_execution",
            "package_backend_implementation_executed",
            "physical_device_execution",
        ):
            if type(getattr(self, flag_name)) is not bool:
                raise TypeError(f"{flag_name} must be bool")
            if getattr(self, flag_name):
                raise ValueError(f"{flag_name} must remain false")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend package admission blocked surfaces changed")
        if type(self.issues) is not tuple:
            raise TypeError("backend package admission issues must be tuple")
        if len(self.issues) > MAX_BACKEND_PACKAGE_EXECUTION_ISSUES:
            raise ValueError("backend package admission issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPackageExecutionAdmissionIssue):
                raise TypeError("backend package admission issues must be issue objects")
        expected_issues = _derive_admission_issues(self)
        if self.issues != expected_issues:
            raise ValueError("backend package admission issues must be derived")

    @property
    def projection_execution_allowed(self) -> bool:
        """Return whether trusted reference projection is admitted."""

        return not self.issues

    @property
    def admission_status(self) -> str:
        """Return stable admitted or blocked status."""

        if self.projection_execution_allowed:
            return BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED
        return BACKEND_PACKAGE_EXECUTION_STATUS_BLOCKED


@dataclass(frozen=True)
class AdmittedBackendPackageExecution:
    """Internal execution result retaining both source and projected plans."""

    admission: BackendPackageExecutionAdmissionReport
    source_partition_plan: PartitionPlan
    projected_partition_plan: PartitionPlan
    execution: RuntimeExecutionResult

    def __post_init__(self) -> None:
        assert_backend_package_execution_admission(self.admission)
        if not isinstance(self.source_partition_plan, PartitionPlan):
            raise TypeError("source partition plan must be PartitionPlan")
        if not isinstance(self.projected_partition_plan, PartitionPlan):
            raise TypeError("projected partition plan must be PartitionPlan")
        if not isinstance(self.execution, RuntimeExecutionResult):
            raise TypeError("admitted execution must be RuntimeExecutionResult")
        projected_sequence = tuple(
            assignment.backend_name
            for assignment in self.projected_partition_plan.assignments
        )
        trace_sequence = tuple(
            step.planned_backend for step in self.execution.trace.steps
        )
        if projected_sequence != trace_sequence:
            raise ValueError("admitted execution trace does not match projected plan")


@dataclass(frozen=True)
class BackendPackageExecutionProofReport:
    """Reviewable proof that an admitted package reached trusted execution."""

    package_id: str
    package_digest: str
    capability_manifest_digest: str
    binding_id: str
    graph_name: str
    package_backend_name: str
    trusted_executor_backend: str
    trusted_executor_contract_digest: str
    source_plan_digest: str
    projected_plan_digest: str
    source_backend_sequence: tuple[str, ...]
    projected_backend_sequence: tuple[str, ...]
    projected_operation_count: int
    transfer_edge_count: int
    execution_step_count: int
    output_tensor_names: tuple[str, ...]
    output_shapes: tuple[tuple[int, ...], ...]
    output_dtypes: tuple[str, ...]
    equivalence_comparison_metadata_digest: str
    equivalence_passed: bool
    proof_contract: str = BACKEND_PACKAGE_EXECUTION_PROOF_CONTRACT
    admission_contract: str = BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT
    admission_status: str = BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED
    execution_mode: str = BACKEND_PACKAGE_EXECUTION_MODE
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    equivalence_contract: str = RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    proof_status: str = BACKEND_PACKAGE_EXECUTION_PROOF_STATUS
    raw_tensor_value_policy: str = BACKEND_PACKAGE_EXECUTION_RAW_VALUE_POLICY
    external_plugin_execution: bool = False
    package_backend_implementation_executed: bool = False
    physical_device_execution: bool = False
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.package_id, "package_id"),
            (self.binding_id, "binding_id"),
            (self.graph_name, "graph_name"),
            (self.package_backend_name, "package_backend_name"),
            (self.trusted_executor_backend, "trusted_executor_backend"),
        ):
            _validate_text(value, label)
        for value, label in (
            (self.package_digest, "package_digest"),
            (self.capability_manifest_digest, "capability_manifest_digest"),
            (self.trusted_executor_contract_digest, "trusted_executor_contract_digest"),
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
        _validate_non_negative_int(
            self.projected_operation_count,
            "projected_operation_count",
        )
        if self.projected_operation_count == 0:
            raise ValueError("backend package proof requires projected operation")
        _validate_non_negative_int(self.transfer_edge_count, "transfer_edge_count")
        _validate_non_negative_int(self.execution_step_count, "execution_step_count")
        if self.execution_step_count != len(self.projected_backend_sequence):
            raise ValueError("execution step count must match projected sequence")
        _validate_text_tuple(self.output_tensor_names, "output_tensor_names")
        _validate_text_tuple(self.output_dtypes, "output_dtypes")
        if len(self.output_shapes) != len(self.output_tensor_names):
            raise ValueError("output shapes must match output names")
        if len(self.output_dtypes) != len(self.output_tensor_names):
            raise ValueError("output dtypes must match output names")
        for shape in self.output_shapes:
            if type(shape) is not tuple or not shape:
                raise TypeError("output shapes must be non-empty tuples")
            for dimension in shape:
                if type(dimension) is not int or dimension <= 0:
                    raise ValueError("output shape dimensions must be positive integers")
        if type(self.equivalence_passed) is not bool or not self.equivalence_passed:
            raise ValueError("backend package proof requires equivalence PASS")
        if self.proof_contract != BACKEND_PACKAGE_EXECUTION_PROOF_CONTRACT:
            raise ValueError("backend package execution proof contract mismatch")
        if self.admission_contract != BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT:
            raise ValueError("backend package execution admission contract mismatch")
        if self.admission_status != BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED:
            raise ValueError("backend package execution proof requires admission")
        if self.execution_mode != BACKEND_PACKAGE_EXECUTION_MODE:
            raise ValueError("backend package execution mode mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("backend package executor contract mismatch")
        if self.equivalence_contract != RUNTIME_BACKEND_EQUIVALENCE_CONTRACT:
            raise ValueError("backend package equivalence contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("backend package trusted registry mismatch")
        if self.proof_status != BACKEND_PACKAGE_EXECUTION_PROOF_STATUS:
            raise ValueError("backend package execution proof status mismatch")
        if self.raw_tensor_value_policy != BACKEND_PACKAGE_EXECUTION_RAW_VALUE_POLICY:
            raise ValueError("backend package proof must omit raw tensor values")
        for flag_name in (
            "external_plugin_execution",
            "package_backend_implementation_executed",
            "physical_device_execution",
        ):
            if type(getattr(self, flag_name)) is not bool or getattr(self, flag_name):
                raise ValueError(f"{flag_name} must remain false")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend package proof blocked surfaces changed")
        if self.package_backend_name not in self.source_backend_sequence:
            raise ValueError("source plan must contain package backend")
        if self.package_backend_name in self.projected_backend_sequence:
            raise ValueError("projected plan must not retain package backend")
        if self.trusted_executor_backend not in self.projected_backend_sequence:
            raise ValueError("projected plan must contain trusted executor")


def trusted_backend_package_execution_bindings(
) -> tuple[TrustedBackendPackageExecutionBinding, ...]:
    """Return the fixed maintainer-owned package execution allowlist."""

    bindings = (
        TrustedBackendPackageExecutionBinding(
            binding_id="external_vector_reference_projection_v0",
            package_id="external-vector-reference-package",
            package_digest=(
                "sha256:bf4bf333025a176f20ad927c249747f6ce923e14f224f4cd94ed769d893288ee"
            ),
            capability_manifest_digest=(
                "sha256:ca1de79c1935a08617343687a06816821b77e4837ac7ac8430998c746bd60d3a"
            ),
            package_backend_name="external-vector",
            trusted_executor_backend="vector-sim",
            trusted_executor_contract_digest=(
                "sha256:89a8be02144416cd98c7aa0e14b1e6cd16dbce7b900da80143756e456cf24d45"
            ),
            allowed_operations=(OperationKind.ELEMENTWISE,),
            expected_memory_domain=MemoryDomainKind.DEVICE_SRAM,
            expected_supported_layouts=(LayoutKind.ROW_MAJOR,),
            expected_produced_layouts=(LayoutKind.ROW_MAJOR,),
            approval_rfc_id="rfc_0283_backend_package_execution_admission",
        ),
    )
    if len(bindings) > MAX_BACKEND_PACKAGE_EXECUTION_BINDINGS:
        raise ValueError("trusted backend package binding count exceeds limit")
    if len({binding.package_id for binding in bindings}) != len(bindings):
        raise ValueError("trusted backend package bindings must use unique package IDs")
    return bindings


def build_backend_package_execution_admission_report(
    integration_report: BackendIntegrationPackageReport,
) -> BackendPackageExecutionAdmissionReport:
    """Bind package evidence to the fixed trusted executor allowlist."""

    if not isinstance(integration_report, BackendIntegrationPackageReport):
        raise TypeError("backend package admission requires integration report")
    package = integration_report.package
    capability = package.capability
    canonical_integration = evaluate_backend_integration_package(package)
    integration_report_matches = integration_report == canonical_integration
    binding = _binding_for_package_id(package.package_id)
    executor_backend = binding.trusted_executor_backend if binding else "unbound"
    binding_id = binding.binding_id if binding else "unbound"
    allowed_operations = binding.allowed_operations if binding else ()
    executor_digest = (
        _executor_contract_digest_for_name(executor_backend)
        if binding is not None
        else BACKEND_PACKAGE_EXECUTION_UNBOUND_DIGEST
    )
    declared_operations = tuple(
        sorted(capability.supported_ops, key=lambda item: item.value)
    )
    supported_layouts = tuple(
        sorted(capability.supported_layouts, key=lambda item: item.value)
    )
    produced_layouts = tuple(
        sorted(capability.produced_layouts, key=lambda item: item.value)
    )
    issues = _derive_admission_issues_from_values(
        package_id=package.package_id,
        package_digest=package.package_digest,
        capability_manifest_digest=package.capability_manifest_digest,
        package_backend_name=capability.name,
        integration_status=integration_report.integration_status,
        integration_report_matches=integration_report_matches,
        declared_operations=declared_operations,
        memory_domain=capability.memory_domain,
        supported_layouts=supported_layouts,
        produced_layouts=produced_layouts,
        binding_id=binding_id,
        trusted_executor_backend=executor_backend,
        trusted_executor_contract_digest=executor_digest,
        allowed_operations=allowed_operations,
    )
    return BackendPackageExecutionAdmissionReport(
        package_id=package.package_id,
        package_version=package.package_version,
        package_digest=package.package_digest,
        capability_manifest_digest=package.capability_manifest_digest,
        package_backend_name=capability.name,
        integration_status=integration_report.integration_status,
        integration_report_matches=integration_report_matches,
        declared_operations=declared_operations,
        memory_domain=capability.memory_domain,
        supported_layouts=supported_layouts,
        produced_layouts=produced_layouts,
        binding_id=binding_id,
        trusted_executor_backend=executor_backend,
        trusted_executor_contract_digest=executor_digest,
        allowed_operations=allowed_operations,
        issues=issues,
    )


def assert_backend_package_execution_admission(
    report: BackendPackageExecutionAdmissionReport,
) -> BackendPackageExecutionAdmissionReport:
    """Return an admitted report or fail closed with structured reasons."""

    if not isinstance(report, BackendPackageExecutionAdmissionReport):
        raise TypeError("backend package execution admission requires report")
    if not report.projection_execution_allowed:
        detail = ",".join(issue.issue_code for issue in report.issues)
        raise BackendPackageExecutionAdmissionError(
            f"backend package execution admission blocked: {detail}"
        )
    return report


def project_backend_package_partition_plan(
    graph: ComputeGraph,
    source_plan: PartitionPlan,
    admission: BackendPackageExecutionAdmissionReport,
) -> PartitionPlan:
    """Project package assignments onto a pre-registered trusted executor."""

    assert_backend_package_execution_admission(admission)
    if not isinstance(graph, ComputeGraph):
        raise TypeError("backend package projection graph must be ComputeGraph")
    if not isinstance(source_plan, PartitionPlan):
        raise TypeError("backend package source plan must be PartitionPlan")
    if graph.name != source_plan.graph_name:
        raise ValueError("backend package source plan graph mismatch")
    operation_names = tuple(operation.name for operation in graph.operations)
    assignment_names = tuple(
        assignment.operation_name for assignment in source_plan.assignments
    )
    if assignment_names != operation_names:
        raise ValueError("backend package source plan assignments must match graph")
    if source_plan.override_effects:
        raise BackendPackageExecutionAdmissionError(
            "backend package projection does not admit runtime overrides"
        )
    if source_plan.candidate_scores:
        raise BackendPackageExecutionAdmissionError(
            "backend package projection does not admit candidate score payloads"
        )
    operations = {operation.name: operation for operation in graph.operations}
    trusted_names = frozenset(trusted_runtime_executor_registry())
    projected_count = 0
    projected_assignments = []
    for assignment in source_plan.assignments:
        backend_name = assignment.backend_name
        if backend_name == admission.package_backend_name:
            operation = operations[assignment.operation_name]
            if operation.kind not in admission.allowed_operations:
                raise BackendPackageExecutionAdmissionError(
                    "backend package plan exceeds admitted operation scope"
                )
            backend_name = admission.trusted_executor_backend
            projected_count += 1
        elif backend_name not in trusted_names:
            raise BackendPackageExecutionAdmissionError(
                "backend package plan contains untrusted non-package backend"
            )
        projected_assignments.append(replace(assignment, backend_name=backend_name))
    if projected_count == 0:
        raise BackendPackageExecutionAdmissionError(
            "backend package plan contains no admitted package assignment"
        )
    projected_edges = tuple(
        replace(
            edge,
            source_backend=_project_backend_name(edge.source_backend, admission),
            target_backend=_project_backend_name(edge.target_backend, admission),
        )
        for edge in source_plan.transfer_edges
    )
    projected = PartitionPlan(
        graph_name=source_plan.graph_name,
        assignments=tuple(projected_assignments),
        transfer_edges=projected_edges,
        layout_conversions=source_plan.layout_conversions,
    )
    runtime_execution_readiness_report(graph, projected)
    return projected


def execute_admitted_backend_package(
    graph: ComputeGraph,
    source_plan: PartitionPlan,
    inputs: Mapping[str, object],
    admission: BackendPackageExecutionAdmissionReport,
) -> AdmittedBackendPackageExecution:
    """Execute an admitted package plan only through trusted reference projection."""

    if type(inputs) is not dict:
        raise TypeError("backend package execution inputs must be a plain mapping")
    projected = project_backend_package_partition_plan(graph, source_plan, admission)
    execution = execute_graph(graph, projected, inputs)
    return AdmittedBackendPackageExecution(
        admission=admission,
        source_partition_plan=source_plan,
        projected_partition_plan=projected,
        execution=execution,
    )


def build_backend_package_execution_proof_report(
    graph: ComputeGraph,
    admitted_execution: AdmittedBackendPackageExecution,
    equivalence_report: RuntimeBackendEquivalenceReport,
) -> BackendPackageExecutionProofReport:
    """Build source-free proof metadata for admitted trusted execution."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("backend package proof graph must be ComputeGraph")
    if not isinstance(admitted_execution, AdmittedBackendPackageExecution):
        raise TypeError("backend package proof requires admitted execution")
    assert_backend_package_execution_admission(admitted_execution.admission)
    assert_runtime_backend_equivalence(equivalence_report)
    if graph.name != admitted_execution.source_partition_plan.graph_name:
        raise ValueError("backend package proof graph and source plan mismatch")
    if graph.name != equivalence_report.graph_name:
        raise ValueError("backend package proof equivalence graph mismatch")
    projected_sequence = tuple(
        assignment.backend_name
        for assignment in admitted_execution.projected_partition_plan.assignments
    )
    candidate_run = next(
        run
        for run in equivalence_report.runs
        if run.run_id == equivalence_report.candidate_run_id
    )
    if candidate_run.planned_backend_sequence != projected_sequence:
        raise ValueError("backend package equivalence candidate does not match projection")
    terminal_records = _terminal_output_records(graph, admitted_execution.execution)
    admission = admitted_execution.admission
    return BackendPackageExecutionProofReport(
        package_id=admission.package_id,
        package_digest=admission.package_digest,
        capability_manifest_digest=admission.capability_manifest_digest,
        binding_id=admission.binding_id,
        graph_name=graph.name,
        package_backend_name=admission.package_backend_name,
        trusted_executor_backend=admission.trusted_executor_backend,
        trusted_executor_contract_digest=admission.trusted_executor_contract_digest,
        source_plan_digest=_partition_plan_digest(
            admitted_execution.source_partition_plan
        ),
        projected_plan_digest=_partition_plan_digest(
            admitted_execution.projected_partition_plan
        ),
        source_backend_sequence=tuple(
            assignment.backend_name
            for assignment in admitted_execution.source_partition_plan.assignments
        ),
        projected_backend_sequence=projected_sequence,
        projected_operation_count=sum(
            1
            for assignment in admitted_execution.source_partition_plan.assignments
            if assignment.backend_name == admission.package_backend_name
        ),
        transfer_edge_count=len(
            admitted_execution.projected_partition_plan.transfer_edges
        ),
        execution_step_count=len(admitted_execution.execution.trace.steps),
        output_tensor_names=tuple(record.tensor_name for record in terminal_records),
        output_shapes=tuple(record.shape for record in terminal_records),
        output_dtypes=tuple(record.dtype for record in terminal_records),
        equivalence_comparison_metadata_digest=(
            equivalence_report.comparison_metadata_digest
        ),
        equivalence_passed=equivalence_report.passed,
    )


def backend_package_execution_admission_report_to_dict(
    report: BackendPackageExecutionAdmissionReport,
) -> dict[str, object]:
    """Return deterministic, source-free admission metadata."""

    if not isinstance(report, BackendPackageExecutionAdmissionReport):
        raise TypeError("backend package admission serialization requires report")
    return {
        "admission_contract": report.admission_contract,
        "admission_policy": report.admission_policy,
        "admission_status": report.admission_status,
        "allowed_operations": [item.value for item in report.allowed_operations],
        "binding_id": report.binding_id,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "capability_manifest_digest": report.capability_manifest_digest,
        "declared_operations": [item.value for item in report.declared_operations],
        "execution_mode": report.execution_mode,
        "external_plugin_execution": report.external_plugin_execution,
        "integration_report_matches": report.integration_report_matches,
        "integration_status": report.integration_status,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "memory_domain": report.memory_domain.value,
        "package_backend_implementation_executed": (
            report.package_backend_implementation_executed
        ),
        "package_backend_name": report.package_backend_name,
        "package_digest": report.package_digest,
        "package_id": report.package_id,
        "package_version": report.package_version,
        "physical_device_execution": report.physical_device_execution,
        "produced_layouts": [item.value for item in report.produced_layouts],
        "projection_execution_allowed": report.projection_execution_allowed,
        "schema_version": BACKEND_PACKAGE_EXECUTION_ADMISSION_REPORT_SCHEMA_VERSION,
        "supported_layouts": [item.value for item in report.supported_layouts],
        "trusted_executor_backend": report.trusted_executor_backend,
        "trusted_executor_contract_digest": (
            report.trusted_executor_contract_digest
        ),
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def backend_package_execution_proof_report_to_dict(
    report: BackendPackageExecutionProofReport,
) -> dict[str, object]:
    """Return deterministic proof metadata without raw tensor values."""

    if not isinstance(report, BackendPackageExecutionProofReport):
        raise TypeError("backend package proof serialization requires report")
    return {
        "admission_contract": report.admission_contract,
        "admission_status": report.admission_status,
        "binding_id": report.binding_id,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "capability_manifest_digest": report.capability_manifest_digest,
        "equivalence_comparison_metadata_digest": (
            report.equivalence_comparison_metadata_digest
        ),
        "equivalence_contract": report.equivalence_contract,
        "equivalence_passed": report.equivalence_passed,
        "execution_mode": report.execution_mode,
        "execution_step_count": report.execution_step_count,
        "executor_contract": report.executor_contract,
        "external_plugin_execution": report.external_plugin_execution,
        "graph_name": report.graph_name,
        "output_dtypes": list(report.output_dtypes),
        "output_shapes": [list(shape) for shape in report.output_shapes],
        "output_tensor_names": list(report.output_tensor_names),
        "package_backend_implementation_executed": (
            report.package_backend_implementation_executed
        ),
        "package_backend_name": report.package_backend_name,
        "package_digest": report.package_digest,
        "package_id": report.package_id,
        "physical_device_execution": report.physical_device_execution,
        "projected_backend_sequence": list(report.projected_backend_sequence),
        "projected_operation_count": report.projected_operation_count,
        "projected_plan_digest": report.projected_plan_digest,
        "proof_contract": report.proof_contract,
        "proof_status": report.proof_status,
        "raw_tensor_value_policy": report.raw_tensor_value_policy,
        "schema_version": BACKEND_PACKAGE_EXECUTION_PROOF_REPORT_SCHEMA_VERSION,
        "source_backend_sequence": list(report.source_backend_sequence),
        "source_plan_digest": report.source_plan_digest,
        "transfer_edge_count": report.transfer_edge_count,
        "trusted_executor_backend": report.trusted_executor_backend,
        "trusted_executor_contract_digest": (
            report.trusted_executor_contract_digest
        ),
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_backend_package_execution_admission_report(
    report: BackendPackageExecutionAdmissionReport,
) -> str:
    """Render bounded deterministic backend package admission evidence."""

    text = json.dumps(
        backend_package_execution_admission_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PACKAGE_EXECUTION_REPORT_BYTES:
        raise ValueError("backend package execution admission report exceeds limit")
    return text + "\n"

def dump_backend_package_execution_proof_report(
    report: BackendPackageExecutionProofReport,
) -> str:
    """Render bounded deterministic backend package execution proof evidence."""

    text = json.dumps(
        backend_package_execution_proof_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PACKAGE_EXECUTION_REPORT_BYTES:
        raise ValueError("backend package execution proof report exceeds limit")
    return text + "\n"


def _derive_admission_issues(
    report: BackendPackageExecutionAdmissionReport,
) -> tuple[BackendPackageExecutionAdmissionIssue, ...]:
    return _derive_admission_issues_from_values(
        package_id=report.package_id,
        package_digest=report.package_digest,
        capability_manifest_digest=report.capability_manifest_digest,
        package_backend_name=report.package_backend_name,
        integration_status=report.integration_status,
        integration_report_matches=report.integration_report_matches,
        declared_operations=report.declared_operations,
        memory_domain=report.memory_domain,
        supported_layouts=report.supported_layouts,
        produced_layouts=report.produced_layouts,
        binding_id=report.binding_id,
        trusted_executor_backend=report.trusted_executor_backend,
        trusted_executor_contract_digest=report.trusted_executor_contract_digest,
        allowed_operations=report.allowed_operations,
    )


def _derive_admission_issues_from_values(
    *,
    package_id: str,
    package_digest: str,
    capability_manifest_digest: str,
    package_backend_name: str,
    integration_status: str,
    integration_report_matches: bool,
    declared_operations: tuple[OperationKind, ...],
    memory_domain: MemoryDomainKind,
    supported_layouts: tuple[LayoutKind, ...],
    produced_layouts: tuple[LayoutKind, ...],
    binding_id: str,
    trusted_executor_backend: str,
    trusted_executor_contract_digest: str,
    allowed_operations: tuple[OperationKind, ...],
) -> tuple[BackendPackageExecutionAdmissionIssue, ...]:
    issues: list[BackendPackageExecutionAdmissionIssue] = []
    if integration_status != BACKEND_INTEGRATION_PACKAGE_STATUS_PASS:
        issues.append(_issue(package_id, "integration_report_failed"))
    if not integration_report_matches:
        issues.append(_issue(package_id, "integration_report_mismatch"))
    binding = _binding_for_package_id(package_id)
    if binding is None:
        issues.append(_issue(package_id, "package_not_allowlisted"))
        return tuple(issues)
    comparisons = (
        (package_digest, binding.package_digest, "package_digest_mismatch"),
        (
            capability_manifest_digest,
            binding.capability_manifest_digest,
            "capability_digest_mismatch",
        ),
        (package_backend_name, binding.package_backend_name, "backend_name_mismatch"),
        (binding_id, binding.binding_id, "binding_id_mismatch"),
        (
            trusted_executor_backend,
            binding.trusted_executor_backend,
            "trusted_executor_binding_mismatch",
        ),
        (
            declared_operations,
            binding.allowed_operations,
            "capability_operation_scope_mismatch",
        ),
        (memory_domain, binding.expected_memory_domain, "memory_domain_mismatch"),
        (
            supported_layouts,
            binding.expected_supported_layouts,
            "supported_layout_mismatch",
        ),
        (
            produced_layouts,
            binding.expected_produced_layouts,
            "produced_layout_mismatch",
        ),
        (
            trusted_executor_contract_digest,
            binding.trusted_executor_contract_digest,
            "trusted_executor_contract_mismatch",
        ),
    )
    for observed, expected, issue_code in comparisons:
        if observed != expected:
            issues.append(_issue(package_id, issue_code))
    registry = trusted_runtime_executor_registry()
    executor = registry.get(trusted_executor_backend)
    if executor is None:
        issues.append(_issue(package_id, "trusted_executor_missing"))
        return tuple(issues)
    trusted_capability = _trusted_capability_for_executor(trusted_executor_backend)
    if trusted_capability is None:
        issues.append(_issue(package_id, "trusted_executor_capability_mismatch"))
        return tuple(issues)
    capability_compatible = (
        set(declared_operations).issubset(trusted_capability.supported_ops)
        and memory_domain == trusted_capability.memory_domain
        and set(supported_layouts).issubset(trusted_capability.supported_layouts)
        and set(produced_layouts).issubset(trusted_capability.produced_layouts)
        and set(allowed_operations).issubset(executor.supported_ops)
    )
    if not capability_compatible:
        issues.append(_issue(package_id, "trusted_executor_capability_mismatch"))
    return tuple(issues)


def _binding_for_package_id(
    package_id: str,
) -> TrustedBackendPackageExecutionBinding | None:
    return next(
        (
            binding
            for binding in trusted_backend_package_execution_bindings()
            if binding.package_id == package_id
        ),
        None,
    )


def _trusted_capability_for_executor(
    executor_name: str,
) -> BackendCapability | None:
    if executor_name == "vector-sim":
        return VectorSimulatorBackend().capability
    return None


def _executor_contract_digest_for_name(executor_name: str) -> str:
    executor = trusted_runtime_executor_registry().get(executor_name)
    if executor is None:
        return BACKEND_PACKAGE_EXECUTION_UNBOUND_DIGEST
    return _executor_contract_digest(executor.contract)


def _executor_contract_digest(contract: RuntimeBackendExecutorContract) -> str:
    payload = {
        "backend_contract": contract.backend_contract,
        "backend_name": contract.backend_name,
        "blocked_execution_surfaces": list(contract.blocked_execution_surfaces),
        "device_access": contract.device_access,
        "execution_mode": contract.execution_mode,
        "external_artifacts": contract.external_artifacts,
        "input_contract": contract.input_contract,
        "output_contract": contract.output_contract,
        "status": contract.status,
        "supported_ops": sorted(item.value for item in contract.supported_ops),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


def _project_backend_name(
    backend_name: str,
    admission: BackendPackageExecutionAdmissionReport,
) -> str:
    if backend_name == admission.package_backend_name:
        return admission.trusted_executor_backend
    if backend_name not in trusted_runtime_executor_registry():
        raise BackendPackageExecutionAdmissionError(
            "backend package transfer references untrusted backend"
        )
    return backend_name


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
        raise ValueError("backend package proof requires terminal output")
    return tuple(execution.record_for(name) for name in terminal_names)


def _partition_plan_digest(plan: PartitionPlan) -> str:
    encoded = dump_partition_plan(plan).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _issue(subject: str, issue_code: str) -> BackendPackageExecutionAdmissionIssue:
    return BackendPackageExecutionAdmissionIssue(
        subject=subject,
        issue_code=issue_code,
    )


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _TEXT_RE.fullmatch(value):
        raise ValueError(f"backend package execution {label} must be safe text")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"backend package execution {label} must be SHA-256")


def _validate_operation_tuple(
    values: tuple[OperationKind, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"backend package execution {label} must be tuple")
    if len(values) != len(set(values)):
        raise ValueError(f"backend package execution {label} must be unique")
    if any(not isinstance(value, OperationKind) for value in values):
        raise TypeError(f"backend package execution {label} must contain operations")


def _validate_layout_tuple(values: tuple[LayoutKind, ...], label: str) -> None:
    if type(values) is not tuple or not values:
        raise TypeError(f"backend package execution {label} must be non-empty tuple")
    if len(values) != len(set(values)):
        raise ValueError(f"backend package execution {label} must be unique")
    if any(not isinstance(value, LayoutKind) for value in values):
        raise TypeError(f"backend package execution {label} must contain layouts")


def _validate_text_tuple(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple or not values:
        raise TypeError(f"backend package execution {label} must be non-empty tuple")
    for value in values:
        _validate_text(value, label)


def _validate_non_negative_int(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"backend package execution {label} must be non-negative")


__all__ = [
    "BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT",
    "BACKEND_PACKAGE_EXECUTION_ADMISSION_REPORT_SCHEMA_VERSION",
    "BACKEND_PACKAGE_EXECUTION_MODE",
    "BACKEND_PACKAGE_EXECUTION_POLICY",
    "BACKEND_PACKAGE_EXECUTION_PROOF_CONTRACT",
    "BACKEND_PACKAGE_EXECUTION_PROOF_REPORT_SCHEMA_VERSION",
    "BACKEND_PACKAGE_EXECUTION_PROOF_STATUS",
    "BACKEND_PACKAGE_EXECUTION_RAW_VALUE_POLICY",
    "BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED",
    "BACKEND_PACKAGE_EXECUTION_STATUS_BLOCKED",
    "AdmittedBackendPackageExecution",
    "BackendPackageExecutionAdmissionError",
    "BackendPackageExecutionAdmissionIssue",
    "BackendPackageExecutionAdmissionReport",
    "BackendPackageExecutionProofReport",
    "TrustedBackendPackageExecutionBinding",
    "assert_backend_package_execution_admission",
    "backend_package_execution_admission_report_to_dict",
    "backend_package_execution_proof_report_to_dict",
    "build_backend_package_execution_admission_report",
    "build_backend_package_execution_proof_report",
    "dump_backend_package_execution_admission_report",
    "dump_backend_package_execution_proof_report",
    "execute_admitted_backend_package",
    "project_backend_package_partition_plan",
    "trusted_backend_package_execution_bindings",
]
