from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.proof_of_backend_equivalence import (
    PROOF_OF_BACKEND_EQUIVALENCE_CONTRACT,
    PROOF_OF_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION,
    assert_proof_of_backend_equivalence_report_contract,
    build_proof_of_backend_equivalence_report,
    build_report,
)

GOLDEN_PATH = Path("tests/golden/proofs/proof_of_backend_equivalence.json")
SCHEMA_PATH = Path("schemas/proof_of_backend_equivalence_report.v0.schema.json")


def test_proof_of_backend_equivalence_report_shape() -> None:
    report = build_proof_of_backend_equivalence_report()
    assert_proof_of_backend_equivalence_report_contract(report)

    assert report["schema_version"] == PROOF_OF_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
    assert report["proof_contract"] == PROOF_OF_BACKEND_EQUIVALENCE_CONTRACT
    assert report["proof_status"] == "PASS"
    assert report["graph_name"] == "runtime_mixed_backend_equivalence"
    assert report["baseline_backend_sequence"] == [
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
        "reference-cpu",
    ]
    assert report["candidate_backend_sequence"] == [
        "systolic-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    ]
    assert report["terminal_output_checks"][0]["comparison_status"] == "matched"


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("proof_status", "WARN", "proof_status"),
        ("comparison_count", 2, "comparison_count"),
        ("raw_tensor_value", [], "top-level report"),
        ("candidate_placement", "gpu", "candidate_placement"),
    ],
)
def test_proof_of_backend_equivalence_contract_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_proof_of_backend_equivalence_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_proof_of_backend_equivalence_report_contract(report)


def test_proof_of_backend_equivalence_contract_rejects_output_drift() -> None:
    report = build_proof_of_backend_equivalence_report()
    checks = report["terminal_output_checks"]
    assert isinstance(checks, list)
    assert isinstance(checks[0], dict)
    checks[0]["comparison_status"] = "mismatched"

    with pytest.raises(ValueError, match="comparison_status drift"):
        assert_proof_of_backend_equivalence_report_contract(report)


def test_proof_of_backend_equivalence_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_proof_of_backend_equivalence_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/proof_of_backend_equivalence.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"proof_status": "PASS"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert '"comparison_status": "matched"' in completed.stdout
    assert "omitted_by_policy" in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_value" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "python_source" not in completed.stdout


def test_proof_of_backend_equivalence_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        PROOF_OF_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["proof_contract"]["const"] == (
        PROOF_OF_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert schema["properties"]["proof_status"]["const"] == "PASS"
    assert schema["properties"]["comparison_count"]["const"] == 1
    assert schema["$defs"]["terminal_output_check"]["additionalProperties"] is False


def test_proof_of_backend_equivalence_schema_fails_closed() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    _assert_objects_fail_closed(schema)
    assert "raw_tensor_value" not in schema["properties"]
    assert "runtime_handle" not in schema["properties"]
    assert "device_id" not in schema["properties"]
    assert "host_path" not in schema["properties"]
    assert "generated_code" not in schema["properties"]


def test_proof_of_backend_equivalence_is_documented_and_in_ci() -> None:
    example_path = "examples/proof_of_backend_equivalence.py"
    schema_path = "schemas/proof_of_backend_equivalence_report.v0.schema.json"
    golden_path = "tests/golden/proofs/proof_of_backend_equivalence.json"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("docs/MINIMAL_TUC_WALKTHROUGH.md"),
        Path("docs/PROOF_OF_BACKEND_EQUIVALENCE.md"),
        Path("docs/RUNTIME_BACKEND_EQUIVALENCE.md"),
        Path("docs/RUNTIME_EVIDENCE_FLOW.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0224-proof-of-backend-equivalence-entrypoint.md"),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("docs/PROOF_OF_BACKEND_EQUIVALENCE.md"),
        Path("rfcs/0224-proof-of-backend-equivalence-entrypoint.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert golden_path in text


def _assert_objects_fail_closed(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
        for value in schema.values():
            _assert_objects_fail_closed(value)
    elif isinstance(schema, list):
        for item in schema:
            _assert_objects_fail_closed(item)
