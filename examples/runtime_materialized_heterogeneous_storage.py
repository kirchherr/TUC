"""Emit proof that heterogeneous storage planning governs trusted execution."""

from __future__ import annotations

import numpy as np

try:
    from examples.runtime_heterogeneous_storage_plan import build_graph
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from runtime_heterogeneous_storage_plan import build_graph  # type: ignore[no-redef]

from tuc import (
    RuntimeMaterializedHeterogeneousStorageReport,
    SystolicArraySimulatorBackend,
    build_runtime_backend_equivalence_report,
    build_runtime_heterogeneous_storage_plan_report,
    build_runtime_materialized_heterogeneous_storage_report,
    build_runtime_materialized_layout_conversion_report,
    build_runtime_materialized_transfer_report,
    build_runtime_reference_correctness_report,
    compile_graph,
    dump_runtime_materialized_heterogeneous_storage_report,
    execute_graph,
    execute_graph_with_materialized_heterogeneous_storage,
)
from tuc.report_output import emit_public_json_report


def proof_inputs() -> dict[str, np.ndarray]:
    """Return deterministic odd-shape inputs with positive and negative results."""

    return {
        "lhs_a": np.array(
            [[1.0, -2.0, 3.0], [-4.0, 5.0, -6.0], [7.0, -8.0, 9.0]],
            dtype=np.float64,
        ),
        "rhs_a": np.array(
            [[1.0, 0.0, -1.0], [0.0, 1.0, 0.0], [1.0, 0.0, 1.0]],
            dtype=np.float64,
        ),
        "lhs_b": np.array(
            [[-9.0, 8.0, -7.0], [6.0, -5.0, 4.0], [-3.0, 2.0, -1.0]],
            dtype=np.float64,
        ),
        "rhs_b": np.array(
            [[0.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, -1.0, 0.0]],
            dtype=np.float64,
        ),
    }


def build_current_runtime_materialized_heterogeneous_storage_report() -> (
    RuntimeMaterializedHeterogeneousStorageReport
):
    """Execute and bind the canonical double-slice storage-reuse proof."""

    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, ())
    candidate = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    storage_plan = build_runtime_heterogeneous_storage_plan_report(
        candidate.hac_ir.graph,
        candidate.partition_plan,
    )
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    materialized = execute_graph_with_materialized_heterogeneous_storage(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
        storage_plan,
    )
    correctness = build_runtime_reference_correctness_report(
        graph,
        materialized.execution,
        {
            "activated_a": np.maximum(inputs["lhs_a"] @ inputs["rhs_a"], 0.0),
            "activated_b": np.maximum(inputs["lhs_b"] @ inputs["rhs_b"], 0.0),
        },
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        materialized.execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="materialized_heterogeneous_storage",
    )
    layout_conversion = build_runtime_materialized_layout_conversion_report(
        graph,
        candidate.partition_plan,
        materialized.execution,
        equivalence,
    )
    transfer = build_runtime_materialized_transfer_report(
        graph,
        candidate.partition_plan,
        materialized.execution,
        equivalence,
        layout_conversion,
    )
    return build_runtime_materialized_heterogeneous_storage_report(
        graph,
        candidate.partition_plan,
        storage_plan,
        materialized,
        correctness,
        equivalence,
        layout_conversion,
        transfer,
    )


def build_report() -> str:
    """Return stable metadata-only JSON evidence."""

    return dump_runtime_materialized_heterogeneous_storage_report(
        build_current_runtime_materialized_heterogeneous_storage_report()
    )


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
