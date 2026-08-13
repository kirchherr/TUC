"""Data-only corpus evidence for future Source-to-Intent parser work.

This module inventories accepted and rejected source buffers for a future
parser proposal. It does not parse source text, emit Source Intent IR, import
frontend modules, inspect Python objects, or construct compiler artifacts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

SOURCE_TO_INTENT_CORPUS_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_corpus_report.v0"
)
SOURCE_TO_INTENT_CORPUS_CONTRACT = "source_to_intent_corpus.data_only.v0"
SOURCE_TO_INTENT_CORPUS_PROPOSAL_NAME = "research-source-to-intent-parser-proposal"
SOURCE_TO_INTENT_CORPUS_CASE_EXPECTATIONS = frozenset({"accepted", "rejected"})
SOURCE_TO_INTENT_CORPUS_OPERATION_FAMILIES = frozenset(
    {"elementwise", "matmul", "reduction", "softmax"}
)
SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS = (
    "source_intent_payload",
    "source_intent_module",
    "metadata",
    "compute_graph",
    "tlir",
    "hac_ir",
    "hs_ir",
    "runtime_plan",
    "backend_decision",
)
SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES = (
    "backend_artifact_execution",
    "bytecode_compilation",
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "environment_dependent_behavior",
    "frontend_module_import",
    "generated_artifact_execution",
    "host_file_read_after_source_buffer",
    "network_access",
    "plugin_discovery",
    "python_function_inspection",
    "subprocess_execution",
    "triton_jit_execution",
)
MAX_SOURCE_TO_INTENT_CORPUS_CASES = 128
MAX_SOURCE_TO_INTENT_CORPUS_REPORT_BYTES = 128 * 1024
MAX_SOURCE_TO_INTENT_CORPUS_SOURCE_BYTES = 64 * 1024
MAX_SOURCE_TO_INTENT_CORPUS_FIELD_BYTES = 256
MAX_SOURCE_TO_INTENT_CORPUS_FEATURES = 32

_CORPUS_TEXT_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class SourceToIntentCorpusCase:
    """One source corpus case summarized without serializing source text."""

    case_id: str
    expectation: str
    source_bytes: int
    source_digest: str
    operation_families: tuple[str, ...] = ()
    expected_rejection_features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_text(self.case_id, "case_id")
        if self.expectation not in SOURCE_TO_INTENT_CORPUS_CASE_EXPECTATIONS:
            raise ValueError("source-to-intent corpus expectation unsupported")
        _validate_source_bytes(self.source_bytes)
        if not isinstance(self.source_digest, str) or not self.source_digest.startswith(
            "sha256:"
        ):
            raise ValueError("source-to-intent corpus source_digest must be sha256")
        _validate_features(self.operation_families, "operation_families")
        _validate_features(
            self.expected_rejection_features,
            "expected_rejection_features",
        )
        unknown_families = set(self.operation_families) - (
            SOURCE_TO_INTENT_CORPUS_OPERATION_FAMILIES
        )
        if unknown_families:
            raise ValueError("source-to-intent corpus operation family unsupported")
        if self.expectation == "accepted" and self.expected_rejection_features:
            raise ValueError("accepted corpus cases must not expect rejection features")
        if self.expectation == "rejected" and not self.expected_rejection_features:
            raise ValueError("rejected corpus cases must name rejection features")


@dataclass(frozen=True)
class SourceToIntentCorpusReport:
    """Data-only source corpus review report for a future parser proposal."""

    proposal_name: str
    cases: tuple[SourceToIntentCorpusCase, ...]
    corpus_contract: str = SOURCE_TO_INTENT_CORPUS_CONTRACT
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        _validate_text(self.proposal_name, "proposal_name")
        if self.corpus_contract != SOURCE_TO_INTENT_CORPUS_CONTRACT:
            raise ValueError("source-to-intent corpus contract mismatch")
        if (
            self.blocked_compiler_outputs
            != SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("source-to-intent corpus blocked compiler outputs changed")
        if (
            self.blocked_execution_surfaces
            != SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source-to-intent corpus blocked surfaces changed")
        if type(self.cases) is not tuple:
            raise TypeError("source-to-intent corpus cases must be a tuple")
        if not self.cases:
            raise ValueError("source-to-intent corpus must contain cases")
        if len(self.cases) > MAX_SOURCE_TO_INTENT_CORPUS_CASES:
            raise ValueError("source-to-intent corpus case count exceeds limit")
        case_ids: list[str] = []
        digests: list[str] = []
        for case in self.cases:
            if not isinstance(case, SourceToIntentCorpusCase):
                raise TypeError("source-to-intent corpus cases must be case objects")
            case_ids.append(case.case_id)
            digests.append(case.source_digest)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("source-to-intent corpus case IDs must be unique")
        if len(digests) != len(set(digests)):
            raise ValueError("source-to-intent corpus source digests must be unique")
        if not self.accepted_case_count:
            raise ValueError("source-to-intent corpus must contain accepted cases")
        if not self.rejected_case_count:
            raise ValueError("source-to-intent corpus must contain rejected cases")

    @property
    def accepted_case_count(self) -> int:
        """Return accepted source corpus case count."""

        return sum(1 for case in self.cases if case.expectation == "accepted")

    @property
    def rejected_case_count(self) -> int:
        """Return rejected source corpus case count."""

        return sum(1 for case in self.cases if case.expectation == "rejected")

    @property
    def operation_family_coverage(self) -> tuple[str, ...]:
        """Return sorted operation families covered by accepted cases."""

        families = {
            family
            for case in self.cases
            if case.expectation == "accepted"
            for family in case.operation_families
        }
        return tuple(sorted(families))

    @property
    def mvp_operation_family_coverage_complete(self) -> bool:
        """Return whether accepted cases cover all MVP operation families."""

        return self.operation_family_coverage == tuple(
            sorted(SOURCE_TO_INTENT_CORPUS_OPERATION_FAMILIES)
        )


def source_to_intent_corpus_case_from_source(
    *,
    case_id: str,
    expectation: str,
    source: str,
    operation_families: tuple[str, ...] = (),
    expected_rejection_features: tuple[str, ...] = (),
) -> SourceToIntentCorpusCase:
    """Build one corpus case summary without retaining source text."""

    _validate_text(case_id, "case_id")
    if not isinstance(source, str) or not source:
        raise ValueError("source-to-intent corpus source must be non-empty text")
    encoded = source.encode("utf-8")
    _validate_source_bytes(len(encoded))
    return SourceToIntentCorpusCase(
        case_id=case_id,
        expectation=expectation,
        source_bytes=len(encoded),
        source_digest=f"sha256:{sha256(encoded).hexdigest()}",
        operation_families=operation_families,
        expected_rejection_features=expected_rejection_features,
    )


def build_source_to_intent_corpus_report(
    cases: tuple[SourceToIntentCorpusCase, ...],
    *,
    proposal_name: str = SOURCE_TO_INTENT_CORPUS_PROPOSAL_NAME,
) -> SourceToIntentCorpusReport:
    """Build a deterministic source corpus report for parser research."""

    return SourceToIntentCorpusReport(
        proposal_name=proposal_name,
        cases=cases,
    )


def source_to_intent_corpus_report_to_dict(
    report: SourceToIntentCorpusReport,
) -> dict[str, object]:
    """Return a JSON-compatible Source-to-Intent corpus report."""

    if not isinstance(report, SourceToIntentCorpusReport):
        raise TypeError("source-to-intent corpus report must be report object")
    return {
        "accepted_case_count": report.accepted_case_count,
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "cases": [
            {
                "case_id": case.case_id,
                "expectation": case.expectation,
                "expected_rejection_features": list(
                    case.expected_rejection_features
                ),
                "operation_families": list(case.operation_families),
                "source_bytes": case.source_bytes,
                "source_digest": case.source_digest,
            }
            for case in report.cases
        ],
        "corpus_contract": report.corpus_contract,
        "mvp_operation_family_coverage_complete": (
            report.mvp_operation_family_coverage_complete
        ),
        "operation_family_coverage": list(report.operation_family_coverage),
        "proposal_name": report.proposal_name,
        "rejected_case_count": report.rejected_case_count,
        "schema_version": SOURCE_TO_INTENT_CORPUS_REPORT_SCHEMA_VERSION,
    }


def dump_source_to_intent_corpus_report(
    report: SourceToIntentCorpusReport,
) -> str:
    """Render stable data-only Source-to-Intent corpus evidence."""

    text = json.dumps(
        source_to_intent_corpus_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_TO_INTENT_CORPUS_REPORT_BYTES:
        raise ValueError("source-to-intent corpus report exceeds byte limit")
    return text + "\n"


def _validate_features(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"source-to-intent corpus {label} must be a tuple")
    if len(values) > MAX_SOURCE_TO_INTENT_CORPUS_FEATURES:
        raise ValueError(f"source-to-intent corpus {label} exceeds limit")
    for value in values:
        _validate_text(value, label)
    if tuple(sorted(values)) != values:
        raise ValueError(f"source-to-intent corpus {label} must be sorted")
    if len(values) != len(set(values)):
        raise ValueError(f"source-to-intent corpus {label} must be unique")


def _validate_source_bytes(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("source-to-intent corpus source bytes must be positive")
    if value > MAX_SOURCE_TO_INTENT_CORPUS_SOURCE_BYTES:
        raise ValueError("source-to-intent corpus source byte budget exceeded")


def _validate_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _CORPUS_TEXT_RE.fullmatch(value):
        raise ValueError(f"source-to-intent corpus {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_SOURCE_TO_INTENT_CORPUS_FIELD_BYTES:
        raise ValueError(f"source-to-intent corpus {label} exceeds field limit")


__all__ = [
    "MAX_SOURCE_TO_INTENT_CORPUS_CASES",
    "MAX_SOURCE_TO_INTENT_CORPUS_REPORT_BYTES",
    "MAX_SOURCE_TO_INTENT_CORPUS_SOURCE_BYTES",
    "SOURCE_TO_INTENT_CORPUS_BLOCKED_COMPILER_OUTPUTS",
    "SOURCE_TO_INTENT_CORPUS_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_TO_INTENT_CORPUS_CASE_EXPECTATIONS",
    "SOURCE_TO_INTENT_CORPUS_CONTRACT",
    "SOURCE_TO_INTENT_CORPUS_OPERATION_FAMILIES",
    "SOURCE_TO_INTENT_CORPUS_PROPOSAL_NAME",
    "SOURCE_TO_INTENT_CORPUS_REPORT_SCHEMA_VERSION",
    "SourceToIntentCorpusCase",
    "SourceToIntentCorpusReport",
    "build_source_to_intent_corpus_report",
    "dump_source_to_intent_corpus_report",
    "source_to_intent_corpus_case_from_source",
    "source_to_intent_corpus_report_to_dict",
]
