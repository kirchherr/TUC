"""Execution-free Source Intent IR to Triton metadata conversion.

This adapter is deliberately separate from `SourceIntentModule`: Source Intent
IR remains a data model, while conversion is an explicit, reviewable frontend
gate. The adapter does not parse source text, inspect Python objects, execute
decorators, discover backends, lower IR, or produce runtime plans.
"""

from __future__ import annotations

from dataclasses import dataclass

from tuc.frontend.hints import CompilationHints
from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_RETURN_POLICY,
    SourceIntentModule,
    SourceIntentOperation,
)
from tuc.frontend.source_intent_returns import source_intent_return_aliases
from tuc.frontend.triton_metadata import (
    TRITON_METADATA_SCHEMA_VERSION,
    TritonKernelMetadata,
    TritonOperationMetadata,
    TritonTensorMetadata,
)
from tuc.ir.model import OperationKind

SOURCE_INTENT_METADATA_CONTRACT = "source_intent_to_metadata.execution_free.v0"
_BLOCKED_EXECUTION_SURFACES = (
    "bytecode_inspection",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "source_parsing",
    "subprocess_execution",
)
_BLOCKED_COMPILER_OUTPUTS = (
    "compute_graph",
    "tlir",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "backend_decision",
)


@dataclass(frozen=True)
class SourceIntentMetadataReport:
    """Deterministic evidence for Source Intent IR metadata conversion."""

    module_name: str
    source_intent_contract: str
    conversion_contract: str
    metadata_schema_version: str
    tensor_count: int
    operation_count: int
    operation_families: tuple[str, ...]
    blocked_execution_surfaces: tuple[str, ...]
    blocked_compiler_outputs: tuple[str, ...]

    def dump(self) -> str:
        operation_families = (
            ",".join(self.operation_families) if self.operation_families else "-"
        )
        blocked_execution = ",".join(self.blocked_execution_surfaces)
        blocked_outputs = ",".join(self.blocked_compiler_outputs)
        return "\n".join(
            (
                f"source_intent.metadata_report @{self.module_name} {{",
                f'  source_intent_contract = "{self.source_intent_contract}"',
                f'  conversion_contract = "{self.conversion_contract}"',
                f'  metadata_schema_version = "{self.metadata_schema_version}"',
                f"  tensor_count = {self.tensor_count}",
                f"  operation_count = {self.operation_count}",
                f'  operation_families = "{operation_families}"',
                f'  blocked_execution_surfaces = "{blocked_execution}"',
                f'  blocked_compiler_outputs = "{blocked_outputs}"',
                "}",
            )
        )


def source_intent_to_triton_metadata(
    module: SourceIntentModule,
) -> TritonKernelMetadata:
    """Convert canonical Source Intent IR into schema-versioned metadata."""

    _require_source_intent_module(module)
    tensors = tuple(
        TritonTensorMetadata(
            name=tensor.name,
            shape=tensor.shape,
            dtype=tensor.dtype,
        )
        for tensor in module.tensors
    )
    operations = tuple(_operation_to_metadata(operation) for operation in module.operations)
    graph_metadata: dict[str, object] = {
        "frontend.source_intent_contract": module.contract,
        "frontend.source_intent_conversion_contract": SOURCE_INTENT_METADATA_CONTRACT,
    }
    if module.returns:
        aliases = source_intent_return_aliases(module)
        graph_metadata["frontend.source_intent_return_policy"] = (
            SOURCE_INTENT_RETURN_POLICY
        )
        graph_metadata["frontend.source_intent_return_aliases"] = tuple(
            f"{public_name}:{tensor_name}"
            for public_name, tensor_name in aliases.items()
        )
    return TritonKernelMetadata(
        name=module.name,
        tensors=tensors,
        operations=operations,
        metadata=graph_metadata,
    )


def build_source_intent_metadata_report(
    module: SourceIntentModule,
) -> SourceIntentMetadataReport:
    """Build deterministic evidence for the conversion boundary."""

    _require_source_intent_module(module)
    return SourceIntentMetadataReport(
        module_name=module.name,
        source_intent_contract=module.contract,
        conversion_contract=SOURCE_INTENT_METADATA_CONTRACT,
        metadata_schema_version=TRITON_METADATA_SCHEMA_VERSION,
        tensor_count=len(module.tensors),
        operation_count=len(module.operations),
        operation_families=tuple(operation.family for operation in module.operations),
        blocked_execution_surfaces=_BLOCKED_EXECUTION_SURFACES,
        blocked_compiler_outputs=_BLOCKED_COMPILER_OUTPUTS,
    )


def _operation_to_metadata(operation: SourceIntentOperation) -> TritonOperationMetadata:
    return TritonOperationMetadata(
        name=operation.name,
        kind=OperationKind(operation.family),
        inputs=operation.inputs,
        outputs=operation.outputs,
        hints=_hints_to_compilation_hints(operation),
    )


def _hints_to_compilation_hints(operation: SourceIntentOperation) -> CompilationHints:
    hints = operation.hints
    return CompilationHints(
        robust_to_noise=hints.get("robust_to_noise", False) is True,
        prefer_sparsity=hints.get("prefer_sparsity", False) is True,
        prefer_linear_accelerator=hints.get("prefer_linear_accelerator", False) is True,
        max_error_budget=_optional_error_budget(operation),
    )


def _optional_error_budget(operation: SourceIntentOperation) -> float | None:
    value = operation.hints.get("max_error_budget")
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError("max_error_budget must be a number")
    return float(value)


def _require_source_intent_module(module: SourceIntentModule) -> None:
    if not isinstance(module, SourceIntentModule):
        raise TypeError("source-intent metadata conversion requires SourceIntentModule")
    if module.contract != SOURCE_INTENT_IR_CONTRACT:
        raise ValueError(
            "source-intent metadata conversion requires contract "
            f"{SOURCE_INTENT_IR_CONTRACT!r}"
        )


__all__ = [
    "SOURCE_INTENT_METADATA_CONTRACT",
    "SourceIntentMetadataReport",
    "build_source_intent_metadata_report",
    "source_intent_to_triton_metadata",
]
