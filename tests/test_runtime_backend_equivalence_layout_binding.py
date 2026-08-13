from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.runtime_backend_equivalence_layout_binding import (
    build_backend_equivalence_layout_binding_report,
    build_report,
)
from examples.runtime_layout_conversion_trace_replay_verifier import (
    build_layout_conversion_trace_replay_verifier_report,
)
from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from tuc.runtime.backend_equivalence import dump_runtime_backend_equivalence_report
from tuc.runtime.backend_equivalence_layout_binding import (
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECK_STATUS,
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT,
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY,
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE,
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY,
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_SCHEMA_VERSION,
    assert_runtime_backend_equivalence_layout_binding,
    build_runtime_backend_equivalence_layout_binding_report,
)
from tuc.runtime.layout_conversion_trace_replay_verifier import (
    dump_runtime_layout_conversion_trace_replay_verifier_report,
)

GOLDEN_PATH = Path("tests/golden/runtime_backend_equivalence_layout_binding/current_report.json")
SCHEMA_PATH = Path("schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json")


def test_runtime_backend_equivalence_layout_binding_passes() -> None:
    report = build_backend_equivalence_layout_binding_report()

    assert report.binding_contract == RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT
    assert report.binding_mode == RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE
    assert report.input_policy == RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY
    assert report.reexecution_policy == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY
    )
    assert report.graph_name == "runtime_mixed_backend_equivalence"
    assert report.baseline_run_id == "reference_cpu"
    assert report.candidate_run_id == "mixed_accelerators"
    assert report.candidate_backend_count == 2
    assert report.layout_replay_check_count == 6
    assert report.check_count == 8
    assert report.passed
    assert report.issues == ()
    assert {check.row_status for check in report.checks} == {
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CHECK_STATUS
    }
    assert tuple(check.check_id for check in report.checks) == (
        "backend_equivalence_contract_bound",
        "layout_trace_replay_contract_bound",
        "graph_name_bound",
        "backend_equivalence_passed_bound",
        "layout_trace_replay_passed_bound",
        "raw_value_policy_bound",
        "candidate_backend_diversity_bound",
        "layout_replay_checks_bound",
    )
    assert assert_runtime_backend_equivalence_layout_binding(report) is report


def test_runtime_backend_equivalence_layout_binding_dump_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_runtime_backend_equivalence_layout_binding_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_backend_equivalence_layout_binding.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT in completed.stdout
    assert "metadata_digest_binding_only" in completed.stdout
    assert "runtime_layout_conversion_trace_replay_verifier" in completed.stdout
    assert "mixed_backend_candidate" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_runtime_backend_equivalence_layout_binding_detects_graph_mismatch() -> None:
    equivalence_text, replay_text = _current_serialized_reports()
    replay = json.loads(replay_text)
    replay["graph_name"] = "runtime_vector_backend_equivalence"
    forged_replay_text = json.dumps(replay, indent=2, sort_keys=True) + "\n"

    report = build_runtime_backend_equivalence_layout_binding_report(
        equivalence_text,
        forged_replay_text,
    )

    assert not report.passed
    assert {issue.issue_code for issue in report.issues} == {
        "graph_name_bound_mismatch",
    }


def test_runtime_backend_equivalence_layout_binding_detects_single_candidate_backend() -> None:
    equivalence_text, replay_text = _current_serialized_reports()
    equivalence = json.loads(equivalence_text)
    equivalence["runs"][1]["planned_backend_sequence"] = [
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
    ]
    forged_equivalence_text = json.dumps(equivalence, indent=2, sort_keys=True) + "\n"

    report = build_runtime_backend_equivalence_layout_binding_report(
        forged_equivalence_text,
        replay_text,
    )

    assert not report.passed
    assert {issue.issue_code for issue in report.issues} == {
        "candidate_backend_diversity_bound_mismatch",
    }
    with pytest.raises(AssertionError, match="candidate_backend_diversity"):
        assert_runtime_backend_equivalence_layout_binding(report)


def test_runtime_backend_equivalence_layout_binding_rejects_source_or_raw_values() -> None:
    equivalence_text, replay_text = _current_serialized_reports()

    with pytest.raises(ValueError, match="forbidden backend layout binding"):
        build_runtime_backend_equivalence_layout_binding_report(
            equivalence_text + '{"python_source": "@triton.jit"}',
            replay_text,
        )

    with pytest.raises(ValueError, match="forbidden backend layout binding"):
        build_runtime_backend_equivalence_layout_binding_report(
            equivalence_text + '{"runtime_handle": "opaque"}',
            replay_text,
        )


def test_runtime_backend_equivalence_layout_binding_rejects_non_json_report() -> None:
    _, replay_text = _current_serialized_reports()

    with pytest.raises(ValueError, match="valid JSON"):
        build_runtime_backend_equivalence_layout_binding_report(
            "not json",
            replay_text,
        )


def test_runtime_backend_equivalence_layout_binding_rejects_missing_checks() -> None:
    report = build_backend_equivalence_layout_binding_report()

    with pytest.raises(ValueError, match="required check count"):
        type(report)(
            graph_name=report.graph_name,
            baseline_run_id=report.baseline_run_id,
            candidate_run_id=report.candidate_run_id,
            backend_equivalence_report_digest=report.backend_equivalence_report_digest,
            layout_trace_replay_report_digest=report.layout_trace_replay_report_digest,
            backend_equivalence_comparison_metadata_digest=(
                report.backend_equivalence_comparison_metadata_digest
            ),
            layout_trace_replay_metadata_digest=report.layout_trace_replay_metadata_digest,
            baseline_backend_sequence_digest=report.baseline_backend_sequence_digest,
            candidate_backend_sequence_digest=report.candidate_backend_sequence_digest,
            candidate_backend_count=report.candidate_backend_count,
            layout_replay_check_count=report.layout_replay_check_count,
            checks=report.checks[:-1],
            issues=(),
        )


def test_runtime_backend_equivalence_layout_binding_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["binding_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT
    )
    assert schema["properties"]["binding_mode"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MODE
    )
    assert schema["properties"]["input_policy"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_INPUT_POLICY
    )
    assert schema["properties"]["reexecution_policy"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REEXECUTION_POLICY
    )
    assert schema["properties"]["check_count"]["const"] == 8
    assert schema["properties"]["layout_replay_check_count"]["const"] == 6
    assert schema["$defs"]["check"]["additionalProperties"] is False
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_backend_equivalence_layout_binding_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_REPORT_SCHEMA_VERSION
    )
    assert golden["binding_contract"] == (RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_CONTRACT)
    assert golden["check_count"] == len(golden["checks"]) == 8
    assert golden["layout_replay_check_count"] == 6
    assert golden["candidate_backend_count"] == 2
    assert golden["passed"] is True
    assert golden["issues"] == []


def test_runtime_backend_equivalence_layout_binding_is_referenced() -> None:
    example_path = "examples/runtime_backend_equivalence_layout_binding.py"
    schema_path = "schemas/runtime_backend_equivalence_layout_binding_report.v0.schema.json"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _current_serialized_reports() -> tuple[str, str]:
    equivalence_text = dump_runtime_backend_equivalence_report(
        build_mixed_backend_equivalence_report()
    )
    replay_text = dump_runtime_layout_conversion_trace_replay_verifier_report(
        build_layout_conversion_trace_replay_verifier_report()
    )
    return equivalence_text, replay_text


def _load_schema() -> dict[str, object]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
