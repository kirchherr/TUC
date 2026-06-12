"""Data-only receipt linking one trusted runtime execution to its evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.ir.model import MAX_TENSOR_DIMENSION, MAX_TENSOR_RANK
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RuntimeExecutionResult,
)
from tuc.runtime.input_manifest import (
    RUNTIME_INPUT_MANIFEST_CONTRACT,
    RuntimeInputManifestReport,
)
from tuc.runtime.output_manifest import (
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RuntimeOutputManifestReport,
)
from tuc.runtime.reference_correctness import (
    RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    RuntimeReferenceCorrectnessReport,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeTensorStoreEvidenceReport,
)

RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_execution_receipt_report.v0"
)
RUNTIME_EXECUTION_RECEIPT_CONTRACT = "runtime_execution_receipt.data_only.v0"
RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS = "review_evidence"
RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY = "metadata_digest_linkage"
RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS = (
    "tensor_store_evidence",
    "input_manifest",
    "output_manifest",
    "reference_correctness",
)
MAX_RUNTIME_EXECUTION_RECEIPT_EVIDENCE_LINKS = 16
MAX_RUNTIME_EXECUTION_RECEIPT_OPERATIONS = 4096
MAX_RUNTIME_EXECUTION_RECEIPT_ISSUES = 256
MAX_RUNTIME_EXECUTION_RECEIPT_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_EXECUTION_RECEIPT_FIELD_BYTES = 512

_RECEIPT_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_EXPECTED_CONTRACT_BY_KIND = {
    "tensor_store_evidence": RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT,
    "input_manifest": RUNTIME_INPUT_MANIFEST_CONTRACT,
    "output_manifest": RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    "reference_correctness": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
}
_FORBIDDEN_RECEIPT_TEXT = frozenset(
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
        "reference_value",
        "source_text",
        "subprocess",
        "tensor_value",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeExecutionReceiptEvidenceLink:
    """One linked evidence report summarized without raw tensor values."""

    evidence_kind: str
    graph_name: str
    evidence_contract: str
    metadata_digest: str
    item_count: int
    passed: bool
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

    def __post_init__(self) -> None:
        _validate_receipt_text(self.evidence_kind, "receipt evidence_kind")
        _validate_receipt_text(self.graph_name, "receipt evidence graph_name")
        _validate_receipt_text(self.evidence_contract, "receipt evidence_contract")
        _validate_digest(self.metadata_digest, "receipt metadata_digest")
        _validate_non_negative_count(self.item_count, "receipt item_count")
        if not isinstance(self.passed, bool):
            raise TypeError("runtime execution receipt passed must be bool")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime execution receipt must omit raw values")


@dataclass(frozen=True)
class RuntimeExecutionReceiptOperation:
    """One operation-level execution fact summarized from the runtime trace."""

    operation_name: str
    operation_kind: str
    planned_backend: str
    executor_backend: str
    input_tensors: tuple[str, ...]
    output_tensors: tuple[str, ...]
    output_shapes: tuple[tuple[int, ...], ...]
    status: str

    def __post_init__(self) -> None:
        _validate_receipt_text(self.operation_name, "receipt operation_name")
        _validate_receipt_text(self.operation_kind, "receipt operation_kind")
        _validate_receipt_text(self.planned_backend, "receipt planned_backend")
        _validate_receipt_text(self.executor_backend, "receipt executor_backend")
        _validate_name_tuple(self.input_tensors, "receipt input_tensors")
        _validate_name_tuple(self.output_tensors, "receipt output_tensors")
        if type(self.output_shapes) is not tuple:
            raise TypeError("runtime execution receipt output_shapes must be a tuple")
        if len(self.output_shapes) != len(self.output_tensors):
            raise ValueError("runtime execution receipt output_shapes mismatch")
        for shape in self.output_shapes:
            _validate_shape(shape, "receipt output_shape")
        _validate_receipt_text(self.status, "receipt operation status")


@dataclass(frozen=True)
class RuntimeExecutionReceiptIssue:
    """One derived runtime execution receipt issue."""

    evidence_kind: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_receipt_text(self.evidence_kind, "receipt issue evidence_kind")
        _validate_receipt_text(self.issue_code, "receipt issue_code")


@dataclass(frozen=True)
class RuntimeExecutionReceiptReport:
    """Deterministic, data-only receipt for one trusted runtime execution."""

    graph_name: str
    evidence_links: tuple[RuntimeExecutionReceiptEvidenceLink, ...]
    operations: tuple[RuntimeExecutionReceiptOperation, ...]
    issues: tuple[RuntimeExecutionReceiptIssue, ...]
    receipt_contract: str = RUNTIME_EXECUTION_RECEIPT_CONTRACT
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    artifact_status: str = RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS
    linkage_policy: str = RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_receipt_text(self.graph_name, "runtime execution receipt graph_name")
        if self.receipt_contract != RUNTIME_EXECUTION_RECEIPT_CONTRACT:
            raise ValueError("runtime execution receipt contract mismatch")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("runtime execution receipt executor contract mismatch")
        if self.artifact_status != RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS:
            raise ValueError("runtime execution receipt artifact status mismatch")
        if self.linkage_policy != RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY:
            raise ValueError("runtime execution receipt linkage policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime execution receipt must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime execution receipt blocked surfaces changed")
        _validate_evidence_links(self.evidence_links)
        _validate_operations(self.operations)
        if type(self.issues) is not tuple:
            raise TypeError("runtime execution receipt issues must be a tuple")
        if len(self.issues) > MAX_RUNTIME_EXECUTION_RECEIPT_ISSUES:
            raise ValueError("runtime execution receipt issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeExecutionReceiptIssue):
                raise TypeError(
                    "runtime execution receipt issues must be receipt issues"
                )
        expected_issues = _derive_issues(self.graph_name, self.evidence_links)
        if self.issues != expected_issues:
            raise ValueError("runtime execution receipt issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether linked runtime execution evidence passed."""

        return not self.issues

    @property
    def execution_trace_metadata_digest(self) -> str:
        """Return a digest over operation trace metadata only."""

        payload = [
            {
                "executor_backend": operation.executor_backend,
                "input_tensors": list(operation.input_tensors),
                "operation_kind": operation.operation_kind,
                "operation_name": operation.operation_name,
                "output_shapes": [list(shape) for shape in operation.output_shapes],
                "output_tensors": list(operation.output_tensors),
                "planned_backend": operation.planned_backend,
                "status": operation.status,
            }
            for operation in self.operations
        ]
        return _metadata_digest(payload)

    @property
    def receipt_metadata_digest(self) -> str:
        """Return a digest over linked evidence and operation metadata."""

        payload = {
            "evidence_links": [
                {
                    "evidence_contract": link.evidence_contract,
                    "evidence_kind": link.evidence_kind,
                    "graph_name": link.graph_name,
                    "item_count": link.item_count,
                    "metadata_digest": link.metadata_digest,
                    "passed": link.passed,
                    "raw_value_policy": link.raw_value_policy,
                }
                for link in self.evidence_links
            ],
            "execution_trace_metadata_digest": self.execution_trace_metadata_digest,
            "graph_name": self.graph_name,
        }
        return _metadata_digest(payload)


