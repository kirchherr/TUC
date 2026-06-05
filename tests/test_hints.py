from __future__ import annotations

import pytest

from tuc.frontend import CompilationHints


def test_hints_are_serialized_as_metadata() -> None:
    hints = CompilationHints(
        robust_to_noise=True,
        prefer_sparsity=True,
        max_error_budget=0.01,
    )

    assert hints.to_metadata() == {
        "robust_to_noise": True,
        "prefer_sparsity": True,
        "prefer_analog_linear": False,
        "max_error_budget": 0.01,
    }


def test_negative_error_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        CompilationHints(max_error_budget=-0.1)
