"""Emit parser fuzz negative corpus evidence for the admitting slice."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from examples.source_ingestion_sandbox_implementation import (
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
    build_source_ingestion_sandbox_implementation_report,
)
from tuc.frontend.parser_fuzz_negative_corpus import (
    PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY,
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES,
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS,
    PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
    PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME,
    PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES,
    PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY,
    PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES,
    PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS,
    PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
    PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE,
    build_parser_fuzz_negative_corpus_report,
    default_parser_fuzz_negative_corpus_seeds,
    parser_fuzz_negative_corpus_report_to_dict,
)
from tuc.frontend.source_ingestion_sandbox import (
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
)

PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION = (
    "tuc.parser_fuzz_negative_corpus_for_admitting_slice_report.v0"
)
PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID = (
    "parser_fuzz_negative_corpus_for_admitting_slice"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "blocked_execution_surfaces",
        "blocked_outputs",
        "case_count",
        "cases",
        "corpus_contract",
        "corpus_status",
        "evidence_id",
        "expected_outcome",
        "issues",
        "mutation_family_coverage",
        "mutation_family_coverage_complete",
        "raw_source_policy",
        "rejection_category_coverage",
        "report_digest",
        "required_control_count",
        "required_controls",
        "required_rejection_coverage_complete",
        "sandbox_evidence",
        "schema_version",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data",
        "source_to_runtime_plan",
        "target_slice",
    }
)
_CASE_KEYS = frozenset(
    {
        "case_id",
        "expected_outcome",
        "expected_reason_code",
        "expected_rejection_category",
        "line_count",
        "mutation_family",
        "sandbox_contract",
        "sandbox_outcome",
        "sandbox_reason_code",
        "sandbox_status",
        "source_bytes",
        "source_digest",
        "source_free",
    }
)
_SANDBOX_EVIDENCE_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "source_free", "status", "supports_corpus"}
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
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_source_text":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_text":',
)


class ParserFuzzNegativeCorpusReportError(AssertionError):
    """Raised when parser fuzz negative corpus evidence drifts."""


def build_parser_fuzz_negative_corpus_for_admitting_slice_report() -> dict[str, object]:
    """Build the current source-free parser negative corpus report."""

    corpus = build_parser_fuzz_negative_corpus_report(
        default_parser_fuzz_negative_corpus_seeds()
    )
    payload = parser_fuzz_negative_corpus_report_to_dict(corpus)
    sandbox_report = build_source_ingestion_sandbox_implementation_report()
    report: dict[str, object] = {
        **payload,
        "evidence_id": PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
        "issues": [],
        "sandbox_evidence": {
            "contract": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
            "digest": _digest_payload(sandbox_report),
            "evidence_id": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
            "source_free": True,
            "status": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
            "supports_corpus": True,
        },
        "schema_version": PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
    }
    report["report_digest"] = _digest_payload(report)
    assert_parser_fuzz_negative_corpus_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the parser negative corpus."""

    return json.dumps(
        build_parser_fuzz_negative_corpus_for_admitting_slice_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_parser_fuzz_negative_corpus_report_contract(report: object) -> None:
    """Fail closed unless the parser negative corpus report matches v0."""

    if not isinstance(report, Mapping):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise ParserFuzzNegativeCorpusReportError("parser fuzz top-level keys drift")
    expected = {
        "artifact_policy": PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY,
        "case_count": len(default_parser_fuzz_negative_corpus_seeds()),
        "corpus_contract": PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
        "corpus_status": PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
        "evidence_id": PARSER_FUZZ_NEGATIVE_CORPUS_EVIDENCE_ID,
        "expected_outcome": PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME,
        "mutation_family_coverage_complete": True,
        "raw_source_policy": PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY,
        "required_control_count": len(PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS),
        "required_rejection_coverage_complete": True,
        "schema_version": PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data": False,
        "source_to_runtime_plan": False,
        "target_slice": PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ParserFuzzNegativeCorpusReportError(f"parser fuzz {key} drift")
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("blocked_outputs"),
        PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS,
        "blocked_outputs",
    )
    _assert_string_sequence(
        report.get("mutation_family_coverage"),
        PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES,
        "mutation_family_coverage",
    )
    _assert_string_sequence(
        report.get("rejection_category_coverage"),
        PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES,
        "rejection_category_coverage",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_sandbox_evidence(report.get("sandbox_evidence"))
    _assert_cases(report.get("cases"))
    if report.get("issues") != []:
        raise ParserFuzzNegativeCorpusReportError("parser fuzz issues must be empty")
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz digest invalid")
    if digest != _digest_payload(report):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_sandbox_evidence(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _SANDBOX_EVIDENCE_KEYS:
        raise ParserFuzzNegativeCorpusReportError("parser fuzz sandbox evidence keys drift")
    expected = {
        "contract": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
        "evidence_id": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_EVIDENCE_ID,
        "source_free": True,
        "status": SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
        "supports_corpus": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ParserFuzzNegativeCorpusReportError("parser fuzz sandbox evidence drift")
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz sandbox digest invalid")


def _assert_cases(value: object) -> None:
    if not isinstance(value, list):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz cases must be list")
    if len(value) != len(default_parser_fuzz_negative_corpus_seeds()):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz case count drift")
    case_ids = []
    digests = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _CASE_KEYS:
            raise ParserFuzzNegativeCorpusReportError("parser fuzz case keys drift")
        if item.get("expected_outcome") != PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME:
            raise ParserFuzzNegativeCorpusReportError("parser fuzz case outcome drift")
        if item.get("source_free") is not True:
            raise ParserFuzzNegativeCorpusReportError("parser fuzz source-free drift")
        for flag in ("case_id", "expected_reason_code", "expected_rejection_category"):
            value_text = item.get(flag)
            if not isinstance(value_text, str) or not _REPORT_TEXT_RE.fullmatch(value_text):
                raise ParserFuzzNegativeCorpusReportError("parser fuzz case text drift")
        digest = item.get("source_digest")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ParserFuzzNegativeCorpusReportError("parser fuzz source digest invalid")
        case_ids.append(item.get("case_id"))
        digests.append(digest)
    if len(case_ids) != len(set(case_ids)):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz case IDs must be unique")
    if len(digests) != len(set(digests)):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz digests must be unique")


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise ParserFuzzNegativeCorpusReportError(f"parser fuzz {field} drift")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ParserFuzzNegativeCorpusReportError("parser fuzz expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise ParserFuzzNegativeCorpusReportError("parser fuzz list item invalid")
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
            raise ParserFuzzNegativeCorpusReportError(
                f"parser fuzz report contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()