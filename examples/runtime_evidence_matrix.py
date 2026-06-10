"""Emit a deterministic runtime evidence matrix for proof review."""

from tuc import (
    RuntimeEvidenceArtifact,
    RuntimeEvidenceGraph,
    RuntimeEvidenceMatrixReport,
    build_runtime_evidence_matrix_report,
    dump_runtime_evidence_matrix_report,
)


def artifact(artifact_kind: str, artifact_id: str) -> RuntimeEvidenceArtifact:
    """Build one explicit review artifact reference."""

    return RuntimeEvidenceArtifact(
        artifact_kind=artifact_kind,
        artifact_id=artifact_id,
    )


def build_matrix_report() -> RuntimeEvidenceMatrixReport:
    """Return the current curated runtime evidence matrix."""

    return build_runtime_evidence_matrix_report(
        "runtime_evidence_matrix_v0",
        (
            RuntimeEvidenceGraph(
                graph_id="proof_of_abstraction",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    artifact("proof_report_golden", "proof_of_abstraction_report"),
                    artifact("hac_ir_golden", "proof_of_abstraction_hac_ir"),
                    artifact("runtime_plan_golden", "proof_of_abstraction_runtime_plan"),
                    artifact(
                        "compiler_decision_golden",
                        "proof_of_abstraction_compiler_decision",
                    ),
                    artifact(
                        "reference_correctness",
                        "proof_of_abstraction_reference_semantics",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_reduction",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    artifact("proof_report_golden", "proof_of_reduction_report"),
                    artifact("hac_ir_golden", "proof_of_reduction_hac_ir"),
                    artifact("runtime_plan_golden", "proof_of_reduction_runtime_plan"),
                    artifact(
                        "compiler_decision_golden",
                        "proof_of_reduction_compiler_decision",
                    ),
                    artifact(
                        "reference_correctness",
                        "proof_of_reduction_reference_semantics",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_softmax",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    artifact("proof_report_golden", "proof_of_softmax_report"),
                    artifact("hac_ir_golden", "proof_of_softmax_hac_ir"),
                    artifact("runtime_plan_golden", "proof_of_softmax_runtime_plan"),
                    artifact(
                        "compiler_decision_golden",
                        "proof_of_softmax_compiler_decision",
                    ),
                    artifact(
                        "reference_correctness",
                        "proof_of_softmax_reference_semantics",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_execution",
                graph_family="objective_alpha_execution",
                source_boundary="typed_compute_graph",
                artifacts=(
                    artifact("proof_report_golden", "proof_of_execution_report"),
                    artifact(
                        "execution_readiness_golden",
                        "proof_of_execution_readiness",
                    ),
                    artifact("execution_trace_golden", "proof_of_execution_trace"),
                    artifact(
                        "reference_correctness",
                        "proof_of_execution_reference_semantics",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="triton_metadata_mvp_families",
                graph_family="triton_metadata_mvp",
                source_boundary="triton_metadata",
                artifacts=(
                    artifact(
                        "frontend_intake_golden",
                        "triton_metadata_mvp_families_intake",
                    ),
                    artifact(
                        "hac_ir_golden",
                        "triton_metadata_mvp_families_hac_ir",
                    ),
                    artifact(
                        "runtime_plan_golden",
                        "triton_metadata_mvp_families_runtime_plan",
                    ),
                    artifact(
                        "compiler_decision_golden",
                        "triton_metadata_mvp_families_compiler_decision",
                    ),
                    artifact(
                        "execution_readiness_golden",
                        "triton_metadata_mvp_families_readiness",
                    ),
                    artifact(
                        "execution_trace_golden",
                        "triton_metadata_mvp_families_trace",
                    ),
                    artifact(
                        "reference_correctness",
                        "triton_metadata_mvp_families_reference_semantics",
                    ),
                ),
            ),
        ),
    )


def build_report() -> str:
    """Return the stable serialized matrix report."""

    return dump_runtime_evidence_matrix_report(build_matrix_report())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
