"""Data-only artifact provenance for future executable backend plugins."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.backends.sandbox_model import BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
from tuc.runtime.executor import RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES

BACKEND_PLUGIN_ARTIFACT_PROVENANCE_REPORT_SCHEMA_VERSION = (
    "tuc.backend_plugin_artifact_provenance_report.v0"
)
BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT = (
    "backend_plugin_artifact_provenance.data_only.v0"
)
BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY = (
    "artifact_provenance.digest_bound.reviewed.no_execution.v0"
)
BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS = "accepted_data_only_provenance"
BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION = "not_granted"
BACKEND_PLUGIN_ARTIFACT_STORAGE_SCOPES = frozenset(
    {"repository_evidence", "release_artifact", "external_attestation"}
)
BACKEND_PLUGIN_ARTIFACT_STATUSES = frozenset({"reviewed_digest_bound"})
BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS = (
    "sandbox_model",
    "content_digest",
    "source_scope",
    "build_recipe",
    "review_record",
)
BACKEND_PLUGIN_ARTIFACT_PROVENANCE_ISSUE_CODES = frozenset(
    {
        "artifact_execution_permission_granted",
        "artifact_missing_required_binding",
        "artifact_review_status_invalid",
        "duplicate_artifact_id",
        "invalid_artifact_digest",
        "invalid_storage_scope",
        "sandbox_binding_mismatch",
    }
)
MAX_BACKEND_PLUGIN_ARTIFACTS = 16
MAX_BACKEND_PLUGIN_ARTIFACT_ISSUES = 64
MAX_BACKEND_PLUGIN_ARTIFACT_REPORT_BYTES = 64 * 1024
MAX_BACKEND_PLUGIN_ARTIFACT_FIELD_BYTES = 512

_PROVENANCE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_PROVENANCE_TEXT = frozenset(
    {
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "subprocess",
        "url",
    }
)


@dataclass(frozen=True)
class BackendPluginArtifactRecord:
    """One provenance record for a future executable backend artifact."""

    artifact_id: str
    artifact_digest: str
    storage_scope: str
    source_scope_id: str
    build_recipe_id: str
    review_record_id: str
    sandbox_model_contract: str
    review_status: str

    def __post_init__(self) -> None:
        _validate_provenance_text(self.artifact_id, "artifact_id")
        _validate_digest(self.artifact_digest)
        _validate_provenance_text(self.storage_scope, "storage_scope")
        _validate_provenance_text(self.source_scope_id, "source_scope_id")
        _validate_provenance_text(self.build_recipe_id, "build_recipe_id")
        _validate_provenance_text(self.review_record_id, "review_record_id")
        _validate_provenance_text(
            self.sandbox_model_contract,
            "sandbox_model_contract",
        )
        _validate_provenance_text(self.review_status, "review_status")
        if self.storage_scope not in BACKEND_PLUGIN_ARTIFACT_STORAGE_SCOPES:
            raise ValueError("backend plugin artifact storage scope unsupported")
        if self.review_status not in BACKEND_PLUGIN_ARTIFACT_STATUSES:
            raise ValueError("backend plugin artifact review status unsupported")


@dataclass(frozen=True)
class BackendPluginArtifactProvenanceIssue:
    """One derived artifact provenance issue."""

    artifact_id: str
    issue_code: str

    def __post_init__(self) -> None:
        _validate_provenance_text(self.artifact_id, "artifact issue artifact_id")
        _validate_provenance_text(self.issue_code, "artifact issue_code")
        if self.issue_code not in BACKEND_PLUGIN_ARTIFACT_PROVENANCE_ISSUE_CODES:
            raise ValueError("backend plugin artifact provenance issue unsupported")


@dataclass(frozen=True)
class BackendPluginArtifactProvenanceReport:
    """Current data-only artifact provenance evidence."""

    artifacts: tuple[BackendPluginArtifactRecord, ...]
    issues: tuple[BackendPluginArtifactProvenanceIssue, ...]
    provenance_contract: str = BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT
    provenance_policy: str = BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY
    provenance_status: str = BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS
    execution_permission: str = BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION
    required_bindings: tuple[str, ...] = BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.provenance_contract != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT:
            raise ValueError("backend plugin artifact provenance contract mismatch")
        if self.provenance_policy != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY:
            raise ValueError("backend plugin artifact provenance policy mismatch")
        if self.provenance_status != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS:
            raise ValueError("backend plugin artifact provenance status mismatch")
        if (
            self.execution_permission
            != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION
        ):
            raise ValueError("backend plugin artifact execution permission mismatch")
        if self.required_bindings != BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS:
            raise ValueError("backend plugin artifact required bindings changed")
        if self.blocked_execution_surfaces != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES:
            raise ValueError("backend plugin artifact blocked surfaces changed")
        if type(self.artifacts) is not tuple:
            raise TypeError("backend plugin artifacts must be a tuple")
        if len(self.artifacts) > MAX_BACKEND_PLUGIN_ARTIFACTS:
            raise ValueError("backend plugin artifact count exceeds limit")
        for artifact in self.artifacts:
            if not isinstance(artifact, BackendPluginArtifactRecord):
                raise TypeError("backend plugin artifacts must be artifact records")
        if type(self.issues) is not tuple:
            raise TypeError("backend plugin artifact issues must be a tuple")
        if len(self.issues) > MAX_BACKEND_PLUGIN_ARTIFACT_ISSUES:
            raise ValueError("backend plugin artifact issue count exceeds limit")
        for issue in self.issues:
            if not isinstance(issue, BackendPluginArtifactProvenanceIssue):
                raise TypeError("backend plugin artifact issues must be issue objects")
        expected_issues = _derive_artifact_issues(self)
        if self.issues != expected_issues:
            raise ValueError("backend plugin artifact issues must be derived")

    @property
    def artifact_count(self) -> int:
        """Return the number of reviewed artifact records."""

        return len(self.artifacts)

    @property
    def provenance_ready(self) -> bool:
        """Return whether artifact provenance evidence is internally complete."""

        return bool(self.artifacts) and not self.issues

    @property
    def execution_allowed(self) -> bool:
        """Return whether this provenance evidence grants execution permission."""

        return False


class BackendPluginArtifactProvenanceError(ValueError):
    """Raised when backend plugin artifact provenance evidence fails."""


def build_backend_plugin_artifact_provenance_report(
    artifacts: tuple[BackendPluginArtifactRecord, ...] | None = None,
) -> BackendPluginArtifactProvenanceReport:
    """Build the current data-only artifact provenance report."""

    normalized_artifacts = (
        _current_artifact_records() if artifacts is None else artifacts
    )
    report = BackendPluginArtifactProvenanceReport(
        artifacts=normalized_artifacts,
        issues=(),
    )
    return BackendPluginArtifactProvenanceReport(
        artifacts=normalized_artifacts,
        issues=_derive_artifact_issues(report),
    )


def assert_backend_plugin_artifact_provenance(
    report: BackendPluginArtifactProvenanceReport,
) -> BackendPluginArtifactProvenanceReport:
    """Return the report or raise when provenance evidence is incomplete."""

    if not isinstance(report, BackendPluginArtifactProvenanceReport):
        raise TypeError("backend plugin artifact provenance must be report object")
    if not report.provenance_ready:
        lines = ["backend plugin artifact provenance failed:"]
        for issue in report.issues:
            lines.append(f"- {issue.artifact_id}: {issue.issue_code}")
        raise BackendPluginArtifactProvenanceError("\n".join(lines))
    return report


def backend_plugin_artifact_provenance_report_to_dict(
    report: BackendPluginArtifactProvenanceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible provenance report."""

    if not isinstance(report, BackendPluginArtifactProvenanceReport):
        raise TypeError("backend plugin artifact provenance must be report object")
    return {
        "artifact_count": report.artifact_count,
        "artifacts": [
            {
                "artifact_digest": artifact.artifact_digest,
                "artifact_id": artifact.artifact_id,
                "build_recipe_id": artifact.build_recipe_id,
                "review_record_id": artifact.review_record_id,
                "review_status": artifact.review_status,
                "sandbox_model_contract": artifact.sandbox_model_contract,
                "source_scope_id": artifact.source_scope_id,
                "storage_scope": artifact.storage_scope,
            }
            for artifact in report.artifacts
        ],
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "execution_allowed": report.execution_allowed,
        "execution_permission": report.execution_permission,
        "issues": [
            {
                "artifact_id": issue.artifact_id,
                "issue_code": issue.issue_code,
            }
            for issue in report.issues
        ],
        "provenance_contract": report.provenance_contract,
        "provenance_policy": report.provenance_policy,
        "provenance_ready": report.provenance_ready,
        "provenance_status": report.provenance_status,
        "required_bindings": list(report.required_bindings),
        "schema_version": BACKEND_PLUGIN_ARTIFACT_PROVENANCE_REPORT_SCHEMA_VERSION,
    }


