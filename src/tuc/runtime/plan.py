"""Runtime data-movement plan objects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import isfinite

from tuc.ir.memory import LayoutKind, MemoryDomainKind

MAX_RUNTIME_TRANSFER_BYTES = 2**63 - 1
_PLAN_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class TransferCostEstimate:
    """Deterministic prototype cost estimate for one runtime transfer."""

    bytes_moved: int
    bandwidth_gb_s: float
    base_latency_ns: float
    energy_pj_per_byte: float

    def __post_init__(self) -> None:
        _require_transfer_bytes(self.bytes_moved, "bytes_moved")
        _require_positive_finite_float(self.bandwidth_gb_s, "bandwidth_gb_s")
        _require_non_negative_finite_float(self.base_latency_ns, "base_latency_ns")
        _require_non_negative_finite_float(
            self.energy_pj_per_byte,
            "energy_pj_per_byte",
        )

    @property
    def estimated_latency_ns(self) -> float:
        """Return latency estimate using decimal GB/s, where 1 GB/s equals 1 byte/ns."""

        return self.base_latency_ns + (self.bytes_moved / self.bandwidth_gb_s)

    @property
    def estimated_energy_pj(self) -> float:
        """Return energy estimate in picojoules."""

        return self.bytes_moved * self.energy_pj_per_byte


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
    cost_estimate: TransferCostEstimate | None = None

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
        if self.cost_estimate is None:
            object.__setattr__(
                self,
                "cost_estimate",
                estimate_default_transfer_cost(
                    bytes_moved=self.bytes_moved,
                    source_domain=self.source_domain,
                    target_domain=self.target_domain,
                ),
            )
        elif self.cost_estimate.bytes_moved != self.bytes_moved:
            raise ValueError("transfer cost bytes must match bytes_moved")


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


def _require_positive_finite_float(value: float, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{label} must be a number")
    if not isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be finite and positive")


def _require_non_negative_finite_float(value: float, label: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"{label} must be a number")
    if not isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def estimate_default_transfer_cost(
    bytes_moved: int,
    source_domain: MemoryDomainKind,
    target_domain: MemoryDomainKind,
) -> TransferCostEstimate:
    """Estimate transfer cost from a small deterministic prototype profile."""

    _require_transfer_bytes(bytes_moved, "bytes_moved")
    _require_enum(source_domain, MemoryDomainKind, "source_domain")
    _require_enum(target_domain, MemoryDomainKind, "target_domain")
    if source_domain == target_domain:
        raise ValueError("default transfer cost requires different domains")

    bandwidth_gb_s, base_latency_ns, energy_pj_per_byte = _DEFAULT_TRANSFER_COSTS.get(
        (source_domain, target_domain),
        _FALLBACK_TRANSFER_COST,
    )
    return TransferCostEstimate(
        bytes_moved=bytes_moved,
        bandwidth_gb_s=bandwidth_gb_s,
        base_latency_ns=base_latency_ns,
        energy_pj_per_byte=energy_pj_per_byte,
    )


_FALLBACK_TRANSFER_COST = (16.0, 20_000.0, 100.0)
_DEFAULT_TRANSFER_COSTS = {
    (MemoryDomainKind.ANALOG_WEIGHT_BANK, MemoryDomainKind.GPU_HBM): (64.0, 5_000.0, 20.0),
    (MemoryDomainKind.GPU_HBM, MemoryDomainKind.ANALOG_WEIGHT_BANK): (64.0, 5_000.0, 20.0),
    (MemoryDomainKind.GPU_HBM, MemoryDomainKind.DEVICE_SRAM): (1_000.0, 100.0, 2.0),
    (MemoryDomainKind.DEVICE_SRAM, MemoryDomainKind.GPU_HBM): (1_000.0, 100.0, 2.0),
    (MemoryDomainKind.HOST_RAM, MemoryDomainKind.GPU_HBM): (32.0, 10_000.0, 50.0),
    (MemoryDomainKind.GPU_HBM, MemoryDomainKind.HOST_RAM): (32.0, 10_000.0, 50.0),
}


__all__ = [
    "LayoutConversionCost",
    "RuntimeTransferEdge",
    "TransferCostEstimate",
    "estimate_default_transfer_cost",
]
