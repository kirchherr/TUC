"""Data-only reference correctness evidence for terminal runtime outputs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from typing import cast

import numpy as np
from numpy.typing import NDArray

from tuc.ir.model import MAX_TENSOR_DIMENSION, MAX_TENSOR_RANK, ComputeGraph
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RuntimeExecutionResult,
)
from tuc.runtime.output_manifest import (
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RuntimeExpectedOutput,
    build_runtime_output_manifest_report,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
)

RUNTIME_REFERENCE_CORRECTNESS_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_reference_correctness_report.v0"
)
RUNTIME_REFERENCE_CORRECTNESS_CONTRACT = "runtime_reference_correctness.data_only.v0"
RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS = "review_evidence"
RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL = 1e-12
RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL = 1e-12
RUNTIME_REFERENCE_CORRECTNESS_MAX_TOLERANCE = 1.0
MAX_RUNTIME_REFERENCE_CORRECTNESS_COMPARISONS = 4096
MAX_RUNTIME_REFERENCE_CORRECTNESS_ISSUES = 256
MAX_RUNTIME_REFERENCE_CORRECTNESS_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_REFERENCE_CORRECTNESS_FIELD_BYTES = 512

_REFERENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_MISSING = object()
_COMPARISON_STATUSES = frozenset(
    {
        "invalid_output",
        "invalid_reference",
        "matched",
        "mismatched",
        "missing_output",
        "missing_reference",
    }
)
_SPECIAL_DTYPES = frozenset({"invalid", "missing"})
_FORBIDDEN_REFERENCE_TEXT = frozenset(
    {
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
        "output_value",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "reference_value",
        "source_text",
        "subprocess",
        "tensor_value",
        "url",
    }
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class RuntimeReferenceComparison:
    """Metadata-only comparison between one terminal output and reference."""

    tensor_name: str
    expected_shape: tuple[int, ...]
    expected_dtype: str
    output_shape: tuple[int, ...]
    output_dtype: str
    reference_shape: tuple[int, ...]
    reference_dtype: str
    rtol: float
    atol: float
    comparison_status: str
    output_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    reference_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_reference_text(self.tensor_name, "comparison tensor_name")
        _validate_shape(self.expected_shape, "comparison expected_shape")
        _validate_expected_dtype(self.expected_dtype, "comparison expected_dtype")
        _validate_shape_or_empty(self.output_shape, "comparison output_shape")
        _validate_dtype(self.output_dtype, "comparison output_dtype")
        _validate_shape_or_empty(self.reference_shape, "comparison reference_shape")
        _validate_dtype(self.reference_dtype, "comparison reference_dtype")
        _validate_tolerance(self.rtol, "rtol")
        _validate_tolerance(self.atol, "atol")
        if self.comparison_status not in _COMPARISON_STATUSES:
            raise ValueError("runtime reference comparison status unsupported")
        if self.output_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime reference correctness must omit output values")
        if self.reference_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime reference correctness must omit reference values")
        self._validate_status_shape_dtype_consistency()

    def _validate_status_shape_dtype_consistency(self) -> None:
        if self.comparison_status == "matched":
            if self.output_shape != self.expected_shape:
                raise ValueError("matched comparison output shape must match expected")
            if self.reference_shape != self.expected_shape:
                raise ValueError("matched comparison reference shape must match expected")
            if self.output_dtype != self.expected_dtype:
                raise ValueError("matched comparison output dtype must match expected")
            if self.reference_dtype != self.expected_dtype:
                raise ValueError("matched comparison reference dtype must match expected")
        if (
            self.comparison_status == "missing_output"
            and (self.output_shape != () or self.output_dtype != "missing")
        ):
            raise ValueError("missing output comparison must use missing output metadata")
        if (
            self.comparison_status == "missing_reference"
            and (self.reference_shape != () or self.reference_dtype != "missing")
        ):
            raise ValueError(
                "missing reference comparison must use missing reference metadata"
            )


@dataclass(frozen=True)
class RuntimeReferenceCorrectnessIssue:
    """One derived runtime reference correctness issue."""

    tensor_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_reference_text(self.tensor_name, "reference issue tensor_name")
        _validate_reference_text(self.issue_code, "reference issue_code")


@dataclass(frozen=True)
class RuntimeReferenceCorrectnessReport:
    """Deterministic, data-only correctness report for terminal outputs."""

    graph_name: str
    comparisons: tuple[RuntimeReferenceComparison, ...]
    reference_tensor_names: tuple[str, ...]
    issues: tuple[RuntimeReferenceCorrectnessIssue, ...]
    correctness_contract: str = RUNTIME_REFERENCE_CORRECTNESS_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    output_manifest_contract: str = RUNTIME_OUTPUT_MANIFEST_CONTRACT
    artifact_status: str = RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_reference_text(self.graph_name, "reference correctness graph_name")
        if self.correctness_contract != RUNTIME_REFERENCE_CORRECTNESS_CONTRACT:
            raise ValueError("runtime reference correctness contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime reference correctness executor contract mismatch")
        if self.output_manifest_contract != RUNTIME_OUTPUT_MANIFEST_CONTRACT:
            raise ValueError(
                "runtime reference correctness output manifest contract mismatch"
            )
        if self.artifact_status != RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS:
            raise ValueError("runtime reference correctness artifact status mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime reference correctness must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime reference blocked execution surfaces changed")
        _validate_comparisons(self.comparisons)
        _validate_reference_tensor_names(self.reference_tensor_names)
        if type(self.issues) is not tuple:
            raise TypeError("runtime reference correctness issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_REFERENCE_CORRECTNESS_ISSUES:
            raise ValueError("runtime reference correctness issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeReferenceCorrectnessIssue):
                raise TypeError(
                    "runtime reference correctness issues must be correctness issues"
                )
        expected_issues = _derive_issues(self.comparisons, self.reference_tensor_names)
        if self.issues != expected_issues:
            raise ValueError("runtime reference correctness issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether reference correctness evidence passed."""

        return not self.issues

    @property
    def comparison_metadata_digest(self) -> str:
        """Return a digest over comparison metadata only, never tensor values."""

        payload = [
            {
                "atol": comparison.atol,
                "comparison_status": comparison.comparison_status,
                "expected_dtype": comparison.expected_dtype,
                "expected_shape": list(comparison.expected_shape),
                "output_dtype": comparison.output_dtype,
                "output_shape": list(comparison.output_shape),
                "output_value_status": comparison.output_value_status,
                "reference_dtype": comparison.reference_dtype,
                "reference_shape": list(comparison.reference_shape),
                "reference_value_status": comparison.reference_value_status,
                "rtol": comparison.rtol,
                "tensor_name": comparison.tensor_name,
            }
            for comparison in self.comparisons
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeReferenceCorrectnessError(AssertionError):
    """Raised when runtime reference correctness evidence does not pass."""


def build_runtime_reference_correctness_report(
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
    references: Mapping[str, object],
    *,
    rtol: float = RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL,
    atol: float = RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL,
) -> RuntimeReferenceCorrectnessReport:
    """Build data-only reference correctness evidence for terminal outputs."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime reference correctness graph must be ComputeGraph")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError(
            "runtime reference correctness execution must be RuntimeExecutionResult"
        )
    if type(references) is not dict:
        raise TypeError("runtime reference correctness references must be a plain dict")
    _validate_tolerance(rtol, "rtol")
    _validate_tolerance(atol, "atol")
    reference_names = _reference_names(references)
    output_manifest = build_runtime_output_manifest_report(graph, execution)
    comparisons = tuple(
        _build_comparison(
            expected=expected,
            execution=execution,
            reference=references.get(expected.tensor_name, _MISSING),
            rtol=rtol,
            atol=atol,
        )
        for expected in output_manifest.expected_outputs
    )
    return RuntimeReferenceCorrectnessReport(
        graph_name=graph.name,
        comparisons=comparisons,
        reference_tensor_names=reference_names,
        issues=_derive_issues(comparisons, reference_names),
    )


def assert_runtime_reference_correctness(
    report: RuntimeReferenceCorrectnessReport,
) -> RuntimeReferenceCorrectnessReport:
    """Return the report or raise when runtime reference correctness fails."""

    if not isinstance(report, RuntimeReferenceCorrectnessReport):
        raise TypeError("runtime reference correctness report must be report object")
    if report.issues:
        lines = [f"runtime reference correctness failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeReferenceCorrectnessError("\n".join(lines))
    return report


def runtime_reference_correctness_report_to_dict(
    report: RuntimeReferenceCorrectnessReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible correctness report."""

    if not isinstance(report, RuntimeReferenceCorrectnessReport):
        raise TypeError("runtime reference correctness report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "comparison_count": len(report.comparisons),
        "comparison_metadata_digest": report.comparison_metadata_digest,
        "comparisons": [
            {
                "atol": comparison.atol,
                "comparison_status": comparison.comparison_status,
                "expected_dtype": comparison.expected_dtype,
                "expected_shape": list(comparison.expected_shape),
                "output_dtype": comparison.output_dtype,
                "output_shape": list(comparison.output_shape),
                "output_value_status": comparison.output_value_status,
                "reference_dtype": comparison.reference_dtype,
                "reference_shape": list(comparison.reference_shape),
                "reference_value_status": comparison.reference_value_status,
                "rtol": comparison.rtol,
                "tensor_name": comparison.tensor_name,
            }
            for comparison in report.comparisons
        ],
        "correctness_contract": report.correctness_contract,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "tensor_name": issue.tensor_name,
            }
            for issue in report.issues
        ],
        "output_manifest_contract": report.output_manifest_contract,
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "reference_tensor_names": list(report.reference_tensor_names),
        "schema_version": RUNTIME_REFERENCE_CORRECTNESS_REPORT_SCHEMA_VERSION,
    }


