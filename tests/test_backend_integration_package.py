from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_integration_package import PACKAGE_PATH, build_report
from tuc.backends.integration_package import (
    BACKEND_INTEGRATION_PACKAGE_BLOCKED_EXECUTION_SURFACES,
    BACKEND_INTEGRATION_PACKAGE_CONTRACT,
    BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY,
    BACKEND_INTEGRATION_PACKAGE_POLICY,
    BACKEND_INTEGRATION_PACKAGE_REPORT_SCHEMA_VERSION,
    BACKEND_INTEGRATION_PACKAGE_SCHEMA_VERSION,
    MAX_BACKEND_INTEGRATION_PACKAGE_CASES,
    BackendIntegrationPackageError,
    assert_backend_integration_package,
    backend_integration_package_report_to_dict,
    evaluate_backend_integration_package,
    load_backend_integration_package,
    parse_backend_integration_package,
)
from tuc.ir import OperationKind
from tuc.manifests import ManifestError, parse_backend_capability_manifest

GOLDEN_PATH = Path(
    "tests/golden/backend_integration_package/external_vector_report.json"
)
PACKAGE_SCHEMA_PATH = Path("schemas/backend_integration_package.v0.schema.json")
REPORT_SCHEMA_PATH = Path(
    "schemas/backend_integration_package_report.v0.schema.json"
)


def test_backend_integration_package_passes_without_backend_execution() -> None:
    package = load_backend_integration_package(PACKAGE_PATH)
    report = evaluate_backend_integration_package(package)
    payload = backend_integration_package_report_to_dict(report)

    assert_backend_integration_package(report)
    assert package.capability.name == "external-vector"
    assert package.capability.supported_ops == frozenset({OperationKind.ELEMENTWISE})
    assert payload["integration_status"] == "PASS"
    assert payload["conformance_passed"] is True
    assert payload["case_count"] == 3
    assert payload["planning_probe"] == {
        "assigned_backend": "external-vector",
        "assignment_matched": True,
        "graph_name": "backend_integration_package_probe",
        "operation_kind": "elementwise",
        "operation_name": "elementwise_row_major_accept",
    }
    assert payload["backend_code_included"] is False
    assert payload["backend_code_executed"] is False
    assert payload["execution_permission"] is False
    assert payload["plugin_discovery"] is False
    assert payload["runtime_execution"] is False
    assert payload["device_access"] is False
    assert payload["network_access"] is False
    assert payload["subprocess_execution"] is False
    assert payload["artifact_execution"] is False


def test_backend_integration_package_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_backend_integration_package_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_integration_package.py"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"integration_status": "PASS"' in completed.stdout
    assert '"backend_code_executed": false' in completed.stdout
    assert "python_source" not in completed.stdout
    assert "runtime_handle" not in completed.stdout
    assert "device_id" not in completed.stdout
    assert "host_path" not in completed.stdout


def test_in_memory_capability_parser_matches_file_loader() -> None:
    payload = _package_payload()["capability_manifest"]
    assert isinstance(payload, dict)

    capability = parse_backend_capability_manifest(payload)

    assert capability == load_backend_integration_package(PACKAGE_PATH).capability


@pytest.mark.parametrize(
    "field",
    (
        "backend_code_included",
        "execution_permission",
    ),
)
def test_backend_integration_package_rejects_execution_permission(field: str) -> None:
    payload = _package_payload()
    payload[field] = True

    with pytest.raises(BackendIntegrationPackageError, match="blocked|not allowed"):
        parse_backend_integration_package(payload)


@pytest.mark.parametrize(
    "field",
    (
        "plugin_entrypoint",
        "python_source",
        "dynamic_library",
        "device_path",
        "shell_command",
        "url",
    ),
)
def test_backend_integration_package_rejects_execution_surface_fields(
    field: str,
) -> None:
    payload = _package_payload()
    payload[field] = "untrusted"

    with pytest.raises(BackendIntegrationPackageError, match="keys changed"):
        parse_backend_integration_package(payload)


def test_backend_integration_package_rejects_capability_escape_field() -> None:
    payload = _package_payload()
    capability = payload["capability_manifest"]
    assert isinstance(capability, dict)
    capability["import_path"] = "vendor.backend:load"

    with pytest.raises(ManifestError, match="unsupported keys"):
        parse_backend_integration_package(payload)


def test_backend_integration_package_rejects_unmodeled_reason() -> None:
    payload = _package_payload()
    cases = payload["conformance_cases"]
    assert isinstance(cases, list)
    first_case = cases[0]
    assert isinstance(first_case, dict)
    first_case["expected_reason"] = "error_budget_exceeds_backend_limit"

    with pytest.raises(BackendIntegrationPackageError, match="not supported"):
        parse_backend_integration_package(payload)


def test_backend_integration_package_rejects_path_like_identifier() -> None:
    payload = _package_payload()
    payload["package_id"] = "../vendor-package"

    with pytest.raises(BackendIntegrationPackageError, match="safe identifier"):
        parse_backend_integration_package(payload)


