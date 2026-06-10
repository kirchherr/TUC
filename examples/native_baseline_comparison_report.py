"""Emit a diagnostic native baseline comparison report."""

from tuc import (
    NativeBaselineComparison,
    build_native_baseline_comparison_report,
    dump_native_baseline_comparison_report,
)


def main() -> None:
    report = build_native_baseline_comparison_report(
        "phase1_native_comparison_candidate",
        comparisons=(
            NativeBaselineComparison(
                comparison_id="matmul64_native_comparison",
                workload_scope_id="matmul64_scope",
                baseline_artifact_id="baseline_report",
                native_artifact_id="native_report",
                comparison_metric_id="median_execution_time_ns",
                summary_policy_id="median_iqr",
                result_status="reported_not_validated",
            ),
        ),
    )
    print(dump_native_baseline_comparison_report(report), end="")


if __name__ == "__main__":
    main()
