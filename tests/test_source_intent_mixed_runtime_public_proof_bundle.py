from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from examples.source_intent_mixed_runtime_public_proof_bundle import (
    SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_ARTIFACT_POLICY,
    SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT,
    SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION,
    assert_source_intent_mixed_runtime_public_proof_bundle_report_contract,
    build_report,
    build_source_intent_mixed_runtime_public_proof_bundle_report,
    reference_outputs,
    run_evidence,
    runtime_inputs,
)
from tuc import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_METADATA_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json"
)
SCHEMA_PATH = Path(
    "schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json"
)
DOC_PATH = "docs/SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE.md"
RFC_PATH = "rfcs/0253-source-intent-mixed-runtime-public-proof-bundle.md"
EXAMPLE_PATH = "examples/source_intent_mixed_runtime_public_proof_bundle.py"


def test_source_intent_mixed_runtime_public_proof_bundle_shape() -> None:
    evidence = run_evidence()
    report = build_source_intent_mixed_runtime_public_proof_bundle_report()

    assert_source_intent_mixed_runtime_public_proof_bundle_report_contract(report)
    assert report["schema_version"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert report["bundle_contract"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT
    )
    assert report["artifact_policy"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_ARTIFACT_POLICY
    )
    assert report["status"] == "PASS"
    assert report["source_intent_contract"] == SOURCE_INTENT_IR_CONTRACT
    assert report["metadata_contract"] == SOURCE_INTENT_METADATA_CONTRACT
    assert report["executor_contract"] == RUNTIME_EXECUTOR_CONTRACT
    assert report["output_manifest_contract"] == RUNTIME_OUTPUT_MANIFEST_CONTRACT
    assert report["output_contract"] == RUNTIME_OUTPUT_CONTRACT
    assert report["public_output_bundle_contract"] == RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    assert report["reference_correctness_contract"] == RUNTIME_REFERENCE_CORRECTNESS_CONTRACT
    assert report["backend_equivalence_contract"] == RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    assert report["trusted_executor_registry"] == TRUSTED_RUNTIME_EXECUTOR_REGISTRY
    assert report["raw_value_policy"] == RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    assert report["operation_families"] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]
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
    assert report["trusted_runtime_backends"] == [
        "reference-cpu",
        "systolic-sim",
        "vector-sim",
    ]
    assert report["public_output_names"] == ["api_activated"]
    assert report["terminal_outputs"] == ["activated"]
    assert report["artifact_count"] == 9
    assert len(report["artifacts"]) == 9
    assert report["comparison_count"] == 1
    assert report["public_output_bundle_passed"] is True
    assert report["reference_correctness_passed"] is True
    assert report["backend_equivalence_passed"] is True

    np.testing.assert_allclose(
        evidence.public_output_bundle.values["api_activated"],
        reference_outputs(runtime_inputs())["activated"],
    )
    assert not evidence.public_output_bundle.values["api_activated"].flags.writeable


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("artifact_count", 8, "artifact_count"),
        ("comparison_count", 2, "comparison_count"),
        ("candidate_backend_sequence", ["vector-sim"], "candidate_backend_sequence"),
        ("raw_tensor_value", [1.0, 1.0], "top-level report"),
    ],
)
def test_source_intent_mixed_runtime_public_proof_bundle_rejects_contract_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = build_source_intent_mixed_runtime_public_proof_bundle_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_source_intent_mixed_runtime_public_proof_bundle_report_contract(report)


def test_source_intent_mixed_runtime_public_proof_bundle_rejects_artifact_drift() -> None:
    report = build_source_intent_mixed_runtime_public_proof_bundle_report()
    artifacts = report["artifacts"]
    assert isinstance(artifacts, list)
    assert isinstance(artifacts[0], dict)
    artifacts[0]["digest"] = "sha256:not-a-real-digest"

    with pytest.raises(ValueError, match="digest drift"):
        assert_source_intent_mixed_runtime_public_proof_bundle_report_contract(report)


