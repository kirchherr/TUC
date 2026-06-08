from __future__ import annotations

from pathlib import Path

import pytest

from examples.external_backend_author_path import (
    MANIFEST_PATH,
    assigned_graph_for_backend,
    build_backend_from_manifest,
    build_graph,
    run_external_backend_author_path,
)
from tuc.backends.conformance import build_conformance_graph, dump_backend_conformance_report
from tuc.backends.registry import BackendRegistry
from tuc.compiler import compile_graph
from tuc.ir import LayoutKind, OperationKind


def test_external_backend_author_path_uses_explicit_manifest_registry() -> None:
    registry = BackendRegistry.from_manifest_paths([MANIFEST_PATH])
    graph = build_graph()

    compiled = compile_graph(graph, registry.capabilities())
    diagnostics = registry.diagnose_operation_support(graph.operations[0])

    assert registry.names() == ("external-vector",)
    assert registry.registrations()[0].source_label == "external_vector_backend.json"
    assert diagnostics[0].supported is True
    assert diagnostics[0].reason == "accepted"
    assert compiled.partition_plan.backend_for("activation") == "external-vector"
    assert compiled.hs_ir.graph.operations[0].attributes["tuc.produced_layout"] == "vector"


def test_external_backend_author_path_passes_conformance_and_lowers_assignment() -> None:
    report = run_external_backend_author_path()

    assert report.conformance.passed
    assert "conformance_elementwise_row_major" in report.conformance.checked_cases
    assert report.lowered.backend_name == "external-vector"
    assert report.lowered.graph_name == "external_backend_author_demo"
    assert "elementwise activation" in report.lowered.artifact


def test_external_backend_author_conformance_report_matches_golden() -> None:
    report = run_external_backend_author_path()
    golden = Path("tests/golden/backend_conformance/external_vector_report.json")

    assert dump_backend_conformance_report(report.conformance) == golden.read_text(
        encoding="utf-8"
    )


def test_external_backend_author_lowering_rejects_unsupported_work() -> None:
    backend = build_backend_from_manifest()
    graph = build_conformance_graph(OperationKind.MATMUL, layout=LayoutKind.ROW_MAJOR)

    with pytest.raises(ValueError, match="external-vector cannot lower: matmul"):
        backend.lower(graph)


def test_external_backend_author_lowering_uses_only_assigned_subgraph() -> None:
    report = run_external_backend_author_path()
    assigned_graph = assigned_graph_for_backend(report.compiled, "external-vector")

    assert assigned_graph.operation_names() == ("activation",)
    assert all(
        operation.attributes["tuc.assigned_backend"] == "external-vector"
        for operation in report.compiled.hs_ir.graph.operations
    )
