from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from examples.runtime_heterogeneous_storage_plan import build_graph
from examples.runtime_materialized_heterogeneous_storage import (
    build_current_runtime_materialized_heterogeneous_storage_report,
    proof_inputs,
)
from tuc import (
    SystolicArraySimulatorBackend,
    build_runtime_backend_equivalence_report,
    build_runtime_heterogeneous_storage_plan_report,
    build_runtime_materialized_layout_conversion_report,
    build_runtime_materialized_transfer_report,
    build_runtime_reference_correctness_report,
    compile_graph,
    execute_graph,
)
from tuc.runtime import heterogeneous_storage_executor as storage_executor
from tuc.runtime.heterogeneous_storage_executor import (
    RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT,
    RuntimeHeterogeneousStorageExecutionTrace,
    assert_materialized_heterogeneous_storage_execution,
    execute_graph_with_materialized_heterogeneous_storage,
)
from tuc.runtime.materialized_heterogeneous_storage import (
    RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT,
    RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_SCHEMA_VERSION,
    build_runtime_materialized_heterogeneous_storage_report,
    dump_runtime_materialized_heterogeneous_storage_report,
)

SCHEMA_PATH = Path(
    "schemas/runtime_materialized_heterogeneous_storage_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/runtime_materialized_heterogeneous_storage/current_report.json"
)


def _execution_artifacts():  # type: ignore[no-untyped-def]
    graph = build_graph()
    inputs = proof_inputs()
    baseline = compile_graph(graph, ())
    candidate = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    storage_plan = build_runtime_heterogeneous_storage_plan_report(
        graph,
        candidate.partition_plan,
    )
    baseline_execution = execute_graph(
        graph,
        baseline.partition_plan,
        inputs,
    )
    materialized = execute_graph_with_materialized_heterogeneous_storage(
        graph,
        candidate.partition_plan,
        inputs,
        storage_plan,
    )
    correctness = build_runtime_reference_correctness_report(
        graph,
        materialized.execution,
        {
            "activated_a": np.maximum(inputs["lhs_a"] @ inputs["rhs_a"], 0.0),
            "activated_b": np.maximum(inputs["lhs_b"] @ inputs["rhs_b"], 0.0),
        },
    )
    equivalence = build_runtime_backend_equivalence_report(
        graph,
        baseline.partition_plan,
        baseline_execution,
        candidate.partition_plan,
        materialized.execution,
        baseline_run_id="reference_cpu",
        candidate_run_id="materialized_heterogeneous_storage",
    )
    layout = build_runtime_materialized_layout_conversion_report(
        graph,
        candidate.partition_plan,
        materialized.execution,
        equivalence,
    )
    transfer = build_runtime_materialized_transfer_report(
        graph,
        candidate.partition_plan,
        materialized.execution,
        equivalence,
        layout,
    )
    report = build_runtime_materialized_heterogeneous_storage_report(
        graph,
        candidate.partition_plan,
        storage_plan,
        materialized,
        correctness,
        equivalence,
        layout,
        transfer,
    )
    return (
        graph,
        inputs,
        candidate,
        storage_plan,
        materialized,
        correctness,
        equivalence,
        layout,
        transfer,
        report,
    )


def test_report_materializes_all_roles_and_executes_planned_reuse() -> None:
    report = build_current_runtime_materialized_heterogeneous_storage_report()

    assert report.status == "passed"
    assert report.evidence_contract == (
        RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT
    )
    assert report.executor_contract == RUNTIME_HETEROGENEOUS_STORAGE_EXECUTOR_CONTRACT
    assert report.operation_count == 4
    assert report.slot_count == 5
    assert report.storage_write_count == report.release_count == 8
    assert report.reused_slot_count == report.reuse_event_count == 3
    assert {
        item.storage_role for item in report.storage_execution.writes
    } == {"produced_value", "layout_staging", "transfer_target_staging"}


