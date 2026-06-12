from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    source_intent_from_mapping,
)

SCHEMA_PATH = Path("schemas/source_intent.v0.schema.json")


def test_source_intent_json_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/source_intent.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INTENT_SCHEMA_VERSION
    )
    assert schema["required"] == ["name", "schema_version", "tensors", "operations"]

    defs = schema["$defs"]
    assert defs["operation"]["properties"]["family"]["enum"] == [
        "elementwise",
        "matmul",
        "reduction",
        "softmax",
    ]
    assert defs["operation"]["properties"]["attributes"]["$ref"] == (
        "#/$defs/attributes"
    )
    assert defs["attributes"]["additionalProperties"] is False
    assert defs["attributes"]["properties"]["axis"]["minimum"] == -8
    assert defs["attributes"]["properties"]["axis"]["maximum"] == 7
    assert defs["tensor"]["properties"]["shape"]["maxItems"] == 8
    assert defs["tensor_name_list"]["maxItems"] == 16
    assert defs["dimension"]["maximum"] == 2147483647
    assert "returns" not in schema["required"]
    assert schema["properties"]["returns"]["items"]["$ref"] == "#/$defs/return"
    assert defs["return"]["additionalProperties"] is False
    assert defs["return"]["required"] == ["public_name", "tensor_name"]


def test_source_intent_json_schema_rejects_unknown_fields_by_contract() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    defs = schema["$defs"]
    hint_properties = set(defs["hints"]["properties"])
    assert "prefer_analog_linear" not in hint_properties
    assert "backend" not in hint_properties
    attribute_properties = set(defs["attributes"]["properties"])
    assert attribute_properties == {"axis"}
    assert "python_source" not in schema["properties"]
    assert "file_path" not in defs["tensor"]["properties"]
    assert "plugin_entrypoint" not in defs["operation"]["properties"]
    assert "python_source" not in defs["return"]["properties"]


def test_source_intent_json_schema_corpus_examples_align_with_intake() -> None:
    valid = json.loads(
        Path("tests/corpus/source_intent_intake/valid_mlp.json").read_text(
            encoding="utf-8"
        )
    )
    module = source_intent_from_mapping(valid)

    assert module.name == "seed_mlp"
    assert tuple(operation.family for operation in module.operations) == (
        "matmul",
        "elementwise",
    )


def test_source_intent_json_schema_is_referenced_by_docs() -> None:
    schema_path = "schemas/source_intent.v0.schema.json"

    for path in (
        Path("docs/SOURCE_INTENT_INTAKE.md"),
        Path("docs/SOURCE_INTENT_SCHEMA.md"),
        Path("rfcs/0058-source-intent-json-schema.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


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
