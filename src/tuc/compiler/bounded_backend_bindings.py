"""Bounded data-only JSON for the existing closed source-target bindings."""

from __future__ import annotations

import json
from typing import NoReturn, cast

from tuc.backends.base import BackendCapability
from tuc.backends.bounded_dag import DAGTarget
from tuc.compiler.bounded_cpu_json import _array, _decode, _object
from tuc.compiler.bounded_source import BoundedBackendBinding, _checked_bindings
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import OperationKind

BACKEND_BINDINGS_SCHEMA = "tuc.bounded_backend_bindings.v0"
MAX_BACKEND_BINDINGS_JSON_BYTES = 65536
_OPS = frozenset({"matmul", "elementwise", "reduction", "softmax"})
_FIELDS = frozenset({
    "name", "target", "supported_ops", "preferred_for", "supports_noise_model",
    "supports_calibration", "max_error_budget", "memory_domain", "supported_layouts",
    "produced_layouts",
})


class BoundedBackendBindingsError(ValueError):
    """Closed diagnostic, without caller data or host information."""

    def __init__(self) -> None:
        super().__init__("backend_bindings_json_rejected")

    @property
    def reason(self) -> str:
        return "backend_bindings_json_rejected"


def _reject() -> NoReturn:
    raise BoundedBackendBindingsError()


def _operations(value: object) -> frozenset[OperationKind]:
    items = _array(value, 0, 4)
    if any(type(item) is not str or item not in _OPS for item in items):
        _reject()
    names = cast(list[str], items)
    if len(set(names)) != len(names):
        _reject()
    return frozenset(OperationKind(name) for name in names)


def backend_bindings_from_json(data: bytes) -> tuple[BoundedBackendBinding, ...]:
    """Decode declarations only; no discovery, imports, device or execution grant.

    The existing source compiler owns the final capability/target invariants.
    Its snapshot validator also rejects duplicate names and targets and returns
    clean, deterministically ordered records. Unknown fields never become hooks.
    """
    try:
        value = _decode(data, max_bytes=MAX_BACKEND_BINDINGS_JSON_BYTES,
                        max_depth=5, max_tokens=4096, inputs=False)
        envelope = _object(value, frozenset({"schema_version", "bindings"}), frozenset())
        if envelope["schema_version"] != BACKEND_BINDINGS_SCHEMA:
            _reject()
        bindings = []
        for raw in _array(envelope["bindings"], 1, 2):
            item = _object(raw, _FIELDS, frozenset())
            if (type(item["name"]) is not str or type(item["target"]) is not str
                    or type(item["memory_domain"]) is not str
                    or item["supported_layouts"] != ["row_major"]
                    or item["produced_layouts"] != ["row_major"]
                    or type(item["supports_noise_model"]) is not bool
                    or type(item["supports_calibration"]) is not bool):
                _reject()
            budget = item["max_error_budget"]
            if budget is not None and type(budget) not in (float, int):
                _reject()
            capability = BackendCapability(
                name=item["name"], supported_ops=_operations(item["supported_ops"]),
                preferred_for=_operations(item["preferred_for"]),
                supports_noise_model=item["supports_noise_model"],
                supports_calibration=item["supports_calibration"],
                max_error_budget=cast(float | None, budget),
                memory_domain=MemoryDomainKind(item["memory_domain"]),
                supported_layouts=frozenset({LayoutKind.ROW_MAJOR}),
                produced_layouts=frozenset({LayoutKind.ROW_MAJOR}),
            )
            bindings.append(BoundedBackendBinding(capability, DAGTarget(item["target"])))
        return _checked_bindings(tuple(bindings))
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedBackendBindingsError() from None


def backend_bindings_to_json(bindings: tuple[BoundedBackendBinding, ...]) -> bytes:
    """Serialize a fully revalidated snapshot; never dispatch caller methods."""
    try:
        records = []
        for item in _checked_bindings(bindings):
            capability = item.capability
            records.append({
                "name": capability.name, "target": item.target.value,
                "supported_ops": sorted(op.value for op in capability.supported_ops),
                "preferred_for": sorted(op.value for op in capability.preferred_for),
                "supports_noise_model": capability.supports_noise_model,
                "supports_calibration": capability.supports_calibration,
                "max_error_budget": capability.max_error_budget,
                "memory_domain": capability.memory_domain.value,
                "supported_layouts": ["row_major"], "produced_layouts": ["row_major"],
            })
        data = (json.dumps({"schema_version": BACKEND_BINDINGS_SCHEMA, "bindings": records},
                           sort_keys=True, ensure_ascii=True, allow_nan=False,
                           separators=(",", ":")).encode("ascii") + b"\n")
        if len(data) > MAX_BACKEND_BINDINGS_JSON_BYTES:
            _reject()
        return data
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise BoundedBackendBindingsError() from None


__all__ = [
    "BACKEND_BINDINGS_SCHEMA", "MAX_BACKEND_BINDINGS_JSON_BYTES",
    "BoundedBackendBindingsError", "backend_bindings_from_json", "backend_bindings_to_json",
]
