"""Declarative memory-domain model for data-movement-aware TUC IR."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite
from typing import Any


class MemoryDomainKind(StrEnum):
    """Memory domains that early TUC passes can reason about declaratively."""

    HOST_RAM = "host_ram"
    GPU_HBM = "gpu_hbm"
    DEVICE_SRAM = "device_sram"
    ANALOG_WEIGHT_BANK = "analog_weight_bank"
    NEUROMORPHIC_SYNAPSE_ARRAY = "neuromorphic_synapse_array"
    PERSISTENT_NVM = "persistent_nvm"
    STREAM_BUFFER = "stream_buffer"
    UNKNOWN = "unknown"


class LayoutKind(StrEnum):
    """Small layout vocabulary for first-stage placement decisions."""

    ROW_MAJOR = "row_major"
    COLUMN_MAJOR = "column_major"
    BLOCKED = "blocked"
    VECTOR = "vector"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MemoryDomain:
    """Named memory domain and its bounded static cost hints."""

    name: str
    kind: MemoryDomainKind
    bandwidth_gb_s: float | None = None
    latency_ns: float | None = None
    energy_pj_per_byte: float | None = None
    capacity_bytes: int | None = None

    def __post_init__(self) -> None:
        _require_name(self.name, "memory domain name")
        _require_enum(self.kind, MemoryDomainKind, "memory domain kind")
        _require_positive_float(self.bandwidth_gb_s, "bandwidth_gb_s")
        _require_non_negative_float(self.latency_ns, "latency_ns")
        _require_non_negative_float(self.energy_pj_per_byte, "energy_pj_per_byte")
        _require_positive_int(self.capacity_bytes, "capacity_bytes")


@dataclass(frozen=True)
class TransferEdge:
    """Declarative data-transfer cost between two memory domains."""

    source: str
    target: str
    bandwidth_gb_s: float | None = None
    latency_ns: float | None = None
    energy_pj_per_byte: float | None = None

    def __post_init__(self) -> None:
        _require_name(self.source, "transfer source")
        _require_name(self.target, "transfer target")
        if self.source == self.target:
            raise ValueError("transfer source and target must differ")
        _require_positive_float(self.bandwidth_gb_s, "bandwidth_gb_s")
        _require_non_negative_float(self.latency_ns, "latency_ns")
        _require_non_negative_float(self.energy_pj_per_byte, "energy_pj_per_byte")


@dataclass(frozen=True)
class LayoutConstraint:
    """Layout constraints attached to movement estimates and backend decisions."""

    layout: LayoutKind
    tile_shape: tuple[int, ...] = ()
    alignment_bytes: int | None = None

    def __post_init__(self) -> None:
        _require_enum(self.layout, LayoutKind, "layout")
        if any(dimension <= 0 for dimension in self.tile_shape):
            raise ValueError("layout tile dimensions must be positive")
        _require_positive_int(self.alignment_bytes, "alignment_bytes")


@dataclass(frozen=True)
class MovementEstimate:
    """Per-operation data movement and compute-intensity estimate."""

    bytes_read: int
    bytes_written: int
    arithmetic_ops: int
    arithmetic_intensity: float
    preferred_domain: MemoryDomainKind
    layout: LayoutConstraint = field(
        default_factory=lambda: LayoutConstraint(LayoutKind.ROW_MAJOR)
    )
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_non_negative_int(self.bytes_read, "bytes_read")
        _require_non_negative_int(self.bytes_written, "bytes_written")
        _require_non_negative_int(self.arithmetic_ops, "arithmetic_ops")
        _require_non_negative_float(self.arithmetic_intensity, "arithmetic_intensity")
        _require_enum(self.preferred_domain, MemoryDomainKind, "preferred_domain")
        if any(not note for note in self.notes):
            raise ValueError("movement estimate notes must not be empty")

    def as_attributes(self) -> dict[str, Any]:
        """Return stable IR attributes used by deterministic dumps."""

        attributes: dict[str, Any] = {
            "tuc.arithmetic_intensity": self.arithmetic_intensity,
            "tuc.arithmetic_ops": self.arithmetic_ops,
            "tuc.bytes_read": self.bytes_read,
            "tuc.bytes_written": self.bytes_written,
            "tuc.layout": self.layout.layout.value,
            "tuc.layout_tile_shape": self.layout.tile_shape,
            "tuc.preferred_memory_domain": self.preferred_domain.value,
        }
        if self.layout.alignment_bytes is not None:
            attributes["tuc.layout_alignment_bytes"] = self.layout.alignment_bytes
        if self.notes:
            attributes["tuc.movement_notes"] = self.notes
        return attributes


def dtype_size_bytes(dtype: str) -> int:
    """Return byte width for supported tensor dtypes, rejecting unknown aliases."""

    if not isinstance(dtype, str):
        raise TypeError("tensor dtype must be a string")

    sizes = {
        "bool": 1,
        "bfloat16": 2,
        "bf16": 2,
        "float16": 2,
        "fp16": 2,
        "f16": 2,
        "float32": 4,
        "fp32": 4,
        "f32": 4,
        "float64": 8,
        "fp64": 8,
        "f64": 8,
        "int8": 1,
        "i8": 1,
        "uint8": 1,
        "u8": 1,
        "int16": 2,
        "i16": 2,
        "uint16": 2,
        "u16": 2,
        "int32": 4,
        "i32": 4,
        "uint32": 4,
        "u32": 4,
        "int64": 8,
        "i64": 8,
        "uint64": 8,
        "u64": 8,
    }
    normalized = dtype.strip().lower()
    if not normalized:
        raise ValueError("tensor dtype must not be empty")
    try:
        return sizes[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported tensor dtype for movement estimate: {dtype!r}") from exc


def _require_name(value: str, label: str) -> None:
    if not value:
        raise ValueError(f"{label} must not be empty")


def _require_enum(value: object, enum_type: type[StrEnum], label: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{label} must be {enum_type.__name__}")


def _require_non_negative_int(value: int | None, label: str) -> None:
    if value is not None and (isinstance(value, bool) or value < 0):
        raise ValueError(f"{label} must be non-negative")


def _require_positive_int(value: int | None, label: str) -> None:
    if value is not None and (isinstance(value, bool) or value <= 0):
        raise ValueError(f"{label} must be positive")


def _require_non_negative_float(value: float | None, label: str) -> None:
    if value is not None and (isinstance(value, bool) or not isfinite(value) or value < 0):
        raise ValueError(f"{label} must be non-negative")


def _require_positive_float(value: float | None, label: str) -> None:
    if value is not None and (isinstance(value, bool) or not isfinite(value) or value <= 0):
        raise ValueError(f"{label} must be positive")


__all__ = [
    "LayoutConstraint",
    "LayoutKind",
    "MemoryDomain",
    "MemoryDomainKind",
    "MovementEstimate",
    "TransferEdge",
    "dtype_size_bytes",
]
