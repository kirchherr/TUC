"""TUC, the experimental Universal Compute prototype."""

from tuc.backends import (
    BackendRegistration,
    BackendRegistry,
    BackendRegistryError,
    BackendSupportDiagnostic,
)
from tuc.compiler import (
    CompilationResult,
    CompilerDecisionReport,
    CompilerPipeline,
    OperationDecisionReport,
    compile_graph,
)
from tuc.frontend import (
    TRITON_METADATA_INTAKE_CONTRACT,
    TRITON_METADATA_SCHEMA_VERSION,
    CompilationHints,
    TritonIntakeReport,
    TritonKernelMetadata,
    TritonOperationMetadata,
    TritonTensorMetadata,
    build_triton_intake_report,
    triton_metadata_to_compute_graph,
)
from tuc.ir.memory import (
    LayoutConstraint,
    LayoutKind,
    MemoryDomain,
    MemoryDomainKind,
    MovementEstimate,
    TransferEdge,
    dtype_size_bytes,
)
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.modules import IRModule, IRStage
from tuc.manifests import (
    ManifestError,
    load_backend_capability_manifest,
    load_transfer_cost_profile_manifest,
)
from tuc.proof import (
    PROOF_REPORT_SCHEMA_VERSION,
    ProofReportMetadata,
    proof_metadata_from_partition_plan,
)
from tuc.runtime import (
    RUNTIME_OVERRIDE_SCHEMA_VERSION,
    CandidateScore,
    RuntimeOverrideAction,
    RuntimeOverrideEffect,
    RuntimeOverrideError,
    RuntimeOverrideRule,
    RuntimeOverrideSet,
)

__all__ = [
    "BackendRegistration",
    "BackendRegistry",
    "BackendRegistryError",
    "BackendSupportDiagnostic",
    "CandidateScore",
    "CompilationHints",
    "CompilationResult",
    "CompilerDecisionReport",
    "ComputeGraph",
    "ComputeOperation",
    "CompilerPipeline",
    "IRModule",
    "IRStage",
    "LayoutConstraint",
    "LayoutKind",
    "ManifestError",
    "MemoryDomain",
    "MemoryDomainKind",
    "MovementEstimate",
    "OperationKind",
    "OperationDecisionReport",
    "PROOF_REPORT_SCHEMA_VERSION",
    "RUNTIME_OVERRIDE_SCHEMA_VERSION",
    "ProofReportMetadata",
    "RuntimeOverrideAction",
    "RuntimeOverrideEffect",
    "RuntimeOverrideError",
    "RuntimeOverrideRule",
    "RuntimeOverrideSet",
    "TRITON_METADATA_INTAKE_CONTRACT",
    "TRITON_METADATA_SCHEMA_VERSION",
    "TensorRef",
    "TritonIntakeReport",
    "TritonKernelMetadata",
    "TritonOperationMetadata",
    "TritonTensorMetadata",
    "TransferEdge",
    "build_triton_intake_report",
    "compile_graph",
    "dtype_size_bytes",
    "load_backend_capability_manifest",
    "load_transfer_cost_profile_manifest",
    "proof_metadata_from_partition_plan",
    "triton_metadata_to_compute_graph",
]
