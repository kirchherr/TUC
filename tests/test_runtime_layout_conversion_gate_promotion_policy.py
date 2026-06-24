from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_layout_conversion_evidence import (
    build_current_runtime_layout_conversion_evidence_report,
)
from examples.runtime_layout_conversion_gate_promotion_policy import (
    build_current_runtime_layout_conversion_gate_promotion_policy_report,
)
from examples.runtime_layout_conversion_gate_readiness import (
    build_current_runtime_layout_conversion_gate_readiness_report,
)
from tuc import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.layout_conversion_digest_binding import (
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID,
)
from tuc.runtime.layout_conversion_gate_promotion_policy import (
    MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ISSUES,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_NEXT_ACTION,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REQUIRED_GATE_CHANGE,
    RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE,
    RuntimeLayoutConversionGatePromotionPolicyError,
    RuntimeLayoutConversionGatePromotionPolicyIssue,
    assert_runtime_layout_conversion_gate_promotion_policy,
    build_runtime_layout_conversion_gate_promotion_policy_report,
    dump_runtime_layout_conversion_gate_promotion_policy_report,
)
from tuc.runtime.layout_conversion_gate_readiness import (
    RuntimeLayoutConversionGateReadinessCheck,
    build_runtime_layout_conversion_gate_readiness_report,
)

SCHEMA_PATH = Path(
    "schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/runtime_layout_conversion_gate_promotion_policy/current_report.json"
)


def test_runtime_layout_conversion_gate_promotion_policy_passes() -> None:
    report = build_current_runtime_layout_conversion_gate_promotion_policy_report()

    assert report.policy_complete is True
    assert report.promotion_ready is True
    assert report.policy_contract == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT
    )
    assert report.policy_id == RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID
    assert report.policy_status == RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS
    assert report.artifact_status == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS
    )
    assert report.promotion_scope == RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE
    assert report.enforcement_status == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS
    )
    assert report.required_gate_change == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_REQUIRED_GATE_CHANGE
    )
    assert report.next_action == RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_NEXT_ACTION
    assert report.target_graph_id == "runtime_mixed_backend_equivalence"
    assert report.target_artifact_kind == "runtime_layout_conversion_evidence"
    assert report.target_artifact_id == "runtime_layout_conversion_evidence_mixed"
    assert report.source_readiness_ready is True
    assert report.source_readiness_status == "ready"
    assert report.source_readiness_target_gate_status == (
        "optional_matrix_inventory_not_gate_required"
    )
    assert report.source_digest_binding_artifact_id == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
    )
    assert report.issues == ()
    assert assert_runtime_layout_conversion_gate_promotion_policy(report) is report


def test_runtime_layout_conversion_gate_promotion_policy_dump_matches_golden() -> None:
    report = build_current_runtime_layout_conversion_gate_promotion_policy_report()

    assert dump_runtime_layout_conversion_gate_promotion_policy_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_layout_conversion_gate_promotion_policy_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_layout_conversion_gate_promotion_policy.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "runtime_layout_conversion_gate_promotion_policy.data_only.v0" in (
        completed.stdout
    )
    assert '"promotion_ready": true' in completed.stdout
    assert '"enforcement_status": "not_enforced"' in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_layout_conversion_gate_promotion_policy_blocks_not_ready() -> None:
    source = build_current_runtime_layout_conversion_evidence_report()
    readiness = build_current_runtime_layout_conversion_gate_readiness_report()
    failed_checks = (
        *readiness.checks[:6],
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="hs_ir_and_tensor_store_digest_binding",
            status="blocked",
            evidence_id="missing_hs_ir_tensor_store_digest_binding",
            detail="digest_binding_deferred",
        ),
    )
    failed_readiness = build_runtime_layout_conversion_gate_readiness_report(
        source,
        failed_checks,
    )

    report = build_runtime_layout_conversion_gate_promotion_policy_report(
        failed_readiness
    )

    assert report.policy_complete is False
    assert ("source_readiness", "readiness_not_ready") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }
    with pytest.raises(RuntimeLayoutConversionGatePromotionPolicyError):
        assert_runtime_layout_conversion_gate_promotion_policy(report)


def test_runtime_layout_conversion_gate_promotion_policy_blocks_wrong_binding_id() -> None:
    readiness = build_current_runtime_layout_conversion_gate_readiness_report()
    forged_checks = (
        *readiness.checks[:6],
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="hs_ir_and_tensor_store_digest_binding",
            status="passed",
            evidence_id="runtime_layout_conversion_digest_binding_other",
            detail="exact_digest_binding_verified",
        ),
    )
    forged_readiness = build_runtime_layout_conversion_gate_readiness_report(
        build_current_runtime_layout_conversion_evidence_report(),
        forged_checks,
    )

    report = build_runtime_layout_conversion_gate_promotion_policy_report(
        forged_readiness
    )

    assert report.policy_complete is False
    assert ("source_digest_binding", "digest_binding_artifact_mismatch") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }


def test_runtime_layout_conversion_gate_promotion_policy_rejects_forged_issues() -> None:
    readiness = build_current_runtime_layout_conversion_gate_readiness_report()
    forged_checks = (
        *readiness.checks[:6],
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="hs_ir_and_tensor_store_digest_binding",
            status="passed",
            evidence_id="runtime_layout_conversion_digest_binding_other",
            detail="exact_digest_binding_verified",
        ),
    )
    forged_readiness = build_runtime_layout_conversion_gate_readiness_report(
        build_current_runtime_layout_conversion_evidence_report(),
        forged_checks,
    )
    report = build_runtime_layout_conversion_gate_promotion_policy_report(
        forged_readiness
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        replace(report, issues=())


def test_runtime_layout_conversion_gate_promotion_policy_rejects_forbidden_text() -> None:
    with pytest.raises(ValueError, match="forbidden execution"):
        RuntimeLayoutConversionGatePromotionPolicyIssue(
            subject="runtime_handle",
            issue_code="readiness_not_ready",
        )


def test_runtime_layout_conversion_gate_promotion_policy_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ARTIFACT_STATUS
    )
    assert schema["properties"]["policy_id"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID
    )
    assert schema["properties"]["policy_contract"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT
    )
    assert schema["properties"]["policy_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_STATUS
    )
    assert schema["properties"]["promotion_scope"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_SCOPE
    )
    assert schema["properties"]["enforcement_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_layout_conversion_gate_promotion_policy_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "device_pointer",
        "memory_address",
        "runtime_handle",
        "allocation_handle",
        "subprocess",
        "raw_tensor_value",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_layout_conversion_gate_promotion_policy_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_REPORT_SCHEMA_VERSION
    )
    assert golden["policy_id"] == RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_ID
    assert golden["policy_contract"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY_CONTRACT
    )
    assert golden["policy_complete"] is True
    assert golden["promotion_ready"] is True
    assert golden["enforcement_status"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_ENFORCEMENT_STATUS
    )
    assert golden["issues"] == []


def test_runtime_layout_conversion_gate_promotion_policy_schema_is_referenced() -> None:
    schema_path = (
        "schemas/runtime_layout_conversion_gate_promotion_policy_report.v0.schema.json"
    )

    for path in (
        Path("docs/RUNTIME_LAYOUT_CONVERSION_GATE_PROMOTION_POLICY.md"),
        Path("docs/RUNTIME_LAYOUT_CONVERSION_GATE_READINESS.md"),
        Path("docs/RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0215-runtime-layout-conversion-gate-promotion-policy.md"),
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
