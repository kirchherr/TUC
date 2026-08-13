"""Source-free diagnostics for Source-To-Intent Research Kernel Ingress."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from tuc.frontend.source_to_intent_research_kernel_ingress import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SourceToIntentResearchKernelIngressError,
    ingest_triton_module_source_to_source_intent,
    source_to_intent_research_kernel_ingress_report_to_dict,
)
from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_diagnostics_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT = (
    "source_to_intent_research_kernel_ingress_diagnostics.execution_free.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASE_EXPECTATIONS = frozenset(
    {"accepted", "rejected"}
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS = {
    "decorator_call": "forbids decorator calls",
    "import_after_kernel_function": "requires import prelude before kernel function",
    "import_from_statement": "forbids import-from statements",
    "kernel_name_mismatch": "target kernel name mismatch",
    "missing_triton_jit_decorator": "requires one @triton.jit decorator",
    "multiple_kernel_functions": "exactly one top-level kernel function",
    "preflight_annotation": "annotation",
    "top_level_side_effect": "supports only imports and one kernel function",
    "unsupported_decorator": "requires @triton.jit decorator data",
    "unsupported_import": "supports only import triton",
}
MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASES = 32
MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_FIELD_BYTES = 256
MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_MODULE_BYTES = 64 * 1024
MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_BYTES = 128 * 1024

_DIAGNOSTIC_TEXT_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourceToIntentResearchKernelIngressDiagnosticCase:
    """One module-source diagnostic input case."""

    case_id: str
    expectation: str
    module_source: str
    source_name: str
    kernel_name: str
    tensor_shapes: Mapping[str, Sequence[int]]
    expected_rejection_reason: str = ""

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_identifier(self.source_name, "source_name")
        _validate_identifier(self.kernel_name, "kernel_name")
        if (
            self.expectation
            not in SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASE_EXPECTATIONS
        ):
            raise ValueError("kernel ingress diagnostic expectation unsupported")
        if not isinstance(self.module_source, str) or not self.module_source:
            raise ValueError("kernel ingress diagnostic module source must be text")
        if (
            len(self.module_source.encode("utf-8"))
            > MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_MODULE_BYTES
        ):
            raise ValueError("kernel ingress diagnostic module source exceeds budget")
        if not isinstance(self.tensor_shapes, Mapping):
            raise TypeError("kernel ingress diagnostic shapes must be a mapping")
        if self.expectation == "accepted" and self.expected_rejection_reason:
            raise ValueError("accepted kernel ingress diagnostic must not reject")
        if self.expectation == "rejected":
            if not self.expected_rejection_reason:
                raise ValueError("rejected kernel ingress diagnostic needs reason")
            if (
                self.expected_rejection_reason
                not in SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
            ):
                raise ValueError("kernel ingress diagnostic rejection reason unsupported")


@dataclass(frozen=True)
class SourceToIntentResearchKernelIngressDiagnosticResult:
    """One source-free kernel ingress diagnostic outcome."""

    case_id: str
    expectation: str
    outcome: str
    source_name: str
    kernel_name: str
    module_bytes: int
    module_digest: str
    operation_families: tuple[str, ...] = ()
    ingress_report_digest: str = ""
    rejection_reason: str = ""

    def __post_init__(self) -> None:
        _validate_report_text(self.case_id, "case_id")
        _validate_identifier(self.source_name, "source_name")
        _validate_identifier(self.kernel_name, "kernel_name")
        if (
            self.expectation
            not in SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASE_EXPECTATIONS
        ):
            raise ValueError("kernel ingress diagnostic expectation unsupported")
        if (
            self.outcome
            not in SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASE_EXPECTATIONS
        ):
            raise ValueError("kernel ingress diagnostic outcome unsupported")
        if self.expectation != self.outcome:
            raise ValueError("kernel ingress diagnostic outcome mismatch")
        _validate_positive_int(self.module_bytes, "module_bytes")
        _validate_digest(self.module_digest, "module_digest")
        _validate_operation_families(self.operation_families)
        if self.outcome == "accepted":
            _validate_digest(self.ingress_report_digest, "ingress_report_digest")
            if self.rejection_reason:
                raise ValueError("accepted kernel ingress result must not reject")
        else:
            if self.ingress_report_digest:
                raise ValueError("rejected kernel ingress result must not carry digest")
            if (
                self.rejection_reason
                not in SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
            ):
                raise ValueError("kernel ingress diagnostic rejection reason unsupported")


@dataclass(frozen=True)
class SourceToIntentResearchKernelIngressDiagnosticsReport:
    """Source-free diagnostics for the explicit kernel ingress."""

    cases: tuple[SourceToIntentResearchKernelIngressDiagnosticResult, ...]
    diagnostics_contract: str = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
    )
    ingress_contract: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT
    parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS
    default_parser_status: str = SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
    input_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY
    output_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY
    parser_output_policy: str = SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY
    raw_source_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY
    raw_value_policy: str = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY
    blocked_claims: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS
    )
    blocked_compiler_outputs: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
    )
    blocked_execution_surfaces: tuple[str, ...] = (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
    )

    def __post_init__(self) -> None:
        if self.diagnostics_contract != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ):
            raise ValueError("kernel ingress diagnostics contract mismatch")
        if self.ingress_contract != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT:
            raise ValueError("kernel ingress diagnostics ingress contract mismatch")
        if self.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise ValueError("kernel ingress diagnostics parser status mismatch")
        if self.default_parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS:
            raise ValueError("kernel ingress diagnostics default parser status mismatch")
        if self.input_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY:
            raise ValueError("kernel ingress diagnostics input policy mismatch")
        if self.output_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY:
            raise ValueError("kernel ingress diagnostics output policy mismatch")
        if self.parser_output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise ValueError("kernel ingress diagnostics parser output policy mismatch")
        if self.raw_source_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY:
            raise ValueError("kernel ingress diagnostics source policy mismatch")
        if self.raw_value_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY:
            raise ValueError("kernel ingress diagnostics value policy mismatch")
        if self.blocked_claims != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS:
            raise ValueError("kernel ingress diagnostics blocked claims mismatch")
        if self.blocked_compiler_outputs != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ):
            raise ValueError("kernel ingress diagnostics compiler outputs mismatch")
        if self.blocked_execution_surfaces != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ):
            raise ValueError("kernel ingress diagnostics execution surfaces mismatch")
        if type(self.cases) is not tuple:
            raise TypeError("kernel ingress diagnostic cases must be tuple")
        if not self.cases:
            raise ValueError("kernel ingress diagnostics require cases")
        if len(self.cases) > (
            MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASES
        ):
            raise ValueError("kernel ingress diagnostic case limit exceeded")
        case_ids: list[str] = []
        module_digests: list[str] = []
        for case in self.cases:
            if not isinstance(case, SourceToIntentResearchKernelIngressDiagnosticResult):
                raise TypeError("kernel ingress diagnostics need result cases")
            case_ids.append(case.case_id)
            module_digests.append(case.module_digest)
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("kernel ingress diagnostic case IDs must be unique")
        if len(module_digests) != len(set(module_digests)):
            raise ValueError("kernel ingress diagnostic module digests must be unique")
        if not self.accepted_case_count:
            raise ValueError("kernel ingress diagnostics need accepted cases")
        if not self.rejected_case_count:
            raise ValueError("kernel ingress diagnostics need rejected cases")

    @property
    def accepted_case_count(self) -> int:
        """Return accepted diagnostic case count."""

        return sum(1 for case in self.cases if case.outcome == "accepted")

    @property
    def rejected_case_count(self) -> int:
        """Return rejected diagnostic case count."""

        return sum(1 for case in self.cases if case.outcome == "rejected")

    @property
    def rejection_reasons(self) -> tuple[str, ...]:
        """Return sorted rejection reasons observed by the report."""

        return tuple(
            sorted(case.rejection_reason for case in self.cases if case.rejection_reason)
        )


def build_source_to_intent_research_kernel_ingress_diagnostics_report(
    cases: tuple[SourceToIntentResearchKernelIngressDiagnosticCase, ...],
) -> SourceToIntentResearchKernelIngressDiagnosticsReport:
    """Run kernel ingress diagnostics and return source-free evidence."""

    if type(cases) is not tuple:
        raise TypeError("kernel ingress diagnostic cases must be a tuple")
    results = tuple(_run_diagnostic_case(case) for case in cases)
    return SourceToIntentResearchKernelIngressDiagnosticsReport(cases=results)


def source_to_intent_research_kernel_ingress_diagnostics_report_to_dict(
    report: SourceToIntentResearchKernelIngressDiagnosticsReport,
) -> dict[str, object]:
    """Return a JSON-compatible kernel ingress diagnostics report."""

    if not isinstance(report, SourceToIntentResearchKernelIngressDiagnosticsReport):
        raise TypeError("kernel ingress diagnostics report must be report")
    return {
        "accepted_case_count": report.accepted_case_count,
        "blocked_claims": list(report.blocked_claims),
        "blocked_compiler_outputs": list(report.blocked_compiler_outputs),
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "cases": [
            {
                "case_id": case.case_id,
                "expectation": case.expectation,
                "ingress_report_digest": case.ingress_report_digest,
                "kernel_name": case.kernel_name,
                "module_bytes": case.module_bytes,
                "module_digest": case.module_digest,
                "operation_families": list(case.operation_families),
                "outcome": case.outcome,
                "rejection_reason": case.rejection_reason,
                "source_name": case.source_name,
            }
            for case in report.cases
        ],
        "default_parser_status": report.default_parser_status,
        "diagnostics_contract": report.diagnostics_contract,
        "ingress_contract": report.ingress_contract,
        "input_policy": report.input_policy,
        "output_policy": report.output_policy,
        "parser_output_policy": report.parser_output_policy,
        "parser_status": report.parser_status,
        "raw_source_policy": report.raw_source_policy,
        "raw_value_policy": report.raw_value_policy,
        "rejected_case_count": report.rejected_case_count,
        "rejection_reasons": list(report.rejection_reasons),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION
        ),
    }


def dump_source_to_intent_research_kernel_ingress_diagnostics_report(
    report: SourceToIntentResearchKernelIngressDiagnosticsReport,
) -> str:
    """Render stable source-free kernel ingress diagnostics evidence."""

    text = json.dumps(
        source_to_intent_research_kernel_ingress_diagnostics_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_BYTES
    ):
        raise ValueError("kernel ingress diagnostics report exceeds budget")
    return text + "\n"


def _run_diagnostic_case(
    case: SourceToIntentResearchKernelIngressDiagnosticCase,
) -> SourceToIntentResearchKernelIngressDiagnosticResult:
    if not isinstance(case, SourceToIntentResearchKernelIngressDiagnosticCase):
        raise TypeError("kernel ingress diagnostic case must be case")
    module_bytes = case.module_source.encode("utf-8")
    module_digest = f"sha256:{sha256(module_bytes).hexdigest()}"
    try:
        result = ingest_triton_module_source_to_source_intent(
            case.module_source,
            source_name=case.source_name,
            kernel_name=case.kernel_name,
            tensor_shapes=case.tensor_shapes,
        )
    except (SourceToIntentResearchKernelIngressError, TypeError, ValueError) as exc:
        if case.expectation != "rejected":
            raise ValueError("accepted kernel ingress diagnostic was rejected") from exc
        _assert_expected_rejection(case.expected_rejection_reason, exc)
        return SourceToIntentResearchKernelIngressDiagnosticResult(
            case_id=case.case_id,
            expectation=case.expectation,
            outcome="rejected",
            source_name=case.source_name,
            kernel_name=case.kernel_name,
            module_bytes=len(module_bytes),
            module_digest=module_digest,
            rejection_reason=case.expected_rejection_reason,
        )
    if case.expectation != "accepted":
        raise ValueError("rejected kernel ingress diagnostic unexpectedly accepted")
    ingress_report_payload = json.dumps(
        source_to_intent_research_kernel_ingress_report_to_dict(result.report),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return SourceToIntentResearchKernelIngressDiagnosticResult(
        case_id=case.case_id,
        expectation=case.expectation,
        outcome="accepted",
        source_name=case.source_name,
        kernel_name=case.kernel_name,
        module_bytes=len(module_bytes),
        module_digest=module_digest,
        operation_families=result.report.operation_families,
        ingress_report_digest=f"sha256:{sha256(ingress_report_payload).hexdigest()}",
    )


def _assert_expected_rejection(reason: str, exc: Exception) -> None:
    fragment = SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS[
        reason
    ]
    if fragment not in str(exc):
        raise ValueError("kernel ingress diagnostic reason mismatch") from exc


def _validate_operation_families(values: tuple[str, ...]) -> None:
    if type(values) is not tuple:
        raise TypeError("kernel ingress diagnostic families must be a tuple")
    if tuple(sorted(values)) != values:
        raise ValueError("kernel ingress diagnostic families must be sorted")
    if len(values) != len(set(values)):
        raise ValueError("kernel ingress diagnostic families must be unique")
    for value in values:
        _validate_report_text(value, "operation_family")


def _validate_positive_int(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"kernel ingress diagnostic {label} must be positive")


def _validate_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"kernel ingress diagnostic {label} must be sha256")


def _validate_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIAGNOSTIC_TEXT_RE.fullmatch(value):
        raise ValueError(f"kernel ingress diagnostic {label} must be report-safe text")
    if (
        len(value.encode("utf-8"))
        > MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_FIELD_BYTES
    ):
        raise ValueError(f"kernel ingress diagnostic {label} exceeds budget")


def _validate_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"kernel ingress diagnostic {label} invalid")
    if (
        len(value.encode("utf-8"))
        > MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_FIELD_BYTES
    ):
        raise ValueError(f"kernel ingress diagnostic {label} exceeds budget")


__all__ = [
    "MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASES",
    "MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_MODULE_BYTES",
    "MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_BYTES",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASE_EXPECTATIONS",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS",
    "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION",
    "SourceToIntentResearchKernelIngressDiagnosticCase",
    "SourceToIntentResearchKernelIngressDiagnosticResult",
    "SourceToIntentResearchKernelIngressDiagnosticsReport",
    "build_source_to_intent_research_kernel_ingress_diagnostics_report",
    "dump_source_to_intent_research_kernel_ingress_diagnostics_report",
    "source_to_intent_research_kernel_ingress_diagnostics_report_to_dict",
]
