"""Backend interfaces and reference implementations."""

from tuc.backends.base import Backend, BackendCapability, LoweringResult
from tuc.backends.conformance import (
    CONFORMANCE_REPORT_SCHEMA_VERSION,
    MVP_CONFORMANCE_OPERATION_KINDS,
    BackendConformanceError,
    BackendConformanceIssue,
    BackendConformanceReport,
    assert_backend_conformance,
    build_conformance_graph,
    conformance_report_to_dict,
    dump_backend_conformance_report,
    run_backend_conformance,
)
from tuc.backends.registry import (
    BackendRegistration,
    BackendRegistry,
    BackendRegistryError,
    BackendSupportDiagnostic,
)
from tuc.backends.simulator import LinearAlgebraSimulatorBackend

__all__ = [
    "Backend",
    "BackendCapability",
    "BackendConformanceError",
    "BackendConformanceIssue",
    "BackendConformanceReport",
    "BackendRegistration",
    "BackendRegistry",
    "BackendRegistryError",
    "BackendSupportDiagnostic",
    "CONFORMANCE_REPORT_SCHEMA_VERSION",
    "LinearAlgebraSimulatorBackend",
    "LoweringResult",
    "MVP_CONFORMANCE_OPERATION_KINDS",
    "assert_backend_conformance",
    "build_conformance_graph",
    "conformance_report_to_dict",
    "dump_backend_conformance_report",
    "run_backend_conformance",
]
