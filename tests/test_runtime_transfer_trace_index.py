from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.proof_of_systolic_execution import build_graph, proof_inputs
from examples.runtime_transfer_trace_index import (
    build_current_runtime_transfer_trace_index_report,
)
from tuc import SystolicArraySimulatorBackend, compile_graph
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime.executor import RuntimeExecutionTrace, execute_graph
from tuc.runtime.transfer_evidence import (
    RuntimeTransferEvidenceReport,
    build_runtime_transfer_evidence_report,
)
from tuc.runtime.transfer_trace_index import (
    MAX_RUNTIME_TRANSFER_TRACE_INDEX_ISSUES,
    MAX_RUNTIME_TRANSFER_TRACE_INDEX_RECORDS,
    RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS,
    RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT,
    RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION,
    RUNTIME_TRANSFER_TRACE_INDEX_SCOPE,
    RUNTIME_TRANSFER_TRACE_INDEX_STATUS,
    RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY,
    RUNTIME_TRANSFER_TRACE_RECORD_STATUS,
    RuntimeTransferTraceIndexIssue,
    RuntimeTransferTraceIndexRecord,
    RuntimeTransferTraceIndexReport,
    assert_runtime_transfer_trace_index,
    build_runtime_transfer_trace_index_report,
    dump_runtime_transfer_trace_index_report,
)

SCHEMA_PATH = Path("schemas/runtime_transfer_trace_index_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_transfer_trace_index/current_report.json")


