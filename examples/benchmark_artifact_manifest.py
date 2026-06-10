"""Emit a diagnostic benchmark-artifact manifest report."""

from tuc import (
    BenchmarkArtifactReference,
    build_benchmark_artifact_manifest_report,
    dump_benchmark_artifact_manifest_report,
)


def main() -> None:
    report = build_benchmark_artifact_manifest_report(
        "phase1_benchmark_artifact_manifest_candidate",
        artifacts=(
            BenchmarkArtifactReference(
                artifact_id="cpu_baseline_benchmark_report_candidate",
                artifact_kind="baseline_benchmark_report",
                schema_version="tuc.baseline_benchmark_report.v0",
                artifact_digest=(
                    "sha256:"
                    "0123456789abcdef0123456789abcdef"
                    "0123456789abcdef0123456789abcdef"
                ),
                storage_scope="review_attachment",
            ),
        ),
    )
    print(dump_benchmark_artifact_manifest_report(report), end="")


if __name__ == "__main__":
    main()
