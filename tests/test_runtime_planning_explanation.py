from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_planning_explanation import (
    build_systolic_runtime_planning_explanation_report,
)
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_PLANNING_EXPLANATION_CANDIDATE_SCORE_MODES,
    RUNTIME_PLANNING_EXPLANATION_CONTRACT,
    RUNTIME_PLANNING_EXPLANATION_REPORT_SCHEMA_VERSION,
    RUNTIME_PLANNING_EXPLANATION_SELECTION_KINDS,
    RUNTIME_PLANNING_EXPLANATION_STATUSES,
    RuntimePlanningExplanationError,
    RuntimePlanningExplanationIssue,
    RuntimePlanningExplanationReport,
    assert_runtime_planning_explanation,
    dump_runtime_planning_explanation_report,
    runtime_planning_explanation_report_to_dict,
)
from tuc.runtime.planning_explanation import (
    MAX_RUNTIME_PLANNING_EXPLANATION_ISSUES,
    MAX_RUNTIME_PLANNING_EXPLANATION_STEPS,
)

SCHEMA_PATH = Path("schemas/runtime_planning_explanation_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_planning_explanation/systolic_report.json")


def test_systolic_runtime_planning_explanation_passes() -> None:
    report = build_systolic_runtime_planning_explanation_report()

    assert report.passed
    assert report.explanation_contract == RUNTIME_PLANNING_EXPLANATION_CONTRACT
    assert report.explanation_status == "passed"
    assert report.candidate_score_mode == "recorded"
    assert report.operation_count == 2
    assert report.backend_sequence == ("systolic-sim", "reference-cpu")
    assert report.selection_kinds == ("fallback", "preferred_for")
    assert report.fallback_count == 1
    assert report.transfer_edge_count == 1
    assert report.layout_conversion_count == 1
    assert report.total_transfer_bytes == 16
    assert report.total_layout_conversion_bytes == 16
    assert report.total_data_movement_bytes == 32
    assert report.candidate_score_count == 1
    assert report.steps[0].operation_name == "systolic_projection"
    assert report.steps[0].selection_kind == "preferred_for"
    assert report.steps[0].candidate_score_count == 1
    assert report.steps[0].selected_candidate_score_count == 1
    assert report.steps[1].operation_name == "host_activation"
    assert report.steps[1].selection_kind == "fallback"
    assert report.steps[1].movement_bytes == 32
    assert assert_runtime_planning_explanation(report) is report


def test_runtime_planning_explanation_dump_matches_golden() -> None:
    report = build_systolic_runtime_planning_explanation_report()

    assert dump_runtime_planning_explanation_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_runtime_planning_explanation_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_planning_explanation.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"explanation_status": "passed"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"reference-cpu"' in completed.stdout


def test_runtime_planning_explanation_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        runtime_planning_explanation_report_to_dict(object())  # type: ignore[arg-type]


def test_runtime_planning_explanation_rejects_hand_written_issues() -> None:
    report = build_systolic_runtime_planning_explanation_report()
    unknown_step = replace(
        report.steps[0],
        reason="unclassified_reason",
        selection_kind="unknown",
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimePlanningExplanationReport(
            graph_name=report.graph_name,
            steps=(unknown_step, *report.steps[1:]),
            transfer_edge_count=report.transfer_edge_count,
            layout_conversion_count=report.layout_conversion_count,
            total_transfer_bytes=report.total_transfer_bytes,
            total_layout_conversion_bytes=report.total_layout_conversion_bytes,
            total_data_movement_bytes=report.total_data_movement_bytes,
            candidate_score_mode=report.candidate_score_mode,
            issues=(),
        )


def test_assert_runtime_planning_explanation_raises_on_unknown_reason() -> None:
    report = build_systolic_runtime_planning_explanation_report()
    unknown_step = replace(
        report.steps[0],
        reason="unclassified_reason",
        selection_kind="unknown",
    )
    failed = RuntimePlanningExplanationReport(
        graph_name=report.graph_name,
        steps=(unknown_step, *report.steps[1:]),
        transfer_edge_count=report.transfer_edge_count,
        layout_conversion_count=report.layout_conversion_count,
        total_transfer_bytes=report.total_transfer_bytes,
        total_layout_conversion_bytes=report.total_layout_conversion_bytes,
        total_data_movement_bytes=report.total_data_movement_bytes,
        candidate_score_mode=report.candidate_score_mode,
        issues=(
            RuntimePlanningExplanationIssue(
                operation_name="systolic_projection",
                issue_code="unknown_selection_reason",
            ),
        ),
    )

    with pytest.raises(RuntimePlanningExplanationError, match="unknown_selection_reason"):
        assert_runtime_planning_explanation(failed)


def test_runtime_planning_explanation_rejects_forbidden_surfaces() -> None:
    report = build_systolic_runtime_planning_explanation_report()

    with pytest.raises(ValueError, match="forbidden execution surface"):
        replace(report.steps[0], reason="fallback:plugin_entrypoint=unsafe")


def test_runtime_planning_explanation_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_planning_explanation_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_PLANNING_EXPLANATION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["explanation_contract"]["const"] == (
        RUNTIME_PLANNING_EXPLANATION_CONTRACT
    )
    assert schema["properties"]["steps"]["maxItems"] == (
        MAX_RUNTIME_PLANNING_EXPLANATION_STEPS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_PLANNING_EXPLANATION_ISSUES
    )
    assert sorted(schema["properties"]["explanation_status"]["enum"]) == sorted(
        RUNTIME_PLANNING_EXPLANATION_STATUSES
    )
    assert sorted(schema["properties"]["candidate_score_mode"]["enum"]) == sorted(
        RUNTIME_PLANNING_EXPLANATION_CANDIDATE_SCORE_MODES
    )
    assert sorted(schema["$defs"]["selection_kind"]["enum"]) == sorted(
        RUNTIME_PLANNING_EXPLANATION_SELECTION_KINDS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_planning_explanation_schema_fails_closed() -> None:
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
        "kernel_source",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["explanation_step"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "python_source" in schema["$defs"]["explanation_reason"]["not"]["pattern"]
    assert "plugin_entrypoint" in schema["$defs"]["explanation_reason"]["not"]["pattern"]


def test_runtime_planning_explanation_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_PLANNING_EXPLANATION_REPORT_SCHEMA_VERSION
    assert golden["explanation_contract"] == RUNTIME_PLANNING_EXPLANATION_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["candidate_score_count"] == 1
    assert golden["backend_sequence"] == ["systolic-sim", "reference-cpu"]
    assert golden["selection_kinds"] == ["fallback", "preferred_for"]


def test_runtime_planning_explanation_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_planning_explanation_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_PLANNING_EXPLANATION.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0203-runtime-planning-explanation-report.md"),
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
