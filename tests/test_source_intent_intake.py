from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.source_intent_intake import build_source_intent_data
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_INTENT_INTAKE_CONTRACT,
    SOURCE_INTENT_SCHEMA_VERSION,
    build_source_intent_intake_report,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.ir import IRStage


def test_source_intent_intake_builds_module_from_plain_data() -> None:
    module = source_intent_from_mapping(build_source_intent_data())

    assert module.name == "source_intent_data_mlp"
    assert tuple(tensor.name for tensor in module.tensors) == ("a", "b", "c", "y")
    assert tuple(operation.family for operation in module.operations) == (
        "matmul",
        "elementwise",
    )
    assert module.operations[0].hints["prefer_linear_accelerator"] is True


def test_source_intent_intake_report_preserves_contracts() -> None:
    module = source_intent_from_mapping(build_source_intent_data())
    report = build_source_intent_intake_report(module)

    assert report.schema_version == SOURCE_INTENT_SCHEMA_VERSION
    assert report.intake_contract == SOURCE_INTENT_INTAKE_CONTRACT
    assert "source_parsing" in report.blocked_execution_surfaces
    assert "metadata" in report.blocked_compiler_outputs


def test_source_intent_intake_accepts_axis_attributes_for_axis_ops() -> None:
    module = source_intent_from_mapping(
        {
            "name": "source_intent_axis_ops",
            "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
            "tensors": [
                {"name": "x", "shape": [4, 8]},
                {"name": "normalized", "shape": [4, 8]},
                {"name": "row_sum", "shape": [4]},
            ],
            "operations": [
                {
                    "name": "normalized",
                    "family": "softmax",
                    "inputs": ["x"],
                    "outputs": ["normalized"],
                    "attributes": {"axis": 1},
                },
                {
                    "name": "row_sum",
                    "family": "reduction",
                    "inputs": ["normalized"],
                    "outputs": ["row_sum"],
                    "attributes": {"axis": 1},
                },
            ],
        }
    )

    assert module.operations[0].attributes["axis"] == 1
    assert module.operations[1].attributes["axis"] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "bad", "schema_version": "source_intent.v999", "tensors": [], "operations": []},
        {
            "name": "bad",
            "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
            "python_source": "def kernel(): pass",
            "tensors": [],
            "operations": [],
        },
        {
            "name": "bad",
            "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
            "tensors": [{"name": "a", "shape": [1], "file_path": "/tmp/x"}],
            "operations": [],
        },
        {
            "name": "bad",
            "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
            "tensors": [{"name": "a", "shape": [1]}],
            "operations": [
                {
                    "name": "op",
                    "family": "matmul",
                    "inputs": ["a"],
                    "outputs": ["a"],
                    "hints": {"backend": "gpu"},
                }
            ],
        },
        {
            "name": "bad",
            "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
            "tensors": [{"name": "a", "shape": [2]}],
            "operations": [
                {
                    "name": "op",
                    "family": "elementwise",
                    "inputs": ["a"],
                    "outputs": ["a"],
                    "attributes": {"axis": 0},
                }
            ],
        },
        {
            "name": "bad",
            "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
            "tensors": [
                {"name": "x", "shape": [4, 8]},
                {"name": "y", "shape": [4]},
            ],
            "operations": [
                {
                    "name": "softmax",
                    "family": "softmax",
                    "inputs": ["x"],
                    "outputs": ["y"],
                    "attributes": {"axis": 2},
                }
            ],
        },
    ],
)
def test_source_intent_intake_rejects_invalid_or_execution_surface_data(
    payload: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        source_intent_from_mapping(payload)


def test_source_intent_intake_does_not_accept_source_text() -> None:
    with pytest.raises(TypeError, match="plain mapping"):
        source_intent_from_mapping("@triton.jit\ndef kernel(): pass")


@pytest.mark.parametrize(
    ("fixture_path", "artifact_builder"),
    (
        (
            Path("frontend") / "source_intent_intake_report.txt",
            lambda: build_source_intent_intake_report(
                source_intent_from_mapping(build_source_intent_data())
            ).dump(),
        ),
        (
            Path("frontend") / "source_intent_intake_module.txt",
            lambda: source_intent_from_mapping(build_source_intent_data()).dump(),
        ),
        (
            Path("frontend") / "source_intent_intake_metadata.txt",
            lambda: source_intent_to_triton_metadata(
                source_intent_from_mapping(build_source_intent_data())
            ).intake_report().dump(),
        ),
        (
            Path("hac_ir") / "source_intent_intake_mlp.txt",
            lambda: _compiled_source_intent_intake_graph().dump(IRStage.HAC_IR),
        ),
        (
            Path("runtime_plans") / "source_intent_intake_mlp.txt",
            lambda: _compiled_source_intent_intake_graph().dump_runtime_plan(),
        ),
        (
            Path("compiler_decisions") / "source_intent_intake_mlp.txt",
            lambda: _compiled_source_intent_intake_graph().dump_decision_report(),
        ),
    ),
)
def test_source_intent_intake_artifact_matches_golden(
    fixture_path: Path,
    artifact_builder: Callable[[], str],
) -> None:
    expected = (Path(__file__).parent / "golden" / fixture_path).read_text(
        encoding="utf-8"
    ).rstrip("\n")

    assert artifact_builder() == expected


def _compiled_source_intent_intake_graph():
    module = source_intent_from_mapping(build_source_intent_data())
    metadata = source_intent_to_triton_metadata(module)
    graph = metadata.to_compute_graph()
    return compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
