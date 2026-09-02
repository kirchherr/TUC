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

from examples.runtime_backend_equivalence import build_graph, proof_inputs
from examples.runtime_materialized_transfer import (
    build_current_runtime_materialized_transfer_report,
)
from tuc import (
    MAX_RUNTIME_MATERIALIZED_TRANSFERS,
    RUNTIME_MATERIALIZED_TRANSFER_CONTRACT,
    RUNTIME_MATERIALIZED_TRANSFER_REPORT_SCHEMA_VERSION,
    LayoutKind,
    MemoryDomainKind,
    SystolicArraySimulatorBackend,
    TrustedRuntimeBackendExecutor,
    build_runtime_backend_equivalence_report,
    build_runtime_materialized_layout_conversion_report,
    build_runtime_materialized_transfer_report,
    compile_graph,
    dump_runtime_materialized_transfer_report,
    execute_graph,
    execute_graph_with_materialized_data_movement,
    execute_graph_with_materialized_layouts,
    materialize_runtime_transfer,
    trusted_runtime_transfer_executor_contract,
)

SCHEMA_PATH = Path("schemas/runtime_materialized_transfer_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_materialized_transfer/current_report.json")


def _compiled_runs():  # type: ignore[no-untyped-def]
    graph = build_graph()
    baseline = compile_graph(graph, ())
    candidate = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    return graph, baseline, candidate


def _materialized_evidence():  # type: ignore[no-untyped-def]
    graph, baseline, candidate = _compiled_runs()
    inputs = proof_inputs()
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph_with_materialized_data_movement(
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
        baseline_run_id="reference_cpu",
        candidate_run_id="materialized_systolic_transfer",
    )
    layout = build_runtime_materialized_layout_conversion_report(
        graph,
        candidate.partition_plan,
        candidate_execution,
        equivalence,
    )
    return graph, candidate, candidate_execution, equivalence, layout


def test_materialized_transfer_executes_after_layout_and_preserves_semantics() -> None:
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
    layout_only_execution = execute_graph_with_materialized_layouts(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    materialized_execution = execute_graph_with_materialized_data_movement(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )

    assert legacy_execution.trace.transfer_steps == ()
    assert layout_only_execution.trace.transfer_steps == ()
    assert len(materialized_execution.trace.layout_conversion_steps) == 1
    assert len(materialized_execution.trace.transfer_steps) == 1
    step = materialized_execution.trace.transfer_steps[0]
    assert step.tensor_name == "projection"
    assert step.source_operation == "projection"
    assert step.target_operation == "activation"
    assert step.source_backend == "systolic-sim"
    assert step.target_backend == "reference-cpu"
    assert step.source_domain is MemoryDomainKind.DEVICE_SRAM
    assert step.target_domain is MemoryDomainKind.HOST_RAM
    assert step.source_layout is LayoutKind.BLOCKED
    assert step.target_layout is LayoutKind.ROW_MAJOR
    assert step.copy_input_layout is LayoutKind.ROW_MAJOR
    assert step.logical_shape == (2, 2)
    assert step.planned_bytes == 16
    assert step.runtime_bytes == 32
    assert step.element_count == 4
    assert step.ownership_verification == "distinct_owned_buffer"
    assert step.semantic_verification == "exact_logical_values"
    assert step.status == "executed_and_verified"
    trace_text = materialized_execution.trace.dump()
    assert trace_text.index("layout_conversion_steps") < trace_text.index(
        "transfer_steps"
    )
    assert "source_domain=device_sram target_domain=host_ram" in trace_text

    assert_array_equal(
        materialized_execution.output_for("activated"),
        legacy_execution.output_for("activated"),
    )
    assert_array_equal(
        materialized_execution.output_for("activated"),
        baseline_execution.output_for("activated"),
    )


def test_transfer_primitive_owns_copy_and_keeps_source_immutable() -> None:
    graph, _baseline, candidate = _compiled_runs()
    transfer = candidate.partition_plan.transfer_edges[0]
    tensor = graph.operations[0].outputs[0]
    source = np.arange(4, dtype=np.float64).reshape(2, 2)

    transferred, step = materialize_runtime_transfer(
        transfer,
        tensor,
        source,
        input_layout=LayoutKind.ROW_MAJOR,
    )

    assert_array_equal(transferred, source)
    assert not np.shares_memory(transferred, source)
    assert transferred.flags.writeable is False
    source[0, 0] = 99.0
    assert transferred[0, 0] == 0.0
    assert step.ownership_verification == "distinct_owned_buffer"


def test_transfer_contract_closes_executable_and_residency_surfaces() -> None:
    contract = trusted_runtime_transfer_executor_contract()

    assert contract.source_domain is MemoryDomainKind.DEVICE_SRAM
    assert contract.target_domain is MemoryDomainKind.HOST_RAM
    assert contract.execution_mode == "in_process_owned_numpy_copy"
    assert contract.sequencing_policy == "layout_ready_then_domain_copy"
    assert contract.external_artifacts == "forbidden"
    assert contract.physical_residency == "not_claimed"
    assert "device_access" in contract.blocked_execution_surfaces
    assert "allocation_handles" in contract.blocked_execution_surfaces
    assert "pointer_or_address_exposure" in contract.blocked_execution_surfaces

    with pytest.raises(ValueError, match="external artifacts must be forbidden"):
        replace(contract, external_artifacts="allowed")
    with pytest.raises(ValueError, match="cannot claim physical residency"):
        replace(contract, physical_residency="claimed")
    with pytest.raises(ValueError, match="security boundary changed"):
        replace(contract, blocked_execution_surfaces=())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        (
            "source_domain",
            MemoryDomainKind.ANALOG_WEIGHT_BANK,
            "domain pair unsupported",
        ),
        ("source_backend", "other", "source assignment mismatch"),
        ("target_backend", "other", "target assignment mismatch"),
        ("source_layout", LayoutKind.ROW_MAJOR, "source assignment mismatch"),
    ),
)
def test_materialized_transfer_rejects_plan_drift_before_execution(
    field: str,
    value: object,
    message: str,
) -> None:
    _graph, _baseline, candidate = _compiled_runs()
    transfer = replace(
        candidate.partition_plan.transfer_edges[0],
        **{field: value},
    )
    plan = replace(candidate.partition_plan, transfer_edges=(transfer,))

    with pytest.raises(ValueError, match=message):
        execute_graph_with_materialized_data_movement(
            candidate.hac_ir.graph,
            plan,
            proof_inputs(),
        )


