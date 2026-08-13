"""Source-free diagnostics evidence for a future admitting parser slice.

This module turns the parser negative corpus into public diagnostic metadata.
It does not parse source into Source Intent, emit compiler artifacts, import
packages, evaluate decorators, execute JIT code, access devices, or serialize
raw source text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from tuc.frontend.parser_fuzz_negative_corpus import (
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES,
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS,
    PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT,
    PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES,
    PARSER_FUZZ_NEGATIVE_CORPUS_STATUS,
    PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE,
    ParserFuzzNegativeCorpusCase,
    ParserFuzzNegativeCorpusReport,
    build_parser_fuzz_negative_corpus_report,
    default_parser_fuzz_negative_corpus_seeds,
)

SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT = (
    "source_free_diagnostics_admission_tests.data_only.v0"
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS = "complete_non_admitting"
SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE = (
    PARSER_FUZZ_NEGATIVE_CORPUS_TARGET_SLICE
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY = "digest_only_source_free"
SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY = "message_template_id_only"
SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY = "no_source_locations"
SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY = "reason_code_digest_only"
SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME = (
    "diagnostics_source_free_before_lowering"
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS = (
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_OUTPUTS
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES = (
    PARSER_FUZZ_NEGATIVE_CORPUS_BLOCKED_EXECUTION_SURFACES
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES = (
    PARSER_FUZZ_NEGATIVE_CORPUS_REJECTION_CATEGORIES
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES = (
    "decorator_call",
    "dynamic_dispatch",
    "hardware_specific_hint",
    "import_statement",
    "line_budget",
    "report_safe_name",
    "shape_profile",
    "syntax_error",
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS = tuple(
    f"diagnostic.{reason_code}"
    for reason_code in SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES
)
SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS = (
    "parser_fuzz_negative_corpus_bound",
    "diagnostic_code_manifest",
    "message_template_id_only",
    "source_digest_only",
    "source_free_diagnostic_payload",
    "bounded_diagnostic_count",
    "bounded_diagnostic_bytes",
    "no_source_excerpt",
    "no_line_column_locations",
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

MAX_SOURCE_FREE_DIAGNOSTICS_ADMISSION_CASES = 64
MAX_SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_BYTES = 128 * 1024
MAX_SOURCE_FREE_DIAGNOSTIC_BYTES = 1024
MAX_SOURCE_FREE_DIAGNOSTIC_FIELD_BYTES = 256

_REPORT_TEXT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_DIAGNOSTIC_CODE_BY_REASON = {
    "decorator_call": "TUC_SRC_DIAG_DECORATOR_CALL",
    "dynamic_dispatch": "TUC_SRC_DIAG_DYNAMIC_DISPATCH",
    "hardware_specific_hint": "TUC_SRC_DIAG_HARDWARE_HINT",
    "import_statement": "TUC_SRC_DIAG_IMPORT_STATEMENT",
    "line_budget": "TUC_SRC_DIAG_LINE_BUDGET",
    "report_safe_name": "TUC_SRC_DIAG_REPORT_SAFE_NAME",
    "shape_profile": "TUC_SRC_DIAG_SHAPE_PROFILE",
    "syntax_error": "TUC_SRC_DIAG_SYNTAX_ERROR",
}
_FORBIDDEN_REPORT_TEXT = frozenset(
    {
        "backend_artifact_path",
        "command_line",
        "device_id",
        "dynamic_library",
        "file_path",
        "generated_code",
        "host_path",
        "line_column_location",
        "plugin_entrypoint",
        "python_source",
        "raw_source",
        "raw_source_text",
        "raw_tensor_value",
        "runtime_handle",
        "source_excerpt",
        "source_intent_payload",
        "source_text",
        "url",
    }
)


class SourceFreeDiagnosticsAdmissionError(ValueError):
    """Raised when source-free diagnostics admission evidence drifts."""


@dataclass(frozen=True)
class SourceFreeDiagnosticRecord:
    """One public source-free diagnostic derived from a negative corpus case."""

    case_id: str
    source_digest: str
    diagnostic_code: str
    diagnostic_class: str
    reason_code: str
    message_template_id: str
    expected_outcome: str
    diagnostic_bytes: int
    source_free: bool = True
    includes_source_excerpt: bool = False
    includes_source_location: bool = False
    emits_source_intent_plain_data: bool = False
    emits_compute_graph: bool = False
    emits_hac_ir: bool = False
    emits_runtime_plan: bool = False

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_digest(self.source_digest, "source_digest")
        _validate_report_text(self.diagnostic_code, "diagnostic_code")
        _validate_report_text(self.diagnostic_class, "diagnostic_class")
        _validate_report_text(self.reason_code, "reason_code")
        _validate_report_text(self.message_template_id, "message_template_id")
        _validate_report_text(self.expected_outcome, "expected_outcome")
        if self.diagnostic_class not in (
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES
        ):
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics class drift"
            )
        expected_code = _DIAGNOSTIC_CODE_BY_REASON.get(self.reason_code)
        if expected_code != self.diagnostic_code:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics code drift"
            )
        if self.message_template_id != f"diagnostic.{self.reason_code}":
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics template drift"
            )
        if self.expected_outcome != SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics outcome drift"
            )
        _validate_positive_int(self.diagnostic_bytes, "diagnostic_bytes")
        if self.diagnostic_bytes > MAX_SOURCE_FREE_DIAGNOSTIC_BYTES:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostic exceeds byte limit"
            )
        if self.source_free is not True:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostic must be source-free"
            )
        for field_name in (
            "includes_source_excerpt",
            "includes_source_location",
            "emits_source_intent_plain_data",
            "emits_compute_graph",
            "emits_hac_ir",
            "emits_runtime_plan",
        ):
            if getattr(self, field_name) is not False:
                raise SourceFreeDiagnosticsAdmissionError(
                    f"source-free diagnostic {field_name} drift"
                )


@dataclass(frozen=True)
class SourceFreeDiagnosticsAdmissionReport:
    """Data-only report proving diagnostics stay source-free."""

    diagnostics: tuple[SourceFreeDiagnosticRecord, ...]
    diagnostics_contract: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT
    diagnostics_status: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS
    target_slice: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE
    artifact_policy: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY
    message_policy: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY
    location_policy: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY
    payload_policy: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY
    expected_outcome: str = SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME
    corpus_contract: str = PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT
    corpus_status: str = PARSER_FUZZ_NEGATIVE_CORPUS_STATUS
    blocked_outputs: tuple[str, ...] = (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES
    )
    required_controls: tuple[str, ...] = (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS
    )

    def __post_init__(self) -> None:
        if self.diagnostics_contract != SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics contract drift"
            )
        if self.diagnostics_status != SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics status drift"
            )
        if self.target_slice != SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics target slice drift"
            )
        if self.artifact_policy != SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics artifact policy drift"
            )
        if self.message_policy != SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics message policy drift"
            )
        if self.location_policy != SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics location policy drift"
            )
        if self.payload_policy != SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics payload policy drift"
            )
        if self.expected_outcome != SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics expected outcome drift"
            )
        if self.corpus_contract != PARSER_FUZZ_NEGATIVE_CORPUS_CONTRACT:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics corpus contract drift"
            )
        if self.corpus_status != PARSER_FUZZ_NEGATIVE_CORPUS_STATUS:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics corpus status drift"
            )
        _validate_exact_tuple(
            self.blocked_outputs,
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS,
            "blocked_outputs",
        )
        _validate_exact_tuple(
            self.blocked_execution_surfaces,
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES,
            "blocked_execution_surfaces",
        )
        _validate_exact_tuple(
            self.required_controls,
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS,
            "required_controls",
        )
        _validate_diagnostics(self.diagnostics)

    @property
    def diagnostic_count(self) -> int:
        """Return diagnostic record count."""

        return len(self.diagnostics)

    @property
    def diagnostic_class_coverage(self) -> tuple[str, ...]:
        """Return sorted diagnostic classes covered by this report."""

        return tuple(sorted({case.diagnostic_class for case in self.diagnostics}))

    @property
    def reason_code_coverage(self) -> tuple[str, ...]:
        """Return sorted diagnostic reason codes covered by this report."""

        return tuple(sorted({case.reason_code for case in self.diagnostics}))

    @property
    def message_template_coverage(self) -> tuple[str, ...]:
        """Return sorted diagnostic message template IDs covered by this report."""

        return tuple(sorted({case.message_template_id for case in self.diagnostics}))

    @property
    def diagnostic_class_coverage_complete(self) -> bool:
        """Return whether every required diagnostic class is covered."""

        return self.diagnostic_class_coverage == (
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES
        )

    @property
    def required_reason_coverage_complete(self) -> bool:
        """Return whether every required reason code is covered."""

        return self.reason_code_coverage == (
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES
        )

    @property
    def message_template_coverage_complete(self) -> bool:
        """Return whether every message template ID is covered."""

        return self.message_template_coverage == (
            SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS
        )


def build_source_free_diagnostics_admission_report(
    corpus: ParserFuzzNegativeCorpusReport | None = None,
) -> SourceFreeDiagnosticsAdmissionReport:
    """Build the source-free diagnostics admission report."""

    selected = corpus or build_parser_fuzz_negative_corpus_report(
        default_parser_fuzz_negative_corpus_seeds()
    )
    diagnostics = tuple(
        _diagnostic_from_corpus_case(case) for case in selected.cases
    )
    return SourceFreeDiagnosticsAdmissionReport(diagnostics=diagnostics)


def source_free_diagnostics_admission_report_to_dict(
    report: SourceFreeDiagnosticsAdmissionReport,
) -> dict[str, object]:
    """Return a JSON-compatible source-free diagnostics report."""

    if not isinstance(report, SourceFreeDiagnosticsAdmissionReport):
        raise TypeError("source-free diagnostics report must be report")
    return {
        "artifact_policy": report.artifact_policy,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "blocked_outputs": list(report.blocked_outputs),
        "corpus_contract": report.corpus_contract,
        "corpus_status": report.corpus_status,
        "diagnostic_class_coverage": list(report.diagnostic_class_coverage),
        "diagnostic_class_coverage_complete": (
            report.diagnostic_class_coverage_complete
        ),
        "diagnostic_count": report.diagnostic_count,
        "diagnostics": [
            {
                "case_id": diagnostic.case_id,
                "diagnostic_bytes": diagnostic.diagnostic_bytes,
                "diagnostic_class": diagnostic.diagnostic_class,
                "diagnostic_code": diagnostic.diagnostic_code,
                "emits_compute_graph": diagnostic.emits_compute_graph,
                "emits_hac_ir": diagnostic.emits_hac_ir,
                "emits_runtime_plan": diagnostic.emits_runtime_plan,
                "emits_source_intent_plain_data": (
                    diagnostic.emits_source_intent_plain_data
                ),
                "expected_outcome": diagnostic.expected_outcome,
                "includes_source_excerpt": diagnostic.includes_source_excerpt,
                "includes_source_location": diagnostic.includes_source_location,
                "message_template_id": diagnostic.message_template_id,
                "reason_code": diagnostic.reason_code,
                "source_digest": diagnostic.source_digest,
                "source_free": diagnostic.source_free,
            }
            for diagnostic in report.diagnostics
        ],
        "diagnostics_contract": report.diagnostics_contract,
        "diagnostics_status": report.diagnostics_status,
        "expected_outcome": report.expected_outcome,
        "location_policy": report.location_policy,
        "message_policy": report.message_policy,
        "message_template_coverage": list(report.message_template_coverage),
        "message_template_coverage_complete": (
            report.message_template_coverage_complete
        ),
        "payload_policy": report.payload_policy,
        "reason_code_coverage": list(report.reason_code_coverage),
        "required_control_count": len(report.required_controls),
        "required_controls": list(report.required_controls),
        "required_reason_coverage_complete": (
            report.required_reason_coverage_complete
        ),
        "target_slice": report.target_slice,
    }


def dump_source_free_diagnostics_admission_report(
    report: SourceFreeDiagnosticsAdmissionReport,
) -> str:
    """Render stable source-free diagnostics admission evidence."""

    payload = source_free_diagnostics_admission_report_to_dict(report)
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    if len(text.encode("utf-8")) > MAX_SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_BYTES:
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics report exceeds byte limit"
        )
    return text + "\n"


def _diagnostic_from_corpus_case(
    case: ParserFuzzNegativeCorpusCase,
) -> SourceFreeDiagnosticRecord:
    reason_code = case.expected_reason_code
    diagnostic_code = _DIAGNOSTIC_CODE_BY_REASON.get(reason_code)
    if diagnostic_code is None:
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics reason code unsupported"
        )
    base_payload = {
        "case_id": case.case_id,
        "diagnostic_class": case.expected_rejection_category,
        "diagnostic_code": diagnostic_code,
        "expected_outcome": SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME,
        "message_template_id": f"diagnostic.{reason_code}",
        "reason_code": reason_code,
        "source_digest": case.source_digest,
        "source_free": True,
    }
    diagnostic_bytes = len(
        json.dumps(base_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    return SourceFreeDiagnosticRecord(
        case_id=case.case_id,
        source_digest=case.source_digest,
        diagnostic_code=diagnostic_code,
        diagnostic_class=case.expected_rejection_category,
        reason_code=reason_code,
        message_template_id=f"diagnostic.{reason_code}",
        expected_outcome=SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME,
        diagnostic_bytes=diagnostic_bytes,
    )


def _validate_diagnostics(
    diagnostics: tuple[SourceFreeDiagnosticRecord, ...],
) -> None:
    if type(diagnostics) is not tuple:
        raise TypeError("source-free diagnostics must be tuple")
    if not diagnostics:
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics must contain records"
        )
    if len(diagnostics) > MAX_SOURCE_FREE_DIAGNOSTICS_ADMISSION_CASES:
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics case count exceeds limit"
        )
    case_ids: list[str] = []
    digests: list[str] = []
    for diagnostic in diagnostics:
        if not isinstance(diagnostic, SourceFreeDiagnosticRecord):
            raise TypeError("source-free diagnostics must be diagnostic records")
        case_ids.append(diagnostic.case_id)
        digests.append(diagnostic.source_digest)
    if len(case_ids) != len(set(case_ids)):
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics case IDs must be unique"
        )
    if len(digests) != len(set(digests)):
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics source digests must be unique"
        )
    if tuple(sorted({item.diagnostic_class for item in diagnostics})) != (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES
    ):
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics class coverage incomplete"
        )
    if tuple(sorted({item.reason_code for item in diagnostics})) != (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES
    ):
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics reason coverage incomplete"
        )
    if tuple(sorted({item.message_template_id for item in diagnostics})) != (
        SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS
    ):
        raise SourceFreeDiagnosticsAdmissionError(
            "source-free diagnostics template coverage incomplete"
        )


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _REPORT_TEXT_RE.fullmatch(value):
        raise SourceFreeDiagnosticsAdmissionError(
            f"source-free diagnostics {label} must be report-safe"
        )
    if len(value.encode("utf-8")) > MAX_SOURCE_FREE_DIAGNOSTIC_FIELD_BYTES:
        raise SourceFreeDiagnosticsAdmissionError(
            f"source-free diagnostics {label} exceeds limit"
        )
    if value in _FORBIDDEN_REPORT_TEXT:
        raise SourceFreeDiagnosticsAdmissionError(
            f"source-free diagnostics {label} must be report-safe"
        )


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SourceFreeDiagnosticsAdmissionError(
            f"source-free diagnostics {label} must be sha256"
        )


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise SourceFreeDiagnosticsAdmissionError(
            f"source-free diagnostics {label} must be positive"
        )


def _validate_exact_tuple(
    values: tuple[str, ...],
    expected: tuple[str, ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"source-free diagnostics {label} must be tuple")
    if values != expected:
        raise SourceFreeDiagnosticsAdmissionError(
            f"source-free diagnostics {label} drift"
        )
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
    ):
        if fragment in lowered:
            raise SourceFreeDiagnosticsAdmissionError(
                "source-free diagnostics report contains forbidden fragment: "
                f"{fragment}"
            )


__all__ = [
    "MAX_SOURCE_FREE_DIAGNOSTIC_BYTES",
    "MAX_SOURCE_FREE_DIAGNOSTIC_FIELD_BYTES",
    "MAX_SOURCE_FREE_DIAGNOSTICS_ADMISSION_CASES",
    "MAX_SOURCE_FREE_DIAGNOSTICS_ADMISSION_REPORT_BYTES",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_ARTIFACT_POLICY",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_EXECUTION_SURFACES",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_BLOCKED_OUTPUTS",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_DIAGNOSTIC_CLASSES",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_EXPECTED_OUTCOME",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_LOCATION_POLICY",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_POLICY",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_MESSAGE_TEMPLATE_IDS",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_PAYLOAD_POLICY",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_REASON_CODES",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_REQUIRED_CONTROLS",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS",
    "SOURCE_FREE_DIAGNOSTICS_ADMISSION_TARGET_SLICE",
    "SourceFreeDiagnosticRecord",
    "SourceFreeDiagnosticsAdmissionError",
    "SourceFreeDiagnosticsAdmissionReport",
    "build_source_free_diagnostics_admission_report",
    "dump_source_free_diagnostics_admission_report",
    "source_free_diagnostics_admission_report_to_dict",
]
