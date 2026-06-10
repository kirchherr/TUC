from __future__ import annotations

import json
from pathlib import Path

import pytest

from examples.triton_idiom_coverage_report import build_report as build_example_report
from tuc.frontend import (
    TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS,
    TRITON_IDIOM_COVERAGE_CONTRACT,
    TRITON_IDIOM_COVERAGE_DEFAULT_ISSUES,
    TRITON_IDIOM_COVERAGE_PARSER_STATUS,
    TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION,
    TritonIdiomCoverage,
    build_triton_idiom_coverage_report,
    dump_triton_idiom_coverage_report,
    triton_idiom_coverage_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/frontend/triton_idiom_coverage_report.json")


def test_triton_idiom_coverage_report_defaults_to_blocked() -> None:
    report = build_triton_idiom_coverage_report("triton_mvp")

    payload = triton_idiom_coverage_report_to_dict(report)

    assert payload["schema_version"] == TRITON_IDIOM_COVERAGE_REPORT_SCHEMA_VERSION
    assert payload["artifact_status"] == TRITON_IDIOM_COVERAGE_ARTIFACT_STATUS
    assert payload["coverage_contract"] == TRITON_IDIOM_COVERAGE_CONTRACT
    assert payload["parser_status"] == TRITON_IDIOM_COVERAGE_PARSER_STATUS
    assert payload["direct_triton_source_ingestion"] is False
    assert payload["triton_idiom_coverage_ready"] is False
    assert payload["issues"] == list(TRITON_IDIOM_COVERAGE_DEFAULT_ISSUES)


def test_triton_idiom_coverage_report_is_ready_with_golden_evidence() -> None:
    report = build_triton_idiom_coverage_report(
        "triton_mvp",
        (
            _coverage("metadata_matmul", "matmul"),
            _coverage("metadata_softmax", "softmax"),
            _coverage("metadata_reduction", "reduction"),
            _coverage("metadata_elementwise", "elementwise"),
        ),
    )

    payload = triton_idiom_coverage_report_to_dict(report)

    assert payload["triton_idiom_coverage_ready"] is True
    assert payload["issues"] == []
    assert [item["operation_family"] for item in payload["coverages"]] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]


def test_triton_idiom_coverage_report_marks_missing_evidence() -> None:
    report = build_triton_idiom_coverage_report(
        "triton_mvp",
        (
            TritonIdiomCoverage(
                idiom_id="metadata_matmul",
                operation_family="matmul",
                metadata_example_id="triton_mvp_metadata",
                intake_golden_id="not_supplied",
                hac_ir_golden_id="triton_mvp_hac_ir",
                runtime_plan_golden_id="triton_mvp_runtime_plan",
                compiler_decision_golden_id="triton_mvp_compiler_decision",
            ),
        ),
    )

    payload = triton_idiom_coverage_report_to_dict(report)

    assert payload["triton_idiom_coverage_ready"] is False
    assert "triton_idiom_coverage_not_supplied" not in payload["issues"]
    assert "triton_idiom_coverage_evidence_not_supplied" in payload["issues"]


def test_triton_idiom_coverage_report_marks_uncovered_status() -> None:
    report = build_triton_idiom_coverage_report(
        "triton_mvp",
        (
            TritonIdiomCoverage(
                idiom_id="program_id_grid_mapping",
                operation_family="elementwise",
                metadata_example_id="not_supplied",
                intake_golden_id="not_supplied",
                hac_ir_golden_id="not_supplied",
                runtime_plan_golden_id="not_supplied",
                compiler_decision_golden_id="not_supplied",
                coverage_status="documented_not_covered",
            ),
        ),
    )

    payload = triton_idiom_coverage_report_to_dict(report)

    assert payload["triton_idiom_coverage_ready"] is False
    assert "triton_idiom_coverage_not_golden_covered" in payload["issues"]


def test_triton_idiom_coverage_report_json_is_stable() -> None:
    report = build_triton_idiom_coverage_report(
        "triton_mvp",
        (_coverage("metadata_matmul", "matmul"),),
    )

    payload = json.loads(dump_triton_idiom_coverage_report(report))

    assert payload["schema_version"] == "tuc.triton_idiom_coverage_report.v0"
    assert payload["coverages"][0]["idiom_id"] == "metadata_matmul"


def test_triton_idiom_coverage_example_matches_golden() -> None:
    assert build_example_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_triton_idiom_coverage_report_rejects_duplicate_ids() -> None:
    coverage = _coverage("metadata_matmul", "matmul")

    with pytest.raises(ValueError, match="duplicate triton idiom coverage id"):
        build_triton_idiom_coverage_report("triton_mvp", (coverage, coverage))


def test_triton_idiom_coverage_report_rejects_unsupported_operation_family() -> None:
    with pytest.raises(ValueError, match="unsupported triton idiom operation family"):
        build_triton_idiom_coverage_report(
            "triton_mvp",
            (
                TritonIdiomCoverage(
                    idiom_id="metadata_load",
                    operation_family="load",
                    metadata_example_id="triton_mvp_metadata",
                    intake_golden_id="triton_mvp_intake",
                    hac_ir_golden_id="triton_mvp_hac_ir",
                    runtime_plan_golden_id="triton_mvp_runtime_plan",
                    compiler_decision_golden_id="triton_mvp_compiler_decision",
                ),
            ),
        )


def test_triton_idiom_coverage_report_rejects_path_like_ids() -> None:
    with pytest.raises(ValueError, match="safe triton idiom coverage identifier"):
        build_triton_idiom_coverage_report(
            "triton_mvp",
            (
                TritonIdiomCoverage(
                    idiom_id="../tests/golden/frontend/intake",
                    operation_family="matmul",
                    metadata_example_id="triton_mvp_metadata",
                    intake_golden_id="triton_mvp_intake",
                    hac_ir_golden_id="triton_mvp_hac_ir",
                    runtime_plan_golden_id="triton_mvp_runtime_plan",
                    compiler_decision_golden_id="triton_mvp_compiler_decision",
                ),
            ),
        )


def test_triton_idiom_coverage_report_rejects_execution_surface_ids() -> None:
    with pytest.raises(ValueError, match="safe triton idiom coverage identifier"):
        build_triton_idiom_coverage_report("python_source")


def _coverage(idiom_id: str, operation_family: str) -> TritonIdiomCoverage:
    return TritonIdiomCoverage(
        idiom_id=idiom_id,
        operation_family=operation_family,
        metadata_example_id="triton_mvp_metadata",
        intake_golden_id="triton_mvp_intake",
        hac_ir_golden_id="triton_mvp_hac_ir",
        runtime_plan_golden_id="triton_mvp_runtime_plan",
        compiler_decision_golden_id="triton_mvp_compiler_decision",
    )
