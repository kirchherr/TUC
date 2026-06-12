"""Data-only bundle for one trusted runtime execution evidence set."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.runtime.execution_receipt import (
    RuntimeExecutionReceiptReport,
    runtime_execution_receipt_report_to_dict,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.input_manifest import (
    RuntimeInputManifestReport,
    runtime_input_manifest_report_to_dict,
)
from tuc.runtime.output_manifest import (
    RuntimeOutputManifestReport,
    runtime_output_manifest_report_to_dict,
)
from tuc.runtime.reference_correctness import (
    RuntimeReferenceCorrectnessReport,
    runtime_reference_correctness_report_to_dict,
)
from tuc.runtime.tensor_store_evidence import (
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    RuntimeTensorStoreEvidenceReport,
    runtime_tensor_store_evidence_report_to_dict,
)

RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_execution_evidence_bundle_report.v0"
)
RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT = (
    "runtime_execution_evidence_bundle.data_only.v0"
)
RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS = "review_evidence"
RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY = "embedded_metadata_reports"
RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS = (
    "tensor_store_evidence",
    "input_manifest",
    "output_manifest",
    "reference_correctness",
    "execution_receipt",
)
MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ISSUES = 256
MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_BYTES = 128 * 1024
MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_FIELD_BYTES = 512

_BUNDLE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_BUNDLE_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "command_line",
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
        "raw_output_value",
        "raw_tensor_value",
        "raw_timing_samples",
        "reference_value",
        "source_text",
        "subprocess",
        "tensor_value",
        "tensor_values",
        "url",
        "value",
        "values",
    }
)


@dataclass(frozen=True)
class RuntimeExecutionEvidenceBundleIssue:
    """One derived runtime execution evidence bundle issue."""

    section: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_bundle_text(self.section, "bundle issue section")
        _validate_bundle_text(self.issue_code, "bundle issue_code")


@dataclass(frozen=True)
class RuntimeExecutionEvidenceBundleReport:
    """Deterministic bundle of one runtime execution's metadata-only evidence."""

    graph_name: str
    tensor_store_report: RuntimeTensorStoreEvidenceReport
    input_manifest_report: RuntimeInputManifestReport
    output_manifest_report: RuntimeOutputManifestReport
    reference_correctness_report: RuntimeReferenceCorrectnessReport
    execution_receipt_report: RuntimeExecutionReceiptReport
    issues: tuple[RuntimeExecutionEvidenceBundleIssue, ...]
    bundle_contract: str = RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT
    artifact_status: str = RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS
    linkage_policy: str = RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    report_sections: tuple[str, ...] = RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_bundle_text(self.graph_name, "runtime evidence bundle graph_name")
        if self.bundle_contract != RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT:
            raise ValueError("runtime execution evidence bundle contract mismatch")
        if self.artifact_status != RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS:
            raise ValueError("runtime execution evidence bundle artifact mismatch")
        if self.linkage_policy != RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY:
            raise ValueError("runtime execution evidence bundle linkage mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime execution evidence bundle must omit raw values")
        if self.report_sections != RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS:
            raise ValueError("runtime execution evidence bundle sections mismatch")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime execution evidence bundle blocked surfaces changed")
        _validate_report_objects(
            self.tensor_store_report,
            self.input_manifest_report,
            self.output_manifest_report,
            self.reference_correctness_report,
            self.execution_receipt_report,
        )
        if type(self.issues) is not tuple:
            raise TypeError("runtime execution evidence bundle issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ISSUES:
            raise ValueError("runtime execution evidence bundle issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeExecutionEvidenceBundleIssue):
                raise TypeError(
                    "runtime execution evidence bundle issues must be bundle issues"
                )
        expected_issues = _derive_issues(
            self.graph_name,
            self.tensor_store_report,
            self.input_manifest_report,
            self.output_manifest_report,
            self.reference_correctness_report,
            self.execution_receipt_report,
        )
        if self.issues != expected_issues:
            raise ValueError("runtime execution evidence bundle issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether the embedded evidence bundle passed."""

        return not self.issues

    @property
    def bundle_metadata_digest(self) -> str:
        """Return a digest over embedded evidence digests only."""

        payload = {
            "execution_receipt": self.execution_receipt_report.receipt_metadata_digest,
            "graph_name": self.graph_name,
            "input_manifest": self.input_manifest_report.input_metadata_digest,
            "output_manifest": self.output_manifest_report.output_metadata_digest,
            "reference_correctness": (
                self.reference_correctness_report.comparison_metadata_digest
            ),
            "tensor_store_evidence": self.tensor_store_report.record_metadata_digest,
        }
        return _metadata_digest(payload)


class RuntimeExecutionEvidenceBundleError(AssertionError):
    """Raised when runtime execution evidence bundle does not pass."""


def build_runtime_execution_evidence_bundle_report(
    tensor_store_report: RuntimeTensorStoreEvidenceReport,
    input_manifest_report: RuntimeInputManifestReport,
    output_manifest_report: RuntimeOutputManifestReport,
    reference_correctness_report: RuntimeReferenceCorrectnessReport,
    execution_receipt_report: RuntimeExecutionReceiptReport,
) -> RuntimeExecutionEvidenceBundleReport:
    """Build a data-only bundle from one execution's evidence reports."""

    _validate_report_objects(
        tensor_store_report,
        input_manifest_report,
        output_manifest_report,
        reference_correctness_report,
        execution_receipt_report,
    )
    graph_name = tensor_store_report.graph_name
    return RuntimeExecutionEvidenceBundleReport(
        graph_name=graph_name,
        tensor_store_report=tensor_store_report,
        input_manifest_report=input_manifest_report,
        output_manifest_report=output_manifest_report,
        reference_correctness_report=reference_correctness_report,
        execution_receipt_report=execution_receipt_report,
        issues=_derive_issues(
            graph_name,
            tensor_store_report,
            input_manifest_report,
            output_manifest_report,
            reference_correctness_report,
            execution_receipt_report,
        ),
    )


def assert_runtime_execution_evidence_bundle(
    report: RuntimeExecutionEvidenceBundleReport,
) -> RuntimeExecutionEvidenceBundleReport:
    """Return the report or raise when bundled evidence fails."""

    if not isinstance(report, RuntimeExecutionEvidenceBundleReport):
        raise TypeError("runtime execution evidence bundle must be report object")
    if report.issues:
        lines = [f"runtime execution evidence bundle failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.section}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeExecutionEvidenceBundleError("\n".join(lines))
    return report


def runtime_execution_evidence_bundle_report_to_dict(
    report: RuntimeExecutionEvidenceBundleReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible bundled runtime evidence."""

    if not isinstance(report, RuntimeExecutionEvidenceBundleReport):
        raise TypeError("runtime execution evidence bundle must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "bundle_contract": report.bundle_contract,
        "bundle_metadata_digest": report.bundle_metadata_digest,
        "execution_receipt": runtime_execution_receipt_report_to_dict(
            report.execution_receipt_report
        ),
        "graph_name": report.graph_name,
        "input_manifest": runtime_input_manifest_report_to_dict(
            report.input_manifest_report
        ),
        "issues": [
            {
                "issue_code": issue.issue_code,
                "section": issue.section,
            }
            for issue in report.issues
        ],
        "linkage_policy": report.linkage_policy,
        "output_manifest": runtime_output_manifest_report_to_dict(
            report.output_manifest_report
        ),
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "reference_correctness": runtime_reference_correctness_report_to_dict(
            report.reference_correctness_report
        ),
        "report_sections": list(report.report_sections),
        "schema_version": RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION,
        "tensor_store_evidence": runtime_tensor_store_evidence_report_to_dict(
            report.tensor_store_report
        ),
    }


def dump_runtime_execution_evidence_bundle_report(
    report: RuntimeExecutionEvidenceBundleReport,
) -> str:
    """Render stable data-only runtime execution evidence bundle."""

    text = json.dumps(
        runtime_execution_evidence_bundle_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_BYTES:
        raise ValueError("runtime execution evidence bundle report exceeds byte limit")
    return text + "\n"


def _derive_issues(
    graph_name: str,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    reference_correctness: RuntimeReferenceCorrectnessReport,
    execution_receipt: RuntimeExecutionReceiptReport,
) -> tuple[RuntimeExecutionEvidenceBundleIssue, ...]:
    issues: list[RuntimeExecutionEvidenceBundleIssue] = []
    report_checks = (
        ("tensor_store_evidence", tensor_store.graph_name, tensor_store.passed),
        ("input_manifest", input_manifest.graph_name, input_manifest.passed),
        ("output_manifest", output_manifest.graph_name, output_manifest.passed),
        (
            "reference_correctness",
            reference_correctness.graph_name,
            reference_correctness.passed,
        ),
        ("execution_receipt", execution_receipt.graph_name, execution_receipt.passed),
    )
    for section, report_graph_name, passed in report_checks:
        if report_graph_name != graph_name:
            issues.append(
                RuntimeExecutionEvidenceBundleIssue(
                    section=section,
                    issue_code="graph_name_mismatch",
                )
            )
        if not passed:
            issues.append(
                RuntimeExecutionEvidenceBundleIssue(
                    section=section,
                    issue_code="evidence_not_passed",
                )
            )

    receipt_links = {link.evidence_kind: link for link in execution_receipt.evidence_links}
    expected_links = {
        "tensor_store_evidence": (
            tensor_store.evidence_contract,
            tensor_store.graph_name,
            len(tensor_store.records),
            tensor_store.record_metadata_digest,
            tensor_store.passed,
            tensor_store.raw_value_policy,
        ),
        "input_manifest": (
            input_manifest.manifest_contract,
            input_manifest.graph_name,
            len(input_manifest.inputs),
            input_manifest.input_metadata_digest,
            input_manifest.passed,
            input_manifest.raw_value_policy,
        ),
        "output_manifest": (
            output_manifest.manifest_contract,
            output_manifest.graph_name,
            len(output_manifest.outputs),
            output_manifest.output_metadata_digest,
            output_manifest.passed,
            output_manifest.raw_value_policy,
        ),
        "reference_correctness": (
            reference_correctness.correctness_contract,
            reference_correctness.graph_name,
            len(reference_correctness.comparisons),
            reference_correctness.comparison_metadata_digest,
            reference_correctness.passed,
            reference_correctness.raw_value_policy,
        ),
    }
    fields = (
        "evidence_contract",
        "graph_name",
        "item_count",
        "metadata_digest",
        "passed",
        "raw_value_policy",
    )
    for section, expected in expected_links.items():
        link = receipt_links.get(section)
        if link is None:
            issues.append(
                RuntimeExecutionEvidenceBundleIssue(
                    section=section,
                    issue_code="missing_receipt_link",
                )
            )
            continue
        actual = (
            link.evidence_contract,
            link.graph_name,
            link.item_count,
            link.metadata_digest,
            link.passed,
            link.raw_value_policy,
        )
        for field_name, actual_value, expected_value in zip(
            fields,
            actual,
            expected,
            strict=True,
        ):
            if actual_value != expected_value:
                issues.append(
                    RuntimeExecutionEvidenceBundleIssue(
                        section=section,
                        issue_code=f"{field_name}_mismatch",
                    )
                )

    return tuple(issues)


def _validate_report_objects(
    tensor_store_report: RuntimeTensorStoreEvidenceReport,
    input_manifest_report: RuntimeInputManifestReport,
    output_manifest_report: RuntimeOutputManifestReport,
    reference_correctness_report: RuntimeReferenceCorrectnessReport,
    execution_receipt_report: RuntimeExecutionReceiptReport,
) -> None:
    if not isinstance(tensor_store_report, RuntimeTensorStoreEvidenceReport):
        raise TypeError("runtime evidence bundle tensor store report mismatch")
    if not isinstance(input_manifest_report, RuntimeInputManifestReport):
        raise TypeError("runtime evidence bundle input manifest report mismatch")
    if not isinstance(output_manifest_report, RuntimeOutputManifestReport):
        raise TypeError("runtime evidence bundle output manifest report mismatch")
    if not isinstance(reference_correctness_report, RuntimeReferenceCorrectnessReport):
        raise TypeError("runtime evidence bundle reference correctness report mismatch")
    if not isinstance(execution_receipt_report, RuntimeExecutionReceiptReport):
        raise TypeError("runtime evidence bundle execution receipt report mismatch")


def _validate_bundle_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _BUNDLE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime evidence bundle identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime evidence bundle field limit")
    if value in _FORBIDDEN_BUNDLE_TEXT:
        raise ValueError(f"{label} names a forbidden execution or value surface")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_FIELD_BYTES",
    "MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ISSUES",
    "MAX_RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_BYTES",
    "RUNTIME_EXECUTION_EVIDENCE_BUNDLE_ARTIFACT_STATUS",
    "RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT",
    "RUNTIME_EXECUTION_EVIDENCE_BUNDLE_LINKAGE_POLICY",
    "RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION",
    "RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS",
    "RuntimeExecutionEvidenceBundleError",
    "RuntimeExecutionEvidenceBundleIssue",
    "RuntimeExecutionEvidenceBundleReport",
    "assert_runtime_execution_evidence_bundle",
    "build_runtime_execution_evidence_bundle_report",
    "dump_runtime_execution_evidence_bundle_report",
    "runtime_execution_evidence_bundle_report_to_dict",
]
