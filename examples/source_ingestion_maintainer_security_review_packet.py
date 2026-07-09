"""Emit the source-ingestion maintainer security review packet."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from hashlib import sha256

from examples.admitting_source_ingestion_rfc import (
    ADMITTING_SOURCE_INGESTION_RFC_ID,
    assert_admitting_source_ingestion_rfc_report_contract,
)
from examples.admitting_source_ingestion_rfc import (
    build_report as build_admitting_source_ingestion_rfc_report,
)
from examples.bounded_source_buffer_api import (
    BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
    assert_bounded_source_buffer_api_report_contract,
)
from examples.bounded_source_buffer_api import (
    build_report as build_bounded_source_buffer_api_report,
)
from examples.ci_replay_for_admitted_slice import (
    CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID,
    assert_ci_replay_for_admitted_slice_report_contract,
)
from examples.ci_replay_for_admitted_slice import (
    build_report as build_ci_replay_for_admitted_slice_report,
)
from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
    assert_parser_fuzz_negative_corpus_report_contract,
)
from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    build_report as build_parser_fuzz_negative_corpus_report,
)
from examples.real_triton_first_slice_plan import (
    REAL_TRITON_FIRST_SLICE_PLAN_ID,
    assert_real_triton_first_slice_plan_report_contract,
)
from examples.real_triton_first_slice_plan import (
    build_report as build_real_triton_first_slice_plan_report,
)
from examples.source_free_diagnostics_admission_tests import (
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
    assert_source_free_diagnostics_admission_report_contract,
)
from examples.source_free_diagnostics_admission_tests import (
    build_report as build_source_free_diagnostics_admission_tests_report,
)
from examples.source_ingestion_sandbox_implementation import (
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
    assert_source_ingestion_sandbox_implementation_report_contract,
)
from examples.source_ingestion_sandbox_implementation import (
    build_report as build_source_ingestion_sandbox_implementation_report,
)
from examples.source_to_intent_plain_data_output_golden_for_admitted_slice import (
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID,
    assert_source_to_intent_admitted_slice_golden_report_contract,
)
from examples.source_to_intent_plain_data_output_golden_for_admitted_slice import (
    build_report as build_source_to_intent_plain_data_output_golden_report,
)
from tuc.frontend.source_ingestion_maintainer_review import (
    SOURCE_INGESTION_MAINTAINER_REVIEW_ADMISSION_EFFECT,
    SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS,
    SOURCE_INGESTION_MAINTAINER_REVIEW_ARTIFACT_POLICY,
    SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT,
    SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE,
    SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS,
    SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS,
    SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE,
    SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE,
    SourceIngestionMaintainerReviewItem,
    build_source_ingestion_maintainer_review_report,
    digest_json_payload,
    source_ingestion_maintainer_review_report_to_dict,
)

SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION = (
    "tuc.source_ingestion_maintainer_security_review_packet_report.v0"
)
SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID = (
    "source_ingestion_maintainer_security_review_packet"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_effect",
        "approval_required",
        "approval_status",
        "artifact_policy",
        "blocked_execution_surfaces",
        "contract",
        "direct_source_ingestion",
        "evidence_id",
        "issues",
        "remaining_external_evidence",
        "remaining_external_evidence_count",
        "report_digest",
        "required_check_count",
        "required_checks",
        "review_evidence",
        "review_evidence_count",
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
_REVIEW_ITEM_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "reviewable", "source_free", "status"}
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

_AssertContract = Callable[[object], None]
_BuildReport = Callable[[], str]

_REVIEW_EVIDENCE_SPECS: tuple[
    tuple[str, _BuildReport, _AssertContract, str, str],
    ...,
] = (
    (
        ADMITTING_SOURCE_INGESTION_RFC_ID,
        build_admitting_source_ingestion_rfc_report,
        assert_admitting_source_ingestion_rfc_report_contract,
        "rfc_contract",
        "proposal_status",
    ),
    (
        BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
        build_bounded_source_buffer_api_report,
        assert_bounded_source_buffer_api_report_contract,
        "api_contract",
        "api_status",
    ),
    (
        SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
        build_source_ingestion_sandbox_implementation_report,
        assert_source_ingestion_sandbox_implementation_report_contract,
        "sandbox_contract",
        "sandbox_status",
    ),
    (
        PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
        build_parser_fuzz_negative_corpus_report,
        assert_parser_fuzz_negative_corpus_report_contract,
        "corpus_contract",
        "corpus_status",
    ),
    (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
        build_source_free_diagnostics_admission_tests_report,
        assert_source_free_diagnostics_admission_report_contract,
        "diagnostics_contract",
        "diagnostics_status",
    ),
    (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID,
        build_source_to_intent_plain_data_output_golden_report,
        assert_source_to_intent_admitted_slice_golden_report_contract,
        "golden_contract",
        "golden_status",
    ),
    (
        CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID,
        build_ci_replay_for_admitted_slice_report,
        assert_ci_replay_for_admitted_slice_report_contract,
        "contract",
        "status",
    ),
    (
        REAL_TRITON_FIRST_SLICE_PLAN_ID,
        build_real_triton_first_slice_plan_report,
        assert_real_triton_first_slice_plan_report_contract,
        "plan_contract",
        "plan_status",
    ),
)
_REVIEW_EVIDENCE_IDS = tuple(spec[0] for spec in _REVIEW_EVIDENCE_SPECS)


class SourceIngestionMaintainerSecurityReviewPacketError(AssertionError):
    """Raised when the maintainer-review packet drifts."""


def build_source_ingestion_maintainer_security_review_packet() -> dict[str, object]:
    """Build the current source-ingestion maintainer-review packet."""

    review_evidence = tuple(_build_review_item(spec) for spec in _REVIEW_EVIDENCE_SPECS)
    base_report = build_source_ingestion_maintainer_review_report(review_evidence)
    payload = source_ingestion_maintainer_review_report_to_dict(base_report)
    report: dict[str, object] = {
        **payload,
        "evidence_id": SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
        "issues": [],
        "schema_version": SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION,
    }
    report["report_digest"] = _digest_payload(report)
    assert_source_ingestion_maintainer_security_review_packet_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the maintainer-review packet."""

    return json.dumps(
        build_source_ingestion_maintainer_security_review_packet(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_ingestion_maintainer_security_review_packet_contract(
    report: object,
) -> None:
    """Fail closed unless the maintainer-review packet matches v0."""

    if not isinstance(report, Mapping):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review packet must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review packet top-level keys drift"
        )
    expected = {
        "admission_effect": SOURCE_INGESTION_MAINTAINER_REVIEW_ADMISSION_EFFECT,
        "approval_required": True,
        "approval_status": SOURCE_INGESTION_MAINTAINER_REVIEW_APPROVAL_STATUS,
        "artifact_policy": SOURCE_INGESTION_MAINTAINER_REVIEW_ARTIFACT_POLICY,
        "contract": SOURCE_INGESTION_MAINTAINER_REVIEW_CONTRACT,
        "direct_source_ingestion": False,
        "evidence_id": SOURCE_INGESTION_MAINTAINER_REVIEW_EVIDENCE_ID,
        "remaining_external_evidence_count": len(
            SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE
        ),
        "required_check_count": len(SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS),
        "review_evidence_count": len(_REVIEW_EVIDENCE_IDS),
        "schema_version": SOURCE_INGESTION_MAINTAINER_REVIEW_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "status": SOURCE_INGESTION_MAINTAINER_REVIEW_STATUS,
        "target_slice": SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SLICE,
        "target_surface": SOURCE_INGESTION_MAINTAINER_REVIEW_TARGET_SURFACE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceIngestionMaintainerSecurityReviewPacketError(
                f"maintainer-review packet {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_INGESTION_MAINTAINER_REVIEW_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("remaining_external_evidence"),
        SOURCE_INGESTION_MAINTAINER_REVIEW_REMAINING_EXTERNAL_EVIDENCE,
        "remaining_external_evidence",
    )
    _assert_string_sequence(
        report.get("required_checks"),
        SOURCE_INGESTION_MAINTAINER_REVIEW_REQUIRED_CHECKS,
        "required_checks",
    )
    _assert_review_evidence(report.get("review_evidence"))
    if report.get("issues") != []:
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review packet issues must be empty"
        )
    report_digest = report.get("report_digest")
    if not isinstance(report_digest, str) or not _SHA256_RE.fullmatch(report_digest):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review packet digest invalid"
        )
    if report_digest != _digest_payload(report):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review packet digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_review_item(
    spec: tuple[str, _BuildReport, _AssertContract, str, str],
) -> SourceIngestionMaintainerReviewItem:
    evidence_id, build_text, assert_contract, contract_key, status_key = spec
    text = build_text()
    _assert_text_is_source_free(text)
    payload = json.loads(text)
    assert_contract(payload)
    if not isinstance(payload, Mapping):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review payload must be object"
        )
    if _payload_id(payload, evidence_id) != evidence_id:
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review evidence id drift"
        )
    contract = payload.get(contract_key)
    status = payload.get(status_key)
    if not isinstance(contract, str) or not isinstance(status, str):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review contract/status missing"
        )
    return SourceIngestionMaintainerReviewItem(
        evidence_id=evidence_id,
        contract=contract,
        status=status,
        digest=digest_json_payload(payload),
    )


