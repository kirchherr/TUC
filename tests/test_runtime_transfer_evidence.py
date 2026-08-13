from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_backend_equivalence import build_graph
from examples.runtime_transfer_evidence import (
    build_current_runtime_transfer_evidence_report,
)
from tuc import SystolicArraySimulatorBackend, compile_graph
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.plan import RuntimeTransferEdge
from tuc.runtime.transfer_evidence import (
    MAX_RUNTIME_TRANSFER_EVIDENCE_ISSUES,
    MAX_RUNTIME_TRANSFER_EVIDENCE_RECORDS,
    RUNTIME_TRANSFER_COST_CLAIM_STATUS,
    RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS,
    RUNTIME_TRANSFER_EVIDENCE_CONTRACT,
    RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION,
    RUNTIME_TRANSFER_EVIDENCE_SCOPE,
    RUNTIME_TRANSFER_EXECUTION_POLICY,
    RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS,
    RUNTIME_TRANSFER_STATUS,
    RuntimeTransferEvidenceError,
    RuntimeTransferEvidenceIssue,
    RuntimeTransferEvidenceRecord,
    RuntimeTransferEvidenceReport,
    assert_runtime_transfer_evidence,
    build_runtime_transfer_evidence_report,
    dump_runtime_transfer_evidence_report,
)

SCHEMA_PATH = Path("schemas/runtime_transfer_evidence_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_transfer_evidence/current_report.json")


def test_runtime_transfer_evidence_report_passes() -> None:
    report = build_current_runtime_transfer_evidence_report()

    assert report.passed is True
    assert report.evidence_contract == RUNTIME_TRANSFER_EVIDENCE_CONTRACT
    assert report.artifact_status == RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS
    assert report.transfer_scope == RUNTIME_TRANSFER_EVIDENCE_SCOPE
    assert report.execution_policy == RUNTIME_TRANSFER_EXECUTION_POLICY
    assert report.residency_claim_status == RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS
    assert report.cost_claim_status == RUNTIME_TRANSFER_COST_CLAIM_STATUS
    assert len(report.transfers) == 1
    assert report.total_planned_bytes == 16
    assert report.total_estimated_latency_ns == 20001.0
    assert report.total_estimated_energy_pj == 1600.0
    assert report.issues == ()

    record = report.transfers[0]
    assert record.transfer_id == "runtime_transfer_0000"
    assert record.tensor_name == "projection"
    assert record.source_operation == "projection"
    assert record.target_operation == "activation"
    assert record.from_backend == "systolic-sim"
    assert record.to_backend == "reference-cpu"
    assert record.from_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert record.to_memory_domain is MemoryDomainKind.HOST_RAM
    assert record.from_layout is LayoutKind.BLOCKED
    assert record.to_layout is LayoutKind.ROW_MAJOR
    assert record.planned_bytes == 16
    assert record.cost_model == "prototype_transfer_cost_profile"
    assert record.source_value_record_id == "projection:projection"
    assert record.consumer_input_id == "activation:projection"
    assert record.transfer_status == RUNTIME_TRANSFER_STATUS
    assert assert_runtime_transfer_evidence(report) is report


def test_runtime_transfer_evidence_dump_matches_golden() -> None:
    report = build_current_runtime_transfer_evidence_report()

    assert dump_runtime_transfer_evidence_report(report) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_runtime_transfer_evidence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_transfer_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "runtime_transfer_evidence.data_only.v0" in completed.stdout
    assert "planning_estimate_not_measurement" in completed.stdout
    assert "device_sram" in completed.stdout
    assert "host_ram" in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_transfer_evidence_rejects_stale_plan_bytes() -> None:
    graph = build_graph()
    compiled = compile_graph(graph, (SystolicArraySimulatorBackend().capability,))
    edge = compiled.partition_plan.transfer_edges[0]
    bad_edge = RuntimeTransferEdge(
        tensor_name=edge.tensor_name,
        source_operation=edge.source_operation,
        target_operation=edge.target_operation,
        source_backend=edge.source_backend,
        target_backend=edge.target_backend,
        source_domain=edge.source_domain,
        target_domain=edge.target_domain,
        source_layout=edge.source_layout,
        target_layout=edge.target_layout,
        bytes_moved=8,
    )
    bad_plan = replace(compiled.partition_plan, transfer_edges=(bad_edge,))

    with pytest.raises(ValueError, match="byte count mismatch"):
        build_runtime_transfer_evidence_report(compiled.hac_ir.graph, bad_plan)