def test_materialized_transfer_rejects_stale_bytes_and_duplicate_edges() -> None:
    _graph, _baseline, candidate = _compiled_runs()
    transfer = candidate.partition_plan.transfer_edges[0]
    stale = replace(transfer, bytes_moved=8, cost_estimate=None)

    with pytest.raises(ValueError, match="planned byte count mismatch"):
        execute_graph_with_materialized_data_movement(
            candidate.hac_ir.graph,
            replace(candidate.partition_plan, transfer_edges=(stale,)),
            proof_inputs(),
        )

    with pytest.raises(ValueError, match="appears more than once"):
        execute_graph_with_materialized_data_movement(
            candidate.hac_ir.graph,
            replace(candidate.partition_plan, transfer_edges=(transfer, transfer)),
            proof_inputs(),
        )


def test_materialized_transfer_requires_matching_layout_conversion() -> None:
    _graph, _baseline, candidate = _compiled_runs()

    with pytest.raises(ValueError, match="requires a planned layout conversion"):
        execute_graph_with_materialized_data_movement(
            candidate.hac_ir.graph,
            replace(candidate.partition_plan, layout_conversions=()),
            proof_inputs(),
        )


def test_materialized_transfer_preflights_before_any_kernel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _graph, _baseline, candidate = _compiled_runs()
    kernel_calls = 0

    def count_kernel_calls(*args: object, **kwargs: object) -> object:
        nonlocal kernel_calls
        kernel_calls += 1
        raise AssertionError("kernel must not execute after failed transfer preflight")

    monkeypatch.setattr(
        TrustedRuntimeBackendExecutor,
        "execute",
        count_kernel_calls,
    )

    with pytest.raises(ValueError, match="requires a planned layout conversion"):
        execute_graph_with_materialized_data_movement(
            candidate.hac_ir.graph,
            replace(candidate.partition_plan, layout_conversions=()),
            proof_inputs(),
        )

    assert kernel_calls == 0


