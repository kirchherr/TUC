"""Emit a diagnostic performance acceptance criteria report."""

from tuc import (
    PerformanceAcceptanceCriteria,
    build_performance_acceptance_criteria_report,
    dump_performance_acceptance_criteria_report,
)


def main() -> None:
    report = build_performance_acceptance_criteria_report(
        "native_performance_proposal",
        criteria=(
            PerformanceAcceptanceCriteria(
                criteria_id="native_matmul64_acceptance_criteria",
                workload_scope_id="matmul64_scope",
                threshold_policy_id="near_native_threshold_policy",
                correctness_evidence_id="matmul64_correctness_goldens",
                benchmark_methodology_id="ci_median_iqr_methodology",
                native_baseline_comparison_id="not_supplied",
                planner_overhead_report_id="planner_overhead_report",
                break_even_workload_size_id="not_supplied",
                leaky_abstraction_report_id="leaky_abstraction_report",
                executable_security_review_id="backend_execution_security_review",
                criteria_status="reviewed_not_accepted",
            ),
        ),
    )
    print(dump_performance_acceptance_criteria_report(report), end="")


if __name__ == "__main__":
    main()
