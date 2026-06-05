"""Stable text dumps for prototype TUC IR modules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from tuc.ir.model import ComputeOperation, TensorRef
from tuc.ir.modules import IRModule


def dump_module(module: IRModule) -> str:
    """Render a compact, deterministic IR dump for debugging and tests."""

    target = f' target="{module.target}"' if module.target else ""
    lines = [f'{module.stage.value}.module @{module.graph.name}{target} {{']
    if module.metadata or module.graph.metadata:
        lines.extend(_format_metadata(module.metadata, module.graph.metadata))
    for operation in module.graph.operations:
        lines.append(_format_operation(operation))
    lines.append("}")
    return "\n".join(lines)


def _format_metadata(
    module_metadata: Mapping[str, object],
    graph_metadata: Mapping[str, object],
) -> list[str]:
    lines = ["  metadata {"]
    combined = {
        **{f"module.{key}": value for key, value in module_metadata.items()},
        **{f"graph.{key}": value for key, value in graph_metadata.items()},
    }
    for key in sorted(combined):
        lines.append(f"    {key} = {_format_value(combined[key])}")
    lines.append("  }")
    return lines


def _format_operation(operation: ComputeOperation) -> str:
    results = ", ".join(f"%{tensor.name}" for tensor in operation.outputs)
    operands = ", ".join(_format_tensor_operand(tensor) for tensor in operation.inputs)
    outputs = ", ".join(_format_tensor_operand(tensor) for tensor in operation.outputs)
    attributes = _format_attributes(operation.attributes)
    return (
        f"  {results} = tuc.{operation.kind.value} @{operation.name}"
        f"({operands}) -> ({outputs}){attributes}"
    )


def _format_tensor_operand(tensor: TensorRef) -> str:
    return f"%{tensor.name}: {_format_tensor_type(tensor)}"


def _format_tensor_type(tensor: TensorRef) -> str:
    shape = "x".join(str(dimension) for dimension in tensor.shape)
    dtype = _format_dtype(tensor.dtype)
    return f"tensor<{shape}x{dtype}>"


def _format_dtype(dtype: str) -> str:
    aliases = {
        "float16": "f16",
        "float32": "f32",
        "float64": "f64",
        "int32": "i32",
        "int64": "i64",
    }
    return aliases.get(dtype, dtype)


def _format_attributes(attributes: Mapping[str, object]) -> str:
    if not attributes:
        return ""
    pairs = ", ".join(
        f"{key} = {_format_value(attributes[key])}"
        for key in sorted(attributes)
    )
    return f" {{{pairs}}}"


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, Mapping):
        pairs = ", ".join(
            f"{key}: {_format_value(value[key])}"
            for key in sorted(value)
        )
        return f"{{{pairs}}}"
    if isinstance(value, Sequence) and not isinstance(value, str):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    return str(value)
