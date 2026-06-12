"""Data-only equivalence evidence for two trusted runtime backend placements."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from tuc.ir.model import MAX_TENSOR_DIMENSION, MAX_TENSOR_RANK, ComputeGraph
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeExecutionResult,
)
from tuc.runtime.output_manifest import RuntimeExpectedOutput, build_runtime_output_manifest_report
from tuc.runtime.partitioning import PartitionPlan
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_backend_equivalence_report.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_CONTRACT = "runtime_backend_equivalence.data_only.v0"
RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS = "review_evidence"
RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_RTOL = 1e-12
RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_ATOL = 1e-12
RUNTIME_BACKEND_EQUIVALENCE_MAX_TOLERANCE = 1.0
MAX_RUNTIME_BACKEND_EQUIVALENCE_RUNS = 2
MAX_RUNTIME_BACKEND_EQUIVALENCE_COMPARISONS = 4096
MAX_RUNTIME_BACKEND_EQUIVALENCE_ISSUES = 256
MAX_RUNTIME_BACKEND_EQUIVALENCE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_BACKEND_EQUIVALENCE_FIELD_BYTES = 512

_EQUIVALENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN_STATUSES = frozenset({"executed"})
_COMPARISON_STATUSES = frozenset(
    {
        "invalid_baseline_output",
        "invalid_candidate_output",
        "matched",
        "mismatched",
        "missing_baseline_output",
        "missing_candidate_output",
    }
)
_SPECIAL_DTYPES = frozenset({"invalid", "missing"})
_FORBIDDEN_EQUIVALENCE_TEXT = frozenset(
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
class RuntimeBackendEquivalenceRun:
    """Metadata for one trusted runtime execution used in equivalence review."""

    run_id: str
    graph_name: str
    planned_backend_sequence: tuple[str, ...]
    output_tensor_names: tuple[str, ...]
    output_metadata_digest: str
    trace_step_count: int
    tensor_record_count: int
    execution_status: str = "executed"
    output_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_equivalence_text(self.run_id, "run_id")
        _validate_equivalence_text(self.graph_name, "run graph_name")
        _validate_text_sequence(
            self.planned_backend_sequence,
            "planned_backend_sequence",
        )
        _validate_text_sequence(self.output_tensor_names, "output_tensor_names")
        _validate_digest(self.output_metadata_digest, "output_metadata_digest")
        _validate_positive_count(self.trace_step_count, "trace_step_count")
        _validate_positive_count(self.tensor_record_count, "tensor_record_count")
        if self.execution_status not in _RUN_STATUSES:
            raise ValueError("runtime backend equivalence run status unsupported")
        if self.output_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime backend equivalence must omit output values")


@dataclass(frozen=True)
class RuntimeBackendEquivalenceComparison:
    """Metadata-only comparison of one terminal output across two placements."""

    tensor_name: str
    baseline_run_id: str
    candidate_run_id: str
    expected_shape: tuple[int, ...]
    expected_dtype: str
    baseline_shape: tuple[int, ...]
    baseline_dtype: str
    candidate_shape: tuple[int, ...]
    candidate_dtype: str
    rtol: float
    atol: float
    comparison_status: str
    baseline_output_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    candidate_output_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_equivalence_text(self.tensor_name, "comparison tensor_name")
        _validate_equivalence_text(self.baseline_run_id, "baseline_run_id")
        _validate_equivalence_text(self.candidate_run_id, "candidate_run_id")
        _validate_shape(self.expected_shape, "expected_shape")
        _validate_concrete_dtype(self.expected_dtype, "expected_dtype")
        _validate_shape_or_empty(self.baseline_shape, "baseline_shape")
        _validate_dtype_or_status(self.baseline_dtype, "baseline_dtype")
        _validate_shape_or_empty(self.candidate_shape, "candidate_shape")
        _validate_dtype_or_status(self.candidate_dtype, "candidate_dtype")
        _validate_tolerance(self.rtol, "rtol")
        _validate_tolerance(self.atol, "atol")
        if self.comparison_status not in _COMPARISON_STATUSES:
            raise ValueError("runtime backend equivalence comparison status unsupported")
        if self.baseline_output_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime backend equivalence must omit baseline values")
        if self.candidate_output_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime backend equivalence must omit candidate values")
        self._validate_status_consistency()

    def _validate_status_consistency(self) -> None:
        if self.comparison_status == "matched":
            if self.baseline_shape != self.expected_shape:
                raise ValueError("matched baseline shape must match expected")
            if self.candidate_shape != self.expected_shape:
                raise ValueError("matched candidate shape must match expected")
            if self.baseline_dtype != self.expected_dtype:
                raise ValueError("matched baseline dtype must match expected")
            if self.candidate_dtype != self.expected_dtype:
                raise ValueError("matched candidate dtype must match expected")
        if (
            self.comparison_status == "missing_baseline_output"
            and (self.baseline_shape != () or self.baseline_dtype != "missing")
        ):
            raise ValueError("missing baseline output must use missing metadata")
        if (
            self.comparison_status == "missing_candidate_output"
            and (self.candidate_shape != () or self.candidate_dtype != "missing")
        ):
            raise ValueError("missing candidate output must use missing metadata")


@dataclass(frozen=True)
class RuntimeBackendEquivalenceIssue:
    """One derived runtime backend equivalence issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_equivalence_text(self.subject, "issue subject")
        _validate_equivalence_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeBackendEquivalenceReport:
    """Deterministic, data-only report for backend placement equivalence."""

    graph_name: str
    baseline_run_id: str
    candidate_run_id: str
    runs: tuple[RuntimeBackendEquivalenceRun, ...]
    comparisons: tuple[RuntimeBackendEquivalenceComparison, ...]
    issues: tuple[RuntimeBackendEquivalenceIssue, ...]
    equivalence_contract: str = RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    artifact_status: str = RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_equivalence_text(self.graph_name, "graph_name")
        _validate_equivalence_text(self.baseline_run_id, "baseline_run_id")
        _validate_equivalence_text(self.candidate_run_id, "candidate_run_id")
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError("runtime backend equivalence run IDs must be distinct")
        if self.equivalence_contract != RUNTIME_BACKEND_EQUIVALENCE_CONTRACT:
            raise ValueError("runtime backend equivalence contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime backend equivalence executor contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("runtime backend equivalence trusted registry mismatch")
        if self.artifact_status != RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS:
            raise ValueError("runtime backend equivalence artifact status mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime backend equivalence must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime backend equivalence blocked surfaces changed")
        _validate_runs(
            self.runs,
            self.graph_name,
            self.baseline_run_id,
            self.candidate_run_id,
        )
        _validate_comparisons(
            self.comparisons,
            self.baseline_run_id,
            self.candidate_run_id,
        )
        if type(self.issues) is not tuple:
            raise TypeError("runtime backend equivalence issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_BACKEND_EQUIVALENCE_ISSUES:
            raise ValueError("runtime backend equivalence issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeBackendEquivalenceIssue):
                raise TypeError(
                    "runtime backend equivalence issues must be equivalence issues"
                )
        expected_issues = _derive_issues(
            self.runs,
            self.comparisons,
            self.baseline_run_id,
            self.candidate_run_id,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime backend equivalence issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether backend equivalence evidence passed."""

        return not self.issues

    @property
    def comparison_metadata_digest(self) -> str:
        """Return a digest over comparison metadata only, never tensor values."""

        payload = [
            {
                "atol": comparison.atol,
                "baseline_dtype": comparison.baseline_dtype,
                "baseline_output_value_status": (
                    comparison.baseline_output_value_status
                ),
                "baseline_run_id": comparison.baseline_run_id,
                "baseline_shape": list(comparison.baseline_shape),
                "candidate_dtype": comparison.candidate_dtype,
                "candidate_output_value_status": (
                    comparison.candidate_output_value_status
                ),
                "candidate_run_id": comparison.candidate_run_id,
                "candidate_shape": list(comparison.candidate_shape),
                "comparison_status": comparison.comparison_status,
                "expected_dtype": comparison.expected_dtype,
                "expected_shape": list(comparison.expected_shape),
                "rtol": comparison.rtol,
                "tensor_name": comparison.tensor_name,
            }
            for comparison in self.comparisons
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeBackendEquivalenceError(AssertionError):
    """Raised when runtime backend equivalence evidence does not pass."""


def build_runtime_backend_equivalence_report(
    graph: ComputeGraph,
    baseline_partition_plan: PartitionPlan,
    baseline_execution: RuntimeExecutionResult,
    candidate_partition_plan: PartitionPlan,
    candidate_execution: RuntimeExecutionResult,
    *,
    baseline_run_id: str = "reference_cpu",
    candidate_run_id: str = "candidate_backend",
    rtol: float = RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_RTOL,
    atol: float = RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_ATOL,
) -> RuntimeBackendEquivalenceReport:
    """Build data-only equivalence evidence for two trusted runtime executions."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime backend equivalence graph must be ComputeGraph")
    if not isinstance(baseline_partition_plan, PartitionPlan):
        raise TypeError("baseline partition plan must be PartitionPlan")
    if not isinstance(candidate_partition_plan, PartitionPlan):
        raise TypeError("candidate partition plan must be PartitionPlan")
    if not isinstance(baseline_execution, RuntimeExecutionResult):
        raise TypeError("baseline execution must be RuntimeExecutionResult")
    if not isinstance(candidate_execution, RuntimeExecutionResult):
        raise TypeError("candidate execution must be RuntimeExecutionResult")
    _validate_equivalence_text(baseline_run_id, "baseline_run_id")
    _validate_equivalence_text(candidate_run_id, "candidate_run_id")
    if baseline_run_id == candidate_run_id:
        raise ValueError("runtime backend equivalence run IDs must be distinct")
    _validate_tolerance(rtol, "rtol")
    _validate_tolerance(atol, "atol")
    _validate_plan_execution(graph, baseline_partition_plan, baseline_execution)
    _validate_plan_execution(graph, candidate_partition_plan, candidate_execution)

    baseline_manifest = build_runtime_output_manifest_report(
        graph,
        baseline_execution,
    )
    candidate_manifest = build_runtime_output_manifest_report(
        graph,
        candidate_execution,
    )
    expected_outputs = baseline_manifest.expected_outputs
    runs = (
        _build_run(
            run_id=baseline_run_id,
            graph=graph,
            partition_plan=baseline_partition_plan,
            execution=baseline_execution,
            output_metadata_digest=baseline_manifest.output_metadata_digest,
            expected_outputs=expected_outputs,
        ),
        _build_run(
            run_id=candidate_run_id,
            graph=graph,
            partition_plan=candidate_partition_plan,
            execution=candidate_execution,
            output_metadata_digest=candidate_manifest.output_metadata_digest,
            expected_outputs=expected_outputs,
        ),
    )
    comparisons = tuple(
        _build_comparison(
            expected=expected,
            baseline_run_id=baseline_run_id,
            baseline_execution=baseline_execution,
            candidate_run_id=candidate_run_id,
            candidate_execution=candidate_execution,
            rtol=rtol,
            atol=atol,
        )
        for expected in expected_outputs
    )
    return RuntimeBackendEquivalenceReport(
        graph_name=graph.name,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        runs=runs,
        comparisons=comparisons,
        issues=_derive_issues(runs, comparisons, baseline_run_id, candidate_run_id),
    )


def assert_runtime_backend_equivalence(
    report: RuntimeBackendEquivalenceReport,
) -> RuntimeBackendEquivalenceReport:
    """Return the report or raise when backend equivalence evidence fails."""

    if not isinstance(report, RuntimeBackendEquivalenceReport):
        raise TypeError("runtime backend equivalence report must be report object")
    if report.issues:
        lines = [f"runtime backend equivalence failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeBackendEquivalenceError("\n".join(lines))
    return report


def runtime_backend_equivalence_report_to_dict(
    report: RuntimeBackendEquivalenceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible backend equivalence report."""

    if not isinstance(report, RuntimeBackendEquivalenceReport):
        raise TypeError("runtime backend equivalence report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "baseline_run_id": report.baseline_run_id,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_run_id": report.candidate_run_id,
        "comparison_count": len(report.comparisons),
        "comparison_metadata_digest": report.comparison_metadata_digest,
        "comparisons": [
            {
                "atol": comparison.atol,
                "baseline_dtype": comparison.baseline_dtype,
                "baseline_output_value_status": (
                    comparison.baseline_output_value_status
                ),
                "baseline_run_id": comparison.baseline_run_id,
                "baseline_shape": list(comparison.baseline_shape),
                "candidate_dtype": comparison.candidate_dtype,
                "candidate_output_value_status": (
                    comparison.candidate_output_value_status
                ),
                "candidate_run_id": comparison.candidate_run_id,
                "candidate_shape": list(comparison.candidate_shape),
                "comparison_status": comparison.comparison_status,
                "expected_dtype": comparison.expected_dtype,
                "expected_shape": list(comparison.expected_shape),
                "rtol": comparison.rtol,
                "tensor_name": comparison.tensor_name,
            }
            for comparison in report.comparisons
        ],
        "equivalence_contract": report.equivalence_contract,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "run_count": len(report.runs),
        "runs": [
            {
                "execution_status": run.execution_status,
                "graph_name": run.graph_name,
                "output_metadata_digest": run.output_metadata_digest,
                "output_tensor_names": list(run.output_tensor_names),
                "output_value_status": run.output_value_status,
                "planned_backend_sequence": list(run.planned_backend_sequence),
                "run_id": run.run_id,
                "tensor_record_count": run.tensor_record_count,
                "trace_step_count": run.trace_step_count,
            }
            for run in report.runs
        ],
        "schema_version": RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_backend_equivalence_report(
    report: RuntimeBackendEquivalenceReport,
) -> str:
    """Render stable data-only runtime backend equivalence evidence."""

    text = json.dumps(
        runtime_backend_equivalence_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_BACKEND_EQUIVALENCE_REPORT_BYTES:
        raise ValueError("runtime backend equivalence report exceeds byte limit")
    return text + "\n"


def _build_run(
    *,
    run_id: str,
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    execution: RuntimeExecutionResult,
    output_metadata_digest: str,
    expected_outputs: tuple[RuntimeExpectedOutput, ...],
) -> RuntimeBackendEquivalenceRun:
    return RuntimeBackendEquivalenceRun(
        run_id=run_id,
        graph_name=graph.name,
        planned_backend_sequence=tuple(
            assignment.backend_name for assignment in partition_plan.assignments
        ),
        output_tensor_names=tuple(output.tensor_name for output in expected_outputs),
        output_metadata_digest=output_metadata_digest,
        trace_step_count=len(execution.trace.steps),
        tensor_record_count=len(execution.records),
    )


def _build_comparison(
    *,
    expected: RuntimeExpectedOutput,
    baseline_run_id: str,
    baseline_execution: RuntimeExecutionResult,
    candidate_run_id: str,
    candidate_execution: RuntimeExecutionResult,
    rtol: float,
    atol: float,
) -> RuntimeBackendEquivalenceComparison:
    baseline = _output_or_missing(baseline_execution, expected.tensor_name)
    candidate = _output_or_missing(candidate_execution, expected.tensor_name)
    status = _comparison_status(
        expected=expected,
        baseline=baseline,
        candidate=candidate,
        rtol=rtol,
        atol=atol,
    )
    return RuntimeBackendEquivalenceComparison(
        tensor_name=expected.tensor_name,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        expected_shape=expected.shape,
        expected_dtype=expected.dtype,
        baseline_shape=_shape_for_output(baseline),
        baseline_dtype=_dtype_for_output(baseline),
        candidate_shape=_shape_for_output(candidate),
        candidate_dtype=_dtype_for_output(candidate),
        rtol=rtol,
        atol=atol,
        comparison_status=status,
    )


def _comparison_status(
    *,
    expected: RuntimeExpectedOutput,
    baseline: object,
    candidate: object,
    rtol: float,
    atol: float,
) -> str:
    if baseline is _MISSING:
        return "missing_baseline_output"
    if candidate is _MISSING:
        return "missing_candidate_output"
    if not isinstance(baseline, np.ndarray) or not _output_is_valid(baseline, expected):
        return "invalid_baseline_output"
    if not isinstance(candidate, np.ndarray) or not _output_is_valid(candidate, expected):
        return "invalid_candidate_output"
    return (
        "matched"
        if bool(np.allclose(baseline, candidate, rtol=rtol, atol=atol))
        else "mismatched"
    )


_MISSING = object()


def _output_or_missing(execution: RuntimeExecutionResult, tensor_name: str) -> object:
    try:
        return execution.output_for(tensor_name)
    except KeyError:
        return _MISSING


def _shape_for_output(value: object) -> tuple[int, ...]:
    if value is _MISSING:
        return ()
    if not isinstance(value, np.ndarray):
        return ()
    return tuple(int(dimension) for dimension in value.shape)


def _dtype_for_output(value: object) -> str:
    if value is _MISSING:
        return "missing"
    if not isinstance(value, np.ndarray):
        return "invalid"
    return str(value.dtype)


def _output_is_valid(
    value: NDArray[np.generic],
    expected: RuntimeExpectedOutput,
) -> bool:
    return (
        tuple(value.shape) == expected.shape
        and value.dtype == np.dtype(np.float64)
        and bool(np.all(np.isfinite(value)))
    )


def _derive_issues(
    runs: tuple[RuntimeBackendEquivalenceRun, ...],
    comparisons: tuple[RuntimeBackendEquivalenceComparison, ...],
    baseline_run_id: str,
    candidate_run_id: str,
) -> tuple[RuntimeBackendEquivalenceIssue, ...]:
    issues: list[RuntimeBackendEquivalenceIssue] = []
    run_by_id = {run.run_id: run for run in runs}
    baseline = run_by_id[baseline_run_id]
    candidate = run_by_id[candidate_run_id]
    if baseline.planned_backend_sequence == candidate.planned_backend_sequence:
        issues.append(
            RuntimeBackendEquivalenceIssue(
                subject="backend_sequence",
                issue_code="backend_sequences_not_distinct",
            )
        )
    if baseline.output_metadata_digest != candidate.output_metadata_digest:
        issues.append(
            RuntimeBackendEquivalenceIssue(
                subject="output_metadata_digest",
                issue_code="output_metadata_digest_mismatch",
            )
        )
    for comparison in comparisons:
        if comparison.comparison_status != "matched":
            issues.append(
                RuntimeBackendEquivalenceIssue(
                    subject=comparison.tensor_name,
                    issue_code=comparison.comparison_status,
                )
            )
    return tuple(issues)


def _validate_plan_execution(
    graph: ComputeGraph,
    partition_plan: PartitionPlan,
    execution: RuntimeExecutionResult,
) -> None:
    if partition_plan.graph_name != graph.name:
        raise ValueError("runtime backend equivalence partition plan graph mismatch")
    if execution.trace.graph_name != graph.name:
        raise ValueError("runtime backend equivalence execution graph mismatch")
    operation_names = tuple(operation.name for operation in graph.operations)
    assignment_names = tuple(assignment.operation_name for assignment in partition_plan.assignments)
    if assignment_names != operation_names:
        raise ValueError("runtime backend equivalence partition plan operation mismatch")
    if len(execution.trace.steps) != len(graph.operations):
        raise ValueError("runtime backend equivalence trace step count mismatch")


def _validate_runs(
    runs: tuple[RuntimeBackendEquivalenceRun, ...],
    graph_name: str,
    baseline_run_id: str,
    candidate_run_id: str,
) -> None:
    if type(runs) is not tuple:
        raise TypeError("runtime backend equivalence runs must be a tuple")
    if len(runs) != MAX_RUNTIME_BACKEND_EQUIVALENCE_RUNS:
        raise ValueError("runtime backend equivalence requires exactly two runs")
    run_ids: list[str] = []
    for run in runs:
        if not isinstance(run, RuntimeBackendEquivalenceRun):
            raise TypeError("runtime backend equivalence runs must be run objects")
        if run.graph_name != graph_name:
            raise ValueError("runtime backend equivalence run graph mismatch")
        run_ids.append(run.run_id)
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("runtime backend equivalence run IDs must be unique")
    if set(run_ids) != {baseline_run_id, candidate_run_id}:
        raise ValueError("runtime backend equivalence runs must match report IDs")


def _validate_comparisons(
    comparisons: tuple[RuntimeBackendEquivalenceComparison, ...],
    baseline_run_id: str,
    candidate_run_id: str,
) -> None:
    if type(comparisons) is not tuple:
        raise TypeError("runtime backend equivalence comparisons must be a tuple")
    if not comparisons:
        raise ValueError("runtime backend equivalence comparisons must not be empty")
    if len(comparisons) > MAX_RUNTIME_BACKEND_EQUIVALENCE_COMPARISONS:
        raise ValueError("runtime backend equivalence comparison count exceeds limit")
    tensor_names: list[str] = []
    for comparison in comparisons:
        if not isinstance(comparison, RuntimeBackendEquivalenceComparison):
            raise TypeError(
                "runtime backend equivalence comparisons must be comparison objects"
            )
        if comparison.baseline_run_id != baseline_run_id:
            raise ValueError("runtime backend equivalence baseline comparison mismatch")
        if comparison.candidate_run_id != candidate_run_id:
            raise ValueError("runtime backend equivalence candidate comparison mismatch")
        tensor_names.append(comparison.tensor_name)
    if len(tensor_names) != len(set(tensor_names)):
        raise ValueError("runtime backend equivalence comparison names must be unique")


def _validate_text_sequence(value: tuple[str, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"runtime backend equivalence {label} must be non-empty tuple")
    for item in value:
        _validate_equivalence_text(item, label)


def _validate_positive_count(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"runtime backend equivalence {label} must be positive")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"runtime backend equivalence {label} must be sha256 digest")


def _validate_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"runtime backend equivalence {label} must be non-empty tuple")
    _validate_shape_dimensions(value, label)


def _validate_shape_or_empty(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple:
        raise ValueError(f"runtime backend equivalence {label} must be a tuple")
    if value:
        _validate_shape_dimensions(value, label)


def _validate_shape_dimensions(value: tuple[int, ...], label: str) -> None:
    if len(value) > MAX_TENSOR_RANK:
        raise ValueError(f"runtime backend equivalence {label} exceeds rank limit")
    for dimension in value:
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
            or dimension > MAX_TENSOR_DIMENSION
        ):
            raise ValueError(
                f"runtime backend equivalence {label} must contain bounded positive integers"
            )


def _validate_concrete_dtype(value: str, label: str) -> None:
    if value in _SPECIAL_DTYPES:
        raise ValueError(f"runtime backend equivalence {label} must be concrete")
    _validate_equivalence_text(value, label)


def _validate_dtype_or_status(value: str, label: str) -> None:
    if value in _SPECIAL_DTYPES:
        return
    _validate_equivalence_text(value, label)


def _validate_tolerance(value: float, label: str) -> None:
    if (
        not isinstance(value, float)
        or isinstance(value, bool)
        or not isfinite(value)
        or value < 0
        or value > RUNTIME_BACKEND_EQUIVALENCE_MAX_TOLERANCE
    ):
        raise ValueError(f"runtime backend equivalence {label} must be bounded")


def _validate_equivalence_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _EQUIVALENCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime backend equivalence identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_BACKEND_EQUIVALENCE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime backend equivalence field limit")
    if value in _FORBIDDEN_EQUIVALENCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_COMPARISONS",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_FIELD_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_ISSUES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_REPORT_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_RUNS",
    "RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS",
    "RUNTIME_BACKEND_EQUIVALENCE_CONTRACT",
    "RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_ATOL",
    "RUNTIME_BACKEND_EQUIVALENCE_DEFAULT_RTOL",
    "RUNTIME_BACKEND_EQUIVALENCE_MAX_TOLERANCE",
    "RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION",
    "RuntimeBackendEquivalenceComparison",
    "RuntimeBackendEquivalenceError",
    "RuntimeBackendEquivalenceIssue",
    "RuntimeBackendEquivalenceReport",
    "RuntimeBackendEquivalenceRun",
    "assert_runtime_backend_equivalence",
    "build_runtime_backend_equivalence_report",
    "dump_runtime_backend_equivalence_report",
    "runtime_backend_equivalence_report_to_dict",
]
