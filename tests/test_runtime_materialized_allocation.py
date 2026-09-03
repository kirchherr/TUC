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

import tuc.runtime.allocation_executor as allocation_executor
from examples.runtime_allocation_admission import (
    build_current_runtime_allocation_admission_report,
)
from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_allocation_receipt import (
    build_current_runtime_allocation_receipt_report,
)
from examples.runtime_allocation_reconciliation import (
    build_current_runtime_allocation_reconciliation_report,
)
from examples.runtime_allocation_request_manifest import (
    build_current_runtime_allocation_request_manifest_report,
)
from examples.runtime_buffer_lifetime import build_graph
from examples.runtime_materialized_allocation import (
    build_current_runtime_materialized_allocation_report,
    proof_inputs,
)
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from tuc import (
    MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS,
    MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS,
    RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT,
    RUNTIME_MATERIALIZED_ALLOCATION_REPORT_SCHEMA_VERSION,
    MemoryDomainKind,
    OperationKind,
    RuntimeAllocationExecutionPrerequisites,
    RuntimeMaterializedAllocationExecution,
    TrustedRuntimeBackendExecutor,
    build_runtime_materialized_allocation_report,
    build_runtime_reference_correctness_report,
    compile_graph,
    dump_runtime_materialized_allocation_report,
    execute_graph,
    execute_graph_with_materialized_allocations,
    trusted_runtime_allocation_executor_contract,
)
from tuc.backends import BackendCapability

SCHEMA_PATH = Path("schemas/runtime_materialized_allocation_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/runtime_materialized_allocation/current_report.json")


def _compiled():  # type: ignore[no-untyped-def]
    graph = build_graph()
    backend = BackendCapability(
        name="reference-cpu",
        supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.HOST_RAM,
    )
    return graph, compile_graph(graph, (backend,))


def _prerequisites() -> RuntimeAllocationExecutionPrerequisites:
    return RuntimeAllocationExecutionPrerequisites(
        allocation_plan=build_current_runtime_allocation_plan_report(),
        memory_budget=build_current_runtime_memory_budget_report(),
        request_manifest=build_current_runtime_allocation_request_manifest_report(),
        admission=build_current_runtime_allocation_admission_report(),
        receipt=build_current_runtime_allocation_receipt_report(),
        reconciliation=build_current_runtime_allocation_reconciliation_report(),
    )


def _materialized():  # type: ignore[no-untyped-def]
    graph, compiled = _compiled()
    prerequisites = _prerequisites()
    inputs = proof_inputs()
    execution = execute_graph_with_materialized_allocations(
        graph,
        compiled.partition_plan,
        inputs,
        prerequisites,
    )
    correctness = build_runtime_reference_correctness_report(
        graph,
        execution.execution,
        {
            "left_out": inputs["lhs_a"] @ inputs["rhs_a"],
            "right_out": inputs["lhs_b"] @ inputs["rhs_b"],
        },
    )
    return graph, compiled, prerequisites, execution, correctness


def test_materialized_allocator_executes_real_release_and_slot_reuse() -> None:
    graph, compiled, prerequisites, materialized, correctness = _materialized()
    legacy = execute_graph(graph, compiled.partition_plan, proof_inputs())

    assert correctness.passed
    assert_array_equal(materialized.output_for("left_out"), legacy.output_for("left_out"))
    assert_array_equal(
        materialized.output_for("right_out"),
        legacy.output_for("right_out"),
    )
    trace = materialized.allocation_trace
    assert len(trace.slots) == 3
    assert len(trace.writes) == len(trace.releases) == 4
    assert trace.reuse_event_count == 1
    assert trace.planned_reserved_bytes == 192
    assert trace.runtime_reserved_bytes == 384
    assert trace.runtime_unreused_tensor_bytes == 512
    assert trace.runtime_reuse_savings_bytes == 128
    reused = next(step for step in trace.writes if step.reuse_status == "reused_after_release")
    assert reused.tensor_name == "right_tmp"
    assert reused.slot_id == "slot_001"
    assert reused.slot_generation == 2
    assert reused.previous_tensor_name == "left_tmp"
    left_release = next(step for step in trace.releases if step.tensor_name == "left_tmp")
    assert left_release.release_index == 1
    assert left_release.release_index < reused.operation_index
    assert prerequisites.allocation_plan.committed_reuse_savings_bytes == 64


