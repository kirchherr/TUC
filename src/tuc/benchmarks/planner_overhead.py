"""Diagnostic planner-overhead reporting for the compiler pipeline."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from time import perf_counter_ns
from typing import TypeVar

from tuc.backends.base import BackendCapability
from tuc.compiler.decisions import build_compiler_decision_report
from tuc.compiler.lowering import lower_hac_to_hs, lower_tlir_to_hac
from tuc.compiler.pipeline import CompilationResult
from tuc.ir.model import ComputeGraph
from tuc.ir.modules import IRModule, IRStage
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT
from tuc.runtime import (
    DEFAULT_FALLBACK_BACKEND,
    RuntimeOverrideSet,
    TransferCostProfile,
    partition_graph,
)

PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION = "tuc.planner_overhead_report.v0"
PLANNER_OVERHEAD_ARTIFACT_STATUS = "diagnostic_only"
PLANNER_OVERHEAD_EXECUTION_TIME_STATUS = "not_measured"
PLANNER_OVERHEAD_BREAK_EVEN_STATUS = "not_established"
PLANNER_OVERHEAD_PHASES = (
    "graph_construction",
    "frontend_intake",
    "tlir_module_construction",
    "tlir_to_hac_lowering",
    "runtime_planning",
    "backend_selection_report",
    "hs_ir_generation",
    "execution",
)
PLANNER_OVERHEAD_NOT_MEASURED_ISSUES = (
    "graph_construction_not_measured",
    "frontend_intake_not_measured",
    "execution_time_not_measured",
    "break_even_not_established",
)
MAX_PLANNER_OVERHEAD_PHASES = 16
MAX_PLANNER_OVERHEAD_REPORT_BYTES = 64 * 1024
MAX_PLANNER_OVERHEAD_TEXT_BYTES = 256
MAX_PLANNER_OVERHEAD_DURATION_NS = 86_400_000_000_000

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_MEASUREMENT_STATUSES = frozenset({"measured", "not_measured"})
_REQUIRED_NOT_MEASURED_PHASES = frozenset(
    {"graph_construction", "frontend_intake", "execution"}
)
_T = TypeVar("_T")


@dataclass(frozen=True)
class PlannerOverheadPhaseTiming:
    """One measured or explicitly unmeasured planner-overhead phase."""

    phase_name: str
    measurement_status: str
    duration_ns: int | None
    included_in_execution_time: bool = False


@dataclass(frozen=True)
class PlannerOverheadReport:
    """Diagnostic report separating planner overhead from execution time."""

    graph_name: str
    phase_timings: tuple[PlannerOverheadPhaseTiming, ...]
    issues: tuple[str, ...] = PLANNER_OVERHEAD_NOT_MEASURED_ISSUES

    @property
    def total_planning_ns(self) -> int:
        return sum(
            phase.duration_ns
            for phase in self.phase_timings
            if phase.duration_ns is not None and phase.phase_name != "execution"
        )


@dataclass(frozen=True)
class PlannerOverheadMeasurement:
    """Compilation result plus diagnostic planner-overhead report."""

    compilation: CompilationResult
    report: PlannerOverheadReport


def measure_pipeline_planner_overhead(
    graph: ComputeGraph,
    backend_capabilities: Iterable[BackendCapability],
    *,
    fallback_backend: str = DEFAULT_FALLBACK_BACKEND,
    transfer_cost_profile: TransferCostProfile | None = None,
    runtime_overrides: RuntimeOverrideSet | None = None,
    include_candidate_scores: bool = False,
) -> PlannerOverheadMeasurement:
    """Compile a graph while timing compiler/planner phases separately."""

    capabilities = tuple(backend_capabilities)
    phase_timings: list[PlannerOverheadPhaseTiming] = [
        _not_measured_phase("graph_construction"),
        _not_measured_phase("frontend_intake"),
    ]

    tlir, duration_ns = _time_call(
        lambda: IRModule(
            stage=IRStage.TLIR,
            graph=graph,
            metadata={"dialect_version": "tlir.v0", "source": "triton-like-python"},
        )
    )
    phase_timings.append(_measured_phase("tlir_module_construction", duration_ns))

    hac_ir, duration_ns = _time_call(lambda: lower_tlir_to_hac(tlir))
    phase_timings.append(_measured_phase("tlir_to_hac_lowering", duration_ns))

    partition_plan, duration_ns = _time_call(
        lambda: partition_graph(
            hac_ir.graph,
            capabilities,
            fallback_backend=fallback_backend,
            transfer_cost_profile=transfer_cost_profile,
            runtime_overrides=runtime_overrides,
            include_candidate_scores=include_candidate_scores,
        )
    )
    phase_timings.append(_measured_phase("runtime_planning", duration_ns))

    decision_report, duration_ns = _time_call(
        lambda: build_compiler_decision_report(
            graph=hac_ir.graph,
            partition_plan=partition_plan,
            backend_capabilities=capabilities,
        )
    )
    phase_timings.append(_measured_phase("backend_selection_report", duration_ns))

    hs_ir, duration_ns = _time_call(lambda: lower_hac_to_hs(hac_ir, partition_plan))
    phase_timings.append(_measured_phase("hs_ir_generation", duration_ns))
    phase_timings.append(_not_measured_phase("execution"))

    diagnostics = tuple(
        f"{assignment.operation_name}->{assignment.backend_name}:{assignment.reason}"
        for assignment in partition_plan.assignments
    )
    compilation = CompilationResult(
        tlir=tlir,
        hac_ir=hac_ir,
        hs_ir=hs_ir,
        partition_plan=partition_plan,
        decision_report=decision_report,
        diagnostics=diagnostics,
    )
    report = build_planner_overhead_report(
        graph_name=graph.name,
        phase_timings=phase_timings,
    )
    return PlannerOverheadMeasurement(compilation=compilation, report=report)


def build_planner_overhead_report(
    *,
    graph_name: str,
    phase_timings: Iterable[PlannerOverheadPhaseTiming],
) -> PlannerOverheadReport:
    """Build a bounded diagnostic planner-overhead report."""

    _validate_report_text(graph_name, "graph_name")
    timings = tuple(phase_timings)
    _validate_phase_timings(timings)
    return PlannerOverheadReport(graph_name=graph_name, phase_timings=timings)


def planner_overhead_report_to_dict(
    report: PlannerOverheadReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible planner-overhead report."""

    _validate_planner_overhead_report(report)
    return {
        "artifact_status": PLANNER_OVERHEAD_ARTIFACT_STATUS,
        "break_even_status": PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "execution_time_status": PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
        "graph_name": report.graph_name,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "phase_timings": [
            {
                "duration_ns": phase.duration_ns,
                "included_in_execution_time": phase.included_in_execution_time,
                "measurement_status": phase.measurement_status,
                "phase_name": phase.phase_name,
            }
            for phase in report.phase_timings
        ],
        "planner_overhead_hidden_in_execution_time": False,
        "schema_version": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
        "total_planning_ns": report.total_planning_ns,
    }


