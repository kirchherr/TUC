"""Emit Runtime Materialized Allocation Report v0."""

from __future__ import annotations

import numpy as np

from examples.runtime_allocation_admission import (
    build_current_runtime_allocation_admission_report,
)
from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_allocation_receipt import (
    build_current_runtime_allocation_receipt_report,
)
from examples.runtime_allocation_reconciliation import (
    build_current_runtime_allocation_reconciliation_report,
)
from examples.runtime_allocation_request_manifest import (
    build_current_runtime_allocation_request_manifest_report,
)
from examples.runtime_buffer_lifetime import build_graph
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from tuc import (
    MemoryDomainKind,
    OperationKind,
    RuntimeAllocationExecutionPrerequisites,
    RuntimeMaterializedAllocationReport,
    build_runtime_materialized_allocation_report,
    build_runtime_reference_correctness_report,
    compile_graph,
    dump_runtime_materialized_allocation_report,
    execute_graph_with_materialized_allocations,
)
from tuc.backends import BackendCapability


def build_current_runtime_materialized_allocation_report() -> (
    RuntimeMaterializedAllocationReport
):
    """Execute and bind the canonical exact-match slot-reuse proof."""

    graph = build_graph()
    backend = BackendCapability(
        name="reference-cpu",
        supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.HOST_RAM,
    )
    compiled = compile_graph(graph, (backend,))
    prerequisites = RuntimeAllocationExecutionPrerequisites(
        allocation_plan=build_current_runtime_allocation_plan_report(),
        memory_budget=build_current_runtime_memory_budget_report(),
        request_manifest=build_current_runtime_allocation_request_manifest_report(),
        admission=build_current_runtime_allocation_admission_report(),
        receipt=build_current_runtime_allocation_receipt_report(),
        reconciliation=build_current_runtime_allocation_reconciliation_report(),
    )
    inputs = proof_inputs()
    materialized = execute_graph_with_materialized_allocations(
        graph,
        compiled.partition_plan,
        inputs,
        prerequisites,
    )
    correctness = build_runtime_reference_correctness_report(
        graph,
        materialized.execution,
        {
            "left_out": inputs["lhs_a"] @ inputs["rhs_a"],
            "right_out": inputs["lhs_b"] @ inputs["rhs_b"],
        },
    )
    return build_runtime_materialized_allocation_report(
        graph,
        compiled.partition_plan,
        prerequisites,
        materialized,
        correctness,
    )


def proof_inputs() -> dict[str, np.ndarray]:
    """Return deterministic finite float64 inputs for the reuse proof."""

    return {
        "lhs_a": np.arange(1, 17, dtype=np.float64).reshape(4, 4),
        "rhs_a": np.eye(4, dtype=np.float64),
        "lhs_b": np.arange(-8, 8, dtype=np.float64).reshape(4, 4),
        "rhs_b": np.flipud(np.eye(4, dtype=np.float64)),
    }


def main() -> None:
    print(
        dump_runtime_materialized_allocation_report(
            build_current_runtime_materialized_allocation_report()
        ),
        end="",
    )


if __name__ == "__main__":
    main()
