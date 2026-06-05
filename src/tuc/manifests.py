"""Schema-versioned JSON manifest loaders for TUC prototype metadata."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from enum import StrEnum
from math import isfinite
from pathlib import Path
from typing import NoReturn, TypeVar, cast

from tuc.backends.base import BackendCapability
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.ir.model import OperationKind
from tuc.runtime.plan import TransferCostProfile

BACKEND_CAPABILITY_SCHEMA_VERSION = "tuc.backend_capability.v0"
TRANSFER_COST_PROFILE_SCHEMA_VERSION = "tuc.transfer_cost_profile.v0"
MAX_MANIFEST_BYTES = 64 * 1024
MAX_MANIFEST_DEPTH = 8
MAX_MANIFEST_OBJECT_KEYS = 64
MAX_MANIFEST_LIST_ITEMS = 128
MAX_MANIFEST_STRING_BYTES = 4096
MAX_MANIFEST_INTEGER_ABS = 2**63 - 1
MAX_MANIFEST_FLOAT_ABS = 1.0e308

_MANIFEST_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_BACKEND_CAPABILITY_KEYS = frozenset(
    {
        "schema_version",
        "name",
        "supported_ops",
        "supports_noise_model",
        "supports_calibration",
        "preferred_for",
        "max_error_budget",
        "memory_domain",
        "supported_layouts",
        "produced_layouts",
    }
)
_TRANSFER_COST_PROFILE_KEYS = frozenset(
    {
        "schema_version",
        "name",
        "fallback",
        "edges",
    }
)

_EnumT = TypeVar("_EnumT", bound=StrEnum)


class ManifestError(ValueError):
    """Raised when a manifest file fails TUC's schema or safety validation."""


def load_json_manifest(
    path: str | Path,
    *,
    max_bytes: int = MAX_MANIFEST_BYTES,
) -> dict[str, object]:
    """Load one bounded JSON object without executing code or accepting duplicates."""

    manifest_path = Path(path)
    if manifest_path.suffix != ".json":
        raise ManifestError("manifest path must use the .json suffix")
    if manifest_path.is_symlink():
        raise ManifestError("manifest path must not be a symlink")
    if not manifest_path.is_file():
        raise ManifestError("manifest path must refer to a regular file")

    size = manifest_path.stat().st_size
    if size > max_bytes:
        raise ManifestError("manifest file exceeds size limit")

    payload = manifest_path.read_bytes()
    if len(payload) > max_bytes:
        raise ManifestError("manifest file exceeds size limit")
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("manifest file must be UTF-8") from exc

    try:
        loaded = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ManifestError("manifest file must contain valid JSON") from exc

    _validate_json_value(loaded, depth=0)
    if type(loaded) is not dict:
        raise ManifestError("manifest top-level value must be a JSON object")
    return cast(dict[str, object], loaded)


def load_backend_capability_manifest(path: str | Path) -> BackendCapability:
    """Load a versioned backend capability manifest as pure data."""

    manifest = load_json_manifest(path)
    _reject_unknown_keys(manifest, _BACKEND_CAPABILITY_KEYS, "backend capability manifest")
    _require_schema_version(
        manifest,
        BACKEND_CAPABILITY_SCHEMA_VERSION,
        "backend capability manifest",
    )
    return BackendCapability(
        name=_require_simple_string(manifest, "name", "backend capability manifest"),
        supported_ops=_required_enum_set(
            manifest,
            "supported_ops",
            OperationKind,
            "backend capability manifest",
        ),
        supports_noise_model=_optional_bool(manifest, "supports_noise_model", False),
        supports_calibration=_optional_bool(manifest, "supports_calibration", False),
        preferred_for=_optional_enum_set(
            manifest,
            "preferred_for",
            OperationKind,
            frozenset(),
            "backend capability manifest",
        ),
        max_error_budget=_optional_number(manifest, "max_error_budget"),
        memory_domain=_optional_enum(
            manifest,
            "memory_domain",
            MemoryDomainKind,
            MemoryDomainKind.GPU_HBM,
            "backend capability manifest",
        ),
        supported_layouts=_optional_enum_set(
            manifest,
            "supported_layouts",
            LayoutKind,
            frozenset({LayoutKind.ROW_MAJOR}),
            "backend capability manifest",
        ),
        produced_layouts=_optional_enum_set(
            manifest,
            "produced_layouts",
            LayoutKind,
            frozenset({LayoutKind.ROW_MAJOR}),
            "backend capability manifest",
        ),
    )


def load_transfer_cost_profile_manifest(path: str | Path) -> TransferCostProfile:
    """Load a versioned transfer-cost profile manifest as pure data."""

    manifest = load_json_manifest(path)
    _reject_unknown_keys(manifest, _TRANSFER_COST_PROFILE_KEYS, "transfer cost manifest")
    _require_schema_version(
        manifest,
        TRANSFER_COST_PROFILE_SCHEMA_VERSION,
        "transfer cost manifest",
    )
    payload: dict[str, object] = {
        "name": manifest.get("name"),
        "fallback": manifest.get("fallback"),
        "edges": manifest.get("edges", ()),
    }
    return TransferCostProfile.from_manifest(payload)


