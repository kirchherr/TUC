"""Emit the requirements-only RFC report for admitting source ingestion."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256

ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION = (
    "tuc.admitting_source_ingestion_rfc_report.v0"
)
ADMITTING_SOURCE_INGESTION_RFC_CONTRACT = "admitting_source_ingestion_rfc.data_only.v0"
ADMITTING_SOURCE_INGESTION_RFC_ID = "admitting_source_ingestion_rfc"
ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_NAME = (
    "direct_source_ingestion_first_slice"
)
ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_STATUS = "accepted_requirements_only"
ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS = "not_implemented"
ADMITTING_SOURCE_INGESTION_RFC_ADMISSION_STATUS = "blocked"
ADMITTING_SOURCE_INGESTION_RFC_TARGET_SURFACE = "direct_source_ingestion"
ADMITTING_SOURCE_INGESTION_RFC_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
ADMITTING_SOURCE_INGESTION_RFC_ARTIFACT_POLICY = "digest_only_source_free"

ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_INPUTS = (
    "bounded_source_buffer",
    "declared_source_name",
    "declared_shape_profile",
)
ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_OUTPUTS = (
    "source_intent_plain_data",
    "sanitized_diagnostics",
    "metadata_digest",
)
ADMITTING_SOURCE_INGESTION_RFC_DENIED_OUTPUTS = (
    "compute_graph",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "generated_artifact",
    "python_function_object",
    "backend_artifact",
)
ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE = (
    "source_free_diagnostics_admission_tests",
    "source_to_intent_plain_data_output_golden_for_admitted_slice",
    "ci_replay_for_admitted_slice",
    "maintainer_security_review_approval",
)
ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS = (
    "bounded_source_buffer",
    "decode_only_before_validation",
    "source_buffer_size_limit",
    "ast_node_limit",
    "ast_depth_limit",
    "fail_closed_diagnostics",
    "no_python_import",
    "no_triton_jit",
    "no_device_access",
    "no_generated_artifacts",
    "no_source_to_hac_ir_shortcut",
    "source_intent_plain_data_only",
    "digest_only_public_evidence",
    "maintainer_security_review_required",
)
ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_EXECUTION_SURFACES = (
    "frontend_package_import",
    "plugin_discovery",
    "triton_jit_execution",
    "device_access",
    "generated_artifact_execution",
    "native_backend_execution",
    "python_import",
    "network_access",
    "subprocess_execution",
    "dynamic_library_loading",
)
ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_CLAIMS = (
    "accepts_arbitrary_triton_source",
    "production_parser",
    "executes_generated_artifacts",
    "executes_native_backends",
    "imports_external_frontend_packages",
    "runs_triton_jit",
    "uses_real_devices",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_status",
        "admitted",
        "allowed_inputs",
        "allowed_outputs",
        "artifact_policy",
        "blocked_claims",
        "blocked_execution_surfaces",
        "denied_outputs",
        "implementation_status",
        "issues",
        "proposal_name",
        "proposal_status",
        "remaining_evidence",
        "remaining_evidence_count",
        "required_controls",
        "required_controls_count",
        "rfc_contract",
        "rfc_digest",
        "rfc_id",
        "schema_version",
        "source_ingestion_admission_ready",
        "target_slice",
        "target_surface",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TOKEN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_FORBIDDEN_TOKENS = frozenset(
    {
        "backend_artifact_path",
        "command_line",
        "device_id",
        "dynamic_library",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_intent_payload",
        "source_text",
        "url",
    }
)
_FORBIDDEN_TEXT_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
)


class AdmittingSourceIngestionRFCError(AssertionError):
    """Raised when the admitting source-ingestion RFC report is invalid."""


@lru_cache(maxsize=1)
def build_admitting_source_ingestion_rfc_report() -> dict[str, object]:
    """Build the current requirements-only RFC report."""

    report: dict[str, object] = {
        "admission_status": ADMITTING_SOURCE_INGESTION_RFC_ADMISSION_STATUS,
        "admitted": False,
        "allowed_inputs": list(ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_INPUTS),
        "allowed_outputs": list(ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_OUTPUTS),
        "artifact_policy": ADMITTING_SOURCE_INGESTION_RFC_ARTIFACT_POLICY,
        "blocked_claims": list(ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_CLAIMS),
        "blocked_execution_surfaces": list(
            ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_EXECUTION_SURFACES
        ),
        "denied_outputs": list(ADMITTING_SOURCE_INGESTION_RFC_DENIED_OUTPUTS),
        "implementation_status": ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS,
        "issues": [],
        "proposal_name": ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_NAME,
        "proposal_status": ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_STATUS,
        "remaining_evidence": list(ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE),
        "remaining_evidence_count": len(ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE),
        "required_controls": list(ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS),
        "required_controls_count": len(ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS),
        "rfc_contract": ADMITTING_SOURCE_INGESTION_RFC_CONTRACT,
        "rfc_id": ADMITTING_SOURCE_INGESTION_RFC_ID,
        "schema_version": ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "target_slice": ADMITTING_SOURCE_INGESTION_RFC_TARGET_SLICE,
        "target_surface": ADMITTING_SOURCE_INGESTION_RFC_TARGET_SURFACE,
    }
    report["rfc_digest"] = _digest_report_metadata(report)
    assert_admitting_source_ingestion_rfc_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the source-ingestion RFC."""

    return json.dumps(
        build_admitting_source_ingestion_rfc_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_admitting_source_ingestion_rfc_report_contract(report: object) -> None:
    """Fail closed unless the admitting source-ingestion RFC report matches v0."""

    if not isinstance(report, Mapping):
        raise AdmittingSourceIngestionRFCError("source-ingestion RFC report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise AdmittingSourceIngestionRFCError("source-ingestion RFC top-level keys drift")
    expected = {
        "admission_status": ADMITTING_SOURCE_INGESTION_RFC_ADMISSION_STATUS,
        "admitted": False,
        "artifact_policy": ADMITTING_SOURCE_INGESTION_RFC_ARTIFACT_POLICY,
        "implementation_status": ADMITTING_SOURCE_INGESTION_RFC_IMPLEMENTATION_STATUS,
        "proposal_name": ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_NAME,
        "proposal_status": ADMITTING_SOURCE_INGESTION_RFC_PROPOSAL_STATUS,
        "remaining_evidence_count": len(ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE),
        "required_controls_count": len(ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS),
        "rfc_contract": ADMITTING_SOURCE_INGESTION_RFC_CONTRACT,
        "rfc_id": ADMITTING_SOURCE_INGESTION_RFC_ID,
        "schema_version": ADMITTING_SOURCE_INGESTION_RFC_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "target_slice": ADMITTING_SOURCE_INGESTION_RFC_TARGET_SLICE,
        "target_surface": ADMITTING_SOURCE_INGESTION_RFC_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise AdmittingSourceIngestionRFCError(f"source-ingestion RFC {key} drift")
    _assert_string_sequence(
        report.get("allowed_inputs"),
        ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_INPUTS,
        "allowed_inputs",
    )
    _assert_string_sequence(
        report.get("allowed_outputs"),
        ADMITTING_SOURCE_INGESTION_RFC_ALLOWED_OUTPUTS,
        "allowed_outputs",
    )
    _assert_string_sequence(
        report.get("denied_outputs"),
        ADMITTING_SOURCE_INGESTION_RFC_DENIED_OUTPUTS,
        "denied_outputs",
    )
    _assert_string_sequence(
        report.get("remaining_evidence"),
        ADMITTING_SOURCE_INGESTION_RFC_REMAINING_EVIDENCE,
        "remaining_evidence",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        ADMITTING_SOURCE_INGESTION_RFC_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        ADMITTING_SOURCE_INGESTION_RFC_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    if report.get("issues") != []:
        raise AdmittingSourceIngestionRFCError("source-ingestion RFC issues must be empty")
    digest = report.get("rfc_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise AdmittingSourceIngestionRFCError("source-ingestion RFC digest invalid")
    if digest != _digest_report_metadata(report):
        raise AdmittingSourceIngestionRFCError("source-ingestion RFC digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _digest_report_metadata(report: Mapping[str, object]) -> str:
    payload = dict(report)
    payload.pop("rfc_digest", None)
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_string_sequence(value: object, expected: tuple[str, ...], field_name: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise AdmittingSourceIngestionRFCError(f"source-ingestion RFC {field_name} drift")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise AdmittingSourceIngestionRFCError("source-ingestion RFC expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise AdmittingSourceIngestionRFCError(
                "source-ingestion RFC string list item invalid"
            )
        _validate_report_token(item, "list item")
        result.append(item)
    return result


def _validate_report_token(value: str, label: str) -> None:
    if not _REPORT_TOKEN_RE.fullmatch(value) or value in _FORBIDDEN_TOKENS:
        raise AdmittingSourceIngestionRFCError(
            f"source-ingestion RFC {label} is not report-safe"
        )


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise AdmittingSourceIngestionRFCError(
                f"source-ingestion RFC contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
