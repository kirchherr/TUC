"""Emit a diagnostic workload-scope report."""

from tuc import (
    WorkloadScope,
    build_workload_scope_report,
    dump_workload_scope_report,
)


def main() -> None:
    report = build_workload_scope_report(
        "phase1_workload_scope_candidate",
        scopes=(
            WorkloadScope(
                scope_id="phase1_mlp_matmul_64x64",
                operation_family="matmul",
                shape_profile_id="square_64x64",
                dtype_policy_id="float64_reference",
                problem_size_min=4096,
                problem_size_max=4096,
                correctness_reference_id="numpy_reference_matmul",
            ),
        ),
    )
    print(dump_workload_scope_report(report), end="")


if __name__ == "__main__":
    main()
