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
from examples.runtime_mixed_backend_equivalence import build_graph
from tuc import SystolicArraySimulatorBackend, VectorSimulatorBackend, compile_graph
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.layout_conversion_evidence import (
    MAX_RUNTIME_LAYOUT_CONVERSION_ISSUES,
    MAX_RUNTIME_LAYOUT_CONVERSION_RECORDS,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE,
    RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY,
    RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS,
    RUNTIME_LAYOUT_CONVERSION_STATUS,
    RuntimeLayoutConversionEvidenceError,
    RuntimeLayoutConversionEvidenceReport,
    RuntimeLayoutConversionIssue,
    RuntimeLayoutConversionRecord,
    assert_runtime_layout_conversion_evidence,
    build_runtime_layout_conversion_evidence_report,
    dump_runtime_layout_conversion_evidence_report,
)
from tuc.runtime.plan import LayoutConversionCost

SCHEMA_PATH = Path("schemas/runtime_layout_conversion_evidence_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_layout_conversion_evidence/current_report.json")


def test_runtime_layout_conversion_evidence_report_passes() -> None:
    report = build_current_runtime_layout_conversion_evidence_report()

    assert report.passed is True
    assert report.evidence_contract == RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT
    assert report.artifact_status == RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS
    assert report.conversion_scope == RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE
    assert report.execution_policy == RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY
    assert report.residency_claim_status == (
        RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
    )
    assert len(report.conversions) == 1
    assert report.total_planned_bytes == 24
    assert report.issues == ()

    record = report.conversions[0]
    assert record.conversion_id == "layout_conversion_0000"
    assert record.tensor_name == "projection"
    assert record.source_operation == "projection"
    assert record.target_operation == "normalize"
    assert record.from_backend == "systolic-sim"
    assert record.to_backend == "vector-sim"
    assert record.from_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert record.to_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert record.from_layout is LayoutKind.BLOCKED
    assert record.to_layout is LayoutKind.ROW_MAJOR
    assert record.planned_bytes == 24
    assert record.planner_reason == "layout_mismatch"
    assert record.source_value_record_id == "projection:projection"
    assert record.consumer_input_id == "normalize:projection"
    assert record.conversion_status == RUNTIME_LAYOUT_CONVERSION_STATUS
    assert assert_runtime_layout_conversion_evidence(report) is report


def test_runtime_layout_conversion_evidence_dump_matches_golden() -> None:
    report = build_current_runtime_layout_conversion_evidence_report()

    assert dump_runtime_layout_conversion_evidence_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_layout_conversion_evidence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_layout_conversion_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert "runtime_layout_conversion_evidence.data_only.v0" in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_layout_conversion_evidence_rejects_stale_plan_bytes() -> None:
    graph = build_graph()
    compiled = compile_graph(
        graph,
        (
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ),
    )
    bad_conversion = LayoutConversionCost(
        tensor_name="projection",
        source_operation="projection",
        target_operation="normalize",
        source_layout=LayoutKind.BLOCKED,
        target_layout=LayoutKind.ROW_MAJOR,
        bytes_converted=8,
        reason="layout_mismatch",
    )
    bad_plan = replace(compiled.partition_plan, layout_conversions=(bad_conversion,))

    with pytest.raises(ValueError, match="byte count mismatch"):
        build_runtime_layout_conversion_evidence_report(compiled.hac_ir.graph, bad_plan)


def test_runtime_layout_conversion_evidence_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution"):
        RuntimeLayoutConversionRecord(
            conversion_id="runtime_handle",
            tensor_name="projection",
            source_operation="projection",
            target_operation="normalize",
            from_backend="systolic-sim",
            to_backend="vector-sim",
            from_memory_domain=MemoryDomainKind.DEVICE_SRAM,
            to_memory_domain=MemoryDomainKind.DEVICE_SRAM,
            from_layout=LayoutKind.BLOCKED,
            to_layout=LayoutKind.ROW_MAJOR,
            planned_bytes=24,
            planner_reason="layout_mismatch",
            source_value_record_id="projection:projection",
            consumer_input_id="normalize:projection",
        )


def test_runtime_layout_conversion_evidence_requires_derived_issues() -> None:
    report = build_current_runtime_layout_conversion_evidence_report()
    duplicate = replace(report.conversions[0], consumer_input_id="normalize:duplicate")

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeLayoutConversionEvidenceReport(
            graph_name=report.graph_name,
            source_partition_plan_digest=report.source_partition_plan_digest,
            conversions=(report.conversions[0], duplicate),
            issues=(),
        )


def test_assert_runtime_layout_conversion_evidence_raises_on_issues() -> None:
    report = build_current_runtime_layout_conversion_evidence_report()
    duplicate = replace(report.conversions[0], consumer_input_id="normalize:duplicate")
    failed = RuntimeLayoutConversionEvidenceReport(
        graph_name=report.graph_name,
        source_partition_plan_digest=report.source_partition_plan_digest,
        conversions=(report.conversions[0], duplicate),
        issues=(
            RuntimeLayoutConversionIssue(
                subject="layout_conversion_0000",
                issue_code="duplicate_conversion_id",
            ),
        ),
    )

    with pytest.raises(RuntimeLayoutConversionEvidenceError):
        assert_runtime_layout_conversion_evidence(failed)


def test_runtime_layout_conversion_evidence_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_layout_conversion_evidence_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS
    )
    assert schema["properties"]["conversion_scope"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE
    )
    assert schema["properties"]["execution_policy"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY
    )
    assert schema["properties"]["residency_claim_status"]["const"] == (
        RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
    )
    assert schema["properties"]["conversions"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_RECORDS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_LAYOUT_CONVERSION_ISSUES
    )


def test_runtime_layout_conversion_evidence_schema_fails_closed() -> None:
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
        "pointer",
        "runtime_handle",
        "allocation_handle",
        "subprocess",
        "raw_tensor_value",
        "raw_benchmark_output",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["conversion"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_layout_conversion_evidence_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_LAYOUT_CONVERSION_EVIDENCE_REPORT_SCHEMA_VERSION
    )
    assert golden["evidence_contract"] == RUNTIME_LAYOUT_CONVERSION_EVIDENCE_CONTRACT
    assert golden["artifact_status"] == RUNTIME_LAYOUT_CONVERSION_EVIDENCE_ARTIFACT_STATUS
    assert golden["conversion_scope"] == RUNTIME_LAYOUT_CONVERSION_EVIDENCE_SCOPE
    assert golden["execution_policy"] == RUNTIME_LAYOUT_CONVERSION_EXECUTION_POLICY
    assert golden["residency_claim_status"] == (
        RUNTIME_LAYOUT_CONVERSION_RESIDENCY_CLAIM_STATUS
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["conversion_count"] == len(golden["conversions"]) == 1
    assert golden["total_planned_bytes"] == 24


def test_runtime_layout_conversion_evidence_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_layout_conversion_evidence_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_LAYOUT_CONVERSION_EVIDENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0212-runtime-layout-conversion-evidence.md"),
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

