"""Data-only evidence for the next Source-to-Intent parser syntax slice.

The next slice records semantic mapping evidence for a broader parser shape:
branched tensor dataflow with multiple terminal public returns. It consumes an
already explicit research parser result and emits metadata-only review evidence
plus digests for the validated Source Intent plain-data golden.

It does not add default source ingestion, import modules, execute Triton JIT,
construct metadata, build a ComputeGraph, or lower into runtime artifacts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent import SOURCE_INTENT_IR_CONTRACT
from tuc.frontend.source_intent_intake import SOURCE_INTENT_SCHEMA_VERSION
from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchParseResult,
)

SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_next_syntax_report.v0"
)
SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT = (
    "source_to_intent_next_syntax.semantic_mapping.v0"
)
SOURCE_TO_INTENT_NEXT_SYNTAX_ARTIFACT_STATUS = "review_evidence_only"
SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE = "phase_epsilon_branched_multi_return"
SOURCE_TO_INTENT_NEXT_SYNTAX_RFC = "rfcs.0242_source_to_intent_next_syntax_slice"
SOURCE_TO_INTENT_NEXT_SYNTAX_GOLDEN_POLICY = "source_intent_plain_data_digest_bound"
SOURCE_TO_INTENT_NEXT_SYNTAX_ALLOWED_FEATURES = frozenset(
    {
        "branched_dataflow",
        "elementwise_where_to_source_intent",
        "explicit_public_return_aliases",
        "fanout_value_reuse",
        "matmul_to_source_intent",
        "multiple_terminal_stores",
        "reduction_explicit_axis_to_source_intent",
        "softmax_explicit_axis_to_source_intent",
    }
)
SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES = (
    "branched_dataflow_preserves_symbolic_dependencies",
    "direct_source_ingestion_remains_blocked",
    "multiple_stores_emit_explicit_public_returns",
    "nonterminal_return_mapping_fails_closed",
    "semantic_mapping_report_omits_raw_source",
    "source_intent_payload_validates_through_intake",
)
MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_CASES = 32
MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_FEATURES = 32
MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_BYTES = 128 * 1024
MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_FIELD_BYTES = 512

_REPORT_TEXT_RE = re.compile(r"^(sha256:[a-f0-9]{64}|[A-Za-z][A-Za-z0-9_.-]*)$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "command_line",
        "device_id",
        "dynamic_library",
        "environment",
        "file_path",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "python_source",
        "raw_source_text",
        "raw_timing_samples",
        "runtime_handle",
        "source_text",
        "url",
    }
)


@dataclass(frozen=True)
class SourceToIntentNextSyntaxCase:
    """One next-syntax semantic mapping case without raw source text."""

    case_id: str
    source_name: str
    source_digest: str
    source_bytes: int
    syntax_features: tuple[str, ...]
    operation_families: tuple[str, ...]
    tensor_count: int
    operation_count: int
    return_count: int
    source_intent_payload_digest: str

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_report_text(self.source_name, "source_name")
        _validate_sha256(self.source_digest, "source_digest")
        _validate_positive_int(self.source_bytes, "source_bytes")
        _validate_features(self.syntax_features, "syntax_features")
        unknown = set(self.syntax_features) - SOURCE_TO_INTENT_NEXT_SYNTAX_ALLOWED_FEATURES
        if unknown:
            raise ValueError("source-to-intent next syntax feature unsupported")
        _validate_features(self.operation_families, "operation_families")
        for family in self.operation_families:
            if family not in {"elementwise", "matmul", "reduction", "softmax"}:
                raise ValueError("source-to-intent next syntax operation family unsupported")
        _validate_positive_int(self.tensor_count, "tensor_count")
        _validate_positive_int(self.operation_count, "operation_count")
        _validate_positive_int(self.return_count, "return_count")
        if self.return_count < 2:
            raise ValueError("source-to-intent next syntax requires multiple returns")
        _validate_sha256(self.source_intent_payload_digest, "source_intent_payload_digest")


@dataclass(frozen=True)
class SourceToIntentNextSyntaxProperty:
    """One required property for the next-syntax semantic mapping slice."""

    property_id: str
    status: str = "satisfied"

    def __post_init__(self) -> None:
        _validate_report_text(self.property_id, "property_id")
        if self.property_id not in SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES:
            raise ValueError("source-to-intent next syntax property unsupported")
        if self.status != "satisfied":
            raise ValueError("source-to-intent next syntax property must be satisfied")


@dataclass(frozen=True)
class SourceToIntentNextSyntaxReport:
    """Review evidence for the next parser syntax slice."""

    cases: tuple[SourceToIntentNextSyntaxCase, ...]
    properties: tuple[SourceToIntentNextSyntaxProperty, ...]
    mapping_contract: str = SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT
    artifact_status: str = SOURCE_TO_INTENT_NEXT_SYNTAX_ARTIFACT_STATUS
    syntax_slice: str = SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE
    parser_rfc: str = SOURCE_TO_INTENT_NEXT_SYNTAX_RFC
    golden_policy: str = SOURCE_TO_INTENT_NEXT_SYNTAX_GOLDEN_POLICY
    parser_contract: str = SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    default_parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    parser_output_policy: str = SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    source_intent_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    source_intent_contract: str = SOURCE_INTENT_IR_CONTRACT
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.mapping_contract != SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT:
            raise ValueError("source-to-intent next syntax contract mismatch")
        if self.artifact_status != SOURCE_TO_INTENT_NEXT_SYNTAX_ARTIFACT_STATUS:
            raise ValueError("source-to-intent next syntax artifact status mismatch")
        if self.syntax_slice != SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE:
            raise ValueError("source-to-intent next syntax slice mismatch")
        if self.parser_rfc != SOURCE_TO_INTENT_NEXT_SYNTAX_RFC:
            raise ValueError("source-to-intent next syntax RFC mismatch")
        if self.golden_policy != SOURCE_TO_INTENT_NEXT_SYNTAX_GOLDEN_POLICY:
            raise ValueError("source-to-intent next syntax golden policy mismatch")
        if self.parser_contract != SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT:
            raise ValueError("source-to-intent next syntax parser contract mismatch")
        if self.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise ValueError("source-to-intent next syntax parser status mismatch")
        if self.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
            raise ValueError("source-to-intent next syntax default parser status mismatch")
        if self.parser_output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise ValueError("source-to-intent next syntax output policy mismatch")
        if self.source_intent_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise ValueError("source-to-intent next syntax source-intent schema mismatch")
        if self.source_intent_contract != SOURCE_INTENT_IR_CONTRACT:
            raise ValueError("source-to-intent next syntax source-intent contract mismatch")
        if self.blocked_compiler_outputs != (
            SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("source-to-intent next syntax blocked outputs changed")
        if self.blocked_execution_surfaces != (
            SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("source-to-intent next syntax blocked surfaces changed")
        _validate_cases(self.cases)
        _validate_properties(self.properties)

    @property
    def case_count(self) -> int:
        return len(self.cases)

    @property
    def property_count(self) -> int:
        return len(self.properties)

    @property
    def property_coverage_complete(self) -> bool:
        return tuple(item.property_id for item in self.properties) == (
            SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES
        )


def source_to_intent_next_syntax_case_from_parse_result(
    result: SourceToIntentResearchParseResult,
    *,
    case_id: str,
    syntax_features: tuple[str, ...],
) -> SourceToIntentNextSyntaxCase:
    """Create one next-syntax case from an explicit research parser result."""

    if not isinstance(result, SourceToIntentResearchParseResult):
        raise TypeError("source-to-intent next syntax requires parser result")
    payload_digest = _payload_digest(result.source_intent_payload)
    return SourceToIntentNextSyntaxCase(
        case_id=case_id,
        source_name=result.report.source_name,
        source_digest=result.report.source_digest,
        source_bytes=result.report.source_bytes,
        syntax_features=syntax_features,
        operation_families=result.report.operation_families,
        tensor_count=result.report.tensor_count,
        operation_count=result.report.operation_count,
        return_count=result.report.return_count,
        source_intent_payload_digest=payload_digest,
    )


def build_source_to_intent_next_syntax_report(
    cases: Iterable[SourceToIntentNextSyntaxCase],
    properties: tuple[SourceToIntentNextSyntaxProperty, ...] = (),
) -> SourceToIntentNextSyntaxReport:
    """Build deterministic next-syntax semantic mapping evidence."""

    selected_properties = properties or default_source_to_intent_next_syntax_properties()
    return SourceToIntentNextSyntaxReport(
        cases=tuple(cases),
        properties=selected_properties,
    )


def default_source_to_intent_next_syntax_properties() -> (
    tuple[SourceToIntentNextSyntaxProperty, ...]
):
    """Return all required next-syntax property obligations as satisfied."""

    return tuple(
        SourceToIntentNextSyntaxProperty(property_id=property_id)
        for property_id in SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES
    )


def source_to_intent_next_syntax_report_to_dict(
    report: SourceToIntentNextSyntaxReport,
) -> dict[str, object]:
    """Return stable JSON-ready next-syntax evidence."""

    if not isinstance(report, SourceToIntentNextSyntaxReport):
        raise TypeError("source-to-intent next syntax report must be report object")
    return {
        "artifact_status": report.artifact_status,
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "case_count": report.case_count,
        "cases": [
            {
                "case_id": case.case_id,
                "operation_count": case.operation_count,
                "operation_families": list(case.operation_families),
                "return_count": case.return_count,
                "source_bytes": case.source_bytes,
                "source_digest": case.source_digest,
                "source_intent_payload_digest": case.source_intent_payload_digest,
                "source_name": case.source_name,
                "syntax_features": list(case.syntax_features),
                "tensor_count": case.tensor_count,
            }
            for case in report.cases
        ],
        "default_parser_status": report.default_parser_status,
        "direct_source_ingestion": False,
        "golden_policy": report.golden_policy,
        "mapping_contract": report.mapping_contract,
        "parser_contract": report.parser_contract,
        "parser_output_policy": report.parser_output_policy,
        "parser_rfc": report.parser_rfc,
        "parser_status": report.parser_status,
        "properties": [
            {"property_id": item.property_id, "status": item.status}
            for item in report.properties
        ],
        "property_count": report.property_count,
        "property_coverage_complete": report.property_coverage_complete,
        "schema_version": SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_SCHEMA_VERSION,
        "source_intent_contract": report.source_intent_contract,
        "source_intent_schema_version": report.source_intent_schema_version,
        "syntax_slice": report.syntax_slice,
        "triton_jit_execution": False,
    }


def dump_source_to_intent_next_syntax_report(
    report: SourceToIntentNextSyntaxReport,
) -> str:
    """Render stable next-syntax semantic mapping evidence."""

    text = json.dumps(
        source_to_intent_next_syntax_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_BYTES:
        raise ValueError("source-to-intent next syntax report exceeds byte limit")
    return f"{text}\n"


def source_intent_payload_digest(payload: Mapping[str, object]) -> str:
    """Return the canonical digest used by next-syntax Source Intent goldens."""

    return _payload_digest(payload)


def _payload_digest(payload: Mapping[str, object]) -> str:
    if not isinstance(payload, Mapping):
        raise TypeError("source-to-intent next syntax payload must be a mapping")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{sha256(encoded).hexdigest()}"


def _validate_cases(cases: tuple[SourceToIntentNextSyntaxCase, ...]) -> None:
    if type(cases) is not tuple:
        raise TypeError("source-to-intent next syntax cases must be a tuple")
    if not cases:
        raise ValueError("source-to-intent next syntax report requires cases")
    if len(cases) > MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_CASES:
        raise ValueError("source-to-intent next syntax case count exceeds limit")
    case_ids: list[str] = []
    payload_digests: list[str] = []
    for case in cases:
        if not isinstance(case, SourceToIntentNextSyntaxCase):
            raise TypeError("source-to-intent next syntax cases must be case objects")
        case_ids.append(case.case_id)
        payload_digests.append(case.source_intent_payload_digest)
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("source-to-intent next syntax case IDs must be unique")
    if len(payload_digests) != len(set(payload_digests)):
        raise ValueError("source-to-intent next syntax payload digests must be unique")


def _validate_properties(
    properties: tuple[SourceToIntentNextSyntaxProperty, ...],
) -> None:
    if type(properties) is not tuple:
        raise TypeError("source-to-intent next syntax properties must be a tuple")
    if tuple(item.property_id for item in properties) != (
        SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES
    ):
        raise ValueError("source-to-intent next syntax property coverage incomplete")


def _validate_features(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"source-to-intent next syntax {label} must be a tuple")
    if len(values) > MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_FEATURES:
        raise ValueError(f"source-to-intent next syntax {label} exceeds limit")
    if tuple(sorted(values)) != values:
        raise ValueError(f"source-to-intent next syntax {label} must be sorted")
    if len(values) != len(set(values)):
        raise ValueError(f"source-to-intent next syntax {label} must be unique")
    for value in values:
        _validate_report_text(value, label)


def _validate_sha256(value: str, label: str) -> None:
    _validate_report_text(value, label)
    if not value.startswith("sha256:"):
        raise ValueError(f"source-to-intent next syntax {label} must be sha256")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"source-to-intent next syntax {label} must be positive")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ValueError(f"source-to-intent next syntax {label} must be report-safe text")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ValueError(f"source-to-intent next syntax {label} must be report-safe text")
    if len(value.encode("utf-8")) > MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_FIELD_BYTES:
        raise ValueError(f"source-to-intent next syntax {label} exceeds limit")


__all__ = [
    "MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_CASES",
    "MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_FEATURES",
    "MAX_SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_BYTES",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_ALLOWED_FEATURES",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_ARTIFACT_STATUS",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_CONTRACT",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_GOLDEN_POLICY",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_REPORT_SCHEMA_VERSION",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_REQUIRED_PROPERTIES",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_RFC",
    "SOURCE_TO_INTENT_NEXT_SYNTAX_SLICE",
    "SourceToIntentNextSyntaxCase",
    "SourceToIntentNextSyntaxProperty",
    "SourceToIntentNextSyntaxReport",
    "build_source_to_intent_next_syntax_report",
    "default_source_to_intent_next_syntax_properties",
    "dump_source_to_intent_next_syntax_report",
    "source_intent_payload_digest",
    "source_to_intent_next_syntax_case_from_parse_result",
    "source_to_intent_next_syntax_report_to_dict",
]
