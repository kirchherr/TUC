from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from examples.backend_package_execution_portfolio import (
    SYSTOLIC_PACKAGE_PATH,
    VECTOR_PACKAGE_PATH,
    build_graph,
    build_proof_report,
    build_report,
    proof_inputs,
)
from tuc.backends.integration_package import (
    BackendIntegrationPackage,
    dump_backend_integration_package_report,
    evaluate_backend_integration_package,
    load_backend_integration_package,
    parse_backend_integration_package,
)
from tuc.compiler import compile_graph
from tuc.ir import LayoutKind, MemoryDomainKind
from tuc.runtime.backend_package_execution import (
    BackendPackageExecutionAdmissionReport,
    build_backend_package_execution_admission_report,
)
from tuc.runtime.backend_package_execution_portfolio import (
    BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
    BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY,
    BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_SCHEMA_VERSION,
    BackendPackageExecutionPortfolioAdmission,
    BackendPackageExecutionPortfolioError,
    assert_backend_package_execution_portfolio,
    backend_package_execution_portfolio_report_to_dict,
    build_backend_package_execution_portfolio_admission,
    execute_backend_package_execution_portfolio,
    project_backend_package_execution_portfolio_plan,
)
from tuc.runtime.overrides import RuntimeOverrideEffect

INTEGRATION_GOLDEN = Path(
    "tests/golden/backend_integration_package/external_systolic_report.json"
)
PROOF_GOLDEN = Path(
    "tests/golden/backend_package_execution_portfolio/proof_report.json"
)
PROOF_SCHEMA = Path(
    "schemas/backend_package_execution_portfolio_report.v0.schema.json"
)


def test_external_systolic_package_matches_integration_golden() -> None:
    package = load_backend_integration_package(SYSTOLIC_PACKAGE_PATH)
    report = evaluate_backend_integration_package(package)

    assert report.integration_status == "PASS"
    assert report.package.capability.name == "external-systolic"
    assert report.package.capability.produced_layouts == frozenset({LayoutKind.BLOCKED})
    assert dump_backend_integration_package_report(report) == (
        INTEGRATION_GOLDEN.read_text(encoding="utf-8")
    )


def test_portfolio_admits_exact_disjoint_package_set() -> None:
    admission = _portfolio_admission()

    assert_backend_package_execution_portfolio(admission)
    assert admission.portfolio_status == "PASS"
    assert tuple(entry.package_id for entry in admission.entries) == (
        "external-systolic-reference-package",
        "external-vector-reference-package",
    )
    assert tuple(entry.trusted_executor_backend for entry in admission.entries) == (
        "systolic-sim",
        "vector-sim",
    )
    assert not admission.external_plugin_execution
    assert not admission.package_backend_implementation_executed
    assert not admission.physical_device_execution


def test_portfolio_plans_projects_and_executes_without_fallback() -> None:
    graph = build_graph()
    packages = _packages()
    source = compile_graph(
        graph,
        tuple(package.capability for package in packages),
    ).partition_plan
    projected = project_backend_package_execution_portfolio_plan(
        graph,
        source,
        _portfolio_admission(),
    )
    execution = execute_backend_package_execution_portfolio(
        graph,
        source,
        proof_inputs(),
        _portfolio_admission(),
    )

    assert tuple(item.backend_name for item in source.assignments) == (
        "external-systolic",
        "external-vector",
    )
    assert tuple(item.backend_name for item in projected.assignments) == (
        "systolic-sim",
        "vector-sim",
    )
    assert len(projected.transfer_edges) == 0
    assert len(projected.layout_conversions) == 1
    conversion = projected.layout_conversions[0]
    assert conversion.tensor_name == "projection"
    assert conversion.source_layout is LayoutKind.BLOCKED
    assert conversion.target_layout is LayoutKind.ROW_MAJOR
    assert conversion.bytes_converted == 32
    assert tuple(step.executor_backend for step in execution.execution.trace.steps) == (
        "systolic-sim",
        "vector-sim",
    )
    assert execution.execution.output_for("activated").shape == (2, 2)


def test_portfolio_proof_binds_equivalence_and_omits_values() -> None:
    report = build_proof_report()
    payload = backend_package_execution_portfolio_report_to_dict(report)

    assert report.portfolio_contract == BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT
    assert report.portfolio_policy == BACKEND_PACKAGE_EXECUTION_PORTFOLIO_POLICY
    assert report.source_backend_sequence == (
        "external-systolic",
        "external-vector",
    )
    assert report.projected_backend_sequence == ("systolic-sim", "vector-sim")
    assert report.fallback_assignment_count == 0
    assert report.package_backend_count == 2
    assert report.trusted_executor_count == 2
    assert report.equivalence_passed
    assert payload["raw_tensor_value_policy"] == "omitted_by_policy"
    text = json.dumps(payload, sort_keys=True)
    for forbidden in (
        "backend_artifact",
        "device_id",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_tensor_values",
        "runtime_handle",
        "shell_command",
        "source_text",
        "tensor_values",
    ):
        assert forbidden not in text


def test_portfolio_proof_matches_golden() -> None:
    assert build_report() == PROOF_GOLDEN.read_text(encoding="utf-8")


def test_portfolio_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_package_execution_portfolio.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.stdout == PROOF_GOLDEN.read_text(encoding="utf-8")
    assert '"fallback_assignment_count": 0' in completed.stdout
    assert '"equivalence_passed": true' in completed.stdout
    assert '"portfolio_status": "PASS"' in completed.stdout


