"""Data-only runtime input manifest for graph external inputs."""

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
    TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT,
    RuntimeExecutionResult,
    RuntimeValueRecord,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RUNTIME_TENSOR_STORE_RUNTIME_DTYPE,
)

RUNTIME_INPUT_MANIFEST_REPORT_SCHEMA_VERSION = "tuc.runtime_input_manifest_report.v0"
RUNTIME_INPUT_MANIFEST_CONTRACT = "runtime_input_manifest.data_only.v0"
RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS = "review_evidence"
RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY = "graph_external_inputs"
MAX_RUNTIME_INPUT_MANIFEST_INPUTS = 4096
MAX_RUNTIME_INPUT_MANIFEST_ISSUES = 256
MAX_RUNTIME_INPUT_MANIFEST_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_INPUT_MANIFEST_FIELD_BYTES = 512

_INPUT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_VALUE_ROLES = frozenset({"input", "computed"})
_PRODUCER_KINDS = frozenset({"external_input", "operation"})
_FORBIDDEN_INPUT_TEXT = frozenset(
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
        "input_value",
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
class RuntimeExpectedInput:
    """External graph input expected by runtime execution."""

    tensor_name: str
    shape: tuple[int, ...]
    dtype: str
    producer_kind: str
    producer_id: str
    value_role: str = "input"

    def __post_init__(self) -> None:
        _validate_input_text(self.tensor_name, "expected input tensor_name")
        _validate_shape(self.shape, "expected input shape")
        _validate_input_text(self.dtype, "expected input dtype")
        if self.value_role != "input":
            raise ValueError("runtime expected input value role must be input")
        if self.producer_kind != "external_input":
            raise ValueError("runtime expected input producer must be external_input")
        _validate_input_text(self.producer_id, "expected input producer_id")
        if self.producer_id != self.tensor_name:
            raise ValueError("runtime expected input producer_id must match tensor_name")


@dataclass(frozen=True)
class RuntimeInputRecord:
    """External input metadata that intentionally excludes tensor contents."""

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
        _validate_input_text(self.tensor_name, "input tensor_name")
        _validate_shape(self.shape, "input shape")
        _validate_input_text(self.dtype, "input dtype")
        _validate_value_role(self.value_role)
        _validate_producer(self.value_role, self.producer_kind, self.producer_id)
        if not isinstance(self.readonly, bool):
            raise TypeError("runtime input readonly must be bool")
        if self.record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime input record contract mismatch")
        if self.raw_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime input manifest must omit raw values")


@dataclass(frozen=True)
class RuntimeInputManifestIssue:
    """One derived runtime input manifest issue."""

    tensor_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_input_text(self.tensor_name, "input issue tensor_name")
        _validate_input_text(self.issue_code, "input issue_code")


@dataclass(frozen=True)
class RuntimeInputManifestReport:
    """Deterministic, data-only manifest for runtime external inputs."""

    graph_name: str
    expected_inputs: tuple[RuntimeExpectedInput, ...]
    inputs: tuple[RuntimeInputRecord, ...]
    issues: tuple[RuntimeInputManifestIssue, ...]
    manifest_contract: str = RUNTIME_INPUT_MANIFEST_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    input_contract: str = TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT
    store_contract: str = RUNTIME_TENSOR_STORE_CONTRACT
    value_record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT
    artifact_status: str = RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS
    external_input_policy: str = RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_input_text(self.graph_name, "runtime input graph_name")
        if self.manifest_contract != RUNTIME_INPUT_MANIFEST_CONTRACT:
            raise ValueError("runtime input manifest contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime input executor contract mismatch")
        if self.input_contract != TRUSTED_RUNTIME_BACKEND_INPUT_CONTRACT:
            raise ValueError("runtime input contract mismatch")
        if self.store_contract != RUNTIME_TENSOR_STORE_CONTRACT:
            raise ValueError("runtime input store contract mismatch")
        if self.value_record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime input value record contract mismatch")
        if self.artifact_status != RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS:
            raise ValueError("runtime input artifact status mismatch")
        if self.external_input_policy != RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY:
            raise ValueError("runtime input external input policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime input manifest must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime input blocked execution surfaces changed")
        _validate_expected_inputs(self.expected_inputs)
        _validate_input_records(self.inputs)
        if type(self.issues) is not tuple:
            raise TypeError("runtime input manifest issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_INPUT_MANIFEST_ISSUES:
            raise ValueError("runtime input manifest issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeInputManifestIssue):
                raise TypeError(
                    "runtime input manifest issues must be input manifest issues"
                )
        expected_issues = _derive_issues(self.expected_inputs, self.inputs)
        if self.issues != expected_issues:
            raise ValueError("runtime input manifest issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the runtime input manifest passed."""

        return not self.issues

    @property
    def input_metadata_digest(self) -> str:
        """Return a digest over external input metadata only."""

        payload = [
            {
                "dtype": input_record.dtype,
                "producer_id": input_record.producer_id,
                "producer_kind": input_record.producer_kind,
                "raw_value_status": input_record.raw_value_status,
                "readonly": input_record.readonly,
                "shape": list(input_record.shape),
                "tensor_name": input_record.tensor_name,
                "value_role": input_record.value_role,
            }
            for input_record in self.inputs
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeInputManifestError(AssertionError):
    """Raised when runtime input manifest evidence does not pass."""


def build_runtime_input_manifest_report(
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
) -> RuntimeInputManifestReport:
    """Build data-only input manifest evidence from an executed graph."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime input manifest graph must be ComputeGraph")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("runtime input manifest execution must be RuntimeExecutionResult")
    expected_inputs = _expected_inputs_for_graph(graph)
    records_by_name = {record.tensor_name: record for record in execution.records}
    inputs = tuple(
        _record_to_input(record)
        for expected in expected_inputs
        for record in (records_by_name.get(expected.tensor_name),)
        if record is not None
    )
    return RuntimeInputManifestReport(
        graph_name=graph.name,
        expected_inputs=expected_inputs,
        inputs=inputs,
        issues=_derive_issues(expected_inputs, inputs),
    )


def assert_runtime_input_manifest(
    report: RuntimeInputManifestReport,
) -> RuntimeInputManifestReport:
    """Return the report or raise when runtime input evidence fails."""

    if not isinstance(report, RuntimeInputManifestReport):
        raise TypeError("runtime input manifest report must be report object")
    if report.issues:
        lines = [f"runtime input manifest failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeInputManifestError("\n".join(lines))
    return report


def runtime_input_manifest_report_to_dict(
    report: RuntimeInputManifestReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible input manifest report."""

    if not isinstance(report, RuntimeInputManifestReport):
        raise TypeError("runtime input manifest report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "executor_contract": report.executor_contract,
        "expected_input_count": len(report.expected_inputs),
        "expected_inputs": [
            {
                "dtype": input_record.dtype,
                "producer_id": input_record.producer_id,
                "producer_kind": input_record.producer_kind,
                "shape": list(input_record.shape),
                "tensor_name": input_record.tensor_name,
                "value_role": input_record.value_role,
            }
            for input_record in report.expected_inputs
        ],
        "external_input_policy": report.external_input_policy,
        "graph_name": report.graph_name,
        "input_contract": report.input_contract,
        "input_count": len(report.inputs),
        "input_metadata_digest": report.input_metadata_digest,
        "inputs": [
            {
                "dtype": input_record.dtype,
                "producer_id": input_record.producer_id,
                "producer_kind": input_record.producer_kind,
                "raw_value_status": input_record.raw_value_status,
                "readonly": input_record.readonly,
                "record_contract": input_record.record_contract,
                "shape": list(input_record.shape),
                "tensor_name": input_record.tensor_name,
                "value_role": input_record.value_role,
            }
            for input_record in report.inputs
        ],
        "issues": [
            {
                "issue_code": issue.issue_code,
                "tensor_name": issue.tensor_name,
            }
            for issue in report.issues
        ],
        "manifest_contract": report.manifest_contract,
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "schema_version": RUNTIME_INPUT_MANIFEST_REPORT_SCHEMA_VERSION,
        "store_contract": report.store_contract,
        "value_record_contract": report.value_record_contract,
    }


def dump_runtime_input_manifest_report(report: RuntimeInputManifestReport) -> str:
    """Render stable data-only runtime input manifest evidence."""

    text = json.dumps(
        runtime_input_manifest_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_INPUT_MANIFEST_REPORT_BYTES:
        raise ValueError("runtime input manifest report exceeds byte limit")
    return text + "\n"


def _expected_inputs_for_graph(
    graph: ComputeGraph,
) -> tuple[RuntimeExpectedInput, ...]:
    produced: set[str] = set()
    expected_by_name = {}
    for operation in graph.operations:
        for tensor in operation.inputs:
            if tensor.name not in produced and tensor.name not in expected_by_name:
                expected_by_name[tensor.name] = tensor
        for tensor in operation.outputs:
            produced.add(tensor.name)
    if not expected_by_name:
        raise ValueError("runtime input manifest graph has no external inputs")
    return tuple(
        RuntimeExpectedInput(
            tensor_name=tensor.name,
            shape=tensor.shape,
            dtype=RUNTIME_TENSOR_STORE_RUNTIME_DTYPE,
            producer_kind="external_input",
            producer_id=tensor.name,
        )
        for tensor in expected_by_name.values()
    )


def _record_to_input(record: RuntimeValueRecord) -> RuntimeInputRecord:
    if not isinstance(record, RuntimeValueRecord):
        raise TypeError("runtime input manifest records must be value records")
    return RuntimeInputRecord(
        tensor_name=record.tensor_name,
        shape=record.shape,
        dtype=record.dtype,
        value_role=record.value_role,
        producer_kind=record.producer_kind,
        producer_id=record.producer_id,
        readonly=not record.value.flags.writeable,
    )


def _derive_issues(
    expected_inputs: tuple[RuntimeExpectedInput, ...],
    inputs: tuple[RuntimeInputRecord, ...],
) -> tuple[RuntimeInputManifestIssue, ...]:
    expected_by_name = {input_record.tensor_name: input_record for input_record in expected_inputs}
    inputs_by_name = {input_record.tensor_name: input_record for input_record in inputs}
    issues: list[RuntimeInputManifestIssue] = []

    for tensor_name in sorted(expected_by_name):
        expected = expected_by_name[tensor_name]
        input_record = inputs_by_name.get(tensor_name)
        if input_record is None:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="expected_input_missing",
                )
            )
            continue
        if input_record.shape != expected.shape:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="shape_mismatch",
                )
            )
        if input_record.dtype != expected.dtype:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="dtype_mismatch",
                )
            )
        if input_record.value_role != expected.value_role:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="value_role_mismatch",
                )
            )
        if input_record.producer_kind != expected.producer_kind:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="producer_kind_mismatch",
                )
            )
        if input_record.producer_id != expected.producer_id:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="producer_id_mismatch",
                )
            )
        if not input_record.readonly:
            issues.append(
                RuntimeInputManifestIssue(
                    tensor_name=tensor_name,
                    issue_code="record_value_mutable",
                )
            )

    for tensor_name in sorted(set(inputs_by_name) - set(expected_by_name)):
        issues.append(
            RuntimeInputManifestIssue(
                tensor_name=tensor_name,
                issue_code="unexpected_input",
            )
        )

    return tuple(issues)


