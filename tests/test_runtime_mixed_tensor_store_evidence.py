from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.runtime_mixed_tensor_store_evidence import (
    build_mixed_tensor_store_evidence_report,
)
from tuc import (
    LayoutKind,
    MemoryDomainKind,
    dump_runtime_tensor_store_evidence_report,
    runtime_tensor_store_evidence_report_to_dict,
)

GOLDEN_PATH = Path(
    "tests/golden/runtime_tensor_store_evidence/runtime_mixed_backend_equivalence.json"
)


def test_mixed_tensor_store_evidence_records_planned_placement() -> None:
    report = build_mixed_tensor_store_evidence_report()
    records = {record.tensor_name: record for record in report.records}

    assert report.graph_name == "runtime_mixed_backend_equivalence"
    assert report.passed
    assert report.issues == ()
    assert tuple(record.tensor_name for record in report.records) == (
        "lhs",
        "rhs",
        "projection",
        "normalized",
        "row_sum",
        "activated",
    )
    assert records["lhs"].planned_backend == "external_input"
    assert records["lhs"].planned_memory_domain is MemoryDomainKind.HOST_RAM
    assert records["lhs"].planned_layout is LayoutKind.ROW_MAJOR
    assert records["projection"].planned_backend == "systolic-sim"
    assert records["projection"].planned_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert records["projection"].planned_layout is LayoutKind.BLOCKED
    assert records["projection"].placement_source == "partition_plan"
    assert records["normalized"].planned_backend == "vector-sim"
    assert records["normalized"].planned_memory_domain is MemoryDomainKind.DEVICE_SRAM
    assert records["normalized"].planned_layout is LayoutKind.ROW_MAJOR
    assert records["row_sum"].planned_backend == "vector-sim"
    assert records["activated"].planned_backend == "vector-sim"
    assert all(record.raw_value_status == "omitted_by_policy" for record in report.records)
    assert all(record.readonly for record in report.records)


def test_mixed_tensor_store_evidence_dump_matches_golden() -> None:
    report = build_mixed_tensor_store_evidence_report()

    assert dump_runtime_tensor_store_evidence_report(report) == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )


def test_mixed_tensor_store_evidence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_mixed_tensor_store_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == (
        GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    )
    assert '"planned_backend": "systolic-sim"' in completed.stdout
    assert '"planned_backend": "vector-sim"' in completed.stdout
    assert '"planned_layout": "blocked"' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout


def test_mixed_tensor_store_evidence_golden_shape() -> None:
    report = build_mixed_tensor_store_evidence_report()
    payload = runtime_tensor_store_evidence_report_to_dict(report)

    assert payload["graph_name"] == "runtime_mixed_backend_equivalence"
    assert payload["expected_record_count"] == 6
    assert payload["record_count"] == 6
    assert payload["raw_value_policy"] == "omitted_by_policy"
