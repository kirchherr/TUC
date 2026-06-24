"""Data-only binding across layout conversion, HS-IR, and tensor store evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.hs_ir_plan_alignment import (
    RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT,
    RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION,
    RuntimeHsIrPlanAlignmentReport,
)
from tuc.runtime.layout_conversion_evidence import (
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION,
    RuntimeLayoutConversionEvidenceReport,
    RuntimeLayoutConversionRecord,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT,
    RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeTensorStoreEvidenceReport,
    RuntimeTensorValueEvidence,
)

RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_layout_conversion_digest_binding_report.v0"
)
RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT = (
    "runtime_layout_conversion_digest_binding.data_only.v0"
)
RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS = "review_evidence"
RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID = (
    "runtime_layout_conversion_digest_binding_mixed"
)
RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE = (
    "metadata_digest_and_record_id_binding"
)
RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_STATUSES = ("bound", "failed")
RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE = "none"
MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ROWS = 4096
MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ISSUES = 256
MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_FIELD_BYTES = 512

_BINDING_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_BINDING_TEXT = frozenset(
    {
        "allocation_handle",
        "backend_artifact",
        "callable",
        "command",
        "command_line",
        "device_id",
        "device_pointer",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "memory_address",
        "module",
        "network",
        "plugin_entrypoint",
        "pointer",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_tensor_value",
        "raw_timing_samples",
        "runtime_handle",
        "source_text",
        "subprocess",
        "tensor_value",
        "tensor_values",
        "url",
    }
)


@dataclass(frozen=True)
class RuntimeLayoutConversionDigestBindingRow:
    """One layout-conversion binding across the three data-only reports."""

    conversion_id: str
    tensor_name: str
    source_operation: str
    target_operation: str
    source_value_record_id: str
    consumer_input_id: str
    layout_conversion_from_backend: str
    layout_conversion_to_backend: str
    layout_conversion_from_memory_domain: str
    layout_conversion_to_memory_domain: str
    layout_conversion_from_layout: str
    layout_conversion_to_layout: str
    planned_bytes: int
    hs_ir_source_backend: str
    hs_ir_target_backend: str
    hs_ir_source_layout: str
    hs_ir_target_layout: str
    hs_ir_target_layout_conversion_bytes: int
    tensor_store_source_backend: str
    tensor_store_source_memory_domain: str
    tensor_store_source_layout: str
    tensor_store_source_producer_id: str
    binding_status: str
    issue_code: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.conversion_id, "conversion_id"),
            (self.tensor_name, "tensor_name"),
            (self.source_operation, "source_operation"),
            (self.target_operation, "target_operation"),
            (self.source_value_record_id, "source_value_record_id"),
            (self.consumer_input_id, "consumer_input_id"),
            (self.layout_conversion_from_backend, "layout_conversion_from_backend"),
            (self.layout_conversion_to_backend, "layout_conversion_to_backend"),
            (
                self.layout_conversion_from_memory_domain,
                "layout_conversion_from_memory_domain",
            ),
            (
                self.layout_conversion_to_memory_domain,
                "layout_conversion_to_memory_domain",
            ),
            (self.layout_conversion_from_layout, "layout_conversion_from_layout"),
            (self.layout_conversion_to_layout, "layout_conversion_to_layout"),
            (self.hs_ir_source_backend, "hs_ir_source_backend"),
            (self.hs_ir_target_backend, "hs_ir_target_backend"),
            (self.hs_ir_source_layout, "hs_ir_source_layout"),
            (self.hs_ir_target_layout, "hs_ir_target_layout"),
            (self.tensor_store_source_backend, "tensor_store_source_backend"),
            (
                self.tensor_store_source_memory_domain,
                "tensor_store_source_memory_domain",
            ),
            (self.tensor_store_source_layout, "tensor_store_source_layout"),
            (self.tensor_store_source_producer_id, "tensor_store_source_producer_id"),
            (self.issue_code, "issue_code"),
        ):
            _validate_binding_text(value, label)
        _validate_non_negative_int(self.planned_bytes, "planned_bytes")
        _validate_non_negative_int(
            self.hs_ir_target_layout_conversion_bytes,
            "hs_ir_target_layout_conversion_bytes",
        )
        if self.binding_status not in RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_STATUSES:
            raise ValueError("runtime layout conversion binding status invalid")
        expected_issue = _row_issue_code(self)
        if self.issue_code != expected_issue:
            raise ValueError("runtime layout conversion binding issue_code mismatch")
        if (self.binding_status == "bound") != (
            expected_issue == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE
        ):
            raise ValueError("runtime layout conversion binding status mismatch")


@dataclass(frozen=True)
class RuntimeLayoutConversionDigestBindingIssue:
    """One derived layout-conversion digest binding issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_binding_text(self.subject, "issue subject")
        _validate_binding_text(self.issue_code, "issue_code")