def test_materialized_runtime_bytes_reflect_blocked_padding_and_reuse() -> None:
    report = build_current_runtime_materialized_heterogeneous_storage_report()
    blocked = next(
        item
        for item in report.storage_execution.writes
        if item.storage_id == "storage.value.projection_a"
    )

    assert blocked.logical_shape == (3, 3)
    assert blocked.physical_shape == (2, 2, 2, 2)
    assert blocked.planned_bytes == 64
    assert blocked.runtime_bytes == 128
    assert blocked.padding_verification == "zero_padding_verified"
    assert report.planned_reserved_bytes == 208
    assert report.runtime_reserved_bytes == 416
    assert report.runtime_unreused_storage_bytes == 688
    assert report.runtime_reuse_savings_bytes == 272


def test_materialized_writes_and_releases_follow_exact_plan_events() -> None:
    _, _, _, storage_plan, materialized, *_ = _execution_artifacts()
    writes = {item.storage_id: item for item in materialized.storage_trace.writes}
    releases = {
        item.storage_id: item for item in materialized.storage_trace.releases
    }

    for lifetime in storage_plan.lifetimes:
        write = writes[lifetime.storage_id]
        release = releases[lifetime.storage_id]
        assert (write.event_index, write.event_phase) == (
            lifetime.first_live_event,
            lifetime.first_live_phase,
        )
        assert (release.event_index, release.event_phase) == (
            lifetime.last_use_event,
            lifetime.last_use_phase,
        )
        assert write.slot_id == release.slot_id == lifetime.slot_id
        assert write.slot_generation == release.slot_generation


def test_reused_slots_bind_released_predecessors() -> None:
    report = build_current_runtime_materialized_heterogeneous_storage_report()
    trace = report.storage_execution
    releases = {item.storage_id: item for item in trace.releases}
    reused = tuple(item for item in trace.writes if item.slot_generation == 2)

    assert {item.slot_id for item in reused} == {
        "storage_slot_001",
        "storage_slot_002",
        "storage_slot_003",
    }
    for item in reused:
        assert item.reuse_status == "reused_after_release"
        assert item.previous_storage_id is not None
        assert releases[item.previous_storage_id].event_index < item.event_index


def test_outputs_match_independent_reference_and_cpu_baseline() -> None:
    _, inputs, _, _, materialized, correctness, equivalence, *_ = (
        _execution_artifacts()
    )

    assert correctness.passed is True
    assert equivalence.passed is True
    np.testing.assert_array_equal(
        materialized.output_for("activated_a"),
        np.maximum(inputs["lhs_a"] @ inputs["rhs_a"], 0.0),
    )
    np.testing.assert_array_equal(
        materialized.output_for("activated_b"),
        np.maximum(inputs["lhs_b"] @ inputs["rhs_b"], 0.0),
    )


def test_report_binds_layout_transfer_correctness_and_equivalence() -> None:
    *_, correctness, equivalence, layout, transfer, report = _execution_artifacts()

    assert report.reference_correctness_passed is correctness.passed is True
    assert report.backend_equivalence_passed is equivalence.passed is True
    assert report.layout_conversion_passed is True
    assert report.transfer_passed is True
    assert report.reference_correctness_digest == (
        correctness.comparison_metadata_digest
    )
    assert report.backend_equivalence_metadata_digest == (
        equivalence.comparison_metadata_digest
    )
    assert layout.status == transfer.status == "passed"


def test_noncanonical_plan_fails_before_first_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = build_graph()
    candidate = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    storage_plan = build_runtime_heterogeneous_storage_plan_report(
        graph,
        candidate.partition_plan,
    )
    tampered = replace(
        storage_plan,
        source_buffer_lifetime_digest="sha256:" + "0" * 64,
    )
    allocation_calls = 0

    def reject_allocation(*args: object, **kwargs: object) -> object:
        nonlocal allocation_calls
        allocation_calls += 1
        raise AssertionError("noncanonical plans must fail before allocation")

    monkeypatch.setattr(storage_executor.np, "empty", reject_allocation)

    with pytest.raises(ValueError, match="plan is not canonical"):
        execute_graph_with_materialized_heterogeneous_storage(
            graph,
            candidate.partition_plan,
            proof_inputs(),
            tampered,
        )
    assert allocation_calls == 0