def test_materialized_allocator_preallocates_each_slot_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allocations: list[np.ndarray] = []
    original = allocation_executor._allocate_slot_storage

    def capture(shape: tuple[int, ...]) -> np.ndarray:
        value = original(shape)
        allocations.append(value)
        return value

    monkeypatch.setattr(allocation_executor, "_allocate_slot_storage", capture)
    _graph, _compiled_graph, prerequisites, materialized, _correctness = _materialized()

    assert len(allocations) == prerequisites.allocation_plan.slot_count == 3
    assert sum(value.nbytes for value in allocations) == 384
    assert materialized.allocation_trace.reuse_event_count == 1


def test_materialized_allocator_retains_only_inputs_and_terminal_snapshots() -> None:
    _graph, _compiled_graph, _prereqs, materialized, _correctness = _materialized()

    assert set(materialized.execution.values) == {
        "lhs_a",
        "rhs_a",
        "lhs_b",
        "rhs_b",
        "left_out",
        "right_out",
    }
    assert materialized.output_for("left_out").flags.writeable is False
    assert materialized.output_for("right_out").flags.writeable is False
    with pytest.raises(KeyError):
        materialized.execution.record_for("left_tmp")
    with pytest.raises(KeyError):
        materialized.execution.record_for("right_tmp")


def test_materialized_allocator_contract_is_fail_closed() -> None:
    contract = trusted_runtime_allocation_executor_contract()

    assert contract.execution_mode == "in_process_preallocated_numpy_slots"
    assert contract.write_mode == "trusted_kernel_result_copied_into_slot"
    assert contract.supported_domain is MemoryDomainKind.HOST_RAM
    assert contract.max_slots == MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS
    assert "pointer_or_address_exposure" in contract.blocked_execution_surfaces
    assert "runtime_handle_serialization" in contract.blocked_execution_surfaces

    with pytest.raises(ValueError, match="contract changed"):
        replace(contract, external_artifacts="allowed")
    with pytest.raises(ValueError, match="security boundary changed"):
        replace(contract, blocked_execution_surfaces=())


def test_noncanonical_memory_chain_rejects_before_allocation_or_kernel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph, compiled = _compiled()
    prerequisites = _prerequisites()
    stale_budget = replace(
        prerequisites.memory_budget,
        source_allocation_metadata_digest="sha256:" + "0" * 64,
    )
    stale = replace(prerequisites, memory_budget=stale_budget)
    allocation_calls = 0
    kernel_calls = 0

    def reject_allocation(shape: tuple[int, ...]) -> np.ndarray:
        nonlocal allocation_calls
        allocation_calls += 1
        raise AssertionError("allocation must not run after failed preflight")

    def reject_kernel(*args: object, **kwargs: object) -> np.ndarray:
        nonlocal kernel_calls
        kernel_calls += 1
        raise AssertionError("kernel must not run after failed preflight")

    monkeypatch.setattr(allocation_executor, "_allocate_slot_storage", reject_allocation)
    monkeypatch.setattr(TrustedRuntimeBackendExecutor, "execute", reject_kernel)
    with pytest.raises(ValueError, match="memory budget is not canonical"):
        execute_graph_with_materialized_allocations(
            graph,
            compiled.partition_plan,
            proof_inputs(),
            stale,
        )
    assert allocation_calls == kernel_calls == 0


@pytest.mark.parametrize(
    ("input_value", "message"),
    (
        (np.ones((4, 4), dtype=np.float32), "dtype must be float64"),
        (np.ones((2, 8), dtype=np.float64), "shape mismatch"),
        (
            np.full((4, 4), np.inf, dtype=np.float64),
            "must be finite",
        ),
    ),
)
def test_invalid_input_rejects_before_slot_allocation(
    monkeypatch: pytest.MonkeyPatch,
    input_value: np.ndarray,
    message: str,
) -> None:
    graph, compiled = _compiled()
    inputs = proof_inputs()
    inputs["lhs_a"] = input_value
    allocation_calls = 0

    def reject_allocation(shape: tuple[int, ...]) -> np.ndarray:
        nonlocal allocation_calls
        allocation_calls += 1
        raise AssertionError("allocation must not run for invalid inputs")

    monkeypatch.setattr(allocation_executor, "_allocate_slot_storage", reject_allocation)
    with pytest.raises((TypeError, ValueError), match=message):
        execute_graph_with_materialized_allocations(
            graph,
            compiled.partition_plan,
            inputs,
            _prerequisites(),
        )
    assert allocation_calls == 0


def test_nonfinite_kernel_result_is_rejected() -> None:
    graph, compiled = _compiled()
    original_execute = TrustedRuntimeBackendExecutor.execute

    def nonfinite(
        self: TrustedRuntimeBackendExecutor,
        operation: object,
        values: object,
    ) -> np.ndarray:
        result = original_execute(self, operation, values)  # type: ignore[arg-type]
        result[0, 0] = np.inf
        return result

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(TrustedRuntimeBackendExecutor, "execute", nonfinite)
        with pytest.raises(ValueError, match="kernel result must be finite"):
            execute_graph_with_materialized_allocations(
                graph,
                compiled.partition_plan,
                proof_inputs(),
                _prerequisites(),
            )


