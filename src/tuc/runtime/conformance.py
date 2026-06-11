"""Trusted Runtime Executor conformance checks.

The conformance report exercises the fixed in-process executor registry with
bounded, in-memory operation fixtures. It does not discover backends, import
modules, access devices, spawn subprocesses, execute generated artifacts, or
load external files.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from tuc.ir.model import ComputeOperation, OperationKind, TensorRef
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    FloatArray,
    TrustedRuntimeBackendExecutor,
    trusted_runtime_executor_registry,
)

RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_executor_conformance_report.v0"
)
RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT = "runtime_executor_conformance.trusted.v0"
MAX_RUNTIME_EXECUTOR_CONFORMANCE_CASES = 128
MAX_RUNTIME_EXECUTOR_CONFORMANCE_ISSUES = 128
MAX_RUNTIME_EXECUTOR_CONFORMANCE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_EXECUTOR_CONFORMANCE_FIELD_BYTES = 512

_CONFORMANCE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_EXPECTED_STATUSES = frozenset({"supported", "unsupported"})
_OBSERVED_STATUSES = frozenset({"executed", "failed", "rejected"})


@dataclass(frozen=True)
class RuntimeExecutorConformanceIssue:
    """One derived conformance issue for the trusted runtime executor registry."""

    executor_name: str
    case_name: str
    message: str

    def __post_init__(self) -> None:
        _validate_conformance_name(self.executor_name, "issue executor_name")
        _validate_conformance_name(self.case_name, "issue case_name")
        _validate_conformance_name(self.message, "issue message")


@dataclass(frozen=True)
class RuntimeExecutorConformanceCase:
    """Observed behavior for one executor and one operation-family fixture."""

    executor_name: str
    operation_kind: OperationKind
    case_name: str
    expected_status: str
    observed_status: str
    output_shape: tuple[int, ...]
    output_dtype: str

    def __post_init__(self) -> None:
        _validate_conformance_name(self.executor_name, "case executor_name")
        if not isinstance(self.operation_kind, OperationKind):
            raise TypeError("case operation_kind must be OperationKind")
        _validate_conformance_name(self.case_name, "case case_name")
        if self.expected_status not in _EXPECTED_STATUSES:
            raise ValueError("case expected_status is not a conformance status")
        if self.observed_status not in _OBSERVED_STATUSES:
            raise ValueError("case observed_status is not a conformance status")
        if self.observed_status == "executed":
            _validate_conformance_shape(self.output_shape)
            if self.output_dtype != "float64":
                raise ValueError("executed conformance case must emit float64")
            return
        if self.output_shape != ():
            raise ValueError("non-executed conformance case must not emit a shape")
        if self.output_dtype != "not_executed":
            raise ValueError("non-executed conformance case must use not_executed dtype")


@dataclass(frozen=True)
class RuntimeExecutorConformanceReport:
    """Deterministic conformance report for trusted runtime executors."""

    checked_cases: tuple[RuntimeExecutorConformanceCase, ...]
    issues: tuple[RuntimeExecutorConformanceIssue, ...]
    conformance_contract: str = RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.conformance_contract != RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT:
            raise ValueError("runtime executor conformance contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime executor contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("trusted runtime executor registry mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime executor blocked execution surfaces changed")
        if type(self.checked_cases) is not tuple:
            raise TypeError("runtime executor conformance cases must be a tuple")
        if not self.checked_cases:
            raise ValueError("runtime executor conformance must contain cases")
        if len(self.checked_cases) > MAX_RUNTIME_EXECUTOR_CONFORMANCE_CASES:
            raise ValueError("runtime executor conformance case count exceeds limit")
        case_names: list[str] = []
        for case in self.checked_cases:
            if not isinstance(case, RuntimeExecutorConformanceCase):
                raise TypeError(
                    "runtime executor conformance cases must be "
                    "RuntimeExecutorConformanceCase"
                )
            case_names.append(case.case_name)
        if len(case_names) != len(set(case_names)):
            raise ValueError("runtime executor conformance case names must be unique")
        if type(self.issues) is not tuple:
            raise TypeError("runtime executor conformance issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_EXECUTOR_CONFORMANCE_ISSUES:
            raise ValueError("runtime executor conformance issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeExecutorConformanceIssue):
                raise TypeError(
                    "runtime executor conformance issues must be "
                    "RuntimeExecutorConformanceIssue"
                )
        expected_issues = _derive_conformance_issues(self.checked_cases)
        if self.issues != expected_issues:
            raise ValueError("runtime executor conformance issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether all trusted executor cases behaved as declared."""

        return not self.issues


