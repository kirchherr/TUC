"""Negative corpus evidence for the first admitting source-ingestion slice.

This module records deterministic negative/fuzz seeds as source-free metadata.
It does not parse source into Source Intent, emit compiler artifacts, import
packages, evaluate decorators, execute JIT code, access devices, or serialize
raw source text.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from tuc.frontend.source_ingestion_sandbox import (
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT,
    SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS,
    run_source_ingestion_sandbox,
    source_ingestion_sandbox_result_to_dict,
)

PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT = (
    "parser_fuzz_negative_corpus_for_admitting_slice.data_only.v0"
)
PARSER_FUZZ_NEGATIVE_CORPUS_STATUS = "complete_non_admitting"
PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE = (
    "bounded_source_buffer_to_source_intent_plain_data"
)
PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY = "digest_only_source_free"
PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY = "omitted_by_policy"
PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME = "rejected_before_lowering"
PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES = (
    "hardware_specific_source",
    "invalid_shape_profile",
    "malformed_syntax",
    "resource_budget",
    "unsafe_execution_surface",
    "unsupported_semantics",
)
PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES = (
    "ast_boundary",
    "budget_boundary",
    "hardware_hint",
    "shape_profile",
    "syntax_boundary",
    "trust_boundary",
)
PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS = (
    "deterministic_seed_manifest",
    "source_digest_only",
    "source_free_rejection_metadata",
    "bounded_source_buffer_sandbox_bound",
    "all_cases_expected_rejected",
    "fail_closed_before_lowering",
    "no_source_to_intent_plain_data",
    "no_source_to_compute_graph",
    "no_source_to_hac_ir",
    "no_source_to_runtime_plan",
    "no_python_import",
    "no_triton_jit",
    "no_device_access",
    "no_generated_artifacts",
)
PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS = (
    "backend_artifact",
    "compute_graph",
    "generated_artifact",
    "hac_ir",
    "hs_ir",
    "python_function_object",
    "runtime_plan",
    "source_intent_plain_data",
    "tlir",
)
PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES = (
    "decorator_evaluation",
    "device_access",
    "dynamic_library_loading",
    "frontend_package_import",
    "generated_artifact_execution",
    "native_backend_execution",
    "network_access",
    "plugin_discovery",
    "python_import",
    "subprocess_execution",
    "triton_jit_execution",
)
MAX_PARSER_FUZZ_NEGATIVE_CORPUS_CASES = 64
MAX_PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_BYTES = 128 * 1024
MAX_PARSER_FUZZ_NEGATIVE_CORPUS_FIELD_BYTES = 256

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
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


class ParserFuzzNegativeCorpusError(ValueError):
    """Raised when parser negative-corpus evidence drifts."""


@dataclass(frozen=True)
class ParserFuzzNegativeCorpusSeed:
    """One private negative source seed summarized by public metadata."""

    case_id: str
    source: str
    declared_shape_profile: Mapping[str, Sequence[int]]
    expected_rejection_category: str
    expected_reason_code: str
    mutation_family: str
    source_name: str | None = None

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_report_text(self.expected_rejection_category, "category")
        _validate_report_text(self.expected_reason_code, "reason_code")
        _validate_report_text(self.mutation_family, "mutation_family")
        if self.expected_rejection_category not in (
            PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES
        ):
            raise ParserFuzzNegativeCorpusError("parser fuzz category unsupported")
        if self.mutation_family not in PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES:
            raise ParserFuzzNegativeCorpusError("parser fuzz mutation unsupported")
        if not isinstance(self.source, str) or not self.source:
            raise ParserFuzzNegativeCorpusError("parser fuzz source must be text")
        if self.source_name is not None and not isinstance(self.source_name, str):
            raise ParserFuzzNegativeCorpusError("parser fuzz source_name must be text")


@dataclass(frozen=True)
class ParserFuzzNegativeCorpusCase:
    """Public source-free summary for one negative corpus seed."""

    case_id: str
    source_digest: str
    source_bytes: int
    line_count: int
    expected_rejection_category: str
    expected_reason_code: str
    expected_outcome: str
    mutation_family: str
    sandbox_contract: str
    sandbox_status: str
    sandbox_outcome: str
    sandbox_reason_code: str
    source_free: bool = True

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_digest(self.source_digest, "source_digest")
        _validate_positive_int(self.source_bytes, "source_bytes")
        _validate_positive_int(self.line_count, "line_count")
        _validate_report_text(
            self.expected_rejection_category,
            "expected_rejection_category",
        )
        _validate_report_text(self.expected_reason_code, "expected_reason_code")
        _validate_report_text(self.expected_outcome, "expected_outcome")
        _validate_report_text(self.mutation_family, "mutation_family")
        if self.expected_rejection_category not in (
            PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES
        ):
            raise ParserFuzzNegativeCorpusError("parser fuzz category drift")
        if self.expected_outcome != PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME:
            raise ParserFuzzNegativeCorpusError("parser fuzz expected outcome drift")
        if self.mutation_family not in PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES:
            raise ParserFuzzNegativeCorpusError("parser fuzz mutation drift")
        if self.sandbox_contract != SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_CONTRACT:
            raise ParserFuzzNegativeCorpusError("parser fuzz sandbox contract drift")
        if self.sandbox_status != SOURCE_INGESTION_SANDBOX_IMPLEMENTATION_STATUS:
            raise ParserFuzzNegativeCorpusError("parser fuzz sandbox status drift")
        _validate_report_text(self.sandbox_outcome, "sandbox_outcome")
        _validate_report_text(self.sandbox_reason_code, "sandbox_reason_code")
        if self.source_free is not True:
            raise ParserFuzzNegativeCorpusError("parser fuzz case must be source-free")


@dataclass(frozen=True)
class ParserFuzzNegativeCorpusReport:
    """Data-only negative corpus report for a future admitting parser slice."""

    cases: tuple[ParserFuzzNegativeCorpusCase, ...]
    corpus_contract: str = PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT
    corpus_status: str = PARSER_FUZZ_NEGATIVE_CORPUS_STATUS
    target_slice: str = PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE
    artifact_policy: str = PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY
    raw_source_policy: str = PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY
    expected_outcome: str = PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME
    blocked_outputs: tuple[str, ...] = PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS
    blocked_execution_surfaces: tuple[str, ...] = (
        PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES
    )
    required_controls: tuple[str, ...] = PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS

    def __post_init__(self) -> None:
        if self.corpus_contract != PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT:
            raise ParserFuzzNegativeCorpusError("parser fuzz contract drift")
        if self.corpus_status != PARSER_FUZZ_NEGATIVE_CORPUS_STATUS:
            raise ParserFuzzNegativeCorpusError("parser fuzz status drift")
        if self.target_slice != PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE:
            raise ParserFuzzNegativeCorpusError("parser fuzz target slice drift")
        if self.artifact_policy != PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY:
            raise ParserFuzzNegativeCorpusError("parser fuzz artifact policy drift")
        if self.raw_source_policy != PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY:
            raise ParserFuzzNegativeCorpusError("parser fuzz raw source policy drift")
        if self.expected_outcome != PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME:
            raise ParserFuzzNegativeCorpusError("parser fuzz expected outcome drift")
        _validate_exact_tuple(
            self.blocked_outputs,
            PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.required_controls,
            PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_cases(self.cases)

    @property
    def case_count(self) -> int:
        """Return negative corpus case count."""

        return len(self.cases)

    @property
    def rejection_category_coverage(self) -> tuple[str, ...]:
        """Return sorted rejection categories covered by this corpus."""

        return tuple(sorted({case.expected_rejection_category for case in self.cases}))

    @property
    def mutation_family_coverage(self) -> tuple[str, ...]:
        """Return sorted mutation families covered by this corpus."""

        return tuple(sorted({case.mutation_family for case in self.cases}))

    @property
    def required_rejection_coverage_complete(self) -> bool:
        """Return whether every required rejection category is covered."""

        return self.rejection_category_coverage == (
            PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES
        )

    @property
    def mutation_family_coverage_complete(self) -> bool:
        """Return whether every required mutation family is covered."""

        return self.mutation_family_coverage == (
            PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES
        )


def build_parser_fuzz_negative_corpus_report(
    seeds: tuple[ParserFuzzNegativeCorpusSeed, ...] = (),
) -> ParserFuzzNegativeCorpusReport:
    """Build the source-free negative corpus report."""

    selected = seeds or default_parser_fuzz_negative_corpus_seeds()
    cases = tuple(_case_from_seed(seed) for seed in selected)
    return ParserFuzzNegativeCorpusReport(cases=cases)


def parser_fuzz_negative_corpus_report_to_dict(
    report: ParserFuzzNegativeCorpusReport,
) -> dict[str, object]:
    """Return a JSON-compatible negative corpus report."""

    if not isinstance(report, ParserFuzzNegativeCorpusReport):
        raise TypeError("parser fuzz negative corpus report must be report")
    return {
        "artifact_policy": report.artifact_policy,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "case_count": report.case_count,
        "cases": [
            {
                "case_id": case.case_id,
                "expected_outcome": case.expected_outcome,
                "expected_reason_code": case.expected_reason_code,
                "expected_rejection_category": case.expected_rejection_category,
                "line_count": case.line_count,
                "mutation_family": case.mutation_family,
                "sandbox_contract": case.sandbox_contract,
                "sandbox_outcome": case.sandbox_outcome,
                "sandbox_reason_code": case.sandbox_reason_code,
                "sandbox_status": case.sandbox_status,
                "source_bytes": case.source_bytes,
                "source_digest": case.source_digest,
                "source_free": case.source_free,
            }
            for case in report.cases
        ],
        "corpus_contract": report.corpus_contract,
        "corpus_status": report.corpus_status,
        "expected_outcome": report.expected_outcome,
        "mutation_family_coverage": list(report.mutation_family_coverage),
        "mutation_family_coverage_complete": report.mutation_family_coverage_complete,
        "raw_source_policy": report.raw_source_policy,
        "rejection_category_coverage": list(report.rejection_category_coverage),
        "required_control_count": len(report.required_controls),
        "required_controls": list(report.required_controls),
        "required_rejection_coverage_complete": (
            report.required_rejection_coverage_complete
        ),
        "target_slice": report.target_slice,
    }


def dump_parser_fuzz_negative_corpus_report(
    report: ParserFuzzNegativeCorpusReport,
) -> str:
    """Render stable data-only parser negative-corpus evidence."""

    payload = parser_fuzz_negative_corpus_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_BYTES:
        raise ParserFuzzNegativeCorpusError("parser fuzz report exceeds byte limit")
    return text + "\n"


def default_parser_fuzz_negative_corpus_seeds() -> (
    tuple[ParserFuzzNegativeCorpusSeed, ...]
):
    """Return deterministic private source seeds for the negative corpus."""

    return (
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_malformed_function_syntax",
            source="def broken(:\n    pass\n",
            declared_shape_profile={"x": (1,)},
            expected_rejection_category="malformed_syntax",
            expected_reason_code="syntax_error",
            mutation_family="syntax_boundary",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_line_budget_overflow",
            source="\n".join("x = 1" for _ in range(2049)),
            declared_shape_profile={"x": (1,)},
            expected_rejection_category="resource_budget",
            expected_reason_code="line_budget",
            mutation_family="budget_boundary",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_invalid_shape_profile",
            source="x = 1\n",
            declared_shape_profile={"x": (True,)},
            expected_rejection_category="invalid_shape_profile",
            expected_reason_code="shape_profile",
            mutation_family="shape_profile",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_import_escape",
            source="import os\n\ndef kernel(x, y):\n    y = x\n",
            declared_shape_profile={"x": (8, 8), "y": (8, 8)},
            expected_rejection_category="unsafe_execution_surface",
            expected_reason_code="import_statement",
            mutation_family="trust_boundary",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_decorator_call",
            source="@triton.jit(num_warps=4)\ndef kernel(x, y):\n    y = x\n",
            declared_shape_profile={"x": (8, 8), "y": (8, 8)},
            expected_rejection_category="unsafe_execution_surface",
            expected_reason_code="decorator_call",
            mutation_family="trust_boundary",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_hardware_hint_literal",
            source='def kernel(x, y):\n    target = "cuda"\n    y = x\n',
            declared_shape_profile={"x": (8, 8), "y": (8, 8)},
            expected_rejection_category="hardware_specific_source",
            expected_reason_code="hardware_specific_hint",
            mutation_family="hardware_hint",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_dynamic_tl_dispatch",
            source="def kernel(x, y):\n    getattr(tl, 'store')(y, x)\n",
            declared_shape_profile={"x": (8, 8), "y": (8, 8)},
            expected_rejection_category="unsupported_semantics",
            expected_reason_code="dynamic_dispatch",
            mutation_family="ast_boundary",
        ),
        ParserFuzzNegativeCorpusSeed(
            case_id="reject_report_unsafe_source_name",
            source="value = 1\n",
            declared_shape_profile={"x": (1,)},
            expected_rejection_category="unsafe_execution_surface",
            expected_reason_code="report_safe_name",
            mutation_family="trust_boundary",
            source_name="../path",
        ),
    )


def _case_from_seed(seed: ParserFuzzNegativeCorpusSeed) -> (
    ParserFuzzNegativeCorpusCase
):
    source_name = seed.source_name or seed.case_id
    sandbox_result = source_ingestion_sandbox_result_to_dict(
        run_source_ingestion_sandbox(
            seed.source,
            source_name=source_name,
            declared_shape_profile=seed.declared_shape_profile,
        )
    )
    source_digest = str(sandbox_result["source_digest"])
    return ParserFuzzNegativeCorpusCase(
        case_id=seed.case_id,
        source_digest=source_digest,
        source_bytes=len(seed.source.encode("utf-8")),
        line_count=max(1, len(seed.source.splitlines())),
        expected_rejection_category=seed.expected_rejection_category,
        expected_reason_code=seed.expected_reason_code,
        expected_outcome=PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME,
        mutation_family=seed.mutation_family,
        sandbox_contract=str(sandbox_result["sandbox_contract"]),
        sandbox_status=str(sandbox_result["sandbox_status"]),
        sandbox_outcome=str(sandbox_result["outcome"]),
        sandbox_reason_code=str(sandbox_result["reason_code"]),
    )


def _validate_cases(cases: tuple[ParserFuzzNegativeCorpusCase, ...]) -> None:
    if type(cases) is not tuple:
        raise TypeError("parser fuzz cases must be tuple")
    if not cases:
        raise ParserFuzzNegativeCorpusError("parser fuzz corpus must contain cases")
    if len(cases) > MAX_PARSER_FUZZ_NEGATIVE_CORPUS_CASES:
        raise ParserFuzzNegativeCorpusError("parser fuzz case count exceeds limit")
    case_ids: list[str] = []
    digests: list[str] = []
    for case in cases:
        if not isinstance(case, ParserFuzzNegativeCorpusCase):
            raise TypeError("parser fuzz cases must be case objects")
        case_ids.append(case.case_id)
        digests.append(case.source_digest)
    if len(case_ids) != len(set(case_ids)):
        raise ParserFuzzNegativeCorpusError("parser fuzz case IDs must be unique")
    if len(digests) != len(set(digests)):
        raise ParserFuzzNegativeCorpusError("parser fuzz source digests must be unique")
    coverage = tuple(sorted({case.expected_rejection_category for case in cases}))
    if coverage != PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES:
        raise ParserFuzzNegativeCorpusError("parser fuzz category coverage incomplete")
    mutation_coverage = tuple(sorted({case.mutation_family for case in cases}))
    if mutation_coverage != PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES:
        raise ParserFuzzNegativeCorpusError("parser fuzz mutation coverage incomplete")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise ParserFuzzNegativeCorpusError(f"parser fuzz {label} must be report-safe")
    if len(value.encode("utf-8")) > MAX_PARSER_FUZZ_NEGATIVE_CORPUS_FIELD_BYTES:
        raise ParserFuzzNegativeCorpusError(f"parser fuzz {label} exceeds limit")
    if value in _FORBIDDEN_REPORT_TEXT:
        raise ParserFuzzNegativeCorpusError(f"parser fuzz {label} must be report-safe")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ParserFuzzNegativeCorpusError(f"parser fuzz {label} must be sha256")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ParserFuzzNegativeCorpusError(f"parser fuzz {label} must be positive")


def _validate_exact_tuple(values: tuple[str, ...], expected: tuple[str, ...], label: str) -> None:
    if type(values) is not tuple:
        raise TypeError(f"parser fuzz {label} must be tuple")
    if values != expected:
        raise ParserFuzzNegativeCorpusError(f"parser fuzz {label} drift")
    for value in values:
        _validate_report_text(value, label)


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in (
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
    ):
        if fragment in lowered:
            raise ParserFuzzNegativeCorpusError(
                f"parser fuzz report contains forbidden fragment: {fragment}"
            )


__all__ = [
    "MAX_PARSER_FUZZ_NEGATIVE_CORPUS_CASES",
    "MAX_PARSER_FUZZ_NEGATIVE_CORPUS_REPORT_BYTES",
    "PARSER_FUZZ_NEGATIVE_CORPUS_ARTIFACT_POLICY",
    "PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES",
    "PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS",
    "PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT",
    "PARSER_FUZZ_NEGATIVE_CORPUS_EXPECTED_OUTCOME",
    "PARSER_FUZZ_NEGATIVE_CORPUS_MUTATION_FAMILIES",
    "PARSER_FUZZ_NEGATIVE_CORPUS_RAW_SOURCE_POLICY",
    "PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES",
    "PARSER_FUZZ_NEGATIVE_CORPUS_REQUIRED_CONTROLS",
    "PARSER_FUZZ_NEGATIVE_CORPUS_STATUS",
    "PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE",
    "ParserFuzzNegativeCorpusCase",
    "ParserFuzzNegativeCorpusError",
    "ParserFuzzNegativeCorpusReport",
    "ParserFuzzNegativeCorpusSeed",
    "build_parser_fuzz_negative_corpus_report",
    "default_parser_fuzz_negative_corpus_seeds",
    "dump_parser_fuzz_negative_corpus_report",
    "parser_fuzz_negative_corpus_report_to_dict",
]
