from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.objective_beta_reproducibility_capsule import (
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS,
)
from examples.objective_beta_reproducibility_gate import (
    OBJECTIVE_BETA_REPRODUCIBILITY_GATE_CONTRACT,
    OBJECTIVE_BETA_REPRODUCIBILITY_GATE_FORBIDDEN_EXECUTION_SURFACES,
    OBJECTIVE_BETA_REPRODUCIBILITY_GATE_ID,
    OBJECTIVE_BETA_REPRODUCIBILITY_GATE_SCHEMA_VERSION,
    ObjectiveBetaReproducibilityGateError,
    assert_objective_beta_reproducibility_gate_report_contract,
    build_objective_beta_reproducibility_gate_report,
    build_report,
)

CAPSULE_PATH = Path(
    "tests/golden/proofs/objective_beta_reproducibility_capsule.json"
)
GOLDEN_PATH = Path("tests/golden/proofs/objective_beta_reproducibility_gate.json")
SCHEMA_PATH = Path(
    "schemas/objective_beta_reproducibility_gate_report.v0.schema.json"
)


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


@lru_cache(maxsize=1)
def _cached_payload() -> dict[str, Any]:
    return json.loads(_cached_text())


def test_objective_beta_reproducibility_gate_contract() -> None:
    report = _cached_payload()

    assert_objective_beta_reproducibility_gate_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_BETA_REPRODUCIBILITY_GATE_SCHEMA_VERSION
    assert report["gate_contract"] == OBJECTIVE_BETA_REPRODUCIBILITY_GATE_CONTRACT
    assert report["gate_id"] == OBJECTIVE_BETA_REPRODUCIBILITY_GATE_ID
    assert report["gate_passed"] is True
    assert report["verified_artifact_count"] == len(
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS
    )
    assert report["claim_link_verified"] is True
    assert report["evidence_links_verified"] is True
    assert report["source_ingestion_admitted"] is False


def test_objective_beta_reproducibility_gate_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_objective_beta_reproducibility_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_beta_reproducibility_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"gate_passed": true' in completed.stdout
    assert '"verified_artifact_count": 9' in completed.stdout
    assert "source_text" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout


def test_objective_beta_reproducibility_gate_detects_artifact_tampering() -> None:
    artifact_texts = _read_artifact_texts()
    artifact_id = "objective_alpha_research_claim_gate"
    artifact_texts[artifact_id] = artifact_texts[artifact_id] + "\n"

    with pytest.raises(ObjectiveBetaReproducibilityGateError, match="digest mismatch"):
        build_objective_beta_reproducibility_gate_report(
            CAPSULE_PATH.read_text(encoding="utf-8"),
            artifact_texts=artifact_texts,
        )


def test_objective_beta_reproducibility_gate_rejects_allowlist_drift() -> None:
    artifact_texts = _read_artifact_texts()
    artifact_texts["unreviewed_artifact"] = "{}\n"

    with pytest.raises(ObjectiveBetaReproducibilityGateError, match="allowlist mismatch"):
        build_objective_beta_reproducibility_gate_report(
            CAPSULE_PATH.read_text(encoding="utf-8"),
            artifact_texts=artifact_texts,
        )


def test_objective_beta_reproducibility_gate_rejects_source_leakage() -> None:
    artifact_texts = _read_artifact_texts()
    artifact_texts["objective_alpha_research_claim_gate"] = (
        '{"source_text":"untrusted"}\n'
    )

    with pytest.raises(ObjectiveBetaReproducibilityGateError, match="forbidden"):
        build_objective_beta_reproducibility_gate_report(
            CAPSULE_PATH.read_text(encoding="utf-8"),
            artifact_texts=artifact_texts,
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("gate_passed", False, "gate_passed"),
        ("claim_link_verified", False, "claim_link_verified"),
        ("evidence_links_verified", False, "evidence_links_verified"),
        ("source_ingestion_admitted", True, "source_ingestion_admitted"),
        ("native_performance_claim", True, "native_performance_claim"),
        ("vendor_replacement_claim", True, "vendor_replacement_claim"),
    ),
)
def test_objective_beta_reproducibility_gate_rejects_contract_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_payload())
    report[field] = value

    with pytest.raises(ObjectiveBetaReproducibilityGateError, match=match):
        assert_objective_beta_reproducibility_gate_report_contract(report)


def test_objective_beta_reproducibility_gate_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_payload()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_GATE_SCHEMA_VERSION
    )
    assert schema["properties"]["gate_contract"]["const"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_GATE_CONTRACT
    )
    assert schema["properties"]["gate_id"]["const"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_GATE_ID
    )
    assert schema["properties"]["verified_artifact_count"]["const"] == len(
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS
    )
    assert schema["properties"]["forbidden_execution_surfaces"]["const"] == list(
        OBJECTIVE_BETA_REPRODUCIBILITY_GATE_FORBIDDEN_EXECUTION_SURFACES
    )


def test_objective_beta_reproducibility_gate_schema_fails_closed() -> None:
    schema = _load_schema()

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
        assert "source_text" not in object_schema.get("properties", {})
        assert "runtime_handle" not in object_schema.get("properties", {})
        assert "host_path" not in object_schema.get("properties", {})
        assert "device_id" not in object_schema.get("properties", {})


def test_objective_beta_reproducibility_gate_docs_are_linked() -> None:
    expected = (
        "OBJECTIVE_BETA_REPRODUCIBILITY_GATE.md",
        "schemas/objective_beta_reproducibility_gate_report.v0.schema.json",
        "examples/objective_beta_reproducibility_gate.py",
        "tests/golden/proofs/objective_beta_reproducibility_gate.json",
        "rfcs/0281-objective-beta-reproducibility-capsule.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_BETA_REPRODUCIBILITY_GATE.md"),
        Path("rfcs/0281-objective-beta-reproducibility-capsule.md"),
    ):
        text = path.read_text(encoding="utf-8")
        for marker in expected:
            assert marker in text or path.name == marker.rsplit("/", 1)[-1]


def _read_artifact_texts() -> dict[str, str]:
    return {
        artifact_id: path.read_text(encoding="utf-8")
        for artifact_id, path in OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS.items()
    }


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8-sig"))


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
