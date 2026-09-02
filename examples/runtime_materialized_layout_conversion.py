"""Emit trusted simulator materialized-layout-conversion evidence."""

try:
    from examples.runtime_mixed_backend_equivalence import build_graph, proof_inputs
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_mixed_backend_equivalence import (  # type: ignore[no-redef]
        build_graph,
        proof_inputs,
    )

from tuc import (
    RuntimeMaterializedLayoutConversionReport,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
    build_runtime_backend_equivalence_report,
    build_runtime_materialized_layout_conversion_report,
    compile_graph,
    dump_runtime_materialized_layout_conversion_report,
    execute_graph,
    execute_graph_with_materialized_layouts,
)
from tuc.report_output import emit_public_json_report


def build_current_runtime_materialized_layout_conversion_report() -> (
    RuntimeMaterializedLayoutConversionReport
):
    """Execute one mixed placement and bind conversion to equivalence evidence."""

    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, ())
    candidate = compile_graph(
        graph,
        (
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ),
    )
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph_with_materialized_layouts(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        candidate_execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="materialized_mixed_simulators",
    )
    return build_runtime_materialized_layout_conversion_report(
        graph,
        candidate.partition_plan,
        candidate_execution,
        equivalence,
    )


def build_report() -> str:
    """Return stable metadata-only JSON evidence."""

    return dump_runtime_materialized_layout_conversion_report(
        build_current_runtime_materialized_layout_conversion_report()
    )


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
