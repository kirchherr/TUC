"""Emit CI replay evidence for the future admitted source slice."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path

from examples.bounded_source_buffer_api import (
    BOUNDED_SOURCE_BUFFER_API_EVIDENCE_ID,
    assert_bounded_source_buffer_api_report_contract,
)
from examples.bounded_source_buffer_api import (
    build_report as build_bounded_source_buffer_api_report,
)
from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
    assert_parser_fuzz_negative_corpus_report_contract,
)
from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    build_report as build_parser_fuzz_negative_corpus_report,
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
from tuc.frontend.admitted_slice_ci_replay import (
    CI_REPLAY_FOR_ADMITTED_SLICE_ADMISSION_EFFECT,
    CI_REPLAY_FOR_ADMITTED_SLICE_ARTIFACT_POLICY,
    CI_REPLAY_FOR_ADMITTED_SLICE_BLOCKED_EXECUTION_SURFACES,
    CI_REPLAY_FOR_ADMITTED_SLICE_CI_BINDING_POLICY,
    CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT,
    CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_MODE,
    CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS,
    CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS,
    CI_REPLAY_FOR_ADMITTED_SLICE_STATUS,
    CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE,
    AdmittedSliceCIReplayItem,
    admitted_slice_ci_replay_report_to_dict,
    build_admitted_slice_ci_replay_report,
    digest_text,
)

CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION = (
    "tuc.ci_replay_for_admitted_slice_report.v0"
)
CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID = "ci_replay_for_admitted_slice"
CI_REPLAY_FOR_ADMITTED_SLICE_WORKFLOW_REPLAY_STEP = (
    "python examples/ci_replay_for_admitted_slice.py"
)
CI_REPLAY_FOR_ADMITTED_SLICE_REMAINING_EXTERNAL_EVIDENCE = (
    "maintainer_security_review_approval",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_effect",
        "all_replayed",
        "artifact_policy",
        "blocked_execution_surfaces",
        "ci_binding_policy",
        "ci_checkout_credentials",
        "ci_replay_step_bound",
        "ci_workflow_digest",
        "ci_workflow_permissions",
        "contract",
        "direct_source_ingestion",
        "evidence_id",
        "issues",
        "maintainer_security_review_required",
        "remaining_external_evidence",
        "remaining_external_evidence_count",
        "replay_mode",
        "replayed_evidence",
        "replayed_evidence_count",
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
    }
)
_REPLAY_ITEM_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "replayed", "source_free", "status"}
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

_EVIDENCE_SPECS: tuple[
    tuple[str, _BuildReport, _AssertContract, str, str],
    ...,
] = (
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
)


class CIReplayForAdmittedSliceReportError(AssertionError):
    """Raised when admitted-slice CI replay evidence drifts."""


def build_ci_replay_for_admitted_slice_report() -> dict[str, object]:
    """Build the current CI replay report for the future admitted slice."""

    workflow_text = _read_ci_workflow_text()
    replayed_evidence = tuple(_build_replay_item(spec) for spec in _EVIDENCE_SPECS)
    base_report = build_admitted_slice_ci_replay_report(
        replayed_evidence,
        ci_workflow_digest=digest_text(workflow_text),
        ci_workflow_permissions=_ci_workflow_permissions(workflow_text),
        ci_checkout_credentials=_ci_checkout_credentials(workflow_text),
        ci_replay_step_bound=_ci_replay_step_bound(workflow_text),
    )
    payload = admitted_slice_ci_replay_report_to_dict(base_report)
    report: dict[str, object] = {
        **payload,
        "evidence_id": CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID,
        "issues": [],
        "maintainer_security_review_required": True,
        "remaining_external_evidence": list(
            CI_REPLAY_FOR_ADMITTED_SLICE_REMAINING_EXTERNAL_EVIDENCE
        ),
        "remaining_external_evidence_count": len(
            CI_REPLAY_FOR_ADMITTED_SLICE_REMAINING_EXTERNAL_EVIDENCE
        ),
        "schema_version": CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
    }
    report["report_digest"] = _digest_payload(report)
    assert_ci_replay_for_admitted_slice_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for admitted-slice CI replay."""

    return json.dumps(
        build_ci_replay_for_admitted_slice_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_ci_replay_for_admitted_slice_report_contract(report: object) -> None:
    """Fail closed unless admitted-slice CI replay matches v0."""

    if not isinstance(report, Mapping):
        raise CIReplayForAdmittedSliceReportError("CI replay report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise CIReplayForAdmittedSliceReportError("CI replay top-level keys drift")
    expected = {
        "admission_effect": CI_REPLAY_FOR_ADMITTED_SLICE_ADMISSION_EFFECT,
        "all_replayed": True,
        "artifact_policy": CI_REPLAY_FOR_ADMITTED_SLICE_ARTIFACT_POLICY,
        "ci_binding_policy": CI_REPLAY_FOR_ADMITTED_SLICE_CI_BINDING_POLICY,
        "ci_checkout_credentials": "persist_credentials_false",
        "ci_replay_step_bound": True,
        "ci_workflow_permissions": "contents_read",
        "contract": CI_REPLAY_FOR_ADMITTED_SLICE_CONTRACT,
        "direct_source_ingestion": False,
        "evidence_id": CI_REPLAY_FOR_ADMITTED_SLICE_EVIDENCE_ID,
        "maintainer_security_review_required": True,
        "remaining_external_evidence_count": 1,
        "replay_mode": CI_REPLAY_FOR_ADMITTED_SLICE_REPLAY_MODE,
        "replayed_evidence_count": len(
            CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS
        ),
        "required_control_count": len(CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS),
        "schema_version": CI_REPLAY_FOR_ADMITTED_SLICE_REPORT_SCHEMA_VERSION,
        "source_ingestion_admission_ready": False,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_runtime_plan": False,
        "status": CI_REPLAY_FOR_ADMITTED_SLICE_STATUS,
        "target_slice": CI_REPLAY_FOR_ADMITTED_SLICE_TARGET_SLICE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise CIReplayForAdmittedSliceReportError(f"CI replay {key} drift")
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        CI_REPLAY_FOR_ADMITTED_SLICE_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("remaining_external_evidence"),
        CI_REPLAY_FOR_ADMITTED_SLICE_REMAINING_EXTERNAL_EVIDENCE,
        "remaining_external_evidence",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        CI_REPLAY_FOR_ADMITTED_SLICE_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_replayed_evidence(report.get("replayed_evidence"))
    if report.get("issues") != []:
        raise CIReplayForAdmittedSliceReportError("CI replay issues must be empty")
    for digest_key in ("ci_workflow_digest", "report_digest"):
        digest = report.get(digest_key)
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise CIReplayForAdmittedSliceReportError(
                f"CI replay {digest_key} invalid"
            )
    if report.get("report_digest") != _digest_payload(report):
        raise CIReplayForAdmittedSliceReportError("CI replay digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_replay_item(
    spec: tuple[str, _BuildReport, _AssertContract, str, str],
) -> AdmittedSliceCIReplayItem:
    evidence_id, build_text, assert_contract, contract_key, status_key = spec
    text = build_text()
    _assert_text_is_source_free(text)
    payload = json.loads(text)
    assert_contract(payload)
    if not isinstance(payload, Mapping):
        raise CIReplayForAdmittedSliceReportError("CI replay payload must be object")
    if payload.get("evidence_id") != evidence_id:
        raise CIReplayForAdmittedSliceReportError("CI replay evidence id drift")
    contract = payload.get(contract_key)
    status = payload.get(status_key)
    if not isinstance(contract, str) or not isinstance(status, str):
        raise CIReplayForAdmittedSliceReportError("CI replay contract/status missing")
    return AdmittedSliceCIReplayItem(
        evidence_id=evidence_id,
        contract=contract,
        status=status,
        digest=_digest_payload(payload),
        source_free=True,
    )


def _read_ci_workflow_text() -> str:
    return Path(".github/workflows/ci.yml").read_text(encoding="utf-8")


def _ci_workflow_permissions(text: str) -> str:
    if "permissions:\n  contents: read\n" not in text:
        raise CIReplayForAdmittedSliceReportError("CI replay workflow permissions drift")
    return "contents_read"


def _ci_checkout_credentials(text: str) -> str:
    if "persist-credentials: false" not in text:
        raise CIReplayForAdmittedSliceReportError(
            "CI replay checkout credentials drift"
        )
    return "persist_credentials_false"


def _ci_replay_step_bound(text: str) -> bool:
    if CI_REPLAY_FOR_ADMITTED_SLICE_WORKFLOW_REPLAY_STEP not in text:
        raise CIReplayForAdmittedSliceReportError("CI replay workflow step drift")
    return True


def _assert_replayed_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise CIReplayForAdmittedSliceReportError(
            "CI replay evidence must be list"
        )
    if len(value) != len(CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS):
        raise CIReplayForAdmittedSliceReportError(
            "CI replay evidence count drift"
        )
    observed_ids = []
    digests = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _REPLAY_ITEM_KEYS:
            raise CIReplayForAdmittedSliceReportError("CI replay item keys drift")
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
                raise CIReplayForAdmittedSliceReportError(
                    f"CI replay item {label} invalid"
                )
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise CIReplayForAdmittedSliceReportError("CI replay item digest invalid")
        if item.get("replayed") is not True or item.get("source_free") is not True:
            raise CIReplayForAdmittedSliceReportError("CI replay item status drift")
        observed_ids.append(evidence_id)
        digests.append(digest)
    if tuple(observed_ids) != CI_REPLAY_FOR_ADMITTED_SLICE_REPLAYED_EVIDENCE_IDS:
        raise CIReplayForAdmittedSliceReportError("CI replay evidence order drift")
    if len(digests) != len(set(digests)):
        raise CIReplayForAdmittedSliceReportError(
            "CI replay evidence digests must be unique"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise CIReplayForAdmittedSliceReportError(f"CI replay {field} drift")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise CIReplayForAdmittedSliceReportError("CI replay expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise CIReplayForAdmittedSliceReportError(
                "CI replay string list item invalid"
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
            raise CIReplayForAdmittedSliceReportError(
                f"CI replay contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
