"""Developer-facing hardware-agnostic compilation hints."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompilationHints:
    """Optional hints that must not change mathematical correctness."""

    robust_to_noise: bool = False
    prefer_sparsity: bool = False
    prefer_analog_linear: bool = False
    max_error_budget: float | None = None

    def __post_init__(self) -> None:
        if self.max_error_budget is not None and self.max_error_budget < 0:
            raise ValueError("max_error_budget must be non-negative")

    def to_metadata(self) -> dict[str, bool | float]:
        metadata: dict[str, bool | float] = {
            "robust_to_noise": self.robust_to_noise,
            "prefer_sparsity": self.prefer_sparsity,
            "prefer_analog_linear": self.prefer_analog_linear,
        }
        if self.max_error_budget is not None:
            metadata["max_error_budget"] = self.max_error_budget
        return metadata
