"""Replay verifier for serialized runtime execution evidence."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from tuc.runtime.execution_evidence_bundle import (
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS,
)
from tuc.runtime.execution_output_closure import (
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS,
)
from tuc.runtime.execution_receipt import (
    RUNTIME_EXECUTION_RECEIPT_CONTRACT,
    RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.output_contract import (
    RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION,
)
from tuc.runtime.public_output_bundle import (
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_evidence_replay_verifier_report.v0"
)
RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT = (
    "runtime_evidence_replay_verifier.review.v0"
)
RUNTIME_EVIDENCE_REPLAY_VERIFIER_ARTIFACT_STATUS = "review_verification"
RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE = "metadata_digest_replay_only"
RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY = "serialized_json_reports_only"
RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY = "runtime_reexecution_not_required"
RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS = "verified"
RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS = (
    "runtime_execution_evidence_bundle",
    "runtime_execution_output_closure",
)
MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_BYTES = 256 * 1024
MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_FIELD_BYTES = 512
MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECKS = 8
MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_ISSUES = 64

_REPLAY_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_REPLAY_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"backend_artifact"',
    '"command_line"',
    '"device_id"',
    '"dynamic_library"',
    '"environment"',
    '"executable"',
    '"file_path"',
    '"generated_code"',
    '"host_path"',
    '"input_value"',
    '"jit_function"',
    '"network"',
    '"output_value"',
    '"plugin_entrypoint"',
    '"python_module"',
    '"python_source"',
    '"raw_benchmark_output"',
    '"raw_output_value"',
    '"raw_tensor_value"',
    '"raw_timing_samples"',
    '"reference_value"',
    '"source_text"',
    '"tensor_value"',
    '"tensor_values"',
    '"url"',
    "tl.dot",
    "tl.store",
)


@dataclass(frozen=True)
class RuntimeEvidenceReplayVerifierCheck:
    """One replayed digest or contract equality check."""

    check_id: str
    subject: str
    observed: str
    expected: str
    row_status: str = RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS

    def __post_init__(self) -> None:
        _validate_text(self.check_id, "runtime replay check_id")
        _validate_text(self.subject, "runtime replay subject")
        _validate_observed_value(self.observed, "runtime replay observed")
        _validate_observed_value(self.expected, "runtime replay expected")
        if self.row_status != RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS:
            raise ValueError("runtime replay verifier row status mismatch")


@dataclass(frozen=True)
class RuntimeEvidenceReplayVerifierIssue:
    """One derived runtime replay verifier issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "runtime replay issue subject")
        _validate_text(self.issue_code, "runtime replay issue_code")


