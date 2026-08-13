from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from examples.external_frontend_package_conformance import (
    build_current_external_frontend_package_conformance_report,
    build_report,
)
from examples.source_intent_frontend_conformance import (
    build_source_intent_frontend_conformance_cases,
)
from tuc.frontend import (
    EXTERNAL_FRONTEND_PACKAGE_BLOCKED_ARTIFACTS,
    EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES,
    EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_ARTIFACT_STATUS,
    EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT,
    EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION,
    EXTERNAL_FRONTEND_PACKAGE_FIXTURE_POLICY,
    EXTERNAL_FRONTEND_PACKAGE_IMPORT_POLICY,
    EXTERNAL_FRONTEND_PACKAGE_INTERFACE_CONTRACT,
    EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES,
    ExternalFrontendPackageConformanceReport,
    ExternalFrontendPackageManifest,
    build_external_frontend_package_conformance_report,
    default_external_frontend_package_manifest,
    external_frontend_package_conformance_report_to_dict,
)

SCHEMA_PATH = Path(
    "schemas/external_frontend_package_conformance_report.v0.schema.json"
)
GOLDEN_PATH = Path(
    "tests/golden/frontend/external_frontend_package_conformance_report.json"
)


def test_external_frontend_package_conformance_passes_reference_manifest() -> None:
    report = build_current_external_frontend_package_conformance_report()
    payload = external_frontend_package_conformance_report_to_dict(report)

    assert payload["schema_version"] == (
        EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert payload["artifact_status"] == (
        EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_ARTIFACT_STATUS
    )
    assert payload["conformance_contract"] == EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT
    assert payload["fixture_policy"] == EXTERNAL_FRONTEND_PACKAGE_FIXTURE_POLICY
    assert payload["conformance_status"] == "pass"
    assert payload["conformance_passed"] is True
    assert payload["capability_coverage_complete"] is True
    assert payload["package_imported"] is False
    assert payload["plugin_discovery"] is False
    assert payload["direct_source_ingestion"] is False
    assert payload["triton_jit_execution"] is False
    assert payload["accepted_case_count"] == 2
    assert payload["rejected_case_count"] == 6
    assert len(payload["checked_cases"]) == 8
    assert len(payload["fixture_digests"]) == 8
    assert payload["package_manifest"]["interface_contract"] == (
        EXTERNAL_FRONTEND_PACKAGE_INTERFACE_CONTRACT
    )
    assert payload["package_manifest"]["import_policy"] == (
        EXTERNAL_FRONTEND_PACKAGE_IMPORT_POLICY
    )
    assert payload["package_manifest"]["declared_capabilities"] == list(
        EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES
    )
    assert payload["blocked_execution_surfaces"] == list(
        EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES
    )
    assert payload["blocked_artifacts"] == list(EXTERNAL_FRONTEND_PACKAGE_BLOCKED_ARTIFACTS)


def test_external_frontend_package_conformance_example_matches_golden() -> None:
    assert build_report() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_external_frontend_package_conformance_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/external_frontend_package_conformance.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"package_imported": false' in completed.stdout
    assert '"plugin_discovery": false' in completed.stdout
    assert '"direct_source_ingestion": false' in completed.stdout
    assert '"triton_jit_execution": false' in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "tl.dot" not in completed.stdout


def test_external_frontend_package_conformance_rejects_import_permission() -> None:
    with pytest.raises(ValueError, match="import policy mismatch"):
        ExternalFrontendPackageManifest(
            package_name="bad_external_frontend",
            package_version="v0.0.0",
            declared_capabilities=EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES,
            import_policy="import_allowed",
        )


def test_external_frontend_package_conformance_rejects_execution_permission() -> None:
    with pytest.raises(ValueError, match="execution permission is blocked"):
        ExternalFrontendPackageManifest(
            package_name="bad_external_frontend",
            package_version="v0.0.0",
            declared_capabilities=EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES,
            execution_permission=True,
        )


def test_external_frontend_package_conformance_rejects_missing_capabilities() -> None:
    with pytest.raises(ValueError, match="required capabilities missing"):
        ExternalFrontendPackageManifest(
            package_name="bad_external_frontend",
            package_version="v0.0.0",
            declared_capabilities=EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES[:-1],
        )


def test_external_frontend_package_conformance_rejects_failed_conformance() -> None:
    cases = build_source_intent_frontend_conformance_cases()
    bad_cases = (
        replace(
            cases[0],
            payload={
                "name": "bad",
                "schema_version": "source_intent.v0",
                "python_source": "x",
                "tensors": [],
                "operations": [],
            },
        ),
        *cases[1:],
    )

    with pytest.raises(ValueError, match="source-intent conformance failed"):
        build_external_frontend_package_conformance_report(
            default_external_frontend_package_manifest(),
            bad_cases,
        )


def test_external_frontend_package_conformance_rejects_tampered_report_counts() -> None:
    report = build_current_external_frontend_package_conformance_report()

    with pytest.raises(ValueError, match="case counts mismatch"):
        ExternalFrontendPackageConformanceReport(
            manifest=report.manifest,
            fixture_digests=report.fixture_digests,
            conformance_report_digest=report.conformance_report_digest,
            checked_cases=report.checked_cases,
            accepted_case_count=999,
            rejected_case_count=report.rejected_case_count,
            conformance_passed=True,
        )


def test_external_frontend_package_conformance_rejects_duplicate_fixture_digest() -> None:
    report = build_current_external_frontend_package_conformance_report()
    duplicate = replace(
        report.fixture_digests[1],
        payload_digest=report.fixture_digests[0].payload_digest,
    )

    with pytest.raises(ValueError, match="payload digests must be unique"):
        ExternalFrontendPackageConformanceReport(
            manifest=report.manifest,
            fixture_digests=(report.fixture_digests[0], duplicate),
            conformance_report_digest=report.conformance_report_digest,
            checked_cases=(report.fixture_digests[0].case_name, duplicate.case_name),
            accepted_case_count=1,
            rejected_case_count=1,
            conformance_passed=True,
        )


def test_external_frontend_package_conformance_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["conformance_contract"]["const"] == (
        EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT
    )
    assert schema["properties"]["package_imported"]["const"] is False
    assert schema["properties"]["plugin_discovery"]["const"] is False
    assert schema["properties"]["direct_source_ingestion"]["const"] is False
    assert schema["properties"]["triton_jit_execution"]["const"] is False
    assert schema["$defs"]["package_manifest"]["additionalProperties"] is False
    assert schema["$defs"]["fixture_digest"]["additionalProperties"] is False


def test_external_frontend_package_conformance_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    assert golden["package_imported"] is False
    assert golden["plugin_discovery"] is False
    assert golden["direct_source_ingestion"] is False
    assert golden["triton_jit_execution"] is False
    assert len(golden["blocked_execution_surfaces"]) == len(
        EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES
    )


def test_external_frontend_package_conformance_is_documented() -> None:
    schema_path = "schemas/external_frontend_package_conformance_report.v0.schema.json"
    example_path = "examples/external_frontend_package_conformance.py"
    doc_path = "docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md"

    for path in (
        Path("README.md"),
        Path("docs/EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE.md"),
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("docs/TRITON_COMPATIBILITY.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0243-external-frontend-package-conformance.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert schema_path in text
        assert example_path in text

    for path in (
        Path("README.md"),
        Path("docs/TRITON_INTEGRATION_READINESS.md"),
        Path("rfcs/0243-external-frontend-package-conformance.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
