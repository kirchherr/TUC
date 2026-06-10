"""Emit a diagnostic performance claim threshold policy report."""

from tuc import (
    PerformanceClaimThresholdPolicy,
    build_performance_claim_threshold_policy_report,
    dump_performance_claim_threshold_policy_report,
)


def main() -> None:
    report = build_performance_claim_threshold_policy_report(
        "native_performance_proposal",
        policies=(
            PerformanceClaimThresholdPolicy(
                policy_id="near_native_threshold_policy",
                workload_scope_id="matmul64_scope",
                comparison_metric_id="median_execution_time_ns",
                summary_policy_id="median_iqr",
                threshold_kind="ratio_to_native_at_least",
                threshold_basis_points=9500,
                policy_status="reviewed_not_accepted",
            ),
        ),
    )
    print(dump_performance_claim_threshold_policy_report(report), end="")


if __name__ == "__main__":
    main()
