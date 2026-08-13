"""Emit fail-closed maintainer approval status for source ingestion."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.source_ingestion_maintainer_security_review_packet import (
    assert_source_ingestion_maintainer_security_review_packet_contract,
)
from examples.source_ingestion_maintainer_security_review_packet import (
    build_report as build_maintainer_review_packet_report,
)
from tuc.frontend.source_ingestion_maintainer_approval import (
    SOURCE_INGESTION_MAINTAINER_APPROVAL_ADMISSION_EFFECT,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_APPROVAL_STATUS,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_POLICY,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_DECISION,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_ID,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_CONTRACT,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_ID,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_STATUS,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SLICE,
    SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SURFACE,
    build_source_ingestion_maintainer_approval_report,
    source_ingestion_maintainer_approval_evidence_from_review_packet_payload,
    source_ingestion_maintainer_approval_report_to_dict,
)

SOURCE_INGESTION_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_maintainer_approval_artifact_report.v0"
)
SOURCE_INGESTION_MAINTAINER_APPROVAL_WORKFLOW_STEP = (
    "python examples/source_ingestion_maintainer_approval_artifact.py"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_effect",
        "admitted",
        "approval_artifact_present",
        "approval_decision",
        "approval_required",
        "approval_status",
        "artifact_policy",
        "blocked_execution_surfaces",
        "contract",
        "criteria_bound_by_review_packet",
        "direct_source_ingestion",
        "evidence_id",
        "execution_permission",
        "external_approval_artifact_present",
        "issues",
        "maintainer_review_packet",
        "remaining_external_evidence",
        "remaining_external_evidence_count",
        "required_external_evidence",
        "report_digest",
        "required_control_count",
        "required_controls",
        "schema_version",
        "source_ingestion_admission_ready",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
        "status",
        "target_slice",
        "target_surface",
    }
)
_EVIDENCE_KEYS = frozenset(
    {
        "contract",
        "criteria_bound",
        "digest",
        "evidence_id",
        "reviewable",
        "source_free",
        "status",
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


class SourceIngestionMaintainerApprovalArtifactReportError(AssertionError):
    """Raised when maintainer approval artifact evidence drifts."""


def build_source_ingestion_maintainer_approval_artifact_report() -> dict[str, object]:
    """Build the current fail-closed maintainer approval artifact report."""

    review_packet_payload = _build_review_packet_payload()
    evidence = source_ingestion_maintainer_approval_evidence_from_review_packet_payload(
        review_packet_payload
    )
    approval_report = build_source_ingestion_maintainer_approval_report(evidence)
    report: dict[str, object] = {
        **source_ingestion_maintainer_approval_report_to_dict(approval_report),
        "issues": [],
        "schema_version": SOURCE_INGESTION_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION,
    }
    report["report_digest"] = _digest_payload(report)
    assert_source_ingestion_maintainer_approval_artifact_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for maintainer approval artifact status."""

    return json.dumps(
        build_source_ingestion_maintainer_approval_artifact_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_ingestion_maintainer_approval_artifact_report_contract(
    report: object,
) -> None:
    """Fail closed unless maintainer approval artifact status matches v0."""

    if not isinstance(report, Mapping):
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval artifact report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval artifact top-level keys drift"
        )
    expected = {
        "admission_effect": SOURCE_INGESTION_MAINTAINER_APPROVAL_ADMISSION_EFFECT,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_decision": SOURCE_INGESTION_MAINTAINER_APPROVAL_DECISION,
        "approval_required": True,
        "approval_status": SOURCE_INGESTION_MAINTAINER_APPROVAL_APPROVAL_STATUS,
        "artifact_policy": SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_POLICY,
        "contract": SOURCE_INGESTION_MAINTAINER_APPROVAL_CONTRACT,
        "criteria_bound_by_review_packet": True,
        "direct_source_ingestion": False,
        "evidence_id": SOURCE_INGESTION_MAINTAINER_APPROVAL_ID,
        "execution_permission": "not_granted",
        "external_approval_artifact_present": False,
        "remaining_external_evidence_count": len(
            SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE
        ),
        "required_control_count": len(
            SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS
        ),
        "schema_version": SOURCE_INGESTION_MAINTAINER_APPROVAL_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "status": SOURCE_INGESTION_MAINTAINER_APPROVAL_STATUS,
        "target_slice": SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SLICE,
        "target_surface": SOURCE_INGESTION_MAINTAINER_APPROVAL_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceIngestionMaintainerApprovalArtifactReportError(
                f"maintainer approval artifact {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_INGESTION_MAINTAINER_APPROVAL_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("remaining_external_evidence"),
        SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE,
        "remaining_external_evidence",
    )
    _assert_string_sequence(
        report.get("required_external_evidence"),
        SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_EXTERNAL_EVIDENCE,
        "required_external_evidence",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        SOURCE_INGESTION_MAINTAINER_APPROVAL_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_review_packet(report.get("maintainer_review_packet"))
    if report.get("issues") != []:
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval artifact issues must be empty"
        )
    report_digest = report.get("report_digest")
    if not isinstance(report_digest, str) or not _SHA256_RE.fullmatch(report_digest):
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval artifact digest invalid"
        )
    if report_digest != _digest_payload(report):
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval artifact digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_review_packet_payload() -> Mapping[str, object]:
    text = build_maintainer_review_packet_report()
    _assert_text_is_source_free(text)
    payload = json.loads(text)
    assert_source_ingestion_maintainer_security_review_packet_contract(payload)
    if not isinstance(payload, Mapping):
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval review packet must be object"
        )
    return payload


def _assert_review_packet(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _EVIDENCE_KEYS:
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval review packet keys drift"
        )
    expected = {
        "contract": SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_CONTRACT,
        "criteria_bound": True,
        "evidence_id": SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_ID,
        "reviewable": True,
        "source_free": True,
        "status": SOURCE_INGESTION_MAINTAINER_APPROVAL_REVIEW_PACKET_STATUS,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SourceIngestionMaintainerApprovalArtifactReportError(
                f"maintainer approval review packet {key} drift"
            )
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval review packet digest invalid"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            f"maintainer approval artifact {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceIngestionMaintainerApprovalArtifactReportError(
            "maintainer approval expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceIngestionMaintainerApprovalArtifactReportError(
                "maintainer approval string list item invalid"
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
            raise SourceIngestionMaintainerApprovalArtifactReportError(
                f"maintainer approval artifact contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
