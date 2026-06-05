"""Explicit backend capability registry for TUC prototype planning."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from types import MappingProxyType

from tuc.backends.base import BackendCapability
from tuc.ir.memory import LayoutKind
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


@dataclass(frozen=True)
class BackendSupportDiagnostic:
    """Explains whether one backend capability accepts one operation."""

    backend_name: str
    operation_name: str
    operation_kind: OperationKind
    supported: bool
    reason: str
    detail: str = ""


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
            self.capability(diagnostic.backend_name)
            for diagnostic in self.diagnose_operation_support(operation)
            if diagnostic.supported
        )

    def diagnose_operation_support(
        self,
        operation: ComputeOperation,
    ) -> tuple[BackendSupportDiagnostic, ...]:
        """Explain each registered backend's pure-data support decision."""

        if not isinstance(operation, ComputeOperation):
            raise TypeError("operation must be ComputeOperation")
        return tuple(
            _diagnose_backend_support(registration.capability, operation)
            for registration in self._registrations.values()
        )


def _diagnose_backend_support(
    capability: BackendCapability,
    operation: ComputeOperation,
) -> BackendSupportDiagnostic:
    if operation.kind not in capability.supported_ops:
        return _support_diagnostic(
            capability,
            operation,
            supported=False,
            reason="unsupported_operation_kind",
            detail=f"{operation.kind.value} not declared in supported_ops",
        )

    layout, layout_error = _operation_layout_for_diagnostics(operation)
    if layout_error is not None:
        return _support_diagnostic(
            capability,
            operation,
            supported=False,
            reason="invalid_layout_attribute",
            detail=layout_error,
        )
    if layout not in capability.supported_layouts:
        supported_layouts = ",".join(
            sorted(layout.value for layout in capability.supported_layouts)
        )
        return _support_diagnostic(
            capability,
            operation,
            supported=False,
            reason="unsupported_layout",
            detail=f"{layout.value} not in supported_layouts={supported_layouts}",
        )

    if capability.max_error_budget is not None:
        requested_budget = operation.attributes.get("max_error_budget")
        if requested_budget is not None:
            budget, budget_error = _error_budget_for_diagnostics(requested_budget)
            if budget_error is not None:
                return _support_diagnostic(
                    capability,
                    operation,
                    supported=False,
                    reason="invalid_error_budget_attribute",
                    detail=budget_error,
                )
            if budget is not None and budget > capability.max_error_budget:
                return _support_diagnostic(
                    capability,
                    operation,
                    supported=False,
                    reason="error_budget_exceeds_backend_limit",
                    detail=(
                        f"requested={budget:g} backend_max="
                        f"{capability.max_error_budget:g}"
                    ),
                )

    return _support_diagnostic(
        capability,
        operation,
        supported=True,
        reason="accepted",
        detail="capability accepts operation kind, layout, and error budget",
    )


def _support_diagnostic(
    capability: BackendCapability,
    operation: ComputeOperation,
    *,
    supported: bool,
    reason: str,
    detail: str,
) -> BackendSupportDiagnostic:
    return BackendSupportDiagnostic(
        backend_name=capability.name,
        operation_name=operation.name,
        operation_kind=operation.kind,
        supported=supported,
        reason=reason,
        detail=detail,
    )


def _operation_layout_for_diagnostics(
    operation: ComputeOperation,
) -> tuple[LayoutKind, str | None]:
    value = operation.attributes.get("tuc.layout")
    if value is None:
        return LayoutKind.ROW_MAJOR, None
    if isinstance(value, LayoutKind):
        return value, None
    if isinstance(value, str):
        try:
            return LayoutKind(value), None
        except ValueError:
            return LayoutKind.ROW_MAJOR, f"unsupported operation layout: {value!r}"
    return LayoutKind.ROW_MAJOR, "operation layout must be a LayoutKind or string"


def _error_budget_for_diagnostics(value: object) -> tuple[float | None, str | None]:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return None, "max_error_budget attribute must be a number"
    budget = float(value)
    if not isfinite(budget) or budget < 0:
        return None, "max_error_budget attribute must be finite and non-negative"
    return budget, None


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
    "BackendSupportDiagnostic",
    "MAX_BACKEND_NAME_BYTES",
    "MAX_REGISTERED_BACKENDS",
]
