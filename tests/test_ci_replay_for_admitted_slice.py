from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.ci_replay_for_admitted_slice import (
    CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID,
    CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION,
    CI_REPLAY_FOR_ADMITTED_SLICE_WORKFLOW_REPLAY_STEP,
    CIReplayForAdmittedSliceReportError,
    assert_ci_replay_for_admitted_slice_report_contract,
    build_ci_replay_for_admitted_slice_report,
    build_report,
)
from tuc.frontend.admitted_slice_ci_replay import (
    CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT,
    CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS,
    CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS,
    CI_REPLAY_FOR_ADMITTED_SLICE_STATUS,
    CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE,
)

SCHEMA_PATH = Path("schemas/ci_replay_for_admitted_slice_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/frontend/ci_replay_for_admitted_slice_report.json")
DOC_PATH = Path("docs/CI_REPLAY_FOR_ADMITTED_SLICE.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_ci_replay_for_admitted_slice_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_ci_replay_for_admitted_slice_passes() -> None:
    report = _cached_report()

    assert_ci_replay_for_admitted_slice_report_contract(report)
    assert report["schema_version"] == CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION
    assert report["evidence_id"] == CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID
    assert report["contract"] == CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT
    assert report["status"] == CI_REPLAY_FOR_ADMITTED_SLICE_STATUS
    assert report["target_slice"] == CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE
    assert report["all_replayed"] is True
    assert report["replayed_evidence_count"] == len(
        CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS
    )
    assert [item["evidence_id"] for item in report["replayed_evidence"]] == list(
        CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS
    )
    assert report["ci_workflow_permissions"] == "contents_read"
    assert report["ci_checkout_credentials"] == "persist_credentials_false"
    assert report["ci_replay_step_bound"] is True
    assert report["direct_source_ingestion"] is False
    assert report["source_ingestion_admission_ready"] is False
    assert report["source_to_compute_graph"] is False
    assert report["source_to_hac_ir"] is False
    assert report["source_to_runtime_plan"] is False
    assert report["maintainer_security_review_required"] is True
    assert report["remaining_external_evidence"] == [
        "maintainer_security_review_approval"
    ]
    assert report["issues"] == []


def test_ci_replay_for_admitted_slice_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_ci_replay_for_admitted_slice_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/ci_replay_for_admitted_slice.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert "ci_replay_for_admitted_slice" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_text" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_ci_replay_for_admitted_slice_is_bound_in_workflow() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read\n" in workflow
    assert "persist-credentials: false" in workflow
    assert CI_REPLAY_FOR_ADMITTED_SLICE_WORKFLOW_REPLAY_STEP in workflow


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("status", "WARN", "status"),
        ("all_replayed", False, "all_replayed"),
        ("ci_replay_step_bound", False, "ci_replay_step_bound"),
        ("source_to_compute_graph", True, "source_to_compute_graph"),
        ("remaining_external_evidence_count", 0, "remaining_external_evidence_count"),
        ("issues", ["unexpected"], "issues"),
    ),
)
def test_ci_replay_for_admitted_slice_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_report())
    report[field] = value

    with pytest.raises(CIReplayForAdmittedSliceReportError, match=match):
        assert_ci_replay_for_admitted_slice_report_contract(report)


def test_ci_replay_for_admitted_slice_rejects_evidence_order_drift() -> None:
    report = dict(_cached_report())
    evidence = list(report["replayed_evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["replayed_evidence"] = evidence

    with pytest.raises(CIReplayForAdmittedSliceReportError, match="evidence order"):
        assert_ci_replay_for_admitted_slice_report_contract(report)


def test_ci_replay_for_admitted_slice_rejects_digest_drift() -> None:
    report = dict(_cached_report())
    report["report_digest"] = "sha256:" + "0" * 64

    with pytest.raises(CIReplayForAdmittedSliceReportError, match="digest drift"):
        assert_ci_replay_for_admitted_slice_report_contract(report)


def test_ci_replay_for_admitted_slice_rejects_source_leakage() -> None:
    report = dict(_cached_report())
    report["source_text"] = "x"

    with pytest.raises(CIReplayForAdmittedSliceReportError, match="top-level keys"):
        assert_ci_replay_for_admitted_slice_report_contract(report)


def test_ci_replay_for_admitted_slice_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_id"]["const"] == (
        CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID
    )
    assert schema["properties"]["contract"]["const"] == (
        CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT
    )
    assert schema["properties"]["status"]["const"] == CI_REPLAY_FOR_ADMITTED_SLICE_STATUS
    assert [
        item["const"] for item in schema["properties"]["required_controls"]["prefixItems"]
    ] == list(CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS)


def test_ci_replay_for_admitted_slice_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
        "command_line",
        "device_id",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
    }
    assert not (set(schema["properties"]) & forbidden_properties)


def test_ci_replay_for_admitted_slice_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION
    assert golden["evidence_id"] == CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID
    assert golden["status"] == CI_REPLAY_FOR_ADMITTED_SLICE_STATUS
    assert golden["all_replayed"] is True


def test_ci_replay_for_admitted_slice_is_documented() -> None:
    schema_path = "schemas/ci_replay_for_admitted_slice_report.v0.schema.json"
    example_path = "examples/ci_replay_for_admitted_slice.py"
    golden_path = "tests/golden/frontend/ci_replay_for_admitted_slice_report.json"
    module_path = "src/tuc/frontend/admitted_slice_ci_replay.py"
    doc_path = "docs/CI_REPLAY_FOR_ADMITTED_SLICE.md"
    rfc_path = "rfcs/0264-ci-replay-for-admitted-slice.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/ADMITTING_SOURCE_INGESTION_RFC.md"),
        Path("docs/REAL_TRITON_FIRST_SLICE_PLAN.md"),
        DOC_PATH,
        Path(rfc_path),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text
        if path != Path(".github/workflows/ci.yml"):
            assert schema_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert golden_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert module_path in text or path.name in {"README.md", "ROADMAP.md"}
            assert doc_path in text or path == DOC_PATH
            assert rfc_path in text or path.name in {"README.md", "ROADMAP.md"}


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
