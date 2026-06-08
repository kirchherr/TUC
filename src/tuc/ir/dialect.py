"""Declarative IR dialect contracts for the early TUC prototype."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from types import MappingProxyType
from typing import cast

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeOperation, OperationKind
from tuc.ir.modules import IRModule, IRStage

HAC_IR_DIALECT_VERSION = "hac-ir.v0"
HAC_IR_MLIR_DIALECT = "tuc_hac.v0"
HS_IR_DIALECT_VERSION = "hs-ir.v0"
HS_IR_MLIR_DIALECT = "tuc_hs.v0"
MOVEMENT_MODEL_VERSION = "movement.v0"
RESERVED_COMPILER_ATTRIBUTE_PREFIX = "tuc."
_BACKEND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")

HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES: Mapping[str, str] = MappingProxyType(
    {
        "tuc.assigned_backend": "backend assignment belongs to HS-IR",
        "tuc.backend_binary": "compiled backend artifacts belong outside HAC-IR",
        "tuc.backend_config": "backend configuration belongs to capabilities or HS-IR",
        "tuc.backend_kernel": "backend kernel names belong outside HAC-IR",
        "tuc.cuda_arch": "vendor target details belong to backend capabilities",
        "tuc.cuda_device": "device selection belongs to runtime planning",
        "tuc.cuda_launch_grid": "launch configuration belongs to backend lowering",
        "tuc.cuda_stream": "runtime stream handles belong outside HAC-IR",
        "tuc.device_path": "host device paths are not compute intent",
        "tuc.dynamic_library": "dynamic libraries are not HAC-IR data",
        "tuc.generated_artifact": "generated artifacts must not enter HAC-IR",
        "tuc.hip_target": "vendor target details belong to backend capabilities",
        "tuc.metal_device": "device selection belongs to runtime planning",
        "tuc.neuromorphic_core": "specialized placement belongs to backend capabilities",
        "tuc.photonic_mesh": "specialized placement belongs to backend capabilities",
        "tuc.plugin_entrypoint": "plugin entrypoints are not HAC-IR data",
        "tuc.produced_layout": "backend-produced layout belongs to HS-IR",
        "tuc.vendor": "vendor identity belongs to backend capabilities",
    }
)


class HacAttributeKind(StrEnum):
    """Small schema vocabulary for prototype IR operation attributes."""

    BACKEND_NAME = "backend_name"
    BOOL = "bool"
    IDENTIFIER = "identifier"
    INT_TUPLE = "int_tuple"
    LAYOUT = "layout"
    MEMORY_DOMAIN = "memory_domain"
    NON_NEGATIVE_FLOAT = "non_negative_float"
    NON_NEGATIVE_INT = "non_negative_int"
    POSITIVE_INT = "positive_int"
    SEMANTIC_OP = "semantic_op"
    SOURCE_STAGE = "source_stage"
    STRING_ENUM = "string_enum"
    STRING_TUPLE = "string_tuple"


@dataclass(frozen=True)
class HacAttributeContract:
    """Declarative contract for one HAC-IR operation attribute."""

    name: str
    kind: HacAttributeKind
    required: bool = False
    allowed_values: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("attribute contract name must not be empty")
        if not isinstance(self.kind, HacAttributeKind):
            raise TypeError("attribute contract kind must be HacAttributeKind")
        if not isinstance(self.allowed_values, frozenset):
            raise TypeError("attribute contract allowed_values must be a frozenset")
        if any(not isinstance(value, str) or not value for value in self.allowed_values):
            raise ValueError("attribute contract allowed values must be non-empty strings")


@dataclass(frozen=True)
class HacOperationContract:
    """Declarative operation contract for the MVP IR dialects."""

    kind: OperationKind
    mlir_operation: str
    min_inputs: int
    max_inputs: int
    min_outputs: int
    max_outputs: int
    required_attributes: frozenset[str]
    optional_attributes: frozenset[str] = field(default_factory=frozenset)
    linearity: str = "nonlinear"
    max_total_tensors: int = 16

    def __post_init__(self) -> None:
        if not isinstance(self.kind, OperationKind):
            raise TypeError("operation contract kind must be OperationKind")
        if not self.mlir_operation.startswith(("tuc_hac.", "tuc_hs.")):
            raise ValueError("IR MLIR operation names must use a TUC dialect prefix")
        _validate_arity_limit(self.min_inputs, "min_inputs")
        _validate_arity_limit(self.max_inputs, "max_inputs")
        _validate_arity_limit(self.min_outputs, "min_outputs")
        _validate_arity_limit(self.max_outputs, "max_outputs")
        if self.min_inputs > self.max_inputs:
            raise ValueError("operation contract input bounds are inconsistent")
        if self.min_outputs > self.max_outputs:
            raise ValueError("operation contract output bounds are inconsistent")
        _validate_arity_limit(self.max_total_tensors, "max_total_tensors")
        if self.max_total_tensors < self.min_inputs + self.min_outputs:
            raise ValueError("operation contract total tensor bounds are inconsistent")
        _validate_string_set(self.required_attributes, "required_attributes")
        _validate_string_set(self.optional_attributes, "optional_attributes")
        if self.linearity not in {"linear", "nonlinear"}:
            raise ValueError("operation contract linearity must be linear or nonlinear")

    @property
    def allowed_attributes(self) -> frozenset[str]:
        """Return all namespaced compiler attributes allowed for this operation."""

        return self.required_attributes | self.optional_attributes


def _validate_arity_limit(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value > 16:
        raise ValueError(f"{label} must be a positive bounded integer")


def _validate_string_set(value: frozenset[str], label: str) -> None:
    if not isinstance(value, frozenset):
        raise TypeError(f"{label} must be a frozenset")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must contain non-empty strings")


_COMMON_REQUIRED_ATTRIBUTES = frozenset(
    {
        "tuc.arithmetic_intensity",
        "tuc.arithmetic_ops",
        "tuc.bytes_read",
        "tuc.bytes_written",
        "tuc.layout",
        "tuc.layout_tile_shape",
        "tuc.linearity",
        "tuc.movement_notes",
        "tuc.preferred_memory_domain",
        "tuc.semantic_op",
        "tuc.source_stage",
    }
)

_COMMON_OPTIONAL_ATTRIBUTES = frozenset(
    {
        "tuc.layout_alignment_bytes",
        "tuc.max_error_budget",
        "tuc.operation_name",
    }
)

_HS_REQUIRED_ATTRIBUTES = _COMMON_REQUIRED_ATTRIBUTES | frozenset(
    {
        "tuc.assigned_backend",
        "tuc.produced_layout",
    }
)

_ATTRIBUTE_CONTRACTS: dict[str, HacAttributeContract] = {
    "tuc.assigned_backend": HacAttributeContract(
        "tuc.assigned_backend",
        HacAttributeKind.BACKEND_NAME,
    ),
    "tuc.arithmetic_intensity": HacAttributeContract(
        "tuc.arithmetic_intensity",
        HacAttributeKind.NON_NEGATIVE_FLOAT,
    ),
    "tuc.arithmetic_ops": HacAttributeContract(
        "tuc.arithmetic_ops",
        HacAttributeKind.NON_NEGATIVE_INT,
    ),
    "tuc.bytes_read": HacAttributeContract(
        "tuc.bytes_read",
        HacAttributeKind.NON_NEGATIVE_INT,
    ),
    "tuc.bytes_written": HacAttributeContract(
        "tuc.bytes_written",
        HacAttributeKind.NON_NEGATIVE_INT,
    ),
    "tuc.layout": HacAttributeContract("tuc.layout", HacAttributeKind.LAYOUT),
    "tuc.layout_alignment_bytes": HacAttributeContract(
        "tuc.layout_alignment_bytes",
        HacAttributeKind.POSITIVE_INT,
    ),
    "tuc.layout_tile_shape": HacAttributeContract(
        "tuc.layout_tile_shape",
        HacAttributeKind.INT_TUPLE,
    ),
    "tuc.linearity": HacAttributeContract(
        "tuc.linearity",
        HacAttributeKind.STRING_ENUM,
        allowed_values=frozenset({"linear", "nonlinear"}),
    ),
    "tuc.max_error_budget": HacAttributeContract(
        "tuc.max_error_budget",
        HacAttributeKind.NON_NEGATIVE_FLOAT,
    ),
    "tuc.movement_notes": HacAttributeContract(
        "tuc.movement_notes",
        HacAttributeKind.STRING_TUPLE,
    ),
    "tuc.operation_name": HacAttributeContract(
        "tuc.operation_name",
        HacAttributeKind.IDENTIFIER,
    ),
    "tuc.preferred_memory_domain": HacAttributeContract(
        "tuc.preferred_memory_domain",
        HacAttributeKind.MEMORY_DOMAIN,
    ),
    "tuc.produced_layout": HacAttributeContract(
        "tuc.produced_layout",
        HacAttributeKind.LAYOUT,
    ),
    "tuc.semantic_op": HacAttributeContract(
        "tuc.semantic_op",
        HacAttributeKind.SEMANTIC_OP,
    ),
    "tuc.source_stage": HacAttributeContract(
        "tuc.source_stage",
        HacAttributeKind.SOURCE_STAGE,
    ),
}

HAC_ATTRIBUTE_CONTRACTS: Mapping[str, HacAttributeContract] = MappingProxyType(
    _ATTRIBUTE_CONTRACTS
)

HAC_OPERATION_CONTRACTS: Mapping[OperationKind, HacOperationContract] = MappingProxyType(
    {
        OperationKind.MATMUL: HacOperationContract(
            kind=OperationKind.MATMUL,
            mlir_operation="tuc_hac.matmul",
            min_inputs=2,
            max_inputs=2,
            min_outputs=1,
            max_outputs=1,
            required_attributes=_COMMON_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="linear",
        ),
        OperationKind.ELEMENTWISE: HacOperationContract(
            kind=OperationKind.ELEMENTWISE,
            mlir_operation="tuc_hac.elementwise",
            min_inputs=1,
            max_inputs=16,
            min_outputs=1,
            max_outputs=16,
            required_attributes=_COMMON_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="nonlinear",
        ),
        OperationKind.REDUCTION: HacOperationContract(
            kind=OperationKind.REDUCTION,
            mlir_operation="tuc_hac.reduction",
            min_inputs=1,
            max_inputs=16,
            min_outputs=1,
            max_outputs=1,
            required_attributes=_COMMON_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="linear",
        ),
        OperationKind.SOFTMAX: HacOperationContract(
            kind=OperationKind.SOFTMAX,
            mlir_operation="tuc_hac.softmax",
            min_inputs=1,
            max_inputs=1,
            min_outputs=1,
            max_outputs=1,
            required_attributes=_COMMON_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="nonlinear",
        ),
    }
)

HS_OPERATION_CONTRACTS: Mapping[OperationKind, HacOperationContract] = MappingProxyType(
    {
        OperationKind.MATMUL: HacOperationContract(
            kind=OperationKind.MATMUL,
            mlir_operation="tuc_hs.matmul",
            min_inputs=2,
            max_inputs=2,
            min_outputs=1,
            max_outputs=1,
            required_attributes=_HS_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="linear",
        ),
        OperationKind.ELEMENTWISE: HacOperationContract(
            kind=OperationKind.ELEMENTWISE,
            mlir_operation="tuc_hs.elementwise",
            min_inputs=1,
            max_inputs=16,
            min_outputs=1,
            max_outputs=16,
            required_attributes=_HS_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="nonlinear",
        ),
        OperationKind.REDUCTION: HacOperationContract(
            kind=OperationKind.REDUCTION,
            mlir_operation="tuc_hs.reduction",
            min_inputs=1,
            max_inputs=16,
            min_outputs=1,
            max_outputs=1,
            required_attributes=_HS_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="linear",
        ),
        OperationKind.SOFTMAX: HacOperationContract(
            kind=OperationKind.SOFTMAX,
            mlir_operation="tuc_hs.softmax",
            min_inputs=1,
            max_inputs=1,
            min_outputs=1,
            max_outputs=1,
            required_attributes=_HS_REQUIRED_ATTRIBUTES,
            optional_attributes=_COMMON_OPTIONAL_ATTRIBUTES,
            linearity="nonlinear",
        ),
    }
)


def validate_hac_module_contract(module: IRModule) -> None:
    """Fail closed unless a module satisfies the HAC-IR v0 dialect contract."""

    if module.stage is not IRStage.HAC_IR:
        raise ValueError(f"expected HAC-IR module, got {module.stage.value}")
    dialect_version = module.metadata.get("dialect_version")
    if dialect_version != HAC_IR_DIALECT_VERSION:
        raise ValueError(
            f"HAC-IR module dialect_version must be {HAC_IR_DIALECT_VERSION!r}"
        )
    for operation in module.graph.operations:
        validate_hac_operation_contract(operation)


def validate_hs_module_contract(module: IRModule) -> None:
    """Fail closed unless a module satisfies the HS-IR v0 dialect contract."""

    if module.stage is not IRStage.HS_IR:
        raise ValueError(f"expected HS-IR module, got {module.stage.value}")
    if module.target != "heterogeneous":
        raise ValueError("HS-IR module target must be 'heterogeneous'")
    dialect_version = module.metadata.get("dialect_version")
    if dialect_version != HS_IR_DIALECT_VERSION:
        raise ValueError(f"HS-IR module dialect_version must be {HS_IR_DIALECT_VERSION!r}")

    _validate_graph_source_stage(module.graph.metadata)
    _validate_movement_summary(
        module.graph.metadata.get("movement_summary"),
        operation_count=len(module.graph.operations),
    )
    _validate_runtime_transfer_summary(module.graph.metadata.get("runtime_transfer_summary"))
    assignments = _validate_backend_assignments(
        module.graph.metadata.get("backend_assignments"),
        module.graph.operations,
    )
    for operation in module.graph.operations:
        validate_hs_operation_contract(operation, assignments)


def validate_hac_operation_contract(operation: ComputeOperation) -> None:
    """Validate one operation against the HAC-IR v0 operation contract."""

    contract = HAC_OPERATION_CONTRACTS.get(operation.kind)
    if contract is None:
        raise ValueError(f"unsupported HAC-IR operation kind: {operation.kind.value}")

    _validate_operation_shape(operation, contract)
    _validate_operation_attributes(
        operation,
        contract,
        dialect_label="HAC-IR",
        expected_source_stage=IRStage.TLIR.value,
        backend_assignments=None,
    )


def validate_hs_operation_contract(
    operation: ComputeOperation,
    backend_assignments: Mapping[str, str] | None = None,
) -> None:
    """Validate one operation against the HS-IR v0 operation contract."""

    contract = HS_OPERATION_CONTRACTS.get(operation.kind)
    if contract is None:
        raise ValueError(f"unsupported HS-IR operation kind: {operation.kind.value}")

    _validate_operation_shape(operation, contract)
    _validate_operation_attributes(
        operation,
        contract,
        dialect_label="HS-IR",
        expected_source_stage=IRStage.HAC_IR.value,
        backend_assignments=backend_assignments,
    )


def _validate_operation_shape(
    operation: ComputeOperation,
    contract: HacOperationContract,
) -> None:
    _validate_arity(
        count=len(operation.inputs),
        minimum=contract.min_inputs,
        maximum=contract.max_inputs,
        label=f"operation {operation.name!r} inputs",
    )
    _validate_arity(
        count=len(operation.outputs),
        minimum=contract.min_outputs,
        maximum=contract.max_outputs,
        label=f"operation {operation.name!r} outputs",
    )
    _validate_arity(
        count=len(operation.inputs) + len(operation.outputs),
        minimum=contract.min_inputs + contract.min_outputs,
        maximum=contract.max_total_tensors,
        label=f"operation {operation.name!r} total tensor",
    )


def _validate_operation_attributes(
    operation: ComputeOperation,
    contract: HacOperationContract,
    dialect_label: str,
    expected_source_stage: str,
    backend_assignments: Mapping[str, str] | None,
) -> None:
    attributes = operation.attributes
    missing = sorted(
        name
        for name in contract.required_attributes
        if name not in attributes
    )
    if missing:
        raise ValueError(
            f"operation {operation.name!r} is missing {dialect_label} attributes: "
            + ", ".join(missing)
        )

    for name, value in attributes.items():
        if name.startswith(RESERVED_COMPILER_ATTRIBUTE_PREFIX):
            if (
                dialect_label == "HAC-IR"
                and name in HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES
            ):
                reason = HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES[name]
                raise ValueError(
                    f"operation {operation.name!r} has forbidden HAC-IR "
                    f"hardware attribute: {name} ({reason})"
                )
            if name not in contract.allowed_attributes:
                raise ValueError(
                    f"operation {operation.name!r} has unsupported {dialect_label} "
                    f"compiler attribute: {name}"
                )
            _validate_attribute_value(
                name,
                value,
                operation,
                contract,
                expected_source_stage,
            )
        elif name in {"max_error_budget"}:
            _validate_non_negative_float(value, name)
        elif name in {"prefer_analog_linear", "prefer_sparsity", "robust_to_noise"}:
            if type(value) is not bool:
                raise TypeError(f"{name} must be a boolean")

    if backend_assignments is not None:
        expected_backend = backend_assignments.get(operation.name)
        assigned_backend = attributes.get("tuc.assigned_backend")
        if expected_backend != assigned_backend:
            raise ValueError(
                f"operation {operation.name!r} backend assignment does not match "
                "HS-IR graph metadata"
            )


def _validate_attribute_value(
    name: str,
    value: object,
    operation: ComputeOperation,
    contract: HacOperationContract,
    expected_source_stage: str,
) -> None:
    attribute_contract = HAC_ATTRIBUTE_CONTRACTS[name]
    kind = attribute_contract.kind

    if kind is HacAttributeKind.BACKEND_NAME:
        _validate_backend_name(value, name)
        return
    if kind is HacAttributeKind.BOOL:
        if type(value) is not bool:
            raise TypeError(f"{name} must be a boolean")
        return
    if kind is HacAttributeKind.IDENTIFIER:
        if value != operation.name:
            raise ValueError(f"{name} must match the operation name")
        return
    if kind is HacAttributeKind.INT_TUPLE:
        _validate_int_tuple(value, name)
        return
    if kind is HacAttributeKind.LAYOUT:
        _validate_layout(value, name)
        return
    if kind is HacAttributeKind.MEMORY_DOMAIN:
        _validate_memory_domain(value, name)
        return
    if kind is HacAttributeKind.NON_NEGATIVE_FLOAT:
        _validate_non_negative_float(value, name)
        return
    if kind is HacAttributeKind.NON_NEGATIVE_INT:
        _validate_non_negative_int(value, name)
        return
    if kind is HacAttributeKind.POSITIVE_INT:
        _validate_positive_int(value, name)
        return
    if kind is HacAttributeKind.SEMANTIC_OP:
        if value != operation.kind.value:
            raise ValueError(f"{name} must match operation kind {operation.kind.value!r}")
        return
    if kind is HacAttributeKind.SOURCE_STAGE:
        if value != expected_source_stage:
            raise ValueError(f"{name} must be {expected_source_stage!r}")
        return
    if kind is HacAttributeKind.STRING_ENUM:
        if not isinstance(value, str) or value not in attribute_contract.allowed_values:
            raise ValueError(f"{name} must be one of {sorted(attribute_contract.allowed_values)}")
        if name == "tuc.linearity" and value != contract.linearity:
            raise ValueError(f"{name} must be {contract.linearity!r} for {operation.kind.value}")
        return
    if kind is HacAttributeKind.STRING_TUPLE:
        _validate_string_tuple(value, name)
        return


def _validate_graph_source_stage(metadata: Mapping[str, object]) -> None:
    value = metadata.get("lowered_from")
    if value != IRStage.HAC_IR.value:
        raise ValueError(f"HS-IR graph lowered_from must be {IRStage.HAC_IR.value!r}")


def _validate_backend_assignments(
    value: object,
    operations: tuple[ComputeOperation, ...],
) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError("HS-IR backend_assignments must be a mapping")
    operation_names = {operation.name for operation in operations}
    assignment_names = set(value)
    if assignment_names != operation_names:
        missing = sorted(operation_names - assignment_names)
        extra = sorted(assignment_names - operation_names)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise ValueError("HS-IR backend_assignments must match operations; " + "; ".join(details))

    assignments: dict[str, str] = {}
    for name, backend in value.items():
        if not isinstance(name, str):
            raise TypeError("HS-IR backend assignment keys must be strings")
        _validate_backend_name(backend, "backend assignment")
        assignments[name] = backend
    return assignments


def _validate_movement_summary(value: object, operation_count: int) -> None:
    summary = _require_summary_mapping(value, "HS-IR movement_summary")
    _require_exact_keys(
        summary,
        frozenset(
            {
                "arithmetic_intensity",
                "movement_model",
                "operation_count",
                "total_arithmetic_ops",
                "total_bytes_read",
                "total_bytes_written",
            }
        ),
        "HS-IR movement_summary",
    )
    _validate_non_negative_float(
        summary["arithmetic_intensity"],
        "movement_summary.arithmetic_intensity",
    )
    if summary["movement_model"] != MOVEMENT_MODEL_VERSION:
        raise ValueError(f"movement_summary.movement_model must be {MOVEMENT_MODEL_VERSION!r}")
    summary_operation_count = _require_summary_int(
        summary,
        "operation_count",
        "movement_summary.operation_count",
    )
    if summary_operation_count != operation_count:
        raise ValueError("movement_summary.operation_count must match HS-IR operations")
    _require_summary_int(
        summary,
        "total_arithmetic_ops",
        "movement_summary.total_arithmetic_ops",
    )
    _require_summary_int(summary, "total_bytes_read", "movement_summary.total_bytes_read")
    _require_summary_int(
        summary,
        "total_bytes_written",
        "movement_summary.total_bytes_written",
    )


def _validate_runtime_transfer_summary(value: object) -> None:
    summary = _require_summary_mapping(value, "HS-IR runtime_transfer_summary")
    _require_exact_keys(
        summary,
        frozenset(
            {
                "estimated_transfer_energy_pj",
                "estimated_transfer_latency_ns",
                "layout_conversion_count",
                "total_data_movement_bytes",
                "total_layout_conversion_bytes",
                "total_transfer_bytes",
                "transfer_edge_count",
            }
        ),
        "HS-IR runtime_transfer_summary",
    )
    _validate_non_negative_float(
        summary["estimated_transfer_energy_pj"],
        "runtime_transfer_summary.estimated_transfer_energy_pj",
    )
    _validate_non_negative_float(
        summary["estimated_transfer_latency_ns"],
        "runtime_transfer_summary.estimated_transfer_latency_ns",
    )
    _require_summary_int(
        summary,
        "layout_conversion_count",
        "runtime_transfer_summary.layout_conversion_count",
    )
    total_data_movement_bytes = _require_summary_int(
        summary,
        "total_data_movement_bytes",
        "runtime_transfer_summary.total_data_movement_bytes",
    )
    total_layout_conversion_bytes = _require_summary_int(
        summary,
        "total_layout_conversion_bytes",
        "runtime_transfer_summary.total_layout_conversion_bytes",
    )
    total_transfer_bytes = _require_summary_int(
        summary,
        "total_transfer_bytes",
        "runtime_transfer_summary.total_transfer_bytes",
    )
    _require_summary_int(
        summary,
        "transfer_edge_count",
        "runtime_transfer_summary.transfer_edge_count",
    )
    total = total_layout_conversion_bytes + total_transfer_bytes
    if total_data_movement_bytes != total:
        raise ValueError(
            "runtime_transfer_summary.total_data_movement_bytes must equal "
            "transfer plus layout-conversion bytes"
        )


def _require_summary_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{label} keys must be strings")
    return value


def _require_summary_int(
    summary: Mapping[str, object],
    key: str,
    label: str,
) -> int:
    value = summary[key]
    _validate_non_negative_int(value, label)
    return cast(int, value)


def _require_exact_keys(
    mapping: Mapping[str, object],
    expected_keys: frozenset[str],
    label: str,
) -> None:
    actual_keys = set(mapping)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("extra: " + ", ".join(extra))
        raise ValueError(f"{label} keys must match contract; " + "; ".join(details))


def _validate_arity(count: int, minimum: int, maximum: int, label: str) -> None:
    if count < minimum or count > maximum:
        raise ValueError(f"{label} count must be between {minimum} and {maximum}")


def _validate_int_tuple(value: object, label: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{label} must be a tuple")
    if any(not isinstance(item, int) or isinstance(item, bool) or item <= 0 for item in value):
        raise ValueError(f"{label} must contain only positive integers")


def _validate_layout(value: object, label: str) -> None:
    if isinstance(value, LayoutKind):
        return
    if isinstance(value, str):
        try:
            LayoutKind(value)
            return
        except ValueError as exc:
            raise ValueError(f"unsupported {label}: {value!r}") from exc
    raise TypeError(f"{label} must be a layout string")


def _validate_backend_name(value: object, label: str) -> None:
    if not isinstance(value, str) or not _BACKEND_NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must be a simple backend name")


def _validate_memory_domain(value: object, label: str) -> None:
    if isinstance(value, MemoryDomainKind):
        return
    if isinstance(value, str):
        try:
            MemoryDomainKind(value)
            return
        except ValueError as exc:
            raise ValueError(f"unsupported {label}: {value!r}") from exc
    raise TypeError(f"{label} must be a memory-domain string")


def _validate_non_negative_float(value: object, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{label} must be a number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validate_non_negative_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


def _validate_positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _validate_string_tuple(value: object, label: str) -> None:
    if not isinstance(value, tuple):
        raise TypeError(f"{label} must be a tuple")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label} must contain non-empty strings")


__all__ = [
    "HAC_ATTRIBUTE_CONTRACTS",
    "HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES",
    "HAC_IR_DIALECT_VERSION",
    "HAC_IR_MLIR_DIALECT",
    "HAC_OPERATION_CONTRACTS",
    "HS_IR_DIALECT_VERSION",
    "HS_IR_MLIR_DIALECT",
    "HS_OPERATION_CONTRACTS",
    "HacAttributeContract",
    "HacAttributeKind",
    "HacOperationContract",
    "MOVEMENT_MODEL_VERSION",
    "RESERVED_COMPILER_ATTRIBUTE_PREFIX",
    "validate_hac_module_contract",
    "validate_hac_operation_contract",
    "validate_hs_module_contract",
    "validate_hs_operation_contract",
]