class RuntimeExecutionReceiptError(AssertionError):
    """Raised when runtime execution receipt evidence does not pass."""


def build_runtime_execution_receipt_report(
    execution: RuntimeExecutionResult,
    tensor_store_report: RuntimeTensorStoreEvidenceReport,
    input_manifest_report: RuntimeInputManifestReport,
    output_manifest_report: RuntimeOutputManifestReport,
    reference_correctness_report: RuntimeReferenceCorrectnessReport,
) -> RuntimeExecutionReceiptReport:
    """Build a data-only receipt linking one runtime execution to evidence."""

    if not isinstance(execution, RuntimeExecutionResult):
        raise TypeError("runtime execution receipt execution must be result object")
    if not isinstance(tensor_store_report, RuntimeTensorStoreEvidenceReport):
        raise TypeError("runtime execution receipt tensor store report mismatch")
    if not isinstance(input_manifest_report, RuntimeInputManifestReport):
        raise TypeError("runtime execution receipt input manifest report mismatch")
    if not isinstance(output_manifest_report, RuntimeOutputManifestReport):
        raise TypeError("runtime execution receipt output manifest report mismatch")
    if not isinstance(reference_correctness_report, RuntimeReferenceCorrectnessReport):
        raise TypeError("runtime execution receipt reference report mismatch")

    operations = tuple(
        RuntimeExecutionReceiptOperation(
            operation_name=step.operation_name,
            operation_kind=step.operation_kind.value,
            planned_backend=step.planned_backend,
            executor_backend=step.executor_backend,
            input_tensors=step.input_tensors,
            output_tensors=step.output_tensors,
            output_shapes=step.output_shapes,
            status=step.status,
        )
        for step in execution.trace.steps
    )
    links = (
        RuntimeExecutionReceiptEvidenceLink(
            evidence_kind="tensor_store_evidence",
            graph_name=tensor_store_report.graph_name,
            evidence_contract=tensor_store_report.evidence_contract,
            metadata_digest=tensor_store_report.record_metadata_digest,
            item_count=len(tensor_store_report.records),
            passed=tensor_store_report.passed,
        ),
        RuntimeExecutionReceiptEvidenceLink(
            evidence_kind="input_manifest",
            graph_name=input_manifest_report.graph_name,
            evidence_contract=input_manifest_report.manifest_contract,
            metadata_digest=input_manifest_report.input_metadata_digest,
            item_count=len(input_manifest_report.inputs),
            passed=input_manifest_report.passed,
        ),
        RuntimeExecutionReceiptEvidenceLink(
            evidence_kind="output_manifest",
            graph_name=output_manifest_report.graph_name,
            evidence_contract=output_manifest_report.manifest_contract,
            metadata_digest=output_manifest_report.output_metadata_digest,
            item_count=len(output_manifest_report.outputs),
            passed=output_manifest_report.passed,
        ),
        RuntimeExecutionReceiptEvidenceLink(
            evidence_kind="reference_correctness",
            graph_name=reference_correctness_report.graph_name,
            evidence_contract=reference_correctness_report.correctness_contract,
            metadata_digest=reference_correctness_report.comparison_metadata_digest,
            item_count=len(reference_correctness_report.comparisons),
            passed=reference_correctness_report.passed,
        ),
    )
    return RuntimeExecutionReceiptReport(
        graph_name=execution.trace.graph_name,
        evidence_links=links,
        operations=operations,
        issues=_derive_issues(execution.trace.graph_name, links),
    )


