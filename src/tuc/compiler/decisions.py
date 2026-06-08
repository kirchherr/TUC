"""Compiler-level decision reports built from pure capability diagnostics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tuc.backends.base import BackendCapability
from tuc.backends.registry import BackendRegistry, BackendSupportDiagnostic
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind
from tuc.runtime import Assignment, PartitionPlan


@dataclass(frozen=True)
class OperationDecisionReport:
    """Explains one compiler placement decision and its support evidence."""

    operation_name: str
    operation_kind: OperationKind
    assigned_backend: str
    assignment_reason: str
    support_diagnostics: tuple[BackendSupportDiagnostic, ...]

    @property
    def accepted_backends(self) -> tuple[str, ...]:
        """Return backend names accepted by pure capability checks."""

        return tuple(
            diagnostic.backend_name
            for diagnostic in self.support_diagnostics
            if diagnostic.supported
        )

    @property
    def rejected_backends(self) -> tuple[str, ...]:
        """Return backend names rejected by pure capability checks."""

        return tuple(
            diagnostic.backend_name
            for diagnostic in self.support_diagnostics
            if not diagnostic.supported
        )


@dataclass(frozen=True)
class CompilerDecisionReport:
    """Inspectability artifact for compiler backend choices."""

    graph_name: str
    operation_reports: tuple[OperationDecisionReport, ...]

    def dump(self) -> str:
        """Render a deterministic text report for review and tests."""

        lines = [f"compiler.decision_report @{self.graph_name} {{"]
        for report in self.operation_reports:
            lines.append(
                "  operation "
                f"{report.operation_name} kind={report.operation_kind.value} "
                f"assigned={report.assigned_backend} "
                f'accepted_backends="{_format_names(report.accepted_backends)}" '
                f'rejected_backends="{_format_names(report.rejected_backends)}" '
                f'reason="{report.assignment_reason}"'
            )
            lines.append("  support {")
            for diagnostic in report.support_diagnostics:
                status = "accepted" if diagnostic.supported else "rejected"
                lines.append(
                    "    "
                    f"{diagnostic.backend_name} {status} "
                    f'reason="{diagnostic.reason}" '
                    f'detail="{diagnostic.detail}"'
                )
            lines.append("  }")
        lines.append("}")
        return "\n".join(lines)


def build_compiler_decision_report(
    *,
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    backend_capabilities: Iterable[BackendCapability],
) -> CompilerDecisionReport:
    """Build a compiler-level report without executing backend code."""

    registry = BackendRegistry.from_capabilities(backend_capabilities)
    assignments = _assignments_by_operation(partition_plan)
    reports = tuple(
        _operation_decision_report(
            operation=operation,
            assignment=assignments[operation.name],
            registry=registry,
        )
        for operation in graph.operations
    )
    return CompilerDecisionReport(
        graph_name=graph.name,
        operation_reports=reports,
    )


def _operation_decision_report(
    *,
    operation: ComputeOperation,
    assignment: Assignment,
    registry: BackendRegistry,
) -> OperationDecisionReport:
    return OperationDecisionReport(
        operation_name=operation.name,
        operation_kind=operation.kind,
        assigned_backend=assignment.backend_name,
        assignment_reason=assignment.reason,
        support_diagnostics=registry.diagnose_operation_support(operation),
    )


def _assignments_by_operation(partition_plan: PartitionPlan) -> dict[str, Assignment]:
    return {
        assignment.operation_name: assignment
        for assignment in partition_plan.assignments
    }


def _format_names(names: tuple[str, ...]) -> str:
    if not names:
        return "-"
    return ",".join(names)


__all__ = [
    "CompilerDecisionReport",
    "OperationDecisionReport",
    "build_compiler_decision_report",
]
