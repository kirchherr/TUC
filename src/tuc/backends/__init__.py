"""Backend interfaces and reference implementations."""

from tuc.backends.base import Backend, BackendCapability, LoweringResult
from tuc.backends.simulator import LinearAlgebraSimulatorBackend

__all__ = [
    "Backend",
    "BackendCapability",
    "LinearAlgebraSimulatorBackend",
    "LoweringResult",
]
