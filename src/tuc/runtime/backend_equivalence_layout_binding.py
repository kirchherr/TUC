"""Bind backend-equivalence evidence to verified layout-conversion traces."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from typing import cast

from tuc.runtime.backend_equivalence import (
    RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS,
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
)
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime.layout_conversion_trace_replay_verifier import (
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_POLICY,
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY,
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPLAY_MODE,
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
)
from tuc.runtime.tensor_store_evidence import RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS

RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_backend_equivalence_layout_binding_report.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT = (
    "runtime_backend_equivalence_layout_binding.data_only.v0"
)
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ARTIFACT_STATUS = "review_binding"
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE = "metadata_digest_binding_only"
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY = "serialized_json_reports_only"
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY = "runtime_reexecution_not_required"
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECK_STATUS = "verified"
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REQUIRED_INPUTS = (
    "runtime_backend_equivalence",
    "runtime_layout_conversion_trace_replay_verifier",
)
MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_BYTES = 256 * 1024
MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_FIELD_BYTES = 512
MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECKS = 8
MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ISSUES = 64

_BINDING_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_BINDING_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"allocation_handle"',
    '"backend_artifact"',
    '"command_line"',
    '"device_id"',
    '"device_pointer"',
    '"dynamic_library"',
    '"environment"',
    '"executable"',
    '"file_path"',
    '"generated_code"',
    '"host_path"',
    '"input_value"',
    '"jit_function"',
    '"memory_address"',
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
    '"runtime_handle"',
    '"source_text"',
    '"tensor_value"',
    '"tensor_values"',
    '"url"',
    "tl.store",
)


@dataclass(frozen=True)
class RuntimeBackendEquivalenceLayoutBindingCheck:
    """One metadata-only backend-equivalence/layout binding check."""

    check_id: str
    subject: str
    observed: str
    expected: str
    row_status: str = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECK_STATUS

    def __post_init__(self) -> None:
        _validate_text(self.check_id, "backend layout binding check_id")
        _validate_text(self.subject, "backend layout binding subject")
        _validate_observed_value(self.observed, "backend layout binding observed")
        _validate_observed_value(self.expected, "backend layout binding expected")
        if self.row_status != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECK_STATUS:
            raise ValueError("backend layout binding row status mismatch")


@dataclass(frozen=True)
class RuntimeBackendEquivalenceLayoutBindingIssue:
    """One derived backend-equivalence/layout binding issue."""

    subject: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_text(self.subject, "backend layout binding issue subject")
        _validate_text(self.issue_code, "backend layout binding issue_code")


@dataclass(frozen=True)
class RuntimeBackendEquivalenceLayoutBindingReport:
    """Data-only report binding backend equivalence to layout trace replay."""

    graph_name: str
    baseline_run_id: str
    candidate_run_id: str
    backend_equivalence_report_digest: str
    layout_trace_replay_report_digest: str
    backend_equivalence_comparison_metadata_digest: str
    layout_trace_replay_metadata_digest: str
    baseline_backend_sequence_digest: str
    candidate_backend_sequence_digest: str
    candidate_backend_count: int
    layout_replay_check_count: int
    checks: tuple[RuntimeBackendEquivalenceLayoutBindingCheck, ...]
    issues: tuple[RuntimeBackendEquivalenceLayoutBindingIssue, ...]
    binding_contract: str = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT
    artifact_status: str = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ARTIFACT_STATUS
    binding_mode: str = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE
    input_policy: str = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY
    reexecution_policy: str = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY
    raw_value_policy: str = RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    executor_contract: str = RUNTIME_EXECUTOR_CONTRACT
    trusted_executor_registry: str = TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    required_inputs: tuple[str, ...] = RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REQUIRED_INPUTS
    blocked_execution_surfaces: tuple[str, ...] = RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

    def __post_init__(self) -> None:
        _validate_text(self.graph_name, "backend layout binding graph_name")
        _validate_text(self.baseline_run_id, "backend layout binding baseline_run_id")
        _validate_text(self.candidate_run_id, "backend layout binding candidate_run_id")
        if self.baseline_run_id == self.candidate_run_id:
            raise ValueError("backend layout binding run IDs must be distinct")
        if self.binding_contract != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT:
            raise ValueError("backend layout binding contract mismatch")
        if self.artifact_status != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ARTIFACT_STATUS:
            raise ValueError("backend layout binding artifact status mismatch")
        if self.binding_mode != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE:
            raise ValueError("backend layout binding mode mismatch")
        if self.input_policy != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY:
            raise ValueError("backend layout binding input policy mismatch")
        if self.reexecution_policy != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY:
            raise ValueError("backend layout binding reexecution policy mismatch")
        if self.raw_value_policy != RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS:
            raise ValueError("backend layout binding must omit raw values")
        if self.executor_contract != RUNTIME_EXECUTOR_CONTRACT:
            raise ValueError("backend layout binding executor contract mismatch")
        if self.trusted_executor_registry != TRUSTED_RUNTIME_EXECUTOR_REGISTRY:
            raise ValueError("backend layout binding trusted registry mismatch")
        if self.required_inputs != RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REQUIRED_INPUTS:
            raise ValueError("backend layout binding required inputs changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend layout binding blocked surfaces changed")
        for digest, label in (
            (self.backend_equivalence_report_digest, "backend_equivalence_report_digest"),
            (self.layout_trace_replay_report_digest, "layout_trace_replay_report_digest"),
            (
                self.backend_equivalence_comparison_metadata_digest,
                "backend_equivalence_comparison_metadata_digest",
            ),
            (
                self.layout_trace_replay_metadata_digest,
                "layout_trace_replay_metadata_digest",
            ),
            (self.baseline_backend_sequence_digest, "baseline_backend_sequence_digest"),
            (self.candidate_backend_sequence_digest, "candidate_backend_sequence_digest"),
        ):
            _validate_digest(digest, label)
        _validate_positive_count(self.candidate_backend_count, "candidate_backend_count")
        _validate_positive_count(self.layout_replay_check_count, "layout_replay_check_count")
        _validate_checks(self.checks)
        if type(self.issues) is not tuple:
            raise TypeError("backend layout binding issues must be tuple")
        if len(self.issues) > MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ISSUES:
            raise ValueError("backend layout binding issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, RuntimeBackendEquivalenceLayoutBindingIssue):
                raise TypeError("backend layout binding issues mismatch")
        if self.issues != _derive_issues(self.checks):
            raise ValueError("backend layout binding issues must be derived")

    @property
    def check_count(self) -> int:
        """Return the number of binding checks."""

        return len(self.checks)

    @property
    def passed(self) -> bool:
        """Return whether all binding checks passed."""

        return not self.issues

    @property
    def binding_metadata_digest(self) -> str:
        """Return a digest over report bindings and check statuses."""

        return _metadata_digest(
            {
                "backend_equivalence_comparison_metadata_digest": (
                    self.backend_equivalence_comparison_metadata_digest
                ),
                "backend_equivalence_report_digest": (self.backend_equivalence_report_digest),
                "candidate_backend_count": self.candidate_backend_count,
                "candidate_backend_sequence_digest": (self.candidate_backend_sequence_digest),
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
                "graph_name": self.graph_name,
                "layout_replay_check_count": self.layout_replay_check_count,
                "layout_trace_replay_metadata_digest": (self.layout_trace_replay_metadata_digest),
                "layout_trace_replay_report_digest": (self.layout_trace_replay_report_digest),
            }
        )


class RuntimeBackendEquivalenceLayoutBindingError(AssertionError):
    """Raised when backend-equivalence/layout binding checks fail."""


def build_runtime_backend_equivalence_layout_binding_report(
    runtime_backend_equivalence_report_text: str,
    runtime_layout_conversion_trace_replay_verifier_report_text: str,
) -> RuntimeBackendEquivalenceLayoutBindingReport:
    """Build a metadata-only binding over two serialized evidence reports."""

    equivalence = _load_json_report(
        runtime_backend_equivalence_report_text,
        "runtime backend equivalence",
    )
    replay = _load_json_report(
        runtime_layout_conversion_trace_replay_verifier_report_text,
        "runtime layout conversion trace replay verifier",
    )
    _validate_backend_equivalence_shape(equivalence)
    _validate_layout_trace_replay_shape(replay)

    graph_name = _expect_text(equivalence, "graph_name")
    replay_graph_name = _expect_text(replay, "graph_name")
    baseline_run_id = _expect_text(equivalence, "baseline_run_id")
    candidate_run_id = _expect_text(equivalence, "candidate_run_id")
    baseline_sequence = _run_backend_sequence(equivalence, baseline_run_id)
    candidate_sequence = _run_backend_sequence(equivalence, candidate_run_id)
    candidate_backend_count = len(set(candidate_sequence))
    replay_check_count = _expect_int(replay, "check_count")
    backend_raw_value_policy = _expect_text(equivalence, "raw_value_policy")
    replay_raw_value_policy = _expect_text(replay, "raw_value_policy")

    checks = (
        _check(
            "backend_equivalence_contract_bound",
            "runtime_backend_equivalence",
            _expect_text(equivalence, "equivalence_contract"),
            RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        ),
        _check(
            "layout_trace_replay_contract_bound",
            "runtime_layout_conversion_trace_replay_verifier",
            _expect_text(replay, "replay_contract"),
            RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT,
        ),
        _check(
            "graph_name_bound",
            "runtime_backend_equivalence_layout_binding",
            graph_name,
            replay_graph_name,
        ),
        _check(
            "backend_equivalence_passed_bound",
            "runtime_backend_equivalence",
            _bool_status(_expect_bool(equivalence, "passed")),
            "passed",
        ),
        _check(
            "layout_trace_replay_passed_bound",
            "runtime_layout_conversion_trace_replay_verifier",
            _bool_status(_expect_bool(replay, "passed")),
            "passed",
        ),
        _check(
            "raw_value_policy_bound",
            "runtime_backend_equivalence_layout_binding",
            f"{backend_raw_value_policy}:{replay_raw_value_policy}",
            f"{RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS}:{RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS}",
        ),
        _check(
            "candidate_backend_diversity_bound",
            "runtime_backend_equivalence",
            "mixed_backend_candidate"
            if candidate_backend_count >= 2
            else "single_backend_candidate",
            "mixed_backend_candidate",
        ),
        _check(
            "layout_replay_checks_bound",
            "runtime_layout_conversion_trace_replay_verifier",
            str(replay_check_count),
            "6",
        ),
    )
    return RuntimeBackendEquivalenceLayoutBindingReport(
        graph_name=graph_name,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        backend_equivalence_report_digest=_text_digest(runtime_backend_equivalence_report_text),
        layout_trace_replay_report_digest=_text_digest(
            runtime_layout_conversion_trace_replay_verifier_report_text
        ),
        backend_equivalence_comparison_metadata_digest=_expect_digest(
            equivalence,
            "comparison_metadata_digest",
        ),
        layout_trace_replay_metadata_digest=_expect_digest(
            replay,
            "replay_metadata_digest",
        ),
        baseline_backend_sequence_digest=_sequence_digest(baseline_sequence),
        candidate_backend_sequence_digest=_sequence_digest(candidate_sequence),
        candidate_backend_count=candidate_backend_count,
        layout_replay_check_count=replay_check_count,
        checks=checks,
        issues=_derive_issues(checks),
    )


def assert_runtime_backend_equivalence_layout_binding(
    report: RuntimeBackendEquivalenceLayoutBindingReport,
) -> RuntimeBackendEquivalenceLayoutBindingReport:
    """Return the report or raise when backend/layout binding checks fail."""

    if not isinstance(report, RuntimeBackendEquivalenceLayoutBindingReport):
        raise TypeError("runtime backend equivalence layout binding must be report")
    if report.issues:
        lines = [f"runtime backend equivalence layout binding failed for {report.graph_name!r}:"]
        lines.extend(f"- {issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeBackendEquivalenceLayoutBindingError("\n".join(lines))
    return report


def runtime_backend_equivalence_layout_binding_report_to_dict(
    report: RuntimeBackendEquivalenceLayoutBindingReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible backend/layout binding report."""

    if not isinstance(report, RuntimeBackendEquivalenceLayoutBindingReport):
        raise TypeError("runtime backend equivalence layout binding must be report")
    return {
        "artifact_status": report.artifact_status,
        "backend_equivalence_comparison_metadata_digest": (
            report.backend_equivalence_comparison_metadata_digest
        ),
        "backend_equivalence_report_digest": report.backend_equivalence_report_digest,
        "baseline_backend_sequence_digest": report.baseline_backend_sequence_digest,
        "baseline_run_id": report.baseline_run_id,
        "binding_contract": report.binding_contract,
        "binding_metadata_digest": report.binding_metadata_digest,
        "binding_mode": report.binding_mode,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "candidate_backend_count": report.candidate_backend_count,
        "candidate_backend_sequence_digest": report.candidate_backend_sequence_digest,
        "candidate_run_id": report.candidate_run_id,
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
        "executor_contract": report.executor_contract,
        "graph_name": report.graph_name,
        "input_policy": report.input_policy,
        "issues": [
            {
                "issue_code": issue.issue_code,
                "subject": issue.subject,
            }
            for issue in report.issues
        ],
        "layout_replay_check_count": report.layout_replay_check_count,
        "layout_trace_replay_metadata_digest": report.layout_trace_replay_metadata_digest,
        "layout_trace_replay_report_digest": report.layout_trace_replay_report_digest,
        "passed": report.passed,
        "raw_value_policy": report.raw_value_policy,
        "reexecution_policy": report.reexecution_policy,
        "required_inputs": list(report.required_inputs),
        "schema_version": (RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_SCHEMA_VERSION),
        "trusted_executor_registry": report.trusted_executor_registry,
    }


