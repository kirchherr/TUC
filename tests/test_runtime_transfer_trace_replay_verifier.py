from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.runtime_transfer_evidence import (
    build_current_runtime_transfer_evidence_report,
)
from examples.runtime_transfer_trace_index import (
    build_current_runtime_transfer_trace_index_report,
)
from examples.runtime_transfer_trace_replay_verifier import (
    build_report,
    build_transfer_trace_replay_verifier_report,
)
from tuc.runtime.transfer_evidence import dump_runtime_transfer_evidence_report
from tuc.runtime.transfer_trace_index import dump_runtime_transfer_trace_index_report
from tuc.runtime.transfer_trace_replay_verifier import (
    RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS,
    RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT,
    RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY,
    RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY,
    RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE,
    RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
    assert_runtime_transfer_trace_replay_verifier,
    build_runtime_transfer_trace_replay_verifier_report,
)

GOLDEN_PATH = Path("tests/golden/runtime_transfer_trace_replay_verifier/current_report.json")
SCHEMA_PATH = Path("schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json")


def test_runtime_transfer_trace_replay_verifier_passes() -> None:
    report = build_transfer_trace_replay_verifier_report()

    assert report.replay_contract == RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT
    assert report.replay_mode == RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE
    assert report.input_policy == RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY
    assert report.reexecution_policy == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY
    )
    assert report.graph_name == "runtime_backend_equivalence"
    assert report.passed
    assert report.issues == ()
    assert report.check_count == 6
    assert {check.row_status for check in report.checks} == {
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CHECK_STATUS
    }
    assert tuple(check.check_id for check in report.checks) == (
        "graph_name_match",
        "transfer_evidence_digest_replayed",
        "partition_plan_digest_bound",
        "transfer_count_bound",
        "transfer_metadata_digest_replayed",
        "trace_materialization_policy_bound",
    )
    assert assert_runtime_transfer_trace_replay_verifier(report) is report


def test_runtime_transfer_trace_replay_verifier_dump_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_runtime_transfer_trace_replay_verifier_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_transfer_trace_replay_verifier.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT in completed.stdout
    assert "metadata_digest_replay_only" in completed.stdout
    assert "transfer_not_materialized_as_runtime_step" in completed.stdout
    assert "runtime_reexecution_not_required" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_runtime_transfer_trace_replay_verifier_detects_forged_evidence_digest() -> None:
    evidence_text, trace_index_text = _current_serialized_reports()
    trace_index = json.loads(trace_index_text)
    trace_index["source_transfer_evidence_digest"] = "sha256:" + "1" * 64
    forged_trace_index_text = json.dumps(trace_index, indent=2, sort_keys=True) + "\n"

    report = build_runtime_transfer_trace_replay_verifier_report(
        evidence_text,
        forged_trace_index_text,
    )

    assert not report.passed
    assert {issue.issue_code for issue in report.issues} == {
        "transfer_evidence_digest_replayed_mismatch",
    }
    with pytest.raises(AssertionError, match="transfer_evidence_digest"):
        assert_runtime_transfer_trace_replay_verifier(report)


def test_runtime_transfer_trace_replay_verifier_detects_record_drift() -> None:
    evidence_text, trace_index_text = _current_serialized_reports()
    trace_index = json.loads(trace_index_text)
    trace_index["records"][0]["planned_bytes"] = 48
    trace_index["total_planned_bytes"] = 48
    forged_trace_index_text = json.dumps(trace_index, indent=2, sort_keys=True) + "\n"

    report = build_runtime_transfer_trace_replay_verifier_report(
        evidence_text,
        forged_trace_index_text,
    )

    assert not report.passed
    assert {issue.issue_code for issue in report.issues} == {
        "transfer_metadata_digest_replayed_mismatch",
    }


def test_runtime_transfer_trace_replay_verifier_rejects_source_or_raw_values() -> None:
    evidence_text, trace_index_text = _current_serialized_reports()

    with pytest.raises(ValueError, match="forbidden transfer trace replay"):
        build_runtime_transfer_trace_replay_verifier_report(
            evidence_text + '{"python_source": "@triton.jit"}',
            trace_index_text,
        )


def test_runtime_transfer_trace_replay_verifier_rejects_non_json_report() -> None:
    _, trace_index_text = _current_serialized_reports()

    with pytest.raises(ValueError, match="valid JSON"):
        build_runtime_transfer_trace_replay_verifier_report(
            "not json",
            trace_index_text,
        )


def test_runtime_transfer_trace_replay_verifier_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["replay_contract"]["const"] == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT
    )
    assert schema["properties"]["replay_mode"]["const"] == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPLAY_MODE
    )
    assert schema["properties"]["input_policy"]["const"] == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_INPUT_POLICY
    )
    assert schema["properties"]["reexecution_policy"]["const"] == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REEXECUTION_POLICY
    )
    assert schema["properties"]["check_count"]["const"] == 6
    assert schema["$defs"]["check"]["additionalProperties"] is False
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_transfer_trace_replay_verifier_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
    )
    assert golden["replay_contract"] == RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER_CONTRACT
    assert golden["check_count"] == len(golden["checks"]) == 6
    assert golden["passed"] is True
    assert golden["issues"] == []


def test_runtime_transfer_trace_replay_verifier_is_referenced() -> None:
    example_path = "examples/runtime_transfer_trace_replay_verifier.py"
    schema_path = "schemas/runtime_transfer_trace_replay_verifier_report.v0.schema.json"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
        Path("docs/RUNTIME_TRANSFER_EVIDENCE.md"),
        Path("docs/RUNTIME_TRANSFER_TRACE_INDEX.md"),
        Path("docs/RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
        Path("docs/RUNTIME_TRANSFER_EVIDENCE.md"),
        Path("docs/RUNTIME_TRANSFER_TRACE_INDEX.md"),
        Path("docs/RUNTIME_TRANSFER_TRACE_REPLAY_VERIFIER.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _current_serialized_reports() -> tuple[str, str]:
    evidence_text = dump_runtime_transfer_evidence_report(
        build_current_runtime_transfer_evidence_report()
    )
    trace_index_text = dump_runtime_transfer_trace_index_report(
        build_current_runtime_transfer_trace_index_report()
    )
    return evidence_text, trace_index_text


def _load_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
