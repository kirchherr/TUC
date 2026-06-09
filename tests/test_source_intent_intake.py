from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from examples.source_intent_intake import build_source_intent_data
from tuc.frontend import (
    SOURCE_INTENT_INTAKE_CONTRACT,
    SOURCE_INTENT_SCHEMA_VERSION,
    build_source_intent_intake_report,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)


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
