from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_heterogeneous_storage_plan import (
    build_current_runtime_heterogeneous_storage_plan_report,
    build_graph,
)
from tuc import (
    MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES,
    MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS,
    RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT,
    RUNTIME_HETEROGENEOUS_STORAGE_PLAN_REPORT_SCHEMA_VERSION,
    LayoutKind,
    SystolicArraySimulatorBackend,
    TrustedRuntimeBackendExecutor,
    build_runtime_heterogeneous_storage_plan_report,
    compile_graph,
    dump_runtime_heterogeneous_storage_plan_report,
)

SCHEMA_PATH = Path("schemas/runtime_heterogeneous_storage_plan_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/runtime_heterogeneous_storage_plan/current_report.json"
)


def _compiled():  # type: ignore[no-untyped-def]
    graph = build_graph()
    compiled = compile_graph(
        graph,
        (SystolicArraySimulatorBackend().capability,),
    )
    return graph, compiled


def test_storage_plan_models_produced_conversion_and_transfer_storage() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()

    assert report.passed is True
    assert report.storage_contract == RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT
    assert report.operation_count == 4
    assert report.event_count == 17
    assert report.produced_storage_count == 4
    assert report.layout_staging_count == report.planned_layout_conversion_count == 2
    assert report.transfer_staging_count == report.planned_transfer_count == 2
    assert len(report.lifetimes) == 8
    assert len(report.slots) == 5
    assert report.reused_slot_count == 3
    assert "runtime_memory_allocation" in report.blocked_execution_surfaces
    assert "external_allocator_calls" in report.blocked_execution_surfaces


def test_blocked_odd_shape_uses_physical_padding_and_larger_slot() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    projection = next(
        item for item in report.lifetimes if item.storage_id == "storage.value.projection_a"
    )

    assert projection.layout is LayoutKind.BLOCKED
    assert projection.logical_shape == (3, 3)
    assert projection.physical_shape == (2, 2, 2, 2)
    assert projection.tile_shape == (2, 2)
    assert projection.logical_element_count == 9
    assert projection.physical_element_count == 16
    assert projection.padding_element_count == 7
    assert projection.logical_bytes == 36
    assert projection.physical_bytes == 64


def test_event_timeline_keeps_copy_endpoints_live_at_each_boundary() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    by_id = {item.storage_id: item for item in report.lifetimes}
    source = by_id["storage.value.projection_a"]
    layout = by_id["storage.layout.projection_a.activation_a"]
    transfer = by_id["storage.transfer.projection_a.activation_a"]

    assert (source.first_live_event, source.last_use_event) == (3, 4)
    assert source.last_use_phase == "layout_conversion"
    assert (layout.first_live_event, layout.last_use_event) == (4, 5)
    assert layout.last_use_phase == "transfer"
    assert (transfer.first_live_event, transfer.last_use_event) == (5, 6)
    assert transfer.last_use_phase == "consumer_execution"


def test_identical_non_overlapping_staging_lifetimes_reuse_slots() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    slots = {slot.storage_role: slot for slot in report.slots if slot.storage_count == 2}

    assert slots["produced_value"].storage_ids == (
        "storage.value.projection_a",
        "storage.value.projection_b",
    )
    assert slots["produced_value"].bytes_reserved == 64
    assert slots["layout_staging"].storage_ids == (
        "storage.layout.projection_a.activation_a",
        "storage.layout.projection_b.activation_b",
    )
    assert slots["layout_staging"].bytes_reserved == 36
    assert slots["transfer_target_staging"].storage_ids == (
        "storage.transfer.projection_a.activation_a",
        "storage.transfer.projection_b.activation_b",
    )
    assert slots["transfer_target_staging"].bytes_reserved == 36
    assert all(slot.non_overlapping for slot in slots.values())


def test_role_boundary_prevents_unsafe_cross_role_reuse() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    row_major_36_byte_slots = tuple(
        slot
        for slot in report.slots
        if slot.layout is LayoutKind.ROW_MAJOR and slot.bytes_reserved == 36
    )

    assert len(row_major_36_byte_slots) == 4
    assert {slot.storage_role for slot in row_major_36_byte_slots} == {
        "produced_value",
        "layout_staging",
        "transfer_target_staging",
    }


def test_storage_plan_accounts_peak_reservation_and_reuse() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    peaks = {peak.memory_domain.value: peak for peak in report.domain_peaks}

    assert report.total_unreused_physical_bytes == 344
    assert report.total_reserved_physical_bytes == 208
    assert report.reuse_savings_bytes == 136
    assert report.peak_live_physical_bytes == 136
    assert peaks["device_sram"].peak_live_physical_bytes == 100
    assert peaks["device_sram"].reserved_slot_bytes == 100
    assert peaks["host_ram"].peak_live_physical_bytes == 72
    assert peaks["host_ram"].reserved_slot_bytes == 108


