from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_hs_ir_plan_alignment import build_alignment_report
from examples.runtime_mixed_backend_equivalence import build_graph, proof_inputs
from tuc import (
    MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_ISSUES,
    MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_STEPS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS,
    RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT,
    RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeHsIrPlanAlignmentError,
    RuntimeHsIrPlanAlignmentStep,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
    assert_runtime_hs_ir_plan_alignment,
    build_runtime_hs_ir_plan_alignment_report,
    compile_graph,
    dump_runtime_hs_ir_plan_alignment_report,
    execute_graph,
    runtime_hs_ir_plan_alignment_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/runtime_hs_ir_plan_alignment/mixed_report.json")
SCHEMA_PATH = Path("schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json")


def test_runtime_hs_ir_plan_alignment_passes_for_mixed_backend_slice() -> None:
    report = build_alignment_report()

    assert report.alignment_contract == RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.trusted_executor_registry == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert report.artifact_status == RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS
    assert report.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert report.passed
    assert report.issues == ()
    assert report.step_count == 4
    assert report.hs_ir_backend_sequence == (
        "systolic-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    )
    assert report.partition_backend_sequence == report.hs_ir_backend_sequence
    assert report.execution_trace_backend_sequence == report.hs_ir_backend_sequence
    assert report.hs_ir_layout_conversion_count == 1
    assert report.hs_ir_total_layout_conversion_bytes == 24
    assert report.partition_total_layout_conversion_bytes == 24
    assert tuple(step.operation_name for step in report.steps) == (
        "projection",
        "normalize",
        "sum_rows",
        "activation",
    )
    assert report.steps[0].hs_ir_produced_layout == "blocked"
    assert report.steps[1].layout_conversion_bytes == 24
    assert {step.alignment_status for step in report.steps} == {"aligned"}
    assert {step.trusted_executor_status for step in report.steps} == {"trusted"}
    assert tuple(runtime_hs_ir_plan_alignment_report_to_dict(report)) == (
        "alignment_contract",
        "alignment_metadata_digest",
        "artifact_status",
        "blocked_execution_surfaces",
        "execution_trace_backend_sequence",
        "execution_trace_graph_name",
        "executor_contract",
        "graph_name",
        "hs_ir_backend_sequence",
        "hs_ir_layout_conversion_count",
        "hs_ir_total_data_movement_bytes",
        "hs_ir_total_layout_conversion_bytes",
        "hs_ir_total_transfer_bytes",
        "hs_ir_transfer_edge_count",
        "issues",
        "partition_backend_sequence",
        "partition_layout_conversion_count",
        "partition_plan_graph_name",
        "partition_total_data_movement_bytes",
        "partition_total_layout_conversion_bytes",
        "partition_total_transfer_bytes",
        "partition_transfer_edge_count",
        "passed",
        "raw_value_policy",
        "schema_version",
        "step_count",
        "steps",
        "trusted_executor_registry",
    )


def test_runtime_hs_ir_plan_alignment_dump_matches_golden() -> None:
    assert dump_runtime_hs_ir_plan_alignment_report(build_alignment_report()) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_runtime_hs_ir_plan_alignment_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_hs_ir_plan_alignment.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_hs_ir_plan_alignment.data_only.v0" in completed.stdout
    assert '"passed": true' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert '"trusted_executor_status": "trusted"' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_runtime_hs_ir_plan_alignment_assertion_returns_report() -> None:
    report = build_alignment_report()

    assert assert_runtime_hs_ir_plan_alignment(report) is report


def test_runtime_hs_ir_plan_alignment_records_partition_backend_mismatch() -> None:
    graph = build_graph()
    compiled = compile_graph(
        graph,
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, proof_inputs())
    forged_plan = replace(
        compiled.partition_plan,
        assignments=(
            replace(compiled.partition_plan.assignments[0], backend_name="reference-cpu"),
            *compiled.partition_plan.assignments[1:],
        ),
    )

    report = build_runtime_hs_ir_plan_alignment_report(
        compiled.hs_ir,
        forged_plan,
        execution,
    )

    assert not report.passed
    assert ("backend_sequence", "hs_ir_partition_backend_mismatch") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }
    assert ("projection", "hs_ir_partition_backend_mismatch") in {
        (issue.subject, issue.issue_code) for issue in report.issues
    }
    with pytest.raises(RuntimeHsIrPlanAlignmentError, match="projection"):
        assert_runtime_hs_ir_plan_alignment(report)


def test_runtime_hs_ir_plan_alignment_rejects_forged_issues() -> None:
    graph = build_graph()
    compiled = compile_graph(
        graph,
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, proof_inputs())
    forged_plan = replace(
        compiled.partition_plan,
        assignments=(
            replace(compiled.partition_plan.assignments[0], backend_name="reference-cpu"),
            *compiled.partition_plan.assignments[1:],
        ),
    )
    report = build_runtime_hs_ir_plan_alignment_report(
        compiled.hs_ir,
        forged_plan,
        execution,
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        replace(report, issues=())


def test_runtime_hs_ir_plan_alignment_rejects_forbidden_text() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeHsIrPlanAlignmentStep(
            operation_name="python_source",
            operation_kind="matmul",
            hs_ir_backend="systolic-sim",
            partition_backend="systolic-sim",
            execution_trace_backend="systolic-sim",
            hs_ir_produced_layout="blocked",
            partition_produced_layout="blocked",
            transfer_bytes=0,
            layout_conversion_bytes=0,
            trusted_executor_status="trusted",
            alignment_status="aligned",
        )


def test_runtime_hs_ir_plan_alignment_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS
    )
    assert schema["properties"]["alignment_contract"]["const"] == (
        RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["trusted_executor_registry"]["const"] == (
        TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["steps"]["maxItems"] == (
        MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_STEPS
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_HS_IR_PLAN_ALIGNMENT_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_hs_ir_plan_alignment_schema_fails_closed() -> None:
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
        "raw_tensor_value",
        "tensor_values",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["step"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_hs_ir_plan_alignment_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == RUNTIME_HS_IR_PLAN_ALIGNMENT_REPORT_SCHEMA_VERSION
    assert golden["artifact_status"] == RUNTIME_HS_IR_PLAN_ALIGNMENT_ARTIFACT_STATUS
    assert golden["alignment_contract"] == RUNTIME_HS_IR_PLAN_ALIGNMENT_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["step_count"] == len(golden["steps"]) == 4


def test_runtime_hs_ir_plan_alignment_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_hs_ir_plan_alignment_report.v0.schema.json"

    for path in (
        Path("README.md"),
        Path("docs/RUNTIME_HS_IR_PLAN_ALIGNMENT.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0148-runtime-hs-ir-plan-alignment.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema_node: dict[str, Any]) -> None:
    if schema_node.get("type") == "object":
        assert schema_node.get("additionalProperties") is False
    for value in schema_node.values():
        if isinstance(value, dict):
            _assert_objects_fail_closed(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _assert_objects_fail_closed(item)
