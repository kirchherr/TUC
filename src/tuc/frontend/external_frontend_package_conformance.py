"""Data-only conformance report for external frontend package authors.

This module validates a package-shaped frontend claim without importing the
package, discovering plugins, executing source, or opening a Triton JIT/device
surface. A candidate package is represented by a bounded manifest plus
Source Intent plain-data fixtures. The fixtures are checked through the
existing Source Intent frontend conformance path, while this report serializes
only package metadata, fixture digests, counts, and blocked surfaces.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent_conformance import (
    SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION,
    SourceIntentFrontendConformanceCase,
    SourceIntentFrontendConformanceReport,
    run_source_intent_frontend_conformance,
    source_intent_frontend_conformance_report_to_dict,
)
from tuc.frontend.source_intent_intake import SOURCE_INTENT_SCHEMA_VERSION

EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION = (
    "tuc.external_frontend_package_conformance_report.v0"
)
EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT = (
    "external_frontend_package_conformance.data_only.v0"
)
EXTERNAL_FRONTEND_PACKAGE_INTERFACE_CONTRACT = (
    "external_frontend.source_intent_plain_data.v0"
)
EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_ARTIFACT_STATUS = "review_evidence_only"
EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_STATUS_PASS = "pass"
EXTERNAL_FRONTEND_PACKAGE_IMPORT_POLICY = "not_imported"
EXTERNAL_FRONTEND_PACKAGE_FIXTURE_POLICY = "digest_only_plain_data_fixtures"
EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES = (
    "does_not_require_package_import",
    "emits_source_intent_plain_data",
    "fails_closed_on_invalid_payloads",
    "omits_raw_source_from_reports",
    "supports_explicit_public_returns",
    "supports_mvp_operation_families",
)
EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES = (
    "backend_artifact_execution",
    "bytecode_compilation",
    "decorator_evaluation",
    "device_access",
    "direct_source_ingestion",
    "dynamic_library_loading",
    "frontend_package_import",
    "generated_artifact_execution",
    "jit_execution",
    "network_access",
    "plugin_discovery",
    "python_function_object_inspection",
    "python_import",
    "subprocess_execution",
)
EXTERNAL_FRONTEND_PACKAGE_BLOCKED_ARTIFACTS = (
    "backend_artifact",
    "command_line",
    "device_id",
    "environment",
    "generated_code",
    "host_path",
    "plugin_entrypoint",
    "python_source",
    "raw_source_text",
    "raw_timing_samples",
    "runtime_handle",
)
MAX_EXTERNAL_FRONTEND_PACKAGE_CASES = 128
MAX_EXTERNAL_FRONTEND_PACKAGE_CAPABILITIES = 32
MAX_EXTERNAL_FRONTEND_PACKAGE_FIELD_BYTES = 512
MAX_EXTERNAL_FRONTEND_PACKAGE_REPORT_BYTES = 128 * 1024

_REPORT_TEXT_RE = re.compile(r"^(sha256:[a-f0-9]{64}|[A-Za-z][A-Za-z0-9_.-]*)$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
        "environment",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_timing_samples",
        "runtime_handle",
        "source_text",
        "url",
    }
)


@dataclass(frozen=True)
class ExternalFrontendPackageManifest:
    """Data-only manifest for an external Source Intent frontend package."""

    package_name: str
    package_version: str
    declared_capabilities: tuple[str, ...]
    interface_contract: str = EXTERNAL_FRONTEND_PACKAGE_INTERFACE_CONTRACT
    emitted_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    import_policy: str = EXTERNAL_FRONTEND_PACKAGE_IMPORT_POLICY
    execution_permission: bool = False

    def __post_init__(self) -> None:
        _validate_report_text(self.package_name, "package_name")
        _validate_report_text(self.package_version, "package_version")
        _validate_features(self.declared_capabilities, "declared_capabilities")
        if self.interface_contract != EXTERNAL_FRONTEND_PACKAGE_INTERFACE_CONTRACT:
            raise ValueError("external frontend package interface contract mismatch")
        if self.emitted_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise ValueError("external frontend package schema version mismatch")
        if self.import_policy != EXTERNAL_FRONTEND_PACKAGE_IMPORT_POLICY:
            raise ValueError("external frontend package import policy mismatch")
        if type(self.execution_permission) is not bool:
            raise TypeError("external frontend package execution permission must be bool")
        if self.execution_permission:
            raise ValueError("external frontend package execution permission is blocked")
        if self.declared_capabilities != EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES:
            raise ValueError("external frontend package required capabilities missing")


@dataclass(frozen=True)
class ExternalFrontendPackageFixtureDigest:
    """Digest-only reference to one package-provided plain-data fixture."""

    case_name: str
    payload_digest: str
    should_accept: bool

    def __post_init__(self) -> None:
        _validate_report_text(self.case_name, "case_name")
        _validate_sha256(self.payload_digest, "payload_digest")
        if type(self.should_accept) is not bool:
            raise TypeError("external frontend fixture should_accept must be bool")


@dataclass(frozen=True)
class ExternalFrontendPackageConformanceReport:
    """Review artifact for external frontend package conformance."""

    manifest: ExternalFrontendPackageManifest
    fixture_digests: tuple[ExternalFrontendPackageFixtureDigest, ...]
    conformance_report_digest: str
    checked_cases: tuple[str, ...]
    accepted_case_count: int
    rejected_case_count: int
    conformance_passed: bool
    conformance_contract: str = EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT
    artifact_status: str = EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_ARTIFACT_STATUS
    fixture_policy: str = EXTERNAL_FRONTEND_PACKAGE_FIXTURE_POLICY
    source_intent_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    frontend_conformance_schema_version: str = (
        SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES
    )
    blocked_artifacts: tuple[str, ...] = EXTERNAL_FRONTEND_PACKAGE_BLOCKED_ARTIFACTS

    def __post_init__(self) -> None:
        if not isinstance(self.manifest, ExternalFrontendPackageManifest):
            raise TypeError("external frontend conformance requires manifest object")
        _validate_fixture_digests(self.fixture_digests)
        _validate_sha256(self.conformance_report_digest, "conformance_report_digest")
        _validate_case_names(self.checked_cases, "checked_cases")
        _validate_non_negative_int(self.accepted_case_count, "accepted_case_count")
        _validate_non_negative_int(self.rejected_case_count, "rejected_case_count")
        if (
            self.accepted_case_count + self.rejected_case_count
            != len(self.checked_cases)
        ):
            raise ValueError("external frontend conformance case counts mismatch")
        if not self.accepted_case_count or not self.rejected_case_count:
            raise ValueError("external frontend conformance requires both case kinds")
        if type(self.conformance_passed) is not bool:
            raise TypeError("external frontend conformance passed flag must be bool")
        if not self.conformance_passed:
            raise ValueError("external frontend package conformance must pass")
        if self.conformance_contract != EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT:
            raise ValueError("external frontend package conformance contract mismatch")
        if self.artifact_status != EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_ARTIFACT_STATUS:
            raise ValueError("external frontend package artifact status mismatch")
        if self.fixture_policy != EXTERNAL_FRONTEND_PACKAGE_FIXTURE_POLICY:
            raise ValueError("external frontend package fixture policy mismatch")
        if self.source_intent_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise ValueError("external frontend package source-intent schema mismatch")
        if (
            self.frontend_conformance_schema_version
            != SOURCE_INTENT_FRONTEND_CONFORMANCE_REPORT_SCHEMA_VERSION
        ):
            raise ValueError("external frontend conformance schema mismatch")
        if self.blocked_execution_surfaces != (
            EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("external frontend package blocked surfaces changed")
        if self.blocked_artifacts != EXTERNAL_FRONTEND_PACKAGE_BLOCKED_ARTIFACTS:
            raise ValueError("external frontend package blocked artifacts changed")
        if tuple(item.case_name for item in self.fixture_digests) != self.checked_cases:
            raise ValueError("external frontend fixture digests must match checked cases")

    @property
    def package_manifest_digest(self) -> str:
        """Return digest of the package manifest metadata."""

        return _digest_mapping(_manifest_to_dict(self.manifest))

    @property
    def package_imported(self) -> bool:
        return False

    @property
    def plugin_discovery(self) -> bool:
        return False

    @property
    def direct_source_ingestion(self) -> bool:
        return False

    @property
    def triton_jit_execution(self) -> bool:
        return False

    @property
    def capability_coverage_complete(self) -> bool:
        return self.manifest.declared_capabilities == (
            EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES
        )

    @property
    def conformance_status(self) -> str:
        return EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_STATUS_PASS


def build_external_frontend_package_conformance_report(
    manifest: ExternalFrontendPackageManifest,
    cases: Iterable[SourceIntentFrontendConformanceCase],
) -> ExternalFrontendPackageConformanceReport:
    """Build external frontend package conformance without importing a package."""

    if not isinstance(manifest, ExternalFrontendPackageManifest):
        raise TypeError("external frontend package conformance requires manifest")
    normalized_cases = tuple(cases)
    if not normalized_cases:
        raise ValueError("external frontend package conformance requires cases")
    if len(normalized_cases) > MAX_EXTERNAL_FRONTEND_PACKAGE_CASES:
        raise ValueError("external frontend package conformance case count exceeds limit")
    _validate_cases(normalized_cases)
    conformance_report = run_source_intent_frontend_conformance(
        manifest.package_name,
        normalized_cases,
    )
    if not conformance_report.passed:
        raise ValueError("external frontend package source-intent conformance failed")
    fixture_digests = tuple(_fixture_digest_from_case(case) for case in normalized_cases)
    return ExternalFrontendPackageConformanceReport(
        manifest=manifest,
        fixture_digests=fixture_digests,
        conformance_report_digest=_conformance_report_digest(conformance_report),
        checked_cases=conformance_report.checked_cases,
        accepted_case_count=conformance_report.accepted_case_count,
        rejected_case_count=conformance_report.rejected_case_count,
        conformance_passed=conformance_report.passed,
    )


def external_frontend_package_conformance_report_to_dict(
    report: ExternalFrontendPackageConformanceReport,
) -> dict[str, object]:
    """Return stable JSON-ready package conformance evidence."""

    if not isinstance(report, ExternalFrontendPackageConformanceReport):
        raise TypeError("external frontend package conformance report must be report")
    return {
        "accepted_case_count": report.accepted_case_count,
        "artifact_status": report.artifact_status,
        "blocked_artifacts": list(report.blocked_artifacts),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "capability_coverage_complete": report.capability_coverage_complete,
        "checked_cases": list(report.checked_cases),
        "conformance_contract": report.conformance_contract,
        "conformance_passed": report.conformance_passed,
        "conformance_report_digest": report.conformance_report_digest,
        "conformance_status": report.conformance_status,
        "direct_source_ingestion": report.direct_source_ingestion,
        "fixture_digests": [
            {
                "case_name": item.case_name,
                "payload_digest": item.payload_digest,
                "should_accept": item.should_accept,
            }
            for item in report.fixture_digests
        ],
        "fixture_policy": report.fixture_policy,
        "frontend_conformance_schema_version": (
            report.frontend_conformance_schema_version
        ),
        "package_imported": report.package_imported,
        "package_manifest": _manifest_to_dict(report.manifest),
        "package_manifest_digest": report.package_manifest_digest,
        "plugin_discovery": report.plugin_discovery,
        "rejected_case_count": report.rejected_case_count,
        "schema_version": EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION,
        "source_intent_schema_version": report.source_intent_schema_version,
        "triton_jit_execution": report.triton_jit_execution,
    }


def dump_external_frontend_package_conformance_report(
    report: ExternalFrontendPackageConformanceReport,
) -> str:
    """Render stable JSON external frontend package conformance evidence."""

    text = json.dumps(
        external_frontend_package_conformance_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_EXTERNAL_FRONTEND_PACKAGE_REPORT_BYTES:
        raise ValueError("external frontend package conformance report exceeds limit")
    return f"{text}\n"


def default_external_frontend_package_manifest() -> ExternalFrontendPackageManifest:
    """Return the current reference external frontend package manifest."""

    return ExternalFrontendPackageManifest(
        package_name="reference_external_source_intent_frontend",
        package_version="v0.0.0_research",
        declared_capabilities=EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES,
    )


def _fixture_digest_from_case(
    case: SourceIntentFrontendConformanceCase,
) -> ExternalFrontendPackageFixtureDigest:
    return ExternalFrontendPackageFixtureDigest(
        case_name=case.name,
        payload_digest=_digest_payload(case.payload),
        should_accept=case.should_accept,
    )


def _conformance_report_digest(report: SourceIntentFrontendConformanceReport) -> str:
    return _digest_mapping(source_intent_frontend_conformance_report_to_dict(report))


def _manifest_to_dict(manifest: ExternalFrontendPackageManifest) -> dict[str, object]:
    return {
        "declared_capabilities": list(manifest.declared_capabilities),
        "emitted_schema_version": manifest.emitted_schema_version,
        "execution_permission": manifest.execution_permission,
        "import_policy": manifest.import_policy,
        "interface_contract": manifest.interface_contract,
        "package_name": manifest.package_name,
        "package_version": manifest.package_version,
    }


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _digest_mapping(payload: Mapping[str, object]) -> str:
    if not isinstance(payload, Mapping):
        raise TypeError("external frontend package digest payload must be mapping")
    return _digest_payload(dict(payload))


def _validate_cases(cases: tuple[SourceIntentFrontendConformanceCase, ...]) -> None:
    case_names: list[str] = []
    for case in cases:
        if not isinstance(case, SourceIntentFrontendConformanceCase):
            raise TypeError("external frontend conformance cases must be case objects")
        _validate_report_text(case.name, "case_name")
        case_names.append(case.name)
    if len(case_names) != len(set(case_names)):
        raise ValueError("external frontend conformance case names must be unique")


def _validate_fixture_digests(
    fixture_digests: tuple[ExternalFrontendPackageFixtureDigest, ...],
) -> None:
    if type(fixture_digests) is not tuple:
        raise TypeError("external frontend fixture digests must be a tuple")
    if not fixture_digests:
        raise ValueError("external frontend fixture digests must not be empty")
    if len(fixture_digests) > MAX_EXTERNAL_FRONTEND_PACKAGE_CASES:
        raise ValueError("external frontend fixture digest count exceeds limit")
    case_names: list[str] = []
    payload_digests: list[str] = []
    for item in fixture_digests:
        if not isinstance(item, ExternalFrontendPackageFixtureDigest):
            raise TypeError("external frontend fixture digests must be digest objects")
        case_names.append(item.case_name)
        payload_digests.append(item.payload_digest)
    if len(case_names) != len(set(case_names)):
        raise ValueError("external frontend fixture case names must be unique")
    if len(payload_digests) != len(set(payload_digests)):
        raise ValueError("external frontend fixture payload digests must be unique")


def _validate_features(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"external frontend package {label} must be a tuple")
    if len(values) > MAX_EXTERNAL_FRONTEND_PACKAGE_CAPABILITIES:
        raise ValueError(f"external frontend package {label} exceeds limit")
    if tuple(sorted(values)) != values:
        raise ValueError(f"external frontend package {label} must be sorted")
    if len(values) != len(set(values)):
        raise ValueError(f"external frontend package {label} must be unique")
    for value in values:
        _validate_report_text(value, label)


def _validate_case_names(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"external frontend package {label} must be a tuple")
    if len(values) > MAX_EXTERNAL_FRONTEND_PACKAGE_CASES:
        raise ValueError(f"external frontend package {label} exceeds limit")
    if len(values) != len(set(values)):
        raise ValueError(f"external frontend package {label} must be unique")
    for value in values:
        _validate_report_text(value, label)

def _validate_sha256(value: str, label: str) -> None:
    _validate_report_text(value, label)
    if not value.startswith("sha256:"):
        raise ValueError(f"external frontend package {label} must be sha256")


def _validate_non_negative_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"external frontend package {label} must be non-negative")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"external frontend package {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"external frontend package {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_EXTERNAL_FRONTEND_PACKAGE_FIELD_BYTES:
        raise ValueError(f"external frontend package {label} exceeds field limit")


__all__ = [
    "EXTERNAL_FRONTEND_PACKAGE_BLOCKED_ARTIFACTS",
    "EXTERNAL_FRONTEND_PACKAGE_BLOCKED_EXECUTION_SURFACES",
    "EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_ARTIFACT_STATUS",
    "EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_CONTRACT",
    "EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_REPORT_SCHEMA_VERSION",
    "EXTERNAL_FRONTEND_PACKAGE_CONFORMANCE_STATUS_PASS",
    "EXTERNAL_FRONTEND_PACKAGE_FIXTURE_POLICY",
    "EXTERNAL_FRONTEND_PACKAGE_IMPORT_POLICY",
    "EXTERNAL_FRONTEND_PACKAGE_INTERFACE_CONTRACT",
    "EXTERNAL_FRONTEND_PACKAGE_REQUIRED_CAPABILITIES",
    "MAX_EXTERNAL_FRONTEND_PACKAGE_CAPABILITIES",
    "MAX_EXTERNAL_FRONTEND_PACKAGE_CASES",
    "MAX_EXTERNAL_FRONTEND_PACKAGE_REPORT_BYTES",
    "ExternalFrontendPackageConformanceReport",
    "ExternalFrontendPackageFixtureDigest",
    "ExternalFrontendPackageManifest",
    "build_external_frontend_package_conformance_report",
    "default_external_frontend_package_manifest",
    "dump_external_frontend_package_conformance_report",
    "external_frontend_package_conformance_report_to_dict",
]