@dataclass(frozen=True)
class RuntimeEvidenceReplayVerifierReport:
    """Metadata-only replay verification over serialized runtime evidence."""

    graph_name: str
    evidence_bundle_report_digest: str
    output_closure_report_digest: str
    evidence_bundle_metadata_digest: str
    output_closure_metadata_digest: str
    execution_receipt_metadata_digest: str
    output_contract_metadata_digest: str
    public_output_bundle_metadata_digest: str
    checks: tuple[RuntimeEvidenceReplayVerifierCheck, ...]
    issues: tuple[RuntimeEvidenceReplayVerifierIssue, ...]
    replay_contract: str = RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT
    artifact_status: str = RUNTIME_EVIDENCE_REPLAY_VERIFIER_ARTIFACT_STATUS
    replay_mode: str = RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE
    input_policy: str = RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY
    reexecution_policy: str = RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    required_inputs: tuple[str, ...] = RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "runtime replay graph_name")
        if self.replay_contract != RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT:
            raise ValueError("runtime replay verifier contract mismatch")
        if self.artifact_status != RUNTIME_EVIDENCE_REPLAY_VERIFIER_ARTIFACT_STATUS:
            raise ValueError("runtime replay verifier artifact status mismatch")
        if self.replay_mode != RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE:
            raise ValueError("runtime replay verifier mode mismatch")
        if self.input_policy != RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY:
            raise ValueError("runtime replay verifier input policy mismatch")
        if (
            self.reexecution_policy
            != RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY
        ):
            raise ValueError("runtime replay verifier reexecution policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("runtime replay verifier must omit raw values")
        if self.required_inputs != RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS:
            raise ValueError("runtime replay verifier required inputs changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("runtime replay verifier blocked surfaces changed")
        for digest, label in (
            (self.evidence_bundle_report_digest, "evidence_bundle_report_digest"),
            (self.output_closure_report_digest, "output_closure_report_digest"),
            (self.evidence_bundle_metadata_digest, "evidence_bundle_metadata_digest"),
            (self.output_closure_metadata_digest, "output_closure_metadata_digest"),
            (self.execution_receipt_metadata_digest, "execution_receipt_metadata_digest"),
            (self.output_contract_metadata_digest, "output_contract_metadata_digest"),
            (
                self.public_output_bundle_metadata_digest,
                "public_output_bundle_metadata_digest",
            ),
        ):
            _validate_digest(digest, label)
        _validate_checks(self.checks)
        if type(self.issues) is not tuple:
            raise TypeError("runtime replay verifier issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_ISSUES:
            raise ValueError("runtime replay verifier issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeEvidenceReplayVerifierIssue):
                raise TypeError("runtime replay verifier issues mismatch")
        if self.issues != _derive_issues(self.checks):
            raise ValueError("runtime replay verifier issues must be derived")

    @property
    def check_count(self) -> int:
        """Return the number of replay checks."""

        return len(self.checks)

    @property
    def passed(self) -> bool:
        """Return whether all replay checks passed."""

        return not self.issues

    @property
    def replay_metadata_digest(self) -> str:
        """Return a digest over replay bindings and check results."""

        payload = {
            "checks": [
                {
                    "check_id": check.check_id,
                    "expected": check.expected,
                    "observed": check.observed,
                    "row_status": check.row_status,
                    "subject": check.subject,
                }
                for check in self.checks
            ],
            "evidence_bundle_metadata_digest": self.evidence_bundle_metadata_digest,
            "execution_receipt_metadata_digest": self.execution_receipt_metadata_digest,
            "graph_name": self.graph_name,
            "output_closure_metadata_digest": self.output_closure_metadata_digest,
            "output_contract_metadata_digest": self.output_contract_metadata_digest,
            "public_output_bundle_metadata_digest": (
                self.public_output_bundle_metadata_digest
            ),
        }
        return _metadata_digest(payload)


class RuntimeEvidenceReplayVerifierError(AssertionError):
    """Raised when serialized runtime evidence replay verification fails."""


def build_runtime_evidence_replay_verifier_report(
    evidence_bundle_report_text: str,
    output_closure_report_text: str,
) -> RuntimeEvidenceReplayVerifierReport:
    """Build a metadata-only replay verifier from serialized evidence reports."""

    evidence_bundle = _load_json_report(
        evidence_bundle_report_text,
        "runtime execution evidence bundle",
    )
    output_closure = _load_json_report(
        output_closure_report_text,
        "runtime execution output closure",
    )
    _validate_evidence_bundle_shape(evidence_bundle)
    _validate_output_closure_shape(output_closure)

    graph_name = _expect_text(evidence_bundle, "graph_name")
    output_closure_graph_name = _expect_text(output_closure, "graph_name")
    if output_closure_graph_name != graph_name:
        output_closure_graph_name = "graph_name_mismatch"
    bundle_metadata_digest = _expect_digest(evidence_bundle, "bundle_metadata_digest")
    receipt = _expect_mapping(evidence_bundle, "execution_receipt")
    receipt_metadata_digest = _expect_digest(receipt, "receipt_metadata_digest")
    output_contract = _expect_mapping(evidence_bundle, "output_contract")
    public_output_bundle = _expect_mapping(evidence_bundle, "public_output_bundle")
    output_contract_digest = _expect_digest(output_contract, "contract_metadata_digest")
    public_output_bundle_digest = _expect_digest(
        public_output_bundle,
        "bundle_metadata_digest",
    )
    output_closure_metadata_digest = _expect_digest(
        output_closure,
        "closure_metadata_digest",
    )
    checks = (
        _check(
            "graph_name_match",
            "runtime_execution_output_closure",
            output_closure_graph_name,
            graph_name,
        ),
        _check(
            "evidence_bundle_metadata_digest_replayed",
            "runtime_execution_evidence_bundle",
            _replay_bundle_metadata_digest(evidence_bundle),
            bundle_metadata_digest,
        ),
        _check(
            "execution_receipt_metadata_digest_replayed",
            "runtime_execution_receipt",
            _replay_receipt_metadata_digest(receipt),
            receipt_metadata_digest,
        ),
        _check(
            "output_closure_metadata_digest_replayed",
            "runtime_execution_output_closure",
            _replay_output_closure_metadata_digest(output_closure),
            output_closure_metadata_digest,
        ),
        _check(
            "closure_binds_evidence_bundle",
            "runtime_execution_evidence_bundle",
            _expect_digest(output_closure, "source_execution_evidence_bundle_metadata_digest"),
            bundle_metadata_digest,
        ),
        _check(
            "closure_binds_execution_receipt",
            "runtime_execution_receipt",
            _expect_digest(output_closure, "source_execution_receipt_metadata_digest"),
            receipt_metadata_digest,
        ),
        _check(
            "closure_binds_output_contract",
            "runtime_output_contract",
            _expect_digest(output_closure, "source_output_contract_metadata_digest"),
            output_contract_digest,
        ),
        _check(
            "closure_binds_public_output_bundle",
            "runtime_public_output_bundle",
            _expect_digest(
                output_closure,
                "source_public_output_bundle_metadata_digest",
            ),
            public_output_bundle_digest,
        ),
    )
    return RuntimeEvidenceReplayVerifierReport(
        graph_name=graph_name,
        evidence_bundle_report_digest=_text_digest(evidence_bundle_report_text),
        output_closure_report_digest=_text_digest(output_closure_report_text),
        evidence_bundle_metadata_digest=bundle_metadata_digest,
        output_closure_metadata_digest=output_closure_metadata_digest,
        execution_receipt_metadata_digest=receipt_metadata_digest,
        output_contract_metadata_digest=output_contract_digest,
        public_output_bundle_metadata_digest=public_output_bundle_digest,
        checks=checks,
        issues=_derive_issues(checks),
    )


def assert_runtime_evidence_replay_verifier(
    report: RuntimeEvidenceReplayVerifierReport,
) -> RuntimeEvidenceReplayVerifierReport:
    """Return the verifier report or raise when replay checks fail."""

    if not isinstance(report, RuntimeEvidenceReplayVerifierReport):
        raise TypeError("runtime evidence replay verifier must be report object")
    if report.issues:
        lines = [f"runtime evidence replay verifier failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceReplayVerifierError("\n".join(lines))
    return report


def runtime_evidence_replay_verifier_report_to_dict(
    report: RuntimeEvidenceReplayVerifierReport,
) -> dict[str, object]:
    """Return deterministic JSON-compatible replay verifier evidence."""

    if not isinstance(report, RuntimeEvidenceReplayVerifierReport):
        raise TypeError("runtime evidence replay verifier must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "check_count": report.check_count,
        "checks": [
            {
                "check_id": check.check_id,
                "expected": check.expected,
                "observed": check.observed,
                "row_status": check.row_status,
                "subject": check.subject,
            }
            for check in report.checks
        ],
        "evidence_bundle_metadata_digest": report.evidence_bundle_metadata_digest,
        "evidence_bundle_report_digest": report.evidence_bundle_report_digest,
        "execution_receipt_metadata_digest": report.execution_receipt_metadata_digest,
        "graph_name": report.graph_name,
        "input_policy": report.input_policy,
        "issues": [
            {"issue_code": issue.issue_code, "subject": issue.subject}
            for issue in report.issues
        ],
        "output_closure_metadata_digest": report.output_closure_metadata_digest,
        "output_closure_report_digest": report.output_closure_report_digest,
        "output_contract_metadata_digest": report.output_contract_metadata_digest,
        "passed": report.passed,
        "public_output_bundle_metadata_digest": (
            report.public_output_bundle_metadata_digest
        ),
        "raw_value_policy": report.raw_value_policy,
        "reexecution_policy": report.reexecution_policy,
        "replay_contract": report.replay_contract,
        "replay_metadata_digest": report.replay_metadata_digest,
        "replay_mode": report.replay_mode,
        "required_inputs": list(report.required_inputs),
        "schema_version": RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
    }


def dump_runtime_evidence_replay_verifier_report(
    report: RuntimeEvidenceReplayVerifierReport,
) -> str:
    """Render stable serialized runtime evidence replay verification."""

    text = json.dumps(
        runtime_evidence_replay_verifier_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_BYTES:
        raise ValueError("runtime evidence replay verifier report exceeds byte limit")
    return text + "\n"


def _load_json_report(text: str, label: str) -> dict[str, object]:
    if not isinstance(text, str):
        raise TypeError(f"{label} text must be string")
    if len(text.encode("utf-8")) > MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_BYTES:
        raise ValueError(f"{label} text exceeds replay verifier byte limit")
    _assert_source_free_text(text, label)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} text must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} JSON must be object")
    return parsed


def _validate_evidence_bundle_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(report, "bundle_contract", RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT)
    _expect_value(report, "artifact_status", "review_evidence")
    _expect_value(report, "linkage_policy", "embedded_metadata_reports")
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(report, "report_sections", list(RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS))
    _expect_value(
        report,
        "blocked_execution_surfaces",
        list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
    )
    receipt = _expect_mapping(report, "execution_receipt")
    _expect_value(
        receipt,
        "schema_version",
        RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION,
    )
    _expect_value(receipt, "receipt_contract", RUNTIME_EXECUTION_RECEIPT_CONTRACT)
    _expect_value(receipt, "passed", True)
    _expect_value(receipt, "issues", [])
    _expect_value(receipt, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)


def _validate_output_closure_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(report, "closure_contract", RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT)
    _expect_value(report, "closure_policy_id", RUNTIME_EXECUTION_OUTPUT_CLOSURE_POLICY_ID)
    _expect_value(report, "closure_status", RUNTIME_EXECUTION_OUTPUT_CLOSURE_STATUS)
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(
        report,
        "source_execution_evidence_bundle_schema_version",
        RUNTIME_EXECUTION_EVIDENCE_BUNDLE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(
        report,
        "source_execution_receipt_schema_version",
        RUNTIME_EXECUTION_RECEIPT_REPORT_SCHEMA_VERSION,
    )
    _expect_value(
        report,
        "source_output_contract_schema_version",
        RUNTIME_OUTPUT_CONTRACT_REPORT_SCHEMA_VERSION,
    )
    _expect_value(
        report,
        "source_public_output_bundle_schema_version",
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(
        report,
        "blocked_execution_surfaces",
        list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
    )
    checks = _expect_list(report, "checks")
    if len(checks) != len(RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS):
        raise ValueError("runtime output closure check count mismatch")
    if report.get("check_count") != len(checks):
        raise ValueError("runtime output closure check_count mismatch")


def _replay_bundle_metadata_digest(report: dict[str, object]) -> str:
    payload = {
        "execution_receipt": _expect_digest(
            _expect_mapping(report, "execution_receipt"),
            "receipt_metadata_digest",
        ),
        "graph_name": _expect_text(report, "graph_name"),
        "input_manifest": _expect_digest(
            _expect_mapping(report, "input_manifest"),
            "input_metadata_digest",
        ),
        "output_contract": _expect_digest(
            _expect_mapping(report, "output_contract"),
            "contract_metadata_digest",
        ),
        "output_manifest": _expect_digest(
            _expect_mapping(report, "output_manifest"),
            "output_metadata_digest",
        ),
        "public_output_bundle": _expect_digest(
            _expect_mapping(report, "public_output_bundle"),
            "bundle_metadata_digest",
        ),
        "reference_correctness": _expect_digest(
            _expect_mapping(report, "reference_correctness"),
            "comparison_metadata_digest",
        ),
        "tensor_store_evidence": _expect_digest(
            _expect_mapping(report, "tensor_store_evidence"),
            "record_metadata_digest",
        ),
    }
    return _metadata_digest(payload)


def _replay_receipt_metadata_digest(report: dict[str, object]) -> str:
    operations = _expect_list(report, "operations")
    trace_payload = []
    for operation in operations:
        operation_mapping = _expect_mapping_value(operation, "receipt operation")
        trace_payload.append(
            {
                "executor_backend": operation_mapping["executor_backend"],
                "input_tensors": operation_mapping["input_tensors"],
                "operation_kind": operation_mapping["operation_kind"],
                "operation_name": operation_mapping["operation_name"],
                "output_shapes": operation_mapping["output_shapes"],
                "output_tensors": operation_mapping["output_tensors"],
                "planned_backend": operation_mapping["planned_backend"],
                "status": operation_mapping["status"],
            }
        )
    execution_trace_digest = _metadata_digest(trace_payload)
    if report.get("execution_trace_metadata_digest") != execution_trace_digest:
        return "execution_trace_metadata_digest_mismatch"
    links = _expect_list(report, "evidence_links")
    link_payload = []
    for link in links:
        link_mapping = _expect_mapping_value(link, "receipt evidence link")
        link_payload.append(
            {
                "evidence_contract": link_mapping["evidence_contract"],
                "evidence_kind": link_mapping["evidence_kind"],
                "graph_name": link_mapping["graph_name"],
                "item_count": link_mapping["item_count"],
                "metadata_digest": link_mapping["metadata_digest"],
                "passed": link_mapping["passed"],
                "raw_value_policy": link_mapping["raw_value_policy"],
            }
        )
    return _metadata_digest(
        {
            "evidence_links": link_payload,
            "execution_trace_metadata_digest": execution_trace_digest,
            "graph_name": _expect_text(report, "graph_name"),
        }
    )


def _replay_output_closure_metadata_digest(report: dict[str, object]) -> str:
    checks = _expect_list(report, "checks")
    check_payload = []
    for check in checks:
        check_mapping = _expect_mapping_value(check, "output closure check")
        check_payload.append(
            {
                "bundle_contract": check_mapping["bundle_contract"],
                "bundle_item_count": check_mapping["bundle_item_count"],
                "bundle_metadata_digest": check_mapping["bundle_metadata_digest"],
                "evidence_kind": check_mapping["evidence_kind"],
                "receipt_contract": check_mapping["receipt_contract"],
                "receipt_item_count": check_mapping["receipt_item_count"],
                "receipt_metadata_digest": check_mapping["receipt_metadata_digest"],
                "row_status": check_mapping["row_status"],
                "source_contract": check_mapping["source_contract"],
                "source_item_count": check_mapping["source_item_count"],
                "source_metadata_digest": check_mapping["source_metadata_digest"],
            }
        )
    return _metadata_digest(
        {
            "checks": check_payload,
            "graph_name": _expect_text(report, "graph_name"),
            "source_execution_evidence_bundle_metadata_digest": _expect_digest(
                report,
                "source_execution_evidence_bundle_metadata_digest",
            ),
            "source_execution_receipt_metadata_digest": _expect_digest(
                report,
                "source_execution_receipt_metadata_digest",
            ),
            "source_output_contract_metadata_digest": _expect_digest(
                report,
                "source_output_contract_metadata_digest",
            ),
            "source_public_output_bundle_metadata_digest": _expect_digest(
                report,
                "source_public_output_bundle_metadata_digest",
            ),
        }
    )


def _derive_issues(
    checks: tuple[RuntimeEvidenceReplayVerifierCheck, ...],
) -> tuple[RuntimeEvidenceReplayVerifierIssue, ...]:
    issues: list[RuntimeEvidenceReplayVerifierIssue] = []
    seen: set[str] = set()
    for check in checks:
        if check.check_id in seen:
            issues.append(
                RuntimeEvidenceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code="duplicate_check_id",
                )
            )
        seen.add(check.check_id)
        if check.observed != check.expected:
            issues.append(
                RuntimeEvidenceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code=f"{check.check_id}_mismatch",
                )
            )
        if check.row_status != RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS:
            issues.append(
                RuntimeEvidenceReplayVerifierIssue(
                    subject=check.subject,
                    issue_code=f"{check.check_id}_row_status_mismatch",
                )
            )
    return tuple(issues)


def _check(
    check_id: str,
    subject: str,
    observed: str,
    expected: str,
) -> RuntimeEvidenceReplayVerifierCheck:
    return RuntimeEvidenceReplayVerifierCheck(
        check_id=check_id,
        subject=subject,
        observed=observed,
        expected=expected,
    )


def _expect_mapping(report: dict[str, object], key: str) -> dict[str, object]:
    value = report.get(key)
    return _expect_mapping_value(value, key)


def _expect_mapping_value(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be object")
    return value


def _expect_list(report: dict[str, object], key: str) -> list[object]:
    value = report.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be list")
    return value


def _expect_text(report: dict[str, object], key: str) -> str:
    value = report.get(key)
    _validate_text(value, key)
    return cast(str, value)


def _expect_digest(report: dict[str, object], key: str) -> str:
    value = report.get(key)
    _validate_digest(value, key)
    return cast(str, value)


def _expect_value(report: dict[str, object], key: str, expected: object) -> None:
    if report.get(key) != expected:
        raise ValueError(f"{key} mismatch")


def _validate_checks(
    checks: tuple[RuntimeEvidenceReplayVerifierCheck, ...],
) -> None:
    if type(checks) is not tuple:
        raise TypeError("runtime replay verifier checks must be tuple")
    if len(checks) > MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECKS:
        raise ValueError("runtime replay verifier check count exceeds limit")
    for check in checks:
        if not isinstance(check, RuntimeEvidenceReplayVerifierCheck):
            raise TypeError("runtime replay verifier checks mismatch")


def _validate_text(value: object, label: str) -> None:
    if not isinstance(value, str) or not _REPLAY_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be safe runtime replay verifier text")
    if len(value.encode("utf-8")) > MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime replay verifier field limit")


def _validate_observed_value(value: object, label: str) -> None:
    if isinstance(value, str) and _DIGEST_RE.fullmatch(value):
        return
    _validate_text(value, label)


def _validate_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _assert_source_free_text(text: str, label: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_REPLAY_FRAGMENTS:
        if fragment.lower() in lowered:
            raise ValueError(f"{label} contains forbidden replay verifier fragment")


def _metadata_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return f"sha256:{sha256(encoded).hexdigest()}"


def _text_digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


__all__ = [
    "MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECKS",
    "MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_FIELD_BYTES",
    "MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_BYTES",
    "MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_ISSUES",
    "MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_BYTES",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_ARTIFACT_STATUS",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECK_STATUS",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION",
    "RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS",
    "RuntimeEvidenceReplayVerifierCheck",
    "RuntimeEvidenceReplayVerifierError",
    "RuntimeEvidenceReplayVerifierIssue",
    "RuntimeEvidenceReplayVerifierReport",
    "assert_runtime_evidence_replay_verifier",
    "build_runtime_evidence_replay_verifier_report",
    "dump_runtime_evidence_replay_verifier_report",
    "runtime_evidence_replay_verifier_report_to_dict",
]
