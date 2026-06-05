"""Compiler decision reports for backend selection and review."""

from __future__ import annotations

from dataclasses import dataclass

from tuc.backends.registry import BackendRegistry, BackendSupportDiagnostic
from tuc.ir.model import ComputeGraph, OperationKind
from tuc.runtime.partitioning import PartitionPlan


@dataclass(frozen=True)
class OperationDecision:
    """Explains backend candidate support and final selection for one operation."""

    operation_name: str
    operation_kind: OperationKind
    selected_backend: str
    candidates: tuple[BackendSupportDiagnostic, ...]


@dataclass(frozen=True)
class CompilerDecisionReport:
    """Pure-data report for compiler backend-selection decisions."""

    graph_name: str
    operations: tuple[OperationDecision, ...]

    def operation(self, operation_name: str) -> OperationDecision:
        """Return the decision record for one operation."""

        for decision in self.operations:
            if decision.operation_name == operation_name:
                return decision
        raise KeyError(operation_name)


def build_decision_report(
    graph: ComputeGraph,
    registry: BackendRegistry,
    partition_plan: PartitionPlan,
) -> CompilerDecisionReport:
    """Build a reviewable backend-selection report from pure planning data."""

    decisions: list[OperationDecision] = []
    for operation in graph.operations:
        decisions.append(
            OperationDecision(
                operation_name=operation.name,
                operation_kind=operation.kind,
                selected_backend=partition_plan.backend_for(operation.name),
                candidates=registry.diagnose_operation_support(operation),
            )
        )
    return CompilerDecisionReport(graph_name=graph.name, operations=tuple(decisions))


def dump_decision_report(report: CompilerDecisionReport) -> str:
    """Render backend-selection decisions as deterministic text."""

    lines = [f"compiler.decisions @{report.graph_name} {{"]
    for decision in report.operations:
        lines.append(
            "  operation "
            f"{decision.operation_name} "
            f"kind={decision.operation_kind.value} "
            f"selected={decision.selected_backend} {{"
        )
        for candidate in decision.candidates:
            lines.append(f"    {_format_candidate(candidate)}")
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)


def _format_candidate(candidate: BackendSupportDiagnostic) -> str:
    supported = "true" if candidate.supported else "false"
    return (
        f"{candidate.backend_name} supported={supported}"
        f' reason="{_escape(candidate.reason)}"'
        f' detail="{_escape(candidate.detail)}"'
    )


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


__all__ = [
    "CompilerDecisionReport",
    "OperationDecision",
    "build_decision_report",
    "dump_decision_report",
]
