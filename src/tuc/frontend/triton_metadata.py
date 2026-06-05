"""Prototype adapter for Triton-like kernel metadata.

The adapter intentionally consumes declarative metadata, not Python source or
`@triton.jit` functions. It is the first narrow frontend bridge into TUC's
hardware-agnostic compute graph.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeVar, cast

from tuc.frontend.hints import CompilationHints
from tuc.ir.memory import LayoutKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef

MAX_TRITON_METADATA_TENSORS = 4096
MAX_TRITON_OPERATION_ARITY = 16
MAX_TRITON_METADATA_OPERATIONS = 4096
_RESERVED_ATTRIBUTE_PREFIX = "tuc."
_EnumT = TypeVar("_EnumT", bound=StrEnum)


@dataclass(frozen=True)
class TritonTensorMetadata:
    """Declarative tensor metadata from a Triton-like frontend."""

    name: str
    shape: tuple[int, ...]
    dtype: str = "float32"

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape", tuple(self.shape))
        TensorRef(self.name, self.shape, self.dtype)

    def to_tensor_ref(self) -> TensorRef:
        """Convert this frontend tensor metadata into TUC IR."""

        return TensorRef(self.name, self.shape, self.dtype)


@dataclass(frozen=True)
class TritonOperationMetadata:
    """Declarative operation metadata from a Triton-like frontend."""

    name: str
    kind: OperationKind
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    hints: CompilationHints = field(default_factory=CompilationHints)
    layout: LayoutKind | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, OperationKind):
            raise TypeError("triton operation kind must be OperationKind")
        if not isinstance(self.hints, CompilationHints):
            raise TypeError("triton operation hints must be CompilationHints")
        if self.layout is not None and not isinstance(self.layout, LayoutKind):
            raise TypeError("triton operation layout must be LayoutKind")
        inputs = _require_name_sequence(self.inputs, "triton operation inputs")
        outputs = _require_name_sequence(self.outputs, "triton operation outputs")
        if len(inputs) > MAX_TRITON_OPERATION_ARITY:
            raise ValueError("triton operation input count exceeds adapter limit")
        if len(outputs) > MAX_TRITON_OPERATION_ARITY:
            raise ValueError("triton operation output count exceeds adapter limit")
        _reject_reserved_attributes(self.attributes)
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "outputs", outputs)
        object.__setattr__(self, "attributes", dict(self.attributes))


@dataclass(frozen=True)
class TritonKernelMetadata:
    """Declarative Triton-like kernel metadata accepted by the prototype adapter."""

    name: str
    tensors: tuple[TritonTensorMetadata, ...]
    operations: tuple[TritonOperationMetadata, ...]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.tensors) > MAX_TRITON_METADATA_TENSORS:
            raise ValueError("triton metadata tensor count exceeds adapter limit")
        if len(self.operations) > MAX_TRITON_METADATA_OPERATIONS:
            raise ValueError("triton metadata operation count exceeds adapter limit")
        if not self.tensors:
            raise ValueError("triton metadata must contain tensors")
        if not self.operations:
            raise ValueError("triton metadata must contain operations")
        _reject_reserved_attributes(self.metadata)
        object.__setattr__(self, "tensors", tuple(self.tensors))
        object.__setattr__(self, "operations", tuple(self.operations))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @classmethod
    def from_mapping(cls, metadata: object) -> TritonKernelMetadata:
        """Build typed metadata from plain JSON-like frontend data."""

        mapping = _require_plain_mapping(metadata, "triton kernel metadata")
        _reject_unknown_keys(
            mapping,
            frozenset({"name", "tensors", "operations", "metadata"}),
            "triton kernel metadata",
        )
        tensors = tuple(
            _tensor_metadata_from_mapping(item)
            for item in _require_plain_sequence(mapping.get("tensors"), "tensors")
        )
        operations = tuple(
            _operation_metadata_from_mapping(item)
            for item in _require_plain_sequence(mapping.get("operations"), "operations")
        )
        graph_metadata = mapping.get("metadata", {})
        if graph_metadata is None:
            graph_metadata = {}
        return cls(
            name=_require_string(mapping, "name"),
            tensors=tensors,
            operations=operations,
            metadata=_require_plain_mapping(graph_metadata, "metadata"),
        )

    def to_compute_graph(self) -> ComputeGraph:
        """Convert Triton-like metadata into TUC's hardware-agnostic graph."""

        return triton_metadata_to_compute_graph(self)


def triton_metadata_to_compute_graph(metadata: TritonKernelMetadata) -> ComputeGraph:
    """Convert typed Triton-like metadata into a TUC `ComputeGraph`."""

    if not isinstance(metadata, TritonKernelMetadata):
        raise TypeError("metadata must be TritonKernelMetadata")

    tensors = {tensor.name: tensor.to_tensor_ref() for tensor in metadata.tensors}
    if len(tensors) != len(metadata.tensors):
        raise ValueError("triton tensor names must be unique")

    operations: list[ComputeOperation] = []
    for operation in metadata.operations:
        inputs = tuple(_lookup_tensor(tensors, name, "input") for name in operation.inputs)
        outputs = tuple(_lookup_tensor(tensors, name, "output") for name in operation.outputs)
        attributes = _operation_attributes(operation)
        operations.append(
            ComputeOperation(
                name=operation.name,
                kind=operation.kind,
                inputs=inputs,
                outputs=outputs,
                attributes=attributes,
            )
        )

    graph_metadata = dict(metadata.metadata)
    graph_metadata["frontend.adapter"] = "triton_metadata.v0"
    return ComputeGraph(
        name=metadata.name,
        operations=tuple(operations),
        metadata=graph_metadata,
    )


