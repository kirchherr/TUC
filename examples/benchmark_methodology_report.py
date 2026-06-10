"""Emit a diagnostic benchmark-methodology report."""

from tuc import (
    BenchmarkMethodology,
    build_benchmark_methodology_report,
    dump_benchmark_methodology_report,
)


def main() -> None:
    report = build_benchmark_methodology_report(
        "phase1_benchmark_methodology_candidate",
        methodologies=(
            BenchmarkMethodology(
                methodology_id="phase1_cpu_baseline_methodology",
                workload_scope_id="phase1_mlp_matmul_64x64",
                measurement_clock="monotonic_ns",
                warmup_iterations=3,
                measurement_iterations=20,
                statistic_policy="min_median_mean",
                isolation_level="process_isolated",
                outlier_policy_id="no_raw_sample_storage",
                reproducibility_policy_id="docker_dev_container",
            ),
        ),
    )
    print(dump_benchmark_methodology_report(report), end="")


if __name__ == "__main__":
    main()
