"""Emit source-free diagnostics admission evidence for the admitting slice."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.parser_fuzz_negative_corpus_for_admitting_slice import (
    PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
    build_parser_fuzz_negative_corpus_for_admitting_slice_report,
)
from tuc.frontend.parser_fuzz_negative_corpus import (
    PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
    PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
)
from tuc.frontend.source_free_diagnostics_admission import (
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE,
    build_source_free_diagnostics_admission_report,
    source_free_diagnostics_admission_report_to_dict,
)

SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION = (
    "tuc.source_free_diagnostics_admission_tests_report.v0"
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID = (
    "source_free_diagnostics_admission_tests"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "corpus_contract",
        "corpus_status",
        "diagnostic_class_coverage",
        "diagnostic_class_coverage_complete",
        "diagnostic_count",
        "diagnostics",
        "diagnostics_contract",
        "diagnostics_status",
        "evidence_id",
        "expected_outcome",
        "issues",
        "location_policy",
        "message_policy",
        "message_template_coverage",
        "message_template_coverage_complete",
        "parser_fuzz_evidence",
        "payload_policy",
        "reason_code_coverage",
        "report_digest",
        "required_control_count",
        "required_controls",
        "required_reason_coverage_complete",
        "schema_version",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
        "target_slice",
    }
)
_DIAGNOSTIC_KEYS = frozenset(
    {
        "case_id",
        "diagnostic_bytes",
        "diagnostic_class",
        "diagnostic_code",
        "emits_compute_graph",
        "emits_hac_ir",
        "emits_runtime_plan",
        "emits_source_intent_plain_data",
        "expected_outcome",
        "includes_source_excerpt",
        "includes_source_location",
        "message_template_id",
        "reason_code",
        "source_digest",
        "source_free",
    }
)
_PARSER_FUZZ_EVIDENCE_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "source_free", "status", "supports_diagnostics"}
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import os",
    "tl.dot",
    '"backend_artifact_path":',
    '"command_line":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"line_column_location":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_excerpt":',
    '"source_intent_payload":',
    '"source_text":',
)


class SourceFreeDiagnosticsAdmissionReportError(AssertionError):
    """Raised when source-free diagnostics admission evidence drifts."""


def build_source_free_diagnostics_admission_tests_report() -> dict[str, object]:
    """Build the current source-free diagnostics admission report."""

    diagnostics = build_source_free_diagnostics_admission_report()
    payload = source_free_diagnostics_admission_report_to_dict(diagnostics)
    parser_fuzz_report = build_parser_fuzz_negative_corpus_for_admitting_slice_report()
    report: dict[str, object] = {
        **payload,
        "evidence_id": SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
        "issues": [],
        "parser_fuzz_evidence": {
            "contract": PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
            "digest": _digest_payload(parser_fuzz_report),
            "evidence_id": PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
            "source_free": True,
            "status": PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
            "supports_diagnostics": True,
        },
        "schema_version": SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
    }
    report["report_digest"] = _digest_payload(report)
    assert_source_free_diagnostics_admission_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for source-free diagnostics admission."""

    return json.dumps(
        build_source_free_diagnostics_admission_tests_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_free_diagnostics_admission_report_contract(
    report: object,
) -> None:
    """Fail closed unless the source-free diagnostics report matches v0."""

    if not isinstance(report, Mapping):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics top-level keys drift"
        )
    expected = {
        "artifact_policy": SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY,
        "corpus_contract": PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
        "corpus_status": PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
        "diagnostic_class_coverage_complete": True,
        "diagnostic_count": 8,
        "diagnostics_contract": SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT,
        "diagnostics_status": SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS,
        "evidence_id": SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
        "expected_outcome": SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME,
        "location_policy": SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY,
        "message_policy": SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY,
        "message_template_coverage_complete": True,
        "payload_policy": SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY,
        "required_control_count": len(
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS
        ),
        "required_reason_coverage_complete": True,
        "schema_version": SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
        "target_slice": SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceFreeDiagnosticsAdmissionReportError(
                f"source-free diagnostics {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("blocked_outputs"),
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS,
        "blocked_outputs",
    )
    _assert_string_sequence(
        report.get("diagnostic_class_coverage"),
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES,
        "diagnostic_class_coverage",
    )
    _assert_string_sequence(
        report.get("reason_code_coverage"),
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES,
        "reason_code_coverage",
    )
    _assert_string_sequence(
        report.get("message_template_coverage"),
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS,
        "message_template_coverage",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_parser_fuzz_evidence(report.get("parser_fuzz_evidence"))
    _assert_diagnostics(report.get("diagnostics"))
    if report.get("issues") != []:
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics issues must be empty"
        )
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics digest invalid"
        )
    if digest != _digest_payload(report):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_parser_fuzz_evidence(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _PARSER_FUZZ_EVIDENCE_KEYS:
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics parser evidence keys drift"
        )
    expected = {
        "contract": PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
        "evidence_id": PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
        "source_free": True,
        "status": PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
        "supports_diagnostics": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics parser evidence drift"
            )
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics parser digest invalid"
        )


def _assert_diagnostics(value: object) -> None:
    if not isinstance(value, list):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics records must be list"
        )
    if len(value) != 8:
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics record count drift"
        )
    case_ids = []
    digests = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _DIAGNOSTIC_KEYS:
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics record keys drift"
            )
        if item.get("expected_outcome") != (
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME
        ):
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics record outcome drift"
            )
        for field_name in (
            "includes_source_excerpt",
            "includes_source_location",
            "emits_source_intent_plain_data",
            "emits_compute_graph",
            "emits_hac_ir",
            "emits_runtime_plan",
        ):
            if item.get(field_name) is not False:
                raise SourceFreeDiagnosticsAdmissionReportError(
                    f"source-free diagnostics {field_name} drift"
                )
        if item.get("source_free") is not True:
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics source flag drift"
            )
        for field_name in (
            "case_id",
            "diagnostic_class",
            "diagnostic_code",
            "message_template_id",
            "reason_code",
        ):
            value_text = item.get(field_name)
            if not isinstance(value_text, str) or not _REPORT_TEXT_RE.fullmatch(
                value_text
            ):
                raise SourceFreeDiagnosticsAdmissionReportError(
                    "source-free diagnostics record text drift"
                )
        source_digest = item.get("source_digest")
        if not isinstance(source_digest, str) or not _SHA256_RE.fullmatch(
            source_digest
        ):
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics source digest invalid"
            )
        diagnostic_bytes = item.get("diagnostic_bytes")
        if not isinstance(diagnostic_bytes, int) or diagnostic_bytes <= 0:
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics byte count invalid"
            )
        if diagnostic_bytes > 1024:
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics byte count exceeds limit"
            )
        case_ids.append(item.get("case_id"))
        digests.append(source_digest)
    if len(case_ids) != len(set(case_ids)):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics case IDs must be unique"
        )
    if len(digests) != len(set(digests)):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics digests must be unique"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceFreeDiagnosticsAdmissionReportError(
            f"source-free diagnostics {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceFreeDiagnosticsAdmissionReportError(
            "source-free diagnostics expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics list item invalid"
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
            raise SourceFreeDiagnosticsAdmissionReportError(
                "source-free diagnostics report contains forbidden fragment: "
                f"{fragment}"
            )


if __name__ == "__main__":
    main()
