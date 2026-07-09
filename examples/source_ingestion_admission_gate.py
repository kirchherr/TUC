"""Emit the fail-closed source-ingestion admission gate report."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.source_ingestion_maintainer_approval_artifact import (
    assert_source_ingestion_maintainer_approval_artifact_report_contract,
    build_report as build_maintainer_approval_artifact_report,
)
from examples.source_ingestion_maintainer_security_review_packet import (
    SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
    assert_source_ingestion_maintainer_security_review_packet_contract,
    build_report as build_maintainer_review_packet_report,
)
from tuc.frontend.source_ingestion_admission_gate import (
    SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS,
    SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS,
    SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
    SOURCE_INGESTION_ADMISSION_GATE_DECISION,
    SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY,
    SOURCE_INGESTION_ADMISSION_GATE_ID,
    SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS,
    SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_ADMISSION_GATE_STATUS,
    SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE,
    SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE,
    build_source_ingestion_admission_gate_report,
    source_ingestion_admission_gate_evidence_from_payload,
    source_ingestion_admission_gate_report_to_dict,
)

SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_admission_gate_report.v0"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_status",
        "admitted",
        "approval_artifact_present",
        "approval_required",
        "approval_status",
        "blocked_execution_surfaces",
        "decision",
        "direct_source_ingestion",
        "evidence_policy",
        "gate_contract",
        "gate_id",
        "gate_report_digest",
        "gate_status",
        "issues",
        "maintainer_approval_artifact",
        "maintainer_review_packet",
        "required_control_count",
        "required_controls",
        "required_external_evidence",
        "required_external_evidence_count",
        "schema_version",
        "source_ingestion_admission_ready",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_runtime_plan",
        "target_slice",
        "target_surface",
    }
)
_EVIDENCE_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "source_free", "status", "supports_gate"}
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


class SourceIngestionAdmissionGateReportError(AssertionError):
    """Raised when the source-ingestion admission-gate report drifts."""


def build_source_ingestion_admission_gate_report_payload() -> dict[str, object]:
    """Build the current fail-closed source-ingestion admission gate."""

    review_packet_payload = _build_review_packet_payload()
    review_evidence = source_ingestion_admission_gate_evidence_from_payload(
        review_packet_payload
    )
    approval_artifact_payload = _build_approval_artifact_payload(
        review_packet_payload
    )
    approval_evidence = source_ingestion_admission_gate_evidence_from_payload(
        approval_artifact_payload
    )
    gate = build_source_ingestion_admission_gate_report(
        review_evidence,
        approval_evidence,
    )
    report: dict[str, object] = {
        **source_ingestion_admission_gate_report_to_dict(gate),
        "issues": [],
        "schema_version": SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION,
    }
    report["gate_report_digest"] = _digest_payload(report)
    assert_source_ingestion_admission_gate_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the source-ingestion admission gate."""

    return json.dumps(
        build_source_ingestion_admission_gate_report_payload(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_ingestion_admission_gate_report_contract(
    report: object,
) -> None:
    """Fail closed unless the source-ingestion admission gate matches v0."""

    if not isinstance(report, Mapping):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate top-level keys drift"
        )
    expected = {
        "admission_status": SOURCE_INGESTION_ADMISSION_GATE_ADMISSION_STATUS,
        "admitted": False,
        "approval_artifact_present": False,
        "approval_required": True,
        "approval_status": SOURCE_INGESTION_ADMISSION_GATE_APPROVAL_STATUS,
        "decision": SOURCE_INGESTION_ADMISSION_GATE_DECISION,
        "direct_source_ingestion": False,
        "evidence_policy": SOURCE_INGESTION_ADMISSION_GATE_EVIDENCE_POLICY,
        "gate_contract": SOURCE_INGESTION_ADMISSION_GATE_CONTRACT,
        "gate_id": SOURCE_INGESTION_ADMISSION_GATE_ID,
        "gate_status": SOURCE_INGESTION_ADMISSION_GATE_STATUS,
        "required_control_count": len(SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS),
        "required_external_evidence_count": len(
            SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE
        ),
        "schema_version": SOURCE_INGESTION_ADMISSION_GATE_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "target_slice": SOURCE_INGESTION_ADMISSION_GATE_TARGET_SLICE,
        "target_surface": SOURCE_INGESTION_ADMISSION_GATE_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceIngestionAdmissionGateReportError(
                f"source-ingestion admission gate {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_INGESTION_ADMISSION_GATE_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_string_sequence(
        report.get("required_external_evidence"),
        SOURCE_INGESTION_ADMISSION_GATE_REQUIRED_EXTERNAL_EVIDENCE,
        "required_external_evidence",
    )
    _assert_maintainer_approval_artifact(report.get("maintainer_approval_artifact"))
    _assert_maintainer_review_packet(report.get("maintainer_review_packet"))
    if report.get("issues") != []:
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate issues must be empty"
        )
    report_digest = report.get("gate_report_digest")
    if not isinstance(report_digest, str) or not _SHA256_RE.fullmatch(report_digest):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate digest invalid"
        )
    if report_digest != _digest_payload(report):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_review_packet_payload() -> Mapping[str, object]:
    text = build_maintainer_review_packet_report()
    _assert_text_is_source_free(text)
    payload = json.loads(text)
    assert_source_ingestion_maintainer_security_review_packet_contract(payload)
    if not isinstance(payload, Mapping):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate review packet must be object"
        )
    return payload


