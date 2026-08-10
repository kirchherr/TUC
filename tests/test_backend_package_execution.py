from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

import tuc.runtime.backend_package_execution as subject
from examples.backend_package_execution_proof import (
    PACKAGE_PATH,
    build_graph,
    build_proof_report,
    build_report,
    proof_inputs,
)
from tuc.backends.integration_package import (
    evaluate_backend_integration_package,
    load_backend_integration_package,
    parse_backend_integration_package,
)
from tuc.compiler import compile_graph
from tuc.ir import ComputeGraph
from tuc.runtime.backend_package_execution import (
    BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
    BACKEND_PACKAGE_EXECUTION_ADMISSION_REPORT_SCHEMA_VERSION,
    BACKEND_PACKAGE_EXECUTION_MODE,
    BACKEND_PACKAGE_EXECUTION_POLICY,
    BACKEND_PACKAGE_EXECUTION_PROOF_CONTRACT,
    BACKEND_PACKAGE_EXECUTION_PROOF_REPORT_SCHEMA_VERSION,
    BACKEND_PACKAGE_EXECUTION_RAW_VALUE_POLICY,
    BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED,
    BackendPackageExecutionAdmissionError,
    BackendPackageExecutionAdmissionReport,
    assert_backend_package_execution_admission,
    backend_package_execution_admission_report_to_dict,
    build_backend_package_execution_admission_report,
    dump_backend_package_execution_admission_report,
    execute_admitted_backend_package,
    project_backend_package_partition_plan,
    trusted_backend_package_execution_bindings,
)
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
from tuc.runtime.overrides import RuntimeOverrideEffect
from tuc.runtime.partitioning import PartitionPlan

ADMISSION_GOLDEN = Path(
    "tests/golden/backend_package_execution/admission_report.json"
)
PROOF_GOLDEN = Path("tests/golden/backend_package_execution/proof_report.json")
ADMISSION_SCHEMA = Path(
    "schemas/backend_package_execution_admission_report.v0.schema.json"
)
PROOF_SCHEMA = Path(
    "schemas/backend_package_execution_proof_report.v0.schema.json"
)


def test_backend_package_execution_admission_passes_exact_binding() -> None:
    admission = _admission()
    payload = backend_package_execution_admission_report_to_dict(admission)

    assert_backend_package_execution_admission(admission)
    assert admission.projection_execution_allowed
    assert admission.admission_status == BACKEND_PACKAGE_EXECUTION_STATUS_ADMITTED
    assert payload["package_backend_name"] == "external-vector"
    assert payload["trusted_executor_backend"] == "vector-sim"
    assert payload["allowed_operations"] == ["elementwise"]
    assert payload["integration_report_matches"] is True
    assert payload["external_plugin_execution"] is False
    assert payload["package_backend_implementation_executed"] is False
    assert payload["physical_device_execution"] is False
    assert payload["issues"] == []


def test_backend_package_execution_admission_matches_golden() -> None:
    assert dump_backend_package_execution_admission_report(_admission()) == (
        ADMISSION_GOLDEN.read_text(encoding="utf-8")
    )


def test_backend_package_execution_proof_matches_golden() -> None:
    assert build_report() == PROOF_GOLDEN.read_text(encoding="utf-8")


def test_backend_package_execution_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_package_execution_proof.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.stdout == PROOF_GOLDEN.read_text(encoding="utf-8")
    assert '"source_backend_sequence": [' in completed.stdout
    assert '"external-vector"' in completed.stdout
    assert '"projected_backend_sequence": [' in completed.stdout
    assert '"vector-sim"' in completed.stdout
    assert '"equivalence_passed": true' in completed.stdout
    assert '"proof_status": "PASS"' in completed.stdout
    for forbidden in (
        "python_source",
        "runtime_handle",
        "device_id",
        "host_path",
        "raw_tensor_values",
        "tensor_values",
    ):
        assert forbidden not in completed.stdout


def test_backend_package_execution_projects_transfer_and_executes() -> None:
    graph = build_graph()
    package = load_backend_integration_package(PACKAGE_PATH)
    source = compile_graph(graph, (package.capability,)).partition_plan
    admitted = execute_admitted_backend_package(
        graph,
        source,
        proof_inputs(),
        _admission(),
    )

    assert tuple(item.backend_name for item in source.assignments) == (
        "reference-cpu",
        "external-vector",
    )
    assert tuple(
        item.backend_name for item in admitted.projected_partition_plan.assignments
    ) == ("reference-cpu", "vector-sim")
    assert len(admitted.projected_partition_plan.transfer_edges) == 1
    edge = admitted.projected_partition_plan.transfer_edges[0]
    assert edge.source_backend == "reference-cpu"
    assert edge.target_backend == "vector-sim"
    assert tuple(step.executor_backend for step in admitted.execution.trace.steps) == (
        "reference-cpu",
        "vector-sim",
    )
    assert admitted.execution.output_for("activated").shape == (2, 2)


