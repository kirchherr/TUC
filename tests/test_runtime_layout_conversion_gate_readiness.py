from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_layout_conversion_digest_binding import (
    build_current_runtime_layout_conversion_digest_binding_report,
)
from examples.runtime_layout_conversion_evidence import (
    build_current_runtime_layout_conversion_evidence_report,
)
from examples.runtime_layout_conversion_gate_readiness import (
    build_current_runtime_layout_conversion_gate_readiness_report,
)
from tuc import (
    RuntimeEvidenceArtifact,
    build_current_runtime_evidence_matrix_report,
    build_runtime_evidence_matrix_report,
)
from tuc.runtime.layout_conversion_digest_binding import (
    RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID,
)
from tuc.runtime.layout_conversion_gate_readiness import (
    MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS,
    MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ISSUES,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_STATUSES,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS,
    RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID,
    RuntimeLayoutConversionGateReadinessCheck,
    RuntimeLayoutConversionGateReadinessError,
    assert_runtime_layout_conversion_gate_readiness,
    build_runtime_layout_conversion_gate_readiness_report,
    dump_runtime_layout_conversion_gate_readiness_report,
)

SCHEMA_PATH = Path(
    "schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/runtime_layout_conversion_gate_readiness/current_report.json"
)


def test_runtime_layout_conversion_gate_readiness_is_ready() -> None:
    report = build_current_runtime_layout_conversion_gate_readiness_report()

    assert report.ready is True
    assert report.readiness_status == "ready"
    assert report.readiness_contract == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT
    )
    assert report.artifact_status == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS
    )
    assert report.target_artifact_kind == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
    )
    assert report.target_artifact_id == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
    )
    assert report.target_graph_id == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID
    )
    assert report.target_gate_status == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GATE_STATUS
    )
    assert report.source_graph_name == "runtime_mixed_backend_equivalence"
    assert report.source_conversion_count == 1
    assert report.source_evidence_issue_count == 0
    assert tuple(check.check_name for check in report.checks) == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS
    )
    assert tuple(check.status for check in report.checks) == (
        "passed",
        "passed",
        "passed",
        "passed",
        "passed",
        "passed",
        "passed",
    )
    assert report.checks[4].evidence_id == (
        "runtime_layout_conversion_evidence_reduction_slice"
    )
    assert report.checks[5].evidence_id == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_ID
    )
    assert report.checks[6].evidence_id == (
        RUNTIME_LAYOUT_CONVERSION_DIGEST_BINDING_ARTIFACT_ID
    )
    assert report.issues == ()
    assert assert_runtime_layout_conversion_gate_readiness(report) is report


