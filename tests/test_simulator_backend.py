from __future__ import annotations

import pytest

from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import LayoutKind


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


def test_backend_capability_rejects_invalid_error_budget_attribute() -> None:
    operation = ComputeOperation(
        name="matmul",
        kind=OperationKind.MATMUL,
        inputs=(TensorRef("a", (8, 8)), TensorRef("b", (8, 8))),
        outputs=(TensorRef("c", (8, 8)),),
        attributes={"max_error_budget": "0.01"},
    )
    capability = BackendCapability(
        name="linear",
        supported_ops=frozenset({OperationKind.MATMUL}),
        max_error_budget=0.05,
    )

    with pytest.raises(ValueError, match="finite non-negative number"):
        capability.supports(operation)


def test_backend_capability_rejects_inconsistent_preference() -> None:
    with pytest.raises(ValueError, match="preferred_for must be a subset"):
        BackendCapability(
            name="bad",
            supported_ops=frozenset({OperationKind.ELEMENTWISE}),
            preferred_for=frozenset({OperationKind.MATMUL}),
        )


def test_backend_capability_rejects_empty_layout_set() -> None:
    with pytest.raises(ValueError, match="supported_layouts"):
        BackendCapability(
            name="bad",
            supported_ops=frozenset({OperationKind.ELEMENTWISE}),
            supported_layouts=frozenset(),
        )


def test_backend_capability_checks_operation_layout() -> None:
    operation = ComputeOperation(
        name="activation",
        kind=OperationKind.ELEMENTWISE,
        inputs=(TensorRef("x", (8, 8)),),
        outputs=(TensorRef("y", (8, 8)),),
        attributes={"tuc.layout": LayoutKind.BLOCKED.value},
    )
    capability = BackendCapability(
        name="row_major_only",
        supported_ops=frozenset({OperationKind.ELEMENTWISE}),
        supported_layouts=frozenset({LayoutKind.ROW_MAJOR}),
    )

    assert capability.supports(operation) is False
