"""End-to-end prototype compiler pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from tuc.backends.base import BackendCapability
from tuc.compiler.decisions import (
    CompilerDecisionReport,
    build_compiler_decision_report,
)
from tuc.compiler.lowering import lower_hac_to_hs, lower_tlir_to_hac
from tuc.ir.dump import dump_module
from tuc.ir.model import ComputeGraph
from tuc.ir.modules import IRModule, IRStage
from tuc.runtime import (
    DEFAULT_FALLBACK_BACKEND,
    PartitionPlan,
    RuntimeOverrideSet,
    TransferCostProfile,
    dump_partition_plan,
    partition_graph,
)


@dataclass(frozen=True)
class CompilationResult:
    """All observable outputs from a Phase 1 pipeline run."""

    tlir: IRModule
    hac_ir: IRModule
    hs_ir: IRModule
    partition_plan: PartitionPlan
    decision_report: CompilerDecisionReport
    diagnostics: tuple[str, ...]

    def dump(self, stage: IRStage) -> str:
        if stage is IRStage.TLIR:
            return dump_module(self.tlir)
        if stage is IRStage.HAC_IR:
            return dump_module(self.hac_ir)
        if stage is IRStage.HS_IR:
            return dump_module(self.hs_ir)
        raise ValueError(f"unsupported stage: {stage.value}")

    def dumps(self) -> dict[str, str]:
        return {
            self.tlir.stage.value: dump_module(self.tlir),
            self.hac_ir.stage.value: dump_module(self.hac_ir),
            self.hs_ir.stage.value: dump_module(self.hs_ir),
        }

    def dump_runtime_plan(self) -> str:
        """Return a deterministic runtime partition and transfer-plan dump."""

        return dump_partition_plan(self.partition_plan)

    def dump_decision_report(self) -> str:
        """Return deterministic compiler decision evidence."""

        return self.decision_report.dump()


class CompilerPipeline:
    """Small TLIR -> HAC-IR -> HS-IR pipeline used by Phase 1."""

    def __init__(
        self,
        backend_capabilities: Iterable[BackendCapability],
        fallback_backend: str = DEFAULT_FALLBACK_BACKEND,
        transfer_cost_profile: TransferCostProfile | None = None,
        runtime_overrides: RuntimeOverrideSet | None = None,
        include_candidate_scores: bool = False,
    ) -> None:
        if not isinstance(include_candidate_scores, bool):
            raise TypeError("include_candidate_scores must be bool")
        self._backend_capabilities = tuple(backend_capabilities)
        self._fallback_backend = fallback_backend
        self._transfer_cost_profile = transfer_cost_profile
        self._runtime_overrides = runtime_overrides
        self._include_candidate_scores = include_candidate_scores

    def compile(self, graph: ComputeGraph) -> CompilationResult:
        tlir = IRModule(
            stage=IRStage.TLIR,
            graph=graph,
            metadata={"dialect_version": "tlir.v0", "source": "triton-like-python"},
        )
        hac_ir = lower_tlir_to_hac(tlir)
        partition_plan = partition_graph(
            hac_ir.graph,
            self._backend_capabilities,
            fallback_backend=self._fallback_backend,
            transfer_cost_profile=self._transfer_cost_profile,
            runtime_overrides=self._runtime_overrides,
            include_candidate_scores=self._include_candidate_scores,
        )
        decision_report = build_compiler_decision_report(
            graph=hac_ir.graph,
            partition_plan=partition_plan,
            backend_capabilities=self._backend_capabilities,
        )
        hs_ir = lower_hac_to_hs(hac_ir, partition_plan)

        diagnostics = tuple(
            f"{assignment.operation_name}->{assignment.backend_name}:{assignment.reason}"
            for assignment in partition_plan.assignments
        )
        return CompilationResult(
            tlir=tlir,
            hac_ir=hac_ir,
            hs_ir=hs_ir,
            partition_plan=partition_plan,
            decision_report=decision_report,
            diagnostics=diagnostics,
        )


def compile_graph(
    graph: ComputeGraph,
    backend_capabilities: Iterable[BackendCapability],
    fallback_backend: str = DEFAULT_FALLBACK_BACKEND,
    transfer_cost_profile: TransferCostProfile | None = None,
    runtime_overrides: RuntimeOverrideSet | None = None,
    include_candidate_scores: bool = False,
) -> CompilationResult:
    """Convenience wrapper for one-shot pipeline runs."""

    return CompilerPipeline(
        backend_capabilities=backend_capabilities,
        fallback_backend=fallback_backend,
        transfer_cost_profile=transfer_cost_profile,
        runtime_overrides=runtime_overrides,
        include_candidate_scores=include_candidate_scores,
    ).compile(graph)
