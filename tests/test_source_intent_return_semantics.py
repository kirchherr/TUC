from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_intent_return_semantics import (
    build_aliases,
    build_report,
    build_source_intent_return_data,
)
from tuc.frontend import (
    SOURCE_INTENT_RETURN_POLICY,
    SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT,
    SourceIntentReturn,
    build_source_intent_return_semantics_report,
    dump_source_intent_return_semantics_report,
    source_intent_from_mapping,
    source_intent_return_aliases,
    source_intent_to_triton_metadata,
)

GOLDEN_PATH = Path("tests/golden/frontend/source_intent_return_semantics_report.txt")
SCHEMA_PATH = Path("schemas/source_intent.v0.schema.json")


def test_source_intent_return_semantics_aliases_public_outputs() -> None:
    module = source_intent_from_mapping(build_source_intent_return_data())
    report = build_source_intent_return_semantics_report(module)
    metadata = source_intent_to_triton_metadata(module)

    assert tuple(source_return.public_name for source_return in module.returns) == (
        "api_y",
    )
    assert tuple(source_return.tensor_name for source_return in module.returns) == (
        "y",
    )
    assert source_intent_return_aliases(module) == {"api_y": "y"}
    assert build_aliases() == {"api_y": "y"}
    assert report.return_semantics_contract == SOURCE_INTENT_RETURN_SEMANTICS_CONTRACT
    assert report.return_policy == SOURCE_INTENT_RETURN_POLICY
    assert report.return_count == 1
    assert dict(report.aliases) == {"api_y": "y"}
    assert metadata.metadata["frontend.source_intent_return_policy"] == (
        SOURCE_INTENT_RETURN_POLICY
    )
    assert metadata.metadata["frontend.source_intent_return_aliases"] == ("api_y:y",)


def test_source_intent_return_semantics_dump_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    report = build_source_intent_return_semantics_report(
        source_intent_from_mapping(build_source_intent_return_data())
    )
    assert dump_source_intent_return_semantics_report(report) == build_report()


def test_source_intent_return_semantics_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_intent_return_semantics.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "source_intent_return_semantics.data_only.v0" in completed.stdout
    assert 'returns = "api_y:y"' in completed.stdout
    assert "python_source" not in completed.stdout
    assert "runtime_output_contract" in completed.stdout


def test_source_intent_return_semantics_requires_explicit_returns() -> None:
    payload = build_source_intent_return_data()
    payload.pop("returns")
    module = source_intent_from_mapping(payload)

    with pytest.raises(ValueError, match="require explicit returns"):
        build_source_intent_return_semantics_report(module)


@pytest.mark.parametrize(
    ("tensor_name", "message"),
    (
        ("z", "unknown tensor"),
        ("a", "produced by an operation"),
        ("c", "must be terminal"),
    ),
)
def test_source_intent_return_semantics_rejects_invalid_return_targets(
    tensor_name: str,
    message: str,
) -> None:
    payload = build_source_intent_return_data()
    payload["returns"] = [{"public_name": "api_y", "tensor_name": tensor_name}]

    with pytest.raises(ValueError, match=message):
        source_intent_from_mapping(payload)


def test_source_intent_return_semantics_rejects_duplicate_public_names() -> None:
    payload = build_source_intent_return_data()
    payload["returns"] = [
        {"public_name": "api_y", "tensor_name": "y"},
        {"public_name": "api_y", "tensor_name": "y"},
    ]

    with pytest.raises(ValueError, match="return public names must be unique"):
        source_intent_from_mapping(payload)


def test_source_intent_return_semantics_rejects_unknown_return_fields() -> None:
    payload = build_source_intent_return_data()
    payload["returns"] = [
        {
            "public_name": "api_y",
            "tensor_name": "y",
            "python_source": "return y",
        }
    ]

    with pytest.raises(ValueError, match="unsupported keys"):
        source_intent_from_mapping(payload)


def test_source_intent_return_requires_boolean_required_flag() -> None:
    with pytest.raises(TypeError, match="required flag"):
        SourceIntentReturn(
            public_name="api_y",
            tensor_name="y",
            required="true",  # type: ignore[arg-type]
        )


def test_source_intent_return_schema_documents_optional_returns() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert "returns" not in schema["required"]
    assert schema["properties"]["returns"]["items"]["$ref"] == "#/$defs/return"
    assert schema["$defs"]["return"]["additionalProperties"] is False
    assert schema["$defs"]["return"]["required"] == ["public_name", "tensor_name"]
    assert "python_source" not in schema["$defs"]["return"]["properties"]


def test_source_intent_return_semantics_docs_are_referenced() -> None:
    docs_path = "docs/SOURCE_INTENT_RETURN_SEMANTICS.md"

    for path in (
        Path("README.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0116-source-intent-return-semantics.md"),
    ):
        assert docs_path in path.read_text(encoding="utf-8")
