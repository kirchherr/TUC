from __future__ import annotations

import json

import pytest

from tuc import (
    NATIVE_BASELINE_DEFAULT_ISSUES,
    NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS,
    NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS,
    NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION,
    NativeBaselineProvenance,
    build_native_baseline_provenance_report,
    dump_native_baseline_provenance_report,
    native_baseline_provenance_report_to_dict,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT


def test_native_baseline_provenance_report_blocks_without_baselines() -> None:
    report = build_native_baseline_provenance_report("blocked_native_baseline")
    payload = native_baseline_provenance_report_to_dict(report)

    assert payload["schema_version"] == NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS
    assert payload["claim_boundary"] == PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    assert payload["performance_claim_status"] == NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS
    assert payload["native_performance_claim"] is False
    assert payload["native_baseline_ready"] is False
    assert payload["baselines"] == []
    assert payload["issues"] == list(NATIVE_BASELINE_DEFAULT_ISSUES)


def test_native_baseline_provenance_report_tracks_candidate_metadata() -> None:
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
    payload = native_baseline_provenance_report_to_dict(report)

    assert payload["native_baseline_ready"] is False
    assert payload["baselines"] == [
        {
            "artifact_digest_status": "not_supplied",
            "baseline_id": "cuda_vendor_matmul_candidate",
            "implementation_kind": "vendor_sample",
            "reproducibility_status": "documented_not_executed",
            "source_provenance_id": "vendor_sample_manifest",
            "target_platform_id": "cuda_sm90",
            "toolchain_id": "cuda_12_4",
            "workload_scope_id": "phase1_mlp_block",
        }
    ]
    assert "native_baselines_not_supplied" not in payload["issues"]
    assert "native_baseline_not_reproduced_by_ci" in payload["issues"]
    assert "native_baseline_artifact_digest_not_supplied" in payload["issues"]


def test_native_baseline_provenance_report_is_json_serializable() -> None:
    report = build_native_baseline_provenance_report("blocked_native_baseline")
    payload = json.loads(dump_native_baseline_provenance_report(report))

    assert payload["schema_version"] == "tuc.native_baseline_provenance_report.v0"
    assert payload["performance_claim_status"] == "blocked"


def test_native_baseline_provenance_rejects_duplicate_baselines() -> None:
    baseline = NativeBaselineProvenance(
        baseline_id="same_baseline",
        workload_scope_id="phase1_mlp_block",
        implementation_kind="vendor_sample",
        target_platform_id="cuda_sm90",
        source_provenance_id="vendor_sample_manifest",
        toolchain_id="cuda_12_4",
        reproducibility_status="documented_not_executed",
    )

    with pytest.raises(ValueError, match="duplicate native baseline id"):
        build_native_baseline_provenance_report(
            "duplicate_native_baseline",
            baselines=(baseline, baseline),
        )


def test_native_baseline_provenance_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unsupported native baseline implementation kind"):
        build_native_baseline_provenance_report(
            "bad_kind",
            baselines=(
                NativeBaselineProvenance(
                    baseline_id="bad_baseline",
                    workload_scope_id="phase1_mlp_block",
                    implementation_kind="python_reference",
                    target_platform_id="cuda_sm90",
                    source_provenance_id="vendor_sample_manifest",
                    toolchain_id="cuda_12_4",
                    reproducibility_status="documented_not_executed",
                ),
            ),
        )


def test_native_baseline_provenance_rejects_host_path_like_identifier() -> None:
    with pytest.raises(ValueError, match="source_provenance_id"):
        build_native_baseline_provenance_report(
            "bad_source_path",
            baselines=(
                NativeBaselineProvenance(
                    baseline_id="bad_baseline",
                    workload_scope_id="phase1_mlp_block",
                    implementation_kind="vendor_sample",
                    target_platform_id="cuda_sm90",
                    source_provenance_id="C:/vendor/kernel.cu",
                    toolchain_id="cuda_12_4",
                    reproducibility_status="documented_not_executed",
                ),
            ),
        )