class RuntimeExecutorConformanceError(AssertionError):
    """Raised when the trusted runtime executor registry fails conformance."""


def run_runtime_executor_conformance() -> RuntimeExecutorConformanceReport:
    """Run bounded conformance cases against the fixed trusted executor registry."""

    registry = trusted_runtime_executor_registry()
    checked_cases: list[RuntimeExecutorConformanceCase] = []

    for executor_name in sorted(registry):
        executor = registry[executor_name]
        for operation_kind in OperationKind:
            checked_cases.append(_run_operation_case(executor, operation_kind))

    cases = tuple(checked_cases)
    return RuntimeExecutorConformanceReport(
        checked_cases=cases,
        issues=_derive_conformance_issues(cases),
    )


def assert_runtime_executor_conformance() -> RuntimeExecutorConformanceReport:
    """Return the conformance report or raise when trusted executors drift."""

    report = run_runtime_executor_conformance()
    if report.issues:
        lines = ["runtime executor conformance failed:"]
        lines.extend(
            f"- {issue.executor_name}:{issue.case_name}:{issue.message}"
            for issue in report.issues
        )
        raise RuntimeExecutorConformanceError("\n".join(lines))
    return report


def runtime_executor_conformance_report_to_dict(
    report: RuntimeExecutorConformanceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible runtime executor conformance report."""

    if not isinstance(report, RuntimeExecutorConformanceReport):
        raise TypeError("runtime executor conformance report must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "case_count": len(report.checked_cases),
        "checked_cases": [
            {
                "case_name": case.case_name,
                "executor_name": case.executor_name,
                "expected_status": case.expected_status,
                "observed_status": case.observed_status,
                "operation_kind": case.operation_kind.value,
                "output_dtype": case.output_dtype,
                "output_shape": list(case.output_shape),
            }
            for case in report.checked_cases
        ],
        "conformance_contract": report.conformance_contract,
        "executor_contract": report.executor_contract,
        "issues": [
            {
                "case_name": issue.case_name,
                "executor_name": issue.executor_name,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "schema_version": RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION,
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_executor_conformance_report(
    report: RuntimeExecutorConformanceReport,
) -> str:
    """Render a stable trusted runtime executor conformance report."""

    text = json.dumps(
        runtime_executor_conformance_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_EXECUTOR_CONFORMANCE_REPORT_BYTES:
        raise ValueError("runtime executor conformance report exceeds byte limit")
    return text + "\n"


def _run_operation_case(
    executor: TrustedRuntimeBackendExecutor,
    operation_kind: OperationKind,
) -> RuntimeExecutorConformanceCase:
    operation, values = _operation_fixture(operation_kind)
    expected_status = (
        "supported" if operation_kind in executor.supported_ops else "unsupported"
    )
    case_name = f"{executor.name}_{operation_kind.value}_{expected_status}"

    try:
        output = executor.execute(operation, values)
    except ValueError:
        return RuntimeExecutorConformanceCase(
            executor_name=executor.name,
            operation_kind=operation_kind,
            case_name=case_name,
            expected_status=expected_status,
            observed_status="rejected",
            output_shape=(),
            output_dtype="not_executed",
        )
    except (KeyError, TypeError):
        return RuntimeExecutorConformanceCase(
            executor_name=executor.name,
            operation_kind=operation_kind,
            case_name=case_name,
            expected_status=expected_status,
            observed_status="failed",
            output_shape=(),
            output_dtype="not_executed",
        )

    return RuntimeExecutorConformanceCase(
        executor_name=executor.name,
        operation_kind=operation_kind,
        case_name=case_name,
        expected_status=expected_status,
        observed_status="executed",
        output_shape=tuple(int(dimension) for dimension in output.shape),
        output_dtype=str(output.dtype),
    )


def _operation_fixture(
    operation_kind: OperationKind,
) -> tuple[ComputeOperation, Mapping[str, FloatArray]]:
    if operation_kind is OperationKind.MATMUL:
        lhs = TensorRef("lhs", (2, 3), "float64")
        rhs = TensorRef("rhs", (3, 2), "float64")
        out = TensorRef("matmul_out", (2, 2), "float64")
        return (
            ComputeOperation(
                name="matmul_fixture",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(out,),
            ),
            {
                "lhs": np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64),
                "rhs": np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float64),
            },
        )
    if operation_kind is OperationKind.ELEMENTWISE:
        source = TensorRef("source", (2, 2), "float64")
        out = TensorRef("elementwise_out", (2, 2), "float64")
        return (
            ComputeOperation(
                name="elementwise_fixture",
                kind=OperationKind.ELEMENTWISE,
                inputs=(source,),
                outputs=(out,),
                attributes={"kernel": "relu"},
            ),
            {
                "source": np.array(
                    [[-1.0, 0.5], [2.0, -3.0]],
                    dtype=np.float64,
                ),
            },
        )
    if operation_kind is OperationKind.REDUCTION:
        source = TensorRef("source", (2, 3), "float64")
        out = TensorRef("reduction_out", (2,), "float64")
        return (
            ComputeOperation(
                name="reduction_fixture",
                kind=OperationKind.REDUCTION,
                inputs=(source,),
                outputs=(out,),
                attributes={"axis": 1},
            ),
            {
                "source": np.array(
                    [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
                    dtype=np.float64,
                ),
            },
        )
    if operation_kind is OperationKind.SOFTMAX:
        source = TensorRef("source", (2, 3), "float64")
        out = TensorRef("softmax_out", (2, 3), "float64")
        return (
            ComputeOperation(
                name="softmax_fixture",
                kind=OperationKind.SOFTMAX,
                inputs=(source,),
                outputs=(out,),
                attributes={"axis": 1},
            ),
            {
                "source": np.array(
                    [[1.0, 2.0, 3.0], [1.5, -0.5, 0.0]],
                    dtype=np.float64,
                ),
            },
        )
    raise ValueError(f"unsupported runtime executor conformance kind: {operation_kind}")


def _derive_conformance_issues(
    cases: tuple[RuntimeExecutorConformanceCase, ...],
) -> tuple[RuntimeExecutorConformanceIssue, ...]:
    issues: list[RuntimeExecutorConformanceIssue] = []
    for case in cases:
        if case.expected_status == "supported" and case.observed_status != "executed":
            issues.append(
                RuntimeExecutorConformanceIssue(
                    executor_name=case.executor_name,
                    case_name=case.case_name,
                    message="supported_case_did_not_execute",
                )
            )
        if case.expected_status == "unsupported" and case.observed_status == "executed":
            issues.append(
                RuntimeExecutorConformanceIssue(
                    executor_name=case.executor_name,
                    case_name=case.case_name,
                    message="unsupported_case_executed",
                )
            )
        if case.expected_status == "unsupported" and case.observed_status == "failed":
            issues.append(
                RuntimeExecutorConformanceIssue(
                    executor_name=case.executor_name,
                    case_name=case.case_name,
                    message="unsupported_case_not_rejected_cleanly",
                )
            )
    return tuple(issues)


def _validate_conformance_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not _CONFORMANCE_NAME_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime conformance identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_EXECUTOR_CONFORMANCE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime conformance field limit")
    if value in {
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "subprocess",
        "url",
    }:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_conformance_shape(value: tuple[int, ...]) -> None:
    if type(value) is not tuple or not value:
        raise ValueError("runtime conformance output shape must be non-empty")
    for dimension in value:
        if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0:
            raise ValueError("runtime conformance output shape must be positive integers")


__all__ = [
    "MAX_RUNTIME_EXECUTOR_CONFORMANCE_CASES",
    "MAX_RUNTIME_EXECUTOR_CONFORMANCE_FIELD_BYTES",
    "MAX_RUNTIME_EXECUTOR_CONFORMANCE_ISSUES",
    "MAX_RUNTIME_EXECUTOR_CONFORMANCE_REPORT_BYTES",
    "RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT",
    "RUNTIME_EXECUTOR_CONFORMANCE_REPORT_SCHEMA_VERSION",
    "RuntimeExecutorConformanceCase",
    "RuntimeExecutorConformanceError",
    "RuntimeExecutorConformanceIssue",
    "RuntimeExecutorConformanceReport",
    "assert_runtime_executor_conformance",
    "dump_runtime_executor_conformance_report",
    "run_runtime_executor_conformance",
    "runtime_executor_conformance_report_to_dict",
]