def dump_runtime_backend_equivalence_layout_binding_report(
    report: RuntimeBackendEquivalenceLayoutBindingReport,
) -> str:
    """Render stable serialized backend-equivalence/layout binding evidence."""

    text = json.dumps(
        runtime_backend_equivalence_layout_binding_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_BYTES:
        raise ValueError("runtime backend equivalence layout binding report exceeds byte limit")
    return text + "\n"


def _load_json_report(text: str, label: str) -> dict[str, object]:
    if not isinstance(text, str):
        raise TypeError(f"{label} text must be string")
    if len(text.encode("utf-8")) > MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_BYTES:
        raise ValueError(f"{label} text exceeds layout binding byte limit")
    _assert_source_free_text(text, label)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} text must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} JSON must be object")
    return parsed


def _validate_backend_equivalence_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
    )
    _expect_value(report, "artifact_status", RUNTIME_BACKEND_EQUIVALENCE_ARTIFACT_STATUS)
    _expect_value(report, "equivalence_contract", RUNTIME_BACKEND_EQUIVALENCE_CONTRACT)
    _expect_value(report, "executor_contract", RUNTIME_EXECUTOR_CONTRACT)
    _expect_value(report, "trusted_executor_registry", TRUSTED_RUNTIME_EXECUTOR_REGISTRY)
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(
        report, "blocked_execution_surfaces", list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    )
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    _expect_value(report, "run_count", 2)
    runs = _expect_list(report, "runs")
    if len(runs) != 2:
        raise ValueError("runtime backend equivalence run_count mismatch")
    comparisons = _expect_list(report, "comparisons")
    if report.get("comparison_count") != len(comparisons):
        raise ValueError("runtime backend equivalence comparison_count mismatch")