def _payload_id(payload: Mapping[str, object], expected_id: str) -> object:
    if expected_id == REAL_TRITON_FIRST_SLICE_PLAN_ID:
        return payload.get("plan_id")
    return payload.get("evidence_id") or payload.get("rfc_id")


def _assert_review_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review evidence must be list"
        )
    if len(value) != len(_REVIEW_EVIDENCE_IDS):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review evidence count drift"
        )
    observed_ids = []
    digests = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _REVIEW_ITEM_KEYS:
            raise SourceIngestionMaintainerSecurityReviewPacketError(
                "maintainer-review item keys drift"
            )
        evidence_id = item.get("evidence_id")
        contract = item.get("contract")
        status = item.get("status")
        digest = item.get("digest")
        for text_value, label in (
            (evidence_id, "evidence_id"),
            (contract, "contract"),
            (status, "status"),
        ):
            if not isinstance(text_value, str) or not _REPORT_TEXT_RE.fullmatch(
                text_value
            ):
                raise SourceIngestionMaintainerSecurityReviewPacketError(
                    f"maintainer-review item {label} invalid"
                )
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise SourceIngestionMaintainerSecurityReviewPacketError(
                "maintainer-review item digest invalid"
            )
        if item.get("reviewable") is not True or item.get("source_free") is not True:
            raise SourceIngestionMaintainerSecurityReviewPacketError(
                "maintainer-review item status drift"
            )
        observed_ids.append(evidence_id)
        digests.append(digest)
    if tuple(observed_ids) != _REVIEW_EVIDENCE_IDS:
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review evidence order drift"
        )
    if len(digests) != len(set(digests)):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review evidence digests must be unique"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            f"maintainer-review packet {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceIngestionMaintainerSecurityReviewPacketError(
            "maintainer-review expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceIngestionMaintainerSecurityReviewPacketError(
                "maintainer-review string list item invalid"
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
            raise SourceIngestionMaintainerSecurityReviewPacketError(
                f"maintainer-review packet contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
