from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.backend_plugin_artifact_provenance import (
    build_current_backend_plugin_artifact_provenance_report,
)
from tuc import (
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT,
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION,
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY,
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_REPORT_SCHEMA_VERSION,
    BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS,
    BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS,
    BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
    MAX_BACKEND_PLUGIN_ARTIFACTS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendPluginArtifactProvenanceError,
    BackendPluginArtifactProvenanceIssue,
    BackendPluginArtifactProvenanceReport,
    BackendPluginArtifactRecord,
    assert_backend_plugin_artifact_provenance,
    backend_plugin_artifact_provenance_report_to_dict,
    build_backend_plugin_artifact_provenance_report,
    dump_backend_plugin_artifact_provenance_report,
)

SCHEMA_PATH = Path("schemas/backend_plugin_artifact_provenance_report.v0.schema.json")
GOLDEN_PATH = Path(
    "tests/golden/backend_plugin_artifact_provenance/current_report.json"
)


def test_backend_plugin_artifact_provenance_is_data_only_and_ready() -> None:
    report = build_current_backend_plugin_artifact_provenance_report()

    assert report.provenance_ready
    assert not report.execution_allowed
    assert report.execution_permission == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION
    assert report.provenance_contract == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    assert report.provenance_policy == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY
    assert report.provenance_status == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS
    assert report.required_bindings == BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS
    assert report.blocked_execution_surfaces == RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    assert report.artifact_count == 1
    assert report.issues == ()

    artifact = report.artifacts[0]
    assert artifact.artifact_digest.startswith("sha256:")
    assert artifact.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    assert artifact.storage_scope == "repository_evidence"
    assert artifact.review_status == "reviewed_digest_bound"


def test_backend_plugin_artifact_provenance_assertion_passes() -> None:
    report = build_current_backend_plugin_artifact_provenance_report()

    assert assert_backend_plugin_artifact_provenance(report) is report


def test_backend_plugin_artifact_provenance_rejects_hand_written_issues() -> None:
    report = build_current_backend_plugin_artifact_provenance_report()

    with pytest.raises(ValueError, match="issues must be derived"):
        BackendPluginArtifactProvenanceReport(
            artifacts=report.artifacts,
            issues=(
                BackendPluginArtifactProvenanceIssue(
                    artifact_id=report.artifacts[0].artifact_id,
                    issue_code="duplicate_artifact_id",
                ),
            ),
        )


def test_backend_plugin_artifact_provenance_assertion_rejects_duplicates() -> None:
    artifact = build_current_backend_plugin_artifact_provenance_report().artifacts[0]
    report = BackendPluginArtifactProvenanceReport(
        artifacts=(artifact, artifact),
        issues=(
            BackendPluginArtifactProvenanceIssue(
                artifact_id=artifact.artifact_id,
                issue_code="duplicate_artifact_id",
            ),
        ),
    )

    assert not report.provenance_ready
    with pytest.raises(BackendPluginArtifactProvenanceError, match="duplicate_artifact_id"):
        assert_backend_plugin_artifact_provenance(report)


def test_backend_plugin_artifact_provenance_rejects_invalid_digest() -> None:
    with pytest.raises(ValueError, match="sha256 digest"):
        BackendPluginArtifactRecord(
            artifact_id="external_vector_lowering_artifact",
            artifact_digest="sha256:not-valid",
            storage_scope="repository_evidence",
            source_scope_id="external_vector_assigned_subgraph",
            build_recipe_id="backend_author_path_lowering_recipe_v0",
            review_record_id="backend_author_evidence_gate.ci.v0",
            sandbox_model_contract=BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
            review_status="reviewed_digest_bound",
        )


def test_backend_plugin_artifact_provenance_rejects_forbidden_identifiers() -> None:
    with pytest.raises(ValueError, match="forbidden execution surface"):
        BackendPluginArtifactRecord(
            artifact_id="python_module",
            artifact_digest=(
                "sha256:"
                "8b4f6d3c2a1e0f9d8c7b6a594837261504f3e2d1c0b9a897867564534231201f"
            ),
            storage_scope="repository_evidence",
            source_scope_id="external_vector_assigned_subgraph",
            build_recipe_id="backend_author_path_lowering_recipe_v0",
            review_record_id="backend_author_evidence_gate.ci.v0",
            sandbox_model_contract=BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT,
            review_status="reviewed_digest_bound",
        )