def _validate_layout_trace_replay_shape(report: dict[str, object]) -> None:
    _expect_value(
        report,
        "schema_version",
        RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
    )
    _expect_value(
        report, "artifact_status", RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_ARTIFACT_STATUS
    )
    _expect_value(
        report, "replay_contract", RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_CONTRACT
    )
    _expect_value(
        report, "replay_mode", RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REPLAY_MODE
    )
    _expect_value(
        report, "input_policy", RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_INPUT_POLICY
    )
    _expect_value(
        report,
        "reexecution_policy",
        RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY,
    )
    _expect_value(report, "raw_value_policy", RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS)
    _expect_value(
        report, "blocked_execution_surfaces", list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    )
    _expect_value(report, "passed", True)
    _expect_value(report, "issues", [])
    checks = _expect_list(report, "checks")
    if report.get("check_count") != len(checks):
        raise ValueError("layout trace replay verifier check_count mismatch")
    if _expect_int(report, "check_count") != 6:
        raise ValueError("layout trace replay verifier required checks mismatch")


def _run_backend_sequence(
    report: dict[str, object],
    run_id: str,
) -> tuple[str, ...]:
    for item in _expect_list(report, "runs"):
        run = _expect_mapping_value(item, "runtime backend equivalence run")
        if _expect_mapping_text(run, "run_id") != run_id:
            continue
        sequence = _expect_mapping_list(run, "planned_backend_sequence")
        return tuple(_expect_sequence_text(value, "planned_backend_sequence") for value in sequence)
    raise ValueError(f"runtime backend equivalence run missing: {run_id}")


