from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.triton_metadata_adapter import build_metadata
from examples.triton_mvp_metadata import build_metadata as build_mvp_metadata
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.compiler.pipeline import CompilationResult
from tuc.ir import IRStage


@pytest.mark.parametrize(
    ("fixture_path", "artifact_builder"),
    (
        (
            Path("frontend") / "triton_metadata_intake.txt",
            lambda: build_metadata().intake_report().dump(),
        ),
        (
            Path("hac_ir") / "triton_metadata_mlp.txt",
            lambda: _compiled_frontend_graph().dump(IRStage.HAC_IR),
        ),
        (
            Path("runtime_plans") / "triton_metadata_mlp.txt",
            lambda: _compiled_frontend_graph().dump_runtime_plan(),
        ),
        (
            Path("compiler_decisions") / "triton_metadata_mlp.txt",
            lambda: _compiled_frontend_graph().dump_decision_report(),
        ),
        (
            Path("frontend") / "triton_metadata_mvp_families_intake.txt",
            lambda: build_mvp_metadata().intake_report().dump(),
        ),
        (
            Path("hac_ir") / "triton_metadata_mvp_families.txt",
            lambda: _compiled_mvp_frontend_graph().dump(IRStage.HAC_IR),
        ),
        (
            Path("runtime_plans") / "triton_metadata_mvp_families.txt",
            lambda: _compiled_mvp_frontend_graph().dump_runtime_plan(),
        ),
        (
            Path("compiler_decisions") / "triton_metadata_mvp_families.txt",
            lambda: _compiled_mvp_frontend_graph().dump_decision_report(),
        ),
    ),
)
def test_triton_frontend_artifact_matches_golden(
    fixture_path: Path,
    artifact_builder: Callable[[], str],
) -> None:
    expected = (Path(__file__).parent / "golden" / fixture_path).read_text(
        encoding="utf-8"
    ).rstrip("\n")

    assert artifact_builder() == expected


def _compiled_frontend_graph() -> CompilationResult:
    graph = build_metadata().to_compute_graph()
    return compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])


def _compiled_mvp_frontend_graph() -> CompilationResult:
    graph = build_mvp_metadata().to_compute_graph()
    return compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
