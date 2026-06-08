"""Backend conformance fixtures for prototype TUC backends."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass

from tuc.backends.base import Backend, LoweringResult
from tuc.ir.memory import LayoutKind
from tuc.ir.model import ComputeGraph, ComputeOperation, OperationKind, TensorRef

CONFORMANCE_REPORT_SCHEMA_VERSION = "tuc.backend_conformance_report.v0"
MVP_CONFORMANCE_OPERATION_KINDS = (
    OperationKind.MATMUL,
    OperationKind.ELEMENTWISE,
    OperationKind.REDUCTION,
    OperationKind.SOFTMAX,
)
MAX_CONFORMANCE_ARTIFACT_BYTES = 64 * 1024
MAX_CONFORMANCE_DIAGNOSTICS = 16
MAX_CONFORMANCE_DIAGNOSTIC_BYTES = 512
MAX_CONFORMANCE_REPORT_BYTES = 64 * 1024
MAX_CONFORMANCE_REPORT_CASES = 128
MAX_CONFORMANCE_REPORT_FIELD_BYTES = 512
MAX_CONFORMANCE_REPORT_ISSUES = 128


@dataclass(frozen=True)
class BackendConformanceIssue:
    """One backend conformance failure."""

    case_name: str
    message: str


@dataclass(frozen=True)
class BackendConformanceReport:
    """Result of running backend conformance fixtures."""

    backend_name: str
    checked_cases: tuple[str, ...]
    issues: tuple[BackendConformanceIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


class BackendConformanceError(AssertionError):
    """Raised when a backend fails the reusable conformance fixtures."""


def build_conformance_graph(
    kind: OperationKind,
    *,
    layout: LayoutKind = LayoutKind.ROW_MAJOR,
) -> ComputeGraph:
    """Build a tiny valid graph for one MVP operation kind."""

    if not isinstance(kind, OperationKind):
        raise TypeError("conformance operation kind must be OperationKind")
    if not isinstance(layout, LayoutKind):
        raise TypeError("conformance layout must be LayoutKind")

    attributes: dict[str, object] = {"tuc.layout": layout.value}
    if kind is OperationKind.MATMUL:
        operation = ComputeOperation(
            name="matmul",
            kind=kind,
            inputs=(TensorRef("a", (4, 8)), TensorRef("b", (8, 3))),
            outputs=(TensorRef("c", (4, 3)),),
            attributes=attributes,
        )
    elif kind is OperationKind.ELEMENTWISE:
        operation = ComputeOperation(
            name="activation",
            kind=kind,
            inputs=(TensorRef("x", (4, 3)),),
            outputs=(TensorRef("y", (4, 3)),),
            attributes=attributes,
        )
    elif kind is OperationKind.REDUCTION:
        operation = ComputeOperation(
            name="sum_rows",
            kind=kind,
            inputs=(TensorRef("x", (4, 3)),),
            outputs=(TensorRef("y", (4,)),),
            attributes=attributes,
        )
    elif kind is OperationKind.SOFTMAX:
        operation = ComputeOperation(
            name="softmax",
            kind=kind,
            inputs=(TensorRef("x", (4, 3)),),
            outputs=(TensorRef("y", (4, 3)),),
            attributes=attributes,
        )
    else:
        raise ValueError(f"unsupported conformance operation kind: {kind.value}")

    return ComputeGraph(
        name=f"conformance_{kind.value}_{layout.value}",
        operations=(operation,),
        metadata={"conformance": "backend.v0.1"},
    )


def run_backend_conformance(
    backend: Backend,
    *,
    operation_kinds: Iterable[OperationKind] = MVP_CONFORMANCE_OPERATION_KINDS,
) -> BackendConformanceReport:
    """Run reusable conformance fixtures against a trusted in-process backend."""

    capability = backend.capability
    cases = tuple(_conformance_cases(operation_kinds, tuple(capability.supported_layouts)))
    issues: list[BackendConformanceIssue] = []
    checked_cases: list[str] = []

    for graph in cases:
        operation = graph.operations[0]
        case_name = graph.name
        checked_cases.append(case_name)
        declared_supported = capability.supports(operation)
        if declared_supported:
            issues.extend(_check_supported_lowering(backend, graph, case_name))
        else:
            issues.extend(_check_unsupported_lowering(backend, graph, case_name))

    return BackendConformanceReport(
        backend_name=capability.name,
        checked_cases=tuple(checked_cases),
        issues=tuple(issues),
    )


def assert_backend_conformance(
    backend: Backend,
    *,
    operation_kinds: Iterable[OperationKind] = MVP_CONFORMANCE_OPERATION_KINDS,
) -> BackendConformanceReport:
    """Raise unless a backend satisfies the reusable conformance fixtures."""

    report = run_backend_conformance(backend, operation_kinds=operation_kinds)
    if report.issues:
        lines = [f"backend {report.backend_name!r} failed conformance:"]
        lines.extend(f"- {issue.case_name}: {issue.message}" for issue in report.issues)
        raise BackendConformanceError("\n".join(lines))
    return report


def conformance_report_to_dict(
    report: BackendConformanceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible conformance report payload."""

    _validate_report(report)
    return {
        "backend_name": report.backend_name,
        "checked_cases": list(report.checked_cases),
        "issues": [
            {
                "case_name": issue.case_name,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "schema_version": CONFORMANCE_REPORT_SCHEMA_VERSION,
    }


def dump_backend_conformance_report(report: BackendConformanceReport) -> str:
    """Render a stable review artifact for backend conformance evidence."""

    text = json.dumps(conformance_report_to_dict(report), indent=2, sort_keys=True)
    if len(text.encode("utf-8")) > MAX_CONFORMANCE_REPORT_BYTES:
        raise ValueError("backend conformance report exceeds byte limit")
    return text + "\n"


def _conformance_cases(
    operation_kinds: Iterable[OperationKind],
    supported_layouts: tuple[LayoutKind, ...],
) -> Iterable[ComputeGraph]:
    layouts = tuple(
        sorted(
            set(supported_layouts) | {LayoutKind.ROW_MAJOR},
            key=lambda item: item.value,
        )
    )
    for kind in tuple(operation_kinds):
        if not isinstance(kind, OperationKind):
            raise TypeError("conformance operation kinds must be OperationKind")
        for layout in layouts:
            yield build_conformance_graph(kind, layout=layout)


def _check_supported_lowering(
    backend: Backend,
    graph: ComputeGraph,
    case_name: str,
) -> tuple[BackendConformanceIssue, ...]:
    try:
        lowered = backend.lower(graph)
    except Exception as exc:
        return (
            BackendConformanceIssue(
                case_name=case_name,
                message=f"declared-supported graph failed to lower with {type(exc).__name__}",
            ),
        )

    issues: list[BackendConformanceIssue] = []
    issues.extend(_validate_lowering_result(backend, graph, lowered, case_name))
    operation = graph.operations[0]
    if operation.kind.value not in lowered.artifact or operation.name not in lowered.artifact:
        issues.append(
            BackendConformanceIssue(
                case_name=case_name,
                message="artifact must mention the operation kind and operation name",
            )
        )
    return tuple(issues)


def _check_unsupported_lowering(
    backend: Backend,
    graph: ComputeGraph,
    case_name: str,
) -> tuple[BackendConformanceIssue, ...]:
    try:
        lowered = backend.lower(graph)
    except Exception as exc:
        message = str(exc)
        if not message:
            return (
                BackendConformanceIssue(
                    case_name=case_name,
                    message="unsupported rejection diagnostic must not be empty",
                ),
            )
        if len(message.encode("utf-8")) > MAX_CONFORMANCE_DIAGNOSTIC_BYTES:
            return (
                BackendConformanceIssue(
                    case_name=case_name,
                    message="unsupported rejection diagnostic exceeds byte limit",
                ),
            )
        return ()

    return (
        BackendConformanceIssue(
            case_name=case_name,
            message=(
                "backend lowered an operation not accepted by capability.supports; "
                f"artifact bytes={len(lowered.artifact.encode('utf-8'))}"
            ),
        ),
    )


def _validate_lowering_result(
    backend: Backend,
    graph: ComputeGraph,
    lowered: LoweringResult,
    case_name: str,
) -> tuple[BackendConformanceIssue, ...]:
    issues: list[BackendConformanceIssue] = []
    if not isinstance(lowered, LoweringResult):
        return (
            BackendConformanceIssue(
                case_name=case_name,
                message="lowering must return LoweringResult",
            ),
        )
    if lowered.backend_name != backend.capability.name:
        issues.append(
            BackendConformanceIssue(
                case_name=case_name,
                message="lowering result backend_name must match capability name",
            )
        )
    if lowered.graph_name != graph.name:
        issues.append(
            BackendConformanceIssue(
                case_name=case_name,
                message="lowering result graph_name must match input graph",
            )
        )
    if not lowered.artifact:
        issues.append(
            BackendConformanceIssue(
                case_name=case_name,
                message="artifact must not be empty",
            )
        )
    if len(lowered.artifact.encode("utf-8")) > MAX_CONFORMANCE_ARTIFACT_BYTES:
        issues.append(
            BackendConformanceIssue(
                case_name=case_name,
                message="artifact exceeds conformance byte limit",
            )
        )
    issues.extend(_validate_diagnostics(lowered, case_name))
    return tuple(issues)


def _validate_diagnostics(
    lowered: LoweringResult,
    case_name: str,
) -> tuple[BackendConformanceIssue, ...]:
    if not isinstance(lowered.diagnostics, tuple):
        return (
            BackendConformanceIssue(
                case_name=case_name,
                message="diagnostics must be a tuple of strings",
            ),
        )
    if len(lowered.diagnostics) > MAX_CONFORMANCE_DIAGNOSTICS:
        return (
            BackendConformanceIssue(
                case_name=case_name,
                message="diagnostics exceed count limit",
            ),
        )

    issues: list[BackendConformanceIssue] = []
    for diagnostic in lowered.diagnostics:
        if not isinstance(diagnostic, str) or not diagnostic:
            issues.append(
                BackendConformanceIssue(
                    case_name=case_name,
                    message="diagnostics must contain non-empty strings",
                )
            )
            continue
        if len(diagnostic.encode("utf-8")) > MAX_CONFORMANCE_DIAGNOSTIC_BYTES:
            issues.append(
                BackendConformanceIssue(
                    case_name=case_name,
                    message="diagnostic exceeds byte limit",
                )
            )
    return tuple(issues)


def _validate_report(report: BackendConformanceReport) -> None:
    if not isinstance(report, BackendConformanceReport):
        raise TypeError("backend conformance report must be BackendConformanceReport")
    _validate_report_text(report.backend_name, "backend_name")
    if len(report.checked_cases) > MAX_CONFORMANCE_REPORT_CASES:
        raise ValueError("backend conformance report exceeds checked-case limit")
    for case_name in report.checked_cases:
        _validate_report_text(case_name, "checked case")
    if len(report.issues) > MAX_CONFORMANCE_REPORT_ISSUES:
        raise ValueError("backend conformance report exceeds issue limit")
    for issue in report.issues:
        if not isinstance(issue, BackendConformanceIssue):
            raise TypeError("backend conformance report issues must be issue objects")
        _validate_report_text(issue.case_name, "issue case_name")
        _validate_report_text(issue.message, "issue message")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_CONFORMANCE_REPORT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds conformance report field limit")


__all__ = [
    "BackendConformanceError",
    "BackendConformanceIssue",
    "BackendConformanceReport",
    "CONFORMANCE_REPORT_SCHEMA_VERSION",
    "MVP_CONFORMANCE_OPERATION_KINDS",
    "assert_backend_conformance",
    "build_conformance_graph",
    "conformance_report_to_dict",
    "dump_backend_conformance_report",
    "run_backend_conformance",
]
