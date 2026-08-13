"""Data-only closure audit for public runtime execution outputs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from types import SimpleNamespace
from typing import cast

from tuc.runtime.execution_evidence_bundle import (
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION,
    RuntimeExecutionEvidenceBundleReport,
)
from tuc.runtime.execution_receipt import (
    RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION,
    RuntimeExecutionReceiptReport,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.output_contract import (
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION,
    RuntimeOutputContractReport,
)
from tuc.runtime.public_output_bundle import (
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION,
    RuntimePublicOutputBundle,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_execution_output_closure_report.v0"
)
RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT = (
    "runtime_execution_output_closure.data_only.v0"
)
RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID = (
    "runtime_execution_output_closure.receipt_bundle_public_outputs.v0"
)
RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS = "closed_by_metadata_digest"
RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS = "closed"
RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS = (
    "output_contract",
    "public_output_bundle",
)
MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECKS = 2
MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_ISSUES = 64
MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_FIELD_BYTES = 512

_CLOSURE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_MISSING_CONTRACT = "missing"
_MISSING_DIGEST = "sha256:" + "0" * 64
_FORBIDDEN_CLOSURE_TEXT = frozenset(
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
class RuntimeExecutionOutputClosureCheck:
    """One source-vs-receipt-vs-bundle public output evidence check."""

    evidence_kind: str
    source_contract: str
    receipt_contract: str
    bundle_contract: str
    source_metadata_digest: str
    receipt_metadata_digest: str
    bundle_metadata_digest: str
    source_item_count: int
    receipt_item_count: int
    bundle_item_count: int
    row_status: str = RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS

    def __post_init__(self) -> None:
        _validate_text(self.evidence_kind, "output closure evidence_kind")
        _validate_text(self.source_contract, "output closure source_contract")
        _validate_text(self.receipt_contract, "output closure receipt_contract")
        _validate_text(self.bundle_contract, "output closure bundle_contract")
        _validate_digest(self.source_metadata_digest, "source_metadata_digest")
        _validate_digest(self.receipt_metadata_digest, "receipt_metadata_digest")
        _validate_digest(self.bundle_metadata_digest, "bundle_metadata_digest")
        _validate_count(self.source_item_count, "source_item_count")
        _validate_count(self.receipt_item_count, "receipt_item_count")
        _validate_count(self.bundle_item_count, "bundle_item_count")
        if self.row_status != RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS:
            raise ValueError("runtime execution output closure row status mismatch")


@dataclass(frozen=True)
class RuntimeExecutionOutputClosureIssue:
    """One derived runtime execution output closure issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "output closure issue subject")
        _validate_text(self.issue_code, "output closure issue_code")


