from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.planner_overhead_portfolio import (
    PLANNER_OVERHEAD_PORTFOLIO_CONTRACT,
    PLANNER_OVERHEAD_PORTFOLIO_REPORT_SCHEMA_VERSION,
    assert_planner_overhead_portfolio_report_contract,
    build_planner_overhead_portfolio_report,
    build_report,
)
from tuc.benchmarks import PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION

GOLDEN_PATH = Path("tests/golden/proofs/planner_overhead_portfolio_report.json")
SCHEMA_PATH = Path("schemas/planner_overhead_portfolio_report.v0.schema.json")


def test_planner_overhead_portfolio_report_shape() -> None:
    report = build_planner_overhead_portfolio_report()
    assert_planner_overhead_portfolio_report_contract(report)

    assert report["schema_version"] == PLANNER_OVERHEAD_PORTFOLIO_REPORT_SCHEMA_VERSION
    assert report["portfolio_contract"] == PLANNER_OVERHEAD_PORTFOLIO_CONTRACT
    assert report["planner_overhead_schema_version"] == PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION
    assert report["status"] == "PASS"
    assert report["case_count"] == 4
    assert report["covered_operation_families"] == [
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ]
    assert [case["case_id"] for case in report["cases"]] == [
        "research_module_matmul_elementwise",
        "research_module_softmax_reduction",
        "research_module_matmul_reduction",
        "research_module_mvp_pipeline",
    ]
    assert {case["measured_compiler_phase_count"] for case in report["cases"]} == {5}
    assert {case["unmeasured_phase_count"] for case in report["cases"]} == {3}


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("case_count", 1, "case_count"),
        ("raw_timing_samples", [], "top-level report"),
        ("native_performance_claim", True, "native_performance_claim"),
    ],
)
def test_planner_overhead_portfolio_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_planner_overhead_portfolio_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_planner_overhead_portfolio_report_contract(report)


def test_planner_overhead_portfolio_contract_rejects_case_drift() -> None:
    report = build_planner_overhead_portfolio_report()
    cases = report["cases"]
    assert isinstance(cases, list)
    assert isinstance(cases[0], dict)
    cases[0]["timing_policy"] = "raw_timing_samples_allowed"

    with pytest.raises(ValueError, match="timing_policy drift"):
        assert_planner_overhead_portfolio_report_contract(report)


def test_planner_overhead_portfolio_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_planner_overhead_portfolio_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/planner_overhead_portfolio.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"portfolio_contract"' in completed.stdout
    assert '"duration_ns"' not in completed.stdout
    assert '"total_planning_ns"' not in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_planner_overhead_portfolio_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        PLANNER_OVERHEAD_PORTFOLIO_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["portfolio_contract"]["const"] == (
        PLANNER_OVERHEAD_PORTFOLIO_CONTRACT
    )
    assert schema["properties"]["planner_overhead_schema_version"]["const"] == (
        PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["case_count"]["const"] == 4
    assert schema["$defs"]["case"]["additionalProperties"] is False
    assert "raw_timing_policy" in schema["required"]


def test_planner_overhead_portfolio_schema_fails_closed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    _assert_objects_fail_closed(schema)
    assert "raw_timing_samples" not in schema["properties"]
    assert "duration_ns" not in schema["$defs"]["case"]["properties"]
    assert "total_planning_ns" not in schema["$defs"]["case"]["properties"]
    assert "device_id" not in schema["properties"]
    assert "host_path" not in schema["properties"]


def test_planner_overhead_portfolio_is_documented_and_in_ci() -> None:
    example_path = "examples/planner_overhead_portfolio.py"
    doc_path = "PLANNER_OVERHEAD_PORTFOLIO.md"
    schema_path = "schemas/planner_overhead_portfolio_report.v0.schema.json"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/PLANNER_OVERHEAD_REPORT.md"),
        Path("docs/PLANNER_OVERHEAD_PORTFOLIO.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0223-planner-overhead-portfolio.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/PLANNER_OVERHEAD_REPORT.md"),
        Path("docs/PLANNER_OVERHEAD_PORTFOLIO.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0223-planner-overhead-portfolio.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")

    for path in (
        Path("docs/PLANNER_OVERHEAD_PORTFOLIO.md"),
        Path("rfcs/0223-planner-overhead-portfolio.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
