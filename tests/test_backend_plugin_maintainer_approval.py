from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_plugin_maintainer_approval import (
    build_current_backend_plugin_maintainer_approval_report,
)
from tuc import (
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
    BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_DECISIONS,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_RECORD_STATUSES,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_SCOPES,
    BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS,
    BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT,
    BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    MAX_BACKEND_PLUGIN_MAINTAINER_APPROVALS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendPluginMaintainerApprovalError,
    BackendPluginMaintainerApprovalIssue,
    BackendPluginMaintainerApprovalRecord,
    BackendPluginMaintainerApprovalReport,
    assert_backend_plugin_maintainer_approval,
    backend_plugin_maintainer_approval_report_to_dict,
    build_backend_plugin_maintainer_approval_report,
    dump_backend_plugin_maintainer_approval_report,
)

SCHEMA_PATH = Path("schemas/backend_plugin_maintainer_approval_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/backend_plugin_maintainer_approval/current_report.json")


def test_backend_plugin_maintainer_approval_is_data_only_and_ready() -> None:
    report = build_current_backend_plugin_maintainer_approval_report()

    assert report.approval_ready
    assert not report.execution_allowed
    assert report.execution_permission == (BACKEND_PLUGIN_MAINTAINER_APPROVAL_EXECUTION_PERMISSION)
    assert report.approval_contract == BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT
    assert report.approval_policy == BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY
    assert report.approval_status == BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS
    assert report.required_bindings == BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS
    assert report.blocked_execution_surfaces == RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    assert report.approval_count == 1
    assert report.issues == ()

    approval = report.approvals[0]
    assert approval.approval_scope in BACKEND_PLUGIN_MAINTAINER_APPROVAL_SCOPES
    assert approval.approval_decision in BACKEND_PLUGIN_MAINTAINER_APPROVAL_DECISIONS
    assert approval.approval_status in BACKEND_PLUGIN_MAINTAINER_APPROVAL_RECORD_STATUSES
    assert approval.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    assert approval.artifact_provenance_contract == (BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT)
    assert approval.resource_budget_contract == BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT
    assert approval.fuzz_negative_tests_contract == (BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT)
    assert approval.implementation_rfc_required is True


def test_backend_plugin_maintainer_approval_assertion_passes() -> None:
    report = build_current_backend_plugin_maintainer_approval_report()

    assert assert_backend_plugin_maintainer_approval(report) is report


def test_backend_plugin_maintainer_approval_rejects_hand_written_issues() -> None:
    report = build_current_backend_plugin_maintainer_approval_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginMaintainerApprovalReport(
            approvals=report.approvals,
            issues=(
                BackendPluginMaintainerApprovalIssue(
                    approval_id=report.approvals[0].approval_id,
                    issue_code="duplicate_approval_id",
                ),
            ),
        )


def test_backend_plugin_maintainer_approval_rejects_missing_implementation_rfc() -> None:
    approval = _make_approval(implementation_rfc_required=False)
    report = BackendPluginMaintainerApprovalReport(
        approvals=(approval,),
        issues=(
            BackendPluginMaintainerApprovalIssue(
                approval_id=approval.approval_id,
                issue_code="implementation_rfc_not_required",
            ),
            BackendPluginMaintainerApprovalIssue(
                approval_id=approval.approval_id,
                issue_code="approval_missing_required_binding",
            ),
        ),
    )

    assert not report.approval_ready
    with pytest.raises(
        BackendPluginMaintainerApprovalError,
        match="implementation_rfc_not_required",
    ):
        assert_backend_plugin_maintainer_approval(report)


def test_backend_plugin_maintainer_approval_rejects_duplicates() -> None:
    approval = build_current_backend_plugin_maintainer_approval_report().approvals[0]
    report = BackendPluginMaintainerApprovalReport(
        approvals=(approval, approval),
        issues=(
            BackendPluginMaintainerApprovalIssue(
                approval_id=approval.approval_id,
                issue_code="duplicate_approval_id",
            ),
        ),
    )

    assert not report.approval_ready
    with pytest.raises(BackendPluginMaintainerApprovalError, match="duplicate_approval_id"):
        assert_backend_plugin_maintainer_approval(report)


def test_backend_plugin_maintainer_approval_rejects_invalid_scope() -> None:
    with pytest.raises(ValueError, match="scope"):
        _make_approval(approval_scope="runtime_enablement")


