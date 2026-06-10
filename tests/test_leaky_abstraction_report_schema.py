from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from examples.leaky_abstraction_report import build_graph
from tuc import (
    LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES,
    LEAKY_ABSTRACTION_ARTIFACT_STATUS,
    LEAKY_ABSTRACTION_DEFAULT_ISSUES,
    LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS,
    LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION,
    LeakyAbstractionFact,
    build_leaky_abstraction_report,
    compile_graph,
    leaky_abstraction_report_to_dict,
)
from tuc.backends import LinearAlgebraSimulatorBackend
from tuc.ir import HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

SCHEMA_PATH = Path("schemas/leaky_abstraction_report.v0.schema.json")


def test_leaky_abstraction_report_schema_matches_runtime_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith("/schemas/leaky_abstraction_report.v0.schema.json")
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["artifact_status"]["const"] == (
        LEAKY_ABSTRACTION_ARTIFACT_STATUS
    )
    assert schema["properties"]["claim_boundary"]["const"] == (
        PERFORMANCE_PROOF_BOUNDARY_CONTRACT
    )
    assert schema["properties"]["performance_claim_status"]["const"] == (
        LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS
    )
    assert schema["properties"]["native_performance_claim"]["const"] is False
    assert schema["properties"]["performance_facts"]["maxItems"] == 128
    assert schema["$defs"]["fact_home"]["enum"] == list(
        LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES
    )


def test_leaky_abstraction_report_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    assert "native_performance_parity" not in schema["properties"]
    assert "raw_benchmark_output" not in schema["properties"]
    assert "device_id" not in schema["properties"]
    assert "hardware_serial" not in schema["properties"]
    assert "plugin_entrypoint" not in schema["properties"]
    assert "backend_artifact" not in schema["properties"]
    assert "generated_code" not in schema["properties"]
    assert schema["$defs"]["report_text"]["maxLength"] == 512


def test_leaky_abstraction_report_mapping_matches_schema_shape() -> None:
    schema = _load_schema()
    simulator = LinearAlgebraSimulatorBackend()
    compiled = compile_graph(build_graph(), [simulator.capability])
    report = build_leaky_abstraction_report(
        compiled.hac_ir,
        performance_facts=(
            LeakyAbstractionFact(
                fact_id="matmul_tile_shape",
                correct_home="backend_implementation",
                required_for_performance=True,
            ),
        ),
    )
    payload = leaky_abstraction_report_to_dict(report)

    assert sorted(payload) == sorted(schema["required"])
    assert payload["schema_version"] == LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION
    assert payload["issues"] == list(LEAKY_ABSTRACTION_DEFAULT_ISSUES)
    assert payload["checked_forbidden_attributes"] == sorted(
        HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES
    )
    assert payload["hac_ir_leak_detected"] is False


def test_leaky_abstraction_report_schema_is_referenced() -> None:
    schema_path = "schemas/leaky_abstraction_report.v0.schema.json"

    for path in (
        Path("docs/LEAKY_ABSTRACTION_REPORT.md"),
        Path("docs/PERFORMANCE_PROOF_BOUNDARY.md"),
        Path("docs/PERFORMANCE_PROOF_READINESS.md"),
        Path("rfcs/0067-leaky-abstraction-report.md"),
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
