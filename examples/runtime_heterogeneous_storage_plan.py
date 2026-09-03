"""Emit data-only heterogeneous storage and transfer-staging evidence."""

from tuc import (
    ComputeGraph,
    ComputeOperation,
    OperationKind,
    SystolicArraySimulatorBackend,
    TensorRef,
    build_runtime_heterogeneous_storage_plan_report,
    compile_graph,
    dump_runtime_heterogeneous_storage_plan_report,
)
from tuc.report_output import emit_public_json_report
from tuc.runtime import RuntimeHeterogeneousStoragePlanReport


def build_graph() -> ComputeGraph:
    """Build two non-overlapping odd-shape heterogeneous transfer slices."""

    lhs_a = TensorRef("lhs_a", (3, 3))
    rhs_a = TensorRef("rhs_a", (3, 3))
    projection_a = TensorRef("projection_a", (3, 3))
    activated_a = TensorRef("activated_a", (3, 3))
    lhs_b = TensorRef("lhs_b", (3, 3))
    rhs_b = TensorRef("rhs_b", (3, 3))
    projection_b = TensorRef("projection_b", (3, 3))
    activated_b = TensorRef("activated_b", (3, 3))
    return ComputeGraph(
        name="runtime_heterogeneous_storage_plan",
        operations=(
            ComputeOperation(
                name="projection_a",
                kind=OperationKind.MATMUL,
                inputs=(lhs_a, rhs_a),
                outputs=(projection_a,),
            ),
            ComputeOperation(
                name="activation_a",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection_a,),
                outputs=(activated_a,),
                attributes={"kernel": "relu"},
            ),
            ComputeOperation(
                name="projection_b",
                kind=OperationKind.MATMUL,
                inputs=(lhs_b, rhs_b),
                outputs=(projection_b,),
            ),
            ComputeOperation(
                name="activation_b",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection_b,),
                outputs=(activated_b,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def build_current_runtime_heterogeneous_storage_plan_report() -> (
    RuntimeHeterogeneousStoragePlanReport
):
    """Compile the proof graph and derive its physical storage plan."""

    graph = build_graph()
    compiled = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    return build_runtime_heterogeneous_storage_plan_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )


def build_report() -> str:
    """Return stable metadata-only JSON evidence."""

    return dump_runtime_heterogeneous_storage_plan_report(
        build_current_runtime_heterogeneous_storage_plan_report()
    )


def main() -> None:
    emit_public_json_report(build_report())


if __name__ == "__main__":
    main()
