"""Compiler-level decision reports built from pure capability diagnostics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tuc.backends.base import BackendCapability
from tuc.backends.registry import BackendRegistry, BackendSupportDiagnostic
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind
from tuc.runtime import Assignment, CandidateScore, PartitionPlan, RuntimeOverrideEffect


@dataclass(frozen=True)
class OperationDecisionReport:
    """Explains one compiler placement decision and its support evidence."""

    operation_name: str
    operation_kind: OperationKind
    assigned_backend: str
    assignment_reason: str
    support_diagnostics: tuple[BackendSupportDiagnostic, ...]
    override_effect: RuntimeOverrideEffect | None = None
    candidate_scores: tuple[CandidateScore, ...] = ()

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
            if report.override_effect is not None and report.override_effect.active:
                lines.append("  manual_overrides {")
                lines.append(f"    {_format_override_effect(report.override_effect)}")
                lines.append("  }")
            if report.candidate_scores:
                lines.append("  candidate_scores {")
                for score in report.candidate_scores:
                    lines.append(f"    {_format_candidate_score(score)}")
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
    override_effects = _override_effects_by_operation(partition_plan)
    candidate_scores = _candidate_scores_by_operation(partition_plan)
    reports = tuple(
        _operation_decision_report(
            operation=operation,
            assignment=assignments[operation.name],
            registry=registry,
            override_effect=override_effects.get(operation.name),
            candidate_scores=candidate_scores.get(operation.name, ()),
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
    override_effect: RuntimeOverrideEffect | None,
    candidate_scores: tuple[CandidateScore, ...],
) -> OperationDecisionReport:
    return OperationDecisionReport(
        operation_name=operation.name,
        operation_kind=operation.kind,
        assigned_backend=assignment.backend_name,
        assignment_reason=assignment.reason,
        support_diagnostics=registry.diagnose_operation_support(operation),
        override_effect=override_effect,
        candidate_scores=candidate_scores,
    )


def _assignments_by_operation(partition_plan: PartitionPlan) -> dict[str, Assignment]:
    return {
        assignment.operation_name: assignment
        for assignment in partition_plan.assignments
    }


def _override_effects_by_operation(
    partition_plan: PartitionPlan,
) -> dict[str, RuntimeOverrideEffect]:
    return {
        effect.operation_name: effect
        for effect in partition_plan.override_effects
        if isinstance(effect, RuntimeOverrideEffect)
    }


def _candidate_scores_by_operation(
    partition_plan: PartitionPlan,
) -> dict[str, tuple[CandidateScore, ...]]:
    scores: dict[str, list[CandidateScore]] = {}
    for score in partition_plan.candidate_scores:
        scores.setdefault(score.operation_name, []).append(score)
    return {
        operation_name: tuple(operation_scores)
        for operation_name, operation_scores in scores.items()
    }


def _format_override_effect(effect: RuntimeOverrideEffect) -> str:
    return (
        f'require_backend="{_format_optional_name(effect.required_backend)}" '
        f'prefer_backend="{_format_optional_name(effect.preferred_backend)}" '
        f'deny_backends="{_format_names(effect.denied_backends)}"'
    )


def _format_candidate_score(score: CandidateScore) -> str:
    return (
        f"{score.backend_name} selected={_format_bool(score.selected)} "
        f"stage={score.selection_stage} "
        f"transfer_score={_format_float(score.transfer_score)} "
        f"transfer_score_unit={score.transfer_score_unit} "
        f"transfer_bytes={score.transfer_bytes} "
        f"layout_conversion_bytes={score.layout_conversion_bytes} "
        "preferred_memory_domain_match="
        f"{_format_bool(score.preferred_memory_domain_match)} "
        f"domain={score.memory_domain.value} "
        f"produced_layout={score.produced_layout.value}"
    )


def _format_optional_name(value: str | None) -> str:
    if value is None:
        return "-"
    return value


def _format_names(names: tuple[str, ...]) -> str:
    if not names:
        return "-"
    return ",".join(names)


def _format_float(value: float) -> str:
    return f"{value:.12g}"


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


__all__ = [
    "CompilerDecisionReport",
    "OperationDecisionReport",
    "build_compiler_decision_report",
]
