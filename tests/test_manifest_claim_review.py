from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.manifest_claim_review import build_current_manifest_claim_review_inputs
from tuc import (
    MANIFEST_CLAIM_REVIEW_CONTRACT,
    MANIFEST_CLAIM_REVIEW_REPORT_SCHEMA_VERSION,
    MAX_MANIFEST_CLAIM_REVIEW_CASES,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    ManifestClaimReviewInput,
    ManifestClaimReviewReport,
    build_manifest_claim_review_report,
    dump_manifest_claim_review_report,
    manifest_claim_review_report_to_dict,
)

SCHEMA_PATH = Path("schemas/manifest_claim_review_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/backend_claim_review/manifest_claim_review_report.json")


def test_manifest_claim_review_blocks_overreaching_claims() -> None:
    report = build_manifest_claim_review_report(
        build_current_manifest_claim_review_inputs()
    )
    cases = {case.manifest_id: case for case in report.cases}

    assert report.passed
    assert cases["systolic_sim_backend"].observed_review_status == "accepted"
    assert cases["systolic_sim_backend"].issue_codes == ()
    assert cases["invalid_executable_surface_backend"].load_status == "rejected"
    assert cases["invalid_executable_surface_backend"].issue_codes == (
        "manifest_loader_rejected_claim",
    )
    assert cases["invalid_noise_without_error_budget_backend"].issue_codes == (
        "noise_model_requires_explicit_error_budget",
    )
    assert cases["invalid_overbroad_accelerator_backend"].issue_codes == (
        "non_reference_backend_claims_all_mvp_ops",
    )


def test_manifest_claim_review_reports_expected_status_mismatches() -> None:
    inputs = (
        ManifestClaimReviewInput(
            manifest_id="systolic_expected_blocked",
            path=Path("examples/manifests/systolic_sim_backend.json"),
            expected_review_status="blocked",
        ),
    )

    report = build_manifest_claim_review_report(inputs)

    assert not report.passed
    assert report.report_issues[0].manifest_id == "systolic_expected_blocked"
    assert report.report_issues[0].issue_code == (
        "manifest_claim_review_status_mismatch"
    )


def test_manifest_claim_review_report_rejects_hand_written_issues() -> None:
    mismatch_report = build_manifest_claim_review_report(
        (
            ManifestClaimReviewInput(
                manifest_id="systolic_expected_blocked",
                path=Path("examples/manifests/systolic_sim_backend.json"),
                expected_review_status="blocked",
            ),
        )
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        ManifestClaimReviewReport(cases=mismatch_report.cases, report_issues=())


def test_manifest_claim_review_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/manifest_claim_review.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["passed"] is True
    assert loaded["case_count"] == 4
    assert loaded["cases"][0]["observed_review_status"] == "accepted"
    assert loaded["cases"][1]["observed_review_status"] == "blocked"


def test_manifest_claim_review_dump_matches_golden() -> None:
    report = build_manifest_claim_review_report(
        build_current_manifest_claim_review_inputs()
    )

    assert dump_manifest_claim_review_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_manifest_claim_review_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/manifest_claim_review_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        MANIFEST_CLAIM_REVIEW_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["claim_review_contract"]["const"] == (
        MANIFEST_CLAIM_REVIEW_CONTRACT
    )
    assert schema["properties"]["case_count"]["maximum"] == (
        MAX_MANIFEST_CLAIM_REVIEW_CASES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    assert schema["$defs"]["review_status"]["enum"] == ["accepted", "blocked"]
    assert "non_reference_backend_claims_all_mvp_ops" in (
        schema["$defs"]["issue_code"]["enum"]
    )


def test_manifest_claim_review_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["review_case"]["properties"]
        assert forbidden not in schema["$defs"]["report_issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_manifest_claim_review_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == MANIFEST_CLAIM_REVIEW_REPORT_SCHEMA_VERSION
    assert golden["claim_review_contract"] == MANIFEST_CLAIM_REVIEW_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["case_count"] == len(golden["cases"]) == 4
    assert golden["passed"] is True
    assert golden["report_issues"] == []
    assert golden["cases"][0]["manifest_id"] == "systolic_sim_backend"
    assert golden["cases"][0]["issue_codes"] == []
    assert golden["cases"][-1]["issue_codes"] == [
        "non_reference_backend_claims_all_mvp_ops"
    ]


def test_manifest_claim_review_schema_is_referenced() -> None:
    schema_path = "schemas/manifest_claim_review_report.v0.schema.json"

    for path in (
        Path("docs/MANIFEST_CLAIM_REVIEW.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0094-manifest-claim-review.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def test_manifest_claim_review_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        manifest_claim_review_report_to_dict(object())  # type: ignore[arg-type]


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
