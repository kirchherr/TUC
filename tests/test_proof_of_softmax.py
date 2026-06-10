from __future__ import annotations

import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from examples.proof_of_softmax import build_graph, evaluate_graph, proof_inputs, run_proof
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph

_GOLDEN_PROOF = Path(__file__).parent / "golden" / "proofs" / "proof_of_softmax.txt"
_GOLDEN_READINESS = (
    Path(__file__).parent / "golden" / "execution_readiness" / "proof_of_softmax.txt"
)
_GOLDEN_TRACE = (
    Path(__file__).parent / "golden" / "execution_traces" / "proof_of_softmax.txt"
)


def test_proof_of_softmax_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_softmax.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "== proof metadata ==" in completed.stdout
    assert "proof_version: alpha.v1" in completed.stdout
    assert "graph_family: softmax" in completed.stdout
    assert "backend_set: linear-sim, reference-cpu" in completed.stdout
    assert "== input graph ==" in completed.stdout
    assert "== hac-ir ==" in completed.stdout
    assert "== execution readiness ==" in completed.stdout
    assert "== execution trace ==" in completed.stdout
    assert "linear_projection -> linear-sim" in completed.stdout
    assert "row_softmax -> reference-cpu" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
    assert completed.stdout.rstrip("\n") == _GOLDEN_PROOF.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_proof_of_softmax_runtime_evidence_goldens() -> None:
    report = run_proof()

    assert report.readiness.status == "ready"
    assert tuple(step.planned_backend for step in report.readiness.steps) == (
        "linear-sim",
        "reference-cpu",
    )
    assert tuple(step.operation_name for step in report.execution.trace.steps) == (
        "linear_projection",
        "row_softmax",
    )
    assert report.readiness.dump() == _GOLDEN_READINESS.read_text(
        encoding="utf-8"
    ).rstrip("\n")
    assert report.execution.trace.dump() == _GOLDEN_TRACE.read_text(
        encoding="utf-8"
    ).rstrip("\n")


@pytest.mark.parametrize("axis", [True, 2])
def test_softmax_proof_axis_validation_fails_closed(axis: object) -> None:
    graph = build_graph()
    softmax = graph.operations[1]
    bad_softmax = replace(
        softmax,
        attributes={**softmax.attributes, "axis": axis},
    )
    bad_graph = ComputeGraph(
        name=graph.name,
        operations=(graph.operations[0], bad_softmax),
    )

    with pytest.raises((TypeError, ValueError), match="softmax axis"):
        compile_graph(bad_graph, [LinearAlgebraSimulatorBackend().capability])

    with pytest.raises((TypeError, ValueError), match="softmax proof axis|axis is out of bounds"):
        evaluate_graph(bad_graph, proof_inputs())
