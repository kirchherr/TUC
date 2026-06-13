"""Canonical source-intent IR data model.

This module defines a bounded, data-only frontend contract. It is intentionally
not connected to metadata conversion, graph construction, lowering, runtime
planning, backend decisions, plugin discovery, or code execution.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import cast

SOURCE_INTENT_IR_CONTRACT = "source_intent_ir.canonical.v0"
SOURCE_INTENT_RETURN_POLICY = "explicit_public_returns"
MAX_SOURCE_INTENT_TENSORS = 4096
MAX_SOURCE_INTENT_OPERATIONS = 4096
MAX_SOURCE_INTENT_ARITY = 16
MAX_SOURCE_INTENT_RANK = 8
MAX_SOURCE_INTENT_DIMENSION = 2**31 - 1

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DTYPE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_ALLOWED_OPERATION_FAMILIES = frozenset(
    {"elementwise", "matmul", "reduction", "softmax"}
)
_ALLOWED_HINTS = frozenset(
    {
        "max_error_budget",
        "prefer_linear_accelerator",
        "prefer_sparsity",
        "robust_to_noise",
    }
)
_ALLOWED_ATTRIBUTES = frozenset({"axis"})
_AXIS_OPERATION_FAMILIES = frozenset({"reduction", "softmax"})
_BOOLEAN_HINTS = frozenset(
    {"prefer_linear_accelerator", "prefer_sparsity", "robust_to_noise"}
)
_FORBIDDEN_KEY_PREFIXES = ("tuc.",)
_FORBIDDEN_SURFACE_KEYS = frozenset(
    {
        "backend",
        "backend_name",
        "bytecode",
        "callable",
        "command",
        "cuda",
        "device",
        "device_path",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_artifact",
        "gpu",
        "hardware",
        "import_module",
        "jit_function",
        "memory_domain",
        "module",
        "network",
        "placement",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "rocm",
        "subprocess",
        "target",
        "url",
        "vendor",
    }
)
_LOWERING_BLOCKS = (
    "metadata",
    "compute_graph",
    "tlir",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "backend_decision",
)


@dataclass(frozen=True)
class SourceIntentTensor:
    """Tensor identity and shape as canonical source intent."""

    name: str
    shape: tuple[int, ...]
    dtype: str = "float32"

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "source-intent tensor name")
        if not isinstance(self.dtype, str) or not _DTYPE_RE.fullmatch(self.dtype):
            raise ValueError("source-intent tensor dtype must be a simple identifier")
        shape = tuple(self.shape)
        if not shape:
            raise ValueError("source-intent tensor shape must not be empty")
        if len(shape) > MAX_SOURCE_INTENT_RANK:
            raise ValueError("source-intent tensor rank exceeds contract limit")
        for dimension in shape:
            if (
                not isinstance(dimension, int)
                or isinstance(dimension, bool)
                or dimension <= 0
                or dimension > MAX_SOURCE_INTENT_DIMENSION
            ):
                raise ValueError(
                    "source-intent tensor dimensions must be positive bounded integers"
                )
        object.__setattr__(self, "shape", shape)

    def dump(self) -> str:
        shape = "x".join(str(dimension) for dimension in self.shape)
        return f"tensor %{self.name} : tensor<{shape}x{self.dtype}>"


@dataclass(frozen=True)
class SourceIntentOperation:
    """Operation family, symbolic operands, and neutral hints."""

    name: str
    family: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    hints: Mapping[str, object] = field(default_factory=dict)
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "source-intent operation name")
        if not isinstance(self.family, str):
            raise TypeError("source-intent operation family must be a string")
        if self.family not in _ALLOWED_OPERATION_FAMILIES:
            raise ValueError(f"unsupported source-intent operation family: {self.family}")
        inputs = _require_name_sequence(self.inputs, "source-intent operation inputs")
        outputs = _require_name_sequence(self.outputs, "source-intent operation outputs")
        if len(inputs) > MAX_SOURCE_INTENT_ARITY:
            raise ValueError("source-intent operation input count exceeds contract limit")
        if len(outputs) > MAX_SOURCE_INTENT_ARITY:
            raise ValueError("source-intent operation output count exceeds contract limit")
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "outputs", outputs)
        object.__setattr__(self, "hints", _freeze_hints(self.hints))
        object.__setattr__(
            self,
            "attributes",
            _freeze_attributes(self.attributes, self.family),
        )

    def dump(self) -> str:
        inputs = ",".join(f"%{name}" for name in self.inputs)
        outputs = ",".join(f"%{name}" for name in self.outputs)
        hints = _format_hints(self.hints)
        line = (
            f"op @{self.name} family={self.family} "
            f"inputs={inputs} outputs={outputs} hints={hints}"
        )
        if self.attributes:
            line = f"{line} attributes={_format_hints(self.attributes)}"
        return line


@dataclass(frozen=True)
class SourceIntentReturn:
    """Public return name bound to one source-intent terminal tensor."""

    public_name: str
    tensor_name: str
    required: bool = True

    def __post_init__(self) -> None:
        _validate_identifier(self.public_name, "source-intent return public_name")
        _validate_identifier(self.tensor_name, "source-intent return tensor_name")
        if type(self.required) is not bool:
            raise TypeError("source-intent return required flag must be a boolean")

    def dump(self) -> str:
        required = str(self.required).lower()
        return (
            f"return @{self.public_name} tensor=%{self.tensor_name} "
            f"required={required}"
        )


@dataclass(frozen=True)
class SourceIntentModule:
    """A canonical source-intent module that remains disconnected from lowering."""

    name: str
    tensors: tuple[SourceIntentTensor, ...]
    operations: tuple[SourceIntentOperation, ...]
    contract: str = SOURCE_INTENT_IR_CONTRACT
    returns: tuple[SourceIntentReturn, ...] = ()

    def __post_init__(self) -> None:
        _validate_identifier(self.name, "source-intent module name")
        if self.contract != SOURCE_INTENT_IR_CONTRACT:
            raise ValueError(
                "source-intent module contract must be "
                f"{SOURCE_INTENT_IR_CONTRACT!r}"
            )
        tensors = tuple(self.tensors)
        operations = tuple(self.operations)
        returns = tuple(self.returns)
        if not tensors:
            raise ValueError("source-intent module must contain tensors")
        if not operations:
            raise ValueError("source-intent module must contain operations")
        if len(tensors) > MAX_SOURCE_INTENT_TENSORS:
            raise ValueError("source-intent tensor count exceeds contract limit")
        if len(operations) > MAX_SOURCE_INTENT_OPERATIONS:
            raise ValueError("source-intent operation count exceeds contract limit")
        _validate_unique_names((tensor.name for tensor in tensors), "tensor")
        _validate_unique_names((operation.name for operation in operations), "operation")
        tensor_names = frozenset(tensor.name for tensor in tensors)
        for operation in operations:
            for name in (*operation.inputs, *operation.outputs):
                if name not in tensor_names:
                    raise ValueError(
                        f"source-intent operation {operation.name!r} "
                        f"references unknown tensor: {name}"
                    )
        _validate_operation_attributes(operations, tensors)
        _validate_returns(returns, tensors, operations)
        object.__setattr__(self, "tensors", tensors)
        object.__setattr__(self, "operations", operations)
        object.__setattr__(self, "returns", returns)

    def dump(self) -> str:
        lines = [
            f"source_intent.module @{self.name} {{",
            f'  contract = "{self.contract}"',
            f"  tensor_count = {len(self.tensors)}",
            f"  operation_count = {len(self.operations)}",
            f'  blocked_lowering = "{",".join(_LOWERING_BLOCKS)}"',
        ]
        if self.returns:
            lines.append(f'  return_policy = "{SOURCE_INTENT_RETURN_POLICY}"')
            lines.append(f"  return_count = {len(self.returns)}")
        lines.extend(f"  {tensor.dump()}" for tensor in self.tensors)
        lines.extend(f"  {operation.dump()}" for operation in self.operations)
        lines.extend(f"  {source_return.dump()}" for source_return in self.returns)
        lines.append("}")
        return "\n".join(lines)


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a simple identifier")


def _require_name_sequence(value: object, label: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{label} must be a tuple")
    sequence = cast(tuple[object, ...], value)
    if not sequence:
        raise ValueError(f"{label} must not be empty")
    for item in sequence:
        if not isinstance(item, str):
            raise TypeError(f"{label} must contain strings")
        _validate_identifier(item, label)
    return cast(tuple[str, ...], sequence)


def _validate_unique_names(values: Iterable[str], label: str) -> None:
    names = tuple(values)
    if len(names) != len(set(names)):
        raise ValueError(f"source-intent {label} names must be unique")


def _validate_returns(
    returns: tuple[SourceIntentReturn, ...],
    tensors: tuple[SourceIntentTensor, ...],
    operations: tuple[SourceIntentOperation, ...],
) -> None:
    if type(returns) is not tuple:
        raise TypeError("source-intent returns must be a tuple")
    if len(returns) > MAX_SOURCE_INTENT_TENSORS:
        raise ValueError("source-intent return count exceeds contract limit")
    tensor_names = frozenset(tensor.name for tensor in tensors)
    produced_names = frozenset(
        output for operation in operations for output in operation.outputs
    )
    consumed_names = frozenset(
        input_name for operation in operations for input_name in operation.inputs
    )
    public_names: list[str] = []
    return_tensor_names: list[str] = []
    for source_return in returns:
        if not isinstance(source_return, SourceIntentReturn):
            raise TypeError("source-intent returns must contain SourceIntentReturn")
        public_names.append(source_return.public_name)
        return_tensor_names.append(source_return.tensor_name)
        if source_return.tensor_name not in tensor_names:
            raise ValueError(
                "source-intent return references unknown tensor: "
                f"{source_return.tensor_name}"
            )
        if source_return.tensor_name not in produced_names:
            raise ValueError(
                "source-intent return tensor must be produced by an operation"
            )
        if source_return.tensor_name in consumed_names:
            raise ValueError("source-intent return tensor must be terminal")
    _validate_unique_names(public_names, "return public")
    _validate_unique_names(return_tensor_names, "return tensor")


def _freeze_hints(hints: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(hints, Mapping):
        raise TypeError("source-intent hints must be a mapping")
    frozen: dict[str, object] = {}
    for key in sorted(hints):
        if not isinstance(key, str):
            raise TypeError("source-intent hint keys must be strings")
        _reject_forbidden_key(key, "source-intent hint")
        if key not in _ALLOWED_HINTS:
            raise ValueError(f"source-intent hint contains unsupported key: {key}")
        value = hints[key]
        if key in _BOOLEAN_HINTS:
            if type(value) is not bool:
                raise TypeError(f"{key} must be a boolean")
            frozen[key] = value
        elif key == "max_error_budget":
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise TypeError("max_error_budget must be a number")
            number = float(value)
            if not isfinite(number) or number < 0.0:
                raise ValueError("max_error_budget must be finite and non-negative")
            frozen[key] = number
    return MappingProxyType(frozen)


def _freeze_attributes(
    attributes: Mapping[str, object],
    family: str,
) -> Mapping[str, object]:
    if not isinstance(attributes, Mapping):
        raise TypeError("source-intent attributes must be a mapping")
    frozen: dict[str, object] = {}
    for key in sorted(attributes):
        if not isinstance(key, str):
            raise TypeError("source-intent attribute keys must be strings")
        _reject_forbidden_key(key, "source-intent attribute")
        if key not in _ALLOWED_ATTRIBUTES:
            raise ValueError(f"source-intent attribute contains unsupported key: {key}")
        value = attributes[key]
        if key == "axis":
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError("source-intent axis attribute must be an integer")
            if family not in _AXIS_OPERATION_FAMILIES:
                raise ValueError(
                    "source-intent axis attribute is allowed only for "
                    "reduction and softmax"
                )
            frozen[key] = value
    if family in _AXIS_OPERATION_FAMILIES and "axis" not in frozen:
        raise ValueError("source-intent reduction and softmax require axis attribute")
    if family not in _AXIS_OPERATION_FAMILIES and frozen:
        raise ValueError("source-intent operation family does not accept attributes")
    return MappingProxyType(frozen)


def _validate_operation_attributes(
    operations: tuple[SourceIntentOperation, ...],
    tensors: tuple[SourceIntentTensor, ...],
) -> None:
    tensors_by_name = {tensor.name: tensor for tensor in tensors}
    for operation in operations:
        if operation.family not in _AXIS_OPERATION_FAMILIES:
            continue
        if len(operation.inputs) != 1 or len(operation.outputs) != 1:
            raise ValueError(
                "source-intent reduction and softmax require one input and one output"
            )
        axis = operation.attributes.get("axis")
        if not isinstance(axis, int) or isinstance(axis, bool):
            raise TypeError("source-intent axis attribute must be an integer")
        input_shape = tensors_by_name[operation.inputs[0]].shape
        output_shape = tensors_by_name[operation.outputs[0]].shape
        normalized_axis = axis + len(input_shape) if axis < 0 else axis
        if normalized_axis < 0 or normalized_axis >= len(input_shape):
            raise ValueError("source-intent axis attribute is out of bounds")
        if operation.family == "softmax" and output_shape != input_shape:
            raise ValueError("source-intent softmax output shape must match input shape")
        if operation.family == "reduction":
            expected = input_shape[:normalized_axis] + input_shape[normalized_axis + 1 :]
            if not expected:
                raise ValueError("source-intent reduction scalar output unsupported")
            if output_shape != expected:
                raise ValueError("source-intent reduction output shape mismatch")


def _reject_forbidden_key(key: str, label: str) -> None:
    if key.startswith(_FORBIDDEN_KEY_PREFIXES) or key in _FORBIDDEN_SURFACE_KEYS:
        raise ValueError(f"{label} contains forbidden execution or hardware key: {key}")


def _format_hints(hints: Mapping[str, object]) -> str:
    if not hints:
        return "{}"
    parts = []
    for key in sorted(hints):
        value = hints[key]
        formatted = str(value).lower() if isinstance(value, bool) else str(value)
        parts.append(f"{key}={formatted}")
    return "{" + ",".join(parts) + "}"


__all__ = [
    "MAX_SOURCE_INTENT_ARITY",
    "MAX_SOURCE_INTENT_OPERATIONS",
    "MAX_SOURCE_INTENT_TENSORS",
    "SOURCE_INTENT_IR_CONTRACT",
    "SOURCE_INTENT_RETURN_POLICY",
    "SourceIntentModule",
    "SourceIntentOperation",
    "SourceIntentReturn",
    "SourceIntentTensor",
]
