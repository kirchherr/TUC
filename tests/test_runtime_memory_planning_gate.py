from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.runtime_allocation_plan import build_current_runtime_allocation_plan_report
from examples.runtime_memory_budget import build_current_runtime_memory_budget_report
from examples.runtime_memory_planning_gate import (
    RuntimeMemoryPlanningGateError,
    build_gate_report,
)
from tuc import (
    MemoryDomainKind,
    RuntimeAllocationIssue,
    RuntimeAllocationPlanReport,
    RuntimeMemoryBudgetReport,
    RuntimeMemoryDomainBudget,
    build_runtime_memory_budget_report,
)

_GOLDEN = Path("tests/golden/runtime_memory_planning_gate/current_gate.txt")


def test_runtime_memory_planning_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'allocation_plan = "passed"' in report
    assert 'memory_budget = "passed"' in report
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


def test_runtime_memory_planning_gate_rejects_graph_mismatch() -> None:
    memory_budget = build_current_runtime_memory_budget_report()
    mismatched = RuntimeMemoryBudgetReport(
        graph_name="other_graph",
        operation_count=memory_budget.operation_count,
        source_allocation_contract=memory_budget.source_allocation_contract,
        source_allocation_schema_version=memory_budget.source_allocation_schema_version,
        source_allocation_issue_count=memory_budget.source_allocation_issue_count,
        budgets=memory_budget.budgets,
        usages=memory_budget.usages,
        issues=memory_budget.issues,
    )

    with pytest.raises(RuntimeMemoryPlanningGateError, match="graph mismatch"):
        build_gate_report(memory_budget_report=mismatched)


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