def test_runtime_transfer_trace_index_report_passes() -> None:
    report = build_current_runtime_transfer_trace_index_report()

    assert report.passed is True
    assert report.status == RUNTIME_TRANSFER_TRACE_INDEX_STATUS
    assert report.trace_index_contract == RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT
    assert report.trace_index_scope == RUNTIME_TRANSFER_TRACE_INDEX_SCOPE
    assert report.trace_materialization_policy == (
        RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    assert report.transfer_count == 1
    assert report.trace_step_count == 2
    assert report.total_planned_bytes == 16
    assert report.total_estimated_latency_ns == 20001.0
    assert report.total_estimated_energy_pj == 1600.0
    assert report.issues == ()

    record = report.records[0]
    assert record.transfer_id == "runtime_transfer_0000"
    assert record.tensor_name == "projection"
    assert record.producer_operation == "systolic_projection"
    assert record.consumer_operation == "host_activation"
    assert record.producer_operation_kind == "matmul"
    assert record.consumer_operation_kind == "elementwise"
    assert record.producer_step_index == 0
    assert record.consumer_step_index == 1
    assert record.producer_planned_backend == "systolic-sim"
    assert record.producer_executor_backend == "systolic-sim"
    assert record.consumer_planned_backend == "reference-cpu"
    assert record.consumer_executor_backend == "reference-cpu"
    assert record.producer_output_tensors == ("projection",)
    assert record.consumer_input_tensors == ("projection",)
    assert record.from_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert record.to_memory_domain is MemoryDomainKind.HOST_RAM
    assert record.from_layout is LayoutKind.BLOCKED
    assert record.to_layout is LayoutKind.ROW_MAJOR
    assert record.planned_bytes == 16
    assert record.cost_model == "prototype_transfer_cost_profile"
    assert record.source_value_record_id == "systolic_projection:projection"
    assert record.consumer_input_id == "host_activation:projection"
    assert record.source_transfer_status == "planned"
    assert record.trace_record_status == RUNTIME_TRANSFER_TRACE_RECORD_STATUS
    assert record.trace_alignment_status == RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS
    assert assert_runtime_transfer_trace_index(report) is report


def test_runtime_transfer_trace_index_dump_matches_golden() -> None:
    report = build_current_runtime_transfer_trace_index_report()

    assert dump_runtime_transfer_trace_index_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_transfer_trace_index_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_transfer_trace_index.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "runtime_transfer_trace_index.data_only.v0" in completed.stdout
    assert "transfer_not_materialized_as_runtime_step" in completed.stdout
    assert "planning_estimate_not_measurement" in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "memory_address" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout


def test_runtime_transfer_trace_index_rejects_trace_graph_drift() -> None:
    evidence, trace = _current_evidence_and_trace()
    bad_trace = RuntimeExecutionTrace(
        graph_name="other_graph",
        executor_contract=trace.executor_contract,
        steps=trace.steps,
    )

    with pytest.raises(ValueError, match="graph mismatch"):
        build_runtime_transfer_trace_index_report(evidence, bad_trace)


def test_runtime_transfer_trace_index_rejects_backend_drift() -> None:
    evidence, trace = _current_evidence_and_trace()
    bad_step = replace(trace.steps[0], planned_backend="reference-cpu")
    bad_trace = replace(trace, steps=(bad_step, *trace.steps[1:]))

    with pytest.raises(ValueError, match="producer backend mismatch"):
        build_runtime_transfer_trace_index_report(evidence, bad_trace)


def test_runtime_transfer_trace_index_rejects_trace_order_drift() -> None:
    evidence, trace = _current_evidence_and_trace()
    bad_trace = replace(trace, steps=(trace.steps[1], trace.steps[0]))

    with pytest.raises(ValueError, match="producer step must precede"):
        build_runtime_transfer_trace_index_report(evidence, bad_trace)


def test_runtime_transfer_trace_index_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution"):
        RuntimeTransferTraceIndexRecord(
            transfer_id="runtime_handle",
            tensor_name="projection",
            producer_operation="systolic_projection",
            consumer_operation="host_activation",
            producer_operation_kind="matmul",
            consumer_operation_kind="elementwise",
            producer_step_index=0,
            consumer_step_index=1,
            producer_planned_backend="systolic-sim",
            producer_executor_backend="systolic-sim",
            consumer_planned_backend="reference-cpu",
            consumer_executor_backend="reference-cpu",
            producer_output_tensors=("projection",),
            consumer_input_tensors=("projection",),
            from_memory_domain=MemoryDomainKind.DEVICE_SRAM,
            to_memory_domain=MemoryDomainKind.HOST_RAM,
            from_layout=LayoutKind.BLOCKED,
            to_layout=LayoutKind.ROW_MAJOR,
            planned_bytes=16,
            estimated_latency_ns=20001.0,
            estimated_energy_pj=1600.0,
            cost_model="prototype_transfer_cost_profile",
            source_value_record_id="systolic_projection:projection",
            consumer_input_id="host_activation:projection",
        )


def test_runtime_transfer_trace_index_requires_derived_issues() -> None:
    report = build_current_runtime_transfer_trace_index_report()
    duplicate = replace(report.records[0], consumer_input_id="host_activation:duplicate")

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeTransferTraceIndexReport(
            graph_name=report.graph_name,
            source_partition_plan_digest=report.source_partition_plan_digest,
            source_transfer_evidence_digest=report.source_transfer_evidence_digest,
            execution_trace_digest=report.execution_trace_digest,
            trace_step_count=report.trace_step_count,
            records=(report.records[0], duplicate),
            issues=(),
        )


def test_assert_runtime_transfer_trace_index_raises_on_issues() -> None:
    report = build_current_runtime_transfer_trace_index_report()
    duplicate = replace(report.records[0], consumer_input_id="host_activation:duplicate")
    failed = RuntimeTransferTraceIndexReport(
        graph_name=report.graph_name,
        source_partition_plan_digest=report.source_partition_plan_digest,
        source_transfer_evidence_digest=report.source_transfer_evidence_digest,
        execution_trace_digest=report.execution_trace_digest,
        trace_step_count=report.trace_step_count,
        records=(report.records[0], duplicate),
        issues=(
            RuntimeTransferTraceIndexIssue(
                subject="runtime_transfer_0000",
                issue_code="duplicate_transfer_id",
            ),
        ),
    )

    with pytest.raises(AssertionError):
        assert_runtime_transfer_trace_index(failed)


def test_runtime_transfer_trace_index_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["trace_index_contract"]["const"] == (
        RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT
    )
    assert schema["properties"]["trace_index_scope"]["const"] == (
        RUNTIME_TRANSFER_TRACE_INDEX_SCOPE
    )
    assert schema["properties"]["trace_materialization_policy"]["const"] == (
        RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    assert schema["properties"]["status"]["const"] == (
        RUNTIME_TRANSFER_TRACE_INDEX_STATUS
    )
    assert schema["properties"]["records"]["maxItems"] == (
        MAX_RUNTIME_TRANSFER_TRACE_INDEX_RECORDS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_TRANSFER_TRACE_INDEX_ISSUES
    )
    assert schema["$defs"]["record"]["properties"]["trace_record_status"]["const"] == (
        RUNTIME_TRANSFER_TRACE_RECORD_STATUS
    )
    assert schema["$defs"]["record"]["properties"]["trace_alignment_status"][
        "const"
    ] == RUNTIME_TRANSFER_TRACE_ALIGNMENT_STATUS


def test_runtime_transfer_trace_index_schema_fails_closed() -> None:
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
        assert forbidden not in schema["$defs"]["record"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "memory_address" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_transfer_trace_index_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_TRANSFER_TRACE_INDEX_REPORT_SCHEMA_VERSION
    assert golden["trace_index_contract"] == RUNTIME_TRANSFER_TRACE_INDEX_CONTRACT
    assert golden["trace_index_scope"] == RUNTIME_TRANSFER_TRACE_INDEX_SCOPE
    assert golden["trace_materialization_policy"] == (
        RUNTIME_TRANSFER_TRACE_INDEX_TRACE_MATERIALIZATION_POLICY
    )
    assert golden["status"] == RUNTIME_TRANSFER_TRACE_INDEX_STATUS
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["transfer_count"] == len(golden["records"]) == 1
    assert golden["trace_step_count"] == 2
    assert golden["total_planned_bytes"] == 16


def test_runtime_transfer_trace_index_is_referenced() -> None:
    example_path = "examples/runtime_transfer_trace_index.py"
    schema_path = "schemas/runtime_transfer_trace_index_report.v0.schema.json"

    assert example_path in Path(".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
        Path("docs/RUNTIME_TRANSFER_EVIDENCE.md"),
        Path("docs/RUNTIME_TRANSFER_TRACE_INDEX.md"),
        Path("docs/ROADMAP_STATUS.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text
        assert schema_path in text


def _current_evidence_and_trace() -> tuple[RuntimeTransferEvidenceReport, RuntimeExecutionTrace]:
    graph = build_graph()
    compiled = compile_graph(graph, (SystolicArraySimulatorBackend().capability,))
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        proof_inputs(),
    )
    evidence = build_runtime_transfer_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    return evidence, execution.trace


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
