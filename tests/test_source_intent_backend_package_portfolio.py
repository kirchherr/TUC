from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

import examples.source_intent_backend_package_portfolio as proof_module
from tuc.frontend.source_intent_intake import source_intent_from_mapping
from tuc.ir import LayoutKind, OperationKind
from tuc.runtime.backend_package_execution_portfolio import (
    BackendPackageExecutionPortfolioError,
)

GOLDEN = Path(
    "tests/golden/frontend/source_intent_backend_package_portfolio_report.json"
)
SCHEMA = Path(
    "schemas/source_intent_backend_package_portfolio_report.v0.schema.json"
)


def test_source_intent_builds_neutral_two_operation_graph() -> None:
    module = source_intent_from_mapping(proof_module.build_source_intent_data())
    graph = proof_module.source_intent_to_triton_metadata(module).to_compute_graph()

    assert tuple(operation.kind for operation in graph.operations) == (
        OperationKind.MATMUL,
        OperationKind.ELEMENTWISE,
    )
    assert tuple(operation.name for operation in graph.operations) == (
        "projection",
        "activation",
    )
    assert proof_module.source_intent_return_aliases(module) == {
        "api_activated": "activated"
    }


def test_source_intent_reaches_no_fallback_package_portfolio_execution() -> None:
    evidence = proof_module.run_evidence()
    source_plan = evidence.compilation.partition_plan
    projected_plan = evidence.candidate.projected_partition_plan

    assert tuple(item.backend_name for item in source_plan.assignments) == (
        "external-systolic",
        "external-vector",
    )
    assert tuple(item.backend_name for item in projected_plan.assignments) == (
        "systolic-sim",
        "vector-sim",
    )
    assert evidence.portfolio_report.fallback_assignment_count == 0
    assert len(projected_plan.layout_conversions) == 1
    conversion = projected_plan.layout_conversions[0]
    assert conversion.tensor_name == "projection"
    assert conversion.source_layout is LayoutKind.BLOCKED
    assert conversion.target_layout is LayoutKind.ROW_MAJOR
    assert conversion.bytes_converted == 32


def test_vertical_proof_closes_public_output_and_correctness() -> None:
    evidence = proof_module.run_evidence()

    assert evidence.public_output_bundle.public_output_names == ("api_activated",)
    assert evidence.public_output_bundle.tensor_names == ("activated",)
    assert evidence.reference_correctness.passed
    assert evidence.backend_equivalence.passed
    assert tuple(
        step.executor_backend for step in evidence.candidate.execution.trace.steps
    ) == ("systolic-sim", "vector-sim")


def test_public_report_matches_golden_and_omits_sensitive_surfaces() -> None:
    report = proof_module.build_source_intent_backend_package_portfolio_report()
    text = proof_module.build_report()

    assert text == GOLDEN.read_text(encoding="utf-8")
    assert report["fallback_assignment_count"] == 0
    assert report["backend_equivalence_passed"] is True
    assert report["reference_correctness_passed"] is True
    assert report["source_text_executed"] is False
    assert report["source_intent_payload_serialized"] is False
    assert report["raw_tensor_values_serialized"] is False
    for fragment in proof_module.SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_FORBIDDEN_FRAGMENTS:
        assert fragment not in text


def test_example_emits_only_canonical_public_report() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_intent_backend_package_portfolio.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.stderr == ""
    assert completed.stdout == GOLDEN.read_text(encoding="utf-8")


def test_public_report_assertion_rejects_unknown_or_drifted_fields() -> None:
    report = proof_module.build_source_intent_backend_package_portfolio_report()
    unknown = dict(report)
    unknown["plugin_entrypoint"] = "attacker.module:run"
    drifted = dict(report)
    drifted["fallback_assignment_count"] = 1
    changed_package = dict(report)
    changed_package["package_digests"] = [
        "sha256:" + "0" * 64,
        proof_module.EXPECTED_PACKAGE_DIGESTS[1],
    ]

    for invalid in (unknown, drifted, changed_package):
        with pytest.raises(ValueError, match="drift"):
            proof_module.assert_source_intent_backend_package_portfolio_report(
                invalid
            )


def test_source_intent_rejects_backend_authority_and_source_text() -> None:
    payload = deepcopy(proof_module.build_source_intent_data())
    operations = cast(list[dict[str, object]], payload["operations"])
    operations[0]["backend"] = "external-systolic"

    with pytest.raises(ValueError, match="unsupported keys: backend"):
        source_intent_from_mapping(payload)
    with pytest.raises(TypeError, match="plain mapping"):
        source_intent_from_mapping("@triton.jit\ndef kernel(): pass")


def test_package_identity_drift_blocks_vertical_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = _load_json(proof_module.SYSTOLIC_PACKAGE_PATH)
    payload["package_version"] = "0.1.1"
    drifted_path = tmp_path / "external_systolic_drifted.json"
    drifted_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(proof_module, "SYSTOLIC_PACKAGE_PATH", drifted_path)

    with pytest.raises(BackendPackageExecutionPortfolioError, match="blocked"):
        proof_module.run_evidence()


def test_report_schema_is_bounded_and_fail_closed() -> None:
    schema = _load_json(SCHEMA)
    report = _load_json(GOLDEN)

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
    assert sorted(report) == sorted(schema["required"])
    assert schema["properties"]["fallback_assignment_count"] == {"const": 0}
    assert schema["properties"]["external_package_code_executed"] == {
        "const": False
    }
    assert schema["properties"]["raw_tensor_values_serialized"] == {
        "const": False
    }
    assert schema["properties"]["source_text_executed"] == {"const": False}


def test_source_intent_package_portfolio_is_documented() -> None:
    markers = (
        "SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md",
        "examples/source_intent_backend_package_portfolio.py",
        "schemas/source_intent_backend_package_portfolio_report.v0.schema.json",
        "tests/golden/frontend/source_intent_backend_package_portfolio_report.json",
        "rfcs/0285-source-intent-backend-package-portfolio.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("TUC_MASTER_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/BACKEND_API.md"),
        Path("docs/SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO.md"),
        Path("rfcs/0285-source-intent-backend-package-portfolio.md"),
    ):
        text = path.read_text(encoding="utf-8-sig")
        for marker in markers:
            assert marker in text or path.name == marker.rsplit("/", 1)[-1]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("expected JSON object")
    return cast(dict[str, Any], payload)


def _iter_object_schemas(value: Any) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if value.get("type") == "object":
            objects.append(value)
        for child in value.values():
            objects.extend(_iter_object_schemas(child))
    elif isinstance(value, list):
        for child in value:
            objects.extend(_iter_object_schemas(child))
    return objects
