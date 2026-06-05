from __future__ import annotations

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, IRStage, OperationKind, TensorRef


def test_pipeline_lowers_through_all_three_ir_stages() -> None:
    a = TensorRef("a", (16, 32))
    b = TensorRef("b", (32, 8))
    c = TensorRef("c", (16, 8))
    y = TensorRef("y", (16, 8))
    graph = ComputeGraph(
        name="mlp",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.01},
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(c,),
                outputs=(y,),
            ),
        ),
    )

    result = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])

    assert result.tlir.stage is IRStage.TLIR
    assert result.hac_ir.stage is IRStage.HAC_IR
    assert result.hs_ir.stage is IRStage.HS_IR
    assert result.partition_plan.backend_for("projection") == "linear-sim"
    assert result.partition_plan.backend_for("activation") == "gpu"
    assert result.hac_ir.graph.operations[0].attributes["tuc.linearity"] == "linear"
    assert result.hac_ir.graph.operations[0].attributes["tuc.bytes_read"] == 3072
    assert result.hac_ir.graph.operations[0].attributes["tuc.bytes_written"] == 512
    assert result.hac_ir.graph.metadata["movement_model"] == "movement.v0"
    assert result.hs_ir.graph.operations[0].attributes["tuc.assigned_backend"] == "linear-sim"
    assert result.hs_ir.graph.operations[0].attributes["tuc.bytes_read"] == 3072
    assert result.hs_ir.graph.metadata["movement_summary"] == {
        "arithmetic_intensity": 8320 / 4608,
        "movement_model": "movement.v0",
        "operation_count": 2,
        "total_arithmetic_ops": 8320,
        "total_bytes_read": 3584,
        "total_bytes_written": 1024,
    }
    assert "projection->linear-sim:preferred_for:matmul" in result.diagnostics


def test_pipeline_dumps_are_keyed_by_stage_name() -> None:
    x = TensorRef("x", (8, 8))
    y = TensorRef("y", (8, 8))
    graph = ComputeGraph(
        name="elementwise",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(x,),
                outputs=(y,),
            ),
        ),
    )

    result = compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])

    assert set(result.dumps()) == {"tlir", "hac-ir", "hs-ir"}
    assert "hs-ir.module @elementwise" in result.dump(IRStage.HS_IR)
