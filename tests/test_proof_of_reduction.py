from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_GOLDEN_PROOF = Path(__file__).parent / "golden" / "proofs" / "proof_of_reduction.txt"


def test_proof_of_reduction_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_reduction.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "== input graph ==" in completed.stdout
    assert "== hac-ir ==" in completed.stdout
    assert "linear_projection -> linear-sim" in completed.stdout
    assert "row_reduction -> linear-sim" in completed.stdout
    assert "digital_activation -> gpu" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
    assert completed.stdout.rstrip("\n") == _GOLDEN_PROOF.read_text(
        encoding="utf-8"
    ).rstrip("\n")
