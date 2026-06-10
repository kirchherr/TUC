from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.proof_of_execution import run_proof

_GOLDEN_PROOF = Path(__file__).parent / "golden" / "proofs" / "proof_of_execution.txt"


def test_proof_of_execution_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_execution.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "== runtime plan ==" in completed.stdout
    assert "== execution trace ==" in completed.stdout
    assert "executor_contract = \"runtime_executor.trusted_backend.v0\"" in (
        completed.stdout
    )
    assert "linear_projection planned_backend=linear-sim executor_backend=linear-sim" in (
        completed.stdout
    )
    assert (
        "activation planned_backend=reference-cpu executor_backend=reference-cpu"
        in completed.stdout
    )
    assert completed.stdout.rstrip().endswith("PASS")
    assert completed.stdout.rstrip("\n") == _GOLDEN_PROOF.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_proof_of_execution_result_is_checked_against_reference() -> None:
    report = run_proof()

    assert report.passed
    assert report.compiled.partition_plan.backend_for("linear_projection") == "linear-sim"
    assert report.compiled.partition_plan.backend_for("row_reduction") == "linear-sim"
    assert report.compiled.partition_plan.backend_for("activation") == "reference-cpu"
    assert report.execution.trace.steps[-1].output_tensors == ("activated",)