def _tensor_metadata_from_mapping(value: object) -> TritonTensorMetadata:
    mapping = _require_plain_mapping(value, "triton tensor metadata")
    _reject_unknown_keys(mapping, frozenset({"name", "shape", "dtype"}), "triton tensor metadata")
    shape = tuple(_require_int(item, "shape dimension") for item in _require_plain_sequence(
        mapping.get("shape"),
        "shape",
    ))
    return TritonTensorMetadata(
        name=_require_string(mapping, "name"),
        shape=shape,
        dtype=_optional_string(mapping, "dtype", "float32"),
    )


def _operation_metadata_from_mapping(value: object) -> TritonOperationMetadata:
    mapping = _require_plain_mapping(value, "triton operation metadata")
    _reject_unknown_keys(
        mapping,
        frozenset({"name", "kind", "inputs", "outputs", "hints", "layout", "attributes"}),
        "triton operation metadata",
    )
    layout = None
    if mapping.get("layout") is not None:
        layout = _enum_from_string(
            _require_string(mapping, "layout"),
            LayoutKind,
            "triton operation layout",
        )
    return TritonOperationMetadata(
        name=_require_string(mapping, "name"),
        kind=_enum_from_string(
            _require_string(mapping, "kind"),
            OperationKind,
            "triton operation kind",
        ),
        inputs=_string_tuple(mapping, "inputs"),
        outputs=_string_tuple(mapping, "outputs"),
        hints=_hints_from_mapping(mapping.get("hints", {})),
        layout=layout,
        attributes=_require_plain_mapping(mapping.get("attributes", {}), "attributes"),
    )


def _hints_from_mapping(value: object) -> CompilationHints:
    mapping = _require_plain_mapping(value, "hints")
    _reject_unknown_keys(
        mapping,
        frozenset(
            {
                "robust_to_noise",
                "prefer_sparsity",
                "prefer_analog_linear",
                "max_error_budget",
            }
        ),
        "hints",
    )
    return CompilationHints(
        robust_to_noise=_optional_bool(mapping, "robust_to_noise", False),
        prefer_sparsity=_optional_bool(mapping, "prefer_sparsity", False),
        prefer_analog_linear=_optional_bool(mapping, "prefer_analog_linear", False),
        max_error_budget=_optional_float(mapping, "max_error_budget"),
    )


def _operation_attributes(operation: TritonOperationMetadata) -> dict[str, object]:
    attributes: dict[str, object] = dict(operation.hints.to_metadata())
    for key, value in operation.attributes.items():
        if key in attributes:
            raise ValueError(f"triton operation attribute conflicts with hint: {key}")
        attributes[key] = value
    if operation.layout is not None:
        attributes["tuc.layout"] = operation.layout.value
    return attributes


def _lookup_tensor(
    tensors: dict[str, TensorRef],
    name: str,
    usage: str,
) -> TensorRef:
    tensor = tensors.get(name)
    if tensor is None:
        raise ValueError(f"triton operation references unknown {usage} tensor: {name}")
    return tensor


def _require_name_sequence(value: object, label: str) -> tuple[str, ...]:
    values = _require_plain_sequence(value, label)
    if not values:
        raise ValueError(f"{label} must not be empty")
    if any(not isinstance(item, str) for item in values):
        raise TypeError(f"{label} must contain strings")
    return tuple(cast(tuple[str, ...], values))


def _string_tuple(mapping: dict[str, object], key: str) -> tuple[str, ...]:
    return _require_name_sequence(mapping.get(key), key)


def _reject_reserved_attributes(attributes: Mapping[str, object]) -> None:
    if not isinstance(attributes, Mapping):
        raise TypeError("triton attributes must be a mapping")
    for key in attributes:
        if not isinstance(key, str):
            raise TypeError("triton attribute keys must be strings")
        if key.startswith(_RESERVED_ATTRIBUTE_PREFIX):
            raise ValueError("triton frontend metadata must not contain reserved tuc.* keys")


def _require_plain_mapping(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise TypeError(f"{label} must be a plain mapping")
    if any(not isinstance(key, str) for key in value):
        raise TypeError(f"{label} keys must be strings")
    return cast(dict[str, object], value)


def _require_plain_sequence(value: object, label: str) -> tuple[object, ...]:
    if type(value) is list:
        return tuple(cast(list[object], value))
    if type(value) is tuple:
        return cast(tuple[object, ...], value)
    raise TypeError(f"{label} must be a plain sequence")


def _reject_unknown_keys(
    mapping: dict[str, object],
    allowed_keys: frozenset[str],
    label: str,
) -> None:
    unknown = sorted(set(mapping) - allowed_keys)
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"{label} contains unsupported keys: {joined}")


def _require_string(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise TypeError(f"{key} must be a string")
    return value


def _optional_string(mapping: dict[str, object], key: str, default: str) -> str:
    if key not in mapping:
        return default
    return _require_string(mapping, key)


def _require_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer")
    return value


def _optional_bool(mapping: dict[str, object], key: str, default: bool) -> bool:
    if key not in mapping:
        return default
    value = mapping[key]
    if type(value) is not bool:
        raise TypeError(f"{key} must be a boolean")
    return value


def _optional_float(mapping: dict[str, object], key: str) -> float | None:
    if key not in mapping or mapping[key] is None:
        return None
    value = mapping[key]
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{key} must be a number")
    return float(value)


def _enum_from_string(value: str, enum_type: type[_EnumT], label: str) -> _EnumT:
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"unsupported {label}: {value!r}") from exc


__all__ = [
    "MAX_TRITON_METADATA_OPERATIONS",
    "MAX_TRITON_METADATA_TENSORS",
    "TritonKernelMetadata",
    "TritonOperationMetadata",
    "TritonTensorMetadata",
    "triton_metadata_to_compute_graph",
]
