from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.testing import assert_array_equal

from examples.runtime_materialized_layout_conversion import (
    build_current_runtime_materialized_layout_conversion_report,
)
from examples.runtime_mixed_backend_equivalence import build_graph, proof_inputs
from tuc import (
    MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSIONS,
    RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT,
    RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_SCHEMA_VERSION,
    CompilationResult,
    ComputeGraph,
    LayoutKind,
    SystolicArraySimulatorBackend,
    TensorRef,
    VectorSimulatorBackend,
    build_runtime_backend_equivalence_report,
    build_runtime_materialized_layout_conversion_report,
    compile_graph,
    dump_runtime_materialized_layout_conversion_report,
    execute_graph,
    execute_graph_with_materialized_layouts,
    materialize_layout_conversion,
    trusted_runtime_layout_converter_contract,
)

SCHEMA_PATH = Path("schemas/runtime_materialized_layout_conversion_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/runtime_materialized_layout_conversion/current_report.json"
)


def _compiled_runs() -> tuple[ComputeGraph, CompilationResult, CompilationResult]:
    graph = build_graph()
    baseline = compile_graph(graph, ())
    candidate = compile_graph(
        graph,
        (
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ),
    )
    return graph, baseline, candidate


def test_materialized_layout_conversion_executes_and_preserves_semantics() -> None:
    graph, baseline, candidate = _compiled_runs()
    inputs = proof_inputs()

    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    legacy_candidate_execution = execute_graph(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    materialized_execution = execute_graph_with_materialized_layouts(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )

    assert legacy_candidate_execution.trace.layout_conversion_steps == ()
    assert "layout_conversion_steps" not in legacy_candidate_execution.trace.dump()
    assert len(materialized_execution.trace.steps) == 4
    assert len(materialized_execution.trace.layout_conversion_steps) == 1
    step = materialized_execution.trace.layout_conversion_steps[0]
    assert step.tensor_name == "projection"
    assert step.source_operation == "projection"
    assert step.target_operation == "normalize"
    assert step.source_layout is LayoutKind.BLOCKED
    assert step.target_layout is LayoutKind.ROW_MAJOR
    assert step.logical_shape == (2, 3)
    assert step.physical_shape == (1, 2, 2, 2)
    assert step.tile_shape == (2, 2)
    assert step.planned_bytes == 24
    assert step.runtime_logical_bytes == 48
    assert step.runtime_physical_bytes == 64
    assert step.logical_element_count == 6
    assert step.physical_element_count == 8
    assert step.padding_element_count == 2
    assert step.temporary_storage_bytes == 112
    assert step.semantic_verification == "exact_logical_values"
    assert step.status == "executed_and_verified"
    assert "source_layout=blocked target_layout=row_major" in (
        materialized_execution.trace.dump()
    )

    assert_array_equal(
        materialized_execution.output_for("activated"),
        legacy_candidate_execution.output_for("activated"),
    )
    assert_array_equal(
        materialized_execution.output_for("activated"),
        baseline_execution.output_for("activated"),
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        materialized_execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="materialized_mixed_simulators",
    )
    assert equivalence.passed


def test_trusted_layout_converter_contract_closes_executable_surfaces() -> None:
    contract = trusted_runtime_layout_converter_contract()

    assert contract.source_layout is LayoutKind.BLOCKED
    assert contract.target_layout is LayoutKind.ROW_MAJOR
    assert contract.tile_shape == (2, 2)
    assert contract.execution_mode == "in_process_fixed_tiled_copy"
    assert contract.external_artifacts == "forbidden"
    assert contract.blocked_execution_surfaces == (
        "backend_plugin_discovery",
        "device_access",
        "dynamic_import",
        "dynamic_library_loading",
        "generated_artifact_execution",
        "jit_execution",
        "network_access",
        "subprocess_execution",
    )

    with pytest.raises(ValueError, match="external artifacts must be forbidden"):
        replace(contract, external_artifacts="allowed")
    with pytest.raises(ValueError, match="runtime name byte limit"):
        replace(contract, converter_name="c" * 257)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("source_layout", LayoutKind.COLUMN_MAJOR, "source layout unsupported"),
        ("target_layout", LayoutKind.COLUMN_MAJOR, "target layout unsupported"),
        ("bytes_converted", 56, "planned byte count mismatch"),
        ("source_operation", "wrong_source", "source operation mismatch"),
    ),
)
def test_materialized_layout_conversion_rejects_plan_drift(
    field: str,
    value: object,
    message: str,
) -> None:
    _graph, _baseline, candidate = _compiled_runs()
    conversion = replace(candidate.partition_plan.layout_conversions[0], **{field: value})
    plan = replace(candidate.partition_plan, layout_conversions=(conversion,))

    with pytest.raises(ValueError, match=message):
        execute_graph_with_materialized_layouts(
            candidate.hac_ir.graph,
            plan,
            proof_inputs(),
        )


def test_materialized_layout_conversion_rejects_duplicate_plan_entry() -> None:
    _graph, _baseline, candidate = _compiled_runs()
    conversion = candidate.partition_plan.layout_conversions[0]
    plan = replace(
        candidate.partition_plan,
        layout_conversions=(conversion, conversion),
    )

    with pytest.raises(ValueError, match="appears more than once"):
        execute_graph_with_materialized_layouts(
            candidate.hac_ir.graph,
            plan,
            proof_inputs(),
        )


