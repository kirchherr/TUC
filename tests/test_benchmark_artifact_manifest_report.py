from __future__ import annotations

import json

import pytest

from tuc import (
    BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS,
    BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS,
    BENCHMARK_ARTIFACT_MANIFEST_DEFAULT_ISSUES,
    BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION,
    BENCHMARK_ARTIFACT_REQUIRED_KINDS,
    BenchmarkArtifactReference,
    benchmark_artifact_manifest_report_to_dict,
    build_benchmark_artifact_manifest_report,
    dump_benchmark_artifact_manifest_report,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

_DIGEST = "sha256:" + ("0123456789abcdef" * 4)


def test_benchmark_artifact_manifest_blocks_without_artifacts() -> None:
    report = build_benchmark_artifact_manifest_report("blocked_benchmark_manifest")
    payload = benchmark_artifact_manifest_report_to_dict(report)

    assert payload["schema_version"] == (
        BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == (
        BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS
    )
    assert payload["native_performance_claim"] is False
    assert payload["benchmark_artifact_manifest_complete"] is False
    assert payload["artifacts"] == []
    assert payload["required_artifact_kinds"] == list(BENCHMARK_ARTIFACT_REQUIRED_KINDS)
    for issue in BENCHMARK_ARTIFACT_MANIFEST_DEFAULT_ISSUES:
        assert issue in payload["issues"]
    assert "benchmark_artifact_missing_baseline_benchmark_report" in payload["issues"]
    assert "benchmark_artifact_missing_native_benchmark_report" in payload["issues"]
    assert "benchmark_artifact_missing_native_baseline_comparison_report" in (
        payload["issues"]
    )


def test_benchmark_artifact_manifest_tracks_candidate_artifact() -> None:
    report = build_benchmark_artifact_manifest_report(
        "phase1_benchmark_manifest_candidate",
        artifacts=(
            BenchmarkArtifactReference(
                artifact_id="cpu_baseline_benchmark_report_candidate",
                artifact_kind="baseline_benchmark_report",
                schema_version="tuc.baseline_benchmark_report.v0",
                artifact_digest=_DIGEST,
                storage_scope="review_attachment",
            ),
        ),
    )
    payload = benchmark_artifact_manifest_report_to_dict(report)

    assert payload["benchmark_artifact_manifest_complete"] is False
    assert payload["artifacts"] == [
        {
            "artifact_digest": _DIGEST,
            "artifact_id": "cpu_baseline_benchmark_report_candidate",
            "artifact_kind": "baseline_benchmark_report",
            "schema_version": "tuc.baseline_benchmark_report.v0",
            "storage_scope": "review_attachment",
        }
    ]
    assert "benchmark_artifacts_not_supplied" not in payload["issues"]
    assert "benchmark_artifact_missing_native_benchmark_report" in payload["issues"]
    assert "benchmark_artifact_digest_not_supplied" not in payload["issues"]


def test_benchmark_artifact_manifest_can_be_inventory_complete() -> None:
    report = build_benchmark_artifact_manifest_report(
        "complete_benchmark_manifest_candidate",
        artifacts=(
            BenchmarkArtifactReference(
                artifact_id="baseline_report",
                artifact_kind="baseline_benchmark_report",
                schema_version="tuc.baseline_benchmark_report.v0",
                artifact_digest=_DIGEST,
            ),
            BenchmarkArtifactReference(
                artifact_id="native_report",
                artifact_kind="native_benchmark_report",
                schema_version="tuc.native_benchmark_report.v0",
                artifact_digest=_DIGEST,
            ),
            BenchmarkArtifactReference(
                artifact_id="comparison_report",
                artifact_kind="native_baseline_comparison_report",
                schema_version="tuc.native_baseline_comparison_report.v0",
                artifact_digest=_DIGEST,
            ),
        ),
    )
    payload = benchmark_artifact_manifest_report_to_dict(report)

    assert payload["benchmark_artifact_manifest_complete"] is True
    assert payload["native_performance_claim"] is False
    assert payload["issues"] == ["native_performance_claim_blocked"]


def test_benchmark_artifact_manifest_report_is_json_serializable() -> None:
    report = build_benchmark_artifact_manifest_report("blocked_benchmark_manifest")
    payload = json.loads(dump_benchmark_artifact_manifest_report(report))

    assert payload["schema_version"] == "tuc.benchmark_artifact_manifest_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_benchmark_artifact_manifest_rejects_duplicate_artifacts() -> None:
    artifact = BenchmarkArtifactReference(
        artifact_id="same_artifact",
        artifact_kind="baseline_benchmark_report",
        schema_version="tuc.baseline_benchmark_report.v0",
        artifact_digest=_DIGEST,
    )

    with pytest.raises(ValueError, match="duplicate benchmark artifact id"):
        build_benchmark_artifact_manifest_report(
            "duplicate_benchmark_artifact",
            artifacts=(artifact, artifact),
        )


def test_benchmark_artifact_manifest_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unsupported benchmark artifact kind"):
        build_benchmark_artifact_manifest_report(
            "bad_kind",
            artifacts=(
                BenchmarkArtifactReference(
                    artifact_id="bad_artifact",
                    artifact_kind="raw_timing_samples",
                    schema_version="tuc.raw_timing_samples.v0",
                    artifact_digest=_DIGEST,
                ),
            ),
        )


def test_benchmark_artifact_manifest_rejects_host_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="artifact_id"):
        build_benchmark_artifact_manifest_report(
            "bad_artifact_path",
            artifacts=(
                BenchmarkArtifactReference(
                    artifact_id="C:/benchmarks/report.json",
                    artifact_kind="baseline_benchmark_report",
                    schema_version="tuc.baseline_benchmark_report.v0",
                    artifact_digest=_DIGEST,
                ),
            ),
        )


def test_benchmark_artifact_manifest_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="artifact_digest"):
        build_benchmark_artifact_manifest_report(
            "bad_digest",
            artifacts=(
                BenchmarkArtifactReference(
                    artifact_id="bad_digest_artifact",
                    artifact_kind="baseline_benchmark_report",
                    schema_version="tuc.baseline_benchmark_report.v0",
                    artifact_digest="sha256:ABCDEF",
                ),
            ),
        )
