from __future__ import annotations

import json
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from tuc.frontend import (
    SOURCE_INTENT_INTAKE_CONTRACT,
    SourceIntentModule,
    build_source_intent_intake_report,
    source_intent_from_mapping,
)

CORPUS_DIR = Path("tests/corpus/source_intent_intake")
SEED_PAYLOADS = {
    path.name: json.loads(path.read_text(encoding="utf-8"))
    for path in sorted(CORPUS_DIR.glob("*.json"))
}

JSON_SCALARS = st.none() | st.booleans() | st.integers() | st.floats(
    allow_nan=False,
    allow_infinity=False,
    width=32,
) | st.text(max_size=64)
JSON_LIKE = st.recursive(
    JSON_SCALARS,
    lambda children: st.lists(children, max_size=8)
    | st.dictionaries(st.text(max_size=32), children, max_size=8),
    max_leaves=64,
)


@given(JSON_LIKE)
@settings(max_examples=100, deadline=None)
def test_source_intent_intake_handles_arbitrary_json_like_data(data: object) -> None:
    try:
        module = source_intent_from_mapping(data)
    except (TypeError, ValueError):
        return

    _assert_safe_module(module)


@given(st.lists(st.sampled_from(tuple(SEED_PAYLOADS.values())), min_size=1, max_size=4))
@settings(max_examples=40, deadline=None)
def test_source_intent_intake_handles_seed_wrapped_data(seeds: list[object]) -> None:
    payload = {"name": "seed_wrapper", "schema_version": "source_intent.v0", "seeds": seeds}

    try:
        module = source_intent_from_mapping(payload)
    except (TypeError, ValueError):
        return

    _assert_safe_module(module)


def test_source_intent_intake_seed_corpus_preserves_expected_decisions() -> None:
    cases = {
        "valid_mlp.json": True,
        "unsupported_schema.json": False,
        "source_text_escape.json": False,
        "backend_hint_escape.json": False,
        "unknown_tensor_reference.json": False,
    }

    for filename, accepted in cases.items():
        if accepted:
            module = source_intent_from_mapping(SEED_PAYLOADS[filename])
            _assert_safe_module(module)
        else:
            try:
                source_intent_from_mapping(SEED_PAYLOADS[filename])
            except (TypeError, ValueError):
                continue
            raise AssertionError(f"{filename} should fail closed")


def _assert_safe_module(module: SourceIntentModule) -> None:
    assert isinstance(module, SourceIntentModule)
    assert not hasattr(module, "to_compute_graph")
    assert not hasattr(module, "to_metadata")
    report = build_source_intent_intake_report(module)
    assert report.intake_contract == SOURCE_INTENT_INTAKE_CONTRACT
    assert "source_parsing" in report.blocked_execution_surfaces
    assert "python_import" in report.blocked_execution_surfaces
    assert "metadata" in report.blocked_compiler_outputs
    assert "ComputeGraph" not in report.dump()
