from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_allocation_request_manifest import (
    build_current_runtime_allocation_request_manifest_report,
)
from examples.runtime_buffer_lifetime import build_current_runtime_buffer_lifetime_report
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from examples.runtime_memory_planning_gate import (
    RuntimeMemoryPlanningGateError,
    build_gate_report,
)
from tuc import (
    MemoryDomainKind,
    RuntimeAllocationIssue,
    RuntimeAllocationPlanReport,
    RuntimeBufferLifetimeIssue,
    RuntimeBufferLifetimeReport,
    RuntimeMemoryBudgetReport,
    RuntimeMemoryDomainBudget,
    build_runtime_allocation_request_manifest_report,
    build_runtime_memory_budget_report,
)

_GOLDEN = Path("tests/golden/runtime_memory_planning_gate/current_gate.txt")


def test_runtime_memory_planning_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'buffer_lifetime = "passed"' in report
    assert 'allocation_plan = "passed"' in report
    assert 'allocation_lifetime_binding = "verified"' in report
    assert 'memory_budget = "passed"' in report
    assert 'memory_budget_allocation_binding = "verified"' in report
    assert 'allocation_request_manifest = "passed"' in report
    assert 'allocation_request_manifest_binding = "verified"' in report
    assert 'allocation_request_handle_policy = "no_runtime_handles"' in report
    assert report.rstrip().endswith('status = "PASS"\n}')


def test_runtime_memory_planning_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_memory_planning_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")


def test_runtime_memory_planning_gate_rejects_failed_allocation_plan() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    bad_slots = (
        replace(allocation.slots[0], live_ranges_non_overlapping=False),
        *allocation.slots[1:],
    )
    failed = RuntimeAllocationPlanReport(
        graph_name=allocation.graph_name,
        operation_count=allocation.operation_count,
        source_lifetime_contract=allocation.source_lifetime_contract,
        source_lifetime_schema_version=allocation.source_lifetime_schema_version,
        source_lifetime_issue_count=allocation.source_lifetime_issue_count,
        source_lifetime_metadata_digest=allocation.source_lifetime_metadata_digest,
        bindings=allocation.bindings,
        slots=bad_slots,
        issues=(
            RuntimeAllocationIssue(
                subject="slot_001",
                issue_code="allocation_slot_lifetimes_overlap",
            ),
        ),
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="allocation plan failed"):
        build_gate_report(allocation_report=failed)


def test_runtime_memory_planning_gate_rejects_failed_buffer_lifetime() -> None:
    lifetime = build_current_runtime_buffer_lifetime_report()
    bad_lifetime = replace(lifetime.lifetimes[0], reuse_group_id="missing_group")
    failed = RuntimeBufferLifetimeReport(
        graph_name=lifetime.graph_name,
        operation_count=lifetime.operation_count,
        lifetimes=(bad_lifetime, *lifetime.lifetimes[1:]),
        reuse_groups=lifetime.reuse_groups,
        issues=(
            RuntimeBufferLifetimeIssue(
                subject=bad_lifetime.tensor_name,
                issue_code="reuse_group_missing",
            ),
        ),
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="buffer lifetime failed"):
        build_gate_report(lifetime_report=failed)


def test_runtime_memory_planning_gate_rejects_failed_memory_budget() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    failed = build_runtime_memory_budget_report(
        allocation,
        (
            RuntimeMemoryDomainBudget(
                budget_id="tiny_host_ram_budget",
                memory_domain=MemoryDomainKind.HOST_RAM,
                max_reserved_bytes=64,
                max_peak_live_bytes=192,
            ),
        ),
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="memory budget failed"):
        build_gate_report(memory_budget_report=failed)


def test_runtime_memory_planning_gate_rejects_failed_request_manifest() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    memory_budget = build_current_runtime_memory_budget_report()
    stale_budget = replace(
        memory_budget,
        source_allocation_metadata_digest="sha256:" + "1" * 64,
    )
    failed = build_runtime_allocation_request_manifest_report(
        allocation,
        stale_budget,
    )

    with pytest.raises(
        RuntimeMemoryPlanningGateError,
        match="allocation request manifest failed",
    ):
        build_gate_report(request_manifest_report=failed)


def test_runtime_memory_planning_gate_rejects_graph_mismatch() -> None:
    memory_budget = build_current_runtime_memory_budget_report()
    mismatched = RuntimeMemoryBudgetReport(
        graph_name="other_graph",
        operation_count=memory_budget.operation_count,
        source_allocation_contract=memory_budget.source_allocation_contract,
        source_allocation_schema_version=memory_budget.source_allocation_schema_version,
        source_allocation_issue_count=memory_budget.source_allocation_issue_count,
        source_allocation_metadata_digest=memory_budget.source_allocation_metadata_digest,
        budgets=memory_budget.budgets,
        usages=memory_budget.usages,
        issues=memory_budget.issues,
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="graph mismatch"):
        build_gate_report(memory_budget_report=mismatched)


def test_runtime_memory_planning_gate_rejects_lifetime_digest_mismatch() -> None:
    allocation = build_current_runtime_allocation_plan_report()
    mismatched = replace(
        allocation,
        source_lifetime_metadata_digest="sha256:" + "1" * 64,
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="lifetime digest"):
        build_gate_report(allocation_report=mismatched)


def test_runtime_memory_planning_gate_rejects_allocation_digest_mismatch() -> None:
    memory_budget = build_current_runtime_memory_budget_report()
    mismatched = replace(
        memory_budget,
        source_allocation_metadata_digest="sha256:" + "1" * 64,
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="allocation digest"):
        build_gate_report(memory_budget_report=mismatched)


def test_runtime_memory_planning_gate_rejects_request_manifest_digest_mismatch() -> None:
    request_manifest = build_current_runtime_allocation_request_manifest_report()
    mismatched = replace(
        request_manifest,
        source_allocation_metadata_digest="sha256:" + "1" * 64,
        source_memory_budget_allocation_digest="sha256:" + "1" * 64,
    )

    with pytest.raises(
        RuntimeMemoryPlanningGateError,
        match="request manifest allocation digest",
    ):
        build_gate_report(request_manifest_report=mismatched)


def test_runtime_memory_planning_gate_rejects_request_manifest_payload_mismatch() -> None:
    request_manifest = build_current_runtime_allocation_request_manifest_report()
    bad_request = replace(
        request_manifest.requests[0],
        dtype="float64",
    )
    mismatched = replace(
        request_manifest,
        requests=(bad_request, *request_manifest.requests[1:]),
    )

    with pytest.raises(
        RuntimeMemoryPlanningGateError,
        match="request manifest slot payload",
    ):
        build_gate_report(request_manifest_report=mismatched)


def test_runtime_memory_planning_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/runtime_memory_planning_gate.py"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/RUNTIME_MEMORY_PLANNING_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0104-runtime-memory-planning-gate.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")