def assert_runtime_execution_receipt(
    report: RuntimeExecutionReceiptReport,
) -> RuntimeExecutionReceiptReport:
    """Return the report or raise when linked execution evidence fails."""

    if not isinstance(report, RuntimeExecutionReceiptReport):
        raise TypeError("runtime execution receipt report must be report object")
    if report.issues:
        lines = [f"runtime execution receipt failed for {report.graph_name!r}:"]
        lines.extend(
            f"- {issue.evidence_kind}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeExecutionReceiptError("\n".join(lines))
    return report


def runtime_execution_receipt_report_to_dict(
    report: RuntimeExecutionReceiptReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible execution receipt report."""

    if not isinstance(report, RuntimeExecutionReceiptReport):
        raise TypeError("runtime execution receipt report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "evidence_link_count": len(report.evidence_links),
        "evidence_links": [
            {
                "evidence_contract": link.evidence_contract,
                "evidence_kind": link.evidence_kind,
                "graph_name": link.graph_name,
                "item_count": link.item_count,
                "metadata_digest": link.metadata_digest,
                "passed": link.passed,
                "raw_value_policy": link.raw_value_policy,
            }
            for link in report.evidence_links
        ],
        "execution_trace_metadata_digest": report.execution_trace_metadata_digest,
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "issues": [
            {
                "evidence_kind": issue.evidence_kind,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "linkage_policy": report.linkage_policy,
        "operation_count": len(report.operations),
        "operations": [
            {
                "executor_backend": operation.executor_backend,
                "input_tensors": list(operation.input_tensors),
                "operation_kind": operation.operation_kind,
                "operation_name": operation.operation_name,
                "output_shapes": [
                    list(shape) for shape in operation.output_shapes
                ],
                "output_tensors": list(operation.output_tensors),
                "planned_backend": operation.planned_backend,
                "status": operation.status,
            }
            for operation in report.operations
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "receipt_contract": report.receipt_contract,
        "receipt_metadata_digest": report.receipt_metadata_digest,
        "required_evidence_kinds": list(
            RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS
        ),
        "schema_version": RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION,
    }


def dump_runtime_execution_receipt_report(
    report: RuntimeExecutionReceiptReport,
) -> str:
    """Render stable data-only runtime execution receipt evidence."""

    text = json.dumps(
        runtime_execution_receipt_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_EXECUTION_RECEIPT_REPORT_BYTES:
        raise ValueError("runtime execution receipt report exceeds byte limit")
    return text + "\n"


def _derive_issues(
    graph_name: str,
    evidence_links: tuple[RuntimeExecutionReceiptEvidenceLink, ...],
) -> tuple[RuntimeExecutionReceiptIssue, ...]:
    links_by_kind = {link.evidence_kind: link for link in evidence_links}
    issues: list[RuntimeExecutionReceiptIssue] = []

    for evidence_kind in RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS:
        link = links_by_kind.get(evidence_kind)
        if link is None:
            issues.append(
                RuntimeExecutionReceiptIssue(
                    evidence_kind=evidence_kind,
                    issue_code="missing_evidence_link",
                )
            )
            continue
        if link.graph_name != graph_name:
            issues.append(
                RuntimeExecutionReceiptIssue(
                    evidence_kind=evidence_kind,
                    issue_code="graph_name_mismatch",
                )
            )
        if link.evidence_contract != _EXPECTED_CONTRACT_BY_KIND[evidence_kind]:
            issues.append(
                RuntimeExecutionReceiptIssue(
                    evidence_kind=evidence_kind,
                    issue_code="contract_mismatch",
                )
            )
        if link.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            issues.append(
                RuntimeExecutionReceiptIssue(
                    evidence_kind=evidence_kind,
                    issue_code="raw_value_policy_mismatch",
                )
            )
        if not link.passed:
            issues.append(
                RuntimeExecutionReceiptIssue(
                    evidence_kind=evidence_kind,
                    issue_code="evidence_not_passed",
                )
            )
        if link.item_count <= 0:
            issues.append(
                RuntimeExecutionReceiptIssue(
                    evidence_kind=evidence_kind,
                    issue_code="empty_evidence",
                )
            )

    return tuple(issues)


def _validate_evidence_links(
    links: tuple[RuntimeExecutionReceiptEvidenceLink, ...],
) -> None:
    if type(links) is not tuple:
        raise TypeError("runtime execution receipt links must be a tuple")
    if not links:
        raise ValueError("runtime execution receipt links must not be empty")
    if len(links) > MAX_RUNTIME_EXECUTION_RECEIPT_EVIDENCE_LINKS:
        raise ValueError("runtime execution receipt link count exceeds limit")
    names: list[str] = []
    for link in links:
        if not isinstance(link, RuntimeExecutionReceiptEvidenceLink):
            raise TypeError("runtime execution receipt links must be evidence links")
        if link.evidence_kind not in _EXPECTED_CONTRACT_BY_KIND:
            raise ValueError("runtime execution receipt evidence kind unsupported")
        names.append(link.evidence_kind)
    if len(names) != len(set(names)):
        raise ValueError("runtime execution receipt evidence kinds must be unique")


def _validate_operations(
    operations: tuple[RuntimeExecutionReceiptOperation, ...],
) -> None:
    if type(operations) is not tuple:
        raise TypeError("runtime execution receipt operations must be a tuple")
    if not operations:
        raise ValueError("runtime execution receipt operations must not be empty")
    if len(operations) > MAX_RUNTIME_EXECUTION_RECEIPT_OPERATIONS:
        raise ValueError("runtime execution receipt operation count exceeds limit")
    for operation in operations:
        if not isinstance(operation, RuntimeExecutionReceiptOperation):
            raise TypeError("runtime execution receipt operations must be operations")


def _validate_name_tuple(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple or not values:
        raise ValueError(f"{label} must be a non-empty tuple")
    for value in values:
        _validate_receipt_text(value, label)


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


def _validate_non_negative_count(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    if value > MAX_RUNTIME_EXECUTION_RECEIPT_OPERATIONS:
        raise ValueError(f"{label} exceeds runtime execution receipt limit")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be a sha256 digest")


def _validate_receipt_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _RECEIPT_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime execution identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_EXECUTION_RECEIPT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime execution receipt field limit")
    if value in _FORBIDDEN_RECEIPT_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_EXECUTION_RECEIPT_EVIDENCE_LINKS",
    "MAX_RUNTIME_EXECUTION_RECEIPT_FIELD_BYTES",
    "MAX_RUNTIME_EXECUTION_RECEIPT_ISSUES",
    "MAX_RUNTIME_EXECUTION_RECEIPT_OPERATIONS",
    "MAX_RUNTIME_EXECUTION_RECEIPT_REPORT_BYTES",
    "RUNTIME_EXECUTION_RECEIPT_ARTIFACT_STATUS",
    "RUNTIME_EXECUTION_RECEIPT_CONTRACT",
    "RUNTIME_EXECUTION_RECEIPT_LINKAGE_POLICY",
    "RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION",
    "RUNTIME_EXECUTION_RECEIPT_REQUIRED_EVIDENCE_KINDS",
    "RuntimeExecutionReceiptError",
    "RuntimeExecutionReceiptEvidenceLink",
    "RuntimeExecutionReceiptIssue",
    "RuntimeExecutionReceiptOperation",
    "RuntimeExecutionReceiptReport",
    "assert_runtime_execution_receipt",
    "build_runtime_execution_receipt_report",
    "dump_runtime_execution_receipt_report",
    "runtime_execution_receipt_report_to_dict",
]