def dump_runtime_reference_correctness_report(
    report: RuntimeReferenceCorrectnessReport,
) -> str:
    """Render stable data-only runtime reference correctness evidence."""

    text = json.dumps(
        runtime_reference_correctness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_REFERENCE_CORRECTNESS_REPORT_BYTES:
        raise ValueError("runtime reference correctness report exceeds byte limit")
    return text + "\n"


def _build_comparison(
    *,
    expected: RuntimeExpectedOutput,
    execution: RuntimeExecutionResult,
    reference: object,
    rtol: float,
    atol: float,
) -> RuntimeReferenceComparison:
    try:
        output = execution.output_for(expected.tensor_name)
    except KeyError:
        return RuntimeReferenceComparison(
            tensor_name=expected.tensor_name,
            expected_shape=expected.shape,
            expected_dtype=expected.dtype,
            output_shape=(),
            output_dtype="missing",
            reference_shape=_shape_for_reference(reference),
            reference_dtype=_dtype_for_reference(reference),
            rtol=rtol,
            atol=atol,
            comparison_status="missing_output",
        )

    output_shape = tuple(int(dimension) for dimension in output.shape)
    output_dtype = str(output.dtype)
    if output_shape != expected.shape or output_dtype != expected.dtype:
        status = "mismatched"
    elif not bool(np.all(np.isfinite(output))):
        status = "invalid_output"
    elif reference is _MISSING:
        status = "missing_reference"
    elif not isinstance(reference, np.ndarray):
        status = "invalid_reference"
    else:
        reference_array = cast(NDArray[np.generic], reference)
        if not _reference_array_is_valid(reference_array, expected):
            status = "invalid_reference"
        else:
            status = (
                "matched"
                if bool(
                    np.allclose(
                        output,
                        cast(FloatArray, reference_array),
                        rtol=rtol,
                        atol=atol,
                    )
                )
                else "mismatched"
            )

    return RuntimeReferenceComparison(
        tensor_name=expected.tensor_name,
        expected_shape=expected.shape,
        expected_dtype=expected.dtype,
        output_shape=output_shape,
        output_dtype=output_dtype,
        reference_shape=_shape_for_reference(reference),
        reference_dtype=_dtype_for_reference(reference),
        rtol=rtol,
        atol=atol,
        comparison_status=status,
    )


def _derive_issues(
    comparisons: tuple[RuntimeReferenceComparison, ...],
    reference_tensor_names: tuple[str, ...],
) -> tuple[RuntimeReferenceCorrectnessIssue, ...]:
    issues: list[RuntimeReferenceCorrectnessIssue] = []
    comparison_names = {comparison.tensor_name for comparison in comparisons}
    reference_names = set(reference_tensor_names)

    for comparison in comparisons:
        if (
            comparison.tensor_name not in reference_names
            and comparison.comparison_status != "missing_reference"
        ):
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="reference_name_missing",
                )
            )
        if comparison.comparison_status == "missing_output":
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="expected_output_missing",
                )
            )
            continue
        if comparison.comparison_status == "missing_reference":
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="reference_missing",
                )
            )
            continue
        if comparison.comparison_status == "invalid_output":
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="output_invalid",
                )
            )
            continue
        if comparison.comparison_status == "invalid_reference":
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="reference_invalid",
                )
            )
            continue
        if comparison.output_shape != comparison.expected_shape:
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="output_shape_mismatch",
                )
            )
        if comparison.output_dtype != comparison.expected_dtype:
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="output_dtype_mismatch",
                )
            )
        if comparison.reference_shape != comparison.expected_shape:
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="reference_shape_mismatch",
                )
            )
        if comparison.reference_dtype != comparison.expected_dtype:
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="reference_dtype_mismatch",
                )
            )
        if comparison.comparison_status == "mismatched":
            issues.append(
                RuntimeReferenceCorrectnessIssue(
                    tensor_name=comparison.tensor_name,
                    issue_code="reference_value_mismatch",
                )
            )

    for tensor_name in sorted(set(reference_tensor_names) - comparison_names):
        issues.append(
            RuntimeReferenceCorrectnessIssue(
                tensor_name=tensor_name,
                issue_code="unexpected_reference",
            )
        )

    return tuple(issues)