def test_materialized_layout_conversion_rejects_rank_and_non_finite_values() -> None:
    graph, _baseline, candidate = _compiled_runs()
    conversion = candidate.partition_plan.layout_conversions[0]
    projection = graph.operations[0].outputs[0]

    with pytest.raises(ValueError, match="supports rank-2 tensors only"):
        materialize_layout_conversion(
            conversion,
            TensorRef("projection", (6,)),
            np.zeros((6,), dtype=np.float64),
        )

    non_finite = np.zeros(projection.shape, dtype=np.float64)
    non_finite[0, 0] = np.inf
    with pytest.raises(ValueError, match="must be finite"):
        materialize_layout_conversion(conversion, projection, non_finite)


def test_materialized_layout_conversion_report_binds_execution_and_equivalence() -> None:
    report = build_current_runtime_materialized_layout_conversion_report()

    assert report.status == "passed"
    assert report.evidence_contract == RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT
    assert report.backend_equivalence_passed is True
    assert report.materialized_trace_metadata_digest.startswith("sha256:")
    assert report.candidate_output_metadata_digest.startswith("sha256:")
    assert report.materialization_scope == "trusted_simulator_only"
    assert report.materialization_policy == "trusted_simulator_conversion_executed"
    assert report.residency_claim_status == "not_native_or_device_residency"
    assert report.performance_claim_status == "not_measured"
    assert report.raw_value_policy == "omitted_by_policy"
    assert report.external_artifacts == "forbidden"
    assert report.operation_step_count == 4
    assert len(report.conversions) == 1
    record = report.conversions[0]
    assert record.source_backend == "systolic-sim"
    assert record.target_backend == "vector-sim"
    assert record.planned_dtype == "float32"
    assert record.runtime_dtype == "float64"
    assert record.planned_bytes == 24
    assert record.runtime_logical_bytes == 48
    assert record.runtime_physical_bytes == 64


def test_materialized_layout_conversion_report_matches_golden() -> None:
    report = build_current_runtime_materialized_layout_conversion_report()

    assert dump_runtime_materialized_layout_conversion_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_materialized_layout_conversion_example_uses_public_output_boundary() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_materialized_layout_conversion.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    for forbidden in (
        "raw_tensor_values",
        "runtime_handle",
        "device_id",
        "host_path",
        "generated_code",
    ):
        assert forbidden not in completed.stdout


def test_materialized_layout_conversion_report_rejects_legacy_execution() -> None:
    graph, baseline, candidate = _compiled_runs()
    inputs = proof_inputs()
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    legacy_execution = execute_graph(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        legacy_execution,
    )

    with pytest.raises(ValueError, match="plan and execution counts must match"):
        build_runtime_materialized_layout_conversion_report(
            graph,
            candidate.partition_plan,
            legacy_execution,
            equivalence,
        )


def test_materialized_layout_conversion_report_rejects_stale_candidate_binding() -> None:
    graph, baseline, candidate = _compiled_runs()
    inputs = proof_inputs()
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph_with_materialized_layouts(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        candidate_execution,
    )
    stale_candidate_run = replace(
        equivalence.runs[1],
        tensor_record_count=equivalence.runs[1].tensor_record_count + 1,
    )
    stale_equivalence = replace(
        equivalence,
        runs=(equivalence.runs[0], stale_candidate_run),
    )

    with pytest.raises(ValueError, match="candidate equivalence run mismatch"):
        build_runtime_materialized_layout_conversion_report(
            graph,
            candidate.partition_plan,
            candidate_execution,
            stale_equivalence,
        )


def test_materialized_layout_conversion_report_contract_is_fail_closed() -> None:
    report = build_current_runtime_materialized_layout_conversion_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        replace(report, external_artifacts="allowed")
    with pytest.raises(ValueError, match="requires backend equivalence PASS"):
        replace(report, backend_equivalence_passed=False)
    with pytest.raises(ValueError, match="blocked surfaces changed"):
        replace(report, blocked_execution_surfaces=())
    with pytest.raises(ValueError, match="run IDs must be distinct"):
        replace(report, baseline_run_id=report.candidate_run_id)
    with pytest.raises(ValueError, match="metadata byte limit"):
        replace(report, graph_name="g" * 257)


def test_materialized_layout_conversion_schema_and_golden_are_closed() -> None:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    golden: dict[str, Any] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_MATERIALIZED_LAYOUT_CONVERSION_CONTRACT
    )
    assert schema["properties"]["conversions"]["maxItems"] == (
        MAX_RUNTIME_MATERIALIZED_LAYOUT_CONVERSIONS
    )
    assert sorted(golden) == sorted(schema["required"])
    assert golden["conversion_count"] == len(golden["conversions"]) == 1
    _assert_objects_fail_closed(schema)
    serialized_schema = json.dumps(schema, sort_keys=True)
    for forbidden in (
        "raw_tensor_values",
        "runtime_handle",
        "device_id",
        "host_path",
        "generated_code",
    ):
        assert f'"{forbidden}"' not in serialized_schema


def test_materialized_layout_conversion_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_materialized_layout_conversion_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_MATERIALIZED_LAYOUT_CONVERSION.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0295-runtime-materialized-layout-conversion.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