def test_backend_plugin_maintainer_approval_rejects_invalid_decision() -> None:
    with pytest.raises(ValueError, match="decision"):
        _make_approval(approval_decision="execute_plugins")


def test_backend_plugin_maintainer_approval_rejects_non_bool_rfc_flag() -> None:
    with pytest.raises(TypeError, match="implementation_rfc_required"):
        _make_approval(implementation_rfc_required="yes")  # type: ignore[arg-type]


def test_backend_plugin_maintainer_approval_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        _make_approval(review_record_id="url")


def test_backend_plugin_maintainer_approval_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_plugin_maintainer_approval.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["approval_ready"] is True
    assert loaded["execution_allowed"] is False
    assert loaded["execution_permission"] == "not_granted"


def test_backend_plugin_maintainer_approval_dump_matches_golden() -> None:
    report = build_backend_plugin_maintainer_approval_report()

    assert dump_backend_plugin_maintainer_approval_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_backend_plugin_maintainer_approval_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_plugin_maintainer_approval_report_to_dict(object())  # type: ignore[arg-type]


def test_backend_plugin_maintainer_approval_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_plugin_maintainer_approval_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["approval_contract"]["const"] == (
        BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT
    )
    assert schema["properties"]["approval_policy"]["const"] == (
        BACKEND_PLUGIN_MAINTAINER_APPROVAL_POLICY
    )
    assert schema["properties"]["approval_status"]["const"] == (
        BACKEND_PLUGIN_MAINTAINER_APPROVAL_STATUS
    )
    assert schema["properties"]["execution_allowed"]["const"] is False
    assert schema["properties"]["execution_permission"]["const"] == "not_granted"
    assert schema["properties"]["approval_count"]["const"] == 1
    assert schema["properties"]["approvals"]["maxItems"] <= (
        MAX_BACKEND_PLUGIN_MAINTAINER_APPROVALS
    )
    assert [
        item["const"] for item in schema["properties"]["required_bindings"]["prefixItems"]
    ] == list(BACKEND_PLUGIN_MAINTAINER_APPROVAL_REQUIRED_BINDINGS)
    assert [
        item["const"] for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_backend_plugin_maintainer_approval_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "python_module",
        "email",
        "token",
        "generated_code",
        "raw_benchmark_output",
        "raw_timing_samples",
        "fuzz_corpus",
        "url",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["base_approval"]["properties"]
        assert forbidden not in schema["$defs"]["approval_issue"]["properties"]
    assert "python_module" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "token" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == ("^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


def test_backend_plugin_maintainer_approval_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (BACKEND_PLUGIN_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION)
    assert golden["approval_contract"] == BACKEND_PLUGIN_MAINTAINER_APPROVAL_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    assert golden["execution_allowed"] is False
    assert golden["execution_permission"] == "not_granted"
    assert golden["approval_ready"] is True
    assert golden["approval_count"] == len(golden["approvals"]) == 1
    assert golden["issues"] == []
    assert golden["approvals"][0]["implementation_rfc_required"] is True


def test_backend_plugin_maintainer_approval_schema_is_referenced() -> None:
    schema_path = "schemas/backend_plugin_maintainer_approval_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_PLUGIN_MAINTAINER_APPROVAL.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0222-backend-plugin-maintainer-approval.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _make_approval(**overrides: object) -> BackendPluginMaintainerApprovalRecord:
    values: dict[str, object] = {
        "approval_id": "backend_plugin_lifecycle_maintainer_approval",
        "approval_scope": "lifecycle_evidence_gate",
        "review_record_id": "rfc_0222_backend_plugin_maintainer_approval",
        "maintainer_group_id": "tuc_maintainers",
        "approval_decision": "approved_for_proposal_gate",
        "approval_status": "reviewed_by_maintainers",
        "sandbox_model_contract": BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
        "artifact_provenance_contract": BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
        "resource_budget_contract": BACKEND_PLUGIN_RESOURCE_BUDGET_CONTRACT,
        "fuzz_negative_tests_contract": BACKEND_PLUGIN_FUZZ_NEGATIVE_TESTS_CONTRACT,
        "implementation_rfc_required": True,
    }
    values.update(overrides)
    return BackendPluginMaintainerApprovalRecord(**values)  # type: ignore[arg-type]


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
