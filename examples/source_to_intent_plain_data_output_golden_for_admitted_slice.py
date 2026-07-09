"""Emit Source Intent plain-data output golden evidence for the admitted slice."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from hashlib import sha256

from examples.source_free_diagnostics_admission_tests import (
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
    build_source_free_diagnostics_admission_tests_report,
)
from examples.source_to_intent_research_parser import (
    MATMUL_ELEMENTWISE_SOURCE,
    SOFTMAX_REDUCTION_SOURCE,
)
from tuc.frontend.source_free_diagnostics_admission import (
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT,
    SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS,
)
from tuc.frontend.source_to_intent_admitted_slice_golden import (
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ADMISSION_EFFECT,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ARTIFACT_POLICY,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OUTPUT_POLICY,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS,
    SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_TARGET_SLICE,
    build_source_intent_plain_data_golden_payload,
    build_source_to_intent_admitted_slice_golden_report,
    source_to_intent_admitted_slice_golden_report_to_dict,
    source_to_intent_plain_data_golden_case_from_parse_result,
)
from tuc.frontend.source_to_intent_research_parser import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    parse_triton_source_to_source_intent,
)

SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_plain_data_output_golden_for_admitted_slice_report.v0"
)
SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID = (
    "source_to_intent_plain_data_output_golden_for_admitted_slice"
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_effect",
        "artifact_policy",
        "blocked_compiler_outputs",
        "blocked_execution_surfaces",
        "case_count",
        "cases",
        "direct_source_ingestion",
        "evidence_id",
        "golden_contract",
        "golden_status",
        "issues",
        "operation_family_coverage",
        "operation_family_coverage_complete",
        "output_policy",
        "plain_data_schema_version",
        "raw_source_policy",
        "report_digest",
        "required_control_count",
        "required_controls",
        "schema_version",
        "source_free_diagnostics_evidence",
        "source_intent_contract",
        "source_intent_schema_version",
        "source_to_compute_graph",
        "source_to_hac_ir",
        "source_to_intent_plain_data_output_golden",
        "source_to_runtime_plan",
        "target_slice",
    }
)
_CASE_KEYS = frozenset(
    {
        "case_id",
        "default_parser_status",
        "line_count",
        "operation_count",
        "operation_families",
        "parser_contract",
        "parser_output_policy",
        "parser_status",
        "plain_data_digest",
        "public_returns",
        "return_count",
        "source_bytes",
        "source_digest",
        "source_intent_contract",
        "source_intent_schema_version",
        "source_name",
        "tensor_count",
    }
)
_SOURCE_FREE_DIAGNOSTICS_EVIDENCE_KEYS = frozenset(
    {"contract", "digest", "evidence_id", "source_free", "status", "supports_golden"}
)
_SHA256_RE = re.compile(r"^sha256:[a-f0-9]{64}$")
_REPORT_TEXT_RE = re.compile(r"^(sha256:[a-f0-9]{64}|[A-Za-z][A-Za-z0-9_.:-]*)$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import os",
    "tl.dot",
    "tl.store",
    '"backend_artifact":',
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
)


class SourceToIntentAdmittedSliceGoldenReportError(AssertionError):
    """Raised when admitted-slice Source Intent golden evidence drifts."""


def build_admitted_slice_parse_results():
    """Build explicit research parser results for the admitted-slice goldens."""

    matmul = parse_triton_source_to_source_intent(
        MATMUL_ELEMENTWISE_SOURCE,
        source_name="research_matmul_elementwise",
        tensor_shapes={
            "a": (4, 8),
            "b": (8, 2),
            "y": (4, 2),
        },
    )
    softmax = parse_triton_source_to_source_intent(
        SOFTMAX_REDUCTION_SOURCE,
        source_name="research_softmax_reduction",
        tensor_shapes={"x": (4, 8), "y": (4,)},
    )
    return (matmul, softmax)


def build_source_to_intent_plain_data_output_golden_report() -> dict[str, object]:
    """Build the current admitted-slice Source Intent plain-data golden report."""

    results = build_admitted_slice_parse_results()
    cases = (
        source_to_intent_plain_data_golden_case_from_parse_result(
            results[0],
            case_id="admitted_slice_matmul_elementwise_plain_data_golden",
        ),
        source_to_intent_plain_data_golden_case_from_parse_result(
            results[1],
            case_id="admitted_slice_softmax_reduction_plain_data_golden",
        ),
    )
    base_report = build_source_to_intent_admitted_slice_golden_report(cases)
    payload = source_to_intent_admitted_slice_golden_report_to_dict(base_report)
    diagnostics_report = build_source_free_diagnostics_admission_tests_report()
    report: dict[str, object] = {
        **payload,
        "evidence_id": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID,
        "issues": [],
        "schema_version": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION,
        "source_free_diagnostics_evidence": {
            "contract": SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT,
            "digest": _digest_payload(diagnostics_report),
            "evidence_id": SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
            "source_free": True,
            "status": SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS,
            "supports_golden": True,
        },
    }
    report["report_digest"] = _digest_payload(report)
    assert_source_to_intent_admitted_slice_golden_report_contract(report)
    return report


def build_source_intent_plain_data_output_golden() -> str:
    """Return the reviewable Source Intent plain-data golden payload."""

    results = build_admitted_slice_parse_results()
    payload = build_source_intent_plain_data_golden_payload(
        (
            (
                "admitted_slice_matmul_elementwise_plain_data_golden",
                results[0].report.source_name,
                results[0].source_intent_payload,
            ),
            (
                "admitted_slice_softmax_reduction_plain_data_golden",
                results[1].report.source_name,
                results[1].source_intent_payload,
            ),
        )
    )
    text = json.dumps(payload, indent=2, sort_keys=True)
    _assert_text_is_source_free(text)
    return text + "\n"


def build_report() -> str:
    """Return stable JSON evidence for the admitted-slice plain-data golden."""

    return json.dumps(
        build_source_to_intent_plain_data_output_golden_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["--source-intent"]:
        print(build_source_intent_plain_data_output_golden(), end="")
        return
    if args:
        raise SystemExit(
            "usage: source_to_intent_plain_data_output_golden_for_admitted_slice.py "
            "[--source-intent]"
        )
    print(build_report(), end="")


def assert_source_to_intent_admitted_slice_golden_report_contract(
    report: object,
) -> None:
    """Fail closed unless the admitted-slice golden report matches v0."""

    if not isinstance(report, Mapping):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden report must be object"
        )
    if set(report) != _TOP_LEVEL_KEYS:
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden top-level keys drift"
        )
    expected = {
        "admission_effect": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ADMISSION_EFFECT,
        "artifact_policy": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_ARTIFACT_POLICY,
        "case_count": 2,
        "direct_source_ingestion": False,
        "evidence_id": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_EVIDENCE_ID,
        "golden_contract": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_CONTRACT,
        "golden_status": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_STATUS,
        "operation_family_coverage_complete": True,
        "output_policy": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OUTPUT_POLICY,
        "plain_data_schema_version": (
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_PLAIN_DATA_SCHEMA_VERSION
        ),
        "raw_source_policy": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_RAW_SOURCE_POLICY,
        "required_control_count": len(
            SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS
        ),
        "schema_version": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REPORT_SCHEMA_VERSION,
        "source_to_compute_graph": False,
        "source_to_hac_ir": False,
        "source_to_intent_plain_data_output_golden": True,
        "source_to_runtime_plan": False,
        "target_slice": SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_TARGET_SLICE,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise SourceToIntentAdmittedSliceGoldenReportError(
                f"admitted-slice golden {key} drift"
            )
    _assert_string_sequence(
        report.get("blocked_compiler_outputs"),
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_COMPILER_OUTPUTS,
        "blocked_compiler_outputs",
    )
    _assert_string_sequence(
        report.get("blocked_execution_surfaces"),
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_BLOCKED_EXECUTION_SURFACES,
        "blocked_execution_surfaces",
    )
    _assert_string_sequence(
        report.get("operation_family_coverage"),
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_OPERATION_FAMILIES,
        "operation_family_coverage",
    )
    _assert_string_sequence(
        report.get("required_controls"),
        SOURCE_TO_INTENT_ADMITTED_SLICE_GOLDEN_REQUIRED_CONTROLS,
        "required_controls",
    )
    _assert_source_free_diagnostics_evidence(report.get("source_free_diagnostics_evidence"))
    _assert_cases(report.get("cases"))
    if report.get("issues") != []:
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden issues must be empty"
        )
    digest = report.get("report_digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden digest invalid"
        )
    if digest != _digest_payload(report):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden digest drift"
        )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_source_free_diagnostics_evidence(value: object) -> None:
    if not isinstance(value, Mapping) or set(value) != _SOURCE_FREE_DIAGNOSTICS_EVIDENCE_KEYS:
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden diagnostics evidence keys drift"
        )
    expected = {
        "contract": SOURCE_FREE_DIAGNOSTICS_ADMISSION_CONTRACT,
        "evidence_id": SOURCE_FREE_DIAGNOSTICS_ADMISSION_EVIDENCE_ID,
        "source_free": True,
        "status": SOURCE_FREE_DIAGNOSTICS_ADMISSION_STATUS,
        "supports_golden": True,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise SourceToIntentAdmittedSliceGoldenReportError(
                "admitted-slice golden diagnostics evidence drift"
            )
    digest = value.get("digest")
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden diagnostics digest invalid"
        )


def _assert_cases(value: object) -> None:
    if not isinstance(value, list):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden cases must be list"
        )
    if len(value) != 2:
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden case count drift"
        )
    case_ids = []
    digests = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _CASE_KEYS:
            raise SourceToIntentAdmittedSliceGoldenReportError(
                "admitted-slice golden case keys drift"
            )
        expected = {
            "parser_contract": SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
            "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
            "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
            "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        }
        for key, expected_value in expected.items():
            if item.get(key) != expected_value:
                raise SourceToIntentAdmittedSliceGoldenReportError(
                    f"admitted-slice golden case {key} drift"
                )
        for field_name in (
            "case_id",
            "source_name",
            "source_intent_contract",
            "source_intent_schema_version",
        ):
            value_text = item.get(field_name)
            if not isinstance(value_text, str) or not _REPORT_TEXT_RE.fullmatch(
                value_text
            ):
                raise SourceToIntentAdmittedSliceGoldenReportError(
                    "admitted-slice golden case text drift"
                )
        plain_data_digest = item.get("plain_data_digest")
        source_digest = item.get("source_digest")
        for digest in (plain_data_digest, source_digest):
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise SourceToIntentAdmittedSliceGoldenReportError(
                    "admitted-slice golden case digest invalid"
                )
        for field_name in (
            "source_bytes",
            "line_count",
            "tensor_count",
            "operation_count",
            "return_count",
        ):
            value_int = item.get(field_name)
            if not isinstance(value_int, int) or value_int <= 0:
                raise SourceToIntentAdmittedSliceGoldenReportError(
                    "admitted-slice golden case count invalid"
                )
        operation_families = item.get("operation_families")
        if not isinstance(operation_families, list):
            raise SourceToIntentAdmittedSliceGoldenReportError(
                "admitted-slice golden operation families drift"
            )
        _string_list(operation_families)
        public_returns = item.get("public_returns")
        if not isinstance(public_returns, list):
            raise SourceToIntentAdmittedSliceGoldenReportError(
                "admitted-slice golden public returns drift"
            )
        _string_list(public_returns)
        case_ids.append(item.get("case_id"))
        digests.append(plain_data_digest)
    if len(case_ids) != len(set(case_ids)):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden case IDs must be unique"
        )
    if len(digests) != len(set(digests)):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden plain-data digests must be unique"
        )


def _assert_string_sequence(value: object, expected: tuple[str, ...], field: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise SourceToIntentAdmittedSliceGoldenReportError(
            f"admitted-slice golden {field} drift"
        )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceToIntentAdmittedSliceGoldenReportError(
            "admitted-slice golden expected string list"
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not _REPORT_TEXT_RE.fullmatch(item):
            raise SourceToIntentAdmittedSliceGoldenReportError(
                "admitted-slice golden string list item invalid"
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
            raise SourceToIntentAdmittedSliceGoldenReportError(
                f"admitted-slice golden contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
