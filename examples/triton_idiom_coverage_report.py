"""Emit a diagnostic Triton idiom coverage report."""

from tuc.frontend import (
    TritonIdiomCoverage,
    build_triton_idiom_coverage_report,
    dump_triton_idiom_coverage_report,
)


def build_report() -> str:
    report = build_triton_idiom_coverage_report(
        "triton_metadata_mvp_coverage",
        (
            TritonIdiomCoverage(
                idiom_id="metadata_matmul_projection",
                operation_family="matmul",
                metadata_example_id="triton_mvp_metadata",
                intake_golden_id="triton_metadata_mvp_families_intake",
                hac_ir_golden_id="triton_metadata_mvp_families_hac_ir",
                runtime_plan_golden_id="triton_metadata_mvp_families_runtime_plan",
                compiler_decision_golden_id=(
                    "triton_metadata_mvp_families_compiler_decision"
                ),
            ),
            TritonIdiomCoverage(
                idiom_id="metadata_softmax_axis",
                operation_family="softmax",
                metadata_example_id="triton_mvp_metadata",
                intake_golden_id="triton_metadata_mvp_families_intake",
                hac_ir_golden_id="triton_metadata_mvp_families_hac_ir",
                runtime_plan_golden_id="triton_metadata_mvp_families_runtime_plan",
                compiler_decision_golden_id=(
                    "triton_metadata_mvp_families_compiler_decision"
                ),
            ),
            TritonIdiomCoverage(
                idiom_id="metadata_reduction_axis",
                operation_family="reduction",
                metadata_example_id="triton_mvp_metadata",
                intake_golden_id="triton_metadata_mvp_families_intake",
                hac_ir_golden_id="triton_metadata_mvp_families_hac_ir",
                runtime_plan_golden_id="triton_metadata_mvp_families_runtime_plan",
                compiler_decision_golden_id=(
                    "triton_metadata_mvp_families_compiler_decision"
                ),
            ),
            TritonIdiomCoverage(
                idiom_id="metadata_elementwise_activation",
                operation_family="elementwise",
                metadata_example_id="triton_mvp_metadata",
                intake_golden_id="triton_metadata_mvp_families_intake",
                hac_ir_golden_id="triton_metadata_mvp_families_hac_ir",
                runtime_plan_golden_id="triton_metadata_mvp_families_runtime_plan",
                compiler_decision_golden_id=(
                    "triton_metadata_mvp_families_compiler_decision"
                ),
            ),
        ),
    )
    return dump_triton_idiom_coverage_report(report)


if __name__ == "__main__":
    print(build_report(), end="")
