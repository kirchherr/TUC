"""Emit a diagnostic break-even workload-size report."""

from tuc import (
    BreakEvenWorkloadSize,
    build_break_even_workload_size_report,
    dump_break_even_workload_size_report,
)


def main() -> None:
    report = build_break_even_workload_size_report(
        "phase1_break_even_candidate",
        workloads=(
            BreakEvenWorkloadSize(
                break_even_id="matmul64_break_even",
                workload_scope_id="matmul64_scope",
                planner_overhead_report_id="planner_overhead_report",
                execution_metric_id="median_execution_time_ns",
                amortization_policy_id="single_compile_many_runs",
                break_even_status="estimated_not_validated",
                break_even_problem_size=4096,
            ),
        ),
    )
    print(dump_break_even_workload_size_report(report), end="")


if __name__ == "__main__":
    main()