def _reject_duplicate_keys(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError("manifest JSON object contains duplicate keys")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> NoReturn:
    raise ManifestError(f"manifest JSON must not contain non-finite number {value!r}")


def _validate_json_value(value: object, *, depth: int) -> None:
    if depth > MAX_MANIFEST_DEPTH:
        raise ManifestError("manifest JSON exceeds nesting limit")
    if value is None or type(value) is bool:
        return
    if type(value) is str:
        if len(value.encode("utf-8")) > MAX_MANIFEST_STRING_BYTES:
            raise ManifestError("manifest JSON string exceeds size limit")
        return
    if type(value) is int:
        if abs(value) > MAX_MANIFEST_INTEGER_ABS:
            raise ManifestError("manifest JSON integer exceeds numeric limit")
        return
    if type(value) is float:
        if not isfinite(value) or abs(value) > MAX_MANIFEST_FLOAT_ABS:
            raise ManifestError("manifest JSON float must be finite and bounded")
        return
    if type(value) is list:
        values = cast(list[object], value)
        if len(values) > MAX_MANIFEST_LIST_ITEMS:
            raise ManifestError("manifest JSON list exceeds item limit")
        for item in values:
            _validate_json_value(item, depth=depth + 1)
        return
    if type(value) is dict:
        mapping = cast(dict[str, object], value)
        if len(mapping) > MAX_MANIFEST_OBJECT_KEYS:
            raise ManifestError("manifest JSON object exceeds key limit")
        for key, item in mapping.items():
            if not isinstance(key, str):
                raise ManifestError("manifest JSON object keys must be strings")
            if len(key.encode("utf-8")) > MAX_MANIFEST_STRING_BYTES:
                raise ManifestError("manifest JSON object key exceeds size limit")
            _validate_json_value(item, depth=depth + 1)
        return
    raise ManifestError("manifest JSON contains unsupported value type")


def _reject_unknown_keys(
    manifest: dict[str, object],
    allowed_keys: frozenset[str],
    label: str,
) -> None:
    unknown = sorted(set(manifest) - allowed_keys)
    if unknown:
        joined = ", ".join(unknown)
        raise ManifestError(f"{label} contains unsupported keys: {joined}")


def _require_schema_version(
    manifest: dict[str, object],
    expected: str,
    label: str,
) -> None:
    schema_version = _require_simple_string(manifest, "schema_version", label)
    if schema_version != expected:
        raise ManifestError(f"{label} schema_version must be {expected!r}")


def _require_simple_string(manifest: dict[str, object], key: str, label: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not _MANIFEST_NAME_RE.fullmatch(value):
        raise ManifestError(f"{label} {key} must be a simple string")
    return value


def _required_string_sequence(
    manifest: dict[str, object],
    key: str,
    label: str,
) -> tuple[str, ...]:
    value = manifest.get(key)
    if type(value) is not list:
        raise ManifestError(f"{label} {key} must be a JSON array")
    values = cast(list[object], value)
    if any(not isinstance(item, str) for item in values):
        raise ManifestError(f"{label} {key} must contain strings")
    return tuple(cast(list[str], values))


def _required_enum_set(
    manifest: dict[str, object],
    key: str,
    enum_type: type[_EnumT],
    label: str,
) -> frozenset[_EnumT]:
    return _enum_set_from_values(_required_string_sequence(manifest, key, label), enum_type, label)


def _optional_enum_set(
    manifest: dict[str, object],
    key: str,
    enum_type: type[_EnumT],
    default: frozenset[_EnumT],
    label: str,
) -> frozenset[_EnumT]:
    if key not in manifest:
        return default
    return _enum_set_from_values(_required_string_sequence(manifest, key, label), enum_type, label)


def _enum_set_from_values(
    values: tuple[str, ...],
    enum_type: type[_EnumT],
    label: str,
) -> frozenset[_EnumT]:
    result: set[_EnumT] = set()
    for value in values:
        try:
            result.add(enum_type(value))
        except ValueError as exc:
            message = f"{label} contains unsupported {enum_type.__name__}: {value!r}"
            raise ManifestError(message) from exc
    return frozenset(result)


def _optional_enum(
    manifest: dict[str, object],
    key: str,
    enum_type: type[_EnumT],
    default: _EnumT,
    label: str,
) -> _EnumT:
    if key not in manifest:
        return default
    value = _require_simple_string(manifest, key, label)
    try:
        return enum_type(value)
    except ValueError as exc:
        message = f"{label} contains unsupported {enum_type.__name__}: {value!r}"
        raise ManifestError(message) from exc


def _optional_bool(manifest: dict[str, object], key: str, default: bool) -> bool:
    if key not in manifest:
        return default
    value = manifest[key]
    if type(value) is not bool:
        raise ManifestError(f"manifest {key} must be a boolean")
    return value


def _optional_number(manifest: dict[str, object], key: str) -> float | None:
    if key not in manifest or manifest[key] is None:
        return None
    value = manifest[key]
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ManifestError(f"manifest {key} must be a number")
    return float(value)


__all__ = [
    "BACKEND_CAPABILITY_SCHEMA_VERSION",
    "MAX_MANIFEST_BYTES",
    "ManifestError",
    "TRANSFER_COST_PROFILE_SCHEMA_VERSION",
    "load_backend_capability_manifest",
    "load_json_manifest",
    "load_transfer_cost_profile_manifest",
]
