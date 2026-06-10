from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.phase1_ir_pipeline import build_graph as build_phase1_graph
from examples.proof_of_abstraction import build_graph as build_proof_graph
from examples.proof_of_execution import build_graph as build_execution_proof_graph
from examples.proof_of_reduction import build_graph as build_reduction_proof_graph
from examples.proof_of_softmax import build_graph as build_softmax_proof_graph
from examples.proof_of_systolic_execution import (
    build_graph as build_systolic_proof_graph,
)
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, IRStage

_GOLDEN_DIR = Path(__file__).parent / "golden" / "hac_ir"


@pytest.mark.parametrize(
    ("fixture_name", "graph_builder"),
    (
        ("proof_of_abstraction.txt", build_proof_graph),
        ("proof_of_reduction.txt", build_reduction_proof_graph),
        ("proof_of_softmax.txt", build_softmax_proof_graph),
        ("proof_of_execution.txt", build_execution_proof_graph),
        ("proof_of_systolic_execution.txt", build_systolic_proof_graph),
        ("phase1_mlp_block.txt", build_phase1_graph),
    ),
)
def test_hac_ir_dump_matches_golden(
    fixture_name: str,
    graph_builder: Callable[[], ComputeGraph],
) -> None:
    expected = (_GOLDEN_DIR / fixture_name).read_text(encoding="utf-8").rstrip("\n")

    assert _dump_hac_ir(graph_builder()) == expected


def _dump_hac_ir(graph: ComputeGraph) -> str:
    backend = LinearAlgebraSimulatorBackend()
    compiled = compile_graph(graph, [backend.capability])
    return compiled.dump(IRStage.HAC_IR)