def test_backend_package_execution_proof_binds_equivalence_and_omits_values() -> None:
    report = build_proof_report()

    assert report.proof_contract == BACKEND_PACKAGE_EXECUTION_PROOF_CONTRACT
    assert report.admission_contract == BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT
    assert report.execution_mode == BACKEND_PACKAGE_EXECUTION_MODE
    assert report.raw_tensor_value_policy == BACKEND_PACKAGE_EXECUTION_RAW_VALUE_POLICY
    assert report.source_backend_sequence == ("reference-cpu", "external-vector")
    assert report.projected_backend_sequence == ("reference-cpu", "vector-sim")
    assert report.projected_operation_count == 1
    assert report.transfer_edge_count == 1
    assert report.execution_step_count == 2
    assert report.output_tensor_names == ("activated",)
    assert report.output_shapes == ((2, 2),)
    assert report.output_dtypes == ("float64",)
    assert report.equivalence_passed
    assert report.external_plugin_execution is False
    assert report.package_backend_implementation_executed is False
    assert report.physical_device_execution is False


@pytest.mark.parametrize(
    ("mutator", "issue_code"),
    (
        (
            lambda payload: payload.__setitem__("package_version", "0.1.1"),
            "package_digest_mismatch",
        ),
        (
            lambda payload: payload.__setitem__("package_id", "unknown-package"),
            "package_not_allowlisted",
        ),
        (
            lambda payload: _capability(payload).__setitem__(
                "name", "external-vector-other"
            ),
            "backend_name_mismatch",
        ),
        (
            lambda payload: _capability(payload).__setitem__(
                "supported_ops", ["elementwise", "reduction"]
            ),
            "capability_operation_scope_mismatch",
        ),
        (
            lambda payload: _capability(payload).__setitem__(
                "produced_layouts", ["vector"]
            ),
            "produced_layout_mismatch",
        ),
    ),
)
def test_backend_package_execution_admission_rejects_package_drift(
    mutator: Any,
    issue_code: str,
) -> None:
    payload = _package_payload()
    mutator(payload)
    package = parse_backend_integration_package(payload)
    integration = evaluate_backend_integration_package(package)
    admission = build_backend_package_execution_admission_report(integration)

    assert not admission.projection_execution_allowed
    assert issue_code in {issue.issue_code for issue in admission.issues}
    with pytest.raises(BackendPackageExecutionAdmissionError, match="blocked"):
        assert_backend_package_execution_admission(admission)


def test_backend_package_execution_admission_rejects_forged_integration_report() -> None:
    package = load_backend_integration_package(PACKAGE_PATH)
    integration = evaluate_backend_integration_package(package)
    forged = replace(integration, case_results=())

    admission = build_backend_package_execution_admission_report(forged)

    assert not admission.projection_execution_allowed
    assert "integration_report_mismatch" in {
        issue.issue_code for issue in admission.issues
    }


def test_backend_package_execution_admission_rejects_executor_registry_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(subject, "trusted_runtime_executor_registry", lambda: {})

    admission = _admission()

    assert not admission.projection_execution_allowed
    assert {issue.issue_code for issue in admission.issues} >= {
        "trusted_executor_contract_mismatch",
        "trusted_executor_missing",
    }


def test_backend_package_execution_admission_issues_cannot_be_forged() -> None:
    admission = _admission()

    with pytest.raises(ValueError, match="issues must be derived"):
        replace(admission, package_digest="sha256:" + ("1" * 64))


def test_backend_package_execution_rejects_runtime_overrides() -> None:
    graph, source = _source_plan()
    overridden = replace(
        source,
        override_effects=(
            RuntimeOverrideEffect(
                operation_name="activation",
                required_backend="external-vector",
            ),
        ),
    )

    with pytest.raises(BackendPackageExecutionAdmissionError, match="overrides"):
        project_backend_package_partition_plan(graph, overridden, _admission())


def test_backend_package_execution_rejects_candidate_score_payloads() -> None:
    graph = build_graph()
    package = load_backend_integration_package(PACKAGE_PATH)
    scored = compile_graph(
        graph,
        (package.capability,),
        include_candidate_scores=True,
    ).partition_plan
    assert scored.candidate_scores

    with pytest.raises(BackendPackageExecutionAdmissionError, match="candidate score"):
        project_backend_package_partition_plan(graph, scored, _admission())


def test_backend_package_execution_rejects_untrusted_plan_backend() -> None:
    graph, source = _source_plan()
    bad_assignment = replace(source.assignments[0], backend_name="untrusted-backend")
    untrusted = replace(source, assignments=(bad_assignment, source.assignments[1]))

    with pytest.raises(BackendPackageExecutionAdmissionError, match="untrusted"):
        project_backend_package_partition_plan(graph, untrusted, _admission())


