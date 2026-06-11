from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_candidate_scoring_policy import (
    build_current_runtime_candidate_scoring_policy,
)
from tuc import (
    MAX_RUNTIME_CANDIDATE_SCORING_COMPONENTS,
    RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS,
    RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS,
    RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT,
    RUNTIME_CANDIDATE_SCORING_POLICY_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeCandidateScoringComponent,
    RuntimeCandidateScoringPolicyError,
    RuntimeCandidateScoringPolicyIssue,
    RuntimeCandidateScoringPolicyReport,
    assert_runtime_candidate_scoring_policy,
    dump_runtime_candidate_scoring_policy_report,
    runtime_candidate_scoring_policy_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_candidate_scoring_policy.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/runtime_candidate_scoring_policy/current_policy_report.json"
)


def test_runtime_candidate_scoring_policy_is_complete() -> None:
    report = build_current_runtime_candidate_scoring_policy()

    assert report.policy_complete
    assert report.policy_contract == RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT
    assert report.active_component_order == RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS
    assert report.blocked_component_names == RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS
    assert not report.automatic_global_optimization_enabled
    assert not report.noise_error_budget_components_enabled
    assert assert_runtime_candidate_scoring_policy(report) is report


def test_runtime_candidate_scoring_policy_dump_matches_golden() -> None:
    report = build_current_runtime_candidate_scoring_policy()

    assert dump_runtime_candidate_scoring_policy_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_runtime_candidate_scoring_policy_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_candidate_scoring_policy.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"policy_complete": true' in completed.stdout
    assert '"noise_error_budget_components_enabled": false' in completed.stdout
    assert '"benchmark_score"' in completed.stdout


def test_runtime_candidate_scoring_policy_rejects_hand_written_issues() -> None:
    report = build_current_runtime_candidate_scoring_policy()
    bad_components = tuple(reversed(report.components))

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeCandidateScoringPolicyReport(
            components=bad_components,
            issues=(),
        )


def test_runtime_candidate_scoring_policy_blocks_noise_component_activation() -> None:
    report = build_current_runtime_candidate_scoring_policy()
    bad_components = tuple(
        replace(
            component,
            status="active",
            ordering="minimize",
            blocker="none",
        )
        if component.component_name == "noise_penalty"
        else component
        for component in report.components
    )
    issues = (
        RuntimeCandidateScoringPolicyIssue(
            component_name="policy",
            issue_code="active_component_order_mismatch",
        ),
        RuntimeCandidateScoringPolicyIssue(
            component_name="policy",
            issue_code="blocked_component_set_mismatch",
        ),
        RuntimeCandidateScoringPolicyIssue(
            component_name="noise_penalty",
            issue_code="blocked_component_enabled",
        ),
    )

    failed = RuntimeCandidateScoringPolicyReport(
        components=bad_components,
        issues=issues,
    )

    with pytest.raises(RuntimeCandidateScoringPolicyError, match="noise_penalty"):
        assert_runtime_candidate_scoring_policy(failed)


def test_runtime_candidate_scoring_policy_rejects_global_optimization_flag() -> None:
    report = build_current_runtime_candidate_scoring_policy()

    with pytest.raises(ValueError, match="global optimization"):
        RuntimeCandidateScoringPolicyReport(
            components=report.components,
            issues=(),
            automatic_global_optimization_enabled=True,
        )


def test_runtime_candidate_scoring_policy_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeCandidateScoringComponent(
            component_name="plugin_entrypoint",
            status="blocked",
            ordering="blocked",
            evidence_source="future_noise_model",
            blocker="blocked",
        )


def test_runtime_candidate_scoring_policy_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        runtime_candidate_scoring_policy_report_to_dict(object())  # type: ignore[arg-type]


def test_runtime_candidate_scoring_policy_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_candidate_scoring_policy.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_CANDIDATE_SCORING_POLICY_SCHEMA_VERSION
    )
    assert schema["properties"]["policy_contract"]["const"] == (
        RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT
    )
    assert schema["properties"]["components"]["maxItems"] == (
        MAX_RUNTIME_CANDIDATE_SCORING_COMPONENTS
    )
    assert [
        item["const"]
        for item in schema["properties"]["active_component_order"]["prefixItems"]
    ] == list(RUNTIME_CANDIDATE_SCORING_ACTIVE_COMPONENTS)
    assert [
        item["const"]
        for item in schema["properties"]["blocked_component_names"]["prefixItems"]
    ] == list(RUNTIME_CANDIDATE_SCORING_BLOCKED_COMPONENTS)
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_candidate_scoring_policy_schema_fails_closed() -> None:
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
        "generated_code",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["component"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_candidate_scoring_policy_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_CANDIDATE_SCORING_POLICY_SCHEMA_VERSION
    assert golden["policy_contract"] == RUNTIME_CANDIDATE_SCORING_POLICY_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["policy_complete"] is True
    assert golden["issues"] == []
    assert golden["component_count"] == len(golden["components"]) == 9


def test_runtime_candidate_scoring_policy_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_candidate_scoring_policy.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_CANDIDATE_SCORING_POLICY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0099-runtime-candidate-scoring-policy.md"),
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
