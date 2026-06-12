"""Proposal-only parser report evidence for future Source-to-Intent work.

This module defines the deterministic report shape a future parser must satisfy.
It does not parse source text, emit Source Intent IR, import frontend modules,
inspect Python objects, or construct compiler artifacts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_to_intent_corpus import (
    SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_CORPUS_CONTRACT,
    SOURCE_TO_INTENT_CORPUS_PROPOSAL_NAME,
)
from tuc.frontend.source_to_intent_property_corpus import (
    SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT,
    SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY,
    SourceToIntentPropertyCorpusReport,
    source_to_intent_property_corpus_report_to_dict,
)

SOURCE_TO_INTENT_PARSER_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_parser_report.v0"
)
SOURCE_TO_INTENT_PARSER_REPORT_CONTRACT = "source_to_intent_parser_report.proposal.v0"
SOURCE_TO_INTENT_PARSER_REPORT_STATUS = "proposal_only"
SOURCE_TO_INTENT_PARSER_OUTPUT_POLICY = "no_parser_outputs_in_proposal_report"
SOURCE_TO_INTENT_PARSER_ALLOWED_FUTURE_OUTPUT = "source_intent.v0_plain_data_only"
SOURCE_TO_INTENT_PARSER_IMPLEMENTATION_STATUS = "not_implemented"
MAX_SOURCE_TO_INTENT_PARSER_REPORT_BYTES = 128 * 1024
MAX_SOURCE_TO_INTENT_PARSER_REPORT_FIELD_BYTES = 256

_PARSER_REPORT_TEXT_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class SourceToIntentParserReport:
    """Proposal-only report for a future Source-to-Intent parser."""

    proposal_name: str
    source_corpus_contract: str
    source_corpus_digest: str
    property_corpus_contract: str
    property_corpus_digest: str
    source_corpus_case_count: int
    property_count: int
    required_property_coverage_complete: bool
    parser_enabled: bool = False
    parser_report_contract: str = SOURCE_TO_INTENT_PARSER_REPORT_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_PARSER_REPORT_STATUS
    implementation_status: str = SOURCE_TO_INTENT_PARSER_IMPLEMENTATION_STATUS
    raw_source_policy: str = SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY
    parser_output_policy: str = SOURCE_TO_INTENT_PARSER_OUTPUT_POLICY
    allowed_future_output: str = SOURCE_TO_INTENT_PARSER_ALLOWED_FUTURE_OUTPUT
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.proposal_name, "proposal_name")
        if self.source_corpus_contract != SOURCE_TO_INTENT_CORPUS_CONTRACT:
            raise ValueError("source-to-intent parser source corpus contract mismatch")
        _validate_digest(self.source_corpus_digest, "source_corpus_digest")
        if self.property_corpus_contract != SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT:
            raise ValueError("source-to-intent parser property corpus contract mismatch")
        _validate_digest(self.property_corpus_digest, "property_corpus_digest")
        _validate_positive_int(self.source_corpus_case_count, "source_corpus_case_count")
        _validate_positive_int(self.property_count, "property_count")
        if type(self.required_property_coverage_complete) is not bool:
            raise TypeError("source-to-intent parser property coverage flag must be bool")
        if not self.required_property_coverage_complete:
            raise ValueError("source-to-intent parser property coverage incomplete")
        if self.parser_enabled is not False:
            raise ValueError("source-to-intent parser report must keep parser disabled")
        if self.parser_report_contract != SOURCE_TO_INTENT_PARSER_REPORT_CONTRACT:
            raise ValueError("source-to-intent parser report contract mismatch")
        if self.parser_status != SOURCE_TO_INTENT_PARSER_REPORT_STATUS:
            raise ValueError("source-to-intent parser status must be proposal_only")
        if self.implementation_status != SOURCE_TO_INTENT_PARSER_IMPLEMENTATION_STATUS:
            raise ValueError("source-to-intent parser implementation must be absent")
        if self.raw_source_policy != SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY:
            raise ValueError("source-to-intent parser report must omit raw source")
        if self.parser_output_policy != SOURCE_TO_INTENT_PARSER_OUTPUT_POLICY:
            raise ValueError("source-to-intent parser output policy mismatch")
        if self.allowed_future_output != SOURCE_TO_INTENT_PARSER_ALLOWED_FUTURE_OUTPUT:
            raise ValueError("source-to-intent parser future output policy mismatch")
        if (
            self.blocked_compiler_outputs
            != SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("source-to-intent parser blocked compiler outputs changed")
        if (
            self.blocked_execution_surfaces
            != SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source-to-intent parser blocked surfaces changed")


def build_source_to_intent_parser_report(
    property_corpus: SourceToIntentPropertyCorpusReport,
    *,
    proposal_name: str = SOURCE_TO_INTENT_CORPUS_PROPOSAL_NAME,
) -> SourceToIntentParserReport:
    """Build a proposal-only parser report bound to property corpus evidence."""

    if not isinstance(property_corpus, SourceToIntentPropertyCorpusReport):
        raise TypeError("source-to-intent parser report requires property corpus")
    if not property_corpus.required_property_coverage_complete:
        raise ValueError("source-to-intent parser report requires property coverage")
    property_payload = json.dumps(
        source_to_intent_property_corpus_report_to_dict(property_corpus),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return SourceToIntentParserReport(
        proposal_name=proposal_name,
        source_corpus_contract=property_corpus.source_corpus_contract,
        source_corpus_digest=property_corpus.source_corpus_digest,
        property_corpus_contract=property_corpus.property_contract,
        property_corpus_digest=f"sha256:{sha256(property_payload).hexdigest()}",
        source_corpus_case_count=property_corpus.source_corpus_case_count,
        property_count=property_corpus.property_count,
        required_property_coverage_complete=(
            property_corpus.required_property_coverage_complete
        ),
    )


def source_to_intent_parser_report_to_dict(
    report: SourceToIntentParserReport,
) -> dict[str, object]:
    """Return a JSON-compatible Source-to-Intent parser report."""

    if not isinstance(report, SourceToIntentParserReport):
        raise TypeError("source-to-intent parser report must be report object")
    return {
        "allowed_future_output": report.allowed_future_output,
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "implementation_status": report.implementation_status,
        "parser_enabled": report.parser_enabled,
        "parser_output_policy": report.parser_output_policy,
        "parser_report_contract": report.parser_report_contract,
        "parser_status": report.parser_status,
        "property_corpus_contract": report.property_corpus_contract,
        "property_corpus_digest": report.property_corpus_digest,
        "property_count": report.property_count,
        "proposal_name": report.proposal_name,
        "raw_source_policy": report.raw_source_policy,
        "required_property_coverage_complete": (
            report.required_property_coverage_complete
        ),
        "schema_version": SOURCE_TO_INTENT_PARSER_REPORT_SCHEMA_VERSION,
        "source_corpus_case_count": report.source_corpus_case_count,
        "source_corpus_contract": report.source_corpus_contract,
        "source_corpus_digest": report.source_corpus_digest,
    }


def dump_source_to_intent_parser_report(report: SourceToIntentParserReport) -> str:
    """Render stable proposal-only Source-to-Intent parser evidence."""

    text = json.dumps(
        source_to_intent_parser_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_TO_INTENT_PARSER_REPORT_BYTES:
        raise ValueError("source-to-intent parser report exceeds byte limit")
    return text + "\n"


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError(f"source-to-intent parser {label} must be sha256")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"source-to-intent parser {label} must be positive")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PARSER_REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"source-to-intent parser {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_SOURCE_TO_INTENT_PARSER_REPORT_FIELD_BYTES:
        raise ValueError(f"source-to-intent parser {label} exceeds field limit")


__all__ = [
    "MAX_SOURCE_TO_INTENT_PARSER_REPORT_BYTES",
    "SOURCE_TO_INTENT_PARSER_ALLOWED_FUTURE_OUTPUT",
    "SOURCE_TO_INTENT_PARSER_IMPLEMENTATION_STATUS",
    "SOURCE_TO_INTENT_PARSER_OUTPUT_POLICY",
    "SOURCE_TO_INTENT_PARSER_REPORT_CONTRACT",
    "SOURCE_TO_INTENT_PARSER_REPORT_SCHEMA_VERSION",
    "SOURCE_TO_INTENT_PARSER_REPORT_STATUS",
    "SourceToIntentParserReport",
    "build_source_to_intent_parser_report",
    "dump_source_to_intent_parser_report",
    "source_to_intent_parser_report_to_dict",
]
