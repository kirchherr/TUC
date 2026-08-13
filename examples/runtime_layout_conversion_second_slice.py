"""Emit a second independent Runtime Layout Conversion Evidence report."""

from tuc import (
    ComputeGraph,
    ComputeOperation,
    OperationKind,
    SystolicArraySimulatorBackend,
    TensorRef,
    VectorSimulatorBackend,
    compile_graph,
)
from tuc.runtime.layout_conversion_evidence import (
    RuntimeLayoutConversionEvidenceReport,
    build_runtime_layout_conversion_evidence_report,
    dump_runtime_layout_conversion_evidence_report,
)


def build_second_slice_graph() -> ComputeGraph:
    """Build a second graph with a planned blocked-to-row-major transition."""

    features = TensorRef("features", (4, 2))
    weights = TensorRef("weights", (2, 2))
    scores = TensorRef("scores", (4, 2))
    totals = TensorRef("totals", (4,))
    activated = TensorRef("activated", (4,))
    return ComputeGraph(
        name="runtime_layout_conversion_reduction_slice",
        operations=(
            ComputeOperation(
                name="score_projection",
                kind=OperationKind.MATMUL,
                inputs=(features, weights),
                outputs=(scores,),
            ),
            ComputeOperation(
                name="reduce_scores",
                kind=OperationKind.REDUCTION,
                inputs=(scores,),
                outputs=(totals,),
                attributes={"axis": 1},
            ),
            ComputeOperation(
                name="activate_totals",
                kind=OperationKind.ELEMENTWISE,
                inputs=(totals,),
                outputs=(activated,),
                attributes={"kernel": "relu"},
            ),
        ),
    )


def build_second_runtime_layout_conversion_evidence_report() -> (
    RuntimeLayoutConversionEvidenceReport
):
    """Return the second data-only layout-conversion evidence report."""

    graph = build_second_slice_graph()
    compiled = compile_graph(
        graph,
        (
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ),
    )
    return build_runtime_layout_conversion_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )


def build_report() -> str:
    """Return the stable serialized second-slice evidence report."""

    return dump_runtime_layout_conversion_evidence_report(
        build_second_runtime_layout_conversion_evidence_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
