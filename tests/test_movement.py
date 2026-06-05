from __future__ import annotations

import pytest

from tuc.compiler.movement import (
    MOVEMENT_MODEL_VERSION,
    annotate_graph_movement,
    estimate_operation_movement,
    summarize_graph_movement,
)
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef, dtype_size_bytes


def test_dtype_size_bytes_rejects_unknown_dtype() -> None:
    assert dtype_size_bytes("float32") == 4
    assert dtype_size_bytes("bf16") == 2

    with pytest.raises(ValueError, match="unsupported tensor dtype"):
        dtype_size_bytes("object")


def test_matmul_movement_estimate_is_shape_and_dtype_aware() -> None:
    a = TensorRef("a", (16, 32), dtype="float32")
    b = TensorRef("b", (32, 8), dtype="float16")
    c = TensorRef("c", (16, 8), dtype="float32")
    operation = ComputeOperation(
        name="projection",
        kind=OperationKind.MATMUL,
        inputs=(a, b),
        outputs=(c,),
    )

    estimate = estimate_operation_movement(operation)

    assert estimate.bytes_read == (16 * 32 * 4) + (32 * 8 * 2)
    assert estimate.bytes_written == 16 * 8 * 4
    assert estimate.arithmetic_ops == 2 * 16 * 8 * 32
    assert estimate.arithmetic_intensity == pytest.approx(8192 / 3072)


def test_matmul_movement_estimate_rejects_shape_mismatch() -> None:
    operation = ComputeOperation(
        name="bad_projection",
        kind=OperationKind.MATMUL,
        inputs=(TensorRef("a", (16, 32)), TensorRef("b", (31, 8))),
        outputs=(TensorRef("c", (16, 8)),),
    )

    with pytest.raises(ValueError, match="matmul input dimensions must agree"):
        estimate_operation_movement(operation)


def test_movement_estimate_rejects_bool_dimensions() -> None:
    operation = ComputeOperation(
        name="bad_tensor",
        kind=OperationKind.ELEMENTWISE,
        inputs=(TensorRef("x", (True, 8)),),
        outputs=(TensorRef("y", (1, 8)),),
    )

    with pytest.raises(ValueError, match="positive integers"):
        estimate_operation_movement(operation)


def test_movement_annotations_preserve_declarative_backend_hints() -> None:
    graph = ComputeGraph(
        name="analog_hint",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(TensorRef("a", (8, 8)), TensorRef("b", (8, 8))),
                outputs=(TensorRef("c", (8, 8)),),
                attributes={"prefer_analog_linear": True},
            ),
        ),
    )

    annotated = annotate_graph_movement(graph)
    operation = annotated.operations[0]

    assert annotated.metadata["movement_model"] == MOVEMENT_MODEL_VERSION
    assert operation.attributes["tuc.preferred_memory_domain"] == "analog_weight_bank"
    assert operation.attributes["tuc.layout"] == "row_major"
    assert operation.attributes["prefer_analog_linear"] is True


def test_summarize_graph_movement_fails_closed_for_unannotated_graph() -> None:
    graph = ComputeGraph(
        name="unannotated",
        operations=(
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(TensorRef("x", (8, 8)),),
                outputs=(TensorRef("y", (8, 8)),),
            ),
        ),
    )

    with pytest.raises(ValueError, match="missing valid tuc.bytes_read"):
        summarize_graph_movement(graph)
