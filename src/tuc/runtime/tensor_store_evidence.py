"""Data-only evidence for Runtime Tensor Store value records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.model import (
    MAX_TENSOR_DIMENSION,
    MAX_TENSOR_RANK,
    ComputeGraph,
    TensorRef,
)
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_TENSOR_STORE_CONTRACT,
    RUNTIME_VALUE_RECORD_CONTRACT,
    RuntimeExecutionResult,
    RuntimeValueRecord,
)

RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_tensor_store_evidence_report.v0"
)
RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT = "runtime_tensor_store_evidence.data_only.v0"
RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS = "review_evidence"
RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS = "omitted_by_policy"
RUNTIME_TENSOR_STORE_RUNTIME_DTYPE = "float64"
MAX_RUNTIME_TENSOR_STORE_EVIDENCE_RECORDS = 4096
MAX_RUNTIME_TENSOR_STORE_EVIDENCE_ISSUES = 256
MAX_RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_TENSOR_STORE_EVIDENCE_FIELD_BYTES = 512

_EVIDENCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_VALUE_ROLES = frozenset({"input", "computed"})
_FORBIDDEN_EVIDENCE_TEXT = frozenset(
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
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "subprocess",
        "tensor_value",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeTensorExpectedRecord:
    """Expected runtime tensor record shape derived from the compute graph."""

    tensor_name: str
    shape: tuple[int, ...]
    dtype: str
    value_role: str

    def __post_init__(self) -> None:
        _validate_evidence_text(self.tensor_name, "expected tensor_name")
        _validate_shape(self.shape, "expected shape")
        _validate_evidence_text(self.dtype, "expected dtype")
        _validate_value_role(self.value_role)


@dataclass(frozen=True)
class RuntimeTensorValueEvidence:
    """Value-record metadata that intentionally excludes tensor contents."""

    tensor_name: str
    shape: tuple[int, ...]
    dtype: str
    value_role: str
    readonly: bool
    record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT
    raw_value_status: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_evidence_text(self.tensor_name, "record tensor_name")
        _validate_shape(self.shape, "record shape")
        _validate_evidence_text(self.dtype, "record dtype")
        _validate_value_role(self.value_role)
        if not isinstance(self.readonly, bool):
            raise TypeError("record readonly must be bool")
        if self.record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime tensor value evidence record contract mismatch")
        if self.raw_value_status != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime tensor value evidence must omit raw values")


@dataclass(frozen=True)
class RuntimeTensorStoreEvidenceIssue:
    """One derived Runtime Tensor Store evidence issue."""

    tensor_name: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_evidence_text(self.tensor_name, "issue tensor_name")
        _validate_evidence_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeTensorStoreEvidenceReport:
    """Deterministic, data-only report for Runtime Tensor Store records."""

    graph_name: str
    expected_records: tuple[RuntimeTensorExpectedRecord, ...]
    records: tuple[RuntimeTensorValueEvidence, ...]
    issues: tuple[RuntimeTensorStoreEvidenceIssue, ...]
    evidence_contract: str = RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT
    store_contract: str = RUNTIME_TENSOR_STORE_CONTRACT
    value_record_contract: str = RUNTIME_VALUE_RECORD_CONTRACT
    artifact_status: str = RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_evidence_text(self.graph_name, "graph_name")
        if self.evidence_contract != RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT:
            raise ValueError("runtime tensor store evidence contract mismatch")
        if self.store_contract != RUNTIME_TENSOR_STORE_CONTRACT:
            raise ValueError("runtime tensor store contract mismatch")
        if self.value_record_contract != RUNTIME_VALUE_RECORD_CONTRACT:
            raise ValueError("runtime value record contract mismatch")
        if self.artifact_status != RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS:
            raise ValueError("runtime tensor store evidence artifact status mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime tensor store evidence must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime tensor store blocked execution surfaces changed")
        _validate_expected_records(self.expected_records)
        _validate_value_evidence_records(self.records)
        if type(self.issues) is not tuple:
            raise TypeError("runtime tensor store evidence issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_TENSOR_STORE_EVIDENCE_ISSUES:
            raise ValueError("runtime tensor store evidence issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeTensorStoreEvidenceIssue):
                raise TypeError("runtime tensor store evidence issues must be issue objects")
        expected_issues = _derive_issues(self.expected_records, self.records)
        if self.issues != expected_issues:
            raise ValueError("runtime tensor store evidence issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether Runtime Tensor Store evidence passed."""

        return not self.issues

    @property
    def record_metadata_digest(self) -> str:
        """Return a digest over record metadata only, never tensor values."""

        payload = [
            {
                "dtype": record.dtype,
                "raw_value_status": record.raw_value_status,
                "readonly": record.readonly,
                "shape": list(record.shape),
                "tensor_name": record.tensor_name,
                "value_role": record.value_role,
            }
            for record in self.records
        ]
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeTensorStoreEvidenceError(AssertionError):
    """Raised when Runtime Tensor Store evidence does not pass."""