def test_portfolio_rejects_incomplete_package_set() -> None:
    admission = build_backend_package_execution_portfolio_admission(
        (_admission_for(VECTOR_PACKAGE_PATH),)
    )

    assert not admission.admitted
    assert {issue.issue_code for issue in admission.issues} >= {
        "portfolio_too_small",
        "required_package_set_mismatch",
    }
    with pytest.raises(BackendPackageExecutionPortfolioError, match="blocked"):
        assert_backend_package_execution_portfolio(admission)


def test_portfolio_rejects_duplicate_or_overlapping_package_scope() -> None:
    vector = _admission_for(VECTOR_PACKAGE_PATH)
    admission = build_backend_package_execution_portfolio_admission((vector, vector))

    assert {issue.issue_code for issue in admission.issues} >= {
        "duplicate_binding_id",
        "duplicate_package_backend",
        "duplicate_package_id",
        "duplicate_trusted_executor",
        "overlapping_operation_scope",
        "required_package_set_mismatch",
    }


def test_portfolio_rejects_package_identity_drift() -> None:
    payload = _load_json(SYSTOLIC_PACKAGE_PATH)
    payload["package_version"] = "0.1.1"
    drifted = parse_backend_integration_package(payload)
    blocked = build_backend_package_execution_admission_report(
        evaluate_backend_integration_package(drifted)
    )
    admission = build_backend_package_execution_portfolio_admission(
        (blocked, _admission_for(VECTOR_PACKAGE_PATH))
    )

    assert "package_admission_blocked" in {
        issue.issue_code for issue in admission.issues
    }


def test_portfolio_rejects_fallback_or_unbound_assignment() -> None:
    graph = build_graph()
    vector = load_backend_integration_package(VECTOR_PACKAGE_PATH)
    source = compile_graph(graph, (vector.capability,)).partition_plan

    with pytest.raises(BackendPackageExecutionPortfolioError, match="fallback"):
        project_backend_package_execution_portfolio_plan(
            graph,
            source,
            _portfolio_admission(),
        )


def test_portfolio_rejects_runtime_overrides_and_candidate_scores() -> None:
    graph = build_graph()
    packages = _packages()
    capabilities = tuple(package.capability for package in packages)
    source = compile_graph(graph, capabilities).partition_plan
    overridden = replace(
        source,
        override_effects=(
            RuntimeOverrideEffect(
                operation_name="activation",
                required_backend="external-vector",
            ),
        ),
    )
    scored = compile_graph(
        graph,
        capabilities,
        include_candidate_scores=True,
    ).partition_plan

    with pytest.raises(BackendPackageExecutionPortfolioError, match="overrides"):
        project_backend_package_execution_portfolio_plan(
            graph,
            overridden,
            _portfolio_admission(),
        )
    with pytest.raises(BackendPackageExecutionPortfolioError, match="candidate score"):
        project_backend_package_execution_portfolio_plan(
            graph,
            scored,
            _portfolio_admission(),
        )


def test_portfolio_rejects_noncanonical_placement_or_movement_metadata() -> None:
    graph = build_graph()
    capabilities = tuple(package.capability for package in _packages())
    source = compile_graph(graph, capabilities).partition_plan
    first = source.assignments[0]
    tampered_plans = (
        replace(
            source,
            assignments=(
                replace(first, memory_domain=MemoryDomainKind.HOST_RAM),
                source.assignments[1],
            ),
        ),
        replace(
            source,
            assignments=(
                replace(first, produced_layout=LayoutKind.ROW_MAJOR),
                source.assignments[1],
            ),
        ),
        replace(source, layout_conversions=()),
    )

    for tampered in tampered_plans:
        with pytest.raises(BackendPackageExecutionPortfolioError, match="canonical"):
            project_backend_package_execution_portfolio_plan(
                graph,
                tampered,
                _portfolio_admission(),
            )


def test_portfolio_schema_fails_closed_and_matches_golden() -> None:
    schema = _load_json(PROOF_SCHEMA)
    proof = _load_json(PROOF_GOLDEN)

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
    assert sorted(proof) == sorted(schema["required"])
    assert proof["schema_version"] == (
        BACKEND_PACKAGE_EXECUTION_PORTFOLIO_REPORT_SCHEMA_VERSION
    )
    assert proof["fallback_assignment_count"] == 0
    assert proof["external_plugin_execution"] is False


def test_backend_package_execution_portfolio_is_documented() -> None:
    expected = (
        "BACKEND_PACKAGE_EXECUTION_PORTFOLIO.md",
        "examples/backend_package_execution_portfolio.py",
        "examples/backend_packages/external_systolic.v0.json",
        "schemas/backend_package_execution_portfolio_report.v0.schema.json",
        "tests/golden/backend_integration_package/external_systolic_report.json",
        "tests/golden/backend_package_execution_portfolio/proof_report.json",
        "rfcs/0284-multi-package-execution-portfolio.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("TUC_MASTER_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/BACKEND_API.md"),
        Path("docs/BACKEND_PACKAGE_EXECUTION_PORTFOLIO.md"),
        Path("rfcs/0284-multi-package-execution-portfolio.md"),
    ):
        text = path.read_text(encoding="utf-8-sig")
        for marker in expected:
            assert marker in text or path.name == marker.rsplit("/", 1)[-1]


def _packages() -> tuple[BackendIntegrationPackage, ...]:
    return tuple(
        load_backend_integration_package(path)
        for path in (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH)
    )


def _admission_for(path: Path) -> BackendPackageExecutionAdmissionReport:
    package = load_backend_integration_package(path)
    return build_backend_package_execution_admission_report(
        evaluate_backend_integration_package(package)
    )


def _portfolio_admission() -> BackendPackageExecutionPortfolioAdmission:
    reports = tuple(
        _admission_for(path)
        for path in (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH)
    )
    return build_backend_package_execution_portfolio_admission(reports)


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
