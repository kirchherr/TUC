"""Runtime data-movement plan objects."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import cast

from tuc.ir.memory import LayoutKind, MemoryDomainKind

MAX_RUNTIME_TRANSFER_BYTES = 2**63 - 1
MAX_TRANSFER_PROFILE_EDGES = 64
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
class TransferCostParameters:
    """Validated per-domain-pair transfer cost parameters."""

    bandwidth_gb_s: float
    base_latency_ns: float
    energy_pj_per_byte: float

    def __post_init__(self) -> None:
        _require_positive_finite_float(self.bandwidth_gb_s, "bandwidth_gb_s")
        _require_non_negative_finite_float(self.base_latency_ns, "base_latency_ns")
        _require_non_negative_finite_float(
            self.energy_pj_per_byte,
            "energy_pj_per_byte",
        )

    def estimate(self, bytes_moved: int) -> TransferCostEstimate:
        """Estimate transfer cost for a concrete byte count."""

        return TransferCostEstimate(
            bytes_moved=bytes_moved,
            bandwidth_gb_s=self.bandwidth_gb_s,
            base_latency_ns=self.base_latency_ns,
            energy_pj_per_byte=self.energy_pj_per_byte,
        )


@dataclass(frozen=True)
class TransferCostProfile:
    """Validated transfer-cost profile, suitable for backend manifest data."""

    name: str
    fallback: TransferCostParameters
    entries: Mapping[tuple[MemoryDomainKind, MemoryDomainKind], TransferCostParameters]

    def __post_init__(self) -> None:
        _require_name(self.name, "transfer_cost_profile.name")
        if not isinstance(self.fallback, TransferCostParameters):
            raise TypeError("transfer_cost_profile.fallback must be TransferCostParameters")
        if type(self.entries) is not dict:
            raise TypeError("transfer_cost_profile.entries must be a plain mapping")
        if len(self.entries) > MAX_TRANSFER_PROFILE_EDGES:
            raise ValueError("transfer cost profile exceeds edge limit")

        normalized: dict[tuple[MemoryDomainKind, MemoryDomainKind], TransferCostParameters] = {}
        for edge, parameters in self.entries.items():
            if not isinstance(edge, tuple) or len(edge) != 2:
                raise TypeError("transfer cost profile edge keys must be domain pairs")
            source_domain, target_domain = edge
            _require_enum(source_domain, MemoryDomainKind, "source_domain")
            _require_enum(target_domain, MemoryDomainKind, "target_domain")
            if source_domain == target_domain:
                raise ValueError("transfer cost profile edges must cross domains")
            if not isinstance(parameters, TransferCostParameters):
                raise TypeError("transfer cost profile values must be TransferCostParameters")
            normalized[(source_domain, target_domain)] = parameters
        object.__setattr__(self, "entries", normalized)

    def estimate(
        self,
        bytes_moved: int,
        source_domain: MemoryDomainKind,
        target_domain: MemoryDomainKind,
    ) -> TransferCostEstimate:
        """Estimate transfer cost for one domain crossing."""

        _require_transfer_bytes(bytes_moved, "bytes_moved")
        _require_enum(source_domain, MemoryDomainKind, "source_domain")
        _require_enum(target_domain, MemoryDomainKind, "target_domain")
        if source_domain == target_domain:
            raise ValueError("transfer cost requires different domains")
        parameters = self.entries.get((source_domain, target_domain), self.fallback)
        return parameters.estimate(bytes_moved)

    @classmethod
    def from_manifest(cls, manifest: object) -> TransferCostProfile:
        """Create a validated profile from untrusted declarative manifest data."""

        manifest_dict = _require_plain_mapping(manifest, "transfer cost manifest")
        name = _require_manifest_string(manifest_dict, "name")
        fallback = _parameters_from_manifest(
            _require_manifest_mapping(manifest_dict, "fallback")
        )
        edges = _require_plain_sequence(
            manifest_dict.get("edges", ()),
            "transfer cost manifest edges",
        )
        if len(edges) > MAX_TRANSFER_PROFILE_EDGES:
            raise ValueError("transfer cost manifest exceeds edge limit")

        entries: dict[tuple[MemoryDomainKind, MemoryDomainKind], TransferCostParameters] = {}
        for edge_value in edges:
            edge = _require_mapping(edge_value, "transfer cost edge")
            source_domain = _domain_from_manifest(edge, "source_domain")
            target_domain = _domain_from_manifest(edge, "target_domain")
            if (source_domain, target_domain) in entries:
                raise ValueError("transfer cost manifest contains duplicate domain pair")
            entries[(source_domain, target_domain)] = _parameters_from_manifest(edge)
        return cls(name=name, fallback=fallback, entries=entries)


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

    return DEFAULT_TRANSFER_COST_PROFILE.estimate(
        bytes_moved=bytes_moved,
        source_domain=source_domain,
        target_domain=target_domain,
    )


def _parameters_from_manifest(manifest: Mapping[str, object]) -> TransferCostParameters:
    return TransferCostParameters(
        bandwidth_gb_s=_require_manifest_number(manifest, "bandwidth_gb_s"),
        base_latency_ns=_require_manifest_number(manifest, "base_latency_ns"),
        energy_pj_per_byte=_require_manifest_number(manifest, "energy_pj_per_byte"),
    )


def _domain_from_manifest(
    manifest: Mapping[str, object],
    key: str,
) -> MemoryDomainKind:
    value = _require_manifest_string(manifest, key)
    try:
        return MemoryDomainKind(value)
    except ValueError as exc:
        raise ValueError(f"unsupported memory domain in transfer cost manifest: {value!r}") from exc


def _require_manifest_mapping(
    manifest: Mapping[str, object],
    key: str,
) -> dict[str, object]:
    value = manifest.get(key)
    return _require_mapping(value, f"transfer cost manifest {key}")


def _require_mapping(value: object, label: str) -> dict[str, object]:
    return _require_plain_mapping(value, label)


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


def _require_manifest_string(manifest: Mapping[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str) or not _PLAN_NAME_RE.fullmatch(value):
        raise ValueError(f"transfer cost manifest {key} must be a simple name")
    return value


def _require_manifest_number(manifest: Mapping[str, object], key: str) -> float:
    value = manifest.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise TypeError(f"transfer cost manifest {key} must be a number")
    return float(value)


DEFAULT_TRANSFER_COST_PROFILE = TransferCostProfile(
    name="prototype",
    fallback=TransferCostParameters(
        bandwidth_gb_s=16.0,
        base_latency_ns=20_000.0,
        energy_pj_per_byte=100.0,
    ),
    entries={
        (MemoryDomainKind.ANALOG_WEIGHT_BANK, MemoryDomainKind.GPU_HBM): (
            TransferCostParameters(64.0, 5_000.0, 20.0)
        ),
        (MemoryDomainKind.GPU_HBM, MemoryDomainKind.ANALOG_WEIGHT_BANK): (
            TransferCostParameters(64.0, 5_000.0, 20.0)
        ),
        (MemoryDomainKind.GPU_HBM, MemoryDomainKind.DEVICE_SRAM): (
            TransferCostParameters(1_000.0, 100.0, 2.0)
        ),
        (MemoryDomainKind.DEVICE_SRAM, MemoryDomainKind.GPU_HBM): (
            TransferCostParameters(1_000.0, 100.0, 2.0)
        ),
        (MemoryDomainKind.HOST_RAM, MemoryDomainKind.GPU_HBM): (
            TransferCostParameters(32.0, 10_000.0, 50.0)
        ),
        (MemoryDomainKind.GPU_HBM, MemoryDomainKind.HOST_RAM): (
            TransferCostParameters(32.0, 10_000.0, 50.0)
        ),
    },
)


__all__ = [
    "LayoutConversionCost",
    "RuntimeTransferEdge",
    "TransferCostParameters",
    "TransferCostEstimate",
    "TransferCostProfile",
    "DEFAULT_TRANSFER_COST_PROFILE",
    "estimate_default_transfer_cost",
]
