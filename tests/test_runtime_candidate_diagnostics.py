from __future__ import annotations

import pytest

from tuc.backends.base import BackendCapability
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph, ComputeOperation, OperationKind, TensorRef
from tuc.ir.memory import LayoutKind, MemoryDomainKind
from tuc.runtime import CandidateScore, partition_graph


def test_candidate_scores_are_opt_in_diagnostics() -> None:
    plan = partition_graph(_candidate_graph(), _candidate_backends())

    assert plan.candidate_scores == ()


def test_candidate_scores_explain_selected_and_rejected_candidates() -> None:
    plan = partition_graph(
        _candidate_graph(),
        _candidate_backends(),
        include_candidate_scores=True,
    )

    assert len(plan.candidate_scores) == 4
    projection_analog, projection_gpu, activation_analog, activation_gpu = plan.candidate_scores

    assert projection_analog.selected is True
    assert projection_analog.backend_name == "analog"
    assert projection_analog.selection_stage == "supported"
    assert projection_analog.transfer_score == 0
    assert projection_analog.transfer_score_unit == "bytes"

    assert projection_gpu.selected is False
    assert projection_gpu.backend_name == "gpu"
    assert projection_gpu.transfer_score == 0

    assert activation_analog.selected is True
    assert activation_analog.transfer_score == 0

    assert activation_gpu.selected is False
    assert activation_gpu.transfer_score == 4 * 4 * 4
    assert activation_gpu.transfer_bytes == 4 * 4 * 4
    assert activation_gpu.memory_domain is MemoryDomainKind.GPU_HBM


def test_candidate_scores_reach_compiler_decision_report_when_enabled() -> None:
    result = compile_graph(
        _candidate_graph(),
        _candidate_backends(),
        include_candidate_scores=True,
    )

    projection, activation = result.decision_report.operation_reports
    assert len(projection.candidate_scores) == 2
    assert len(activation.candidate_scores) == 2
    assert "candidate_scores {" in result.dump_decision_report()
    assert "candidate_scores {" in result.dump_runtime_plan()


def test_candidate_score_rejects_unsafe_diagnostic_names() -> None:
    with pytest.raises(ValueError, match="safe runtime-plan name"):
        CandidateScore(
            operation_name="bad operation",
            backend_name="gpu",
            selection_stage="supported",
            selected=True,
            transfer_score=0,
            transfer_score_unit="bytes",
            transfer_bytes=0,
            layout_conversion_bytes=0,
            preferred_memory_domain_match=False,
            memory_domain=MemoryDomainKind.GPU_HBM,
            produced_layout=LayoutKind.ROW_MAJOR,
        )


def test_candidate_score_rejects_unsupported_score_unit() -> None:
    with pytest.raises(ValueError, match="transfer_score_unit"):
        CandidateScore(
            operation_name="projection",
            backend_name="gpu",
            selection_stage="supported",
            selected=True,
            transfer_score=0,
            transfer_score_unit="cycles",
            transfer_bytes=0,
            layout_conversion_bytes=0,
            preferred_memory_domain_match=False,
            memory_domain=MemoryDomainKind.GPU_HBM,
            produced_layout=LayoutKind.ROW_MAJOR,
        )


def test_candidate_score_flag_must_be_boolean() -> None:
    with pytest.raises(TypeError, match="include_candidate_scores must be bool"):
        partition_graph(
            _candidate_graph(),
            _candidate_backends(),
            include_candidate_scores="yes",  # type: ignore[arg-type]
        )


def _candidate_graph() -> ComputeGraph:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    projection = TensorRef("projection_out", (4, 4))
    activated = TensorRef("activated", (4, 4))
    return ComputeGraph(
        name="candidate_diagnostics",
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


def _candidate_backends() -> tuple[BackendCapability, ...]:
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
    return (analog, gpu)