def dump_backend_plugin_artifact_provenance_report(
    report: BackendPluginArtifactProvenanceReport,
) -> str:
    """Render a stable backend plugin artifact provenance report."""

    text = json.dumps(
        backend_plugin_artifact_provenance_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BACKEND_PLUGIN_ARTIFACT_REPORT_BYTES:
        raise ValueError("backend plugin artifact provenance report exceeds byte limit")
    return text + "\n"


def _current_artifact_records() -> tuple[BackendPluginArtifactRecord, ...]:
    return (
        BackendPluginArtifactRecord(
            artifact_id="external_vector_lowering_artifact",
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
        ),
    )


def _derive_artifact_issues(
    report: BackendPluginArtifactProvenanceReport,
) -> tuple[BackendPluginArtifactProvenanceIssue, ...]:
    issues: list[BackendPluginArtifactProvenanceIssue] = []
    artifact_ids = tuple(artifact.artifact_id for artifact in report.artifacts)
    duplicate_ids = {
        artifact_id
        for artifact_id in artifact_ids
        if artifact_ids.count(artifact_id) > 1
    }
    for artifact_id in sorted(duplicate_ids):
        issues.append(
            BackendPluginArtifactProvenanceIssue(
                artifact_id=artifact_id,
                issue_code="duplicate_artifact_id",
            )
        )
    for artifact in report.artifacts:
        if not _SHA256_RE.fullmatch(artifact.artifact_digest):
            issues.append(
                BackendPluginArtifactProvenanceIssue(
                    artifact_id=artifact.artifact_id,
                    issue_code="invalid_artifact_digest",
                )
            )
        if artifact.storage_scope not in BACKEND_PLUGIN_ARTIFACT_STORAGE_SCOPES:
            issues.append(
                BackendPluginArtifactProvenanceIssue(
                    artifact_id=artifact.artifact_id,
                    issue_code="invalid_storage_scope",
                )
            )
        if artifact.review_status not in BACKEND_PLUGIN_ARTIFACT_STATUSES:
            issues.append(
                BackendPluginArtifactProvenanceIssue(
                    artifact_id=artifact.artifact_id,
                    issue_code="artifact_review_status_invalid",
                )
            )
        if artifact.sandbox_model_contract != BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT:
            issues.append(
                BackendPluginArtifactProvenanceIssue(
                    artifact_id=artifact.artifact_id,
                    issue_code="sandbox_binding_mismatch",
                )
            )
        for binding in BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS:
            if not _artifact_has_binding(artifact, binding):
                issues.append(
                    BackendPluginArtifactProvenanceIssue(
                        artifact_id=artifact.artifact_id,
                        issue_code="artifact_missing_required_binding",
                    )
                )
    if report.execution_permission != BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION:
        for artifact in report.artifacts:
            issues.append(
                BackendPluginArtifactProvenanceIssue(
                    artifact_id=artifact.artifact_id,
                    issue_code="artifact_execution_permission_granted",
                )
            )
    return tuple(issues)


def _artifact_has_binding(
    artifact: BackendPluginArtifactRecord,
    binding: str,
) -> bool:
    if binding == "sandbox_model":
        return artifact.sandbox_model_contract == BACKEND_PLUGIN_SANDBOX_MODEL_CONTRACT
    if binding == "content_digest":
        return bool(_SHA256_RE.fullmatch(artifact.artifact_digest))
    if binding == "source_scope":
        return artifact.source_scope_id != "not_supplied"
    if binding == "build_recipe":
        return artifact.build_recipe_id != "not_supplied"
    if binding == "review_record":
        return artifact.review_record_id != "not_supplied"
    return False


def _validate_provenance_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROVENANCE_TEXT_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe backend artifact identifier")
    if len(value.encode("utf-8")) > MAX_BACKEND_PLUGIN_ARTIFACT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds backend artifact field limit")
    if value in _FORBIDDEN_PROVENANCE_TEXT:
        raise ValueError(f"{label} names a forbidden execution surface")


def _validate_digest(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("backend artifact digest must be a string")
    if not _SHA256_RE.fullmatch(value):
        raise ValueError("backend artifact digest must be a sha256 digest")


__all__ = [
    "BACKEND_PLUGIN_ARTIFACT_PROVENANCE_CONTRACT",
    "BACKEND_PLUGIN_ARTIFACT_PROVENANCE_EXECUTION_PERMISSION",
    "BACKEND_PLUGIN_ARTIFACT_PROVENANCE_ISSUE_CODES",
    "BACKEND_PLUGIN_ARTIFACT_PROVENANCE_POLICY",
    "BACKEND_PLUGIN_ARTIFACT_PROVENANCE_REPORT_SCHEMA_VERSION",
    "BACKEND_PLUGIN_ARTIFACT_PROVENANCE_STATUS",
    "BACKEND_PLUGIN_ARTIFACT_REQUIRED_BINDINGS",
    "BACKEND_PLUGIN_ARTIFACT_STATUSES",
    "BACKEND_PLUGIN_ARTIFACT_STORAGE_SCOPES",
    "MAX_BACKEND_PLUGIN_ARTIFACT_FIELD_BYTES",
    "MAX_BACKEND_PLUGIN_ARTIFACT_ISSUES",
    "MAX_BACKEND_PLUGIN_ARTIFACT_REPORT_BYTES",
    "MAX_BACKEND_PLUGIN_ARTIFACTS",
    "BackendPluginArtifactProvenanceError",
    "BackendPluginArtifactProvenanceIssue",
    "BackendPluginArtifactProvenanceReport",
    "BackendPluginArtifactRecord",
    "assert_backend_plugin_artifact_provenance",
    "backend_plugin_artifact_provenance_report_to_dict",
    "build_backend_plugin_artifact_provenance_report",
    "dump_backend_plugin_artifact_provenance_report",
]