def test_backend_integration_package_rejects_custom_mapping() -> None:
    class CustomMapping(dict[str, object]):
        pass

    with pytest.raises(BackendIntegrationPackageError, match="unsupported value type"):
        parse_backend_integration_package(CustomMapping(_package_payload()))


def test_capability_parser_rejects_custom_mapping() -> None:
    class CustomMapping(dict[str, object]):
        pass

    capability = _package_payload()["capability_manifest"]
    assert isinstance(capability, dict)
    with pytest.raises(ManifestError, match="plain JSON object"):
        parse_backend_capability_manifest(CustomMapping(capability))


def test_backend_integration_package_rejects_excessive_cases() -> None:
    payload = _package_payload()
    cases = payload["conformance_cases"]
    assert isinstance(cases, list)
    cases.extend(
        {
            "case_id": f"extra_case_{index}",
            "operation_kind": "matmul",
            "layout": "row_major",
            "expected_supported": False,
            "expected_reason": "unsupported_operation_kind",
        }
        for index in range(MAX_BACKEND_INTEGRATION_PACKAGE_CASES)
    )

    with pytest.raises(BackendIntegrationPackageError, match="case count exceeds"):
        parse_backend_integration_package(payload)


def test_backend_integration_package_loader_rejects_duplicate_keys(
    tmp_path: Path,
) -> None:
    package_path = tmp_path / "duplicate.json"
    package_path.write_text(
        '{"schema_version":"tuc.backend_integration_package.v0",'
        '"schema_version":"tuc.backend_integration_package.v0"}',
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="duplicate keys"):
        load_backend_integration_package(package_path)


def test_backend_integration_package_reports_claim_mismatch() -> None:
    payload = _package_payload()
    capability = payload["capability_manifest"]
    assert isinstance(capability, dict)
    capability["supported_ops"] = ["matmul"]
    capability["preferred_for"] = ["matmul"]
    package = parse_backend_integration_package(payload)

    report = evaluate_backend_integration_package(package)

    assert report.conformance_passed is False
    assert report.integration_status == "FAIL"
    assert "case_mismatch:elementwise_row_major_accept" in report.issues
    assert "planning_assignment_mismatch" in report.issues
    with pytest.raises(BackendIntegrationPackageError, match="conformance failed"):
        assert_backend_integration_package(report)


def test_backend_integration_package_schema_matches_reference_package() -> None:
    schema = _load_json(PACKAGE_SCHEMA_PATH)
    payload = _package_payload()

    assert sorted(payload) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_INTEGRATION_PACKAGE_SCHEMA_VERSION
    )
    assert schema["properties"]["interface_contract"]["const"] == (
        BACKEND_INTEGRATION_PACKAGE_CONTRACT
    )
    assert schema["properties"]["package_policy"]["const"] == (
        BACKEND_INTEGRATION_PACKAGE_POLICY
    )
    assert schema["properties"]["import_policy"]["const"] == (
        BACKEND_INTEGRATION_PACKAGE_IMPORT_POLICY
    )


def test_backend_integration_package_report_schema_matches_golden() -> None:
    schema = _load_json(REPORT_SCHEMA_PATH)
    golden = _load_json(GOLDEN_PATH)

    assert sorted(golden) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_INTEGRATION_PACKAGE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["blocked_execution_surfaces"]["const"] == list(
        BACKEND_INTEGRATION_PACKAGE_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["integration_status"] == "PASS"
    assert golden["issues"] == []


@pytest.mark.parametrize("schema_path", (PACKAGE_SCHEMA_PATH, REPORT_SCHEMA_PATH))
def test_backend_integration_package_schemas_fail_closed(schema_path: Path) -> None:
    schema = _load_json(schema_path)

    for object_schema in _iter_object_schemas(schema):
        assert object_schema.get("additionalProperties") is False
        forbidden = {
            "backend_artifact",
            "device_id",
            "host_path",
            "plugin_entrypoint",
            "python_source",
            "runtime_handle",
            "shell_command",
            "source_text",
            "url",
        }
        assert not (set(object_schema.get("properties", {})) & forbidden)


def test_backend_integration_package_is_documented() -> None:
    expected = (
        "BACKEND_INTEGRATION_PACKAGE.md",
        "examples/backend_integration_package.py",
        "examples/backend_packages/external_vector.v0.json",
        "schemas/backend_integration_package.v0.schema.json",
        "schemas/backend_integration_package_report.v0.schema.json",
        "tests/golden/backend_integration_package/external_vector_report.json",
        "rfcs/0282-backend-integration-package.md",
    )
    for path in (
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("TUC_MASTER_PLAN.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/BACKEND_API.md"),
        Path("docs/BACKEND_INTEGRATION_PACKAGE.md"),
        Path("rfcs/0282-backend-integration-package.md"),
    ):
        text = path.read_text(encoding="utf-8-sig")
        for marker in expected:
            assert marker in text or path.name == marker.rsplit("/", 1)[-1]


def _package_payload() -> dict[str, Any]:
    return _load_json(PACKAGE_PATH)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
