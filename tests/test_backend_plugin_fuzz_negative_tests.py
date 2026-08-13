from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_plugin_fuzz_negative_tests import (
    build_current_backend_plugin_fuzz_negative_tests_report,
)
from tuc import (
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_REPORT_SCHEMA_VERSION,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS,
    BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT,
    BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASES,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendPluginFuzzNegativeTestCase,
    BackendPluginFuzzNegativeTestIssue,
    BackendPluginFuzzNegativeTestsError,
    BackendPluginFuzzNegativeTestsReport,
    assert_backend_plugin_fuzz_negative_tests,
    backend_plugin_fuzz_negative_tests_report_to_dict,
    build_backend_plugin_fuzz_negative_tests_report,
    dump_backend_plugin_fuzz_negative_tests_report,
)

SCHEMA_PATH = Path("schemas/backend_plugin_fuzz_negative_tests_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/backend_plugin_fuzz_negative_tests/current_report.json"
)


def test_backend_plugin_fuzz_negative_tests_is_data_only_and_ready() -> None:
    report = build_current_backend_plugin_fuzz_negative_tests_report()

    assert report.evidence_ready
    assert not report.execution_allowed
    assert report.execution_permission == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_EXECUTION_PERMISSION
    )
    assert report.negative_tests_contract == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
    assert report.negative_tests_policy == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY
    assert report.negative_tests_status == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS
    assert report.seed_policy == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY
    assert report.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    assert report.artifact_provenance_contract == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    assert report.resource_budget_contract == BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    assert report.required_bindings == BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS
    assert report.blocked_execution_surfaces == RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    assert report.case_count == len(BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS)
    assert report.issues == ()
    assert frozenset(case.case_kind for case in report.cases) == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS
    )
    for case in report.cases:
        assert case.case_status == "covered_by_repository_tests"
        assert case.expected_result == "rejects_before_execution"
        assert case.blocked_surface in RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        assert case.seed_id.startswith("seed_")


def test_backend_plugin_fuzz_negative_tests_assertion_passes() -> None:
    report = build_current_backend_plugin_fuzz_negative_tests_report()

    assert assert_backend_plugin_fuzz_negative_tests(report) is report


def test_backend_plugin_fuzz_negative_tests_rejects_hand_written_issues() -> None:
    report = build_current_backend_plugin_fuzz_negative_tests_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginFuzzNegativeTestsReport(
            cases=report.cases,
            issues=(
                BackendPluginFuzzNegativeTestIssue(
                    case_id=report.cases[0].case_id,
                    issue_code="duplicate_case_id",
                ),
            ),
        )


def test_backend_plugin_fuzz_negative_tests_assertion_rejects_missing_case_kind() -> None:
    report = build_current_backend_plugin_fuzz_negative_tests_report()
    reduced_cases = report.cases[:-1]
    reduced_report = BackendPluginFuzzNegativeTestsReport(
        cases=reduced_cases,
        issues=(
            BackendPluginFuzzNegativeTestIssue(
                case_id="schema_fail_closed",
                issue_code="missing_required_case_kind",
            ),
            BackendPluginFuzzNegativeTestIssue(
                case_id="negative_case_inventory",
                issue_code="missing_required_binding",
            ),
        ),
    )

    assert not reduced_report.evidence_ready
    with pytest.raises(
        BackendPluginFuzzNegativeTestsError,
        match="missing_required_case_kind",
    ):
        assert_backend_plugin_fuzz_negative_tests(reduced_report)


def test_backend_plugin_fuzz_negative_tests_assertion_rejects_duplicates() -> None:
    case = build_current_backend_plugin_fuzz_negative_tests_report().cases[0]
    report = BackendPluginFuzzNegativeTestsReport(
        cases=(case, case),
        issues=(
            BackendPluginFuzzNegativeTestIssue(
                case_id=case.case_id,
                issue_code="duplicate_case_id",
            ),
            BackendPluginFuzzNegativeTestIssue(
                case_id="duplicate_record",
                issue_code="missing_required_case_kind",
            ),
            BackendPluginFuzzNegativeTestIssue(
                case_id="invalid_digest",
                issue_code="missing_required_case_kind",
            ),
            BackendPluginFuzzNegativeTestIssue(
                case_id="oversized_resource_budget",
                issue_code="missing_required_case_kind",
            ),
            BackendPluginFuzzNegativeTestIssue(
                case_id="schema_fail_closed",
                issue_code="missing_required_case_kind",
            ),
            BackendPluginFuzzNegativeTestIssue(
                case_id="negative_case_inventory",
                issue_code="missing_required_binding",
            ),
        ),
    )

    assert not report.evidence_ready
    with pytest.raises(BackendPluginFuzzNegativeTestsError, match="duplicate_case_id"):
        assert_backend_plugin_fuzz_negative_tests(report)