def _reference_names(references: Mapping[str, object]) -> tuple[str, ...]:
    names: list[str] = []
    for name in references:
        _validate_reference_text(name, "reference tensor name")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("runtime reference correctness reference names must be unique")
    return tuple(sorted(names))


def _shape_for_reference(reference: object) -> tuple[int, ...]:
    if reference is _MISSING:
        return ()
    if not isinstance(reference, np.ndarray):
        return ()
    return tuple(int(dimension) for dimension in reference.shape)


def _dtype_for_reference(reference: object) -> str:
    if reference is _MISSING:
        return "missing"
    if not isinstance(reference, np.ndarray):
        return "invalid"
    return str(reference.dtype)


def _reference_array_is_valid(
    reference: NDArray[np.generic],
    expected: RuntimeExpectedOutput,
) -> bool:
    return (
        tuple(reference.shape) == expected.shape
        and reference.dtype == np.dtype(np.float64)
        and bool(np.all(np.isfinite(reference)))
    )


def _validate_comparisons(
    comparisons: tuple[RuntimeReferenceComparison, ...],
) -> None:
    if type(comparisons) is not tuple:
        raise TypeError("runtime reference correctness comparisons must be a tuple")
    if not comparisons:
        raise ValueError("runtime reference correctness comparisons must not be empty")
    if len(comparisons) > MAX_RUNTIME_REFERENCE_CORRECTNESS_COMPARISONS:
        raise ValueError("runtime reference correctness comparison count exceeds limit")
    names: list[str] = []
    for comparison in comparisons:
        if not isinstance(comparison, RuntimeReferenceComparison):
            raise TypeError(
                "runtime reference correctness comparisons must be comparison objects"
            )
        names.append(comparison.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime reference correctness comparison names must be unique")


def _validate_reference_tensor_names(names: tuple[str, ...]) -> None:
    if type(names) is not tuple:
        raise TypeError("runtime reference correctness reference names must be a tuple")
    if len(names) > MAX_RUNTIME_REFERENCE_CORRECTNESS_COMPARISONS:
        raise ValueError("runtime reference correctness reference name count exceeds limit")
    for name in names:
        _validate_reference_text(name, "reference tensor name")
    if len(names) != len(set(names)):
        raise ValueError("runtime reference correctness reference names must be unique")
    if names != tuple(sorted(names)):
        raise ValueError("runtime reference correctness reference names must be sorted")


def _validate_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"{label} must be a non-empty tuple")
    _validate_shape_dimensions(value, label)


