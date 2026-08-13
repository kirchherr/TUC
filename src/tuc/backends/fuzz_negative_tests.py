"""Data-only fuzz and negative-test evidence for backend plugin proposals."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.artifact_provenance import BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
from tuc.backends.resource_budget import BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
from tuc.backends.sandbox_model import BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_REPORT_SCHEMA_VERSION = (
    "tuc.backend_plugin_fuzz_negative_tests_report.v0"
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT = (
    "backend_plugin_fuzz_negative_tests.data_only.v0"
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY = (
    "fuzz_negative_tests.required_cases.no_execution.v0"
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS = "accepted_data_only_test_evidence"
BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION = "not_granted"
BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY = "deterministic_seed_ids_only"
BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS = frozenset(
    {
        "duplicate_record",
        "forbidden_execution_surface",
        "invalid_digest",
        "oversized_resource_budget",
        "schema_fail_closed",
    }
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_STATUSES = frozenset(
    {"covered_by_repository_tests"}
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_EXPECTED_RESULTS = frozenset(
    {"rejects_before_execution"}
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS = (
    "sandbox_model",
    "artifact_provenance",
    "resource_budget",
    "negative_case_inventory",
    "fuzz_seed_policy",
)
BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_ISSUE_CODES = frozenset(
    {
        "artifact_provenance_binding_mismatch",
        "blocked_surface_invalid",
        "case_kind_invalid",
        "case_status_invalid",
        "duplicate_case_id",
        "execution_permission_granted",
        "expected_result_invalid",
        "missing_required_binding",
        "missing_required_case_kind",
        "resource_budget_binding_mismatch",
        "sandbox_binding_mismatch",
        "seed_policy_mismatch",
    }
)
MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASES = 32
MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_ISSUES = 64
MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REPORT_BYTES = 64 * 1024
MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_FIELD_BYTES = 512

_TEST_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_FORBIDDEN_TEST_TEXT = frozenset(
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
        "raw_timing_samples",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class BackendPluginFuzzNegativeTestCase:
    """One bounded negative or fuzz-seed evidence case."""

    case_id: str
    case_kind: str
    evidence_id: str
    seed_id: str
    blocked_surface: str
    expected_result: str
    case_status: str

    def __post_init__(self) -> None:
        _validate_test_text(self.case_id, "case_id")
        _validate_test_text(self.case_kind, "case_kind")
        _validate_test_text(self.evidence_id, "evidence_id")
        _validate_test_text(self.seed_id, "seed_id")
        _validate_test_text(self.blocked_surface, "blocked_surface")
        _validate_test_text(self.expected_result, "expected_result")
        _validate_test_text(self.case_status, "case_status")
        if self.case_kind not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS:
            raise ValueError("backend plugin fuzz negative case kind unsupported")
        if self.blocked_surface not in RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin fuzz negative blocked surface unsupported")
        if (
            self.expected_result
            not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_EXPECTED_RESULTS
        ):
            raise ValueError("backend plugin fuzz negative expected result unsupported")
        if self.case_status not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_STATUSES:
            raise ValueError("backend plugin fuzz negative case status unsupported")


@dataclass(frozen=True)
class BackendPluginFuzzNegativeTestIssue:
    """One derived fuzz or negative-test evidence issue."""

    case_id: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_test_text(self.case_id, "negative test issue case_id")
        _validate_test_text(self.issue_code, "negative test issue_code")
        if self.issue_code not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_ISSUE_CODES:
            raise ValueError("backend plugin fuzz negative issue unsupported")


@dataclass(frozen=True)
class BackendPluginFuzzNegativeTestsReport:
    """Current data-only fuzz and negative-test evidence."""

    cases: tuple[BackendPluginFuzzNegativeTestCase, ...]
    issues: tuple[BackendPluginFuzzNegativeTestIssue, ...]
    negative_tests_contract: str = BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
    negative_tests_policy: str = BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY
    negative_tests_status: str = BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS
    execution_permission: str = BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION
    seed_policy: str = BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY
    sandbox_model_contract: str = BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    artifact_provenance_contract: str = BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    resource_budget_contract: str = BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    required_bindings: tuple[str, ...] = (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.negative_tests_contract != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT:
            raise ValueError("backend plugin fuzz negative contract mismatch")
        if self.negative_tests_policy != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY:
            raise ValueError("backend plugin fuzz negative policy mismatch")
        if self.negative_tests_status != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS:
            raise ValueError("backend plugin fuzz negative status mismatch")
        if (
            self.execution_permission
            != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION
        ):
            raise ValueError("backend plugin fuzz negative permission mismatch")
        if self.seed_policy != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY:
            raise ValueError("backend plugin fuzz negative seed policy mismatch")
        if self.sandbox_model_contract != BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT:
            raise ValueError("backend plugin fuzz negative sandbox contract mismatch")
        if (
            self.artifact_provenance_contract
            != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
        ):
            raise ValueError("backend plugin fuzz negative provenance contract mismatch")
        if self.resource_budget_contract != BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT:
            raise ValueError("backend plugin fuzz negative budget contract mismatch")
        if (
            self.required_bindings
            != BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS
        ):
            raise ValueError("backend plugin fuzz negative required bindings changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin fuzz negative blocked surfaces changed")
        if type(self.cases) is not tuple:
            raise TypeError("backend plugin fuzz negative cases must be a tuple")
        if len(self.cases) > MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASES:
            raise ValueError("backend plugin fuzz negative case count exceeds limit")
        for case in self.cases:
            if not isinstance(case, BackendPluginFuzzNegativeTestCase):
                raise TypeError("backend plugin fuzz negative cases must be case objects")
        if type(self.issues) is not tuple:
            raise TypeError("backend plugin fuzz negative issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_ISSUES:
            raise ValueError("backend plugin fuzz negative issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPluginFuzzNegativeTestIssue):
                raise TypeError("backend plugin fuzz negative issues must be objects")
        expected_issues = _derive_negative_test_issues(self)
        if self.issues != expected_issues:
            raise ValueError("backend plugin fuzz negative issues must be derived")

    @property
    def case_count(self) -> int:
        """Return the number of accepted negative-test cases."""

        return len(self.cases)

    @property
    def evidence_ready(self) -> bool:
        """Return whether fuzz/negative evidence is internally complete."""

        return bool(self.cases) and not self.issues

    @property
    def execution_allowed(self) -> bool:
        """Return whether this evidence grants execution permission."""

        return False


class BackendPluginFuzzNegativeTestsError(ValueError):
    """Raised when backend plugin fuzz/negative evidence fails."""


def build_backend_plugin_fuzz_negative_tests_report(
    cases: tuple[BackendPluginFuzzNegativeTestCase, ...] | None = None,
) -> BackendPluginFuzzNegativeTestsReport:
    """Build the current data-only fuzz and negative-test evidence report."""

    normalized_cases = _current_negative_test_cases() if cases is None else cases
    report = BackendPluginFuzzNegativeTestsReport(
        cases=normalized_cases,
        issues=(),
    )
    return BackendPluginFuzzNegativeTestsReport(
        cases=normalized_cases,
        issues=_derive_negative_test_issues(report),
    )


def assert_backend_plugin_fuzz_negative_tests(
    report: BackendPluginFuzzNegativeTestsReport,
) -> BackendPluginFuzzNegativeTestsReport:
    """Return the report or raise when fuzz/negative evidence is incomplete."""

    if not isinstance(report, BackendPluginFuzzNegativeTestsReport):
        raise TypeError("backend plugin fuzz negative tests must be report object")
    if not report.evidence_ready:
        lines = ["backend plugin fuzz negative tests failed:"]
        for issue in report.issues:
            lines.append(f"- {issue.case_id}: {issue.issue_code}")
        raise BackendPluginFuzzNegativeTestsError("\n".join(lines))
    return report


def backend_plugin_fuzz_negative_tests_report_to_dict(
    report: BackendPluginFuzzNegativeTestsReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible fuzz/negative evidence report."""

    if not isinstance(report, BackendPluginFuzzNegativeTestsReport):
        raise TypeError("backend plugin fuzz negative tests must be report object")
    return {
        "artifact_provenance_contract": report.artifact_provenance_contract,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "case_count": report.case_count,
        "cases": [
            {
                "blocked_surface": case.blocked_surface,
                "case_id": case.case_id,
                "case_kind": case.case_kind,
                "case_status": case.case_status,
                "evidence_id": case.evidence_id,
                "expected_result": case.expected_result,
                "seed_id": case.seed_id,
            }
            for case in report.cases
        ],
        "evidence_ready": report.evidence_ready,
        "execution_allowed": report.execution_allowed,
        "execution_permission": report.execution_permission,
        "issues": [
            {
                "case_id": issue.case_id,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "negative_tests_contract": report.negative_tests_contract,
        "negative_tests_policy": report.negative_tests_policy,
        "negative_tests_status": report.negative_tests_status,
        "required_bindings": list(report.required_bindings),
        "resource_budget_contract": report.resource_budget_contract,
        "sandbox_model_contract": report.sandbox_model_contract,
        "schema_version": BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_REPORT_SCHEMA_VERSION,
        "seed_policy": report.seed_policy,
    }


def dump_backend_plugin_fuzz_negative_tests_report(
    report: BackendPluginFuzzNegativeTestsReport,
) -> str:
    """Render a stable backend plugin fuzz/negative evidence report."""

    text = json.dumps(
        backend_plugin_fuzz_negative_tests_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REPORT_BYTES:
        raise ValueError("backend plugin fuzz negative report exceeds byte limit")
    return text + "\n"


def _current_negative_test_cases() -> tuple[BackendPluginFuzzNegativeTestCase, ...]:
    return (
        BackendPluginFuzzNegativeTestCase(
            case_id="forbidden_execution_surface_identifier",
            case_kind="forbidden_execution_surface",
            evidence_id="backend_plugin_artifact_provenance.rejects_forbidden_identifiers",
            seed_id="seed_python_module_identifier",
            blocked_surface="dynamic_import",
            expected_result="rejects_before_execution",
            case_status="covered_by_repository_tests",
        ),
        BackendPluginFuzzNegativeTestCase(
            case_id="invalid_artifact_digest",
            case_kind="invalid_digest",
            evidence_id="backend_plugin_artifact_provenance.rejects_invalid_digest",
            seed_id="seed_invalid_sha256_digest",
            blocked_surface="generated_artifact_execution",
            expected_result="rejects_before_execution",
            case_status="covered_by_repository_tests",
        ),
        BackendPluginFuzzNegativeTestCase(
            case_id="oversized_resource_budget",
            case_kind="oversized_resource_budget",
            evidence_id="backend_plugin_resource_budget.rejects_limits_above_policy",
            seed_id="seed_oversized_memory_budget",
            blocked_surface="device_access",
            expected_result="rejects_before_execution",
            case_status="covered_by_repository_tests",
        ),
        BackendPluginFuzzNegativeTestCase(
            case_id="duplicate_evidence_record",
            case_kind="duplicate_record",
            evidence_id="backend_plugin_resource_budget.rejects_duplicate_budget_ids",
            seed_id="seed_duplicate_budget_id",
            blocked_surface="generated_artifact_execution",
            expected_result="rejects_before_execution",
            case_status="covered_by_repository_tests",
        ),
        BackendPluginFuzzNegativeTestCase(
            case_id="schema_forbidden_surface_keys",
            case_kind="schema_fail_closed",
            evidence_id="backend_plugin_resource_budget.schema_fails_closed",
            seed_id="seed_forbidden_schema_surface_keys",
            blocked_surface="backend_plugin_discovery",
            expected_result="rejects_before_execution",
            case_status="covered_by_repository_tests",
        ),
    )


def _derive_negative_test_issues(
    report: BackendPluginFuzzNegativeTestsReport,
) -> tuple[BackendPluginFuzzNegativeTestIssue, ...]:
    issues: list[BackendPluginFuzzNegativeTestIssue] = []
    case_ids = tuple(case.case_id for case in report.cases)
    duplicate_ids = {case_id for case_id in case_ids if case_ids.count(case_id) > 1}
    for case_id in sorted(duplicate_ids):
        issues.append(
            BackendPluginFuzzNegativeTestIssue(
                case_id=case_id,
                issue_code="duplicate_case_id",
            )
        )
    observed_kinds = frozenset(case.case_kind for case in report.cases)
    for required_kind in sorted(BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS):
        if required_kind not in observed_kinds:
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=required_kind,
                    issue_code="missing_required_case_kind",
                )
            )
    for case in report.cases:
        if case.case_kind not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS:
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=case.case_id,
                    issue_code="case_kind_invalid",
                )
            )
        if case.blocked_surface not in RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=case.case_id,
                    issue_code="blocked_surface_invalid",
                )
            )
        if (
            case.expected_result
            not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_EXPECTED_RESULTS
        ):
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=case.case_id,
                    issue_code="expected_result_invalid",
                )
            )
        if case.case_status not in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_STATUSES:
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=case.case_id,
                    issue_code="case_status_invalid",
                )
            )
    if report.sandbox_model_contract != BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT:
        issues.append(
            BackendPluginFuzzNegativeTestIssue(
                case_id="sandbox_model",
                issue_code="sandbox_binding_mismatch",
            )
        )
    if (
        report.artifact_provenance_contract
        != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    ):
        issues.append(
            BackendPluginFuzzNegativeTestIssue(
                case_id="artifact_provenance",
                issue_code="artifact_provenance_binding_mismatch",
            )
        )
    if report.resource_budget_contract != BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT:
        issues.append(
            BackendPluginFuzzNegativeTestIssue(
                case_id="resource_budget",
                issue_code="resource_budget_binding_mismatch",
            )
        )
    if report.seed_policy != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY:
        issues.append(
            BackendPluginFuzzNegativeTestIssue(
                case_id="fuzz_seed_policy",
                issue_code="seed_policy_mismatch",
            )
        )
    for binding in BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS:
        if not _report_has_binding(report, binding):
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=binding,
                    issue_code="missing_required_binding",
                )
            )
    if (
        report.execution_permission
        != BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION
    ):
        for case in report.cases:
            issues.append(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=case.case_id,
                    issue_code="execution_permission_granted",
                )
            )
    return tuple(issues)