def build_runtime_tensor_store_evidence_report(
    graph: ComputeGraph,
    execution: RuntimeExecutionResult,
) -> RuntimeTensorStoreEvidenceReport:
    """Build data-only evidence from an executed graph's value records."""

    if not isinstance(graph, ComputeGraph):
        raise TypeError("runtime tensor store evidence graph must be ComputeGraph")
    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError(
            "runtime tensor store evidence execution must be RuntimeExecutionResult"
        )
    expected_records = _expected_records_for_graph(graph)
    records = tuple(_record_to_evidence(record) for record in execution.records)
    return RuntimeTensorStoreEvidenceReport(
        graph_name=graph.name,
        expected_records=expected_records,
        records=records,
        issues=_derive_issues(expected_records, records),
    )


def assert_runtime_tensor_store_evidence(
    report: RuntimeTensorStoreEvidenceReport,
) -> RuntimeTensorStoreEvidenceReport:
    """Return the report or raise when Runtime Tensor Store evidence fails."""

    if not isinstance(report, RuntimeTensorStoreEvidenceReport):
        raise TypeError("runtime tensor store evidence report must be report object")
    if report.issues:
        lines = [f"runtime tensor store evidence failed for {report.graph_name!r}:"]
        lines.extend(
            f"- {issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeTensorStoreEvidenceError("\n".join(lines))
    return report


def runtime_tensor_store_evidence_report_to_dict(
    report: RuntimeTensorStoreEvidenceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible tensor store evidence report."""

    if not isinstance(report, RuntimeTensorStoreEvidenceReport):
        raise TypeError("runtime tensor store evidence report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "evidence_contract": report.evidence_contract,
        "expected_record_count": len(report.expected_records),
        "expected_records": [
            {
                "dtype": record.dtype,
                "shape": list(record.shape),
                "tensor_name": record.tensor_name,
                "value_role": record.value_role,
            }
            for record in report.expected_records
        ],
        "graph_name": report.graph_name,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "tensor_name": issue.tensor_name,
            }
            for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "record_count": len(report.records),
        "record_metadata_digest": report.record_metadata_digest,
        "records": [
            {
                "dtype": record.dtype,
                "raw_value_status": record.raw_value_status,
                "readonly": record.readonly,
                "record_contract": record.record_contract,
                "shape": list(record.shape),
                "tensor_name": record.tensor_name,
                "value_role": record.value_role,
            }
            for record in report.records
        ],
        "schema_version": RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION,
        "store_contract": report.store_contract,
        "value_record_contract": report.value_record_contract,
    }


def dump_runtime_tensor_store_evidence_report(
    report: RuntimeTensorStoreEvidenceReport,
) -> str:
    """Render stable data-only Runtime Tensor Store evidence."""

    text = json.dumps(
        runtime_tensor_store_evidence_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_BYTES:
        raise ValueError("runtime tensor store evidence report exceeds byte limit")
    return text + "\n"


def _expected_records_for_graph(
    graph: ComputeGraph,
) -> tuple[RuntimeTensorExpectedRecord, ...]:
    produced = {output.name for operation in graph.operations for output in operation.outputs}
    input_tensors: dict[str, TensorRef] = {}
    for operation in graph.operations:
        for tensor in operation.inputs:
            if tensor.name not in produced:
                existing = input_tensors.get(tensor.name)
                if existing is not None and existing != tensor:
                    raise ValueError("runtime tensor store evidence input tensor conflict")
                input_tensors[tensor.name] = tensor
    expected: list[RuntimeTensorExpectedRecord] = [
        RuntimeTensorExpectedRecord(
            tensor_name=name,
            shape=input_tensors[name].shape,
            dtype=RUNTIME_TENSOR_STORE_RUNTIME_DTYPE,
            value_role="input",
        )
        for name in sorted(input_tensors)
    ]
    for operation in graph.operations:
        for tensor in operation.outputs:
            expected.append(
                RuntimeTensorExpectedRecord(
                    tensor_name=tensor.name,
                    shape=tensor.shape,
                    dtype=RUNTIME_TENSOR_STORE_RUNTIME_DTYPE,
                    value_role="computed",
                )
            )
    return tuple(expected)


def _record_to_evidence(record: RuntimeValueRecord) -> RuntimeTensorValueEvidence:
    if not isinstance(record, RuntimeValueRecord):
        raise TypeError("runtime tensor store evidence records must be value records")
    return RuntimeTensorValueEvidence(
        tensor_name=record.tensor_name,
        shape=record.shape,
        dtype=record.dtype,
        value_role=record.value_role,
        readonly=not record.value.flags.writeable,
    )


def _derive_issues(
    expected_records: tuple[RuntimeTensorExpectedRecord, ...],
    records: tuple[RuntimeTensorValueEvidence, ...],
) -> tuple[RuntimeTensorStoreEvidenceIssue, ...]:
    expected_by_name = {record.tensor_name: record for record in expected_records}
    records_by_name = {record.tensor_name: record for record in records}
    issues: list[RuntimeTensorStoreEvidenceIssue] = []

    for tensor_name in sorted(expected_by_name):
        expected = expected_by_name[tensor_name]
        record = records_by_name.get(tensor_name)
        if record is None:
            issues.append(
                RuntimeTensorStoreEvidenceIssue(
                    tensor_name=tensor_name,
                    issue_code="expected_record_missing",
                )
            )
            continue
        if record.shape != expected.shape:
            issues.append(
                RuntimeTensorStoreEvidenceIssue(
                    tensor_name=tensor_name,
                    issue_code="shape_mismatch",
                )
            )
        if record.dtype != expected.dtype:
            issues.append(
                RuntimeTensorStoreEvidenceIssue(
                    tensor_name=tensor_name,
                    issue_code="dtype_mismatch",
                )
            )
        if record.value_role != expected.value_role:
            issues.append(
                RuntimeTensorStoreEvidenceIssue(
                    tensor_name=tensor_name,
                    issue_code="value_role_mismatch",
                )
            )
        if not record.readonly:
            issues.append(
                RuntimeTensorStoreEvidenceIssue(
                    tensor_name=tensor_name,
                    issue_code="record_value_mutable",
                )
            )

    for tensor_name in sorted(set(records_by_name) - set(expected_by_name)):
        issues.append(
            RuntimeTensorStoreEvidenceIssue(
                tensor_name=tensor_name,
                issue_code="unexpected_record",
            )
        )

    return tuple(issues)


def _validate_expected_records(
    records: tuple[RuntimeTensorExpectedRecord, ...],
) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime tensor store expected records must be a tuple")
    _validate_record_count(len(records))
    names: list[str] = []
    for record in records:
        if not isinstance(record, RuntimeTensorExpectedRecord):
            raise TypeError(
                "runtime tensor store expected records must be expected record objects"
            )
        names.append(record.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime tensor store expected record names must be unique")


def _validate_value_evidence_records(
    records: tuple[RuntimeTensorValueEvidence, ...],
) -> None:
    if type(records) is not tuple:
        raise TypeError("runtime tensor store value evidence records must be a tuple")
    _validate_record_count(len(records))
    names: list[str] = []
    for record in records:
        if not isinstance(record, RuntimeTensorValueEvidence):
            raise TypeError(
                "runtime tensor store value records must be value evidence objects"
            )
        names.append(record.tensor_name)
    if len(names) != len(set(names)):
        raise ValueError("runtime tensor store value record names must be unique")


def _validate_record_count(count: int) -> None:
    if count > MAX_RUNTIME_TENSOR_STORE_EVIDENCE_RECORDS:
        raise ValueError("runtime tensor store evidence record count exceeds limit")


def _validate_value_role(value: str) -> None:
    if value not in _VALUE_ROLES:
        raise ValueError("runtime tensor store evidence value role unsupported")


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


def _validate_evidence_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _EVIDENCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime tensor store identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_TENSOR_STORE_EVIDENCE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime tensor store evidence field limit")
    if value in _FORBIDDEN_EVIDENCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


__all__ = [
    "MAX_RUNTIME_TENSOR_STORE_EVIDENCE_FIELD_BYTES",
    "MAX_RUNTIME_TENSOR_STORE_EVIDENCE_ISSUES",
    "MAX_RUNTIME_TENSOR_STORE_EVIDENCE_RECORDS",
    "MAX_RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_BYTES",
    "RUNTIME_TENSOR_STORE_EVIDENCE_ARTIFACT_STATUS",
    "RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT",
    "RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION",
    "RUNTIME_TENSOR_STORE_RUNTIME_DTYPE",
    "RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS",
    "RuntimeTensorExpectedRecord",
    "RuntimeTensorStoreEvidenceError",
    "RuntimeTensorStoreEvidenceIssue",
    "RuntimeTensorStoreEvidenceReport",
    "RuntimeTensorValueEvidence",
    "assert_runtime_tensor_store_evidence",
    "build_runtime_tensor_store_evidence_report",
    "dump_runtime_tensor_store_evidence_report",
    "runtime_tensor_store_evidence_report_to_dict",
]