def _derive_issues(
    checks: tuple[RuntimeBackendEquivalenceLayoutBindingCheck, ...],
) -> tuple[RuntimeBackendEquivalenceLayoutBindingIssue, ...]:
    issues: list[RuntimeBackendEquivalenceLayoutBindingIssue] = []
    seen: set[str] = set()
    for check in checks:
        if check.check_id in seen:
            issues.append(
                RuntimeBackendEquivalenceLayoutBindingIssue(
                    subject=check.subject,
                    issue_code="duplicate_check_id",
                )
            )
        seen.add(check.check_id)
        if check.observed != check.expected:
            issues.append(
                RuntimeBackendEquivalenceLayoutBindingIssue(
                    subject=check.subject,
                    issue_code=f"{check.check_id}_mismatch",
                )
            )
    return tuple(issues)


def _validate_checks(
    checks: tuple[RuntimeBackendEquivalenceLayoutBindingCheck, ...],
) -> None:
    if type(checks) is not tuple:
        raise TypeError("backend layout binding checks must be tuple")
    if len(checks) != MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECKS:
        raise ValueError("backend layout binding required check count mismatch")
    for check in checks:
        if not isinstance(check, RuntimeBackendEquivalenceLayoutBindingCheck):
            raise TypeError("backend layout binding checks mismatch")


