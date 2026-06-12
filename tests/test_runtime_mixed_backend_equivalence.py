from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from tuc import (
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    dump_runtime_backend_equivalence_report,
)

GOLDEN_PATH = Path("tests/golden/runtime_backend_equivalence/mixed_accelerators.json")


def test_runtime_mixed_backend_equivalence_passes() -> None:
    report = build_mixed_backend_equivalence_report()

    assert report.passed
    assert report.issues == ()
    assert report.graph_name == "runtime_mixed_backend_equivalence"
    assert report.baseline_run_id == "reference_cpu"
    assert report.candidate_run_id == "mixed_accelerators"
    assert len(report.runs) == 2
    baseline, candidate = report.runs
    assert baseline.planned_backend_sequence == (
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
    )
    assert candidate.planned_backend_sequence == (
        "systolic-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    )
    assert baseline.output_tensor_names == ("activated",)
    assert candidate.output_tensor_names == ("activated",)
    assert baseline.output_metadata_digest == candidate.output_metadata_digest
    assert len(report.comparisons) == 1
    comparison = report.comparisons[0]
    assert comparison.tensor_name == "activated"
    assert comparison.comparison_status == "matched"
    assert comparison.expected_shape == (2,)
    assert comparison.baseline_shape == (2,)
    assert comparison.candidate_shape == (2,)
    assert comparison.baseline_dtype == "float64"
    assert comparison.candidate_dtype == "float64"
    assert comparison.baseline_output_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert comparison.candidate_output_value_status == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS


def test_runtime_mixed_backend_equivalence_dump_matches_golden() -> None:
    assert dump_runtime_backend_equivalence_report(
        build_mixed_backend_equivalence_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_mixed_backend_equivalence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_mixed_backend_equivalence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_mixed_backend_equivalence" in completed.stdout
    assert '"reference-cpu"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert '"comparison_status": "matched"' in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
