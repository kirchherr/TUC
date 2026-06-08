from __future__ import annotations

import subprocess
import sys


def test_proof_of_abstraction_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_abstraction.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "== input graph ==" in completed.stdout
    assert "== hac-ir ==" in completed.stdout
    assert "linear_projection -> linear-sim" in completed.stdout
    assert "digital_activation -> gpu" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
