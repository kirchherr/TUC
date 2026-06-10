from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_author_readiness import build_external_vector_backend_author_readiness
from tuc import (
    BACKEND_AUTHOR_READINESS_CONTRACT,
    BACKEND_AUTHOR_READINESS_REPORT_SCHEMA_VERSION,
    BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS,
    MAX_BACKEND_AUTHOR_READINESS_CHECKS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendAuthorReadinessCheck,
    BackendAuthorReadinessError,
    BackendAuthorReadinessReport,
    assert_backend_author_readiness,
    backend_author_readiness_report_to_dict,
    build_backend_author_readiness_report,
    dump_backend_author_readiness_report,
)

SCHEMA_PATH = Path("schemas/backend_author_readiness_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/backend_author_readiness/external_vector_readiness_report.json"
)


def test_external_vector_backend_author_readiness_is_ready() -> None:
    report = build_external_vector_backend_author_readiness()

    assert report.ready
    assert report.backend_name == "external-vector"
    assert report.manifest_id == "external_vector_backend"
    assert tuple(check.check_name for check in report.checks) == (
        BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS
    )
    assert tuple(check.status for check in report.checks) == (
        "passed",
        "passed",
        "passed",
        "passed",
        "passed",
    )
    assert report.issues == ()


def test_backend_author_readiness_derives_failed_check_issues() -> None:
    checks = _checks_with_status(compiler_assignment="failed")

    report = build_backend_author_readiness_report(
        backend_name="candidate",
        manifest_id="candidate_manifest",
        checks=checks,
    )

    assert not report.ready
    assert report.issues[0].check_name == "compiler_assignment"
    assert report.issues[0].issue_code == "compiler_assignment_not_passed"


def test_backend_author_readiness_rejects_hand_written_issues() -> None:
    checks = _checks_with_status(backend_conformance="failed")
    report = build_backend_author_readiness_report(
        backend_name="candidate",
        manifest_id="candidate_manifest",
        checks=checks,
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendAuthorReadinessReport(
            backend_name=report.backend_name,
            manifest_id=report.manifest_id,
            checks=report.checks,
            issues=(),
        )


def test_backend_author_readiness_rejects_wrong_check_order() -> None:
    checks = tuple(reversed(_checks_with_status()))

    with pytest.raises(ValueError, match="required order"):
        build_backend_author_readiness_report(
            backend_name="candidate",
            manifest_id="candidate_manifest",
            checks=checks,
        )


def test_assert_backend_author_readiness_raises_on_failed_check() -> None:
    report = build_backend_author_readiness_report(
        backend_name="candidate",
        manifest_id="candidate_manifest",
        checks=_checks_with_status(manifest_registry="failed"),
    )

    with pytest.raises(BackendAuthorReadinessError, match="manifest_registry"):
        assert_backend_author_readiness(report)


def test_backend_author_readiness_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_author_readiness.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["ready"] is True
    assert loaded["check_count"] == 5
    assert loaded["checks"][0]["check_name"] == "manifest_claim_review"
    assert loaded["checks"][-1]["check_name"] == "assigned_subgraph_lowering"


def test_backend_author_readiness_dump_matches_golden() -> None:
    report = build_external_vector_backend_author_readiness()

    assert dump_backend_author_readiness_report(report) == GOLDEN_PATH.read_text(
        encoding="utf-8"
    )


def test_backend_author_readiness_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_author_readiness_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_AUTHOR_READINESS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["readiness_contract"]["const"] == (
        BACKEND_AUTHOR_READINESS_CONTRACT
    )
    assert schema["properties"]["check_count"]["const"] == (
        len(BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS)
    )
    assert len(schema["properties"]["checks"]["prefixItems"]) <= (
        MAX_BACKEND_AUTHOR_READINESS_CHECKS
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    assert [
        item["const"]
        for item in schema["properties"]["required_checks"]["prefixItems"]
    ] == list(BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS)


def test_backend_author_readiness_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["readiness_check"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_author_readiness_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == BACKEND_AUTHOR_READINESS_REPORT_SCHEMA_VERSION
    assert golden["readiness_contract"] == BACKEND_AUTHOR_READINESS_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["check_count"] == len(golden["checks"]) == 5
    assert golden["ready"] is True
    assert golden["issues"] == []
    assert golden["required_checks"] == list(BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS)


def test_backend_author_readiness_schema_is_referenced() -> None:
    schema_path = "schemas/backend_author_readiness_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_AUTHOR_READINESS.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0096-backend-author-readiness-report.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def test_backend_author_readiness_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_author_readiness_report_to_dict(object())  # type: ignore[arg-type]


def _checks_with_status(
    *,
    manifest_claim_review: str = "passed",
    manifest_registry: str = "passed",
    compiler_assignment: str = "passed",
    backend_conformance: str = "passed",
    assigned_subgraph_lowering: str = "passed",
) -> tuple[BackendAuthorReadinessCheck, ...]:
    statuses = {
        "manifest_claim_review": manifest_claim_review,
        "manifest_registry": manifest_registry,
        "compiler_assignment": compiler_assignment,
        "backend_conformance": backend_conformance,
        "assigned_subgraph_lowering": assigned_subgraph_lowering,
    }
    return tuple(
        BackendAuthorReadinessCheck(
            check_name=check_name,
            status=statuses[check_name],
            evidence_id=f"{check_name}_evidence",
            detail="test_detail",
        )
        for check_name in BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS
    )


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
