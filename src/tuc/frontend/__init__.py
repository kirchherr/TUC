"""Frontend metadata and developer-facing helpers."""

from tuc.frontend.hints import CompilationHints
from tuc.frontend.triton_metadata import (
    TRITON_METADATA_INTAKE_CONTRACT,
    TRITON_METADATA_SCHEMA_VERSION,
    TritonIntakeReport,
    TritonKernelMetadata,
    TritonOperationMetadata,
    TritonTensorMetadata,
    build_triton_intake_report,
    triton_metadata_to_compute_graph,
)

__all__ = [
    "CompilationHints",
    "TRITON_METADATA_INTAKE_CONTRACT",
    "TRITON_METADATA_SCHEMA_VERSION",
    "TritonIntakeReport",
    "TritonKernelMetadata",
    "TritonOperationMetadata",
    "TritonTensorMetadata",
    "build_triton_intake_report",
    "triton_metadata_to_compute_graph",
]