def _validate_shape_or_empty(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{label} must be a tuple")
    if value:
        _validate_shape_dimensions(value, label)


def _validate_shape_dimensions(value: tuple[int, ...], label: str) -> None:
    if len(value) > MAX_TENSOR_RANK:
        raise ValueError(f"{label} exceeds tensor rank limit")
    for dimension in value:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_TENSOR_DIMENSION
        ):
            raise ValueError(f"{label} must contain bounded positive integers")


def _validate_dtype(value: str, label: str) -> None:
    if value in _SPECIAL_DTYPES:
        return
    _validate_reference_text(value, label)


def _validate_expected_dtype(value: str, label: str) -> None:
    if value in _SPECIAL_DTYPES:
        raise ValueError(f"{label} must be a concrete dtype")
    _validate_reference_text(value, label)


def _validate_tolerance(value: float, label: str) -> None:
    if (
        not isinstance(value, float)
        or isinstance(value, bool)
        or not isfinite(value)
        or value < 0
        or value > RUNTIME_REFERENCE_CORRECTNESS_MAX_TOLERANCE
    ):
        raise ValueError(f"runtime reference correctness {label} must be bounded")


def _validate_reference_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REFERENCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime reference identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_REFERENCE_CORRECTNESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime reference correctness field limit")
    if value in _FORBIDDEN_REFERENCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_REFERENCE_CORRECTNESS_COMPARISONS",
    "MAX_RUNTIME_REFERENCE_CORRECTNESS_FIELD_BYTES",
    "MAX_RUNTIME_REFERENCE_CORRECTNESS_ISSUES",
    "MAX_RUNTIME_REFERENCE_CORRECTNESS_REPORT_BYTES",
    "RUNTIME_REFERENCE_CORRECTNESS_ARTIFACT_STATUS",
    "RUNTIME_REFERENCE_CORRECTNESS_CONTRACT",
    "RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_ATOL",
    "RUNTIME_REFERENCE_CORRECTNESS_DEFAULT_RTOL",
    "RUNTIME_REFERENCE_CORRECTNESS_MAX_TOLERANCE",
    "RUNTIME_REFERENCE_CORRECTNESS_REPORT_SCHEMA_VERSION",
    "RuntimeReferenceComparison",
    "RuntimeReferenceCorrectnessError",
    "RuntimeReferenceCorrectnessIssue",
    "RuntimeReferenceCorrectnessReport",
    "assert_runtime_reference_correctness",
    "build_runtime_reference_correctness_report",
    "dump_runtime_reference_correctness_report",
    "runtime_reference_correctness_report_to_dict",
]
