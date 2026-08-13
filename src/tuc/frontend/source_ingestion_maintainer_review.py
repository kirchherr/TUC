"""Maintainer-review packet for the first source-ingestion slice.

This module prepares review evidence only. It never grants approval and never
admits source ingestion into compiler artifacts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT = (
    "source_ingestion_maintainer_security_review_packet.review.v0"
)
SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS = "ready_for_maintainer_review"
SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS = "not_approved"
SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE = "direct_source_ingestion"
SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
SOURCE_INGESTION_MAINTAINER_REVIEW_ARTIFACT_POLICY = "digest_only_source_free"
SOURCE_INGESTION_MAINTAINER_REVIEW_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)
SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS = (
    "bounded_source_buffer_reviewed",
    "sandbox_boundary_reviewed",
    "negative_corpus_reviewed",
    "source_free_diagnostics_reviewed",
    "plain_data_golden_reviewed",
    "ci_replay_reviewed",
    "approval_criteria_reviewed",
    "first_slice_plan_reviewed",
    "approval_criteria_non_admitting",
    "no_raw_source_serialization",
    "no_source_intent_payload_serialization",
    "no_runtime_handle_serialization",
    "no_host_path_serialization",
    "no_command_serialization",
    "direct_source_ingestion_remains_blocked",
    "maintainer_approval_required",
)
SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES = (
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

MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_ITEMS = 9
MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_BYTES = 160 * 1024
MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_FIELD_BYTES = 512

_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source",
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


class SourceIngestionMaintainerReviewError(ValueError):
    """Raised when source-ingestion maintainer-review evidence drifts."""


@dataclass(frozen=True)
class SourceIngestionMaintainerReviewItem:
    """One evidence artifact summarized for maintainer review."""

    evidence_id: str
    contract: str
    status: str
    digest: str
    source_free: bool = True
    reviewable: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.evidence_id, "evidence_id")
        _validate_report_text(self.contract, "contract")
        _validate_report_text(self.status, "status")
        _validate_digest(self.digest, "digest")
        if self.source_free is not True:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review item must be source-free"
            )
        if self.reviewable is not True:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review item must be reviewable"
            )


@dataclass(frozen=True)
class SourceIngestionMaintainerReviewReport:
    """Data-only review packet for the first source-ingestion slice."""

    review_evidence: tuple[SourceIngestionMaintainerReviewItem, ...]
    contract: str = SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT
    status: str = SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS
    approval_status: str = SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS
    target_surface: str = SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE
    target_slice: str = SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE
    artifact_policy: str = SOURCE_INGESTION_MAINTAINER_REVIEW_ARTIFACT_POLICY
    admission_effect: str = SOURCE_INGESTION_MAINTAINER_REVIEW_ADMISSION_EFFECT
    required_checks: tuple[str, ...] = SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES
    )
    remaining_external_evidence: tuple[str, ...] = (
        SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE
    )

    def __post_init__(self) -> None:
        if self.contract != SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review contract drift"
            )
        if self.status != SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS:
            raise SourceIngestionMaintainerReviewError("maintainer-review status drift")
        if self.approval_status != SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review approval status drift"
            )
        if self.target_surface != SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review target surface drift"
            )
        if self.target_slice != SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review target slice drift"
            )
        if self.artifact_policy != SOURCE_INGESTION_MAINTAINER_REVIEW_ARTIFACT_POLICY:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review artifact policy drift"
            )
        if self.admission_effect != SOURCE_INGESTION_MAINTAINER_REVIEW_ADMISSION_EFFECT:
            raise SourceIngestionMaintainerReviewError(
                "maintainer-review admission effect drift"
            )
        _validate_exact_tuple(
            self.required_checks,
            SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS,
            "required_checks",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.remaining_external_evidence,
            SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE,
            "remaining_external_evidence",
        )
        _validate_review_evidence(self.review_evidence)

    @property
    def review_evidence_count(self) -> int:
        """Return number of review evidence items."""

        return len(self.review_evidence)

    @property
    def approval_required(self) -> bool:
        """Return whether a real maintainer approval is still required."""

        return True


def build_source_ingestion_maintainer_review_report(
    review_evidence: Iterable[SourceIngestionMaintainerReviewItem],
) -> SourceIngestionMaintainerReviewReport:
    """Build source-ingestion maintainer-review evidence."""

    return SourceIngestionMaintainerReviewReport(tuple(review_evidence))


def source_ingestion_maintainer_review_report_to_dict(
    report: SourceIngestionMaintainerReviewReport,
) -> dict[str, object]:
    """Return stable JSON-ready maintainer-review evidence."""

    if not isinstance(report, SourceIngestionMaintainerReviewReport):
        raise TypeError("maintainer-review report must be report object")
    return {
        "admission_effect": report.admission_effect,
        "approval_required": report.approval_required,
        "approval_status": report.approval_status,
        "artifact_policy": report.artifact_policy,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "contract": report.contract,
        "direct_source_ingestion": False,
        "remaining_external_evidence": list(report.remaining_external_evidence),
        "remaining_external_evidence_count": len(report.remaining_external_evidence),
        "required_check_count": len(report.required_checks),
        "required_checks": list(report.required_checks),
        "review_evidence": [
            {
                "contract": item.contract,
                "digest": item.digest,
                "evidence_id": item.evidence_id,
                "reviewable": item.reviewable,
                "source_free": item.source_free,
                "status": item.status,
            }
            for item in report.review_evidence
        ],
        "review_evidence_count": report.review_evidence_count,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "status": report.status,
        "target_slice": report.target_slice,
        "target_surface": report.target_surface,
    }


def digest_json_payload(payload: Mapping[str, object]) -> str:
    """Return canonical digest for JSON-compatible payloads."""

    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def dump_source_ingestion_maintainer_review_report(
    report: SourceIngestionMaintainerReviewReport,
) -> str:
    """Render stable source-ingestion maintainer-review evidence."""

    payload = source_ingestion_maintainer_review_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_BYTES:
        raise SourceIngestionMaintainerReviewError(
            "maintainer-review report exceeds byte limit"
        )
    return text + "\n"


def _validate_review_evidence(
    review_evidence: tuple[SourceIngestionMaintainerReviewItem, ...],
) -> None:
    if type(review_evidence) is not tuple:
        raise TypeError("maintainer-review evidence must be tuple")
    if len(review_evidence) > MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_ITEMS:
        raise SourceIngestionMaintainerReviewError(
            "maintainer-review evidence count exceeds limit"
        )
    evidence_ids = [item.evidence_id for item in review_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise SourceIngestionMaintainerReviewError(
            "maintainer-review evidence IDs must be unique"
        )
    digests = [item.digest for item in review_evidence]
    if len(digests) != len(set(digests)):
        raise SourceIngestionMaintainerReviewError(
            "maintainer-review evidence digests must be unique"
        )


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"maintainer-review {label} must be tuple")
    if values != expected:
        raise SourceIngestionMaintainerReviewError(
            f"maintainer-review {label} drift"
        )
    for value in values:
        _validate_report_text(value, label)


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceIngestionMaintainerReviewError(
            f"maintainer-review {label} must be report-safe"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceIngestionMaintainerReviewError(
            f"maintainer-review {label} must be report-safe"
        )
    if len(value.encode("utf-8")) > MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_FIELD_BYTES:
        raise SourceIngestionMaintainerReviewError(
            f"maintainer-review {label} exceeds limit"
        )


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceIngestionMaintainerReviewError(
            f"maintainer-review {label} must be sha256"
        )


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in _FORBIDDEN_TEXT_FRAGMENTS:
        if fragment in lowered:
            raise SourceIngestionMaintainerReviewError(
                f"maintainer-review contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_FIELD_BYTES",
    "MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_ITEMS",
    "MAX_SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_BYTES",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_ADMISSION_EFFECT",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_ARTIFACT_POLICY",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE",
    "SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE",
    "SourceIngestionMaintainerReviewError",
    "SourceIngestionMaintainerReviewItem",
    "SourceIngestionMaintainerReviewReport",
    "build_source_ingestion_maintainer_review_report",
    "digest_json_payload",
    "dump_source_ingestion_maintainer_review_report",
    "source_ingestion_maintainer_review_report_to_dict",
]