def _report_has_binding(
    report: BackendPluginFuzzNegativeTestsReport,
    binding: str,
) -> bool:
    if binding == "sandbox_model":
        return report.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    if binding == "artifact_provenance":
        return (
            report.artifact_provenance_contract
            == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
        )
    if binding == "resource_budget":
        return report.resource_budget_contract == BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    if binding == "negative_case_inventory":
        return (
            frozenset(case.case_kind for case in report.cases)
            == BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS
        )
    if binding == "fuzz_seed_policy":
        return report.seed_policy == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY
    return False


def _validate_test_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _TEST_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend negative-test identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend negative-test field limit")
    if value in _FORBIDDEN_TEST_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


__all__ = [
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_REPORT_SCHEMA_VERSION",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_STATUSES",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_EXPECTED_RESULTS",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_ISSUE_CODES",
    "BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS",
    "MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASES",
    "MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_FIELD_BYTES",
    "MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_ISSUES",
    "MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REPORT_BYTES",
    "BackendPluginFuzzNegativeTestCase",
    "BackendPluginFuzzNegativeTestIssue",
    "BackendPluginFuzzNegativeTestsError",
    "BackendPluginFuzzNegativeTestsReport",
    "assert_backend_plugin_fuzz_negative_tests",
    "backend_plugin_fuzz_negative_tests_report_to_dict",
    "build_backend_plugin_fuzz_negative_tests_report",
    "dump_backend_plugin_fuzz_negative_tests_report",
]
