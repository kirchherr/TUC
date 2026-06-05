"""Explicit backend capability registry for TUC prototype planning."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from tuc.backends.base import BackendCapability
from tuc.ir.model import ComputeOperation, OperationKind
from tuc.manifests import load_backend_capability_manifest

MAX_REGISTERED_BACKENDS = 64
MAX_BACKEND_NAME_BYTES = 128

_BACKEND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class BackendRegistryError(ValueError):
    """Raised when backend capability registration would be ambiguous or unsafe."""


@dataclass(frozen=True)
class BackendRegistration:
    """Pure-data backend registration used for planning and diagnostics."""

    capability: BackendCapability
    source_label: str = "in-memory"

    @property
    def name(self) -> str:
        """Return the stable backend name."""

        return self.capability.name


class BackendRegistry:
    """Immutable registry of backend capabilities loaded through explicit inputs."""

    def __init__(self, registrations: Iterable[BackendRegistration] = ()) -> None:
        registration_tuple = tuple(registrations)
        _validate_registration_count(registration_tuple)

        by_name: dict[str, BackendRegistration] = {}
        for registration in registration_tuple:
            _validate_registration(registration)
            name = registration.name
            if name in by_name:
                raise BackendRegistryError(f"duplicate backend registration: {name}")
            by_name[name] = registration

        self._registrations: Mapping[str, BackendRegistration] = MappingProxyType(by_name)

    @classmethod
    def from_capabilities(cls, capabilities: Iterable[BackendCapability]) -> BackendRegistry:
        """Build a registry from trusted in-process capability objects."""

        return cls(BackendRegistration(capability) for capability in capabilities)

    @classmethod
    def from_manifest_paths(cls, paths: Iterable[str | Path]) -> BackendRegistry:
        """Load backend capability manifests from an explicit path list."""

        registrations: list[BackendRegistration] = []
        for path in paths:
            manifest_path = Path(path)
            capability = load_backend_capability_manifest(manifest_path)
            registrations.append(
                BackendRegistration(
                    capability=capability,
                    source_label=manifest_path.name,
                )
            )
        return cls(registrations)

    def names(self) -> tuple[str, ...]:
        """Return registered backend names in deterministic registration order."""

        return tuple(self._registrations)

    def registrations(self) -> tuple[BackendRegistration, ...]:
        """Return immutable backend registration records."""

        return tuple(self._registrations.values())

    def capabilities(self) -> tuple[BackendCapability, ...]:
        """Return capability objects suitable for compiler partitioning."""

        return tuple(registration.capability for registration in self._registrations.values())

    def capability(self, name: str) -> BackendCapability:
        """Return a registered capability by name."""

        try:
            return self._registrations[name].capability
        except KeyError as exc:
            raise BackendRegistryError(f"backend is not registered: {name}") from exc

    def supporting_operation_kind(
        self,
        operation_kind: OperationKind,
    ) -> tuple[BackendCapability, ...]:
        """Return capabilities that declare support for one operation family."""

        if not isinstance(operation_kind, OperationKind):
            raise TypeError("operation_kind must be OperationKind")
        return tuple(
            capability
            for capability in self.capabilities()
            if operation_kind in capability.supported_ops
        )

    def supporting_operation(self, operation: ComputeOperation) -> tuple[BackendCapability, ...]:
        """Return capabilities whose pure-data checks accept an operation."""

        if not isinstance(operation, ComputeOperation):
            raise TypeError("operation must be ComputeOperation")
        return tuple(
            capability
            for capability in self.capabilities()
            if capability.supports(operation)
        )


def _validate_registration_count(
    registrations: tuple[BackendRegistration, ...],
) -> None:
    if len(registrations) > MAX_REGISTERED_BACKENDS:
        raise BackendRegistryError("too many backend registrations")


def _validate_registration(registration: BackendRegistration) -> None:
    if not isinstance(registration, BackendRegistration):
        raise TypeError("backend registry entries must be BackendRegistration")
    _validate_backend_name(registration.capability.name)
    _validate_source_label(registration.source_label)


def _validate_backend_name(name: str) -> None:
    if not isinstance(name, str) or not _BACKEND_NAME_RE.fullmatch(name):
        raise BackendRegistryError("backend name must be a safe registry identifier")
    if len(name.encode("utf-8")) > MAX_BACKEND_NAME_BYTES:
        raise BackendRegistryError("backend name exceeds registry size limit")


def _validate_source_label(source_label: str) -> None:
    if not isinstance(source_label, str) or not source_label:
        raise BackendRegistryError("backend source label must be a non-empty string")
    if "/" in source_label or "\\" in source_label:
        raise BackendRegistryError("backend source label must not contain path separators")
    if len(source_label.encode("utf-8")) > MAX_BACKEND_NAME_BYTES:
        raise BackendRegistryError("backend source label exceeds registry size limit")


__all__ = [
    "BackendRegistration",
    "BackendRegistry",
    "BackendRegistryError",
    "MAX_BACKEND_NAME_BYTES",
    "MAX_REGISTERED_BACKENDS",
]
