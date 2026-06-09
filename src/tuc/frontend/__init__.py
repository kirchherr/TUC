"""Frontend metadata and developer-facing helpers."""

from tuc.frontend.hints import CompilationHints
from tuc.frontend.source_intent import (
    MAX_SOURCE_INTENT_ARITY,
    MAX_SOURCE_INTENT_OPERATIONS,
    MAX_SOURCE_INTENT_TENSORS,
    SOURCE_INTENT_IR_CONTRACT,
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentTensor,
)
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
    MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES,
    MAX_TRITON_SOURCE_DIAGNOSTICS,
    MAX_TRITON_SOURCE_LINES,
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    TritonSourcePreflightReport,
    preflight_triton_source,
)

__all__ = [
    "CompilationHints",
    "MAX_SOURCE_INTENT_ARITY",
    "MAX_SOURCE_INTENT_OPERATIONS",
    "MAX_SOURCE_INTENT_TENSORS",
    "MAX_TRITON_SOURCE_AST_DEPTH",
    "MAX_TRITON_SOURCE_AST_NODES",
    "MAX_TRITON_SOURCE_BYTES",
    "MAX_TRITON_SOURCE_DIAGNOSTICS",
    "MAX_TRITON_SOURCE_DIAGNOSTIC_BYTES",
    "MAX_TRITON_SOURCE_LINES",
    "SOURCE_INTENT_IR_CONTRACT",
    "SourceIntentModule",
    "SourceIntentOperation",
    "SourceIntentTensor",
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
