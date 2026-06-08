"""TUC, the experimental Universal Compute prototype."""

from tuc.backends import (
    BackendRegistration,
    BackendRegistry,
    BackendRegistryError,
    BackendSupportDiagnostic,
)
from tuc.compiler import CompilationResult, CompilerPipeline, compile_graph
from tuc.frontend import (
    CompilationHints,
    TritonKernelMetadata,
    TritonOperationMetadata,
    TritonTensorMetadata,
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

__all__ = [
    "BackendRegistration",
    "BackendRegistry",
    "BackendRegistryError",
    "BackendSupportDiagnostic",
    "CompilationHints",
    "CompilationResult",
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
    "TensorRef",
    "TritonKernelMetadata",
    "TritonOperationMetadata",
    "TritonTensorMetadata",
    "TransferEdge",
    "compile_graph",
    "dtype_size_bytes",
    "load_backend_capability_manifest",
    "load_transfer_cost_profile_manifest",
    "triton_metadata_to_compute_graph",
]