@dataclass(frozen=True)
class RuntimeExecutionOutputClosureReport:
    """Deterministic audit that public outputs are closed over one execution."""

    graph_name: str
    source_output_contract_schema_version: str
    source_output_contract_metadata_digest: str
    source_output_contract_item_count: int
    source_output_contract_passed: bool
    source_public_output_bundle_schema_version: str
    source_public_output_bundle_metadata_digest: str
    source_public_output_bundle_item_count: int
    source_public_output_bundle_passed: bool
    source_execution_receipt_schema_version: str
    source_execution_receipt_metadata_digest: str
    source_execution_receipt_passed: bool
    source_execution_evidence_bundle_schema_version: str
    source_execution_evidence_bundle_metadata_digest: str
    source_execution_evidence_bundle_passed: bool
    source_bundle_execution_receipt_metadata_digest: str
    checks: tuple[RuntimeExecutionOutputClosureCheck, ...]
    issues: tuple[RuntimeExecutionOutputClosureIssue, ...]
    closure_contract: str = RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT
    closure_policy_id: str = RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID
    closure_status: str = RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "runtime execution output closure graph_name")
        if self.closure_contract != RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT:
            raise ValueError("runtime execution output closure contract mismatch")
        if self.closure_policy_id != RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID:
            raise ValueError("runtime execution output closure policy mismatch")
        if self.closure_status != RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS:
            raise ValueError("runtime execution output closure status mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime execution output closure must omit raw values")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime execution output closure blocked surfaces changed")
        if (
            self.source_output_contract_schema_version
            != RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("output closure output contract schema mismatch")
        if (
            self.source_public_output_bundle_schema_version
            != RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("output closure public bundle schema mismatch")
        if (
            self.source_execution_receipt_schema_version
            != RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("output closure receipt schema mismatch")
        if (
            self.source_execution_evidence_bundle_schema_version
            != RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("output closure bundle schema mismatch")
        _validate_digest(
            self.source_output_contract_metadata_digest,
            "source_output_contract_metadata_digest",
        )
        _validate_digest(
            self.source_public_output_bundle_metadata_digest,
            "source_public_output_bundle_metadata_digest",
        )
        _validate_digest(
            self.source_execution_receipt_metadata_digest,
            "source_execution_receipt_metadata_digest",
        )
        _validate_digest(
            self.source_execution_evidence_bundle_metadata_digest,
            "source_execution_evidence_bundle_metadata_digest",
        )
        _validate_digest(
            self.source_bundle_execution_receipt_metadata_digest,
            "source_bundle_execution_receipt_metadata_digest",
        )
        _validate_count(
            self.source_output_contract_item_count,
            "source_output_contract_item_count",
        )
        _validate_count(
            self.source_public_output_bundle_item_count,
            "source_public_output_bundle_item_count",
        )
        _validate_bool(self.source_output_contract_passed, "output contract passed")
        _validate_bool(
            self.source_public_output_bundle_passed,
            "public output bundle passed",
        )
        _validate_bool(
            self.source_execution_receipt_passed,
            "execution receipt passed",
        )
        _validate_bool(
            self.source_execution_evidence_bundle_passed,
            "execution evidence bundle passed",
        )
        _validate_checks(self.checks)
        if type(self.issues) is not tuple:
            raise TypeError("runtime execution output closure issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_ISSUES:
            raise ValueError("runtime execution output closure issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeExecutionOutputClosureIssue):
                raise TypeError("runtime execution output closure issues mismatch")
        expected_issues = _derive_issues(self)
        if self.issues != expected_issues:
            raise ValueError("runtime execution output closure issues must be derived")

    @property
    def passed(self) -> bool:
        """Return whether public output closure evidence passed."""

        return not self.issues

    @property
    def check_count(self) -> int:
        """Return the number of public output closure checks."""

        return len(self.checks)

    @property
    def closure_metadata_digest(self) -> str:
        """Return a digest over closure checks and source report digests."""

        payload = {
            "checks": [
                {
                    "bundle_contract": check.bundle_contract,
                    "bundle_item_count": check.bundle_item_count,
                    "bundle_metadata_digest": check.bundle_metadata_digest,
                    "evidence_kind": check.evidence_kind,
                    "receipt_contract": check.receipt_contract,
                    "receipt_item_count": check.receipt_item_count,
                    "receipt_metadata_digest": check.receipt_metadata_digest,
                    "row_status": check.row_status,
                    "source_contract": check.source_contract,
                    "source_item_count": check.source_item_count,
                    "source_metadata_digest": check.source_metadata_digest,
                }
                for check in self.checks
            ],
            "graph_name": self.graph_name,
            "source_execution_evidence_bundle_metadata_digest": (
                self.source_execution_evidence_bundle_metadata_digest
            ),
            "source_execution_receipt_metadata_digest": (
                self.source_execution_receipt_metadata_digest
            ),
            "source_output_contract_metadata_digest": (
                self.source_output_contract_metadata_digest
            ),
            "source_public_output_bundle_metadata_digest": (
                self.source_public_output_bundle_metadata_digest
            ),
        }
        return _metadata_digest(payload)


class RuntimeExecutionOutputClosureError(AssertionError):
    """Raised when runtime execution output closure evidence does not pass."""


def build_runtime_execution_output_closure_report(
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    execution_receipt: RuntimeExecutionReceiptReport,
    execution_evidence_bundle: RuntimeExecutionEvidenceBundleReport,
) -> RuntimeExecutionOutputClosureReport:
    """Build data-only proof that public outputs are closed over execution."""

    if not isinstance(output_contract, RuntimeOutputContractReport):
        raise TypeError("output closure output contract report mismatch")
    if not isinstance(public_output_bundle, RuntimePublicOutputBundle):
        raise TypeError("output closure public output bundle mismatch")
    if not isinstance(execution_receipt, RuntimeExecutionReceiptReport):
        raise TypeError("output closure execution receipt mismatch")
    if not isinstance(execution_evidence_bundle, RuntimeExecutionEvidenceBundleReport):
        raise TypeError("output closure execution evidence bundle mismatch")

    checks = _build_checks(
        output_contract,
        public_output_bundle,
        execution_receipt,
        execution_evidence_bundle,
    )
    graph_name = output_contract.graph_name
    source_output_contract_schema_version = RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION
    source_output_contract_metadata_digest = output_contract.contract_metadata_digest
    source_output_contract_item_count = len(output_contract.public_outputs)
    source_output_contract_passed = output_contract.passed
    source_public_output_bundle_schema_version = (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION
    )
    source_public_output_bundle_metadata_digest = public_output_bundle.bundle_metadata_digest
    source_public_output_bundle_item_count = len(public_output_bundle.outputs)
    source_public_output_bundle_passed = public_output_bundle.passed
    source_execution_receipt_schema_version = (
        RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION
    )
    source_execution_receipt_metadata_digest = execution_receipt.receipt_metadata_digest
    source_execution_receipt_passed = execution_receipt.passed
    source_execution_evidence_bundle_schema_version = (
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION
    )
    source_execution_evidence_bundle_metadata_digest = (
        execution_evidence_bundle.bundle_metadata_digest
    )
    source_execution_evidence_bundle_passed = execution_evidence_bundle.passed
    source_bundle_execution_receipt_metadata_digest = (
        execution_evidence_bundle.execution_receipt_report.receipt_metadata_digest
    )
    issue_view = cast(
        RuntimeExecutionOutputClosureReport,
        SimpleNamespace(
            graph_name=graph_name,
            source_output_contract_schema_version=(
                source_output_contract_schema_version
            ),
            source_output_contract_metadata_digest=(
                source_output_contract_metadata_digest
            ),
            source_output_contract_item_count=source_output_contract_item_count,
            source_output_contract_passed=source_output_contract_passed,
            source_public_output_bundle_schema_version=(
                source_public_output_bundle_schema_version
            ),
            source_public_output_bundle_metadata_digest=(
                source_public_output_bundle_metadata_digest
            ),
            source_public_output_bundle_item_count=(
                source_public_output_bundle_item_count
            ),
            source_public_output_bundle_passed=source_public_output_bundle_passed,
            source_execution_receipt_schema_version=(
                source_execution_receipt_schema_version
            ),
            source_execution_receipt_metadata_digest=(
                source_execution_receipt_metadata_digest
            ),
            source_execution_receipt_passed=source_execution_receipt_passed,
            source_execution_evidence_bundle_schema_version=(
                source_execution_evidence_bundle_schema_version
            ),
            source_execution_evidence_bundle_metadata_digest=(
                source_execution_evidence_bundle_metadata_digest
            ),
            source_execution_evidence_bundle_passed=(
                source_execution_evidence_bundle_passed
            ),
            source_bundle_execution_receipt_metadata_digest=(
                source_bundle_execution_receipt_metadata_digest
            ),
            checks=checks,
        ),
    )
    return RuntimeExecutionOutputClosureReport(
        graph_name=graph_name,
        source_output_contract_schema_version=source_output_contract_schema_version,
        source_output_contract_metadata_digest=source_output_contract_metadata_digest,
        source_output_contract_item_count=source_output_contract_item_count,
        source_output_contract_passed=source_output_contract_passed,
        source_public_output_bundle_schema_version=(
            source_public_output_bundle_schema_version
        ),
        source_public_output_bundle_metadata_digest=(
            source_public_output_bundle_metadata_digest
        ),
        source_public_output_bundle_item_count=source_public_output_bundle_item_count,
        source_public_output_bundle_passed=source_public_output_bundle_passed,
        source_execution_receipt_schema_version=(
            source_execution_receipt_schema_version
        ),
        source_execution_receipt_metadata_digest=source_execution_receipt_metadata_digest,
        source_execution_receipt_passed=source_execution_receipt_passed,
        source_execution_evidence_bundle_schema_version=(
            source_execution_evidence_bundle_schema_version
        ),
        source_execution_evidence_bundle_metadata_digest=(
            source_execution_evidence_bundle_metadata_digest
        ),
        source_execution_evidence_bundle_passed=source_execution_evidence_bundle_passed,
        source_bundle_execution_receipt_metadata_digest=(
            source_bundle_execution_receipt_metadata_digest
        ),
        checks=checks,
        issues=_derive_issues(issue_view),
    )

def assert_runtime_execution_output_closure(
    report: RuntimeExecutionOutputClosureReport,
) -> RuntimeExecutionOutputClosureReport:
    """Return the report or raise when public output closure fails."""

    if not isinstance(report, RuntimeExecutionOutputClosureReport):
        raise TypeError("runtime execution output closure must be report object")
    if report.issues:
        lines = [f"runtime execution output closure failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeExecutionOutputClosureError("\n".join(lines))
    return report


def runtime_execution_output_closure_report_to_dict(
    report: RuntimeExecutionOutputClosureReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible output closure evidence."""

    if not isinstance(report, RuntimeExecutionOutputClosureReport):
        raise TypeError("runtime execution output closure must be report object")
    return {
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "check_count": report.check_count,
        "checks": [
            {
                "bundle_contract": check.bundle_contract,
                "bundle_item_count": check.bundle_item_count,
                "bundle_metadata_digest": check.bundle_metadata_digest,
                "evidence_kind": check.evidence_kind,
                "receipt_contract": check.receipt_contract,
                "receipt_item_count": check.receipt_item_count,
                "receipt_metadata_digest": check.receipt_metadata_digest,
                "row_status": check.row_status,
                "source_contract": check.source_contract,
                "source_item_count": check.source_item_count,
                "source_metadata_digest": check.source_metadata_digest,
            }
            for check in report.checks
        ],
        "closure_contract": report.closure_contract,
        "closure_metadata_digest": report.closure_metadata_digest,
        "closure_policy_id": report.closure_policy_id,
        "closure_status": report.closure_status,
        "graph_name": report.graph_name,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "schema_version": RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION,
        "source_bundle_execution_receipt_metadata_digest": (
            report.source_bundle_execution_receipt_metadata_digest
        ),
        "source_execution_evidence_bundle_metadata_digest": (
            report.source_execution_evidence_bundle_metadata_digest
        ),
        "source_execution_evidence_bundle_passed": (
            report.source_execution_evidence_bundle_passed
        ),
        "source_execution_evidence_bundle_schema_version": (
            report.source_execution_evidence_bundle_schema_version
        ),
        "source_execution_receipt_metadata_digest": (
            report.source_execution_receipt_metadata_digest
        ),
        "source_execution_receipt_passed": report.source_execution_receipt_passed,
        "source_execution_receipt_schema_version": (
            report.source_execution_receipt_schema_version
        ),
        "source_output_contract_item_count": report.source_output_contract_item_count,
        "source_output_contract_metadata_digest": (
            report.source_output_contract_metadata_digest
        ),
        "source_output_contract_passed": report.source_output_contract_passed,
        "source_output_contract_schema_version": (
            report.source_output_contract_schema_version
        ),
        "source_public_output_bundle_item_count": (
            report.source_public_output_bundle_item_count
        ),
        "source_public_output_bundle_metadata_digest": (
            report.source_public_output_bundle_metadata_digest
        ),
        "source_public_output_bundle_passed": (
            report.source_public_output_bundle_passed
        ),
        "source_public_output_bundle_schema_version": (
            report.source_public_output_bundle_schema_version
        ),
    }


def dump_runtime_execution_output_closure_report(
    report: RuntimeExecutionOutputClosureReport,
) -> str:
    """Render stable metadata-only runtime execution output closure evidence."""

    text = json.dumps(
        runtime_execution_output_closure_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_BYTES:
        raise ValueError("runtime execution output closure report exceeds byte limit")
    return text + "\n"


def _build_checks(
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    execution_receipt: RuntimeExecutionReceiptReport,
    execution_evidence_bundle: RuntimeExecutionEvidenceBundleReport,
) -> tuple[RuntimeExecutionOutputClosureCheck, ...]:
    links = {link.evidence_kind: link for link in execution_receipt.evidence_links}
    output_contract_link = links.get("output_contract")
    public_output_bundle_link = links.get("public_output_bundle")
    return (
        RuntimeExecutionOutputClosureCheck(
            evidence_kind="output_contract",
            source_contract=output_contract.output_contract,
            receipt_contract=(
                output_contract_link.evidence_contract
                if output_contract_link is not None
                else _MISSING_CONTRACT
            ),
            bundle_contract=execution_evidence_bundle.output_contract_report.output_contract,
            source_metadata_digest=output_contract.contract_metadata_digest,
            receipt_metadata_digest=(
                output_contract_link.metadata_digest
                if output_contract_link is not None
                else _MISSING_DIGEST
            ),
            bundle_metadata_digest=(
                execution_evidence_bundle.output_contract_report.contract_metadata_digest
            ),
            source_item_count=len(output_contract.public_outputs),
            receipt_item_count=(
                output_contract_link.item_count if output_contract_link is not None else 0
            ),
            bundle_item_count=len(
                execution_evidence_bundle.output_contract_report.public_outputs
            ),
        ),
        RuntimeExecutionOutputClosureCheck(
            evidence_kind="public_output_bundle",
            source_contract=public_output_bundle.bundle_contract,
            receipt_contract=(
                public_output_bundle_link.evidence_contract
                if public_output_bundle_link is not None
                else _MISSING_CONTRACT
            ),
            bundle_contract=execution_evidence_bundle.public_output_bundle.bundle_contract,
            source_metadata_digest=public_output_bundle.bundle_metadata_digest,
            receipt_metadata_digest=(
                public_output_bundle_link.metadata_digest
                if public_output_bundle_link is not None
                else _MISSING_DIGEST
            ),
            bundle_metadata_digest=(
                execution_evidence_bundle.public_output_bundle.bundle_metadata_digest
            ),
            source_item_count=len(public_output_bundle.outputs),
            receipt_item_count=(
                public_output_bundle_link.item_count
                if public_output_bundle_link is not None
                else 0
            ),
            bundle_item_count=len(execution_evidence_bundle.public_output_bundle.outputs),
        ),
    )


def _derive_issues(
    report: RuntimeExecutionOutputClosureReport,
) -> tuple[RuntimeExecutionOutputClosureIssue, ...]:
    issues: list[RuntimeExecutionOutputClosureIssue] = []
    if not report.source_output_contract_passed:
        issues.append(_issue("output_contract", "source_report_failed"))
    if not report.source_public_output_bundle_passed:
        issues.append(_issue("public_output_bundle", "source_report_failed"))
    if not report.source_execution_receipt_passed:
        issues.append(_issue("execution_receipt", "source_report_failed"))
    if not report.source_execution_evidence_bundle_passed:
        issues.append(_issue("execution_evidence_bundle", "source_report_failed"))
    if (
        report.source_bundle_execution_receipt_metadata_digest
        != report.source_execution_receipt_metadata_digest
    ):
        issues.append(
            _issue("execution_evidence_bundle", "execution_receipt_digest_mismatch")
        )

    checks_by_kind = {check.evidence_kind: check for check in report.checks}
    if len(checks_by_kind) != len(report.checks):
        issues.append(_issue("checks", "duplicate_evidence_kind"))
    expected = {
        "output_contract": (
            RUNTIME_OUTPUT_CONTRACT,
            report.source_output_contract_metadata_digest,
            report.source_output_contract_item_count,
        ),
        "public_output_bundle": (
            RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
            report.source_public_output_bundle_metadata_digest,
            report.source_public_output_bundle_item_count,
        ),
    }
    for evidence_kind in RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS:
        check = checks_by_kind.get(evidence_kind)
        if check is None:
            issues.append(_issue(evidence_kind, "missing_check"))
            continue
        expected_contract, expected_digest, expected_count = expected[evidence_kind]
        if check.source_contract != expected_contract:
            issues.append(_issue(evidence_kind, "source_contract_mismatch"))
        if check.receipt_contract != expected_contract:
            issues.append(_issue(evidence_kind, "receipt_contract_mismatch"))
        if check.bundle_contract != expected_contract:
            issues.append(_issue(evidence_kind, "bundle_contract_mismatch"))
        if check.source_metadata_digest != expected_digest:
            issues.append(_issue(evidence_kind, "source_metadata_digest_mismatch"))
        if check.receipt_metadata_digest != expected_digest:
            issues.append(_issue(evidence_kind, "receipt_metadata_digest_mismatch"))
        if check.bundle_metadata_digest != expected_digest:
            issues.append(_issue(evidence_kind, "bundle_metadata_digest_mismatch"))
        if check.source_item_count != expected_count:
            issues.append(_issue(evidence_kind, "source_item_count_mismatch"))
        if check.receipt_item_count != expected_count:
            issues.append(_issue(evidence_kind, "receipt_item_count_mismatch"))
        if check.bundle_item_count != expected_count:
            issues.append(_issue(evidence_kind, "bundle_item_count_mismatch"))
        if check.row_status != RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS:
            issues.append(_issue(evidence_kind, "row_status_mismatch"))
    return tuple(issues)


def _issue(subject: str, issue_code: str) -> RuntimeExecutionOutputClosureIssue:
    return RuntimeExecutionOutputClosureIssue(subject=subject, issue_code=issue_code)


def _validate_checks(checks: tuple[RuntimeExecutionOutputClosureCheck, ...]) -> None:
    if type(checks) is not tuple:
        raise TypeError("runtime execution output closure checks must be tuple")
    if len(checks) > MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECKS:
        raise ValueError("runtime execution output closure check count exceeds limit")
    for check in checks:
        if not isinstance(check, RuntimeExecutionOutputClosureCheck):
            raise TypeError("runtime execution output closure checks mismatch")
        if check.evidence_kind not in RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS:
            raise ValueError("runtime execution output closure evidence kind unsupported")


def _validate_bool(value: bool, label: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"runtime execution output closure {label} must be bool")


def _validate_count(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"runtime execution output closure {label} must be count")
    if value > MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_BYTES:
        raise ValueError(f"runtime execution output closure {label} exceeds limit")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"runtime execution output closure {label} must be sha256")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _CLOSURE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime output closure identifier")
    if len(value.encode("utf-8")) > MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime output closure field limit")
    if value in _FORBIDDEN_CLOSURE_TEXT:
        raise ValueError(f"{label} names a forbidden output closure surface")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECKS",
    "MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_FIELD_BYTES",
    "MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_ISSUES",
    "MAX_RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_BYTES",
    "RUNTIME_EXECUTION_OUTPUT_CLOSURE_CHECK_STATUS",
    "RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT",
    "RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID",
    "RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION",
    "RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS",
    "RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS",
    "RuntimeExecutionOutputClosureCheck",
    "RuntimeExecutionOutputClosureError",
    "RuntimeExecutionOutputClosureIssue",
    "RuntimeExecutionOutputClosureReport",
    "assert_runtime_execution_output_closure",
    "build_runtime_execution_output_closure_report",
    "dump_runtime_execution_output_closure_report",
    "runtime_execution_output_closure_report_to_dict",
]
