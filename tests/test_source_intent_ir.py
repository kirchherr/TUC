from __future__ import annotations

from pathlib import Path

import pytest

from tuc.frontend import (
    SOURCE_INTENT_IR_CONTRACT,
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentTensor,
)


def test_source_intent_module_dump_is_deterministic() -> None:
    module = _source_intent_module()

    assert module.contract == SOURCE_INTENT_IR_CONTRACT
    assert module.dump() == Path("tests/golden/frontend/source_intent_ir.txt").read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_source_intent_ir_has_no_lowering_exit() -> None:
    module = _source_intent_module()
    source = Path("src/tuc/frontend/source_intent.py").read_text(encoding="utf-8")

    assert not hasattr(module, "to_compute_graph")
    assert not hasattr(module, "to_metadata")
    assert "tuc.ir" not in source


def test_source_intent_operation_rejects_hardware_family() -> None:
    with pytest.raises(ValueError, match="unsupported source-intent operation family"):
        SourceIntentOperation(
            name="projection",
            family="gpu",
            inputs=("a", "b"),
            outputs=("c",),
        )


@pytest.mark.parametrize(
    "hint",
    [
        {"prefer_analog_linear": True},
        {"tuc.backend": "gpu"},
        {"backend": "gpu"},
        {"python_source": "def kernel(): pass"},
    ],
)
def test_source_intent_hints_reject_execution_and_hardware_keys(
    hint: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        SourceIntentOperation(
            name="projection",
            family="matmul",
            inputs=("a", "b"),
            outputs=("c",),
            hints=hint,
        )


def test_source_intent_module_rejects_unknown_tensor_reference() -> None:
    with pytest.raises(ValueError, match="references unknown tensor"):
        SourceIntentModule(
            name="bad_source",
            tensors=(SourceIntentTensor("a", (2, 3)),),
            operations=(
                SourceIntentOperation(
                    name="projection",
                    family="matmul",
                    inputs=("a", "missing"),
                    outputs=("a",),
                ),
            ),
        )


def _source_intent_module() -> SourceIntentModule:
    return SourceIntentModule(
        name="mvp_kernel",
        tensors=(
            SourceIntentTensor("a", (2, 3)),
            SourceIntentTensor("b", (3, 4)),
            SourceIntentTensor("c", (2, 4)),
            SourceIntentTensor("y", (2, 4)),
        ),
        operations=(
            SourceIntentOperation(
                name="projection",
                family="matmul",
                inputs=("a", "b"),
                outputs=("c",),
                hints={
                    "max_error_budget": 0.02,
                    "prefer_linear_accelerator": True,
                },
            ),
            SourceIntentOperation(
                name="activation",
                family="elementwise",
                inputs=("c",),
                outputs=("y",),
            ),
        ),
    )
