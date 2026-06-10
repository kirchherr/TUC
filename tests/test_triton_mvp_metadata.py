from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from numpy.testing import assert_allclose

from examples.triton_mvp_metadata import (
    build_graph,
    evaluate_graph,
    mvp_inputs,
    reference_result,
    run_report,
)
from tuc.ir import OperationKind
from tuc.runtime import DEFAULT_FALLBACK_BACKEND

_GOLDEN_TRACE = (
    Path(__file__).parent
    / "golden"
    / "execution_traces"
    / "triton_metadata_mvp_families.txt"
)


def test_triton_mvp_metadata_covers_all_mvp_operation_families() -> None:
    graph = build_graph()

    assert tuple(operation.kind for operation in graph.operations) == (
        OperationKind.MATMUL,
        OperationKind.SOFTMAX,
        OperationKind.MATMUL,
        OperationKind.REDUCTION,
        OperationKind.ELEMENTWISE,
    )
    assert graph.metadata["frontend.schema_version"] == "triton_metadata.v0"
    assert graph.metadata["frontend.intake_contract"] == "triton_intake.execution_free.v0"


def test_triton_mvp_metadata_reference_result_is_stable() -> None:
    graph = build_graph()
    inputs = mvp_inputs()

    result = evaluate_graph(graph, inputs)
    expected = reference_result(inputs)

    assert_allclose(result, expected, rtol=1e-12, atol=1e-12)
    assert_allclose(
        result,
        np.array([2.621850822520665, 0.32197780350546923], dtype=np.float64),
        rtol=1e-12,
        atol=1e-12,
    )


def test_triton_mvp_metadata_pipeline_assignments_are_explainable() -> None:
    report = run_report()

    assert report.compiled.partition_plan.backend_for("score_projection") == "linear-sim"
    assert (
        report.compiled.partition_plan.backend_for("attention_softmax")
        == DEFAULT_FALLBACK_BACKEND
    )
    assert report.compiled.partition_plan.backend_for("value_projection") == "linear-sim"
    assert report.compiled.partition_plan.backend_for("context_reduction") == "linear-sim"
    assert (
        report.compiled.partition_plan.backend_for("summary_activation")
        == DEFAULT_FALLBACK_BACKEND
    )
    assert report.passed


def test_triton_mvp_metadata_runtime_executor_covers_all_mvp_families() -> None:
    report = run_report()

    assert tuple(step.operation_kind for step in report.execution.trace.steps) == (
        OperationKind.MATMUL,
        OperationKind.SOFTMAX,
        OperationKind.MATMUL,
        OperationKind.REDUCTION,
        OperationKind.ELEMENTWISE,
    )
    assert tuple(step.executor_backend for step in report.execution.trace.steps) == (
        "linear-sim",
        DEFAULT_FALLBACK_BACKEND,
        "linear-sim",
        "linear-sim",
        DEFAULT_FALLBACK_BACKEND,
    )
    assert report.execution.trace.dump() == _GOLDEN_TRACE.read_text(
        encoding="utf-8"
    ).rstrip("\n")


def test_triton_mvp_metadata_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/triton_mvp_metadata.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "== intake report ==" in completed.stdout
    assert "== execution trace ==" in completed.stdout
    assert "triton_metadata_mvp_families" in completed.stdout
    assert 'operation_kinds = "matmul,softmax,matmul,reduction,elementwise"' in completed.stdout
    assert "attention_softmax planned_backend=reference-cpu" in completed.stdout
    assert completed.stdout.rstrip().endswith("PASS")