def test_runtime_transfer_evidence_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution"):
        RuntimeTransferEvidenceRecord(
            transfer_id="runtime_handle",
            tensor_name="projection",
            source_operation="projection",
            target_operation="activation",
            from_backend="systolic-sim",
            to_backend="reference-cpu",
            from_memory_domain=MemoryDomainKind.DEVICE_SRAM,
            to_memory_domain=MemoryDomainKind.HOST_RAM,
            from_layout=LayoutKind.BLOCKED,
            to_layout=LayoutKind.ROW_MAJOR,
            planned_bytes=16,
            estimated_latency_ns=20001.0,
            estimated_energy_pj=1600.0,
            cost_model="prototype_transfer_cost_profile",
            source_value_record_id="projection:projection",
            consumer_input_id="activation:projection",
        )


def test_runtime_transfer_evidence_requires_derived_issues() -> None:
    report = build_current_runtime_transfer_evidence_report()
    duplicate = replace(report.transfers[0], consumer_input_id="activation:duplicate")

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeTransferEvidenceReport(
            graph_name=report.graph_name,
            source_partition_plan_digest=report.source_partition_plan_digest,
            transfers=(report.transfers[0], duplicate),
            issues=(),
        )


def test_assert_runtime_transfer_evidence_raises_on_issues() -> None:
    report = build_current_runtime_transfer_evidence_report()
    duplicate = replace(report.transfers[0], consumer_input_id="activation:duplicate")
    failed = RuntimeTransferEvidenceReport(
        graph_name=report.graph_name,
        source_partition_plan_digest=report.source_partition_plan_digest,
        transfers=(report.transfers[0], duplicate),
        issues=(
            RuntimeTransferEvidenceIssue(
                subject="runtime_transfer_0000",
                issue_code="duplicate_transfer_id",
            ),
        ),
    )

    with pytest.raises(RuntimeTransferEvidenceError):
        assert_runtime_transfer_evidence(failed)


def test_runtime_transfer_evidence_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/runtime_transfer_evidence_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_TRANSFER_EVIDENCE_CONTRACT
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS
    )
    assert schema["properties"]["transfer_scope"]["const"] == (RUNTIME_TRANSFER_EVIDENCE_SCOPE)
    assert schema["properties"]["execution_policy"]["const"] == (RUNTIME_TRANSFER_EXECUTION_POLICY)
    assert schema["properties"]["residency_claim_status"]["const"] == (
        RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS
    )
    assert schema["properties"]["cost_claim_status"]["const"] == (
        RUNTIME_TRANSFER_COST_CLAIM_STATUS
    )
    assert schema["properties"]["transfers"]["maxItems"] == (MAX_RUNTIME_TRANSFER_EVIDENCE_RECORDS)
    assert schema["properties"]["issues"]["maxItems"] == (MAX_RUNTIME_TRANSFER_EVIDENCE_ISSUES)


def test_runtime_transfer_evidence_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["transfer"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_transfer_evidence_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_TRANSFER_EVIDENCE_REPORT_SCHEMA_VERSION
    assert golden["evidence_contract"] == RUNTIME_TRANSFER_EVIDENCE_CONTRACT
    assert golden["artifact_status"] == RUNTIME_TRANSFER_EVIDENCE_ARTIFACT_STATUS
    assert golden["transfer_scope"] == RUNTIME_TRANSFER_EVIDENCE_SCOPE
    assert golden["execution_policy"] == RUNTIME_TRANSFER_EXECUTION_POLICY
    assert golden["residency_claim_status"] == RUNTIME_TRANSFER_RESIDENCY_CLAIM_STATUS
    assert golden["cost_claim_status"] == RUNTIME_TRANSFER_COST_CLAIM_STATUS
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["transfer_count"] == len(golden["transfers"]) == 1
    assert golden["total_planned_bytes"] == 16


def test_runtime_transfer_evidence_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_transfer_evidence_report.v0.schema.json"
    example_path = "examples/runtime_transfer_evidence.py"

    assert example_path in Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/RUNTIME_TRANSFER_EVIDENCE.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text


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
