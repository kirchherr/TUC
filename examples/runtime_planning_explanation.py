"""Emit Runtime Planning Explanation evidence for the systolic proof plan."""

from __future__ import annotations

try:
    from examples.proof_of_systolic_execution import build_graph
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from proof_of_systolic_execution import build_graph

from tuc import (
    RuntimePlanningExplanationReport,
    SystolicArraySimulatorBackend,
    build_runtime_planning_explanation_report,
    compile_graph,
    dump_runtime_planning_explanation_report,
)


def build_systolic_runtime_planning_explanation_report() -> RuntimePlanningExplanationReport:
    """Return planning explanation evidence for the systolic proof graph."""

    result = compile_graph(
        build_graph(),
        [SystolicArraySimulatorBackend().capability],
        include_candidate_scores=True,
    )
    return build_runtime_planning_explanation_report(result.partition_plan)


def main() -> None:
    print(
        dump_runtime_planning_explanation_report(
            build_systolic_runtime_planning_explanation_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
