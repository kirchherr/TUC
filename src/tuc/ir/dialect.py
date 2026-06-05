"""Declarative HAC-IR dialect contracts for the early TUC prototype."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from types import MappingProxyType

from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import ComputeOperation, OperationKind
from tuc.ir.modules import IRModule, IRStage

HAC_IR_DIALECT_VERSION = "hac-ir.v0"
HAC_IR_MLIR_DIALECT = "tuc_hac.v0"
RESERVED_COMPILER_ATTRIBUTE_PREFIX = "tuc."


class HacAttributeKind(StrEnum):
    """Small schema vocabulary for HAC-IR operation attributes."""

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
    """Declarative operation contract for the HAC-IR MVP dialect."""

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
        if not self.mlir_operation.startswith("tuc_hac."):
            raise ValueError("HAC-IR MLIR operation names must use tuc_hac.*")
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

_ATTRIBUTE_CONTRACTS: dict[str, HacAttributeContract] = {
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


def validate_hac_operation_contract(operation: ComputeOperation) -> None:
    """Validate one operation against the HAC-IR v0 operation contract."""

    contract = HAC_OPERATION_CONTRACTS.get(operation.kind)
    if contract is None:
        raise ValueError(f"unsupported HAC-IR operation kind: {operation.kind.value}")

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
    _validate_hac_attributes(operation, contract)


def _validate_hac_attributes(
    operation: ComputeOperation,
    contract: HacOperationContract,
) -> None:
    attributes = operation.attributes
    missing = sorted(
        name
        for name in contract.required_attributes
        if name not in attributes
    )
    if missing:
        raise ValueError(
            f"operation {operation.name!r} is missing HAC-IR attributes: "
            + ", ".join(missing)
        )

    for name, value in attributes.items():
        if name.startswith(RESERVED_COMPILER_ATTRIBUTE_PREFIX):
            if name not in contract.allowed_attributes:
                raise ValueError(
                    f"operation {operation.name!r} has unsupported HAC-IR "
                    f"compiler attribute: {name}"
                )
            _validate_attribute_value(name, value, operation, contract)
        elif name in {"max_error_budget"}:
            _validate_non_negative_float(value, name)
        elif name in {"prefer_analog_linear", "prefer_sparsity", "robust_to_noise"}:
            if type(value) is not bool:
                raise TypeError(f"{name} must be a boolean")


def _validate_attribute_value(
    name: str,
    value: object,
    operation: ComputeOperation,
    contract: HacOperationContract,
) -> None:
    attribute_contract = HAC_ATTRIBUTE_CONTRACTS[name]
    kind = attribute_contract.kind

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
        if value != IRStage.TLIR.value:
            raise ValueError(f"{name} must be {IRStage.TLIR.value!r}")
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
    "HAC_IR_DIALECT_VERSION",
    "HAC_IR_MLIR_DIALECT",
    "HAC_OPERATION_CONTRACTS",
    "HacAttributeContract",
    "HacAttributeKind",
    "HacOperationContract",
    "RESERVED_COMPILER_ATTRIBUTE_PREFIX",
    "validate_hac_module_contract",
    "validate_hac_operation_contract",
]
