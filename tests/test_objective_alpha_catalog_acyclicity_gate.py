from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.objective_alpha_catalog_acyclicity_gate import (
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_EVIDENCE_POLICY,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_CONTRACT,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_ID,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCOPE,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_STATUS,
    OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_REQUIRED_INVARIANTS,
    ObjectiveAlphaCatalogAcyclicityGateError,
    assert_objective_alpha_catalog_acyclicity_gate_report_contract,
    build_objective_alpha_catalog_acyclicity_gate_report,
    build_report,
)
from tuc.objective_alpha import (
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
    OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID,
)

SCHEMA_PATH = Path("schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json")
GOLDEN_PATH = Path("tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json")
DOC_PATH = Path("docs/OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md")
RFC_PATH = Path("rfcs/0276-objective-alpha-catalog-acyclicity-gate.md")


@lru_cache(maxsize=1)
def _cached_report() -> dict[str, object]:
    return build_objective_alpha_catalog_acyclicity_gate_report()


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


def test_objective_alpha_catalog_acyclicity_gate_passes() -> None:
    report = _cached_report()

    assert_objective_alpha_catalog_acyclicity_gate_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION
    assert report["gate_contract"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_CONTRACT
    assert report["gate_id"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_ID
    assert report["gate_scope"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCOPE
    assert report["gate_status"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_STATUS
    assert report["evidence_policy"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_EVIDENCE_POLICY
    assert report["catalog_id"] == OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ID
    assert report["catalog_entry_count"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert report["catalog_entry_ids"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert report["forbidden_downstream_dependency_ids"] == list(
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS
    )
    assert report["required_invariants"] == list(
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_REQUIRED_INVARIANTS
    )
    assert report["cycle_count"] == 0
    assert report["detected_cycles"] == []
    assert report["issues"] == []
    assert report["source_free"] is True
    assert report["surface_opened"] is False
    assert len(report["entry_scan_results"]) == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    for scan_result, expected_id in zip(
        report["entry_scan_results"],
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS,
        strict=True,
    ):
        assert scan_result["evidence_id"] == expected_id
        assert scan_result["forbidden_downstream_dependency_hits"] == []
        assert scan_result["source_free"] is True
        assert str(scan_result["report_digest"]).startswith("sha256:")


def test_objective_alpha_catalog_acyclicity_gate_dump_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_objective_alpha_catalog_acyclicity_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_alpha_catalog_acyclicity_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "objective_alpha.catalog_acyclicity_gate.data_only.v0" in completed.stdout
    assert '"cycle_count": 0' in completed.stdout
    assert '"gate_passed": true' in completed.stdout
    assert "real_triton_first_slice_evidence_portfolio" in completed.stdout
    assert "research_scope_claim_gate" in completed.stdout
    assert '"forbidden_downstream_dependency_hits": []' in completed.stdout
    assert '"source_text":' not in completed.stdout
    assert '"raw_tensor_value":' not in completed.stdout
    assert '"runtime_handle":' not in completed.stdout
    assert '"host_path":' not in completed.stdout
    assert '"device_id":' not in completed.stdout


def test_objective_alpha_catalog_acyclicity_gate_rejects_downstream_dependency() -> None:
    with pytest.raises(
        ObjectiveAlphaCatalogAcyclicityGateError,
        match="forbidden downstream",
    ):
        build_objective_alpha_catalog_acyclicity_gate_report(
            entry_report_text_overrides={
                "real_triton_first_slice_evidence_portfolio": (
                    '{"artifact_id":"research_scope_claim_gate"}'
                )
            }
        )


def test_objective_alpha_catalog_acyclicity_gate_rejects_source_leakage() -> None:
    with pytest.raises(
        ObjectiveAlphaCatalogAcyclicityGateError,
        match="forbidden fragment",
    ):
        build_objective_alpha_catalog_acyclicity_gate_report(
            entry_report_text_overrides={
                "first_real_triton_kernel_path": '{"source_text":"x"}'
            }
        )


def test_objective_alpha_catalog_acyclicity_gate_rejects_contract_drift() -> None:
    report = dict(_cached_report())
    report["cycle_count"] = 1

    with pytest.raises(ObjectiveAlphaCatalogAcyclicityGateError, match="cycle_count"):
        assert_objective_alpha_catalog_acyclicity_gate_report_contract(report)


def test_objective_alpha_catalog_acyclicity_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_report()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == (
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_ID
    )
    assert schema["properties"]["gate_scope"]["const"] == (
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCOPE
    )
    assert schema["properties"]["evidence_policy"]["const"] == (
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_EVIDENCE_POLICY
    )
    assert schema["properties"]["catalog_entry_count"]["const"] == len(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert _prefix_consts(schema["properties"]["catalog_entry_ids"]) == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert _prefix_consts(
        schema["properties"]["forbidden_downstream_dependency_ids"]
    ) == list(OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS)
    assert _prefix_consts(schema["properties"]["required_invariants"]) == list(
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_REQUIRED_INVARIANTS
    )


def test_objective_alpha_catalog_acyclicity_gate_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "backend_artifact",
        "command_line",
        "device_id",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
    }
    for object_schema in _iter_object_schemas(schema):
        assert not (set(object_schema.get("properties", {})) & forbidden_properties)


def test_objective_alpha_catalog_acyclicity_gate_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_SCHEMA_VERSION
    assert golden["gate_status"] == OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE_STATUS
    assert golden["cycle_count"] == 0
    assert golden["detected_cycles"] == []
    assert golden["issues"] == []
    assert golden["catalog_entry_ids"] == list(
        OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_EXPECTED_ENTRY_IDS
    )
    assert golden["forbidden_downstream_dependency_ids"] == list(
        OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_FORBIDDEN_DOWNSTREAM_IDS
    )


def test_objective_alpha_catalog_acyclicity_gate_is_documented() -> None:
    schema_path = "schemas/objective_alpha_catalog_acyclicity_gate_report.v0.schema.json"
    example_path = "examples/objective_alpha_catalog_acyclicity_gate.py"
    golden_path = "tests/golden/proofs/objective_alpha_catalog_acyclicity_gate.json"
    doc_path = "docs/OBJECTIVE_ALPHA_CATALOG_ACYCLICITY_GATE.md"
    rfc_path = "rfcs/0276-objective-alpha-catalog-acyclicity-gate.md"

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG.md"),
        Path("docs/OBJECTIVE_ALPHA_PUBLIC_EVIDENCE_CATALOG_ADMISSION_GATE.md"),
        DOC_PATH,
        RFC_PATH,
    ):
        text = path.read_text(encoding="utf-8")
        assert example_path in text
        assert schema_path in text
        assert golden_path in text
        assert doc_path in text or path == DOC_PATH
        assert rfc_path in text or path == RFC_PATH


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))


def _prefix_consts(schema: dict[str, Any]) -> list[str]:
    return [str(item["const"]) for item in schema["prefixItems"]]


def _assert_objects_fail_closed(schema: Any) -> None:
    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False


def _iter_object_schemas(schema: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            found.append(schema)
        for value in schema.values():
            found.extend(_iter_object_schemas(value))
    elif isinstance(schema, list):
        for item in schema:
            found.extend(_iter_object_schemas(item))
    return found
