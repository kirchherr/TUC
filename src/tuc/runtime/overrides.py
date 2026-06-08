"""Declarative runtime placement overrides."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from tuc.backends.base import BackendCapability
from tuc.ir.model import ComputeGraph

RUNTIME_OVERRIDE_SCHEMA_VERSION = "tuc.runtime_overrides.v0"
MAX_RUNTIME_OVERRIDE_RULES = 64
MAX_RUNTIME_OVERRIDE_NAME_BYTES = 128

_OVERRIDE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class RuntimeOverrideError(ValueError):
    """Raised when manual runtime placement override data is invalid."""


class RuntimeOverrideAction(StrEnum):
    """Supported manual override actions."""

    REQUIRE_BACKEND = "require_backend"
    PREFER_BACKEND = "prefer_backend"
    DENY_BACKEND = "deny_backend"


@dataclass(frozen=True)
class RuntimeOverrideRule:
    """One operation-scoped backend placement override rule."""

    operation_name: str
    action: RuntimeOverrideAction
    backend_name: str

    def __post_init__(self) -> None:
        _require_safe_name(self.operation_name, "runtime override operation_name")
        _require_safe_name(self.backend_name, "runtime override backend_name")
        if not isinstance(self.action, RuntimeOverrideAction):
            raise TypeError("runtime override action must be RuntimeOverrideAction")


@dataclass(frozen=True)
class RuntimeOverrideEffect:
    """Resolved override effect for one operation."""

    operation_name: str
    required_backend: str | None = None
    preferred_backend: str | None = None
    denied_backends: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_safe_name(self.operation_name, "runtime override operation_name")
        if self.required_backend is not None:
            _require_safe_name(self.required_backend, "runtime override required_backend")
        if self.preferred_backend is not None:
            _require_safe_name(self.preferred_backend, "runtime override preferred_backend")
        denied = tuple(self.denied_backends)
        for backend_name in denied:
            _require_safe_name(backend_name, "runtime override denied_backend")
        if len(set(denied)) != len(denied):
            raise RuntimeOverrideError("runtime override contains duplicate deny rules")
        if self.required_backend is not None and self.preferred_backend is not None:
            raise RuntimeOverrideError(
                "runtime override contains both require_backend and prefer_backend"
            )
        if self.required_backend is not None and self.required_backend in denied:
            raise RuntimeOverrideError(
                "runtime override contains contradictory require_backend and deny_backend"
            )
        if self.preferred_backend is not None and self.preferred_backend in denied:
            raise RuntimeOverrideError(
                "runtime override contains contradictory prefer_backend and deny_backend"
            )
        object.__setattr__(self, "denied_backends", denied)

    @property
    def active(self) -> bool:
        """Return whether this effect changes placement behavior."""

        return (
            self.required_backend is not None
            or self.preferred_backend is not None
            or bool(self.denied_backends)
        )


@dataclass(frozen=True)
class RuntimeOverrideSet:
    """Validated collection of declarative runtime placement overrides."""

    rules: tuple[RuntimeOverrideRule, ...] = ()

    def __post_init__(self) -> None:
        rules = tuple(self.rules)
        if len(rules) > MAX_RUNTIME_OVERRIDE_RULES:
            raise RuntimeOverrideError("runtime override rule count exceeds limit")
        for rule in rules:
            if not isinstance(rule, RuntimeOverrideRule):
                raise TypeError("runtime override rules must be RuntimeOverrideRule")
        _validate_rule_consistency(rules)
        object.__setattr__(self, "rules", rules)

    @classmethod
    def from_manifest(cls, manifest: object) -> RuntimeOverrideSet:
        """Create overrides from bounded, schema-versioned declarative data."""

        manifest_dict = _require_plain_mapping(manifest, "runtime override manifest")
        _reject_unknown_fields(
            manifest_dict,
            {"schema_version", "rules"},
            "runtime override manifest",
        )
        schema_version = _require_manifest_string(manifest_dict, "schema_version")
        if schema_version != RUNTIME_OVERRIDE_SCHEMA_VERSION:
            raise RuntimeOverrideError(
                f"unsupported runtime override schema_version: {schema_version!r}"
            )

        raw_rules = _require_plain_sequence(
            manifest_dict.get("rules", ()),
            "runtime override rules",
        )
        if len(raw_rules) > MAX_RUNTIME_OVERRIDE_RULES:
            raise RuntimeOverrideError("runtime override rule count exceeds limit")

        rules = tuple(_rule_from_manifest(raw_rule) for raw_rule in raw_rules)
        return cls(rules=rules)

    def effect_for_operation(self, operation_name: str) -> RuntimeOverrideEffect | None:
        """Return the resolved effect for an operation, if any."""

        _require_safe_name(operation_name, "runtime override operation_name")
        operation_rules = tuple(
            rule for rule in self.rules if rule.operation_name == operation_name
        )
        if not operation_rules:
            return None

        required = tuple(
            rule.backend_name
            for rule in operation_rules
            if rule.action is RuntimeOverrideAction.REQUIRE_BACKEND
        )
        preferred = tuple(
            rule.backend_name
            for rule in operation_rules
            if rule.action is RuntimeOverrideAction.PREFER_BACKEND
        )
        denied = tuple(
            sorted(
                rule.backend_name
                for rule in operation_rules
                if rule.action is RuntimeOverrideAction.DENY_BACKEND
            )
        )
        return RuntimeOverrideEffect(
            operation_name=operation_name,
            required_backend=required[0] if required else None,
            preferred_backend=preferred[0] if preferred else None,
            denied_backends=denied,
        )

    def active_effects_for_graph(self, graph: ComputeGraph) -> tuple[RuntimeOverrideEffect, ...]:
        """Return active effects in graph operation order."""

        return tuple(
            effect
            for operation in graph.operations
            if (effect := self.effect_for_operation(operation.name)) is not None
            and effect.active
        )

    def validate_for_graph(
        self,
        graph: ComputeGraph,
        backend_capabilities: Iterable[BackendCapability],
    ) -> None:
        """Validate overrides against graph operations and accepted backend candidates."""

        if not isinstance(graph, ComputeGraph):
            raise TypeError("runtime override validation requires a ComputeGraph")
        capabilities = tuple(backend_capabilities)
        backend_names = {capability.name for capability in capabilities}
        operation_names = {operation.name for operation in graph.operations}

        for rule in self.rules:
            if rule.operation_name not in operation_names:
                raise RuntimeOverrideError(
                    f"runtime override references unknown operation: {rule.operation_name}"
                )
            if rule.backend_name not in backend_names:
                raise RuntimeOverrideError(
                    f"runtime override references unknown backend: {rule.backend_name}"
                )

        accepted_by_operation = {
            operation.name: frozenset(
                capability.name
                for capability in capabilities
                if capability.supports(operation)
            )
            for operation in graph.operations
        }

        for rule in self.rules:
            accepted = accepted_by_operation[rule.operation_name]
            if rule.backend_name not in accepted:
                raise RuntimeOverrideError(
                    "runtime override backend is not an accepted candidate: "
                    f"{rule.operation_name}->{rule.backend_name}"
                )

        for operation in graph.operations:
            effect = self.effect_for_operation(operation.name)
            if effect is None:
                continue
            self.apply_to_candidates(
                operation_name=operation.name,
                candidates=tuple(
                    capability
                    for capability in capabilities
                    if capability.name in accepted_by_operation[operation.name]
                ),
            )

    def apply_to_candidates(
        self,
        *,
        operation_name: str,
        candidates: tuple[BackendCapability, ...],
    ) -> tuple[BackendCapability, ...]:
        """Return candidates after applying a validated override effect."""

        effect = self.effect_for_operation(operation_name)
        if effect is None:
            return candidates

        by_name = {candidate.name: candidate for candidate in candidates}
        remaining = tuple(
            candidate for candidate in candidates if candidate.name not in effect.denied_backends
        )
        if not remaining:
            raise RuntimeOverrideError(
                f"runtime override removes every accepted backend candidate: {operation_name}"
            )

        if effect.required_backend is not None:
            required = by_name.get(effect.required_backend)
            if required is None or required.name in effect.denied_backends:
                raise RuntimeOverrideError(
                    "runtime override required backend is not an accepted candidate: "
                    f"{operation_name}->{effect.required_backend}"
                )
            return (required,)

        if effect.preferred_backend is not None:
            preferred = by_name.get(effect.preferred_backend)
            if preferred is None or preferred.name in effect.denied_backends:
                raise RuntimeOverrideError(
                    "runtime override preferred backend is not an accepted candidate: "
                    f"{operation_name}->{effect.preferred_backend}"
                )
            return (preferred,)

        return remaining


def _rule_from_manifest(raw_rule: object) -> RuntimeOverrideRule:
    rule = _require_plain_mapping(raw_rule, "runtime override rule")
    _reject_unknown_fields(
        rule,
        {"operation_name", "action", "backend_name"},
        "runtime override rule",
    )
    action_value = _require_manifest_string(rule, "action")
    try:
        action = RuntimeOverrideAction(action_value)
    except ValueError as exc:
        raise RuntimeOverrideError(
            f"unsupported runtime override action: {action_value!r}"
        ) from exc
    return RuntimeOverrideRule(
        operation_name=_require_manifest_string(rule, "operation_name"),
        action=action,
        backend_name=_require_manifest_string(rule, "backend_name"),
    )


def _validate_rule_consistency(rules: tuple[RuntimeOverrideRule, ...]) -> None:
    seen_rule_keys: set[tuple[str, RuntimeOverrideAction, str]] = set()
    required_by_operation: dict[str, str] = {}
    preferred_by_operation: dict[str, str] = {}
    denied_by_operation: dict[str, set[str]] = {}

    for rule in rules:
        rule_key = (rule.operation_name, rule.action, rule.backend_name)
        if rule_key in seen_rule_keys:
            raise RuntimeOverrideError("runtime override contains duplicate rules")
        seen_rule_keys.add(rule_key)

        if rule.action is RuntimeOverrideAction.REQUIRE_BACKEND:
            previous = required_by_operation.get(rule.operation_name)
            if previous is not None and previous != rule.backend_name:
                raise RuntimeOverrideError(
                    "runtime override contains multiple required backends for one operation"
                )
            required_by_operation[rule.operation_name] = rule.backend_name

        if rule.action is RuntimeOverrideAction.PREFER_BACKEND:
            previous = preferred_by_operation.get(rule.operation_name)
            if previous is not None and previous != rule.backend_name:
                raise RuntimeOverrideError(
                    "runtime override contains multiple preferred backends for one operation"
                )
            preferred_by_operation[rule.operation_name] = rule.backend_name

        if rule.action is RuntimeOverrideAction.DENY_BACKEND:
            denied_by_operation.setdefault(rule.operation_name, set()).add(rule.backend_name)

    for operation_name, required_backend in required_by_operation.items():
        denied = denied_by_operation.get(operation_name, set())
        if operation_name in preferred_by_operation:
            raise RuntimeOverrideError(
                "runtime override contains both require_backend and prefer_backend"
            )
        if required_backend in denied:
            raise RuntimeOverrideError(
                "runtime override contains contradictory require_backend and deny_backend"
            )

    for operation_name, preferred_backend in preferred_by_operation.items():
        denied = denied_by_operation.get(operation_name, set())
        if preferred_backend in denied:
            raise RuntimeOverrideError(
                "runtime override contains contradictory prefer_backend and deny_backend"
            )


def _reject_unknown_fields(
    value: Mapping[str, object],
    allowed_fields: set[str],
    label: str,
) -> None:
    unknown_fields = tuple(sorted(set(value) - allowed_fields))
    if unknown_fields:
        raise RuntimeOverrideError(
            f"{label} contains unknown fields: {','.join(unknown_fields)}"
        )


def _require_manifest_string(manifest: Mapping[str, object], key: str) -> str:
    value = manifest.get(key)
    if not isinstance(value, str):
        raise TypeError(f"runtime override manifest {key} must be a string")
    _require_safe_name(value, f"runtime override manifest {key}")
    return value


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


def _require_safe_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not _OVERRIDE_NAME_RE.fullmatch(value):
        raise RuntimeOverrideError(f"{label} must be a safe override identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_OVERRIDE_NAME_BYTES:
        raise RuntimeOverrideError(f"{label} exceeds override size limit")


__all__ = [
    "MAX_RUNTIME_OVERRIDE_NAME_BYTES",
    "MAX_RUNTIME_OVERRIDE_RULES",
    "RUNTIME_OVERRIDE_SCHEMA_VERSION",
    "RuntimeOverrideAction",
    "RuntimeOverrideEffect",
    "RuntimeOverrideError",
    "RuntimeOverrideRule",
    "RuntimeOverrideSet",
]
