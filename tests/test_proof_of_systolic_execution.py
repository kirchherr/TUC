from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.proof_of_systolic_execution import run_proof

_GOLDEN_PROOF = (
    Path(__file__).parent / "golden" / "proofs" / "proof_of_systolic_execution.txt"
)
_GOLDEN_READINESS = (
    Path(__file__).parent
    / "golden"
    / "execution_readiness"
    / "proof_of_systolic_execution.txt"
)
_GOLDEN_TRACE = (
    Path(__file__).parent
    / "golden"
    / "execution_traces"
    / "proof_of_systolic_execution.txt"
)


def test_proof_of_systolic_execution_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_systolic_execution.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "proof_id: proof_of_systolic_execution" in completed.stdout
    assert "backend_set: reference-cpu, systolic-sim" in completed.stdout
    assert "systolic_projection -> systolic-sim" in completed.stdout
    assert "host_activation -> reference-cpu" in completed.stdout
    assert "layout_conversions" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
    assert completed.stdout.rstrip("\n") == _GOLDEN_PROOF.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_proof_of_systolic_execution_runtime_evidence_goldens() -> None:
    report = run_proof()

    assert report.readiness.status == "ready"
    assert tuple(step.planned_backend for step in report.readiness.steps) == (
        "systolic-sim",
        "reference-cpu",
    )
    assert tuple(step.operation_name for step in report.execution.trace.steps) == (
        "systolic_projection",
        "host_activation",
    )
    assert report.readiness.dump() == _GOLDEN_READINESS.read_text(
        encoding="utf-8"
    ).rstrip("\n")
    assert report.execution.trace.dump() == _GOLDEN_TRACE.read_text(
        encoding="utf-8"
    ).rstrip("\n")
