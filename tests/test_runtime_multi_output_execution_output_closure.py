from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from examples.runtime_multi_output_execution_output_closure import (
    build_multi_output_execution_closure_evidence_reports,
    build_multi_output_execution_output_closure_report,
)
from tuc import (
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS,
    dump_runtime_execution_output_closure_report,
)

GOLDEN_PATH = Path(
    "tests/golden/runtime_execution_output_closure/multi_output_execution.json"
)


def test_multi_output_execution_output_closure_passes() -> None:
    report = build_multi_output_execution_output_closure_report()

    assert report.graph_name == "multi_output_execution"
    assert report.passed
    assert report.issues == ()
    assert report.check_count == 2
    assert tuple(check.evidence_kind for check in report.checks) == (
        RUNTIME_EXECUTION_OUTPUT_CLOSURE_REQUIRED_EVIDENCE_KINDS
    )
    assert tuple(check.source_item_count for check in report.checks) == (2, 2)
    assert tuple(check.receipt_item_count for check in report.checks) == (2, 2)
    assert tuple(check.bundle_item_count for check in report.checks) == (2, 2)


def test_multi_output_execution_output_closure_binds_two_public_outputs() -> None:
    evidence = build_multi_output_execution_closure_evidence_reports()

    assert tuple(output.public_name for output in evidence.output_contract.public_outputs) == (
        "api_positive_projection",
        "api_row_sums",
    )
    assert tuple(output.tensor_name for output in evidence.output_contract.public_outputs) == (
        "positive_projection",
        "row_sum",
    )
    assert evidence.public_output_bundle.public_output_names == (
        "api_positive_projection",
        "api_row_sums",
    )
    assert evidence.public_output_bundle.tensor_names == (
        "positive_projection",
        "row_sum",
    )


def test_multi_output_execution_output_closure_dump_matches_golden() -> None:
    assert dump_runtime_execution_output_closure_report(
        build_multi_output_execution_output_closure_report()
    ) == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"


def test_multi_output_execution_output_closure_example_runs_without_raw_values() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_multi_output_execution_output_closure.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["graph_name"] == "multi_output_execution"
    assert payload["passed"] is True
    assert payload["check_count"] == 2
    assert payload["source_output_contract_item_count"] == 2
    assert payload["source_public_output_bundle_item_count"] == 2
    assert "omitted_by_policy" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_values" not in completed.stdout
    assert "python_source" not in completed.stdout


def test_multi_output_execution_output_closure_docs_are_linked() -> None:
    golden_path = (
        "tests/golden/runtime_execution_output_closure/multi_output_execution.json"
    )

    for path in (
        Path("docs/RUNTIME_EXECUTION_OUTPUT_CLOSURE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0205-runtime-execution-output-closure-report.md"),
        Path("rfcs/0207-runtime-multi-output-execution-output-closure.md"),
    ):
        assert golden_path in path.read_text(encoding="utf-8")
