"""Emit trusted simulator materialized-transfer evidence."""

try:
    from examples.runtime_backend_equivalence import build_graph, proof_inputs
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_backend_equivalence import (  # type: ignore[no-redef]
        build_graph,
        proof_inputs,
    )

from tuc import (
    RuntimeMaterializedTransferReport,
    SystolicArraySimulatorBackend,
    build_runtime_backend_equivalence_report,
    build_runtime_materialized_layout_conversion_report,
    build_runtime_materialized_transfer_report,
    compile_graph,
    dump_runtime_materialized_transfer_report,
    execute_graph,
    execute_graph_with_materialized_data_movement,
)
from tuc.report_output import emit_public_json_report


def build_current_runtime_materialized_transfer_report() -> (
    RuntimeMaterializedTransferReport
):
    """Execute and bind one transfer plus its required layout conversion."""

    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, ())
    candidate = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph_with_materialized_data_movement(
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
        candidate_run_id="materialized_systolic_transfer",
    )
    layout_conversion = build_runtime_materialized_layout_conversion_report(
        graph,
        candidate.partition_plan,
        candidate_execution,
        equivalence,
    )
    return build_runtime_materialized_transfer_report(
        graph,
        candidate.partition_plan,
        candidate_execution,
        equivalence,
        layout_conversion,
    )


def build_report() -> str:
    """Return stable metadata-only JSON evidence."""

    return dump_runtime_materialized_transfer_report(
        build_current_runtime_materialized_transfer_report()
    )


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
