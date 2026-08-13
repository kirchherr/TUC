"""Bind accepted Source-to-Intent research parser slices to Triton idiom scope."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_execution_bridge import (
        SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
    )
    from examples.source_to_intent_research_execution_bridge import (
        build_report as build_execution_bridge_report,
    )
    from examples.source_to_intent_research_parser_conformance_gate import (
        REQUIRED_PARSER_SOURCE_NAMES,
        build_source_to_intent_research_parser_results,
    )
    from examples.triton_idiom_coverage_report import (
        build_report as build_triton_idiom_coverage_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
    )
    from source_to_intent_research_execution_bridge import (
        build_report as build_execution_bridge_report,
    )
    from source_to_intent_research_parser_conformance_gate import (  # type: ignore[no-redef]
        REQUIRED_PARSER_SOURCE_NAMES,
        build_source_to_intent_research_parser_results,
    )
    from triton_idiom_coverage_report import (  # type: ignore[no-redef]
        build_report as build_triton_idiom_coverage_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES,
    TRITON_IDIOM_COVERAGE_CONTRACT,
)

SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_idiom_alignment_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_CONTRACT = (
    "source_to_intent_research_idiom_alignment.scope.v0"
)
SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_INPUT_POLICY = (
    "accepted_research_parser_results_only"
)
SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_COVERAGE_POLICY = (
    "parser_operation_families_must_match_covered_idioms"
)
SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_SOURCE_BOUNDARY = (
    "source_intent.v0_plain_data_reintake"
)
SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "python_source",
    "raw_source",
    "raw_tensor_value",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_source_count",
        "alignment_contract",
        "artifact_policy",
        "blocked_execution_surfaces",
        "cases",
        "coverage_contract",
        "coverage_policy",
        "coverage_report_digest",
        "covered_operation_families",
        "default_parser_status",
        "direct_triton_source_ingestion",
        "execution_bridge_contract",
        "execution_bridge_digest",
        "input_policy",
        "parser_sources",
        "parser_status",
        "schema_version",
        "source_boundary",
        "status",
        "unsupported_operation_families",
    }
)
_CASE_KEYS = frozenset(
    {"case_id", "matched_idioms", "operation_families", "status"}
)
_EXPECTED_COVERED_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)
_EXPECTED_CASE_SUMMARIES = {
    "research_matmul_elementwise": {
        "matched_idioms": ["metadata_elementwise_activation", "metadata_matmul_projection"],
        "operation_families": ["elementwise", "matmul"],
    },
    "research_softmax_reduction": {
        "matched_idioms": ["metadata_reduction_axis", "metadata_softmax_axis"],
        "operation_families": ["reduction", "softmax"],
    },
}


def build_idiom_alignment_report() -> dict[str, object]:
    """Return metadata-only evidence that parser slices fit covered Triton idioms."""

    coverage_text = build_triton_idiom_coverage_report()
    coverage_report = json.loads(coverage_text)
    execution_bridge_text = build_execution_bridge_report()
    parser_results = build_source_to_intent_research_parser_results()
    coverage_by_family = _coverage_by_family(coverage_report)
    cases = [
        _build_case(result.report.source_name, result.report.operation_families, coverage_by_family)
        for result in parser_results
    ]
    covered_operation_families = sorted(coverage_by_family)
    unsupported = sorted(
        family
        for case in cases
        for family in case["operation_families"]
        if family not in covered_operation_families
    )
    report: dict[str, object] = {
        "accepted_source_count": len(cases),
        "alignment_contract": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_CONTRACT,
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_ARTIFACT_POLICY,
        "blocked_execution_surfaces": list(
            TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES
        ),
        "cases": cases,
        "coverage_contract": TRITON_IDIOM_COVERAGE_CONTRACT,
        "coverage_policy": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_COVERAGE_POLICY,
        "coverage_report_digest": _digest(coverage_text),
        "covered_operation_families": covered_operation_families,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "direct_triton_source_ingestion": False,
        "execution_bridge_contract": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
        "execution_bridge_digest": _digest(execution_bridge_text),
        "input_policy": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_INPUT_POLICY,
        "parser_sources": list(REQUIRED_PARSER_SOURCE_NAMES),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_SOURCE_BOUNDARY,
        "status": "PASS" if not unsupported else "FAIL",
        "unsupported_operation_families": unsupported,
    }
    assert_research_idiom_alignment_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for research parser idiom alignment."""

    return json.dumps(build_idiom_alignment_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_research_idiom_alignment_report_contract(report: object) -> None:
    """Fail closed unless the idiom alignment report matches the v0 contract."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research idiom alignment report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "alignment_contract": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_CONTRACT,
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_ARTIFACT_POLICY,
        "coverage_contract": TRITON_IDIOM_COVERAGE_CONTRACT,
        "coverage_policy": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_COVERAGE_POLICY,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "direct_triton_source_ingestion": False,
        "execution_bridge_contract": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_INPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(
                "source-to-intent research idiom alignment "
                f"{key} contract drift"
            )
    if report["blocked_execution_surfaces"] != list(
        TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES
    ):
        raise ValueError(
            "source-to-intent research idiom alignment execution surface drift"
        )
    if report["parser_sources"] != list(REQUIRED_PARSER_SOURCE_NAMES):
        raise ValueError("source-to-intent research idiom alignment source drift")
    if (
        tuple(report["covered_operation_families"])
        != _EXPECTED_COVERED_OPERATION_FAMILIES
    ):
        raise ValueError("source-to-intent research idiom alignment coverage drift")
    if report["unsupported_operation_families"] != []:
        raise ValueError("source-to-intent research idiom alignment unsupported scope")
    for key in ("coverage_report_digest", "execution_bridge_digest"):
        value = report[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("source-to-intent research idiom alignment digest drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("source-to-intent research idiom alignment cases drift")
    if report["accepted_source_count"] != len(cases):
        raise ValueError("source-to-intent research idiom alignment count drift")
    case_ids = []
    for case in cases:
        case_ids.append(_assert_idiom_alignment_case_contract(case))
    if tuple(case_ids) != REQUIRED_PARSER_SOURCE_NAMES:
        raise ValueError("source-to-intent research idiom alignment case order drift")
    _assert_report_is_metadata_only(report)


def _build_case(
    source_name: str,
    operation_families: tuple[str, ...],
    coverage_by_family: Mapping[str, str],
) -> dict[str, object]:
    families = sorted(operation_families)
    matched_idioms = sorted(coverage_by_family[family] for family in families)
    return {
        "case_id": source_name,
        "matched_idioms": matched_idioms,
        "operation_families": families,
        "status": "covered",
    }


def _coverage_by_family(coverage_report: Mapping[str, object]) -> dict[str, str]:
    if coverage_report.get("coverage_contract") != TRITON_IDIOM_COVERAGE_CONTRACT:
        raise ValueError("source-to-intent research idiom alignment coverage drift")
    if coverage_report.get("triton_idiom_coverage_ready") is not True:
        raise ValueError("source-to-intent research idiom alignment coverage not ready")
    coverages = coverage_report.get("coverages")
    if not isinstance(coverages, list):
        raise ValueError("source-to-intent research idiom alignment coverage missing")
    by_family: dict[str, str] = {}
    for coverage in coverages:
        if not isinstance(coverage, Mapping):
            raise ValueError("source-to-intent research idiom alignment coverage invalid")
        family = coverage.get("operation_family")
        idiom_id = coverage.get("idiom_id")
        status = coverage.get("coverage_status")
        if not isinstance(family, str) or not isinstance(idiom_id, str):
            raise ValueError("source-to-intent research idiom alignment coverage invalid")
        if status != "metadata_golden_covered":
            raise ValueError("source-to-intent research idiom alignment coverage invalid")
        by_family[family] = idiom_id
    return by_family


def _assert_idiom_alignment_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("source-to-intent research idiom alignment case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_SUMMARIES:
        raise ValueError("source-to-intent research idiom alignment case id drift")
    expected = _EXPECTED_CASE_SUMMARIES[case_id]
    if case["operation_families"] != expected["operation_families"]:
        raise ValueError("source-to-intent research idiom alignment family drift")
    if case["matched_idioms"] != expected["matched_idioms"]:
        raise ValueError("source-to-intent research idiom alignment idiom drift")
    if case["status"] != "covered":
        raise ValueError("source-to-intent research idiom alignment case status drift")
    return case_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research idiom alignment {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "source-to-intent research idiom alignment report is not JSON data"
        ) from exc
    for fragment in SOURCE_TO_INTENT_RESEARCH_IDIOM_ALIGNMENT_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research idiom alignment report contains "
                "forbidden source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
