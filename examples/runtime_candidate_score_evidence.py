"""Emit Runtime Candidate Score Evidence v0."""

from tuc import (
    ComputeGraph,
    ComputeOperation,
    OperationKind,
    TensorRef,
    build_runtime_candidate_score_evidence_report,
    compile_graph,
    dump_runtime_candidate_score_evidence_report,
)
from tuc.backends import BackendCapability
from tuc.ir import MemoryDomainKind
from tuc.runtime import (
    RuntimeCandidateScoreEvidenceReport,
    TransferCostProfile,
)


def build_profiled_candidate_score_evidence_report() -> RuntimeCandidateScoreEvidenceReport:
    """Build the current runtime candidate score evidence report."""

    graph = _candidate_score_graph()
    backends = _candidate_score_backends()
    transfer_profile = _candidate_score_transfer_profile()
    default_result = compile_graph(
        graph,
        backends,
        transfer_cost_profile=transfer_profile,
    )
    scored_result = compile_graph(
        graph,
        backends,
        transfer_cost_profile=transfer_profile,
        include_candidate_scores=True,
    )
    compiler_decision_scores = tuple(
        score
        for report in scored_result.decision_report.operation_reports
        for score in report.candidate_scores
    )
    return build_runtime_candidate_score_evidence_report(
        default_plan=default_result.partition_plan,
        scored_plan=scored_result.partition_plan,
        compiler_decision_candidate_scores=compiler_decision_scores,
    )


def main() -> None:
    print(
        dump_runtime_candidate_score_evidence_report(
            build_profiled_candidate_score_evidence_report()
        ),
        end="",
    )


def _candidate_score_graph() -> ComputeGraph:
    lhs = TensorRef("lhs", (4, 4))
    rhs = TensorRef("rhs", (4, 4))
    projection = TensorRef("projection_out", (4, 4))
    activated = TensorRef("activated", (4, 4))
    return ComputeGraph(
        name="runtime_candidate_score_evidence",
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


def _candidate_score_backends() -> tuple[BackendCapability, ...]:
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


def _candidate_score_transfer_profile() -> TransferCostProfile:
    return TransferCostProfile.from_manifest(
        {
            "name": "candidate_score_profile",
            "fallback": {
                "bandwidth_gb_s": 16.0,
                "base_latency_ns": 20_000.0,
                "energy_pj_per_byte": 100.0,
            },
            "edges": (
                {
                    "source_domain": "analog_weight_bank",
                    "target_domain": "gpu_hbm",
                    "bandwidth_gb_s": 64.0,
                    "base_latency_ns": 5_000.0,
                    "energy_pj_per_byte": 20.0,
                },
            ),
        }
    )


if __name__ == "__main__":
    main()
