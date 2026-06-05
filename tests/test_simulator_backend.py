from __future__ import annotations

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef


def test_simulator_lowers_supported_graph() -> None:
    a = TensorRef("a", (8, 8))
    b = TensorRef("b", (8, 8))
    c = TensorRef("c", (8, 8))
    graph = ComputeGraph(
        name="linear",
        operations=(
            ComputeOperation(
                name="matmul",
                kind=OperationKind.MATMUL,
                inputs=(a, b),
                outputs=(c,),
                attributes={"max_error_budget": 0.01},
            ),
        ),
    )

    lowered = LinearAlgebraSimulatorBackend().lower(graph)

    assert lowered.backend_name == "linear-sim"
    assert "matmul matmul" in lowered.artifact
    assert "noise_model=enabled" in lowered.diagnostics


def test_simulator_rejects_unsupported_operation() -> None:
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

    with pytest.raises(ValueError, match="cannot lower"):
        LinearAlgebraSimulatorBackend().lower(graph)
