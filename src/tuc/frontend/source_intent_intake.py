"""Schema-versioned plain-data intake for canonical Source Intent IR.

This module accepts JSON-like Python data and builds `SourceIntentModule`
objects. It does not read source files, parse source text, inspect Python
objects, import modules, discover plugins, lower IR, or produce compiler
artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SourceIntentModule,
    SourceIntentOperation,
    SourceIntentTensor,
)

SOURCE_INTENT_SCHEMA_VERSION = "source_intent.v0"
SOURCE_INTENT_INTAKE_CONTRACT = "source_intent_intake.execution_free.v0"
_TOP_LEVEL_KEYS = frozenset({"name", "schema_version", "tensors", "operations"})
_TENSOR_KEYS = frozenset({"name", "shape", "dtype"})
_OPERATION_KEYS = frozenset({"name", "family", "inputs", "outputs", "hints"})
_BLOCKED_EXECUTION_SURFACES = (
    "bytecode_inspection",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "file_system_access",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "source_parsing",
    "subprocess_execution",
)
_BLOCKED_COMPILER_OUTPUTS = (
    "metadata",
    "compute_graph",
    "tlir",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "backend_decision",
)


@dataclass(frozen=True)
class SourceIntentIntakeReport:
    """Deterministic evidence for plain-data Source Intent IR intake."""

    module_name: str
    schema_version: str
    intake_contract: str
    source_intent_contract: str
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
                f"source_intent.intake_report @{self.module_name} {{",
                f'  schema_version = "{self.schema_version}"',
                f'  intake_contract = "{self.intake_contract}"',
                f'  source_intent_contract = "{self.source_intent_contract}"',
                f"  tensor_count = {self.tensor_count}",
                f"  operation_count = {self.operation_count}",
                f'  operation_families = "{operation_families}"',
                f'  blocked_execution_surfaces = "{blocked_execution}"',
                f'  blocked_compiler_outputs = "{blocked_outputs}"',
                "}",
            )
        )


def source_intent_from_mapping(data: object) -> SourceIntentModule:
    """Build a `SourceIntentModule` from schema-versioned plain data."""

    mapping = _require_plain_mapping(data, "source-intent data")
    _reject_unknown_keys(mapping, _TOP_LEVEL_KEYS, "source-intent data")
    schema_version = _optional_string(
        mapping,
        "schema_version",
        SOURCE_INTENT_SCHEMA_VERSION,
    )
    if schema_version != SOURCE_INTENT_SCHEMA_VERSION:
        raise ValueError(
            "source-intent schema_version must be "
            f"{SOURCE_INTENT_SCHEMA_VERSION!r}"
        )
    tensors = tuple(
        _tensor_from_mapping(item)
        for item in _require_plain_sequence(mapping.get("tensors"), "tensors")
    )
    operations = tuple(
        _operation_from_mapping(item)
        for item in _require_plain_sequence(mapping.get("operations"), "operations")
    )
    return SourceIntentModule(
        name=_require_string(mapping, "name"),
        tensors=tensors,
        operations=operations,
    )


def build_source_intent_intake_report(
    module: SourceIntentModule,
) -> SourceIntentIntakeReport:
    """Build deterministic evidence for schema-versioned source-intent intake."""

    if not isinstance(module, SourceIntentModule):
        raise TypeError("source-intent intake report requires SourceIntentModule")
    if module.contract != SOURCE_INTENT_IR_CONTRACT:
        raise ValueError(
            "source-intent intake report requires contract "
            f"{SOURCE_INTENT_IR_CONTRACT!r}"
        )
    return SourceIntentIntakeReport(
        module_name=module.name,
        schema_version=SOURCE_INTENT_SCHEMA_VERSION,
        intake_contract=SOURCE_INTENT_INTAKE_CONTRACT,
        source_intent_contract=module.contract,
        tensor_count=len(module.tensors),
        operation_count=len(module.operations),
        operation_families=tuple(operation.family for operation in module.operations),
        blocked_execution_surfaces=_BLOCKED_EXECUTION_SURFACES,
        blocked_compiler_outputs=_BLOCKED_COMPILER_OUTPUTS,
    )


def _tensor_from_mapping(data: object) -> SourceIntentTensor:
    mapping = _require_plain_mapping(data, "source-intent tensor")
    _reject_unknown_keys(mapping, _TENSOR_KEYS, "source-intent tensor")
    shape = tuple(
        _require_int(item, "source-intent tensor dimension")
        for item in _require_plain_sequence(mapping.get("shape"), "shape")
    )
    return SourceIntentTensor(
        name=_require_string(mapping, "name"),
        shape=shape,
        dtype=_optional_string(mapping, "dtype", "float32"),
    )


def _operation_from_mapping(data: object) -> SourceIntentOperation:
    mapping = _require_plain_mapping(data, "source-intent operation")
    _reject_unknown_keys(mapping, _OPERATION_KEYS, "source-intent operation")
    hints = mapping.get("hints", {})
    if hints is None:
        hints = {}
    return SourceIntentOperation(
        name=_require_string(mapping, "name"),
        family=_require_string(mapping, "family"),
        inputs=_string_tuple(mapping, "inputs"),
        outputs=_string_tuple(mapping, "outputs"),
        hints=_require_plain_mapping(hints, "hints"),
    )


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


def _string_tuple(mapping: dict[str, object], key: str) -> tuple[str, ...]:
    values = _require_plain_sequence(mapping.get(key), key)
    if not values:
        raise ValueError(f"{key} must not be empty")
    if any(not isinstance(item, str) for item in values):
        raise TypeError(f"{key} must contain strings")
    return cast(tuple[str, ...], values)


__all__ = [
    "SOURCE_INTENT_INTAKE_CONTRACT",
    "SOURCE_INTENT_SCHEMA_VERSION",
    "SourceIntentIntakeReport",
    "build_source_intent_intake_report",
    "source_intent_from_mapping",
]
