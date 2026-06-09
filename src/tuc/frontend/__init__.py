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
from tuc.frontend.triton_source import (
    MAX_TRITON_SOURCE_AST_DEPTH,
    MAX_TRITON_SOURCE_AST_NODES,
    MAX_TRITON_SOURCE_BYTES,
    MAX_TRITON_SOURCE_LINES,
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    TritonSourcePreflightReport,
    preflight_triton_source,
)

__all__ = [
    "CompilationHints",
    "MAX_TRITON_SOURCE_AST_DEPTH",
    "MAX_TRITON_SOURCE_AST_NODES",
    "MAX_TRITON_SOURCE_BYTES",
    "MAX_TRITON_SOURCE_LINES",
    "TRITON_METADATA_INTAKE_CONTRACT",
    "TRITON_METADATA_SCHEMA_VERSION",
    "TRITON_SOURCE_PREFLIGHT_CONTRACT",
    "TritonIntakeReport",
    "TritonKernelMetadata",
    "TritonOperationMetadata",
    "TritonSourcePreflightReport",
    "TritonTensorMetadata",
    "build_triton_intake_report",
    "preflight_triton_source",
    "triton_metadata_to_compute_graph",
]
