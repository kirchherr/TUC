"""Property-corpus evidence for future Source-to-Intent parser work.

This module records fuzz/property obligations for a future parser proposal. It
does not parse source text, emit Source Intent IR, import frontend modules,
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
    SourceToIntentCorpusReport,
    source_to_intent_corpus_report_to_dict,
)

SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_property_corpus_report.v0"
)
SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT = (
    "source_to_intent_property_corpus.data_only.v0"
)
SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES = (
    "accepted_corpus_emits_only_source_intent_plain_data",
    "arbitrary_decoded_bytes_fail_closed",
    "diagnostics_are_bounded_and_source_free",
    "forbidden_execution_surfaces_rejected",
    "invalid_unicode_fail_closed",
    "oversized_source_budget_fail_closed",
    "rejected_corpus_never_emits_compiler_artifacts",
    "seed_combinations_fail_closed",
)
SOURCE_TO_INTENT_PROPERTY_CORPUS_CATEGORIES = frozenset(
    {
        "artifact_boundary",
        "budget_invariant",
        "diagnostic_boundary",
        "fuzz_input",
        "security_surface",
        "seed_mutation",
    }
)
MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_PROPERTIES = 64
MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_BYTES = 128 * 1024
MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_FIELD_BYTES = 256

_PROPERTY_TEXT_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class SourceToIntentPropertyRequirement:
    """One future parser property requirement."""

    property_id: str
    category: str
    expectation: str

    def __post_init__(self) -> None:
        _validate_text(self.property_id, "property_id")
        _validate_text(self.category, "category")
        _validate_text(self.expectation, "expectation")
        if self.category not in SOURCE_TO_INTENT_PROPERTY_CORPUS_CATEGORIES:
            raise ValueError("source-to-intent property category unsupported")


@dataclass(frozen=True)
class SourceToIntentPropertyCorpusReport:
    """Data-only property corpus for a future Source-to-Intent parser."""

    proposal_name: str
    source_corpus_contract: str
    source_corpus_digest: str
    source_corpus_case_count: int
    accepted_source_case_count: int
    rejected_source_case_count: int
    properties: tuple[SourceToIntentPropertyRequirement, ...]
    property_contract: str = SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT
    raw_source_policy: str = SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.proposal_name, "proposal_name")
        if self.source_corpus_contract != SOURCE_TO_INTENT_CORPUS_CONTRACT:
            raise ValueError("source-to-intent source corpus contract mismatch")
        if (
            not isinstance(self.source_corpus_digest, str)
            or not self.source_corpus_digest.startswith("sha256:")
        ):
            raise ValueError("source-to-intent property source corpus digest must be sha256")
        _validate_positive_int(self.source_corpus_case_count, "source_corpus_case_count")
        _validate_positive_int(
            self.accepted_source_case_count,
            "accepted_source_case_count",
        )
        _validate_positive_int(
            self.rejected_source_case_count,
            "rejected_source_case_count",
        )
        if self.source_corpus_case_count != (
            self.accepted_source_case_count + self.rejected_source_case_count
        ):
            raise ValueError("source-to-intent source corpus counts must add up")
        if self.property_contract != SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT:
            raise ValueError("source-to-intent property corpus contract mismatch")
        if self.raw_source_policy != SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY:
            raise ValueError("source-to-intent property corpus must omit raw source")
        if (
            self.blocked_compiler_outputs
            != SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("source-to-intent property blocked compiler outputs changed")
        if (
            self.blocked_execution_surfaces
            != SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source-to-intent property blocked surfaces changed")
        _validate_properties(self.properties)

    @property
    def property_count(self) -> int:
        """Return number of parser property requirements."""

        return len(self.properties)

    @property
    def categories(self) -> tuple[str, ...]:
        """Return sorted property categories covered by the report."""

        return tuple(sorted({item.category for item in self.properties}))

    @property
    def required_property_coverage_complete(self) -> bool:
        """Return whether every required parser property is present."""

        return tuple(item.property_id for item in self.properties) == (
            SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES
        )


def build_source_to_intent_property_corpus_report(
    source_corpus: SourceToIntentCorpusReport,
    properties: tuple[SourceToIntentPropertyRequirement, ...] = (),
    *,
    proposal_name: str = SOURCE_TO_INTENT_CORPUS_PROPOSAL_NAME,
) -> SourceToIntentPropertyCorpusReport:
    """Build a property corpus report bound to source-corpus evidence."""

    if not isinstance(source_corpus, SourceToIntentCorpusReport):
        raise TypeError("source-to-intent property corpus requires source corpus report")
    if not source_corpus.mvp_operation_family_coverage_complete:
        raise ValueError("source-to-intent source corpus MVP coverage incomplete")
    selected_properties = properties or default_source_to_intent_property_requirements()
    source_corpus_payload = json.dumps(
        source_to_intent_corpus_report_to_dict(source_corpus),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return SourceToIntentPropertyCorpusReport(
        proposal_name=proposal_name,
        source_corpus_contract=source_corpus.corpus_contract,
        source_corpus_digest=f"sha256:{sha256(source_corpus_payload).hexdigest()}",
        source_corpus_case_count=len(source_corpus.cases),
        accepted_source_case_count=source_corpus.accepted_case_count,
        rejected_source_case_count=source_corpus.rejected_case_count,
        properties=selected_properties,
    )


def default_source_to_intent_property_requirements() -> (
    tuple[SourceToIntentPropertyRequirement, ...]
):
    """Return the current parser property corpus requirements."""

    return (
        SourceToIntentPropertyRequirement(
            property_id="accepted_corpus_emits_only_source_intent_plain_data",
            category="artifact_boundary",
            expectation="accepted_source_may_emit_only_source_intent_plain_data",
        ),
        SourceToIntentPropertyRequirement(
            property_id="arbitrary_decoded_bytes_fail_closed",
            category="fuzz_input",
            expectation="arbitrary_decoded_bytes_return_bounded_rejection_or_valid_intent",
        ),
        SourceToIntentPropertyRequirement(
            property_id="diagnostics_are_bounded_and_source_free",
            category="diagnostic_boundary",
            expectation="diagnostics_omit_raw_source_and_stay_within_budget",
        ),
        SourceToIntentPropertyRequirement(
            property_id="forbidden_execution_surfaces_rejected",
            category="security_surface",
            expectation="imports_decorators_jit_devices_plugins_and_subprocesses_reject",
        ),
        SourceToIntentPropertyRequirement(
            property_id="invalid_unicode_fail_closed",
            category="fuzz_input",
            expectation="invalid_unicode_returns_bounded_rejection",
        ),
        SourceToIntentPropertyRequirement(
            property_id="oversized_source_budget_fail_closed",
            category="budget_invariant",
            expectation="source_byte_line_ast_and_diagnostic_budgets_fail_closed",
        ),
        SourceToIntentPropertyRequirement(
            property_id="rejected_corpus_never_emits_compiler_artifacts",
            category="artifact_boundary",
            expectation="rejected_source_never_emits_metadata_graph_ir_or_plan",
        ),
        SourceToIntentPropertyRequirement(
            property_id="seed_combinations_fail_closed",
            category="seed_mutation",
            expectation="seed_combinations_return_bounded_rejection_or_valid_intent",
        ),
    )


def source_to_intent_property_corpus_report_to_dict(
    report: SourceToIntentPropertyCorpusReport,
) -> dict[str, object]:
    """Return a JSON-compatible Source-to-Intent property corpus report."""

    if not isinstance(report, SourceToIntentPropertyCorpusReport):
        raise TypeError("source-to-intent property corpus report must be report object")
    return {
        "accepted_source_case_count": report.accepted_source_case_count,
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "categories": list(report.categories),
        "properties": [
            {
                "category": item.category,
                "expectation": item.expectation,
                "property_id": item.property_id,
            }
            for item in report.properties
        ],
        "property_contract": report.property_contract,
        "property_count": report.property_count,
        "proposal_name": report.proposal_name,
        "raw_source_policy": report.raw_source_policy,
        "rejected_source_case_count": report.rejected_source_case_count,
        "required_property_coverage_complete": (
            report.required_property_coverage_complete
        ),
        "schema_version": SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_SCHEMA_VERSION,
        "source_corpus_case_count": report.source_corpus_case_count,
        "source_corpus_contract": report.source_corpus_contract,
        "source_corpus_digest": report.source_corpus_digest,
    }


def dump_source_to_intent_property_corpus_report(
    report: SourceToIntentPropertyCorpusReport,
) -> str:
    """Render stable data-only Source-to-Intent property corpus evidence."""

    text = json.dumps(
        source_to_intent_property_corpus_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_BYTES:
        raise ValueError("source-to-intent property corpus report exceeds byte limit")
    return text + "\n"


def _validate_properties(
    properties: tuple[SourceToIntentPropertyRequirement, ...],
) -> None:
    if type(properties) is not tuple:
        raise TypeError("source-to-intent property corpus properties must be a tuple")
    if not properties:
        raise ValueError("source-to-intent property corpus must contain properties")
    if len(properties) > MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_PROPERTIES:
        raise ValueError("source-to-intent property corpus property count exceeds limit")
    if len(properties) != len(SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES):
        raise ValueError("source-to-intent property corpus property count mismatch")
    for item in properties:
        if not isinstance(item, SourceToIntentPropertyRequirement):
            raise TypeError("source-to-intent property entries must be requirements")
    property_ids = tuple(item.property_id for item in properties)
    if property_ids != SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES:
        raise ValueError("source-to-intent property IDs must match required corpus")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"source-to-intent property corpus {label} must be positive")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROPERTY_TEXT_RE.fullmatch(value):
        raise ValueError(
            f"source-to-intent property corpus {label} must be report-safe text"
        )
    if len(value.encode("utf-8")) > MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_FIELD_BYTES:
        raise ValueError(f"source-to-intent property corpus {label} exceeds limit")


__all__ = [
    "MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_PROPERTIES",
    "MAX_SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_BYTES",
    "SOURCE_TO_INTENT_PROPERTY_CORPUS_CATEGORIES",
    "SOURCE_TO_INTENT_PROPERTY_CORPUS_CONTRACT",
    "SOURCE_TO_INTENT_PROPERTY_CORPUS_RAW_SOURCE_POLICY",
    "SOURCE_TO_INTENT_PROPERTY_CORPUS_REPORT_SCHEMA_VERSION",
    "SOURCE_TO_INTENT_PROPERTY_CORPUS_REQUIRED_PROPERTIES",
    "SourceToIntentPropertyCorpusReport",
    "SourceToIntentPropertyRequirement",
    "build_source_to_intent_property_corpus_report",
    "default_source_to_intent_property_requirements",
    "dump_source_to_intent_property_corpus_report",
    "source_to_intent_property_corpus_report_to_dict",
]