def test_source_evidence_projections_are_bound_independently() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()

    assert report.source_transfer_partition_plan_digest.startswith("sha256:")
    assert report.source_layout_partition_plan_digest.startswith("sha256:")
    assert (
        report.source_transfer_partition_plan_digest
        != report.source_layout_partition_plan_digest
    )
    assert report.source_buffer_lifetime_digest.startswith("sha256:")
    assert report.source_transfer_evidence_digest.startswith("sha256:")
    assert report.source_layout_conversion_evidence_digest.startswith("sha256:")


def test_storage_planning_never_executes_a_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def reject_execution(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("data-only storage planning must not execute a backend")

    monkeypatch.setattr(TrustedRuntimeBackendExecutor, "execute", reject_execution)
    graph, compiled = _compiled()

    report = build_runtime_heterogeneous_storage_plan_report(
        graph,
        compiled.partition_plan,
    )

    assert report.passed is True
    assert calls == 0


def test_storage_plan_rejects_unsupported_layout() -> None:
    graph, compiled = _compiled()
    assignments = list(compiled.partition_plan.assignments)
    assignments[0] = replace(assignments[0], produced_layout=LayoutKind.VECTOR)
    transfer_edges = list(compiled.partition_plan.transfer_edges)
    transfer_edges[0] = replace(
        transfer_edges[0],
        source_layout=LayoutKind.VECTOR,
    )
    conversions = list(compiled.partition_plan.layout_conversions)
    conversions[0] = replace(
        conversions[0],
        source_layout=LayoutKind.VECTOR,
    )
    plan = replace(
        compiled.partition_plan,
        assignments=tuple(assignments),
        transfer_edges=tuple(transfer_edges),
        layout_conversions=tuple(conversions),
    )

    with pytest.raises(ValueError, match="heterogeneous storage layout is unsupported"):
        build_runtime_heterogeneous_storage_plan_report(graph, plan)


def test_storage_plan_rejects_stale_transfer_bytes() -> None:
    graph, compiled = _compiled()
    transfers = list(compiled.partition_plan.transfer_edges)
    transfers[0] = replace(transfers[0], bytes_moved=32, cost_estimate=None)
    plan = replace(compiled.partition_plan, transfer_edges=tuple(transfers))

    with pytest.raises(ValueError, match="byte count mismatch"):
        build_runtime_heterogeneous_storage_plan_report(graph, plan)


def test_storage_plan_contract_is_fail_closed() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()

    with pytest.raises(ValueError, match="contract mismatch"):
        replace(report, execution_policy="may_allocate")
    with pytest.raises(ValueError, match="blocked surfaces changed"):
        replace(report, blocked_execution_surfaces=())
    with pytest.raises(ValueError, match="event count mismatch"):
        replace(report, event_count=report.event_count + 1)
    with pytest.raises(ValueError, match="issues must be derived"):
        replace(report, slots=(replace(report.slots[0], non_overlapping=False), *report.slots[1:]))


def test_storage_plan_rejects_missing_slot_membership() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    reused = report.slots[0]
    truncated = replace(
        reused,
        storage_ids=(reused.storage_ids[1],),
        total_storage_bytes=reused.bytes_reserved,
        reuse_savings_bytes=0,
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        replace(report, slots=(truncated, *report.slots[1:]))


def test_storage_lifetime_rejects_tampered_physical_shape() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()
    blocked = next(item for item in report.lifetimes if item.layout is LayoutKind.BLOCKED)

    with pytest.raises(ValueError, match="physical element count mismatch"):
        replace(blocked, physical_shape=(3, 3))


def test_storage_plan_matches_golden() -> None:
    report = build_current_runtime_heterogeneous_storage_plan_report()

    assert dump_runtime_heterogeneous_storage_plan_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_storage_plan_example_emits_only_public_metadata() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_heterogeneous_storage_plan.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    for forbidden in (
        '"raw_tensor_values"',
        '"runtime_handle"',
        '"device_id"',
        '"memory_address"',
        '"host_path"',
        '"generated_code"',
    ):
        assert forbidden not in completed.stdout


def test_storage_plan_schema_and_golden_are_closed() -> None:
    schema: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    golden: dict[str, Any] = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_HETEROGENEOUS_STORAGE_PLAN_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["storage_contract"]["const"] == (
        RUNTIME_HETEROGENEOUS_STORAGE_PLAN_CONTRACT
    )
    assert schema["properties"]["lifetimes"]["maxItems"] == (
        MAX_RUNTIME_HETEROGENEOUS_STORAGE_LIFETIMES
    )
    assert schema["properties"]["slots"]["maxItems"] == (
        MAX_RUNTIME_HETEROGENEOUS_STORAGE_SLOTS
    )
    assert sorted(golden) == sorted(schema["required"])
    _assert_objects_fail_closed(schema)
    serialized_schema = json.dumps(schema, sort_keys=True)
    for forbidden in (
        '"raw_tensor_values"',
        '"runtime_handle"',
        '"device_id"',
        '"memory_address"',
        '"host_path"',
        '"generated_code"',
    ):
        assert forbidden not in serialized_schema


def test_storage_plan_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_heterogeneous_storage_plan_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_HETEROGENEOUS_STORAGE_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0298-runtime-heterogeneous-storage-plan.md"),
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
