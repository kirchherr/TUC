from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.runtime_multi_output_evidence import build_report, run_evidence

GOLDEN_PATH = Path("tests/golden/runtime_multi_output_evidence/current_report.json")


def test_runtime_multi_output_evidence_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"


def test_runtime_multi_output_evidence_records_two_terminal_outputs() -> None:
    evidence = run_evidence()

    assert evidence.output_manifest.passed
    assert evidence.reference_correctness.passed
    assert tuple(output.tensor_name for output in evidence.output_manifest.outputs) == (
        "row_sum",
        "positive_projection",
    )
    assert tuple(
        comparison.tensor_name
        for comparison in evidence.reference_correctness.comparisons
    ) == (
        "row_sum",
        "positive_projection",
    )
    assert tuple(output.producer_id for output in evidence.output_manifest.outputs) == (
        "row_reduction",
        "positive_branch",
    )
    assert evidence.reference_correctness.reference_tensor_names == (
        "positive_projection",
        "row_sum",
    )


def test_runtime_multi_output_evidence_example_runs_without_raw_values() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_multi_output_evidence.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    parsed = json.loads(completed.stdout)

    assert parsed["evidence_fixture"] == "runtime_multi_output_evidence.v0"
    assert parsed["output_manifest"]["output_count"] == 2
    assert parsed["reference_correctness"]["comparison_count"] == 2
    assert parsed["reference_correctness"]["passed"] is True
    assert "omitted_by_policy" in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
