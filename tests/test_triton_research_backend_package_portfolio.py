from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

import examples.triton_research_backend_package_portfolio as proof_module
from examples.source_intent_backend_package_portfolio import run_module_evidence
from examples.source_to_intent_research_execution_bridge import (
    _inputs_for,
    _references_for,
)
from tuc.frontend import (
    SourceToIntentResearchKernelIngressError,
    source_intent_from_mapping,
)
from tuc.ir import LayoutKind, OperationKind

GOLDEN = Path(
    "tests/golden/frontend/"
    "triton_research_backend_package_portfolio_report.json"
)
SCHEMA = Path(
    "schemas/triton_research_backend_package_portfolio_report.v0.schema.json"
)


def test_bounded_module_source_becomes_canonical_source_intent() -> None:
    evidence = proof_module.run_evidence()
    graph = evidence.portfolio.compilation.hac_ir.graph

    assert evidence.ingress.report.parser_status == "research_explicit_only"
    assert evidence.ingress.report.default_parser_status == "default_parser_blocked"
    assert evidence.ingress.report.import_count == 2
    assert evidence.module.name == "research_matmul_elementwise"
    assert tuple(operation.kind for operation in graph.operations) == (
        OperationKind.MATMUL,
        OperationKind.ELEMENTWISE,
    )
    assert evidence.module.returns[0].public_name == "y"
    assert evidence.module.returns[0].tensor_name == "activated"


def test_research_source_reaches_no_fallback_external_package_execution() -> None:
    evidence = proof_module.run_evidence()
    source_plan = evidence.portfolio.compilation.partition_plan
    projected_plan = evidence.portfolio.candidate.projected_partition_plan

    assert tuple(item.backend_name for item in source_plan.assignments) == (
        "external-systolic",
        "external-vector",
    )
    assert tuple(item.backend_name for item in projected_plan.assignments) == (
        "systolic-sim",
        "vector-sim",
    )
    assert evidence.portfolio.portfolio_report.fallback_assignment_count == 0
    assert len(projected_plan.layout_conversions) == 1
    conversion = projected_plan.layout_conversions[0]
    assert conversion.tensor_name == "projection"
    assert conversion.source_layout is LayoutKind.BLOCKED
    assert conversion.target_layout is LayoutKind.ROW_MAJOR
    assert conversion.bytes_converted == 32


def test_research_source_closes_public_output_and_semantics() -> None:
    evidence = proof_module.run_evidence().portfolio

    assert evidence.public_output_bundle.public_output_names == ("y",)
    assert evidence.public_output_bundle.tensor_names == ("activated",)
    assert evidence.reference_correctness.passed
    assert evidence.backend_equivalence.passed
    assert tuple(
        step.executor_backend for step in evidence.candidate.execution.trace.steps
    ) == ("systolic-sim", "vector-sim")


def test_public_report_matches_golden_and_omits_source_and_values() -> None:
    report = proof_module.build_triton_research_backend_package_portfolio_report()
    text = proof_module.build_report()

    assert text == GOLDEN.read_text(encoding="utf-8")
    assert report["proof_status"] == "PASS"
    assert cast(dict[str, object], report["planning"])[
        "fallback_assignment_count"
    ] == 0
    security = cast(dict[str, object], report["security"])
    assert security["production_source_ingestion_admitted"] is False
    for fragment in proof_module.TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_FORBIDDEN_FRAGMENTS:
        assert fragment not in text


def test_example_emits_only_canonical_public_report() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/triton_research_backend_package_portfolio.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.stderr == ""
    assert completed.stdout == GOLDEN.read_text(encoding="utf-8")


def test_report_rejects_unknown_fields_and_security_claim_drift() -> None:
    report = proof_module.build_triton_research_backend_package_portfolio_report()
    unknown = dict(report)
    unknown["plugin_entrypoint"] = "attacker.module:run"
    security_drift = dict(report)
    security = dict(cast(dict[str, object], security_drift["security"]))
    security["production_source_ingestion_admitted"] = True
    security_drift["security"] = security
    package_drift = dict(report)
    packages = dict(cast(dict[str, object], package_drift["packages"]))
    packages["package_digests"] = ["sha256:" + "0" * 64]
    package_drift["packages"] = packages

    for invalid in (unknown, security_drift, package_drift):
        with pytest.raises(ValueError, match="drift"):
            proof_module.assert_triton_research_backend_package_portfolio_report(
                invalid
            )


@pytest.mark.parametrize(
    "malicious_source",
    (
        proof_module.REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
            "import triton\n",
            "import os\n",
            1,
        ),
        proof_module.REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
            "@triton.jit",
            "@triton.autotune",
        ),
        proof_module.REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE
        + "\nopen('secret.txt').read()\n",
    ),
)
def test_vertical_proof_rejects_malicious_module_surface(
    malicious_source: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        proof_module,
        "REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE",
        malicious_source,
    )

    with pytest.raises(SourceToIntentResearchKernelIngressError):
        proof_module.run_evidence()


def test_shared_portfolio_boundary_rejects_custom_value_mappings() -> None:
    evidence = proof_module.run_evidence()
    module = source_intent_from_mapping(
        evidence.ingress.parser_result.source_intent_payload
    )
    inputs = _inputs_for(proof_module.SOURCE_NAME)
    references = _references_for(proof_module.SOURCE_NAME, inputs)

    class CustomDict(dict[str, object]):
        pass

    with pytest.raises(TypeError, match="plain dictionaries"):
        run_module_evidence(
            module,
            cast(Any, CustomDict(inputs)),
            references,
        )


def test_report_schema_is_bounded_and_fail_closed() -> None:
    schema = _load_json(SCHEMA)
    report = _load_json(GOLDEN)

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
    assert sorted(report) == sorted(schema["required"])
    for section in ("execution", "frontend", "packages", "planning", "security", "source"):
        section_schema = schema["properties"][section]
        assert sorted(report[section]) == sorted(section_schema["required"])
    assert schema["properties"]["planning"]["properties"][
        "fallback_assignment_count"
    ] == {"const": 0}
    assert schema["properties"]["security"]["properties"][
        "production_source_ingestion_admitted"
    ] == {"const": False}


def test_triton_research_package_portfolio_is_documented() -> None:
    markers = (
        "TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md",
        "examples/triton_research_backend_package_portfolio.py",
        "schemas/triton_research_backend_package_portfolio_report.v0.schema.json",
        "tests/golden/frontend/triton_research_backend_package_portfolio_report.json",
        "rfcs/0286-triton-research-backend-package-portfolio.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("TUC_MASTER_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/BACKEND_API.md"),
        Path("docs/TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO.md"),
        Path("rfcs/0286-triton-research-backend-package-portfolio.md"),
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
