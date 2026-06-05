from __future__ import annotations

from tuc.ir import ComputeGraph, ComputeOperation, IRModule, IRStage, OperationKind, TensorRef
from tuc.ir.dump import dump_module


def test_dump_module_is_deterministic_and_stage_aware() -> None:
    a = TensorRef("a", (4, 8))
    b = TensorRef("b", (8, 2))
    c = TensorRef("c", (4, 2))
    graph = ComputeGraph(
        name="projection",
        operations=(
            ComputeOperation(
                name="matmul",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"z": True, "a": "first"},
            ),
        ),
    )
    module = IRModule(stage=IRStage.TLIR, graph=graph, metadata={"dialect_version": "tlir.v0"})

    dumped = dump_module(module)

    assert dumped.splitlines()[0] == "tlir.module @projection {"
    assert 'module.dialect_version = "tlir.v0"' in dumped
    assert "tuc.matmul @matmul" in dumped
    assert '{a = "first", z = true}' in dumped
