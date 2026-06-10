from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.phase1_ir_pipeline import build_graph as build_phase1_graph
from examples.proof_of_abstraction import run_proof as run_abstraction_proof
from examples.proof_of_execution import run_proof as run_execution_proof
from examples.proof_of_reduction import run_proof as run_reduction_proof
from examples.proof_of_softmax import run_proof as run_softmax_proof
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import MemoryDomainKind
from tuc.runtime import RUNTIME_OVERRIDE_SCHEMA_VERSION, RuntimeOverrideSet

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
            "proof_of_softmax.txt",
            lambda: run_softmax_proof().compiled.dump_decision_report(),
        ),
        (
            "proof_of_execution.txt",
            lambda: run_execution_proof().compiled.dump_decision_report(),
        ),
        (
            "phase1_mlp_block.txt",
            lambda: compile_graph(
                build_phase1_graph(),
                [LinearAlgebraSimulatorBackend().capability],
            ).dump_decision_report(),
        ),
        (
            "manual_override_require.txt",
            lambda: _manual_override_decision_report(),
        ),
        (
            "candidate_scores.txt",
            lambda: _candidate_score_decision_report(),
        ),
    ),
)
def test_compiler_decision_report_matches_golden(
    fixture_name: str,
    report_builder: Callable[[], str],
) -> None:
    expected = (_GOLDEN_DIR / fixture_name).read_text(encoding="utf-8").rstrip("\n")

    assert report_builder() == expected


def _manual_override_decision_report() -> str:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    out = TensorRef("out", (4, 4))
    graph = ComputeGraph(
        name="golden_manual_override",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(out,),
                attributes={"max_error_budget": 0.01},
            ),
        ),
    )
    gpu_backend = BackendCapability(
        name="gpu-matmul",
        supported_ops=frozenset({OperationKind.MATMUL}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )
    overrides = RuntimeOverrideSet.from_manifest(
        {
            "schema_version": RUNTIME_OVERRIDE_SCHEMA_VERSION,
            "rules": (
                {
                    "operation_name": "projection",
                    "action": "require_backend",
                    "backend_name": "gpu-matmul",
                },
            ),
        }
    )
    return compile_graph(
        graph,
        [LinearAlgebraSimulatorBackend().capability, gpu_backend],
        runtime_overrides=overrides,
    ).dump_decision_report()


def _candidate_score_decision_report() -> str:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    projection = TensorRef("projection_out", (4, 4))
    activated = TensorRef("activated", (4, 4))
    graph = ComputeGraph(
        name="golden_candidate_scores",
        operations=(
            ComputeOperation(
                name="projection",
                kind=OperationKind.MATMUL,
                inputs=(lhs, rhs),
                outputs=(projection,),
            ),
            ComputeOperation(
                name="activation",
                kind=OperationKind.ELEMENTWISE,
                inputs=(projection,),
                outputs=(activated,),
            ),
        ),
    )
    analog = BackendCapability(
        name="analog",
        supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.ANALOG_WEIGHT_BANK,
    )
    gpu = BackendCapability(
        name="gpu",
        supported_ops=frozenset({OperationKind.MATMUL, OperationKind.ELEMENTWISE}),
        memory_domain=MemoryDomainKind.GPU_HBM,
    )
    return compile_graph(
        graph,
        [analog, gpu],
        include_candidate_scores=True,
    ).dump_decision_report()
