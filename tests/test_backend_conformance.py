from __future__ import annotations

import pytest

from tuc.backends import (
    LinearAlgebraSimulatorBackend,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
)
from tuc.backends.base import BackendCapability, LoweringResult
from tuc.backends.conformance import (
    CONFORMANCE_REPORT_SCHEMA_VERSION,
    BackendConformanceError,
    BackendConformanceIssue,
    BackendConformanceReport,
    assert_backend_conformance,
    build_conformance_graph,
    conformance_report_to_dict,
    dump_backend_conformance_report,
    run_backend_conformance,
)
from tuc.ir.model import ComputeGraph, OperationKind


def test_linear_algebra_simulator_passes_backend_conformance() -> None:
    report = assert_backend_conformance(LinearAlgebraSimulatorBackend())

    assert report.passed
    assert "conformance_matmul_row_major" in report.checked_cases
    assert "conformance_reduction_row_major" in report.checked_cases
    assert "conformance_elementwise_row_major" in report.checked_cases
    assert "conformance_softmax_row_major" in report.checked_cases


def test_systolic_array_simulator_passes_backend_conformance() -> None:
    report = assert_backend_conformance(SystolicArraySimulatorBackend())

    assert report.passed
    assert "conformance_matmul_row_major" in report.checked_cases
    assert "conformance_elementwise_row_major" in report.checked_cases
    assert "conformance_reduction_row_major" in report.checked_cases
    assert "conformance_softmax_row_major" in report.checked_cases


def test_vector_simulator_passes_backend_conformance() -> None:
    report = assert_backend_conformance(VectorSimulatorBackend())

    assert report.passed
    assert "conformance_matmul_row_major" in report.checked_cases
    assert "conformance_elementwise_row_major" in report.checked_cases
    assert "conformance_reduction_row_major" in report.checked_cases
    assert "conformance_softmax_row_major" in report.checked_cases


def test_conformance_builds_valid_mvp_operation_graphs() -> None:
    matmul = build_conformance_graph(OperationKind.MATMUL)
    reduction = build_conformance_graph(OperationKind.REDUCTION)
    softmax = build_conformance_graph(OperationKind.SOFTMAX)

    assert matmul.operations[0].outputs[0].shape == (4, 3)
    assert reduction.operations[0].outputs[0].shape == (4,)
    assert softmax.operations[0].inputs[0].shape == softmax.operations[0].outputs[0].shape


def test_conformance_detects_backend_that_lowers_unsupported_operations() -> None:
    class BadBackend:
        capability = BackendCapability(
            name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
        )

        def lower(self, graph: ComputeGraph) -> LoweringResult:
            return LoweringResult(
                backend_name=self.capability.name,
                graph_name=graph.name,
                artifact=f"{graph.operations[0].kind.value} {graph.operations[0].name}",
            )

    report = run_backend_conformance(BadBackend())

    assert not report.passed
    assert any(
        "not accepted by capability.supports" in issue.message
        for issue in report.issues
    )


def test_conformance_detects_missing_semantic_artifact_markers() -> None:
    class BadBackend:
        capability = BackendCapability(
            name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
        )

        def lower(self, graph: ComputeGraph) -> LoweringResult:
            return LoweringResult(
                backend_name=self.capability.name,
                graph_name=graph.name,
                artifact="# opaque artifact",
            )

    report = run_backend_conformance(BadBackend())

    assert any("operation kind and operation name" in issue.message for issue in report.issues)


def test_conformance_detects_malformed_diagnostics() -> None:
    class BadBackend:
        capability = BackendCapability(
            name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
        )

        def lower(self, graph: ComputeGraph) -> LoweringResult:
            return LoweringResult(
                backend_name=self.capability.name,
                graph_name=graph.name,
                artifact=f"{graph.operations[0].kind.value} {graph.operations[0].name}",
                diagnostics=("",),
            )

    report = run_backend_conformance(BadBackend())

    assert any(
        "diagnostics must contain non-empty strings" in issue.message
        for issue in report.issues
    )


def test_assert_backend_conformance_raises_with_compact_report() -> None:
    class BadBackend:
        capability = BackendCapability(
            name="bad",
            supported_ops=frozenset({OperationKind.MATMUL}),
        )

        def lower(self, graph: ComputeGraph) -> LoweringResult:
            return LoweringResult(
                backend_name="wrong",
                graph_name=graph.name,
                artifact=f"{graph.operations[0].kind.value} {graph.operations[0].name}",
            )

    with pytest.raises(BackendConformanceError, match="failed conformance"):
        assert_backend_conformance(BadBackend())


def test_conformance_report_dump_is_stable_review_artifact() -> None:
    report = run_backend_conformance(LinearAlgebraSimulatorBackend())

    artifact = dump_backend_conformance_report(report)
    payload = conformance_report_to_dict(report)

    assert payload["schema_version"] == CONFORMANCE_REPORT_SCHEMA_VERSION
    assert payload["passed"] is True
    assert payload["issues"] == []
    assert artifact.endswith("\n")
    assert '"backend_name": "linear-sim"' in artifact
    assert '"conformance_matmul_row_major"' in artifact


def test_conformance_report_dump_includes_failures() -> None:
    report = BackendConformanceReport(
        backend_name="bad",
        checked_cases=("conformance_matmul_row_major",),
        issues=(
            BackendConformanceIssue(
                case_name="conformance_matmul_row_major",
                message="artifact must not be empty",
            ),
        ),
    )

    artifact = dump_backend_conformance_report(report)

    assert '"passed": false' in artifact
    assert '"message": "artifact must not be empty"' in artifact


def test_conformance_report_dump_rejects_oversized_fields() -> None:
    report = BackendConformanceReport(
        backend_name="bad",
        checked_cases=("x" * 513,),
        issues=(),
    )

    with pytest.raises(ValueError, match="field limit"):
        dump_backend_conformance_report(report)
