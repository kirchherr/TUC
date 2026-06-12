from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.runtime_systolic_tensor_store_evidence import (
    build_systolic_tensor_store_evidence_report,
)
from tuc import (
    LayoutKind,
    MemoryDomainKind,
    dump_runtime_tensor_store_evidence_report,
    runtime_tensor_store_evidence_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/runtime_tensor_store_evidence/proof_of_systolic_execution.json"
)


def test_systolic_tensor_store_evidence_records_planned_placement() -> None:
    report = build_systolic_tensor_store_evidence_report()
    records = {record.tensor_name: record for record in report.records}

    assert report.passed
    assert report.issues == ()
    assert records["lhs"].planned_backend == "external_input"
    assert records["lhs"].planned_memory_domain is MemoryDomainKind.HOST_RAM
    assert records["lhs"].planned_layout is LayoutKind.ROW_MAJOR
    assert records["projection"].planned_backend == "systolic-sim"
    assert records["projection"].planned_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert records["projection"].planned_layout is LayoutKind.BLOCKED
    assert records["projection"].placement_source == "partition_plan"
    assert records["activated"].planned_backend == "reference-cpu"
    assert records["activated"].planned_memory_domain is MemoryDomainKind.HOST_RAM
    assert records["activated"].planned_layout is LayoutKind.ROW_MAJOR
    assert all(record.raw_value_status == "omitted_by_policy" for record in report.records)


def test_systolic_tensor_store_evidence_dump_matches_golden() -> None:
    report = build_systolic_tensor_store_evidence_report()

    assert dump_runtime_tensor_store_evidence_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_systolic_tensor_store_evidence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_systolic_tensor_store_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert '"planned_backend": "systolic-sim"' in completed.stdout
    assert '"planned_memory_domain": "device_sram"' in completed.stdout
    assert '"planned_layout": "blocked"' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_systolic_tensor_store_evidence_golden_shape() -> None:
    report = build_systolic_tensor_store_evidence_report()
    payload = runtime_tensor_store_evidence_report_to_dict(report)

    assert payload["graph_name"] == "proof_of_systolic_execution"
    assert payload["expected_record_count"] == 4
    assert payload["record_count"] == 4
    assert payload["raw_value_policy"] == "omitted_by_policy"