def _validate_expected_inputs(records: tuple[RuntimeExpectedInput, ...]) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime input manifest expected inputs must be a tuple")
    if not records:
        raise ValueError("runtime input manifest expected inputs must not be empty")
    _validate_input_count(len(records))
    names: list[str] = []
    for record in records:
        if not isinstance(record, RuntimeExpectedInput):
            raise TypeError(
                "runtime input manifest expected inputs must be expected inputs"
            )
        names.append(record.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime input manifest expected input names must be unique")


def _validate_input_records(records: tuple[RuntimeInputRecord, ...]) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime input manifest records must be a tuple")
    _validate_input_count(len(records))
    names: list[str] = []
    for record in records:
        if not isinstance(record, RuntimeInputRecord):
            raise TypeError("runtime input manifest records must be input records")
        names.append(record.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime input manifest record names must be unique")


def _validate_input_count(count: int) -> None:
    if count > MAX_RUNTIME_INPUT_MANIFEST_INPUTS:
        raise ValueError("runtime input manifest input count exceeds limit")


def _validate_value_role(value: str) -> None:
    if value not in _VALUE_ROLES:
        raise ValueError("runtime input manifest value role unsupported")


def _validate_producer(value_role: str, producer_kind: str, producer_id: str) -> None:
    if producer_kind not in _PRODUCER_KINDS:
        raise ValueError("runtime input manifest producer kind unsupported")
    _validate_input_text(producer_id, "producer_id")
    if value_role == "input" and producer_kind != "external_input":
        raise ValueError("runtime input manifest input producer must be external_input")
    if value_role == "computed" and producer_kind != "operation":
        raise ValueError("runtime input manifest computed producer must be operation")


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


def _validate_input_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _INPUT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime input identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_INPUT_MANIFEST_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime input manifest field limit")
    if value in _FORBIDDEN_INPUT_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_INPUT_MANIFEST_FIELD_BYTES",
    "MAX_RUNTIME_INPUT_MANIFEST_INPUTS",
    "MAX_RUNTIME_INPUT_MANIFEST_ISSUES",
    "MAX_RUNTIME_INPUT_MANIFEST_REPORT_BYTES",
    "RUNTIME_INPUT_MANIFEST_ARTIFACT_STATUS",
    "RUNTIME_INPUT_MANIFEST_CONTRACT",
    "RUNTIME_INPUT_MANIFEST_EXTERNAL_INPUT_POLICY",
    "RUNTIME_INPUT_MANIFEST_REPORT_SCHEMA_VERSION",
    "RuntimeExpectedInput",
    "RuntimeInputManifestError",
    "RuntimeInputManifestIssue",
    "RuntimeInputManifestReport",
    "RuntimeInputRecord",
    "assert_runtime_input_manifest",
    "build_runtime_input_manifest_report",
    "dump_runtime_input_manifest_report",
    "runtime_input_manifest_report_to_dict",
]
