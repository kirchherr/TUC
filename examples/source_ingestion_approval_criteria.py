"""Emit data-only approval criteria for the future source-ingestion slice."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from tuc.frontend.source_ingestion_approval_criteria import (
    SOURCE_INGESTION_APPROVAL_CRITERIA_ADMISSION_EFFECT,
    SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS,
    SOURCE_INGESTION_APPROVAL_CRITERIA_ARTIFACT_POLICY,
    SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS,
    SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT,
    SOURCE_INGESTION_APPROVAL_CRITERIA_ID,
    SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA,
    SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS,
    SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE,
    SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE,
    build_source_ingestion_approval_criteria_report,
    source_ingestion_approval_criteria_report_to_dict,
)

SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_approval_criteria_report.v0"
)
SOURCE_INGESTION_APPROVAL_CRITERIA_WORKFLOW_STEP = (
    "python examples/source_ingestion_approval_criteria.py"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_effect",
        "admitted",
        "approval_artifact_present",
        "approval_required",
        "approval_status",
        "artifact_policy",
        "blocked_claims",
        "blocked_execution_surfaces",
        "criteria_contract",
        "criteria_id",
        "criteria_ready",
        "criteria_status",
        "direct_source_ingestion",
        "evidence_id",
        "execution_permission",
        "issues",
        "remaining_external_evidence",
        "remaining_external_evidence_count",
        "report_digest",
        "required_criteria",
        "required_criteria_count",
        "schema_version",
        "source_ingestion_admission_ready",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
        "target_slice",
        "target_surface",
    }
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import os",
    "import triton",
    "tl.dot",
    "tl.store",
    '"backend_artifact":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
)


class SourceIngestionApprovalCriteriaReportError(AssertionError):
    """Raised when source-ingestion approval criteria evidence drifts."""


def build_source_ingestion_approval_criteria_report_payload() -> dict[str, object]:
    """Build the current source-ingestion approval criteria report."""

    base_report = build_source_ingestion_approval_criteria_report()
    report: dict[str, object] = {
        **source_ingestion_approval_criteria_report_to_dict(base_report),
        "issues": [],
        "schema_version": SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION,
    }
    report["report_digest"] = _digest_payload(report)
    assert_source_ingestion_approval_criteria_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for source-ingestion approval criteria."""

    return json.dumps(
        build_source_ingestion_approval_criteria_report_payload(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_ingestion_approval_criteria_report_contract(report: object) -> None:
    """Fail closed unless approval criteria match v0."""

    if not isinstance(report, Mapping):
        raise SourceIngestionApprovalCriteriaReportError(
            "approval criteria report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceIngestionApprovalCriteriaReportError(
            "approval criteria top-level keys drift"
        )
    expected = {
        "admission_effect": SOURCE_INGESTION_APPROVAL_CRITERIA_ADMISSION_EFFECT,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_required": True,
        "approval_status": SOURCE_INGESTION_APPROVAL_CRITERIA_APPROVAL_STATUS,
        "artifact_policy": SOURCE_INGESTION_APPROVAL_CRITERIA_ARTIFACT_POLICY,
        "criteria_contract": SOURCE_INGESTION_APPROVAL_CRITERIA_CONTRACT,
        "criteria_id": SOURCE_INGESTION_APPROVAL_CRITERIA_ID,
        "criteria_ready": True,
        "criteria_status": SOURCE_INGESTION_APPROVAL_CRITERIA_STATUS,
        "direct_source_ingestion": False,
        "evidence_id": SOURCE_INGESTION_APPROVAL_CRITERIA_ID,
        "execution_permission": "not_granted",
        "remaining_external_evidence_count": len(
            SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE
        ),
        "required_criteria_count": len(
            SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA
        ),
        "schema_version": SOURCE_INGESTION_APPROVAL_CRITERIA_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "target_slice": SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SLICE,
        "target_surface": SOURCE_INGESTION_APPROVAL_CRITERIA_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceIngestionApprovalCriteriaReportError(
                f"approval criteria {key} drift"
            )
    _assert_string_sequence(
        report.get("required_criteria"),
        SOURCE_INGESTION_APPROVAL_CRITERIA_REQUIRED_CRITERIA,
        "required_criteria",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_INGESTION_APPROVAL_CRITERIA_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("remaining_external_evidence"),
        SOURCE_INGESTION_APPROVAL_CRITERIA_REMAINING_EXTERNAL_EVIDENCE,
        "remaining_external_evidence",
    )
    if report.get("issues") != []:
        raise SourceIngestionApprovalCriteriaReportError(
            "approval criteria issues must be empty"
        )
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceIngestionApprovalCriteriaReportError(
            "approval criteria digest invalid"
        )
    if digest != _digest_payload(report):
        raise SourceIngestionApprovalCriteriaReportError(
            "approval criteria digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceIngestionApprovalCriteriaReportError(
            f"approval criteria {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceIngestionApprovalCriteriaReportError(
            "approval criteria expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceIngestionApprovalCriteriaReportError(
                "approval criteria string list item invalid"
            )
        result.append(item)
    return result


def _digest_payload(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("report_digest", None)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionApprovalCriteriaReportError(
                f"approval criteria contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
