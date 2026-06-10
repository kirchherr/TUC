from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_candidate_score_evidence import (
    build_profiled_candidate_score_evidence_report,
)
from tuc import (
    MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_SCORES,
    RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT,
    RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RuntimeCandidateScoreEvidenceError,
    RuntimeCandidateScoreEvidenceIssue,
    RuntimeCandidateScoreEvidenceReport,
    assert_runtime_candidate_score_evidence,
    dump_runtime_candidate_score_evidence_report,
    runtime_candidate_score_evidence_report_to_dict,
)

SCHEMA_PATH = Path("schemas/runtime_candidate_score_evidence_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/runtime_candidate_score_evidence/profiled_candidate_score_report.json"
)


def test_profiled_candidate_score_evidence_passes() -> None:
    report = build_profiled_candidate_score_evidence_report()

    assert report.passed
    assert report.evidence_contract == RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT
    assert report.default_plan_candidate_score_count == 0
    assert report.compiler_decision_candidate_score_count == 4
    assert report.compiler_decision_candidate_score_digest == report.candidate_score_digest
    assert len(report.candidate_scores) == 4
    assert report.operation_count == 2
    assert report.selected_candidate_count == 2
    assert report.rejected_candidate_count == 2
    assert report.score_units == ("latency_ns",)
    assert report.selection_stages == ("supported",)
    assert assert_runtime_candidate_score_evidence(report) is report


def test_runtime_candidate_score_evidence_dump_matches_golden() -> None:
    report = build_profiled_candidate_score_evidence_report()

    assert dump_runtime_candidate_score_evidence_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_runtime_candidate_score_evidence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_candidate_score_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"passed": true' in completed.stdout
    assert '"score_units": [' in completed.stdout
    assert '"latency_ns"' in completed.stdout


def test_runtime_candidate_score_evidence_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        runtime_candidate_score_evidence_report_to_dict(object())  # type: ignore[arg-type]


def test_runtime_candidate_score_evidence_rejects_hand_written_issues() -> None:
    report = build_profiled_candidate_score_evidence_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeCandidateScoreEvidenceReport(
            graph_name=report.graph_name,
            operation_count=report.operation_count,
            default_plan_candidate_score_count=1,
            compiler_decision_candidate_score_count=(
                report.compiler_decision_candidate_score_count
            ),
            compiler_decision_candidate_score_digest=(
                report.compiler_decision_candidate_score_digest
            ),
            candidate_scores=report.candidate_scores,
            issues=(),
        )


def test_assert_runtime_candidate_score_evidence_raises_on_default_scores() -> None:
    report = build_profiled_candidate_score_evidence_report()
    failed = RuntimeCandidateScoreEvidenceReport(
        graph_name=report.graph_name,
        operation_count=report.operation_count,
        default_plan_candidate_score_count=1,
        compiler_decision_candidate_score_count=(
            report.compiler_decision_candidate_score_count
        ),
        compiler_decision_candidate_score_digest=(
            report.compiler_decision_candidate_score_digest
        ),
        candidate_scores=report.candidate_scores,
        issues=(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="default_plan_emitted_candidate_scores",
            ),
        ),
    )

    with pytest.raises(RuntimeCandidateScoreEvidenceError, match="default_plan"):
        assert_runtime_candidate_score_evidence(failed)


def test_runtime_candidate_score_evidence_requires_one_selected_candidate() -> None:
    report = build_profiled_candidate_score_evidence_report()
    broken_scores = tuple(
        replace(score, selected=False)
        if score.operation_name == "projection"
        else score
        for score in report.candidate_scores
    )

    failed = RuntimeCandidateScoreEvidenceReport(
        graph_name=report.graph_name,
        operation_count=report.operation_count,
        default_plan_candidate_score_count=0,
        compiler_decision_candidate_score_count=(
            report.compiler_decision_candidate_score_count
        ),
        compiler_decision_candidate_score_digest=(
            report.compiler_decision_candidate_score_digest
        ),
        candidate_scores=broken_scores,
        issues=(
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="graph",
                issue_code="compiler_decision_score_digest_mismatch",
            ),
            RuntimeCandidateScoreEvidenceIssue(
                operation_name="projection",
                issue_code="selected_candidate_count_invalid",
            ),
        ),
    )

    assert not failed.passed
    assert {issue.issue_code for issue in failed.issues} == {
        "compiler_decision_score_digest_mismatch",
        "selected_candidate_count_invalid",
    }


def test_runtime_candidate_score_evidence_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_candidate_score_evidence_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT
    )
    assert schema["properties"]["candidate_scores"]["maxItems"] == (
        MAX_RUNTIME_CANDIDATE_SCORE_EVIDENCE_SCORES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_candidate_score_evidence_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["candidate_score"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_candidate_score_evidence_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_CANDIDATE_SCORE_EVIDENCE_REPORT_SCHEMA_VERSION
    )
    assert golden["evidence_contract"] == RUNTIME_CANDIDATE_SCORE_EVIDENCE_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["candidate_score_count"] == len(golden["candidate_scores"]) == 4
    assert golden["compiler_decision_candidate_score_digest"] == (
        golden["candidate_score_digest"]
    )


def test_runtime_candidate_score_evidence_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_candidate_score_evidence_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_CANDIDATE_SCORE_EVIDENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0098-runtime-candidate-score-evidence.md"),
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
