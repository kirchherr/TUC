"""Emit Runtime Buffer Lifetime Report v0."""

from tuc import (
    ComputeGraph,
    ComputeOperation,
    MemoryDomainKind,
    OperationKind,
    RuntimeBufferLifetimeReport,
    TensorRef,
    build_runtime_buffer_lifetime_report,
    compile_graph,
    dump_runtime_buffer_lifetime_report,
)
from tuc.backends import BackendCapability


def build_current_runtime_buffer_lifetime_report() -> RuntimeBufferLifetimeReport:
    """Build the current runtime buffer lifetime report."""

    graph = _buffer_lifetime_graph()
    backend = BackendCapability(
        name="reference-cpu",
        supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.HOST_RAM,
    )
    compiled = compile_graph(graph, (backend,))
    return build_runtime_buffer_lifetime_report(graph, compiled.partition_plan)


def main() -> None:
    print(
        dump_runtime_buffer_lifetime_report(
            build_current_runtime_buffer_lifetime_report()
        ),
        end="",
    )


def _buffer_lifetime_graph() -> ComputeGraph:
    lhs_a = TensorRef("lhs_a", (4, 4))
    rhs_a = TensorRef("rhs_a", (4, 4))
    lhs_b = TensorRef("lhs_b", (4, 4))
    rhs_b = TensorRef("rhs_b", (4, 4))
    left_tmp = TensorRef("left_tmp", (4, 4))
    left_out = TensorRef("left_out", (4, 4))
    right_tmp = TensorRef("right_tmp", (4, 4))
    right_out = TensorRef("right_out", (4, 4))
    return ComputeGraph(
        name="runtime_buffer_lifetime",
        operations=(
            ComputeOperation(
                name="left_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs_a, rhs_a),
                outputs=(left_tmp,),
            ),
            ComputeOperation(
                name="left_activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(left_tmp,),
                outputs=(left_out,),
            ),
            ComputeOperation(
                name="right_projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs_b, rhs_b),
                outputs=(right_tmp,),
            ),
            ComputeOperation(
                name="right_activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(right_tmp,),
                outputs=(right_out,),
            ),
        ),
    )


if __name__ == "__main__":
    main()
