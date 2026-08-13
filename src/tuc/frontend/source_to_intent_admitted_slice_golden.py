"""Plain-data output golden evidence for a future admitting source slice.

This module records what a future admitting source-to-Intent slice may emit:
validated `source_intent.v0` plain data only. It consumes explicit research
parser results as data, revalidates their plain-data output through Source
Intent Intake, and emits digest-only report evidence.

It does not admit direct source ingestion, parse source text itself, lower into
metadata, build a graph, produce HAC-IR, produce a runtime plan, execute code,
or serialize raw source text.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_intent import SOURCE_INTENT_IR_CONTRACT
from tuc.frontend.source_intent_intake import (
    SOURCE_INTENT_SCHEMA_VERSION,
    source_intent_from_mapping,
)
from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchParseResult,
)

SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT = (
    "source_to_intent_plain_data_output_golden_for_admitted_slice.data_only.v0"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS = "complete_non_admitting"
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ARTIFACT_POLICY = (
    "digest_only_report_with_reviewable_plain_data_golden"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OUTPUT_POLICY = (
    "source_intent.v0_plain_data_only"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ADMISSION_EFFECT = (
    "does_not_admit_direct_source_ingestion"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_RAW_SOURCE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION = (
    "tuc.source_to_intent_plain_data_output_golden_for_admitted_slice_plain_data.v0"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS = (
    "bounded_source_buffer_api_bound",
    "source_ingestion_sandbox_implementation_bound",
    "parser_fuzz_negative_corpus_bound",
    "source_free_diagnostics_admission_tests_bound",
    "source_intent_plain_data_validates_through_intake",
    "source_intent_plain_data_digest_bound",
    "source_intent_plain_data_only",
    "reviewable_plain_data_golden",
    "raw_source_omitted",
    "direct_source_ingestion_remains_blocked",
    "no_source_to_compute_graph",
    "no_source_to_hac_ir",
    "no_source_to_runtime_plan",
    "no_python_import",
    "no_triton_jit",
    "no_device_access",
    "no_generated_artifacts",
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_COMPILER_OUTPUTS = (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_EXECUTION_SURFACES = (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_EXECUTION_SURFACES
)

MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CASES = 16
MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_BYTES = 128 * 1024
MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_FIELD_BYTES = 512

_REPORT_TEXT_RE = re.compile(r"^(sha256:[a-f0-9]{64}|[A-Za-z][A-Za-z0-9_.:-]*)$")
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact",
        "backend_artifact_path",
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


class SourceToIntentAdmittedSliceGoldenError(ValueError):
    """Raised when admitted-slice Source Intent golden evidence drifts."""


@dataclass(frozen=True)
class SourceToIntentPlainDataGoldenCase:
    """One Source Intent plain-data golden summarized without raw source."""

    case_id: str
    source_name: str
    source_digest: str
    source_bytes: int
    line_count: int
    plain_data_digest: str
    tensor_count: int
    operation_count: int
    return_count: int
    operation_families: tuple[str, ...]
    public_returns: tuple[str, ...]
    source_intent_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    source_intent_contract: str = SOURCE_INTENT_IR_CONTRACT
    parser_contract: str = SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    default_parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    parser_output_policy: str = SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_report_text(self.source_name, "source_name")
        _validate_digest(self.source_digest, "source_digest")
        _validate_positive_int(self.source_bytes, "source_bytes")
        _validate_positive_int(self.line_count, "line_count")
        _validate_digest(self.plain_data_digest, "plain_data_digest")
        _validate_positive_int(self.tensor_count, "tensor_count")
        _validate_positive_int(self.operation_count, "operation_count")
        _validate_positive_int(self.return_count, "return_count")
        if self.source_intent_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden source-intent schema drift"
            )
        if self.source_intent_contract != SOURCE_INTENT_IR_CONTRACT:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden source-intent contract drift"
            )
        if self.parser_contract != SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden parser contract drift"
            )
        if self.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden parser status drift"
            )
        if self.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden default parser status drift"
            )
        if self.parser_output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden output policy drift"
            )
        _validate_text_tuple(self.operation_families, "operation_families")
        _validate_text_tuple(self.public_returns, "public_returns")
        for family in self.operation_families:
            if family not in SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES:
                raise SourceToIntentAdmittedSliceGoldenError(
                    "admitted-slice golden operation family unsupported"
                )


@dataclass(frozen=True)
class SourceToIntentAdmittedSliceGoldenReport:
    """Digest-only report binding reviewable Source Intent plain-data goldens."""

    cases: tuple[SourceToIntentPlainDataGoldenCase, ...]
    golden_contract: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT
    golden_status: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS
    target_slice: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_TARGET_SLICE
    artifact_policy: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ARTIFACT_POLICY
    output_policy: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OUTPUT_POLICY
    admission_effect: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ADMISSION_EFFECT
    raw_source_policy: str = SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_RAW_SOURCE_POLICY
    plain_data_schema_version: str = (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION
    )
    source_intent_schema_version: str = SOURCE_INTENT_SCHEMA_VERSION
    source_intent_contract: str = SOURCE_INTENT_IR_CONTRACT
    required_controls: tuple[str, ...] = (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS
    )
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.golden_contract != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden contract drift"
            )
        if self.golden_status != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden status drift"
            )
        if self.target_slice != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_TARGET_SLICE:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden target slice drift"
            )
        if self.artifact_policy != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ARTIFACT_POLICY:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden artifact policy drift"
            )
        if self.output_policy != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OUTPUT_POLICY:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden output policy drift"
            )
        if self.admission_effect != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ADMISSION_EFFECT:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden admission effect drift"
            )
        if self.raw_source_policy != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_RAW_SOURCE_POLICY:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden raw source policy drift"
            )
        if self.plain_data_schema_version != (
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION
        ):
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden plain-data schema drift"
            )
        if self.source_intent_schema_version != SOURCE_INTENT_SCHEMA_VERSION:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden source-intent schema drift"
            )
        if self.source_intent_contract != SOURCE_INTENT_IR_CONTRACT:
            raise SourceToIntentAdmittedSliceGoldenError(
                "admitted-slice golden source-intent contract drift"
            )
        _validate_exact_tuple(
            self.required_controls,
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_exact_tuple(
            self.blocked_compiler_outputs,
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_COMPILER_OUTPUTS,
            "blocked_compiler_outputs",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_cases(self.cases)

    @property
    def case_count(self) -> int:
        """Return golden case count."""

        return len(self.cases)

    @property
    def operation_family_coverage(self) -> tuple[str, ...]:
        """Return sorted operation-family coverage."""

        return tuple(sorted({family for case in self.cases for family in case.operation_families}))

    @property
    def operation_family_coverage_complete(self) -> bool:
        """Return whether the current admitted-slice golden covers MVP families."""

        return self.operation_family_coverage == (
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES
        )


def source_to_intent_plain_data_golden_case_from_parse_result(
    result: SourceToIntentResearchParseResult,
    *,
    case_id: str,
) -> SourceToIntentPlainDataGoldenCase:
    """Create one admitted-slice golden case from a research parser result."""

    if not isinstance(result, SourceToIntentResearchParseResult):
        raise TypeError("admitted-slice golden requires parser result")
    module = source_intent_from_mapping(dict(result.source_intent_payload))
    public_returns = tuple(source_return.public_name for source_return in module.returns)
    return SourceToIntentPlainDataGoldenCase(
        case_id=case_id,
        source_name=result.report.source_name,
        source_digest=result.report.source_digest,
        source_bytes=result.report.source_bytes,
        line_count=result.report.line_count,
        plain_data_digest=source_intent_plain_data_digest(result.source_intent_payload),
        tensor_count=len(module.tensors),
        operation_count=len(module.operations),
        return_count=len(module.returns),
        operation_families=result.report.operation_families,
        public_returns=public_returns,
    )


def build_source_to_intent_admitted_slice_golden_report(
    cases: Iterable[SourceToIntentPlainDataGoldenCase],
) -> SourceToIntentAdmittedSliceGoldenReport:
    """Build digest-only admitted-slice Source Intent plain-data golden evidence."""

    return SourceToIntentAdmittedSliceGoldenReport(cases=tuple(cases))


def source_to_intent_admitted_slice_golden_report_to_dict(
    report: SourceToIntentAdmittedSliceGoldenReport,
) -> dict[str, object]:
    """Return stable JSON-ready admitted-slice golden evidence."""

    if not isinstance(report, SourceToIntentAdmittedSliceGoldenReport):
        raise TypeError("admitted-slice golden report must be report object")
    return {
        "admission_effect": report.admission_effect,
        "artifact_policy": report.artifact_policy,
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "case_count": report.case_count,
        "cases": [
            {
                "case_id": case.case_id,
                "default_parser_status": case.default_parser_status,
                "line_count": case.line_count,
                "operation_count": case.operation_count,
                "operation_families": list(case.operation_families),
                "parser_contract": case.parser_contract,
                "parser_output_policy": case.parser_output_policy,
                "parser_status": case.parser_status,
                "plain_data_digest": case.plain_data_digest,
                "public_returns": list(case.public_returns),
                "return_count": case.return_count,
                "source_bytes": case.source_bytes,
                "source_digest": case.source_digest,
                "source_intent_contract": case.source_intent_contract,
                "source_intent_schema_version": case.source_intent_schema_version,
                "source_name": case.source_name,
                "tensor_count": case.tensor_count,
            }
            for case in report.cases
        ],
        "direct_source_ingestion": False,
        "golden_contract": report.golden_contract,
        "golden_status": report.golden_status,
        "operation_family_coverage": list(report.operation_family_coverage),
        "operation_family_coverage_complete": report.operation_family_coverage_complete,
        "output_policy": report.output_policy,
        "plain_data_schema_version": report.plain_data_schema_version,
        "raw_source_policy": report.raw_source_policy,
        "required_control_count": len(report.required_controls),
        "required_controls": list(report.required_controls),
        "source_intent_contract": report.source_intent_contract,
        "source_intent_schema_version": report.source_intent_schema_version,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data_output_golden": True,
        "source_to_runtime_plan": False,
        "target_slice": report.target_slice,
    }


def build_source_intent_plain_data_golden_payload(
    cases: Iterable[tuple[str, str, Mapping[str, object]]],
) -> dict[str, object]:
    """Build the reviewable Source Intent plain-data golden payload."""

    golden_cases = []
    for case_id, source_name, plain_data in cases:
        _validate_report_text(case_id, "case_id")
        _validate_report_text(source_name, "source_name")
        module = source_intent_from_mapping(dict(plain_data))
        golden_cases.append(
            {
                "case_id": case_id,
                "plain_data_digest": source_intent_plain_data_digest(plain_data),
                "source_intent_plain_data": plain_data,
                "source_name": source_name,
                "tensor_count": len(module.tensors),
                "operation_count": len(module.operations),
                "return_count": len(module.returns),
            }
        )
    if not golden_cases:
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice plain-data golden requires cases"
        )
    return {
        "case_count": len(golden_cases),
        "cases": golden_cases,
        "plain_data_schema_version": (
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION
        ),
    }


def dump_source_to_intent_admitted_slice_golden_report(
    report: SourceToIntentAdmittedSliceGoldenReport,
) -> str:
    """Render stable admitted-slice golden report evidence."""

    payload = source_to_intent_admitted_slice_golden_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_BYTES:
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice golden report exceeds byte limit"
        )
    return text + "\n"


def source_intent_plain_data_digest(payload: Mapping[str, object]) -> str:
    """Return canonical digest for Source Intent plain-data goldens."""

    if not isinstance(payload, Mapping):
        raise TypeError("Source Intent plain-data golden payload must be mapping")
    source_intent_from_mapping(dict(payload))
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    _assert_text_is_source_free(text)
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _validate_cases(cases: tuple[SourceToIntentPlainDataGoldenCase, ...]) -> None:
    if type(cases) is not tuple:
        raise TypeError("admitted-slice golden cases must be tuple")
    if not cases:
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice golden requires cases"
        )
    if len(cases) > MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CASES:
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice golden case count exceeds limit"
        )
    case_ids: list[str] = []
    digests: list[str] = []
    for case in cases:
        if not isinstance(case, SourceToIntentPlainDataGoldenCase):
            raise TypeError("admitted-slice golden cases must be case objects")
        case_ids.append(case.case_id)
        digests.append(case.plain_data_digest)
    if len(case_ids) != len(set(case_ids)):
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice golden case IDs must be unique"
        )
    if len(digests) != len(set(digests)):
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice golden plain-data digests must be unique"
        )
    families = tuple(sorted({family for case in cases for family in case.operation_families}))
    if families != SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES:
        raise SourceToIntentAdmittedSliceGoldenError(
            "admitted-slice golden operation family coverage incomplete"
        )


def _validate_text_tuple(values: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"admitted-slice golden {label} must be tuple")
    if not values:
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must not be empty"
        )
    if tuple(sorted(values)) != values:
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must be sorted"
        )
    if len(values) != len(set(values)):
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must be unique"
        )
    for value in values:
        _validate_report_text(value, label)


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"admitted-slice golden {label} must be tuple")
    if values != expected:
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} drift"
        )
    for value in values:
        _validate_report_text(value, label)


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must be report-safe"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must be report-safe"
        )
    if len(value.encode("utf-8")) > MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_FIELD_BYTES:
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} exceeds limit"
        )


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must be sha256"
        )


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SourceToIntentAdmittedSliceGoldenError(
            f"admitted-slice golden {label} must be positive"
        )


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in (
        "@triton.jit",
        "import os",
        "tl.dot",
        "tl.store",
        '"backend_artifact":',
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
        '"source_intent_payload":',
        '"source_text":',
    ):
        if fragment in lowered:
            raise SourceToIntentAdmittedSliceGoldenError(
                f"admitted-slice golden contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CASES",
    "MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_FIELD_BYTES",
    "MAX_SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_BYTES",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ADMISSION_EFFECT",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ARTIFACT_POLICY",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_COMPILER_OUTPUTS",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OUTPUT_POLICY",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_RAW_SOURCE_POLICY",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS",
    "SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_TARGET_SLICE",
    "SourceToIntentAdmittedSliceGoldenError",
    "SourceToIntentAdmittedSliceGoldenReport",
    "SourceToIntentPlainDataGoldenCase",
    "build_source_intent_plain_data_golden_payload",
    "build_source_to_intent_admitted_slice_golden_report",
    "dump_source_to_intent_admitted_slice_golden_report",
    "source_intent_plain_data_digest",
    "source_to_intent_admitted_slice_golden_report_to_dict",
    "source_to_intent_plain_data_golden_case_from_parse_result",
]