def dump_planner_overhead_report(report: PlannerOverheadReport) -> str:
    """Render a stable diagnostic planner-overhead report."""

    text = json.dumps(planner_overhead_report_to_dict(report), indent=2, sort_keys=True)
    if len(text.encode("utf-8")) > MAX_PLANNER_OVERHEAD_REPORT_BYTES:
        raise ValueError("planner overhead report exceeds byte limit")
    return text + "\n"


def _time_call(callback: Callable[[], _T]) -> tuple[_T, int]:
    start = perf_counter_ns()
    value = callback()
    end = perf_counter_ns()
    duration_ns = end - start
    if duration_ns < 0 or duration_ns > MAX_PLANNER_OVERHEAD_DURATION_NS:
        raise ValueError("planner overhead duration is outside allowed range")
    return value, duration_ns


def _measured_phase(phase_name: str, duration_ns: int) -> PlannerOverheadPhaseTiming:
    return PlannerOverheadPhaseTiming(
        phase_name=phase_name,
        measurement_status="measured",
        duration_ns=duration_ns,
        included_in_execution_time=False,
    )


def _not_measured_phase(phase_name: str) -> PlannerOverheadPhaseTiming:
    return PlannerOverheadPhaseTiming(
        phase_name=phase_name,
        measurement_status="not_measured",
        duration_ns=None,
        included_in_execution_time=False,
    )


