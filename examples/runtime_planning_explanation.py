"""Emit Runtime Planning Explanation evidence for proof runtime plans."""

from __future__ import annotations

try:
    from examples.proof_of_systolic_execution import build_graph
    from examples.runtime_backend_equivalence import (
        build_graph as build_backend_equivalence_graph,
    )
    from examples.runtime_mixed_backend_equivalence import (
        build_graph as build_mixed_backend_equivalence_graph,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from proof_of_systolic_execution import build_graph
    from runtime_backend_equivalence import (
        build_graph as build_backend_equivalence_graph,
    )
    from runtime_mixed_backend_equivalence import (
        build_graph as build_mixed_backend_equivalence_graph,
    )

from tuc import (
    RuntimePlanningExplanationReport,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
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


def build_backend_equivalence_runtime_planning_explanation_report() -> (
    RuntimePlanningExplanationReport
):
    """Return planning explanation evidence for backend-equivalence placement."""

    result = compile_graph(
        build_backend_equivalence_graph(),
        [SystolicArraySimulatorBackend().capability],
        include_candidate_scores=True,
    )
    return build_runtime_planning_explanation_report(result.partition_plan)


def build_mixed_backend_equivalence_runtime_planning_explanation_report() -> (
    RuntimePlanningExplanationReport
):
    """Return planning explanation evidence for mixed-accelerator placement."""

    result = compile_graph(
        build_mixed_backend_equivalence_graph(),
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
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
