from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from examples.objective_beta_reproducibility_capsule import (
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_POLICY,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_CONTRACT,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION,
    ObjectiveBetaReproducibilityCapsuleError,
    assert_objective_beta_reproducibility_capsule_report_contract,
    build_report,
)

GOLDEN_PATH = Path(
    "tests/golden/proofs/objective_beta_reproducibility_capsule.json"
)
SCHEMA_PATH = Path(
    "schemas/objective_beta_reproducibility_capsule_report.v0.schema.json"
)


@lru_cache(maxsize=1)
def _cached_text() -> str:
    return build_report()


@lru_cache(maxsize=1)
def _cached_payload() -> dict[str, Any]:
    return json.loads(_cached_text())


def test_objective_beta_reproducibility_capsule_contract() -> None:
    report = _cached_payload()

    assert_objective_beta_reproducibility_capsule_report_contract(report)
    assert report["schema_version"] == OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION
    assert report["capsule_contract"] == OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_CONTRACT
    assert report["capsule_id"] == OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID
    assert report["artifact_policy"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_POLICY
    )
    assert report["replay_policy"] == OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY
    assert report["evidence_count"] == len(
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS
    )
    assert report["source_ingestion_admitted"] is False
    assert report["native_performance_claim"] is False
    assert report["vendor_replacement_claim"] is False


def test_objective_beta_reproducibility_capsule_matches_golden() -> None:
    assert _cached_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_objective_beta_reproducibility_capsule_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/objective_beta_reproducibility_capsule.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"evidence_count": 11' in completed.stdout
    assert '"source_ingestion_admitted": false' in completed.stdout
    assert "source_text" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "host_path" not in completed.stdout
    assert "device_id" not in completed.stdout


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("source_ingestion_admitted", True, "source_ingestion_admitted"),
        ("native_performance_claim", True, "native_performance_claim"),
        ("vendor_replacement_claim", True, "vendor_replacement_claim"),
        ("external_approval_required", False, "external_approval_required"),
    ),
)
def test_objective_beta_reproducibility_capsule_rejects_claim_boundary_drift(
    field: str,
    value: object,
    match: str,
) -> None:
    report = dict(_cached_payload())
    report[field] = value

    with pytest.raises(ObjectiveBetaReproducibilityCapsuleError, match=match):
        assert_objective_beta_reproducibility_capsule_report_contract(report)


def test_objective_beta_reproducibility_capsule_rejects_evidence_order_drift() -> None:
    report = dict(_cached_payload())
    evidence = list(report["evidence"])
    evidence[0], evidence[1] = evidence[1], evidence[0]
    report["evidence"] = evidence

    with pytest.raises(ObjectiveBetaReproducibilityCapsuleError, match="evidence order"):
        assert_objective_beta_reproducibility_capsule_report_contract(report)


def test_objective_beta_reproducibility_capsule_rejects_source_leakage() -> None:
    report = dict(_cached_payload())
    report["source_text"] = "untrusted"

    with pytest.raises(ObjectiveBetaReproducibilityCapsuleError, match="keys changed"):
        assert_objective_beta_reproducibility_capsule_report_contract(report)


def test_objective_beta_reproducibility_capsule_schema_matches_contract() -> None:
    schema = _load_schema()
    report = _cached_payload()

    assert sorted(report) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION
    )
    assert schema["properties"]["capsule_contract"]["const"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_CONTRACT
    )
    assert schema["properties"]["capsule_id"]["const"] == (
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID
    )
    assert schema["properties"]["evidence_count"]["const"] == len(
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS
    )


def test_objective_beta_reproducibility_capsule_schema_fails_closed() -> None:
    schema = _load_schema()

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
        assert "source_text" not in object_schema.get("properties", {})
        assert "runtime_handle" not in object_schema.get("properties", {})
        assert "host_path" not in object_schema.get("properties", {})
        assert "device_id" not in object_schema.get("properties", {})


def test_objective_beta_reproducibility_capsule_docs_are_linked() -> None:
    expected = (
        "OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE.md",
        "schemas/objective_beta_reproducibility_capsule_report.v0.schema.json",
        "examples/objective_beta_reproducibility_capsule.py",
        "tests/golden/proofs/objective_beta_reproducibility_capsule.json",
        "rfcs/0281-objective-beta-reproducibility-capsule.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE.md"),
        Path("rfcs/0281-objective-beta-reproducibility-capsule.md"),
    ):
        text = path.read_text(encoding="utf-8")
        for marker in expected:
            assert marker in text or path.name == marker.rsplit("/", 1)[-1]


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