def test_invalid_input_fails_before_first_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = build_graph()
    candidate = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    storage_plan = build_runtime_heterogeneous_storage_plan_report(
        graph,
        candidate.partition_plan,
    )
    inputs = proof_inputs()
    inputs["lhs_a"] = np.ones((2, 2), dtype=np.float64)
    allocation_calls = 0

    def reject_allocation(*args: object, **kwargs: object) -> object:
        nonlocal allocation_calls
        allocation_calls += 1
        raise AssertionError("invalid inputs must fail before allocation")

    monkeypatch.setattr(storage_executor.np, "empty", reject_allocation)

    with pytest.raises(ValueError, match="lhs_a shape mismatch"):
        execute_graph_with_materialized_heterogeneous_storage(
            graph,
            candidate.partition_plan,
            inputs,
            storage_plan,
        )
    assert allocation_calls == 0


def test_materialized_assertion_rejects_forged_staging_source() -> None:
    _, _, _, storage_plan, materialized, *_ = _execution_artifacts()
    writes = list(materialized.storage_trace.writes)
    index = next(
        index
        for index, item in enumerate(writes)
        if item.storage_role == "layout_staging"
    )
    writes[index] = replace(
        writes[index],
        source_storage_id="storage.value.activated_a",
    )
    forged_trace = replace(materialized.storage_trace, writes=tuple(writes))
    forged = replace(materialized, storage_trace=forged_trace)

    with pytest.raises(ValueError, match="source storage mismatch"):
        assert_materialized_heterogeneous_storage_execution(storage_plan, forged)


def test_execution_trace_rejects_reuse_before_predecessor_release() -> None:
    report = build_current_runtime_materialized_heterogeneous_storage_report()
    trace = report.storage_execution
    releases = list(trace.releases)
    index = next(
        index
        for index, item in enumerate(releases)
        if item.storage_id == "storage.value.projection_a"
    )
    releases[index] = replace(
        releases[index],
        event_index=11,
        event_phase="output_produced",
    )
    reordered = tuple(sorted(releases, key=lambda item: item.event_index))

    with pytest.raises(ValueError, match="reuse precedes release"):
        RuntimeHeterogeneousStorageExecutionTrace(
            graph_name=trace.graph_name,
            source_storage_plan_digest=trace.source_storage_plan_digest,
            slots=trace.slots,
            writes=trace.writes,
            releases=reordered,
        )


def test_report_contract_and_security_boundary_fail_closed() -> None:
    report = build_current_runtime_materialized_heterogeneous_storage_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        replace(report, execution_mode="external_allocator")
    with pytest.raises(ValueError, match="security boundary changed"):
        replace(report, blocked_execution_surfaces=())
    with pytest.raises(ValueError, match="requires all proofs"):
        replace(report, backend_equivalence_passed=False)


def test_report_matches_golden() -> None:
    report = build_current_runtime_materialized_heterogeneous_storage_report()

    assert dump_runtime_materialized_heterogeneous_storage_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_example_emits_only_public_metadata() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_materialized_heterogeneous_storage.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    for forbidden in (
        '"value"',
        '"values"',
        '"runtime_handle"',
        '"memory_address"',
        '"device_id"',
        '"host_path"',
        '"command"',
        '"generated_code"',
        '"backend_artifact"',
    ):
        assert forbidden not in completed.stdout


def test_schema_and_golden_are_closed() -> None:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    golden: dict[str, Any] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["evidence_contract"]["const"] == (
        RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE_CONTRACT
    )
    assert sorted(golden) == sorted(schema["required"])
    _assert_objects_fail_closed(schema)
    serialized_schema = json.dumps(schema, sort_keys=True)
    for forbidden in (
        '"value"',
        '"values"',
        '"runtime_handle"',
        '"memory_address"',
        '"device_id"',
        '"host_path"',
        '"command"',
        '"generated_code"',
        '"backend_artifact"',
    ):
        assert forbidden not in serialized_schema


def test_schema_is_referenced_by_design_and_status_docs() -> None:
    schema_path = (
        "schemas/runtime_materialized_heterogeneous_storage_report.v0.schema.json"
    )

    for path in (
        Path("docs/RUNTIME_MATERIALIZED_HETEROGENEOUS_STORAGE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0299-runtime-materialized-heterogeneous-storage.md"),
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
