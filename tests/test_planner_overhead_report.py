from __future__ import annotations

import json

import pytest

from examples.phase1_ir_pipeline import build_graph
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.benchmarks import (
    PLANNER_OVERHEAD_ARTIFACT_STATUS,
    PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
    PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
    PLANNER_OVERHEAD_NOT_MEASURED_ISSUES,
    PLANNER_OVERHEAD_PHASES,
    PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
    PlannerOverheadPhaseTiming,
    build_planner_overhead_report,
    dump_planner_overhead_report,
    measure_pipeline_planner_overhead,
    planner_overhead_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT


def test_measure_pipeline_planner_overhead_separates_phases() -> None:
    simulator = LinearAlgebraSimulatorBackend()
    measurement = measure_pipeline_planner_overhead(
        build_graph(),
        [simulator.capability],
    )
    report = measurement.report
    payload = planner_overhead_report_to_dict(report)

    assert measurement.compilation.partition_plan.backend_for("dense_projection") == (
        "linear-sim"
    )
    assert tuple(phase.phase_name for phase in report.phase_timings) == (
        PLANNER_OVERHEAD_PHASES
    )
    assert payload["schema_version"] == PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == PLANNER_OVERHEAD_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["execution_time_status"] == PLANNER_OVERHEAD_EXECUTION_TIME_STATUS
    assert payload["break_even_status"] == PLANNER_OVERHEAD_BREAK_EVEN_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["planner_overhead_hidden_in_execution_time"] is False
    assert payload["issues"] == list(PLANNER_OVERHEAD_NOT_MEASURED_ISSUES)
    assert payload["total_planning_ns"] > 0

    execution_phase = report.phase_timings[-1]
    assert execution_phase.phase_name == "execution"
    assert execution_phase.measurement_status == "not_measured"
    assert execution_phase.duration_ns is None


def test_planner_overhead_report_is_json_serializable() -> None:
    simulator = LinearAlgebraSimulatorBackend()
    measurement = measure_pipeline_planner_overhead(
        build_graph(),
        [simulator.capability],
    )

    payload = json.loads(dump_planner_overhead_report(measurement.report))

    assert payload["graph_name"] == "phase1_mlp_block"
    assert len(payload["phase_timings"]) == len(PLANNER_OVERHEAD_PHASES)
    assert payload["phase_timings"][0]["duration_ns"] is None


def test_planner_overhead_report_rejects_hidden_execution_time() -> None:
    phases = tuple(
        PlannerOverheadPhaseTiming(
            phase_name=phase,
            measurement_status=(
                "not_measured"
                if phase in {"graph_construction", "frontend_intake", "execution"}
                else "measured"
            ),
            duration_ns=(
                None
                if phase in {"graph_construction", "frontend_intake", "execution"}
                else 1
            ),
            included_in_execution_time=(phase == "execution"),
        )
        for phase in PLANNER_OVERHEAD_PHASES
    )

    with pytest.raises(ValueError, match="hidden in execution time"):
        build_planner_overhead_report(
            graph_name="bad_hidden_overhead",
            phase_timings=phases,
        )


def test_planner_overhead_report_rejects_wrong_phase_order() -> None:
    phases = tuple(
        PlannerOverheadPhaseTiming(
            phase_name=phase,
            measurement_status="not_measured",
            duration_ns=None,
        )
        for phase in reversed(PLANNER_OVERHEAD_PHASES)
    )

    with pytest.raises(ValueError, match="phases must match contract order"):
        build_planner_overhead_report(
            graph_name="bad_phase_order",
            phase_timings=phases,
        )


def test_planner_overhead_report_rejects_unmeasured_duration() -> None:
    phases = tuple(
        PlannerOverheadPhaseTiming(
            phase_name=phase,
            measurement_status=(
                "not_measured"
                if phase in {"graph_construction", "frontend_intake", "execution"}
                else "measured"
            ),
            duration_ns=(
                1
                if phase == "execution"
                else (
                    None
                    if phase in {"graph_construction", "frontend_intake"}
                    else 1
                )
            ),
        )
        for phase in PLANNER_OVERHEAD_PHASES
    )

    with pytest.raises(ValueError, match="requires unmeasured phase"):
        build_planner_overhead_report(
            graph_name="bad_unmeasured_duration",
            phase_timings=phases,
        )
