"""Backend interfaces and reference implementations."""

from tuc.backends.base import Backend, BackendCapability, LoweringResult
from tuc.backends.conformance import (
    MVP_CONFORMANCE_OPERATION_KINDS,
    BackendConformanceError,
    BackendConformanceIssue,
    BackendConformanceReport,
    assert_backend_conformance,
    build_conformance_graph,
    run_backend_conformance,
)
from tuc.backends.simulator import LinearAlgebraSimulatorBackend

__all__ = [
    "Backend",
    "BackendCapability",
    "BackendConformanceError",
    "BackendConformanceIssue",
    "BackendConformanceReport",
    "LinearAlgebraSimulatorBackend",
    "LoweringResult",
    "MVP_CONFORMANCE_OPERATION_KINDS",
    "assert_backend_conformance",
    "build_conformance_graph",
    "run_backend_conformance",
]
