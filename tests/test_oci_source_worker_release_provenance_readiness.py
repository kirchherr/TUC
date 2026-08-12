from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pytest

from examples.oci_source_worker_release_provenance_readiness import (
    ATTEST_ACTION,
    BLOCKED_CLAIMS,
    BUILDKIT_IMAGE,
    BUILDX_ACTION,
    BUILDX_VERSION,
    READINESS_CONTRACT,
    REQUIRED_CONTROLS,
    SCHEMA_VERSION,
    assert_report_contract,
    build_report,
)

SCHEMA_PATH = Path(
    "schemas/oci_source_worker_release_provenance_readiness_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json"
)


@lru_cache(maxsize=1)
def _report_text() -> str:
    return build_report()


def test_release_provenance_readiness_contract_passes() -> None:
    report = json.loads(_report_text())

    assert_report_contract(report)
    assert report["readiness_status"] == "PASS"
    assert report["readiness_contract"] == READINESS_CONTRACT
    assert report["attest_action"] == ATTEST_ACTION
    assert report["buildx_action"] == BUILDX_ACTION
    assert report["buildx_version"] == BUILDX_VERSION
    assert report["buildkit_image"] == BUILDKIT_IMAGE
    assert report["required_controls"] == list(REQUIRED_CONTROLS)
    assert report["blocked_claims"] == list(BLOCKED_CLAIMS)
    assert report["attested_release_artifact_configured"] is True
    assert report["external_attestation_verified"] is False
    assert report["published_worker_image_provenance"] is False
    assert report["production_source_sandbox"] is False
    assert report["execution_permission"] is False


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("external_attestation_verified", True),
        ("published_worker_image_provenance", True),
        ("production_source_ingestion", True),
        ("production_source_sandbox", True),
        ("execution_permission", True),
        ("attested_release_artifact_configured", False),
    ],
)
def test_release_provenance_readiness_rejects_claim_drift(
    field: str,
    value: object,
) -> None:
    report = json.loads(_report_text())
    report[field] = value

    with pytest.raises(ValueError, match=field):
        assert_report_contract(report)


def test_release_provenance_readiness_rejects_digest_drift() -> None:
    report = json.loads(_report_text())
    report["material_digests"]["dockerfile"] = "sha256:" + "0" * 64

    with pytest.raises(ValueError, match="report digest"):
        assert_report_contract(report)


def test_release_provenance_readiness_rejects_source_leak() -> None:
    report = json.loads(_report_text())
    report["artifact_name"] = "raw_source"

    with pytest.raises(ValueError):
        assert_report_contract(report)


def test_release_provenance_readiness_matches_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    report = json.loads(_report_text())

    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert schema["properties"]["readiness_contract"]["const"] == READINESS_CONTRACT
    assert set(schema["required"]) == set(report)
    assert set(schema["properties"]) == set(report)


def test_release_provenance_readiness_schema_rejects_unknown_field() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    report = json.loads(_report_text())
    report["unknown"] = True

    assert schema["additionalProperties"] is False
    assert "unknown" not in schema["properties"]


def test_release_provenance_readiness_matches_golden() -> None:
    assert _report_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_release_provenance_readiness_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/oci_source_worker_release_provenance_readiness.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")


def test_release_provenance_readiness_rejects_material_set_drift() -> None:
    report = deepcopy(json.loads(_report_text()))
    del report["material_digests"]["worker_source"]

    with pytest.raises(ValueError, match="material set"):
        assert_report_contract(report)