@dataclass(frozen=True)
class RuntimeLayoutConversionDigestBindingReport:
    """Deterministic binding report for layout conversion proof promotion."""

    graph_name: str
    source_hs_ir_graph_name: str
    source_tensor_store_graph_name: str
    source_layout_conversion_contract: str
    source_layout_conversion_schema_version: str
    source_layout_conversion_passed: bool
    source_layout_conversion_issue_count: int
    source_layout_conversion_count: int
    source_layout_conversion_total_planned_bytes: int
    source_layout_conversion_metadata_digest: str
    source_partition_plan_digest: str
    source_hs_ir_alignment_contract: str
    source_hs_ir_alignment_schema_version: str
    source_hs_ir_alignment_passed: bool
    source_hs_ir_issue_count: int
    source_hs_ir_step_count: int
    source_hs_ir_layout_conversion_count: int
    source_hs_ir_total_layout_conversion_bytes: int
    source_hs_ir_alignment_metadata_digest: str
    source_tensor_store_evidence_contract: str
    source_tensor_store_evidence_schema_version: str
    source_tensor_store_passed: bool
    source_tensor_store_issue_count: int
    source_tensor_store_record_count: int
    source_tensor_store_record_metadata_digest: str
    bindings: tuple[RuntimeLayoutConversionDigestBindingRow, ...]
    issues: tuple[RuntimeLayoutConversionDigestBindingIssue, ...]
    binding_contract: str = RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT
    artifact_status: str = RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS
    artifact_id: str = RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
    binding_scope: str = RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        for value, label in (
            (self.graph_name, "graph_name"),
            (self.source_hs_ir_graph_name, "source_hs_ir_graph_name"),
            (self.source_tensor_store_graph_name, "source_tensor_store_graph_name"),
        ):
            _validate_binding_text(value, label)
        if self.source_layout_conversion_contract != (
            RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT
        ):
            raise ValueError("runtime layout conversion source contract mismatch")
        if self.source_layout_conversion_schema_version != (
            RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("runtime layout conversion source schema mismatch")
        if self.source_hs_ir_alignment_contract != RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT:
            raise ValueError("runtime layout conversion HS-IR contract mismatch")
        if self.source_hs_ir_alignment_schema_version != (
            RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("runtime layout conversion HS-IR schema mismatch")
        if self.source_tensor_store_evidence_contract != (
            RUNTIME_TENSOR_STORE_EVIDENCE_CONTRACT
        ):
            raise ValueError("runtime layout conversion tensor store contract mismatch")
        if self.source_tensor_store_evidence_schema_version != (
            RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("runtime layout conversion tensor store schema mismatch")
        for int_value, int_label in (
            (
                self.source_layout_conversion_issue_count,
                "source_layout_conversion_issue_count",
            ),
            (self.source_layout_conversion_count, "source_layout_conversion_count"),
            (
                self.source_layout_conversion_total_planned_bytes,
                "source_layout_conversion_total_planned_bytes",
            ),
            (self.source_hs_ir_issue_count, "source_hs_ir_issue_count"),
            (self.source_hs_ir_step_count, "source_hs_ir_step_count"),
            (
                self.source_hs_ir_layout_conversion_count,
                "source_hs_ir_layout_conversion_count",
            ),
            (
                self.source_hs_ir_total_layout_conversion_bytes,
                "source_hs_ir_total_layout_conversion_bytes",
            ),
            (self.source_tensor_store_issue_count, "source_tensor_store_issue_count"),
            (self.source_tensor_store_record_count, "source_tensor_store_record_count"),
        ):
            _validate_non_negative_int(int_value, int_label)
        for digest_value, digest_label in (
            (
                self.source_layout_conversion_metadata_digest,
                "source_layout_conversion_metadata_digest",
            ),
            (self.source_partition_plan_digest, "source_partition_plan_digest"),
            (
                self.source_hs_ir_alignment_metadata_digest,
                "source_hs_ir_alignment_metadata_digest",
            ),
            (
                self.source_tensor_store_record_metadata_digest,
                "source_tensor_store_record_metadata_digest",
            ),
        ):
            _validate_digest(digest_value, digest_label)
        if not isinstance(self.source_layout_conversion_passed, bool):
            raise TypeError("source_layout_conversion_passed must be bool")
        if not isinstance(self.source_hs_ir_alignment_passed, bool):
            raise TypeError("source_hs_ir_alignment_passed must be bool")
        if not isinstance(self.source_tensor_store_passed, bool):
            raise TypeError("source_tensor_store_passed must be bool")
        if self.binding_contract != RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT:
            raise ValueError("runtime layout conversion digest binding contract mismatch")
        if (
            self.artifact_status
            != RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS
        ):
            raise ValueError("runtime layout conversion digest binding status mismatch")
        if self.artifact_id != RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID:
            raise ValueError("runtime layout conversion digest binding artifact mismatch")
        if self.binding_scope != RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE:
            raise ValueError("runtime layout conversion digest binding scope mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime layout conversion digest binding omits raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime layout conversion blocked surfaces changed")
        _validate_binding_rows(self.bindings)
        _validate_binding_issues(self.issues)
        expected_issues = _derive_issues(self)
        if self.issues != expected_issues:
            raise ValueError("runtime layout conversion binding issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the three source reports bind cleanly."""

        return not self.issues

    @property
    def binding_metadata_digest(self) -> str:
        """Return a digest over source metadata and binding rows only."""

        payload = {
            "artifact_id": self.artifact_id,
            "bindings": [_binding_row_to_dict(row) for row in self.bindings],
            "graph_name": self.graph_name,
            "source_hs_ir_alignment_metadata_digest": (
                self.source_hs_ir_alignment_metadata_digest
            ),
            "source_layout_conversion_metadata_digest": (
                self.source_layout_conversion_metadata_digest
            ),
            "source_partition_plan_digest": self.source_partition_plan_digest,
            "source_tensor_store_record_metadata_digest": (
                self.source_tensor_store_record_metadata_digest
            ),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return f"sha256:{sha256(encoded).hexdigest()}"


class RuntimeLayoutConversionDigestBindingError(AssertionError):
    """Raised when layout conversion digest binding fails."""


def build_runtime_layout_conversion_digest_binding_report(
    layout_conversion: RuntimeLayoutConversionEvidenceReport,
    hs_ir_alignment: RuntimeHsIrPlanAlignmentReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
) -> RuntimeLayoutConversionDigestBindingReport:
    """Build data-only binding evidence across the three source reports."""

    if not isinstance(layout_conversion, RuntimeLayoutConversionEvidenceReport):
        raise TypeError("layout conversion digest binding requires layout evidence")
    if not isinstance(hs_ir_alignment, RuntimeHsIrPlanAlignmentReport):
        raise TypeError("layout conversion digest binding requires HS-IR alignment")
    if not isinstance(tensor_store, RuntimeTensorStoreEvidenceReport):
        raise TypeError("layout conversion digest binding requires tensor store evidence")

    hs_steps = {step.operation_name: step for step in hs_ir_alignment.steps}
    tensor_records = {record.tensor_name: record for record in tensor_store.records}
    bindings = tuple(
        _binding_row_for_conversion(conversion, hs_steps, tensor_records)
        for conversion in layout_conversion.conversions
    )
    issues = _derive_issues_from_values(
        graph_name=layout_conversion.graph_name,
        source_hs_ir_graph_name=hs_ir_alignment.graph_name,
        source_tensor_store_graph_name=tensor_store.graph_name,
        source_layout_conversion_passed=layout_conversion.passed,
        source_layout_conversion_issue_count=len(layout_conversion.issues),
        source_layout_conversion_count=len(layout_conversion.conversions),
        source_layout_conversion_total_planned_bytes=(
            layout_conversion.total_planned_bytes
        ),
        source_hs_ir_alignment_passed=hs_ir_alignment.passed,
        source_hs_ir_issue_count=len(hs_ir_alignment.issues),
        source_hs_ir_layout_conversion_count=(
            hs_ir_alignment.partition_layout_conversion_count
        ),
        source_hs_ir_total_layout_conversion_bytes=(
            hs_ir_alignment.partition_total_layout_conversion_bytes
        ),
        source_tensor_store_passed=tensor_store.passed,
        source_tensor_store_issue_count=len(tensor_store.issues),
        bindings=bindings,
    )
    return RuntimeLayoutConversionDigestBindingReport(
        graph_name=layout_conversion.graph_name,
        source_hs_ir_graph_name=hs_ir_alignment.graph_name,
        source_tensor_store_graph_name=tensor_store.graph_name,
        source_layout_conversion_contract=layout_conversion.evidence_contract,
        source_layout_conversion_schema_version=(
            RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION
        ),
        source_layout_conversion_passed=layout_conversion.passed,
        source_layout_conversion_issue_count=len(layout_conversion.issues),
        source_layout_conversion_count=len(layout_conversion.conversions),
        source_layout_conversion_total_planned_bytes=(
            layout_conversion.total_planned_bytes
        ),
        source_layout_conversion_metadata_digest=(
            layout_conversion.conversion_metadata_digest
        ),
        source_partition_plan_digest=layout_conversion.source_partition_plan_digest,
        source_hs_ir_alignment_contract=hs_ir_alignment.alignment_contract,
        source_hs_ir_alignment_schema_version=(
            RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION
        ),
        source_hs_ir_alignment_passed=hs_ir_alignment.passed,
        source_hs_ir_issue_count=len(hs_ir_alignment.issues),
        source_hs_ir_step_count=hs_ir_alignment.step_count,
        source_hs_ir_layout_conversion_count=(
            hs_ir_alignment.partition_layout_conversion_count
        ),
        source_hs_ir_total_layout_conversion_bytes=(
            hs_ir_alignment.partition_total_layout_conversion_bytes
        ),
        source_hs_ir_alignment_metadata_digest=(
            hs_ir_alignment.alignment_metadata_digest
        ),
        source_tensor_store_evidence_contract=tensor_store.evidence_contract,
        source_tensor_store_evidence_schema_version=(
            RUNTIME_TENSOR_STORE_EVIDENCE_REPORT_SCHEMA_VERSION
        ),
        source_tensor_store_passed=tensor_store.passed,
        source_tensor_store_issue_count=len(tensor_store.issues),
        source_tensor_store_record_count=len(tensor_store.records),
        source_tensor_store_record_metadata_digest=(
            tensor_store.record_metadata_digest
        ),
        bindings=bindings,
        issues=issues,
    )

def assert_runtime_layout_conversion_digest_binding(
    report: RuntimeLayoutConversionDigestBindingReport,
) -> RuntimeLayoutConversionDigestBindingReport:
    """Return the report or raise when digest binding fails."""

    if not isinstance(report, RuntimeLayoutConversionDigestBindingReport):
        raise TypeError("layout conversion digest binding report required")
    if report.issues:
        lines = [
            f"runtime layout conversion digest binding failed for {report.graph_name!r}:"
        ]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeLayoutConversionDigestBindingError("\n".join(lines))
    return report


def runtime_layout_conversion_digest_binding_report_to_dict(
    report: RuntimeLayoutConversionDigestBindingReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible digest binding data."""

    if not isinstance(report, RuntimeLayoutConversionDigestBindingReport):
        raise TypeError("layout conversion digest binding report required")
    return {
        "artifact_id": report.artifact_id,
        "artifact_status": report.artifact_status,
        "binding_contract": report.binding_contract,
        "binding_count": len(report.bindings),
        "binding_metadata_digest": report.binding_metadata_digest,
        "binding_scope": report.binding_scope,
        "bindings": [_binding_row_to_dict(row) for row in report.bindings],
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "graph_name": report.graph_name,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "schema_version": (
            RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_SCHEMA_VERSION
        ),
        "source_hs_ir_alignment_contract": report.source_hs_ir_alignment_contract,
        "source_hs_ir_alignment_metadata_digest": (
            report.source_hs_ir_alignment_metadata_digest
        ),
        "source_hs_ir_alignment_passed": report.source_hs_ir_alignment_passed,
        "source_hs_ir_alignment_schema_version": (
            report.source_hs_ir_alignment_schema_version
        ),
        "source_hs_ir_graph_name": report.source_hs_ir_graph_name,
        "source_hs_ir_issue_count": report.source_hs_ir_issue_count,
        "source_hs_ir_layout_conversion_count": (
            report.source_hs_ir_layout_conversion_count
        ),
        "source_hs_ir_step_count": report.source_hs_ir_step_count,
        "source_hs_ir_total_layout_conversion_bytes": (
            report.source_hs_ir_total_layout_conversion_bytes
        ),
        "source_layout_conversion_contract": (
            report.source_layout_conversion_contract
        ),
        "source_layout_conversion_count": report.source_layout_conversion_count,
        "source_layout_conversion_issue_count": (
            report.source_layout_conversion_issue_count
        ),
        "source_layout_conversion_metadata_digest": (
            report.source_layout_conversion_metadata_digest
        ),
        "source_layout_conversion_passed": report.source_layout_conversion_passed,
        "source_layout_conversion_schema_version": (
            report.source_layout_conversion_schema_version
        ),
        "source_layout_conversion_total_planned_bytes": (
            report.source_layout_conversion_total_planned_bytes
        ),
        "source_partition_plan_digest": report.source_partition_plan_digest,
        "source_tensor_store_evidence_contract": (
            report.source_tensor_store_evidence_contract
        ),
        "source_tensor_store_evidence_schema_version": (
            report.source_tensor_store_evidence_schema_version
        ),
        "source_tensor_store_graph_name": report.source_tensor_store_graph_name,
        "source_tensor_store_issue_count": report.source_tensor_store_issue_count,
        "source_tensor_store_passed": report.source_tensor_store_passed,
        "source_tensor_store_record_count": report.source_tensor_store_record_count,
        "source_tensor_store_record_metadata_digest": (
            report.source_tensor_store_record_metadata_digest
        ),
    }


def dump_runtime_layout_conversion_digest_binding_report(
    report: RuntimeLayoutConversionDigestBindingReport,
) -> str:
    """Render stable data-only layout-conversion digest binding evidence."""

    text = json.dumps(
        runtime_layout_conversion_digest_binding_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_BYTES
    ):
        raise ValueError("runtime layout conversion digest binding report too large")
    return text + "\n"


def _binding_row_for_conversion(
    conversion: RuntimeLayoutConversionRecord,
    hs_steps: Mapping[str, object],
    tensor_records: dict[str, RuntimeTensorValueEvidence],
) -> RuntimeLayoutConversionDigestBindingRow:
    source_step = hs_steps.get(conversion.source_operation)
    target_step = hs_steps.get(conversion.target_operation)
    source_record = tensor_records.get(conversion.tensor_name)
    hs_ir_source_backend = _get_text(source_step, "hs_ir_backend")
    hs_ir_target_backend = _get_text(target_step, "hs_ir_backend")
    hs_ir_source_layout = _get_text(source_step, "hs_ir_produced_layout")
    hs_ir_target_layout = _get_text(target_step, "hs_ir_produced_layout")
    hs_ir_target_layout_conversion_bytes = _get_int(
        target_step,
        "layout_conversion_bytes",
    )
    tensor_store_source_backend = (
        "missing" if source_record is None else source_record.planned_backend
    )
    tensor_store_source_memory_domain = (
        "missing" if source_record is None else source_record.planned_memory_domain.value
    )
    tensor_store_source_layout = (
        "missing" if source_record is None else source_record.planned_layout.value
    )
    tensor_store_source_producer_id = (
        "missing" if source_record is None else source_record.producer_id
    )
    issue_code = _row_issue_code_from_values(
        source_operation=conversion.source_operation,
        layout_conversion_from_backend=conversion.from_backend,
        layout_conversion_to_backend=conversion.to_backend,
        layout_conversion_from_memory_domain=conversion.from_memory_domain.value,
        layout_conversion_from_layout=conversion.from_layout.value,
        layout_conversion_to_layout=conversion.to_layout.value,
        planned_bytes=conversion.planned_bytes,
        hs_ir_source_backend=hs_ir_source_backend,
        hs_ir_target_backend=hs_ir_target_backend,
        hs_ir_source_layout=hs_ir_source_layout,
        hs_ir_target_layout=hs_ir_target_layout,
        hs_ir_target_layout_conversion_bytes=hs_ir_target_layout_conversion_bytes,
        tensor_store_source_backend=tensor_store_source_backend,
        tensor_store_source_memory_domain=tensor_store_source_memory_domain,
        tensor_store_source_layout=tensor_store_source_layout,
        tensor_store_source_producer_id=tensor_store_source_producer_id,
    )
    return RuntimeLayoutConversionDigestBindingRow(
        conversion_id=conversion.conversion_id,
        tensor_name=conversion.tensor_name,
        source_operation=conversion.source_operation,
        target_operation=conversion.target_operation,
        source_value_record_id=conversion.source_value_record_id,
        consumer_input_id=conversion.consumer_input_id,
        layout_conversion_from_backend=conversion.from_backend,
        layout_conversion_to_backend=conversion.to_backend,
        layout_conversion_from_memory_domain=conversion.from_memory_domain.value,
        layout_conversion_to_memory_domain=conversion.to_memory_domain.value,
        layout_conversion_from_layout=conversion.from_layout.value,
        layout_conversion_to_layout=conversion.to_layout.value,
        planned_bytes=conversion.planned_bytes,
        hs_ir_source_backend=hs_ir_source_backend,
        hs_ir_target_backend=hs_ir_target_backend,
        hs_ir_source_layout=hs_ir_source_layout,
        hs_ir_target_layout=hs_ir_target_layout,
        hs_ir_target_layout_conversion_bytes=hs_ir_target_layout_conversion_bytes,
        tensor_store_source_backend=tensor_store_source_backend,
        tensor_store_source_memory_domain=tensor_store_source_memory_domain,
        tensor_store_source_layout=tensor_store_source_layout,
        tensor_store_source_producer_id=tensor_store_source_producer_id,
        binding_status=(
            "bound"
            if issue_code == RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE
            else "failed"
        ),
        issue_code=issue_code,
    )


def _binding_row_to_dict(
    row: RuntimeLayoutConversionDigestBindingRow,
) -> dict[str, object]:
    return {
        "binding_status": row.binding_status,
        "consumer_input_id": row.consumer_input_id,
        "conversion_id": row.conversion_id,
        "hs_ir_source_backend": row.hs_ir_source_backend,
        "hs_ir_source_layout": row.hs_ir_source_layout,
        "hs_ir_target_backend": row.hs_ir_target_backend,
        "hs_ir_target_layout": row.hs_ir_target_layout,
        "hs_ir_target_layout_conversion_bytes": (
            row.hs_ir_target_layout_conversion_bytes
        ),
        "issue_code": row.issue_code,
        "layout_conversion_from_backend": row.layout_conversion_from_backend,
        "layout_conversion_from_layout": row.layout_conversion_from_layout,
        "layout_conversion_from_memory_domain": (
            row.layout_conversion_from_memory_domain
        ),
        "layout_conversion_to_backend": row.layout_conversion_to_backend,
        "layout_conversion_to_layout": row.layout_conversion_to_layout,
        "layout_conversion_to_memory_domain": row.layout_conversion_to_memory_domain,
        "planned_bytes": row.planned_bytes,
        "source_operation": row.source_operation,
        "source_value_record_id": row.source_value_record_id,
        "target_operation": row.target_operation,
        "tensor_name": row.tensor_name,
        "tensor_store_source_backend": row.tensor_store_source_backend,
        "tensor_store_source_layout": row.tensor_store_source_layout,
        "tensor_store_source_memory_domain": row.tensor_store_source_memory_domain,
        "tensor_store_source_producer_id": row.tensor_store_source_producer_id,
    }


def _derive_issues(
    report: RuntimeLayoutConversionDigestBindingReport,
) -> tuple[RuntimeLayoutConversionDigestBindingIssue, ...]:
    return _derive_issues_from_values(
        graph_name=report.graph_name,
        source_hs_ir_graph_name=report.source_hs_ir_graph_name,
        source_tensor_store_graph_name=report.source_tensor_store_graph_name,
        source_layout_conversion_passed=report.source_layout_conversion_passed,
        source_layout_conversion_issue_count=(
            report.source_layout_conversion_issue_count
        ),
        source_layout_conversion_count=report.source_layout_conversion_count,
        source_layout_conversion_total_planned_bytes=(
            report.source_layout_conversion_total_planned_bytes
        ),
        source_hs_ir_alignment_passed=report.source_hs_ir_alignment_passed,
        source_hs_ir_issue_count=report.source_hs_ir_issue_count,
        source_hs_ir_layout_conversion_count=(
            report.source_hs_ir_layout_conversion_count
        ),
        source_hs_ir_total_layout_conversion_bytes=(
            report.source_hs_ir_total_layout_conversion_bytes
        ),
        source_tensor_store_passed=report.source_tensor_store_passed,
        source_tensor_store_issue_count=report.source_tensor_store_issue_count,
        bindings=report.bindings,
    )


def _derive_issues_from_values(
    *,
    graph_name: str,
    source_hs_ir_graph_name: str,
    source_tensor_store_graph_name: str,
    source_layout_conversion_passed: bool,
    source_layout_conversion_issue_count: int,
    source_layout_conversion_count: int,
    source_layout_conversion_total_planned_bytes: int,
    source_hs_ir_alignment_passed: bool,
    source_hs_ir_issue_count: int,
    source_hs_ir_layout_conversion_count: int,
    source_hs_ir_total_layout_conversion_bytes: int,
    source_tensor_store_passed: bool,
    source_tensor_store_issue_count: int,
    bindings: tuple[RuntimeLayoutConversionDigestBindingRow, ...],
) -> tuple[RuntimeLayoutConversionDigestBindingIssue, ...]:
    issues: list[RuntimeLayoutConversionDigestBindingIssue] = []
    if graph_name != source_hs_ir_graph_name:
        issues.append(_issue("graph", "hs_ir_graph_mismatch"))
    if graph_name != source_tensor_store_graph_name:
        issues.append(_issue("graph", "tensor_store_graph_mismatch"))
    if not source_layout_conversion_passed or source_layout_conversion_issue_count:
        issues.append(_issue("source_layout_conversion", "source_report_failed"))
    if not source_layout_conversion_count:
        issues.append(_issue("source_layout_conversion", "source_report_empty"))
    if not source_hs_ir_alignment_passed or source_hs_ir_issue_count:
        issues.append(_issue("source_hs_ir_alignment", "source_report_failed"))
    if not source_tensor_store_passed or source_tensor_store_issue_count:
        issues.append(_issue("source_tensor_store", "source_report_failed"))
    if source_layout_conversion_count != source_hs_ir_layout_conversion_count:
        issues.append(_issue("layout_conversion_count", "hs_ir_count_mismatch"))
    if (
        source_layout_conversion_total_planned_bytes
        != source_hs_ir_total_layout_conversion_bytes
    ):
        issues.append(_issue("layout_conversion_bytes", "hs_ir_bytes_mismatch"))
    if len(bindings) != source_layout_conversion_count:
        issues.append(_issue("bindings", "binding_row_count_mismatch"))
    for row in bindings:
        issue_code = _row_issue_code(row)
        if issue_code != RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE:
            issues.append(_issue(row.conversion_id, issue_code))
    if len(issues) > MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ISSUES:
        raise ValueError("runtime layout conversion digest binding issue limit exceeded")
    return tuple(dict.fromkeys(issues))


def _row_issue_code(row: RuntimeLayoutConversionDigestBindingRow) -> str:
    return _row_issue_code_from_values(
        source_operation=row.source_operation,
        layout_conversion_from_backend=row.layout_conversion_from_backend,
        layout_conversion_to_backend=row.layout_conversion_to_backend,
        layout_conversion_from_memory_domain=(
            row.layout_conversion_from_memory_domain
        ),
        layout_conversion_from_layout=row.layout_conversion_from_layout,
        layout_conversion_to_layout=row.layout_conversion_to_layout,
        planned_bytes=row.planned_bytes,
        hs_ir_source_backend=row.hs_ir_source_backend,
        hs_ir_target_backend=row.hs_ir_target_backend,
        hs_ir_source_layout=row.hs_ir_source_layout,
        hs_ir_target_layout=row.hs_ir_target_layout,
        hs_ir_target_layout_conversion_bytes=(
            row.hs_ir_target_layout_conversion_bytes
        ),
        tensor_store_source_backend=row.tensor_store_source_backend,
        tensor_store_source_memory_domain=row.tensor_store_source_memory_domain,
        tensor_store_source_layout=row.tensor_store_source_layout,
        tensor_store_source_producer_id=row.tensor_store_source_producer_id,
    )


def _row_issue_code_from_values(
    *,
    source_operation: str,
    layout_conversion_from_backend: str,
    layout_conversion_to_backend: str,
    layout_conversion_from_memory_domain: str,
    layout_conversion_from_layout: str,
    layout_conversion_to_layout: str,
    planned_bytes: int,
    hs_ir_source_backend: str,
    hs_ir_target_backend: str,
    hs_ir_source_layout: str,
    hs_ir_target_layout: str,
    hs_ir_target_layout_conversion_bytes: int,
    tensor_store_source_backend: str,
    tensor_store_source_memory_domain: str,
    tensor_store_source_layout: str,
    tensor_store_source_producer_id: str,
) -> str:
    if hs_ir_source_backend == "missing" or hs_ir_target_backend == "missing":
        return "hs_ir_step_missing"
    if tensor_store_source_backend == "missing":
        return "source_tensor_record_missing"
    if layout_conversion_from_backend != hs_ir_source_backend:
        return "hs_ir_source_backend_mismatch"
    if layout_conversion_to_backend != hs_ir_target_backend:
        return "hs_ir_target_backend_mismatch"
    if layout_conversion_from_backend != tensor_store_source_backend:
        return "tensor_store_source_backend_mismatch"
    if layout_conversion_from_layout != hs_ir_source_layout:
        return "hs_ir_source_layout_mismatch"
    if layout_conversion_to_layout != hs_ir_target_layout:
        return "hs_ir_target_layout_mismatch"
    if layout_conversion_from_layout != tensor_store_source_layout:
        return "tensor_store_source_layout_mismatch"
    if layout_conversion_from_memory_domain != tensor_store_source_memory_domain:
        return "tensor_store_source_memory_domain_mismatch"
    if source_operation != tensor_store_source_producer_id:
        return "tensor_store_source_producer_mismatch"
    if planned_bytes != hs_ir_target_layout_conversion_bytes:
        return "hs_ir_layout_conversion_bytes_mismatch"
    return RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE


def _issue(
    subject: str,
    issue_code: str,
) -> RuntimeLayoutConversionDigestBindingIssue:
    return RuntimeLayoutConversionDigestBindingIssue(
        subject=subject,
        issue_code=issue_code,
    )


def _get_text(value: object, attribute: str) -> str:
    text = getattr(value, attribute, "missing")
    return text if isinstance(text, str) else "missing"


def _get_int(value: object, attribute: str) -> int:
    number = getattr(value, attribute, 0)
    return number if isinstance(number, int) and not isinstance(number, bool) else 0


def _validate_binding_rows(
    rows: tuple[RuntimeLayoutConversionDigestBindingRow, ...],
) -> None:
    if type(rows) is not tuple:
        raise TypeError("runtime layout conversion binding rows must be a tuple")
    if len(rows) > MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ROWS:
        raise ValueError("runtime layout conversion digest binding row limit exceeded")
    for row in rows:
        if not isinstance(row, RuntimeLayoutConversionDigestBindingRow):
            raise TypeError("runtime layout conversion binding rows must be row objects")


def _validate_binding_issues(
    issues: tuple[RuntimeLayoutConversionDigestBindingIssue, ...],
) -> None:
    if type(issues) is not tuple:
        raise TypeError("runtime layout conversion binding issues must be a tuple")
    if len(issues) > MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ISSUES:
        raise ValueError("runtime layout conversion digest binding issue limit exceeded")
    for issue in issues:
        if not isinstance(issue, RuntimeLayoutConversionDigestBindingIssue):
            raise TypeError(
                "runtime layout conversion binding issues must be issue objects"
            )


def _validate_binding_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _BINDING_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe layout conversion binding identifier")
    if len(value.encode("utf-8")) > (
        MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_FIELD_BYTES
    ):
        raise ValueError(f"{label} exceeds layout conversion binding field limit")
    if value in _FORBIDDEN_BINDING_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _validate_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")


__all__ = [
    "MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_FIELD_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ISSUES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_BYTES",
    "MAX_RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ROWS",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_STATUS",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_CONTRACT",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_NO_ISSUE",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_REPORT_SCHEMA_VERSION",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_SCOPE",
    "RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_STATUSES",
    "RuntimeLayoutConversionDigestBindingError",
    "RuntimeLayoutConversionDigestBindingIssue",
    "RuntimeLayoutConversionDigestBindingReport",
    "RuntimeLayoutConversionDigestBindingRow",
    "assert_runtime_layout_conversion_digest_binding",
    "build_runtime_layout_conversion_digest_binding_report",
    "dump_runtime_layout_conversion_digest_binding_report",
    "runtime_layout_conversion_digest_binding_report_to_dict",
]
