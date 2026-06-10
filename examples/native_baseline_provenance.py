"""Emit a diagnostic native-baseline provenance report."""

from tuc import (
    NativeBaselineProvenance,
    build_native_baseline_provenance_report,
    dump_native_baseline_provenance_report,
)


def main() -> None:
    report = build_native_baseline_provenance_report(
        "phase1_native_baseline_candidate",
        baselines=(
            NativeBaselineProvenance(
                baseline_id="cuda_vendor_matmul_candidate",
                workload_scope_id="phase1_mlp_block",
                implementation_kind="vendor_sample",
                target_platform_id="cuda_sm90",
                source_provenance_id="vendor_sample_manifest",
                toolchain_id="cuda_12_4",
                reproducibility_status="documented_not_executed",
            ),
        ),
    )
    print(dump_native_baseline_provenance_report(report), end="")


if __name__ == "__main__":
    main()
