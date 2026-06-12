from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tuc import (
    RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT,
    RuntimeExecutorConformanceCase,
    RuntimeExecutorConformanceReport,
    assert_runtime_executor_conformance,
    dump_runtime_executor_conformance_report,
    run_runtime_executor_conformance,
    runtime_executor_conformance_report_to_dict,
)
from tuc.ir import OperationKind

_GOLDEN = Path(
    "tests/golden/runtime_executor_conformance/trusted_runtime_executor_registry.json"
)


def test_runtime_executor_conformance_passes_for_trusted_registry() -> None:
    report = run_runtime_executor_conformance()

    assert report.conformance_contract == RUNTIME_EXECUTOR_CONFORMANCE_CONTRACT
    assert report.passed
    assert report.issues == ()
    assert tuple(case.case_name for case in report.checked_cases) == (
        "linear-sim_matmul_supported",
        "linear-sim_elementwise_unsupported",
        "linear-sim_reduction_supported",
        "linear-sim_softmax_unsupported",
        "reference-cpu_matmul_supported",
        "reference-cpu_elementwise_supported",
        "reference-cpu_reduction_supported",
        "reference-cpu_softmax_supported",
        "systolic-sim_matmul_supported",
        "systolic-sim_elementwise_unsupported",
        "systolic-sim_reduction_unsupported",
        "systolic-sim_softmax_unsupported",
        "vector-sim_matmul_unsupported",
        "vector-sim_elementwise_supported",
        "vector-sim_reduction_supported",
        "vector-sim_softmax_supported",
    )
    assert tuple(runtime_executor_conformance_report_to_dict(report)) == (
        "blocked_execution_surfaces",
        "case_count",
        "checked_cases",
        "conformance_contract",
        "executor_contract",
        "issues",
        "passed",
        "schema_version",
        "trusted_executor_registry",
    )


def test_runtime_executor_conformance_records_expected_rejections() -> None:
    report = run_runtime_executor_conformance()
    cases = {case.case_name: case for case in report.checked_cases}

    assert cases["linear-sim_elementwise_unsupported"].observed_status == "rejected"
    assert cases["linear-sim_elementwise_unsupported"].output_dtype == "not_executed"
    assert cases["linear-sim_softmax_unsupported"].observed_status == "rejected"
    assert cases["linear-sim_softmax_unsupported"].output_shape == ()
    assert cases["reference-cpu_softmax_supported"].observed_status == "executed"
    assert cases["reference-cpu_softmax_supported"].output_shape == (2, 3)
    assert cases["systolic-sim_matmul_supported"].observed_status == "executed"
    assert cases["systolic-sim_elementwise_unsupported"].observed_status == "rejected"
    assert cases["systolic-sim_reduction_unsupported"].observed_status == "rejected"
    assert cases["systolic-sim_softmax_unsupported"].observed_status == "rejected"
    assert cases["vector-sim_matmul_unsupported"].observed_status == "rejected"
    assert cases["vector-sim_elementwise_supported"].observed_status == "executed"
    assert cases["vector-sim_reduction_supported"].observed_status == "executed"
    assert cases["vector-sim_softmax_supported"].observed_status == "executed"


def test_runtime_executor_conformance_assertion_returns_report() -> None:
    assert assert_runtime_executor_conformance().passed


def test_runtime_executor_conformance_dump_matches_golden() -> None:
    assert dump_runtime_executor_conformance_report(
        run_runtime_executor_conformance()
    ) == (_GOLDEN.read_text(encoding="utf-8").rstrip("\n") + "\n")


def test_runtime_executor_conformance_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/runtime_executor_conformance.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "runtime_executor_conformance.trusted.v0" in completed.stdout
    assert '"passed": true' in completed.stdout
    assert "linear-sim_elementwise_unsupported" in completed.stdout


def test_runtime_executor_conformance_issues_must_be_derived() -> None:
    case = RuntimeExecutorConformanceCase(
        executor_name="reference-cpu",
        operation_kind=OperationKind.MATMUL,
        case_name="forged_supported_case",
        expected_status="supported",
        observed_status="rejected",
        output_shape=(),
        output_dtype="not_executed",
    )

    with pytest.raises(ValueError, match="issues must be derived"):
        RuntimeExecutorConformanceReport(checked_cases=(case,), issues=())


def test_runtime_executor_conformance_rejects_forbidden_surface_names() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        RuntimeExecutorConformanceCase(
            executor_name="python_source",
            operation_kind=OperationKind.MATMUL,
            case_name="bad_case",
            expected_status="supported",
            observed_status="executed",
            output_shape=(2, 2),
            output_dtype="float64",
        )