def test_backend_plugin_fuzz_negative_tests_rejects_invalid_case_kind() -> None:
    with pytest.raises(ValueError, match="case kind"):
        _make_case(case_kind="runtime_execution")


def test_backend_plugin_fuzz_negative_tests_rejects_invalid_blocked_surface() -> None:
    with pytest.raises(ValueError, match="blocked surface"):
        _make_case(blocked_surface="not_a_surface")


def test_backend_plugin_fuzz_negative_tests_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        _make_case(case_id="python_module")


def test_backend_plugin_fuzz_negative_tests_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_plugin_fuzz_negative_tests.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["evidence_ready"] is True
    assert loaded["execution_allowed"] is False
    assert loaded["execution_permission"] == "not_granted"


def test_backend_plugin_fuzz_negative_tests_dump_matches_golden() -> None:
    report = build_backend_plugin_fuzz_negative_tests_report()

    assert dump_backend_plugin_fuzz_negative_tests_report(
        report
    ) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_backend_plugin_fuzz_negative_tests_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_plugin_fuzz_negative_tests_report_to_dict(object())  # type: ignore[arg-type]


def test_backend_plugin_fuzz_negative_tests_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_plugin_fuzz_negative_tests_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["negative_tests_contract"]["const"] == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
    )
    assert schema["properties"]["negative_tests_policy"]["const"] == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_POLICY
    )
    assert schema["properties"]["negative_tests_status"]["const"] == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_STATUS
    )
    assert schema["properties"]["seed_policy"]["const"] == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_SEED_POLICY
    )
    assert schema["properties"]["execution_allowed"]["const"] is False
    assert schema["properties"]["execution_permission"]["const"] == "not_granted"
    assert schema["properties"]["case_count"]["const"] == (
        len(BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS)
    )
    assert schema["properties"]["cases"]["maxItems"] <= (
        MAX_BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASES
    )
    assert [
        item["const"]
        for item in schema["properties"]["required_bindings"]["prefixItems"]
    ] == list(BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_REQUIRED_BINDINGS)
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    assert set(schema["$defs"]["case_kind"]["enum"]) == set(
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS
    )


def test_backend_plugin_fuzz_negative_tests_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "artifact_bytes",
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "python_module",
        "generated_code",
        "raw_benchmark_output",
        "raw_timing_samples",
        "fuzz_corpus",
        "url",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["base_case"]["properties"]
        assert forbidden not in schema["$defs"]["negative_test_issue"]["properties"]
    assert "python_module" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_plugin_fuzz_negative_tests_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_REPORT_SCHEMA_VERSION
    )
    assert golden["negative_tests_contract"] == BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["execution_allowed"] is False
    assert golden["execution_permission"] == "not_granted"
    assert golden["evidence_ready"] is True
    assert golden["case_count"] == len(golden["cases"]) == (
        len(BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS)
    )
    assert golden["issues"] == []
    assert set(case["case_kind"] for case in golden["cases"]) == set(
        BACKEND_PLUGIN_FUZZ_NEGATIVE_TEST_CASE_KINDS
    )


def test_backend_plugin_fuzz_negative_tests_schema_is_referenced() -> None:
    schema_path = "schemas/backend_plugin_fuzz_negative_tests_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0221-backend-plugin-fuzz-negative-tests.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _make_case(**overrides: str) -> BackendPluginFuzzNegativeTestCase:
    values = {
        "case_id": "forbidden_execution_surface_identifier",
        "case_kind": "forbidden_execution_surface",
        "case_status": "covered_by_repository_tests",
        "blocked_surface": "dynamic_import",
        "evidence_id": "backend_plugin_artifact_provenance.rejects_forbidden_identifiers",
        "expected_result": "rejects_before_execution",
        "seed_id": "seed_python_module_identifier",
    }
    values.update(overrides)
    return BackendPluginFuzzNegativeTestCase(**values)


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
