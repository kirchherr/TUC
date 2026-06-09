from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.source_intent_metadata import build_source_intent
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_INTENT_METADATA_CONTRACT,
    build_source_intent_metadata_report,
    source_intent_to_triton_metadata,
)
from tuc.ir import IRStage, OperationKind


def test_source_intent_metadata_conversion_preserves_intent() -> None:
    module = build_source_intent()
    metadata = source_intent_to_triton_metadata(module)

    assert metadata.name == "source_intent_mlp"
    assert metadata.metadata["frontend.source_intent_contract"] == module.contract
    assert (
        metadata.metadata["frontend.source_intent_conversion_contract"]
        == SOURCE_INTENT_METADATA_CONTRACT
    )
    assert tuple(tensor.name for tensor in metadata.tensors) == ("a", "b", "c", "y")
    assert metadata.operations[0].kind is OperationKind.MATMUL
    assert metadata.operations[0].hints.prefer_linear_accelerator is True
    assert metadata.operations[0].hints.max_error_budget == 0.02
    assert metadata.operations[1].kind is OperationKind.ELEMENTWISE


def test_source_intent_metadata_conversion_rejects_non_module() -> None:
    with pytest.raises(TypeError, match="SourceIntentModule"):
        source_intent_to_triton_metadata("def kernel(): pass")  # type: ignore[arg-type]


def test_source_intent_metadata_conversion_has_no_source_or_preflight_entry() -> None:
    module = build_source_intent()

    assert not hasattr(module, "to_metadata")
    assert not hasattr(module, "to_compute_graph")
    assert not hasattr(module, "from_source")


@pytest.mark.parametrize(
    ("fixture_path", "artifact_builder"),
    (
        (
            Path("frontend") / "source_intent_metadata_report.txt",
            lambda: build_source_intent_metadata_report(build_source_intent()).dump(),
        ),
        (
            Path("frontend") / "source_intent_metadata_intake.txt",
            lambda: source_intent_to_triton_metadata(
                build_source_intent()
            ).intake_report().dump(),
        ),
        (
            Path("hac_ir") / "source_intent_metadata_mlp.txt",
            lambda: _compiled_source_intent_graph().dump(IRStage.HAC_IR),
        ),
        (
            Path("runtime_plans") / "source_intent_metadata_mlp.txt",
            lambda: _compiled_source_intent_graph().dump_runtime_plan(),
        ),
        (
            Path("compiler_decisions") / "source_intent_metadata_mlp.txt",
            lambda: _compiled_source_intent_graph().dump_decision_report(),
        ),
    ),
)
def test_source_intent_metadata_artifact_matches_golden(
    fixture_path: Path,
    artifact_builder: Callable[[], str],
) -> None:
    expected = (Path(__file__).parent / "golden" / fixture_path).read_text(
        encoding="utf-8"
    ).rstrip("\n")

    assert artifact_builder() == expected


def _compiled_source_intent_graph():
    metadata = source_intent_to_triton_metadata(build_source_intent())
    graph = metadata.to_compute_graph()
    return compile_graph(graph, [LinearAlgebraSimulatorBackend().capability])