def test_runtime_layout_conversion_gate_readiness_dump_matches_golden() -> None:
    report = build_current_runtime_layout_conversion_gate_readiness_report()

    assert dump_runtime_layout_conversion_gate_readiness_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_layout_conversion_gate_readiness_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_layout_conversion_gate_readiness.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "runtime_layout_conversion_gate_readiness.data_only.v0" in (
        completed.stdout
    )
    assert '"readiness_status": "ready"' in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_layout_conversion_gate_readiness_rejects_forged_issues() -> None:
    source = build_current_runtime_layout_conversion_evidence_report()
    report = build_current_runtime_layout_conversion_gate_readiness_report()
    failed_checks = (
        *report.checks[:6],
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="hs_ir_and_tensor_store_digest_binding",
            status="blocked",
            evidence_id="missing_hs_ir_tensor_store_digest_binding",
            detail="digest_binding_deferred",
        ),
    )
    failed = build_runtime_layout_conversion_gate_readiness_report(
        source,
        failed_checks,
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        replace(failed, issues=())


def test_runtime_layout_conversion_gate_readiness_rejects_wrong_check_order() -> None:
    source = build_current_runtime_layout_conversion_evidence_report()
    current = build_current_runtime_layout_conversion_gate_readiness_report()
    checks = tuple(reversed(current.checks))

    with pytest.raises(ValueError, match="checks are out of order"):
        build_runtime_layout_conversion_gate_readiness_report(source, checks)


def test_runtime_layout_conversion_gate_readiness_blocks_wrong_matrix_artifact() -> None:
    matrix = build_current_runtime_evidence_matrix_report()
    forged = build_runtime_evidence_matrix_report(
        "runtime_layout_conversion_gate_readiness_wrong_artifact",
        tuple(
            replace(
                graph,
                artifacts=tuple(
                    RuntimeEvidenceArtifact(
                        artifact_kind=artifact.artifact_kind,
                        artifact_id="runtime_layout_conversion_evidence_other",
                    )
                    if artifact.artifact_kind
                    == RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_ARTIFACT_KIND
                    else artifact
                    for artifact in graph.artifacts
                ),
            )
            if graph.graph_id
            == RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_TARGET_GRAPH_ID
            else graph
            for graph in matrix.graphs
        ),
    )

    report = build_current_runtime_layout_conversion_gate_readiness_report(
        matrix_report=forged,
    )

    exact_binding = {
        check.check_name: check for check in report.checks
    }["gate_exact_artifact_binding"]
    assert exact_binding.status == "blocked"
    assert exact_binding.evidence_id == "missing_runtime_evidence_gate_binding"
    assert "gate_exact_artifact_binding" in {
        issue.subject for issue in report.issues
    }

def test_runtime_layout_conversion_gate_readiness_blocks_forged_digest_binding() -> None:
    forged = replace(
        build_current_runtime_layout_conversion_digest_binding_report(),
        source_layout_conversion_metadata_digest=(
            "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        ),
    )

    report = build_current_runtime_layout_conversion_gate_readiness_report(
        digest_binding_report=forged,
    )

    digest_binding = {
        check.check_name: check for check in report.checks
    }["hs_ir_and_tensor_store_digest_binding"]
    assert digest_binding.status == "blocked"
    assert digest_binding.evidence_id == "missing_hs_ir_tensor_store_digest_binding"
    assert "hs_ir_and_tensor_store_digest_binding" in {
        issue.subject for issue in report.issues
    }
    with pytest.raises(RuntimeLayoutConversionGateReadinessError):
        assert_runtime_layout_conversion_gate_readiness(report)


def test_runtime_layout_conversion_gate_readiness_rejects_forbidden_text() -> None:
    with pytest.raises(ValueError, match="forbidden execution"):
        RuntimeLayoutConversionGateReadinessCheck(
            check_name="layout_conversion_evidence_report_passes",
            status="passed",
            evidence_id="runtime_handle",
            detail="source_report_passed",
        )


def test_runtime_layout_conversion_gate_readiness_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS
    )
    assert schema["properties"]["readiness_contract"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT
    )
    assert schema["properties"]["checks"]["minItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS
    )
    assert schema["properties"]["checks"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ISSUES
    )
    assert schema["$defs"]["check"]["properties"]["check_name"]["enum"] == list(
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REQUIRED_CHECKS
    )
    assert schema["$defs"]["check"]["properties"]["status"]["enum"] == list(
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_STATUSES
    )


def test_runtime_layout_conversion_gate_readiness_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
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
        assert forbidden not in schema["$defs"]["check"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_layout_conversion_gate_readiness_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_REPORT_SCHEMA_VERSION
    )
    assert golden["readiness_contract"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CONTRACT
    )
    assert golden["artifact_status"] == (
        RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_ARTIFACT_STATUS
    )
    assert golden["ready"] is True
    assert golden["readiness_status"] == "ready"
    assert golden["source_conversion_count"] == 1
    assert golden["source_evidence_issue_count"] == 0
    assert len(golden["checks"]) == MAX_RUNTIME_LAYOUT_CONVERSION_GATE_READINESS_CHECKS
    assert len(golden["issues"]) == 0


def test_runtime_layout_conversion_gate_readiness_schema_is_referenced() -> None:
    schema_path = (
        "schemas/runtime_layout_conversion_gate_readiness_report.v0.schema.json"
    )

    for path in (
        Path("docs/RUNTIME_LAYOUT_CONVERSION_GATE_READINESS.md"),
        Path("docs/RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0213-runtime-layout-conversion-gate-readiness.md"),
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