def test_materialized_transfer_rejects_non_finite_value() -> None:
    graph, _baseline, candidate = _compiled_runs()
    transfer = candidate.partition_plan.transfer_edges[0]
    tensor = graph.operations[0].outputs[0]
    value = np.zeros((2, 2), dtype=np.float64)
    value[0, 0] = np.inf

    with pytest.raises(ValueError, match="must be finite"):
        materialize_runtime_transfer(
            transfer,
            tensor,
            value,
            input_layout=LayoutKind.ROW_MAJOR,
        )


def test_materialized_transfer_report_binds_all_practical_evidence() -> None:
    report = build_current_runtime_materialized_transfer_report()

    assert report.status == "passed"
    assert report.evidence_contract == RUNTIME_MATERIALIZED_TRANSFER_CONTRACT
    assert report.materialization_scope == "trusted_simulator_domain_copy_only"
    assert report.materialization_policy == "trusted_simulator_transfer_executed"
    assert report.sequencing_policy == "layout_ready_then_domain_copy"
    assert report.backend_equivalence_passed is True
    assert report.layout_conversion_count == 1
    assert report.operation_step_count == 2
    assert len(report.transfers) == 1
    assert report.materialized_trace_metadata_digest.startswith("sha256:")
    assert report.materialized_layout_conversion_metadata_digest.startswith(
        "sha256:"
    )
    assert report.residency_claim_status == (
        "simulated_domains_not_physical_residency"
    )
    assert report.performance_claim_status == "not_measured"
    assert report.raw_value_policy == "omitted_by_policy"
    record = report.transfers[0]
    assert record.source_domain is MemoryDomainKind.DEVICE_SRAM
    assert record.target_domain is MemoryDomainKind.HOST_RAM
    assert record.planned_dtype == "float32"
    assert record.runtime_dtype == "float64"
    assert record.planned_bytes == 16
    assert record.runtime_bytes == 32


def test_materialized_transfer_report_matches_golden() -> None:
    report = build_current_runtime_materialized_transfer_report()

    assert dump_runtime_materialized_transfer_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_materialized_transfer_example_emits_only_public_metadata() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_materialized_transfer.py"],
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
        "memory_address",
        "host_path",
        "generated_code",
    ):
        assert forbidden not in completed.stdout


def test_materialized_transfer_report_rejects_legacy_execution() -> None:
    graph, baseline, candidate = _compiled_runs()
    inputs = proof_inputs()
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    legacy_execution = execute_graph_with_materialized_layouts(
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
    layout = build_runtime_materialized_layout_conversion_report(
        graph,
        candidate.partition_plan,
        legacy_execution,
        equivalence,
    )

    with pytest.raises(ValueError, match="plan and execution counts must match"):
        build_runtime_materialized_transfer_report(
            graph,
            candidate.partition_plan,
            legacy_execution,
            equivalence,
            layout,
        )


def test_materialized_transfer_report_rejects_stale_layout_binding() -> None:
    graph, candidate, execution, equivalence, layout = _materialized_evidence()
    stale_layout = replace(
        layout,
        candidate_output_metadata_digest="sha256:" + "0" * 64,
    )

    with pytest.raises(ValueError, match="layout report does not match execution"):
        build_runtime_materialized_transfer_report(
            graph,
            candidate.partition_plan,
            execution,
            equivalence,
            stale_layout,
        )


def test_materialized_transfer_report_contract_is_fail_closed() -> None:
    report = build_current_runtime_materialized_transfer_report()

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


def test_materialized_transfer_schema_and_golden_are_closed() -> None:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    golden: dict[str, Any] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_MATERIALIZED_TRANSFER_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_MATERIALIZED_TRANSFER_CONTRACT
    )
    assert schema["properties"]["transfers"]["maxItems"] == (
        MAX_RUNTIME_MATERIALIZED_TRANSFERS
    )
    assert sorted(golden) == sorted(schema["required"])
    assert golden["transfer_count"] == len(golden["transfers"]) == 1
    _assert_objects_fail_closed(schema)
    serialized_schema = json.dumps(schema, sort_keys=True)
    for forbidden in (
        "raw_tensor_values",
        "runtime_handle",
        "device_id",
        "memory_address",
        "host_path",
        "generated_code",
    ):
        assert f'"{forbidden}"' not in serialized_schema


def test_materialized_transfer_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_materialized_transfer_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_MATERIALIZED_TRANSFER.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0296-runtime-materialized-transfer.md"),
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
