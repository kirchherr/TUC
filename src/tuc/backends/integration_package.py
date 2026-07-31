"""Portable data-only backend integration packages and conformance reports."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import cast

from tuc.backends.base import BackendCapability
from tuc.backends.registry import BackendRegistry
from tuc.compiler import compile_graph
from tuc.ir.memory import LayoutKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.manifests import load_json_manifest, parse_backend_capability_manifest

BACKEND_INTEGRATION_PACKAGE_SCHEMA_VERSION = "tuc.backend_integration_package.v0"
BACKEND_INTEGRATION_PACKAGE_REPORT_SCHEMA_VERSION = (
    "tuc.backend_integration_package_report.v0"
)
BACKEND_INTEGRATION_PACKAGE_CONTRACT = "backend_integration.data_only.v0"
BACKEND_INTEGRATION_PACKAGE_POLICY = "capability_and_planning_conformance_only"
BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY = "no_import_or_plugin_discovery"
BACKEND_INTEGRATION_PACKAGE_STATUS_PASS = "PASS"
BACKEND_INTEGRATION_PACKAGE_STATUS_FAIL = "FAIL"
BACKEND_INTEGRATION_PACKAGE_EXPECTED_REASONS = frozenset(
    {
        "accepted",
        "unsupported_layout",
        "unsupported_operation_kind",
    }
)
BACKEND_INTEGRATION_PACKAGE_BLOCKED_EXECUTION_SURFACES = (
    "backend_code_execution",
    "plugin_discovery",
    "dynamic_import",
    "dynamic_library_loading",
    "subprocess_execution",
    "network_access",
    "device_access",
    "generated_artifact_execution",
    "runtime_execution",
)
MAX_BACKEND_INTEGRATION_PACKAGE_BYTES = 64 * 1024
MAX_BACKEND_INTEGRATION_PACKAGE_CASES = 32
MAX_BACKEND_INTEGRATION_PACKAGE_FIELD_BYTES = 256
MAX_BACKEND_INTEGRATION_PACKAGE_REPORT_BYTES = 64 * 1024
MAX_BACKEND_INTEGRATION_PACKAGE_DEPTH = 8
MAX_BACKEND_INTEGRATION_PACKAGE_OBJECT_KEYS = 64
MAX_BACKEND_INTEGRATION_PACKAGE_LIST_ITEMS = 128

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_PACKAGE_KEYS = frozenset(
    {
        "backend_code_included",
        "capability_manifest",
        "conformance_cases",
        "execution_permission",
        "import_policy",
        "interface_contract",
        "package_id",
        "package_policy",
        "package_version",
        "schema_version",
    }
)
_CASE_KEYS = frozenset(
    {
        "case_id",
        "expected_reason",
        "expected_supported",
        "layout",
        "operation_kind",
    }
)


class BackendIntegrationPackageError(ValueError):
    """Raised when a backend integration package violates the v0 boundary."""


@dataclass(frozen=True)
class BackendIntegrationCase:
    """One pure-data support expectation supplied by a backend author."""

    case_id: str
    operation_kind: OperationKind
    layout: LayoutKind
    expected_supported: bool
    expected_reason: str

    def __post_init__(self) -> None:
        _validate_identifier(self.case_id, "case_id")
        if not isinstance(self.operation_kind, OperationKind):
            raise TypeError("backend integration operation_kind must be OperationKind")
        if not isinstance(self.layout, LayoutKind):
            raise TypeError("backend integration layout must be LayoutKind")
        if type(self.expected_supported) is not bool:
            raise TypeError("backend integration expected_supported must be bool")
        if self.expected_reason not in BACKEND_INTEGRATION_PACKAGE_EXPECTED_REASONS:
            raise BackendIntegrationPackageError(
                "backend integration expected_reason is not supported"
            )
        if self.expected_supported != (self.expected_reason == "accepted"):
            raise BackendIntegrationPackageError(
                "backend integration support expectation and reason disagree"
            )


@dataclass(frozen=True)
class BackendIntegrationPackage:
    """Validated portable backend package containing no executable code."""

    package_id: str
    package_version: str
    capability: BackendCapability
    conformance_cases: tuple[BackendIntegrationCase, ...]
    package_digest: str
    capability_manifest_digest: str
    interface_contract: str = BACKEND_INTEGRATION_PACKAGE_CONTRACT
    package_policy: str = BACKEND_INTEGRATION_PACKAGE_POLICY
    import_policy: str = BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY
    backend_code_included: bool = False
    execution_permission: bool = False

    def __post_init__(self) -> None:
        _validate_identifier(self.package_id, "package_id")
        _validate_identifier(self.package_version, "package_version")
        if not isinstance(self.capability, BackendCapability):
            raise TypeError("backend integration package requires capability")
        _validate_cases(self.conformance_cases)
        _validate_digest(self.package_digest, "package_digest")
        _validate_digest(self.capability_manifest_digest, "capability_manifest_digest")
        if self.interface_contract != BACKEND_INTEGRATION_PACKAGE_CONTRACT:
            raise BackendIntegrationPackageError(
                "backend integration interface contract mismatch"
            )
        if self.package_policy != BACKEND_INTEGRATION_PACKAGE_POLICY:
            raise BackendIntegrationPackageError("backend integration package policy mismatch")
        if self.import_policy != BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY:
            raise BackendIntegrationPackageError("backend integration import policy mismatch")
        if type(self.backend_code_included) is not bool:
            raise TypeError("backend integration backend_code_included must be bool")
        if self.backend_code_included:
            raise BackendIntegrationPackageError("backend code is not allowed in package")
        if type(self.execution_permission) is not bool:
            raise TypeError("backend integration execution_permission must be bool")
        if self.execution_permission:
            raise BackendIntegrationPackageError(
                "backend integration execution permission is blocked"
            )


@dataclass(frozen=True)
class BackendIntegrationCaseResult:
    """Observed pure-data capability decision for one package case."""

    case_id: str
    operation_kind: OperationKind
    layout: LayoutKind
    expected_supported: bool
    observed_supported: bool
    expected_reason: str
    observed_reason: str
    matched: bool


@dataclass(frozen=True)
class BackendIntegrationPlanningProbe:
    """Compiler assignment produced from one accepted package case."""

    graph_name: str
    operation_name: str
    operation_kind: OperationKind
    assigned_backend: str
    assignment_matched: bool


@dataclass(frozen=True)
class BackendIntegrationPackageReport:
    """Reviewable result of data-only package conformance and planning."""

    package: BackendIntegrationPackage
    case_results: tuple[BackendIntegrationCaseResult, ...]
    planning_probe: BackendIntegrationPlanningProbe
    issues: tuple[str, ...]

    @property
    def conformance_passed(self) -> bool:
        return not self.issues and all(result.matched for result in self.case_results)

    @property
    def integration_status(self) -> str:
        if self.conformance_passed:
            return BACKEND_INTEGRATION_PACKAGE_STATUS_PASS
        return BACKEND_INTEGRATION_PACKAGE_STATUS_FAIL


def load_backend_integration_package(path: str | Path) -> BackendIntegrationPackage:
    """Load one explicit bounded package without discovery, imports, or execution."""

    payload = load_json_manifest(path, max_bytes=MAX_BACKEND_INTEGRATION_PACKAGE_BYTES)
    return parse_backend_integration_package(payload)


def parse_backend_integration_package(
    payload: Mapping[str, object],
) -> BackendIntegrationPackage:
    """Validate already-decoded package data and return an immutable contract."""

    _validate_plain_json(payload, depth=0)
    if type(payload) is not dict:
        raise BackendIntegrationPackageError("backend integration package must be plain object")
    normalized = cast(dict[str, object], payload)
    _require_exact_keys(normalized, _PACKAGE_KEYS, "package")
    _require_const(
        normalized,
        "schema_version",
        BACKEND_INTEGRATION_PACKAGE_SCHEMA_VERSION,
    )
    _require_const(
        normalized,
        "interface_contract",
        BACKEND_INTEGRATION_PACKAGE_CONTRACT,
    )
    _require_const(normalized, "package_policy", BACKEND_INTEGRATION_PACKAGE_POLICY)
    _require_const(
        normalized,
        "import_policy",
        BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY,
    )
    backend_code_included = _require_bool(normalized, "backend_code_included")
    execution_permission = _require_bool(normalized, "execution_permission")
    if backend_code_included:
        raise BackendIntegrationPackageError("backend code is not allowed in package")
    if execution_permission:
        raise BackendIntegrationPackageError(
            "backend integration execution permission is blocked"
        )
    capability_manifest = _require_plain_object(normalized, "capability_manifest")
    conformance_payloads = _require_plain_list(normalized, "conformance_cases")
    if not conformance_payloads:
        raise BackendIntegrationPackageError("backend integration cases must not be empty")
    if len(conformance_payloads) > MAX_BACKEND_INTEGRATION_PACKAGE_CASES:
        raise BackendIntegrationPackageError("backend integration case count exceeds limit")
    cases = tuple(_parse_case(item) for item in conformance_payloads)
    capability = parse_backend_capability_manifest(capability_manifest)
    return BackendIntegrationPackage(
        package_id=_require_identifier(normalized, "package_id"),
        package_version=_require_identifier(normalized, "package_version"),
        capability=capability,
        conformance_cases=cases,
        package_digest=_digest_json(normalized),
        capability_manifest_digest=_digest_json(capability_manifest),
        backend_code_included=backend_code_included,
        execution_permission=execution_permission,
    )


def evaluate_backend_integration_package(
    package: BackendIntegrationPackage,
) -> BackendIntegrationPackageReport:
    """Evaluate capability conformance and compiler assignment without backend code."""

    if not isinstance(package, BackendIntegrationPackage):
        raise TypeError("backend integration evaluation requires package")
    registry = BackendRegistry.from_capabilities((package.capability,))
    results: list[BackendIntegrationCaseResult] = []
    issues: list[str] = []
    for case in package.conformance_cases:
        operation = _build_operation(case)
        diagnostic = registry.diagnose_operation_support(operation)[0]
        matched = (
            diagnostic.supported == case.expected_supported
            and diagnostic.reason == case.expected_reason
        )
        results.append(
            BackendIntegrationCaseResult(
                case_id=case.case_id,
                operation_kind=case.operation_kind,
                layout=case.layout,
                expected_supported=case.expected_supported,
                observed_supported=diagnostic.supported,
                expected_reason=case.expected_reason,
                observed_reason=diagnostic.reason,
                matched=matched,
            )
        )
        if not matched:
            issues.append(f"case_mismatch:{case.case_id}")

    accepted_case = next(case for case in package.conformance_cases if case.expected_supported)
    accepted_operation = _build_operation(accepted_case)
    graph = ComputeGraph(
        name="backend_integration_package_probe",
        operations=(accepted_operation,),
    )
    compiled = compile_graph(graph, registry.capabilities())
    assigned_backend = compiled.partition_plan.backend_for(accepted_operation.name)
    assignment_matched = assigned_backend == package.capability.name
    if not assignment_matched:
        issues.append("planning_assignment_mismatch")
    planning_probe = BackendIntegrationPlanningProbe(
        graph_name=graph.name,
        operation_name=accepted_operation.name,
        operation_kind=accepted_operation.kind,
        assigned_backend=assigned_backend,
        assignment_matched=assignment_matched,
    )
    return BackendIntegrationPackageReport(
        package=package,
        case_results=tuple(results),
        planning_probe=planning_probe,
        issues=tuple(issues),
    )


def assert_backend_integration_package(report: BackendIntegrationPackageReport) -> None:
    """Fail closed unless package conformance and planning both pass."""

    if not isinstance(report, BackendIntegrationPackageReport):
        raise TypeError("backend integration assertion requires report")
    if not report.conformance_passed:
        detail = ",".join(report.issues) or "unknown_failure"
        raise BackendIntegrationPackageError(
            f"backend integration package conformance failed: {detail}"
        )


def backend_integration_package_report_to_dict(
    report: BackendIntegrationPackageReport,
) -> dict[str, object]:
    """Return deterministic public data for one integration package report."""

    if not isinstance(report, BackendIntegrationPackageReport):
        raise TypeError("backend integration serialization requires report")
    package = report.package
    capability = package.capability
    return {
        "artifact_execution": False,
        "backend_code_executed": False,
        "backend_code_included": package.backend_code_included,
        "backend_name": capability.name,
        "blocked_execution_surfaces": list(
            BACKEND_INTEGRATION_PACKAGE_BLOCKED_EXECUTION_SURFACES
        ),
        "capability_manifest_digest": package.capability_manifest_digest,
        "case_count": len(report.case_results),
        "case_results": [
            {
                "case_id": result.case_id,
                "expected_reason": result.expected_reason,
                "expected_supported": result.expected_supported,
                "layout": result.layout.value,
                "matched": result.matched,
                "observed_reason": result.observed_reason,
                "observed_supported": result.observed_supported,
                "operation_kind": result.operation_kind.value,
            }
            for result in report.case_results
        ],
        "conformance_passed": report.conformance_passed,
        "declared_operation_families": sorted(
            operation.value for operation in capability.supported_ops
        ),
        "device_access": False,
        "execution_permission": package.execution_permission,
        "import_policy": package.import_policy,
        "integration_contract": package.interface_contract,
        "integration_status": report.integration_status,
        "issues": list(report.issues),
        "memory_domain": capability.memory_domain.value,
        "network_access": False,
        "package_digest": package.package_digest,
        "package_id": package.package_id,
        "package_policy": package.package_policy,
        "package_version": package.package_version,
        "planning_probe": {
            "assigned_backend": report.planning_probe.assigned_backend,
            "assignment_matched": report.planning_probe.assignment_matched,
            "graph_name": report.planning_probe.graph_name,
            "operation_kind": report.planning_probe.operation_kind.value,
            "operation_name": report.planning_probe.operation_name,
        },
        "plugin_discovery": False,
        "produced_layouts": sorted(layout.value for layout in capability.produced_layouts),
        "runtime_execution": False,
        "schema_version": BACKEND_INTEGRATION_PACKAGE_REPORT_SCHEMA_VERSION,
        "subprocess_execution": False,
        "supported_layouts": sorted(layout.value for layout in capability.supported_layouts),
    }


def dump_backend_integration_package_report(
    report: BackendIntegrationPackageReport,
) -> str:
    """Render bounded deterministic backend integration package evidence."""

    text = json.dumps(
        backend_integration_package_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_INTEGRATION_PACKAGE_REPORT_BYTES:
        raise BackendIntegrationPackageError("backend integration report exceeds limit")
    return f"{text}\n"


def _parse_case(value: object) -> BackendIntegrationCase:
    if type(value) is not dict:
        raise BackendIntegrationPackageError("backend integration case must be plain object")
    payload = cast(dict[str, object], value)
    _require_exact_keys(payload, _CASE_KEYS, "case")
    try:
        operation_kind = OperationKind(_require_identifier(payload, "operation_kind"))
    except ValueError as exc:
        raise BackendIntegrationPackageError(
            "backend integration case operation_kind is unsupported"
        ) from exc
    try:
        layout = LayoutKind(_require_identifier(payload, "layout"))
    except ValueError as exc:
        raise BackendIntegrationPackageError(
            "backend integration case layout is unsupported"
        ) from exc
    return BackendIntegrationCase(
        case_id=_require_identifier(payload, "case_id"),
        operation_kind=operation_kind,
        layout=layout,
        expected_supported=_require_bool(payload, "expected_supported"),
        expected_reason=_require_identifier(payload, "expected_reason"),
    )


def _build_operation(case: BackendIntegrationCase) -> ComputeOperation:
    output = TensorRef(f"{case.case_id}_output", (4, 4))
    inputs: tuple[TensorRef, ...]
    if case.operation_kind is OperationKind.MATMUL:
        inputs = (
            TensorRef(f"{case.case_id}_lhs", (4, 4)),
            TensorRef(f"{case.case_id}_rhs", (4, 4)),
        )
    else:
        inputs = (TensorRef(f"{case.case_id}_input", (4, 4)),)
    return ComputeOperation(
        name=case.case_id,
        kind=case.operation_kind,
        inputs=inputs,
        outputs=(output,),
        attributes={"tuc.layout": case.layout.value},
    )


def _validate_cases(cases: tuple[BackendIntegrationCase, ...]) -> None:
    if type(cases) is not tuple:
        raise TypeError("backend integration cases must be tuple")
    if not cases:
        raise BackendIntegrationPackageError("backend integration cases must not be empty")
    if len(cases) > MAX_BACKEND_INTEGRATION_PACKAGE_CASES:
        raise BackendIntegrationPackageError("backend integration case count exceeds limit")
    case_ids: list[str] = []
    for case in cases:
        if not isinstance(case, BackendIntegrationCase):
            raise TypeError("backend integration cases must be case objects")
        case_ids.append(case.case_id)
    if len(case_ids) != len(set(case_ids)):
        raise BackendIntegrationPackageError("backend integration case ids must be unique")
    if not any(case.expected_supported for case in cases):
        raise BackendIntegrationPackageError("backend integration requires accepted case")
    if not any(not case.expected_supported for case in cases):
        raise BackendIntegrationPackageError("backend integration requires rejected case")


def _validate_plain_json(value: object, *, depth: int) -> None:
    if depth > MAX_BACKEND_INTEGRATION_PACKAGE_DEPTH:
        raise BackendIntegrationPackageError("backend integration package exceeds depth limit")
    if value is None or type(value) is bool:
        return
    if type(value) is str:
        if len(value.encode("utf-8")) > MAX_BACKEND_INTEGRATION_PACKAGE_FIELD_BYTES:
            raise BackendIntegrationPackageError("backend integration string exceeds limit")
        return
    if type(value) is int:
        return
    if type(value) is float:
        if not isfinite(value):
            raise BackendIntegrationPackageError("backend integration number must be finite")
        return
    if type(value) is list:
        items = cast(list[object], value)
        if len(items) > MAX_BACKEND_INTEGRATION_PACKAGE_LIST_ITEMS:
            raise BackendIntegrationPackageError("backend integration list exceeds limit")
        for item in items:
            _validate_plain_json(item, depth=depth + 1)
        return
    if type(value) is dict:
        mapping = cast(dict[str, object], value)
        if len(mapping) > MAX_BACKEND_INTEGRATION_PACKAGE_OBJECT_KEYS:
            raise BackendIntegrationPackageError("backend integration object exceeds limit")
        for key, item in mapping.items():
            if not isinstance(key, str):
                raise BackendIntegrationPackageError("backend integration keys must be strings")
            _validate_plain_json(key, depth=depth + 1)
            _validate_plain_json(item, depth=depth + 1)
        return
    raise BackendIntegrationPackageError(
        "backend integration package contains unsupported value type"
    )


def _require_exact_keys(
    payload: Mapping[str, object],
    expected: frozenset[str],
    label: str,
) -> None:
    if set(payload) != expected:
        raise BackendIntegrationPackageError(f"backend integration {label} keys changed")


def _require_const(payload: Mapping[str, object], key: str, expected: str) -> None:
    if payload.get(key) != expected:
        raise BackendIntegrationPackageError(f"backend integration {key} mismatch")


def _require_identifier(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise BackendIntegrationPackageError(f"backend integration {key} must be string")
    _validate_identifier(value, key)
    return value


def _require_bool(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if type(value) is not bool:
        raise BackendIntegrationPackageError(f"backend integration {key} must be bool")
    return value


def _require_plain_object(
    payload: Mapping[str, object], key: str
) -> dict[str, object]:
    value = payload.get(key)
    if type(value) is not dict:
        raise BackendIntegrationPackageError(f"backend integration {key} must be object")
    return cast(dict[str, object], value)


def _require_plain_list(payload: Mapping[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if type(value) is not list:
        raise BackendIntegrationPackageError(f"backend integration {key} must be list")
    return cast(list[object], value)


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise BackendIntegrationPackageError(
            f"backend integration {label} must be safe identifier"
        )
    if len(value.encode("utf-8")) > MAX_BACKEND_INTEGRATION_PACKAGE_FIELD_BYTES:
        raise BackendIntegrationPackageError(f"backend integration {label} exceeds limit")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise BackendIntegrationPackageError(f"backend integration {label} invalid")


def _digest_json(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


__all__ = [
    "BACKEND_INTEGRATION_PACKAGE_BLOCKED_EXECUTION_SURFACES",
    "BACKEND_INTEGRATION_PACKAGE_CONTRACT",
    "BACKEND_INTEGRATION_PACKAGE_EXPECTED_REASONS",
    "BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY",
    "BACKEND_INTEGRATION_PACKAGE_POLICY",
    "BACKEND_INTEGRATION_PACKAGE_REPORT_SCHEMA_VERSION",
    "BACKEND_INTEGRATION_PACKAGE_SCHEMA_VERSION",
    "BACKEND_INTEGRATION_PACKAGE_STATUS_FAIL",
    "BACKEND_INTEGRATION_PACKAGE_STATUS_PASS",
    "MAX_BACKEND_INTEGRATION_PACKAGE_BYTES",
    "MAX_BACKEND_INTEGRATION_PACKAGE_CASES",
    "MAX_BACKEND_INTEGRATION_PACKAGE_FIELD_BYTES",
    "MAX_BACKEND_INTEGRATION_PACKAGE_REPORT_BYTES",
    "BackendIntegrationCase",
    "BackendIntegrationCaseResult",
    "BackendIntegrationPackage",
    "BackendIntegrationPackageError",
    "BackendIntegrationPackageReport",
    "BackendIntegrationPlanningProbe",
    "assert_backend_integration_package",
    "backend_integration_package_report_to_dict",
    "dump_backend_integration_package_report",
    "evaluate_backend_integration_package",
    "load_backend_integration_package",
    "parse_backend_integration_package",
]
