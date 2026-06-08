from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.phase1_ir_pipeline import build_graph as build_phase1_graph
from examples.proof_of_abstraction import run_proof as run_abstraction_proof
from examples.proof_of_reduction import run_proof as run_reduction_proof
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph

_GOLDEN_DIR = Path(__file__).parent / "golden" / "compiler_decisions"


@pytest.mark.parametrize(
    ("fixture_name", "report_builder"),
    (
        (
            "proof_of_abstraction.txt",
            lambda: run_abstraction_proof().compiled.dump_decision_report(),
        ),
        (
            "proof_of_reduction.txt",
            lambda: run_reduction_proof().compiled.dump_decision_report(),
        ),
        (
            "phase1_mlp_block.txt",
            lambda: compile_graph(
                build_phase1_graph(),
                [LinearAlgebraSimulatorBackend().capability],
            ).dump_decision_report(),
        ),
    ),
)
def test_compiler_decision_report_matches_golden(
    fixture_name: str,
    report_builder: Callable[[], str],
) -> None:
    expected = (_GOLDEN_DIR / fixture_name).read_text(encoding="utf-8").rstrip("\n")

    assert report_builder() == expected