def test_source_intent_mixed_runtime_public_proof_bundle_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_intent_mixed_runtime_public_proof_bundle_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, EXAMPLE_PATH],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"systolic-sim"' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert '"api_activated"' in completed.stdout
    assert "raw_tensor_value" not in completed.stdout
    assert "tensor_values" not in completed.stdout
    assert '"value":' not in completed.stdout
    assert '"values":' not in completed.stdout
    assert "python_source" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout
    assert "@triton.jit" not in completed.stdout


def test_source_intent_mixed_runtime_public_proof_bundle_schema_declares_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["bundle_contract"]["const"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT
    )
    assert schema["properties"]["artifact_policy"]["const"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_ARTIFACT_POLICY
    )
    assert schema["properties"]["source_intent_contract"]["const"] == (
        SOURCE_INTENT_IR_CONTRACT
    )
    assert schema["properties"]["metadata_contract"]["const"] == (
        SOURCE_INTENT_METADATA_CONTRACT
    )
    assert schema["properties"]["executor_contract"]["const"] == (
        RUNTIME_EXECUTOR_CONTRACT
    )
    assert schema["properties"]["output_manifest_contract"]["const"] == (
        RUNTIME_OUTPUT_MANIFEST_CONTRACT
    )
    assert schema["properties"]["output_contract"]["const"] == RUNTIME_OUTPUT_CONTRACT
    assert schema["properties"]["public_output_bundle_contract"]["const"] == (
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
    )
    assert schema["properties"]["reference_correctness_contract"]["const"] == (
        RUNTIME_REFERENCE_CORRECTNESS_CONTRACT
    )
    assert schema["properties"]["backend_equivalence_contract"]["const"] == (
        RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
    )
    assert schema["properties"]["raw_value_policy"]["const"] == (
        RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS
    )
    assert [
        item["const"]
        for item in schema["$defs"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)


def test_source_intent_mixed_runtime_public_proof_bundle_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    forbidden_properties = {
        "command",
        "device_id",
        "file_path",
        "generated_code",
        "host_path",
        "python_source",
        "raw_output_value",
        "raw_source",
        "raw_tensor_value",
        "source_intent_payload",
        "source_text",
        "tensor_value",
        "tensor_values",
        "value",
        "values",
    }
    assert not (set(schema["properties"]) & forbidden_properties)
    assert not (set(schema["$defs"]["artifact"]["properties"]) & forbidden_properties)


def test_source_intent_mixed_runtime_public_proof_bundle_golden_matches_schema() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
    )
    assert golden["bundle_contract"] == (
        SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT
    )
    assert golden["status"] == "PASS"
    assert golden["artifact_count"] == 9
    assert len(golden["artifacts"]) == 9
    assert golden["public_output_names"] == ["api_activated"]
    assert golden["terminal_outputs"] == ["activated"]
    assert golden["candidate_backend_sequence"] == [
        "systolic-sim",
        "vector-sim",
        "vector-sim",
        "vector-sim",
    ]


def test_source_intent_mixed_runtime_public_proof_bundle_is_documented_and_in_ci() -> None:
    schema_path = (
        "schemas/source_intent_mixed_runtime_public_proof_bundle_report.v0.schema.json"
    )
    golden_path = (
        "tests/golden/frontend/source_intent_mixed_runtime_public_proof_bundle.json"
    )

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/MINIMAL_TUC_WALKTHROUGH.md"),
        Path("docs/PROOF_OF_BACKEND_EQUIVALENCE.md"),
        Path(DOC_PATH),
        Path(RFC_PATH),
    ):
        text = path.read_text(encoding="utf-8")
        assert EXAMPLE_PATH in text

    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/MINIMAL_TUC_WALKTHROUGH.md"),
        Path("docs/PROOF_OF_BACKEND_EQUIVALENCE.md"),
        Path(DOC_PATH),
        Path(RFC_PATH),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert golden_path in text

    for path in (
        Path("README.md"),
        Path("docs/MINIMAL_TUC_WALKTHROUGH.md"),
        Path("docs/PROOF_OF_BACKEND_EQUIVALENCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path(RFC_PATH),
    ):
        assert DOC_PATH in path.read_text(encoding="utf-8")


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