def test_backend_package_execution_rejects_plan_without_package_assignment() -> None:
    graph = build_graph()
    baseline = compile_graph(graph, ()).partition_plan

    with pytest.raises(BackendPackageExecutionAdmissionError, match="no admitted"):
        project_backend_package_partition_plan(graph, baseline, _admission())


def test_backend_package_execution_requires_plain_input_mapping() -> None:
    class CustomInputs(dict[str, object]):
        pass

    graph, source = _source_plan()
    with pytest.raises(TypeError, match="plain mapping"):
        execute_admitted_backend_package(
            graph,
            source,
            CustomInputs(proof_inputs()),
            _admission(),
        )


def test_backend_package_execution_binding_is_digest_pinned() -> None:
    bindings = trusted_backend_package_execution_bindings()

    assert len(bindings) == 2
    by_id = {binding.package_id: binding for binding in bindings}
    vector = by_id["external-vector-reference-package"]
    assert vector.package_digest == (
        "sha256:bf4bf333025a176f20ad927c249747f6ce923e14f224f4cd94ed769d893288ee"
    )
    assert vector.capability_manifest_digest == (
        "sha256:ca1de79c1935a08617343687a06816821b77e4837ac7ac8430998c746bd60d3a"
    )
    assert vector.trusted_executor_backend == "vector-sim"
    systolic = by_id["external-systolic-reference-package"]
    assert systolic.package_digest == (
        "sha256:806813974dfde16b46f694566d751b18780d5e43d8455467bf4e5d7ea38b452c"
    )
    assert systolic.capability_manifest_digest == (
        "sha256:7a282b30b775cca5b826019ee1652ce221a85eef6878c7266febc2202293bbf0"
    )
    assert systolic.trusted_executor_backend == "systolic-sim"


@pytest.mark.parametrize("schema_path", (ADMISSION_SCHEMA, PROOF_SCHEMA))
def test_backend_package_execution_schemas_fail_closed(schema_path: Path) -> None:
    schema = _load_json(schema_path)

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
    forbidden = {
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
        "url",
    }
    assert not (set(schema["properties"]) & forbidden)


def test_backend_package_execution_schemas_match_goldens() -> None:
    admission_schema = _load_json(ADMISSION_SCHEMA)
    proof_schema = _load_json(PROOF_SCHEMA)
    admission = _load_json(ADMISSION_GOLDEN)
    proof = _load_json(PROOF_GOLDEN)

    assert sorted(admission) == sorted(admission_schema["required"])
    assert sorted(proof) == sorted(proof_schema["required"])
    assert admission["schema_version"] == (
        BACKEND_PACKAGE_EXECUTION_ADMISSION_REPORT_SCHEMA_VERSION
    )
    assert admission["admission_policy"] == BACKEND_PACKAGE_EXECUTION_POLICY
    assert proof["schema_version"] == (
        BACKEND_PACKAGE_EXECUTION_PROOF_REPORT_SCHEMA_VERSION
    )
    assert admission["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert proof["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )


def test_backend_package_execution_is_documented() -> None:
    expected = (
        "BACKEND_PACKAGE_EXECUTION_ADMISSION.md",
        "examples/backend_package_execution_proof.py",
        "schemas/backend_package_execution_admission_report.v0.schema.json",
        "schemas/backend_package_execution_proof_report.v0.schema.json",
        "tests/golden/backend_package_execution/admission_report.json",
        "tests/golden/backend_package_execution/proof_report.json",
        "rfcs/0283-backend-package-execution-admission.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("TUC_MASTER_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/BACKEND_API.md"),
        Path("docs/BACKEND_PACKAGE_EXECUTION_ADMISSION.md"),
        Path("rfcs/0283-backend-package-execution-admission.md"),
    ):
        text = path.read_text(encoding="utf-8-sig")
        for marker in expected:
            assert marker in text or path.name == marker.rsplit("/", 1)[-1]


def _admission() -> BackendPackageExecutionAdmissionReport:
    package = load_backend_integration_package(PACKAGE_PATH)
    integration = evaluate_backend_integration_package(package)
    return build_backend_package_execution_admission_report(integration)


def _source_plan() -> tuple[ComputeGraph, PartitionPlan]:
    graph = build_graph()
    package = load_backend_integration_package(PACKAGE_PATH)
    return graph, compile_graph(graph, (package.capability,)).partition_plan


def _package_payload() -> dict[str, Any]:
    return _load_json(PACKAGE_PATH)


def _capability(payload: dict[str, Any]) -> dict[str, Any]:
    capability = payload["capability_manifest"]
    assert isinstance(capability, dict)
    return capability


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError("expected JSON object")
    return cast(dict[str, Any], payload)


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
