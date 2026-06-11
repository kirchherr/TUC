"""Data-only runtime output manifest for terminal graph outputs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.model import (
    MAX_TENSOR_DIMENSION,
    MAX_TENSOR_RANK,
    ComputeGraph,
)
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_CONTRACT,
    RUNTIME_VALUE_RECORD_CONTRACT,
    RuntimeExecutionResult,
    RuntimeValueRecord,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RUNTIME_TENSOR_STORE_RUNTIME_DTYPE,
)

RUNTIME_OUTPUT_MANIFEST_REPORT_SCHEMA_VERSION = "tuc.runtime_output_manifest_report.v0"
RUNTIME_OUTPUT_MANIFEST_CONTRACT = "runtime_output_manifest.data_only.v0"
RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS = "review_evidence"
RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY = "graph_terminal_outputs"
MAX_RUNTIME_OUTPUT_MANIFEST_OUTPUTS = 4096
MAX_RUNTIME_OUTPUT_MANIFEST_ISSUES = 256
MAX_RUNTIME_OUTPUT_MANIFEST_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_OUTPUT_MANIFEST_FIELD_BYTES = 512

_OUTPUT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_VALUE_ROLES = frozenset({"input", "computed"})
_PRODUCER_KINDS = frozenset({"external_input", "operation"})
_FORBIDDEN_OUTPUT_TEXT = frozenset(
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
        "source_text",
        "subprocess",
        "tensor_value",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeExpectedOutput:
    """Terminal graph output expected from runtime execution."""

    tensor_name: str
    shape: tuple[int, ...]
    dtype: str
    producer_kind: str
    producer_id: str
    value_role: str = "computed"

    def __post_init__(self) -> None:
        _validate_output_text(self.tensor_name, "expected output tensor_name")
        _validate_shape(self.shape, "expected output shape")
        _validate_output_text(self.dtype, "expected output dtype")
        if self.value_role != "computed":
            raise ValueError("runtime expected output value role must be computed")
        if self.producer_kind != "operation":
            raise ValueError("runtime expected output producer must be operation")
        _validate_output_text(self.producer_id, "expected output producer_id")


@dataclass(frozen=True)
class RuntimeOutputRecord:
    """Terminal output metadata that intentionally excludes tensor contents."""

    tensor_name: str
    shape: tuple[int, ...]
    dtype: str
    value_role: str
    producer_kind: str
    producer_id: str
    readonly: bool
    record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT
    raw_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_output_text(self.tensor_name, "output tensor_name")
        _validate_shape(self.shape, "output shape")
        _validate_output_text(self.dtype, "output dtype")
        _validate_value_role(self.value_role)
        _validate_producer(self.value_role, self.producer_kind, self.producer_id)
        if not isinstance(self.readonly, bool):
            raise TypeError("runtime output readonly must be bool")
        if self.record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime output record contract mismatch")
        if self.raw_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime output manifest must omit raw values")


@dataclass(frozen=True)
class RuntimeOutputManifestIssue:
    """One derived runtime output manifest issue."""

    tensor_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_output_text(self.tensor_name, "output issue tensor_name")
        _validate_output_text(self.issue_code, "output issue_code")


@dataclass(frozen=True)
class RuntimeOutputManifestReport:
    """Deterministic, data-only manifest for terminal runtime outputs."""

    graph_name: str
    expected_outputs: tuple[RuntimeExpectedOutput, ...]
    outputs: tuple[RuntimeOutputRecord, ...]
    issues: tuple[RuntimeOutputManifestIssue, ...]
    manifest_contract: str = RUNTIME_OUTPUT_MANIFEST_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    store_contract: str = RUNTIME_TENSOR_STORE_CONTRACT
    value_record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT
    artifact_status: str = RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS
    terminal_output_policy: str = RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_output_text(self.graph_name, "runtime output graph_name")
        if self.manifest_contract != RUNTIME_OUTPUT_MANIFEST_CONTRACT:
            raise ValueError("runtime output manifest contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime output executor contract mismatch")
        if self.store_contract != RUNTIME_TENSOR_STORE_CONTRACT:
            raise ValueError("runtime output store contract mismatch")
        if self.value_record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime output value record contract mismatch")
        if self.artifact_status != RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS:
            raise ValueError("runtime output artifact status mismatch")
        if self.terminal_output_policy != RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY:
            raise ValueError("runtime output terminal policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime output manifest must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime output blocked execution surfaces changed")
        _validate_expected_outputs(self.expected_outputs)
        _validate_output_records(self.outputs)
        if type(self.issues) is not tuple:
            raise TypeError("runtime output manifest issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_OUTPUT_MANIFEST_ISSUES:
            raise ValueError("runtime output manifest issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeOutputManifestIssue):
                raise TypeError(
                    "runtime output manifest issues must be output manifest issues"
                )
        expected_issues = _derive_issues(self.expected_outputs, self.outputs)
        if self.issues != expected_issues:
            raise ValueError("runtime output manifest issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the runtime output manifest passed."""

        return not self.issues

    @property
    def output_metadata_digest(self) -> str:
        """Return a digest over terminal output metadata only."""

        payload = [
            {
                "dtype": output.dtype,
                "producer_id": output.producer_id,
                "producer_kind": output.producer_kind,
                "raw_value_status": output.raw_value_status,
                "readonly": output.readonly,
                "shape": list(output.shape),
                "tensor_name": output.tensor_name,
                "value_role": output.value_role,
            }
            for output in self.outputs
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeOutputManifestError(AssertionError):
    """Raised when runtime output manifest evidence does not pass."""


def build_runtime_output_manifest_report(
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
) -> RuntimeOutputManifestReport:
    """Build data-only output manifest evidence from an executed graph."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime output manifest graph must be ComputeGraph")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("runtime output manifest execution must be RuntimeExecutionResult")
    expected_outputs = _expected_outputs_for_graph(graph)
    records_by_name = {record.tensor_name: record for record in execution.records}
    outputs = tuple(
        _record_to_output(record)
        for expected in expected_outputs
        for record in (records_by_name.get(expected.tensor_name),)
        if record is not None
    )
    return RuntimeOutputManifestReport(
        graph_name=graph.name,
        expected_outputs=expected_outputs,
        outputs=outputs,
        issues=_derive_issues(expected_outputs, outputs),
    )


def assert_runtime_output_manifest(
    report: RuntimeOutputManifestReport,
) -> RuntimeOutputManifestReport:
    """Return the report or raise when runtime output evidence fails."""

    if not isinstance(report, RuntimeOutputManifestReport):
        raise TypeError("runtime output manifest report must be report object")
    if report.issues:
        lines = [f"runtime output manifest failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeOutputManifestError("\n".join(lines))
    return report


def runtime_output_manifest_report_to_dict(
    report: RuntimeOutputManifestReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible output manifest report."""

    if not isinstance(report, RuntimeOutputManifestReport):
        raise TypeError("runtime output manifest report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "executor_contract": report.executor_contract,
        "expected_output_count": len(report.expected_outputs),
        "expected_outputs": [
            {
                "dtype": output.dtype,
                "producer_id": output.producer_id,
                "producer_kind": output.producer_kind,
                "shape": list(output.shape),
                "tensor_name": output.tensor_name,
                "value_role": output.value_role,
            }
            for output in report.expected_outputs
        ],
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "tensor_name": issue.tensor_name,
            }
            for issue in report.issues
        ],
        "manifest_contract": report.manifest_contract,
        "output_count": len(report.outputs),
        "output_metadata_digest": report.output_metadata_digest,
        "outputs": [
            {
                "dtype": output.dtype,
                "producer_id": output.producer_id,
                "producer_kind": output.producer_kind,
                "raw_value_status": output.raw_value_status,
                "readonly": output.readonly,
                "record_contract": output.record_contract,
                "shape": list(output.shape),
                "tensor_name": output.tensor_name,
                "value_role": output.value_role,
            }
            for output in report.outputs
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "schema_version": RUNTIME_OUTPUT_MANIFEST_REPORT_SCHEMA_VERSION,
        "store_contract": report.store_contract,
        "terminal_output_policy": report.terminal_output_policy,
        "value_record_contract": report.value_record_contract,
    }


