from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.runtime_backend_equivalence import build_backend_equivalence_report
from examples.runtime_backend_equivalence_portfolio import (
    build_backend_equivalence_portfolio_report,
)
from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from examples.runtime_vector_backend_equivalence import (
    build_vector_backend_equivalence_report,
)
from tuc import (
    MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ISSUES,
    MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_SLICES,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT,
    RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_SCHEMA_VERSION,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    RuntimeBackendEquivalenceIssue,
    RuntimeBackendEquivalencePortfolioIssue,
    RuntimeBackendEquivalencePortfolioReport,
    RuntimeBackendEquivalencePortfolioSlice,
    RuntimeBackendEquivalenceReport,
    assert_runtime_backend_equivalence_portfolio,
    build_runtime_backend_equivalence_portfolio_report,
    dump_runtime_backend_equivalence_portfolio_report,
    runtime_backend_equivalence_portfolio_report_to_dict,
)

GOLDEN_PATH = Path("tests/golden/runtime_backend_equivalence/portfolio_report.json")
SCHEMA_PATH = Path(
    "schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json"
)


def test_runtime_backend_equivalence_portfolio_passes() -> None:
    report = build_backend_equivalence_portfolio_report()

    assert report.portfolio_contract == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT
    assert report.executor_contract == RUNTIME_EXECUTOR_CONTRACT
    assert report.trusted_executor_registry == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert report.artifact_status == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS
    assert report.raw_value_policy == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert report.passed
    assert report.issues == ()
    assert report.slice_count == 3
    assert report.candidate_backend_families == ("systolic-sim", "vector-sim")
    assert tuple(slice_.slice_id for slice_ in report.slices) == (
        "runtime_backend_equivalence",
        "runtime_vector_backend_equivalence",
        "runtime_mixed_backend_equivalence",
    )
    assert tuple(slice_.comparison_count for slice_ in report.slices) == (1, 1, 1)
    assert tuple(slice_.passed for slice_ in report.slices) == (True, True, True)
    assert report.slices[0].candidate_backend_sequence == (
        "systolic-sim",
        "reference-cpu",
    )
    assert report.slices[1].candidate_backend_sequence == (
        "vector-sim",
        "vector-sim",
        "vector-sim",
    )
    assert report.slices[2].candidate_backend_sequence == (
        "systolic-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    )
    assert tuple(runtime_backend_equivalence_portfolio_report_to_dict(report)) == (
        "artifact_status",
        "blocked_execution_surfaces",
        "candidate_backend_families",
        "executor_contract",
        "issues",
        "passed",
        "portfolio_contract",
        "portfolio_id",
        "portfolio_metadata_digest",
        "raw_value_policy",
        "schema_version",
        "slice_count",
        "slices",
        "trusted_executor_registry",
    )


def test_runtime_backend_equivalence_portfolio_dump_matches_golden() -> None:
    assert dump_runtime_backend_equivalence_portfolio_report(
        build_backend_equivalence_portfolio_report()
    ) == (GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_backend_equivalence_portfolio_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_backend_equivalence_portfolio.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_backend_equivalence_portfolio.data_only.v0" in completed.stdout
    assert '"runtime_backend_equivalence"' in completed.stdout
    assert '"runtime_vector_backend_equivalence"' in completed.stdout
    assert '"runtime_mixed_backend_equivalence"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "python_source" not in completed.stdout


def test_runtime_backend_equivalence_portfolio_assertion_returns_report() -> None:
    assert assert_runtime_backend_equivalence_portfolio(
        build_backend_equivalence_portfolio_report()
    ).passed


def test_runtime_backend_equivalence_portfolio_derives_failed_slice_issue() -> None:
    report = build_vector_backend_equivalence_report()
    candidate = replace(
        report.runs[1],
        planned_backend_sequence=report.runs[0].planned_backend_sequence,
    )
    failed_equivalence = RuntimeBackendEquivalenceReport(
        graph_name=report.graph_name,
        baseline_run_id=report.baseline_run_id,
        candidate_run_id=report.candidate_run_id,
        runs=(report.runs[0], candidate),
        comparisons=report.comparisons,
        issues=(
            RuntimeBackendEquivalenceIssue(
                subject="backend_sequence",
                issue_code="backend_sequences_not_distinct",
            ),
        ),
    )

    portfolio = build_runtime_backend_equivalence_portfolio_report(
        "runtime_backend_equivalence_portfolio_failed_slice",
        (build_backend_equivalence_report(), failed_equivalence),
    )

    assert not portfolio.passed
    assert portfolio.issues == (
        RuntimeBackendEquivalencePortfolioIssue(
            slice_id="runtime_vector_backend_equivalence",
            issue_code="equivalence_report_failed",
        ),
    )
    with pytest.raises(
        AssertionError,
        match="runtime backend equivalence portfolio failed",
    ):
        assert_runtime_backend_equivalence_portfolio(portfolio)


def test_runtime_backend_equivalence_portfolio_derives_duplicate_slice_issue() -> None:
    report = build_backend_equivalence_report()
    portfolio = build_runtime_backend_equivalence_portfolio_report(
        "runtime_backend_equivalence_portfolio_duplicate_slice",
        (report, report),
    )

    assert not portfolio.passed
    assert portfolio.issues == (
        RuntimeBackendEquivalencePortfolioIssue(
            slice_id="runtime_backend_equivalence",
            issue_code="slice_id_duplicate",
        ),
    )


def test_runtime_backend_equivalence_portfolio_issues_must_be_derived() -> None:
    report = build_backend_equivalence_portfolio_report()
    bad_slice = replace(report.slices[0], passed=False)

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeBackendEquivalencePortfolioReport(
            portfolio_id=report.portfolio_id,
            slices=(bad_slice, *report.slices[1:]),
            issues=(),
        )


def test_runtime_backend_equivalence_portfolio_rejects_raw_value_status() -> None:
    report = build_backend_equivalence_portfolio_report()

    with pytest.raises(ValueError, match="omit raw values"):
        replace(report.slices[0], raw_value_policy="included")


def test_runtime_backend_equivalence_portfolio_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution or value surface"):
        RuntimeBackendEquivalencePortfolioSlice(
            slice_id="python_source",
            graph_name="runtime_backend_equivalence",
            baseline_run_id="reference_cpu",
            candidate_run_id="systolic_sim",
            baseline_backend_sequence=("reference-cpu",),
            candidate_backend_sequence=("systolic-sim",),
            comparison_count=1,
            comparison_metadata_digest="sha256:" + "0" * 64,
            passed=True,
        )


def test_runtime_backend_equivalence_portfolio_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS
    )
    assert schema["properties"]["portfolio_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["trusted_executor_registry"]["const"] == (
        TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert schema["properties"]["slices"]["maxItems"] == (
        MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_SLICES
    )
    assert schema["properties"]["issues"]["maxItems"] == (
        MAX_RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ISSUES
    )
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_runtime_backend_equivalence_portfolio_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "generated_code",
        "raw_benchmark_output",
        "raw_tensor_value",
        "tensor_values",
        "runtime_handle",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["slice"]["properties"]
        assert forbidden not in schema["$defs"]["issue"]["properties"]
    assert "python_source" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "raw_tensor_value" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "runtime_handle" in schema["$defs"]["report_text"]["not"]["enum"]


def test_runtime_backend_equivalence_portfolio_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_REPORT_SCHEMA_VERSION
    )
    assert golden["artifact_status"] == (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ARTIFACT_STATUS
    )
    assert golden["portfolio_contract"] == RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_CONTRACT
    assert golden["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert golden["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert golden["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["passed"] is True
    assert golden["issues"] == []
    assert golden["slice_count"] == len(golden["slices"]) == 3
    assert golden["candidate_backend_families"] == ["systolic-sim", "vector-sim"]
    assert [slice_["slice_id"] for slice_ in golden["slices"]] == [
        "runtime_backend_equivalence",
        "runtime_vector_backend_equivalence",
        "runtime_mixed_backend_equivalence",
    ]
    assert all(slice_["passed"] is True for slice_ in golden["slices"])
    assert all(
        slice_["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
        for slice_ in golden["slices"]
    )


def test_runtime_backend_equivalence_portfolio_schema_is_referenced() -> None:
    schema_path = "schemas/runtime_backend_equivalence_portfolio_report.v0.schema.json"

    for path in (
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE.md"),
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO.md"),
        Path("docs/RUNTIME_EVIDENCE_GATE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0143-runtime-backend-equivalence-portfolio.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def test_runtime_backend_equivalence_portfolio_accepts_scoped_subportfolio() -> None:
    portfolio = build_runtime_backend_equivalence_portfolio_report(
        "runtime_backend_equivalence_subportfolio",
        (
            build_backend_equivalence_report(),
            build_mixed_backend_equivalence_report(),
        ),
    )

    assert portfolio.passed
    assert portfolio.slice_count == 2
    assert portfolio.candidate_backend_families == ("systolic-sim", "vector-sim")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
