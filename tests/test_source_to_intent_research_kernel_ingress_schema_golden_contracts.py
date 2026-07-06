from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

SCHEMA_DIR = Path("schemas")
GOLDEN_DIR = Path("tests/golden/frontend")

SCHEMA_GOLDEN_PAIRS = (
    (
        "source_to_intent_research_kernel_ingress_backend_equivalence_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_backend_equivalence.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_boundary_budget_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_boundary_budget.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_diagnostics_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_diagnostics_report.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_e2e_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_idiom_alignment_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_idiom_alignment.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_proof_bundle_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_proof_bundle.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_rejection_coverage_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_rejection_coverage.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_matrix_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_matrix.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_output_closure_index_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_output_closure_index.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_runtime_step_trace_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_runtime_step_trace.json",
    ),
    (
        "source_to_intent_research_kernel_ingress_workload_scope_report.v0.schema.json",
        "source_to_intent_research_kernel_ingress_workload_scope.json",
    ),
)

COUNT_ARRAY_BINDINGS = {
    "accepted_case_count": "accepted_observations",
    "accepted_source_count": "cases",
    "case_count": "cases",
    "observed_case_count": "case_requirements",
    "required_case_count": "case_requirements",
}


@pytest.mark.parametrize(("schema_name", "golden_name"), SCHEMA_GOLDEN_PAIRS)
def test_kernel_ingress_schema_fixed_counts_match_goldens(
    schema_name: str,
    golden_name: str,
) -> None:
    schema = _load_json(SCHEMA_DIR / schema_name)
    golden = _load_json(GOLDEN_DIR / golden_name)
    properties = schema["properties"]

    for count_key, array_key in COUNT_ARRAY_BINDINGS.items():
        if count_key not in golden or count_key not in properties:
            continue
        assert properties[count_key]["const"] == golden[count_key], count_key
        if array_key in golden:
            assert golden[count_key] == len(golden[array_key]), array_key


@pytest.mark.parametrize(("schema_name", "golden_name"), SCHEMA_GOLDEN_PAIRS)
def test_kernel_ingress_schema_fixed_arrays_match_goldens(
    schema_name: str,
    golden_name: str,
) -> None:
    schema = _load_json(SCHEMA_DIR / schema_name)
    golden = _load_json(GOLDEN_DIR / golden_name)

    for property_name, actual_value in golden.items():
        property_schema = schema["properties"].get(property_name)
        if not isinstance(actual_value, list) or not isinstance(property_schema, dict):
            continue

        fixed_length = _fixed_array_length(property_schema)
        if fixed_length is not None:
            assert fixed_length == len(actual_value), property_name

        _assert_prefix_items_match_actual(
            property_name,
            property_schema,
            actual_value,
        )


@pytest.mark.parametrize(("schema_name", "_golden_name"), SCHEMA_GOLDEN_PAIRS)
def test_kernel_ingress_schema_objects_fail_closed(
    schema_name: str,
    _golden_name: str,
) -> None:
    schema = _load_json(SCHEMA_DIR / schema_name)

    _assert_objects_fail_closed(schema, path=schema_name)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fixed_array_length(schema: dict[str, Any]) -> int | None:
    min_items = schema.get("minItems")
    max_items = schema.get("maxItems")
    if isinstance(min_items, int) and min_items == max_items:
        return min_items
    return None


def _assert_prefix_items_match_actual(
    property_name: str,
    property_schema: dict[str, Any],
    actual_value: list[Any],
) -> None:
    prefix_items = property_schema.get("prefixItems")
    if not isinstance(prefix_items, list):
        return

    assert len(prefix_items) <= len(actual_value), property_name
    for index, item_schema in enumerate(prefix_items):
        if not isinstance(item_schema, dict):
            continue
        actual_item = actual_value[index]
        _assert_const_schema_matches_actual(
            f"{property_name}[{index}]",
            item_schema,
            actual_item,
        )


def _assert_const_schema_matches_actual(
    path: str,
    schema: dict[str, Any],
    actual_value: Any,
) -> None:
    if "const" in schema:
        assert schema["const"] == actual_value, path
        return

    if schema.get("type") == "array" and isinstance(actual_value, list):
        fixed_length = _fixed_array_length(schema)
        if fixed_length is not None:
            assert fixed_length == len(actual_value), path
        _assert_prefix_items_match_actual(path, schema, actual_value)
        return

    if schema.get("type") != "object" or not isinstance(actual_value, dict):
        return

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return
    for field_name, field_schema in properties.items():
        if field_name not in actual_value or not isinstance(field_schema, dict):
            continue
        _assert_const_schema_matches_actual(
            f"{path}.{field_name}",
            field_schema,
            actual_value[field_name],
        )


def _assert_objects_fail_closed(schema: Any, path: str) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False, path
        for key, value in schema.items():
            _assert_objects_fail_closed(value, path=f"{path}.{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            _assert_objects_fail_closed(value, path=f"{path}[{index}]")