def dump_runtime_output_manifest_report(report: RuntimeOutputManifestReport) -> str:
    """Render stable data-only runtime output manifest evidence."""

    text = json.dumps(
        runtime_output_manifest_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_OUTPUT_MANIFEST_REPORT_BYTES:
        raise ValueError("runtime output manifest report exceeds byte limit")
    return text + "\n"


def _expected_outputs_for_graph(
    graph: ComputeGraph,
) -> tuple[RuntimeExpectedOutput, ...]:
    consumed = {tensor.name for operation in graph.operations for tensor in operation.inputs}
    expected: list[RuntimeExpectedOutput] = []
    for operation in graph.operations:
        for tensor in operation.outputs:
            if tensor.name not in consumed:
                expected.append(
                    RuntimeExpectedOutput(
                        tensor_name=tensor.name,
                        shape=tensor.shape,
                        dtype=RUNTIME_TENSOR_STORE_RUNTIME_DTYPE,
                        producer_kind="operation",
                        producer_id=operation.name,
                    )
                )
    if not expected:
        raise ValueError("runtime output manifest graph has no terminal outputs")
    return tuple(expected)


def _record_to_output(record: RuntimeValueRecord) -> RuntimeOutputRecord:
    if not isinstance(record, RuntimeValueRecord):
        raise TypeError("runtime output manifest records must be value records")
    return RuntimeOutputRecord(
        tensor_name=record.tensor_name,
        shape=record.shape,
        dtype=record.dtype,
        value_role=record.value_role,
        producer_kind=record.producer_kind,
        producer_id=record.producer_id,
        readonly=not record.value.flags.writeable,
    )


def _derive_issues(
    expected_outputs: tuple[RuntimeExpectedOutput, ...],
    outputs: tuple[RuntimeOutputRecord, ...],
) -> tuple[RuntimeOutputManifestIssue, ...]:
    expected_by_name = {output.tensor_name: output for output in expected_outputs}
    outputs_by_name = {output.tensor_name: output for output in outputs}
    issues: list[RuntimeOutputManifestIssue] = []

    for tensor_name in sorted(expected_by_name):
        expected = expected_by_name[tensor_name]
        output = outputs_by_name.get(tensor_name)
        if output is None:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="expected_output_missing",
                )
            )
            continue
        if output.shape != expected.shape:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="shape_mismatch",
                )
            )
        if output.dtype != expected.dtype:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="dtype_mismatch",
                )
            )
        if output.value_role != expected.value_role:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="value_role_mismatch",
                )
            )
        if output.producer_kind != expected.producer_kind:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="producer_kind_mismatch",
                )
            )
        if output.producer_id != expected.producer_id:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="producer_id_mismatch",
                )
            )
        if not output.readonly:
            issues.append(
                RuntimeOutputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="record_value_mutable",
                )
            )

    for tensor_name in sorted(set(outputs_by_name) - set(expected_by_name)):
        issues.append(
            RuntimeOutputManifestIssue(
                tensor_name=tensor_name,
                issue_code="unexpected_output",
            )
        )

    return tuple(issues)


