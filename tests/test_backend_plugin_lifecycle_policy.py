from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_plugin_lifecycle_policy import (
    build_current_backend_plugin_lifecycle_policy_report,
)
from tuc import (
    BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT,
    BACKEND_PLUGIN_LIFECYCLE_POLICY_REPORT_SCHEMA_VERSION,
    BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS,
    MAX_BACKEND_PLUGIN_LIFECYCLE_REQUIREMENTS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendPluginLifecyclePolicyError,
    BackendPluginLifecyclePolicyIssue,
    BackendPluginLifecyclePolicyReport,
    BackendPluginLifecycleRequirement,
    assert_backend_plugin_lifecycle_policy,
    backend_plugin_lifecycle_policy_report_to_dict,
    build_backend_plugin_lifecycle_policy_report,
    dump_backend_plugin_lifecycle_policy_report,
)

SCHEMA_PATH = Path("schemas/backend_plugin_lifecycle_policy_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/backend_plugin_lifecycle_policy/current_report.json"
)


def test_backend_plugin_lifecycle_policy_blocks_plugins_by_default() -> None:
    report = build_current_backend_plugin_lifecycle_policy_report()

    assert report.policy_enforced
    assert not report.ready_to_enable_plugins
    assert report.missing_requirement_count == 2
    assert not report.plugin_discovery_enabled
    assert not report.artifact_execution_enabled
    assert not report.native_plugin_abi_enabled
    assert tuple(item.requirement_id for item in report.requirements) == (
        BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS
    )
    assert tuple(item.status for item in report.requirements[:7]) == (
        "satisfied",
        "satisfied",
        "satisfied",
        "satisfied",
        "satisfied",
        "satisfied",
        "satisfied",
    )
    assert {item.status for item in report.requirements[7:]} == {"missing"}


def test_backend_plugin_lifecycle_policy_assertion_passes() -> None:
    report = build_current_backend_plugin_lifecycle_policy_report()

    assert assert_backend_plugin_lifecycle_policy(report) is report


def test_backend_plugin_lifecycle_policy_rejects_hand_written_issues() -> None:
    report = build_current_backend_plugin_lifecycle_policy_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginLifecyclePolicyReport(
            requirements=report.requirements,
            policy_issues=(
                BackendPluginLifecyclePolicyIssue(
                    subject="backend_plugin_discovery",
                    issue_code="plugin_discovery_enabled",
                ),
            ),
        )


def test_backend_plugin_lifecycle_policy_rejects_missing_required_requirement() -> None:
    report = build_current_backend_plugin_lifecycle_policy_report()
    requirements = report.requirements[:-1]

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginLifecyclePolicyReport(
            requirements=requirements,
            policy_issues=(),
        )


def test_backend_plugin_lifecycle_policy_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        BackendPluginLifecycleRequirement(
            requirement_id="python_module",
            status="missing",
            evidence_id="not_approved",
            required_before="backend_plugin_discovery",
        )


def test_backend_plugin_lifecycle_policy_assertion_rejects_unenforced_policy() -> None:
    requirement = BackendPluginLifecycleRequirement(
        requirement_id="capability_manifest_claim_review",
        status="satisfied",
        evidence_id="manifest_claim_review.data_only.v0",
        required_before="backend_plugin_discovery",
    )
    report = BackendPluginLifecyclePolicyReport(
        requirements=(requirement,),
        policy_issues=(

            BackendPluginLifecyclePolicyIssue(
                subject="backend_author_evidence_gate",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="trusted_executor_contract",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="plugin_lifecycle_rfc",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="sandbox_model",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="artifact_provenance",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="resource_budget",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="fuzz_negative_tests",
                issue_code="missing_required_requirement",
            ),
            BackendPluginLifecyclePolicyIssue(
                subject="maintainer_approval",
                issue_code="missing_required_requirement",
            ),
        ),
    )

    with pytest.raises(BackendPluginLifecyclePolicyError, match="sandbox_model"):
        assert_backend_plugin_lifecycle_policy(report)


def test_backend_plugin_lifecycle_policy_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_plugin_lifecycle_policy.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["policy_enforced"] is True
    assert loaded["ready_to_enable_plugins"] is False
    assert loaded["missing_requirement_count"] == 2


def test_backend_plugin_lifecycle_policy_dump_matches_golden() -> None:
    report = build_backend_plugin_lifecycle_policy_report()

    assert dump_backend_plugin_lifecycle_policy_report(
        report
    ) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_backend_plugin_lifecycle_policy_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_plugin_lifecycle_policy_report_to_dict(object())  # type: ignore[arg-type]


def test_backend_plugin_lifecycle_policy_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_plugin_lifecycle_policy_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_PLUGIN_LIFECYCLE_POLICY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["policy_contract"]["const"] == (
        BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT
    )
    assert schema["properties"]["policy_enforced"]["const"] is True
    assert schema["properties"]["plugin_discovery_enabled"]["const"] is False
    assert schema["properties"]["artifact_execution_enabled"]["const"] is False
    assert schema["properties"]["native_plugin_abi_enabled"]["const"] is False
    assert schema["properties"]["requirement_count"]["const"] == 9
    assert schema["properties"]["requirements"]["maxItems"] == (
        len(BACKEND_PLUGIN_LIFECYCLE_REQUIRED_REQUIREMENTS)
    )
    assert (
        schema["properties"]["requirements"]["maxItems"]
    ) <= MAX_BACKEND_PLUGIN_LIFECYCLE_REQUIREMENTS
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_backend_plugin_lifecycle_policy_schema_fails_closed() -> None:
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
        "generated_code",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["requirement"]["properties"]
        assert forbidden not in schema["$defs"]["policy_issue"]["properties"]
    assert "python_module" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_plugin_lifecycle_policy_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        BACKEND_PLUGIN_LIFECYCLE_POLICY_REPORT_SCHEMA_VERSION
    )
    assert golden["policy_contract"] == BACKEND_PLUGIN_LIFECYCLE_POLICY_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["policy_enforced"] is True
    assert golden["ready_to_enable_plugins"] is False
    assert golden["requirement_count"] == len(golden["requirements"]) == 9
    assert golden["missing_requirement_count"] == 2
    assert golden["policy_issues"] == []


def test_backend_plugin_lifecycle_policy_schema_is_referenced() -> None:
    schema_path = "schemas/backend_plugin_lifecycle_policy_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_PLUGIN_LIFECYCLE_POLICY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0217-backend-plugin-lifecycle-policy.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


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
