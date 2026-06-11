from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from examples.proof_of_abstraction import run_proof

_GOLDEN_PROOF = Path(__file__).parent / "golden" / "proofs" / "proof_of_abstraction.txt"
_GOLDEN_READINESS = (
    Path(__file__).parent / "golden" / "execution_readiness" / "proof_of_abstraction.txt"
)
_GOLDEN_TRACE = (
    Path(__file__).parent / "golden" / "execution_traces" / "proof_of_abstraction.txt"
)


def test_proof_of_abstraction_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_abstraction.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "== proof metadata ==" in completed.stdout
    assert "proof_version: alpha.v1" in completed.stdout
    assert "graph_family: abstraction" in completed.stdout
    assert "backend_set: linear-sim, reference-cpu" in completed.stdout
    assert "== input graph ==" in completed.stdout
    assert "== hac-ir ==" in completed.stdout
    assert "== execution readiness ==" in completed.stdout
    assert "== execution trace ==" in completed.stdout
    assert "linear_projection -> linear-sim" in completed.stdout
    assert "digital_activation -> reference-cpu" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
    assert completed.stdout.rstrip("\n") == _GOLDEN_PROOF.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_proof_of_abstraction_runtime_evidence_goldens() -> None:
    report = run_proof()

    assert report.readiness.status == "ready"
    assert tuple(step.planned_backend for step in report.readiness.steps) == (
        "linear-sim",
        "reference-cpu",
    )
    assert tuple(step.operation_name for step in report.execution.trace.steps) == (
        "linear_projection",
        "digital_activation",
    )
    assert report.readiness.dump() == _GOLDEN_READINESS.read_text(
        encoding="utf-8"
    ).rstrip("\n")
    assert report.execution.trace.dump() == _GOLDEN_TRACE.read_text(
        encoding="utf-8"
    ).rstrip("\n")
