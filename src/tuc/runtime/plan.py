"""Runtime data-movement plan objects."""

from __future__ import annotations

import re
from dataclasses import dataclass

from tuc.ir.memory import LayoutKind, MemoryDomainKind

MAX_RUNTIME_TRANSFER_BYTES = 2**63 - 1
_PLAN_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class RuntimeTransferEdge:
    """Concrete data transfer required between two runtime memory domains."""

    tensor_name: str
    source_operation: str
    target_operation: str
    source_backend: str
    target_backend: str
    source_domain: MemoryDomainKind
    target_domain: MemoryDomainKind
    source_layout: LayoutKind
    target_layout: LayoutKind
    bytes_moved: int

    def __post_init__(self) -> None:
        _require_name(self.tensor_name, "tensor_name")
        _require_name(self.source_operation, "source_operation")
        _require_name(self.target_operation, "target_operation")
        _require_name(self.source_backend, "source_backend")
        _require_name(self.target_backend, "target_backend")
        _require_enum(self.source_domain, MemoryDomainKind, "source_domain")
        _require_enum(self.target_domain, MemoryDomainKind, "target_domain")
        _require_enum(self.source_layout, LayoutKind, "source_layout")
        _require_enum(self.target_layout, LayoutKind, "target_layout")
        _require_transfer_bytes(self.bytes_moved, "bytes_moved")
        if self.source_domain == self.target_domain:
            raise ValueError("runtime transfer domains must differ")


@dataclass(frozen=True)
class LayoutConversionCost:
    """Concrete layout conversion required before an operation can consume a tensor."""

    tensor_name: str
    target_operation: str
    source_layout: LayoutKind
    target_layout: LayoutKind
    bytes_converted: int
    reason: str
    source_operation: str | None = None

    def __post_init__(self) -> None:
        _require_name(self.tensor_name, "tensor_name")
        _require_name(self.target_operation, "target_operation")
        if self.source_operation is not None:
            _require_name(self.source_operation, "source_operation")
        _require_name(self.reason, "reason")
        _require_enum(self.source_layout, LayoutKind, "source_layout")
        _require_enum(self.target_layout, LayoutKind, "target_layout")
        _require_transfer_bytes(self.bytes_converted, "bytes_converted")
        if self.source_layout == self.target_layout:
            raise ValueError("layout conversion requires different layouts")


def _require_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PLAN_NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must be a simple runtime-plan name")


def _require_enum(value: object, enum_type: type[object], label: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{label} must be {enum_type.__name__}")


def _require_transfer_bytes(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    if value > MAX_RUNTIME_TRANSFER_BYTES:
        raise ValueError(f"{label} exceeds runtime transfer limit")


__all__ = [
    "LayoutConversionCost",
    "RuntimeTransferEdge",
]