def _validate_planner_overhead_report(report: PlannerOverheadReport) -> None:
    if not isinstance(report, PlannerOverheadReport):
        raise TypeError("planner overhead report must be report object")
    _validate_report_text(report.graph_name, "graph_name")
    _validate_phase_timings(report.phase_timings)
    if tuple(report.issues) != PLANNER_OVERHEAD_NOT_MEASURED_ISSUES:
        raise ValueError("planner overhead issues must match diagnostic boundary")


def _validate_phase_timings(
    phase_timings: tuple[PlannerOverheadPhaseTiming, ...],
) -> None:
    if len(phase_timings) > MAX_PLANNER_OVERHEAD_PHASES:
        raise ValueError("planner overhead phase count exceeds limit")
    if tuple(phase.phase_name for phase in phase_timings) != PLANNER_OVERHEAD_PHASES:
        raise ValueError("planner overhead phases must match contract order")
    for phase in phase_timings:
        if not isinstance(phase, PlannerOverheadPhaseTiming):
            raise TypeError("planner overhead phases must be phase timing objects")
        _validate_report_text(phase.phase_name, "phase_name")
        if phase.measurement_status not in _MEASUREMENT_STATUSES:
            raise ValueError("planner overhead measurement status is unsupported")
        if not isinstance(phase.included_in_execution_time, bool):
            raise TypeError("included_in_execution_time must be bool")
        if phase.included_in_execution_time:
            raise ValueError("planner overhead must not be hidden in execution time")
        if phase.phase_name in _REQUIRED_NOT_MEASURED_PHASES:
            if phase.measurement_status != "not_measured" or phase.duration_ns is not None:
                raise ValueError("v0 planner overhead boundary requires unmeasured phase")
            continue
        if phase.measurement_status != "measured":
            raise ValueError("v0 planner overhead boundary requires measured compiler phase")
        if (
            not isinstance(phase.duration_ns, int)
            or isinstance(phase.duration_ns, bool)
            or phase.duration_ns < 0
            or phase.duration_ns > MAX_PLANNER_OVERHEAD_DURATION_NS
        ):
            raise ValueError("measured planner overhead duration is invalid")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe planner-overhead identifier")
    if len(value.encode("utf-8")) > MAX_PLANNER_OVERHEAD_TEXT_BYTES:
        raise ValueError(f"{label} exceeds planner-overhead text limit")


__all__ = [
    "MAX_PLANNER_OVERHEAD_DURATION_NS",
    "MAX_PLANNER_OVERHEAD_PHASES",
    "PLANNER_OVERHEAD_ARTIFACT_STATUS",
    "PLANNER_OVERHEAD_BREAK_EVEN_STATUS",
    "PLANNER_OVERHEAD_EXECUTION_TIME_STATUS",
    "PLANNER_OVERHEAD_NOT_MEASURED_ISSUES",
    "PLANNER_OVERHEAD_PHASES",
    "PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION",
    "PlannerOverheadMeasurement",
    "PlannerOverheadPhaseTiming",
    "PlannerOverheadReport",
    "build_planner_overhead_report",
    "dump_planner_overhead_report",
    "measure_pipeline_planner_overhead",
    "planner_overhead_report_to_dict",
]
