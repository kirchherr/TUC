from __future__ import annotations

import pytest

from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef


def test_tensor_ref_rejects_dump_unsafe_names() -> None:
    with pytest.raises(ValueError, match="simple identifier"):
        TensorRef("bad-name", (8, 8))


def test_tensor_ref_rejects_unbounded_or_bool_dimensions() -> None:
    with pytest.raises(ValueError, match="positive bounded integers"):
        TensorRef("x", (True, 8))

    with pytest.raises(ValueError, match="positive bounded integers"):
        TensorRef("x", (2**31, 8))


def test_operation_attributes_are_frozen_and_canonicalized() -> None:
    operation = ComputeOperation(
        name="activation",
        kind=OperationKind.ELEMENTWISE,
        inputs=(TensorRef("x", (8, 8)),),
        outputs=(TensorRef("y", (8, 8)),),
        attributes={"nested": {"b": 2, "a": 1}},
    )

    assert operation.attributes["nested"] == {"a": 1, "b": 2}
    with pytest.raises(TypeError):
        operation.attributes["late_mutation"] = True  # type: ignore[index]


def test_operation_attributes_reject_unsupported_values() -> None:
    with pytest.raises(TypeError, match="unsupported IR attribute type"):
        ComputeOperation(
            name="activation",
            kind=OperationKind.ELEMENTWISE,
            inputs=(TensorRef("x", (8, 8)),),
            outputs=(TensorRef("y", (8, 8)),),
            attributes={"callable": lambda value: value},
        )


def test_graph_rejects_duplicate_operations_and_inconsistent_tensors() -> None:
    x = TensorRef("x", (8, 8))
    y = TensorRef("y", (8, 8))
    z = TensorRef("z", (8, 8))
    duplicate_a = ComputeOperation(
        name="activation",
        kind=OperationKind.ELEMENTWISE,
        inputs=(x,),
        outputs=(y,),
    )
    duplicate_b = ComputeOperation(
        name="activation",
        kind=OperationKind.ELEMENTWISE,
        inputs=(y,),
        outputs=(z,),
    )

    with pytest.raises(ValueError, match="operation names must be unique"):
        ComputeGraph(name="bad_graph", operations=(duplicate_a, duplicate_b))

    inconsistent = ComputeOperation(
        name="second",
        kind=OperationKind.ELEMENTWISE,
        inputs=(TensorRef("y", (4, 4)),),
        outputs=(z,),
    )
    with pytest.raises(ValueError, match="inconsistent shape or dtype"):
        ComputeGraph(name="bad_graph", operations=(duplicate_a, inconsistent))