def test_materialized_allocation_report_binds_execution_and_correctness() -> None:
    report = build_current_runtime_materialized_allocation_report()

    assert report.status == "passed"
    assert report.evidence_contract == RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT
    assert report.materialization_policy == "preallocate_write_release_reuse"
    assert report.reference_correctness_passed is True
    assert report.slot_count == 3
    assert report.reused_slot_count == 1
    assert report.allocation_count == report.release_count == 4
    assert report.reuse_event_count == 1
    assert report.runtime_reserved_bytes == 384
    assert report.runtime_reuse_savings_bytes == 128
    assert report.terminal_output_snapshot_bytes == 256
    assert report.kernel_temporary_policy == "excluded_from_allocator_memory_claim"
    assert report.native_allocator_claim == "not_claimed"
    assert report.performance_claim == "not_measured"
    assert report.raw_value_policy == "omitted_by_policy"


def test_materialized_allocation_report_rejects_stale_trace_binding() -> None:
    graph, compiled, prerequisites, materialized, correctness = _materialized()
    stale_trace = replace(
        materialized.allocation_trace,
        source_admission_digest="sha256:" + "0" * 64,
    )
    stale_execution = RuntimeMaterializedAllocationExecution(
        execution=materialized.execution,
        allocation_trace=stale_trace,
    )

    with pytest.raises(ValueError, match="source digest linkage mismatch"):
        build_runtime_materialized_allocation_report(
            graph,
            compiled.partition_plan,
            prerequisites,
            stale_execution,
            correctness,
        )


def test_materialized_allocation_report_requires_correctness_pass() -> None:
    graph, compiled, prerequisites, materialized, _correctness = _materialized()
    failed = build_runtime_reference_correctness_report(
        graph,
        materialized.execution,
        {
            "left_out": np.zeros((4, 4), dtype=np.float64),
            "right_out": np.zeros((4, 4), dtype=np.float64),
        },
    )

    with pytest.raises(ValueError, match="requires passing correctness"):
        build_runtime_materialized_allocation_report(
            graph,
            compiled.partition_plan,
            prerequisites,
            materialized,
            failed,
        )


def test_materialized_allocation_report_contract_rejects_claim_expansion() -> None:
    report = build_current_runtime_materialized_allocation_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        replace(report, native_allocator_claim="claimed")
    with pytest.raises(ValueError, match="contract mismatch"):
        replace(report, kernel_temporary_policy="included")
    with pytest.raises(ValueError, match="correctness PASS"):
        replace(report, reference_correctness_passed=False)
    with pytest.raises(ValueError, match="security boundary changed"):
        replace(report, blocked_execution_surfaces=())


def test_materialized_allocation_report_matches_golden() -> None:
    report = build_current_runtime_materialized_allocation_report()

    assert dump_runtime_materialized_allocation_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_materialized_allocation_example_emits_metadata_only() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_materialized_allocation.py"],
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
        "memory_address",
        "device_pointer",
        "host_path",
        "generated_code",
    ):
        assert f'"{forbidden}"' not in completed.stdout


def test_materialized_allocation_schema_and_golden_are_closed() -> None:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    golden: dict[str, Any] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_MATERIALIZED_ALLOCATION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_MATERIALIZED_ALLOCATION_CONTRACT
    )
    assert schema["properties"]["slots"]["maxItems"] == (
        MAX_RUNTIME_MATERIALIZED_ALLOCATION_SLOTS
    )
    assert schema["properties"]["allocations"]["maxItems"] == (
        MAX_RUNTIME_MATERIALIZED_ALLOCATION_BINDINGS
    )
    assert sorted(golden) == sorted(schema["required"])
    assert golden["allocation_count"] == len(golden["allocations"]) == 4
    assert golden["slot_count"] == len(golden["slots"]) == 3
    _assert_objects_fail_closed(schema)
    serialized_schema = json.dumps(schema, sort_keys=True)
    for forbidden in (
        "raw_tensor_values",
        "runtime_handle",
        "memory_address",
        "device_pointer",
        "host_path",
        "generated_code",
    ):
        assert f'"{forbidden}"' not in serialized_schema


def test_materialized_allocation_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_materialized_allocation_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_MATERIALIZED_ALLOCATION.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0297-runtime-materialized-allocation.md"),
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
