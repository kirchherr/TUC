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
from tuc.frontend.source_intent_intake import (
    SOURCE_INTENT_INTAKE_CONTRACT,
    SOURCE_INTENT_SCHEMA_VERSION,
    SourceIntentIntakeReport,
    build_source_intent_intake_report,
    source_intent_from_mapping,
)
from tuc.frontend.source_intent_metadata import (
    SOURCE_INTENT_METADATA_CONTRACT,
    SourceIntentMetadataReport,
    build_source_intent_metadata_report,
    source_intent_to_triton_metadata,
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
    "SOURCE_INTENT_INTAKE_CONTRACT",
    "SOURCE_INTENT_METADATA_CONTRACT",
    "SOURCE_INTENT_SCHEMA_VERSION",
    "SourceIntentIntakeReport",
    "SourceIntentModule",
    "SourceIntentMetadataReport",
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
    "build_source_intent_intake_report",
    "build_source_intent_metadata_report",
    "build_triton_intake_report",
    "preflight_triton_source",
    "source_intent_from_mapping",
    "source_intent_to_triton_metadata",
    "triton_metadata_to_compute_graph",
]