def _build_approval_artifact_payload(
    review_packet_payload: Mapping[str, object],
) -> Mapping[str, object]:
    text = build_maintainer_approval_artifact_report()
    _assert_text_is_source_free(text)
    payload = json.loads(text)
    assert_source_ingestion_maintainer_approval_artifact_report_contract(payload)
    if not isinstance(payload, Mapping):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate approval artifact must be object"
        )
    artifact_packet = payload.get("maintainer_review_packet")
    if not isinstance(artifact_packet, Mapping):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate approval artifact packet missing"
        )
    expected_digest = _digest_payload(review_packet_payload)
    if artifact_packet.get("digest") != expected_digest:
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate approval artifact packet digest drift"
        )
    return payload


def _assert_maintainer_approval_artifact(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _EVIDENCE_KEYS:
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate approval artifact keys drift"
        )
    expected = {
        "contract": "source_ingestion_maintainer_approval_artifact.absent.v0",
        "evidence_id": "source_ingestion_maintainer_approval_artifact",
        "source_free": True,
        "status": "external_approval_not_supplied",
        "supports_gate": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SourceIngestionAdmissionGateReportError(
                f"source-ingestion admission gate approval artifact {key} drift"
            )
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate approval artifact digest invalid"
        )


def _assert_maintainer_review_packet(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _EVIDENCE_KEYS:
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate evidence keys drift"
        )
    expected = {
        "evidence_id": SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
        "source_free": True,
        "supports_gate": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SourceIngestionAdmissionGateReportError(
                f"source-ingestion admission gate evidence {key} drift"
            )
    for text_key in ("evidence_id", "contract", "status"):
        text_value = value.get(text_key)
        if not isinstance(text_value, str) or not _REPORT_TEXT_RE.fullmatch(text_value):
            raise SourceIngestionAdmissionGateReportError(
                f"source-ingestion admission gate evidence {text_key} invalid"
            )
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate evidence digest invalid"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceIngestionAdmissionGateReportError(
            f"source-ingestion admission gate {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceIngestionAdmissionGateReportError(
            "source-ingestion admission gate expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceIngestionAdmissionGateReportError(
                "source-ingestion admission gate string list item invalid"
            )
        result.append(item)
    return result


def _digest_payload(payload: Mapping[str, object]) -> str:
    value = dict(payload)
    value.pop("gate_report_digest", None)
    text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionAdmissionGateReportError(
                f"source-ingestion admission gate contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