def _validate_expected_outputs(records: tuple[RuntimeExpectedOutput, ...]) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime output manifest expected outputs must be a tuple")
    if not records:
        raise ValueError("runtime output manifest expected outputs must not be empty")
    _validate_output_count(len(records))
    names: list[str] = []
    for record in records:
        if not isinstance(record, RuntimeExpectedOutput):
            raise TypeError(
                "runtime output manifest expected outputs must be expected outputs"
            )
        names.append(record.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime output manifest expected output names must be unique")


def _validate_output_records(records: tuple[RuntimeOutputRecord, ...]) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime output manifest records must be a tuple")
    _validate_output_count(len(records))
    names: list[str] = []
    for record in records:
        if not isinstance(record, RuntimeOutputRecord):
            raise TypeError("runtime output manifest records must be output records")
        names.append(record.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime output manifest record names must be unique")


def _validate_output_count(count: int) -> None:
    if count > MAX_RUNTIME_OUTPUT_MANIFEST_OUTPUTS:
        raise ValueError("runtime output manifest output count exceeds limit")


def _validate_value_role(value: str) -> None:
    if value not in _VALUE_ROLES:
        raise ValueError("runtime output manifest value role unsupported")


def _validate_producer(value_role: str, producer_kind: str, producer_id: str) -> None:
    if producer_kind not in _PRODUCER_KINDS:
        raise ValueError("runtime output manifest producer kind unsupported")
    _validate_output_text(producer_id, "producer_id")
    if value_role == "input" and producer_kind != "external_input":
        raise ValueError("runtime output manifest input producer must be external_input")
    if value_role == "computed" and producer_kind != "operation":
        raise ValueError("runtime output manifest computed producer must be operation")


def _validate_shape(value: tuple[int, ...], label: str) -> None:
    if type(value) is not tuple or not value:
        raise ValueError(f"{label} must be a non-empty tuple")
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


def _validate_output_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _OUTPUT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime output identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_OUTPUT_MANIFEST_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime output manifest field limit")
    if value in _FORBIDDEN_OUTPUT_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_OUTPUT_MANIFEST_FIELD_BYTES",
    "MAX_RUNTIME_OUTPUT_MANIFEST_ISSUES",
    "MAX_RUNTIME_OUTPUT_MANIFEST_OUTPUTS",
    "MAX_RUNTIME_OUTPUT_MANIFEST_REPORT_BYTES",
    "RUNTIME_OUTPUT_MANIFEST_ARTIFACT_STATUS",
    "RUNTIME_OUTPUT_MANIFEST_CONTRACT",
    "RUNTIME_OUTPUT_MANIFEST_REPORT_SCHEMA_VERSION",
    "RUNTIME_OUTPUT_MANIFEST_TERMINAL_OUTPUT_POLICY",
    "RuntimeExpectedOutput",
    "RuntimeOutputManifestError",
    "RuntimeOutputManifestIssue",
    "RuntimeOutputManifestReport",
    "RuntimeOutputRecord",
    "assert_runtime_output_manifest",
    "build_runtime_output_manifest_report",
    "dump_runtime_output_manifest_report",
    "runtime_output_manifest_report_to_dict",
]