def test_backend_plugin_artifact_provenance_example_matches_golden() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_plugin_artifact_provenance.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    loaded = json.loads(completed.stdout)
    assert loaded["provenance_ready"] is True
    assert loaded["execution_allowed"] is False
    assert loaded["execution_permission"] == "not_granted"


def test_backend_plugin_artifact_provenance_dump_matches_golden() -> None:
    report = build_backend_plugin_artifact_provenance_report()

    assert dump_backend_plugin_artifact_provenance_report(
        report
    ) == GOLDEN_PATH.read_text(encoding="utf-8")


def test_backend_plugin_artifact_provenance_to_dict_requires_report() -> None:
    with pytest.raises(TypeError, match="report object"):
        backend_plugin_artifact_provenance_report_to_dict(object())  # type: ignore[arg-type]


def test_backend_plugin_artifact_provenance_schema_matches_contract() -> None:
    schema = _load_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(
        "/schemas/backend_plugin_artifact_provenance_report.v0.schema.json"
    )
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        BACKEND_PLUGIN_ARTIFACT_PROVENANCE_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["provenance_contract"]["const"] == (
        BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    )
    assert schema["properties"]["provenance_policy"]["const"] == (
        BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY
    )
    assert schema["properties"]["provenance_status"]["const"] == (
        BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS
    )
    assert schema["properties"]["execution_allowed"]["const"] is False
    assert schema["properties"]["execution_permission"]["const"] == "not_granted"
    assert schema["properties"]["artifact_count"]["const"] == 1
    assert schema["properties"]["artifacts"]["maxItems"] <= MAX_BACKEND_PLUGIN_ARTIFACTS
    assert [
        item["const"]
        for item in schema["properties"]["required_bindings"]["prefixItems"]
    ] == list(BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS)
    assert [
        item["const"]
        for item in schema["properties"]["blocked_execution_surfaces"]["prefixItems"]
    ] == list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)
    artifact_schema = schema["$defs"]["artifact"]
    assert artifact_schema["properties"]["artifact_digest"]["$ref"].endswith(
        "sha256_digest"
    )
    assert artifact_schema["properties"]["sandbox_model_contract"]["const"] == (
        BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    )


def test_backend_plugin_artifact_provenance_schema_fails_closed() -> None:
    schema = _load_schema()

    _assert_objects_fail_closed(schema)
    for forbidden in (
        "artifact_bytes",
        "source_text",
        "python_source",
        "file_path",
        "host_path",
        "command_line",
        "device_id",
        "plugin_entrypoint",
        "python_module",
        "generated_code",
        "raw_benchmark_output",
        "url",
    ):
        assert forbidden not in schema["properties"]
        assert forbidden not in schema["$defs"]["artifact"]["properties"]
        assert forbidden not in schema["$defs"]["provenance_issue"]["properties"]
    assert "python_module" in schema["$defs"]["report_text"]["not"]["enum"]
    assert "plugin_entrypoint" in schema["$defs"]["report_text"]["not"]["enum"]
    assert schema["$defs"]["sha256_digest"]["pattern"] == "^sha256:[0-9a-f]{64}$"
    assert schema["$defs"]["report_text"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )


def test_backend_plugin_artifact_provenance_golden_matches_schema_shape() -> None:
    schema = _load_schema()
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))

    assert sorted(golden) == sorted(schema["required"])
    assert golden["schema_version"] == (
        BACKEND_PLUGIN_ARTIFACT_PROVENANCE_REPORT_SCHEMA_VERSION
    )
    assert golden["provenance_contract"] == BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    assert golden["blocked_execution_surfaces"] == list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    assert golden["execution_allowed"] is False
    assert golden["execution_permission"] == "not_granted"
    assert golden["provenance_ready"] is True
    assert golden["artifact_count"] == len(golden["artifacts"]) == 1
    assert golden["issues"] == []
    artifact = golden["artifacts"][0]
    assert artifact["artifact_digest"].startswith("sha256:")
    assert artifact["sandbox_model_contract"] == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT


def test_backend_plugin_artifact_provenance_schema_is_referenced() -> None:
    schema_path = "schemas/backend_plugin_artifact_provenance_report.v0.schema.json"

    for path in (
        Path("docs/BACKEND_PLUGIN_ARTIFACT_PROVENANCE.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("rfcs/0219-backend-plugin-artifact-provenance.md"),
    ):
        assert schema_path in path.read_text(encoding="utf-8")


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