def _check(
    check_id: str,
    subject: str,
    observed: str,
    expected: str,
) -> RuntimeBackendEquivalenceLayoutBindingCheck:
    return RuntimeBackendEquivalenceLayoutBindingCheck(
        check_id=check_id,
        subject=subject,
        observed=observed,
        expected=expected,
    )


def _expect_value(
    report: dict[str, object],
    field_name: str,
    expected: object,
) -> None:
    if report.get(field_name) != expected:
        raise ValueError(f"{field_name} mismatch")


def _expect_text(report: dict[str, object], field_name: str) -> str:
    value = report.get(field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be string")
    _validate_text(value, field_name)
    return value


def _expect_bool(report: dict[str, object], field_name: str) -> bool:
    value = report.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be boolean")
    return value


def _expect_int(report: dict[str, object], field_name: str) -> int:
    value = report.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"{field_name} must be integer")
    _validate_positive_count(value, field_name)
    return value


def _expect_digest(report: dict[str, object], field_name: str) -> str:
    value = _expect_text(report, field_name)
    _validate_digest(value, field_name)
    return value


def _expect_list(report: dict[str, object], field_name: str) -> list[object]:
    value = report.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be list")
    return value


def _expect_mapping_value(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be object")
    return cast(dict[str, object], value)


def _expect_mapping_text(mapping: dict[str, object], field_name: str) -> str:
    value = mapping.get(field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be string")
    _validate_text(value, field_name)
    return value


def _expect_sequence_text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} item must be string")
    _validate_text(value, label)
    return value


def _expect_mapping_list(mapping: dict[str, object], field_name: str) -> list[object]:
    value = mapping.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be list")
    return value


def _bool_status(value: bool) -> str:
    return "passed" if value else "failed"


def _validate_positive_count(value: int, label: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{label} must be int")
    if value < 1:
        raise ValueError(f"{label} must be positive")


def _validate_observed_value(value: str, label: str) -> None:
    if _DIGEST_RE.fullmatch(value):
        return
    _validate_text(value, label)


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be string")
    if (
        not value
        or len(value.encode("utf-8")) > MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_FIELD_BYTES
    ):
        raise ValueError(f"{label} length unsupported")
    if not _BINDING_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} has unsupported characters")
    if value in {fragment.strip('"') for fragment in _FORBIDDEN_BINDING_FRAGMENTS}:
        raise ValueError(f"{label} contains forbidden execution or value surface")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"{label} must be sha256 digest")


def _assert_source_free_text(text: str, label: str) -> None:
    for fragment in _FORBIDDEN_BINDING_FRAGMENTS:
        if fragment in text:
            raise ValueError(f"{label} contains forbidden backend layout binding text")


def _text_digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _metadata_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _sequence_digest(sequence: tuple[str, ...]) -> str:
    return _metadata_digest(list(sequence))


__all__ = [
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECKS",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_FIELD_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_BYTES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ISSUES",
    "MAX_RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_BYTES",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_ARTIFACT_STATUS",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECK_STATUS",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_SCHEMA_VERSION",
    "RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REQUIRED_INPUTS",
    "RuntimeBackendEquivalenceLayoutBindingCheck",
    "RuntimeBackendEquivalenceLayoutBindingError",
    "RuntimeBackendEquivalenceLayoutBindingIssue",
    "RuntimeBackendEquivalenceLayoutBindingReport",
    "assert_runtime_backend_equivalence_layout_binding",
    "build_runtime_backend_equivalence_layout_binding_report",
    "dump_runtime_backend_equivalence_layout_binding_report",
    "runtime_backend_equivalence_layout_binding_report_to_dict",
]
