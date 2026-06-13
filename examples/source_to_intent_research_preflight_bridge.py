"""Bind Source-to-Intent research parser diagnostics to Triton source preflight."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_diagnostics import (
        build_source_to_intent_research_diagnostic_cases,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_diagnostics import (  # type: ignore[no-redef]
        build_source_to_intent_research_diagnostic_cases,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    TRITON_SOURCE_PREFLIGHT_CONTRACT,
    SourceToIntentResearchDiagnosticCase,
    build_source_to_intent_research_diagnostics_report,
    preflight_triton_source,
    source_to_intent_research_diagnostics_report_to_dict,
)

SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_preflight_bridge_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_CONTRACT = (
    "source_to_intent_research_preflight_bridge.execution_free.v0"
)
SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_ARTIFACT_POLICY = (
    "metadata_only_source_omitted"
)
SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_SOURCE_BOUNDARY = (
    "triton_source_preflight_before_research_parser"
)
SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "python_source",
    "raw_source_text",
    "raw_tensor_value",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_case_count",
        "artifact_policy",
        "blocked_execution_surfaces",
        "bridge_contract",
        "case_count",
        "cases",
        "default_parser_status",
        "diagnostics_contract",
        "diagnostics_digest",
        "parser_output_policy",
        "parser_semantic_reject_count",
        "parser_status",
        "preflight_accepted_count",
        "preflight_contract",
        "preflight_reject_count",
        "raw_source_policy",
        "rejected_case_count",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_CASE_KEYS = frozenset(
    {
        "bridge_stage",
        "case_id",
        "expectation",
        "operation_families",
        "parser_diagnostic_outcome",
        "parser_rejection_reason",
        "preflight_rejected_features",
        "preflight_status",
        "source_digest",
        "source_name",
    }
)
_EXPECTED_CASE_STAGES = {
    "accepted_matmul_elementwise": "accepted_pipeline",
    "accepted_softmax_reduction": "accepted_pipeline",
    "reject_ambiguous_softmax_axis": "parser_semantic_reject",
    "reject_decorator_call": "preflight_reject",
    "reject_hardware_hint": "parser_semantic_reject",
    "reject_import_escape": "preflight_reject",
}
_EXPECTED_PREFLIGHT_REJECTIONS = {
    "accepted_matmul_elementwise": [],
    "accepted_softmax_reduction": [],
    "reject_ambiguous_softmax_axis": [],
    "reject_decorator_call": ["decorator_call", "unsupported_call_target"],
    "reject_hardware_hint": [],
    "reject_import_escape": ["import_statement"],
}
_EXPECTED_OPERATION_FAMILIES = {
    "accepted_matmul_elementwise": ["elementwise", "matmul"],
    "accepted_softmax_reduction": ["reduction", "softmax"],
    "reject_ambiguous_softmax_axis": ["softmax"],
    "reject_decorator_call": [],
    "reject_hardware_hint": [],
    "reject_import_escape": [],
}


def build_preflight_bridge_report() -> dict[str, object]:
    """Return source-free evidence that research parsing is gated by preflight."""

    diagnostic_cases = build_source_to_intent_research_diagnostic_cases()
    diagnostics = build_source_to_intent_research_diagnostics_report(diagnostic_cases)
    diagnostics_payload = source_to_intent_research_diagnostics_report_to_dict(diagnostics)
    diagnostic_results = {
        case["case_id"]: case for case in diagnostics_payload["cases"]
    }
    cases = [
        _build_case(case, diagnostic_results[case.case_id]) for case in diagnostic_cases
    ]
    bridge_stage_counts = {
        "accepted_pipeline": sum(
            1 for case in cases if case["bridge_stage"] == "accepted_pipeline"
        ),
        "parser_semantic_reject": sum(
            1 for case in cases if case["bridge_stage"] == "parser_semantic_reject"
        ),
        "preflight_reject": sum(
            1 for case in cases if case["bridge_stage"] == "preflight_reject"
        ),
    }
    diagnostics_text = json.dumps(
        diagnostics_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    report: dict[str, object] = {
        "accepted_case_count": diagnostics.accepted_case_count,
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_ARTIFACT_POLICY,
        "blocked_execution_surfaces": list(diagnostics.blocked_execution_surfaces),
        "bridge_contract": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_CONTRACT,
        "case_count": len(cases),
        "cases": cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT,
        "diagnostics_digest": _digest(diagnostics_text),
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_semantic_reject_count": bridge_stage_counts["parser_semantic_reject"],
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "preflight_accepted_count": sum(
            1 for case in cases if case["preflight_status"] == "accepted"
        ),
        "preflight_contract": TRITON_SOURCE_PREFLIGHT_CONTRACT,
        "preflight_reject_count": bridge_stage_counts["preflight_reject"],
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY,
        "rejected_case_count": diagnostics.rejected_case_count,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    assert_preflight_bridge_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the research preflight bridge."""

    return json.dumps(build_preflight_bridge_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_preflight_bridge_report_contract(report: object) -> None:
    """Fail closed unless the preflight bridge report matches the v0 contract."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research preflight bridge report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "accepted_case_count": 2,
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_ARTIFACT_POLICY,
        "bridge_contract": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_CONTRACT,
        "case_count": 6,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_CONTRACT,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_semantic_reject_count": 2,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "preflight_accepted_count": 4,
        "preflight_contract": TRITON_SOURCE_PREFLIGHT_CONTRACT,
        "preflight_reject_count": 2,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_DIAGNOSTICS_RAW_SOURCE_POLICY,
        "rejected_case_count": 4,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(
                "source-to-intent research preflight bridge "
                f"{key} contract drift"
            )
    diagnostics_digest = report["diagnostics_digest"]
    if (
        not isinstance(diagnostics_digest, str)
        or not _SHA256_DIGEST_PATTERN.fullmatch(diagnostics_digest)
    ):
        raise ValueError("source-to-intent research preflight bridge digest drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("source-to-intent research preflight bridge cases drift")
    case_ids = []
    for case in cases:
        case_ids.append(_assert_preflight_bridge_case_contract(case))
    if tuple(case_ids) != tuple(_EXPECTED_CASE_STAGES):
        raise ValueError("source-to-intent research preflight bridge case order drift")
    _assert_report_is_source_free(report)


def _build_case(
    case: SourceToIntentResearchDiagnosticCase,
    diagnostic_result: Mapping[str, object],
) -> dict[str, object]:
    preflight = preflight_triton_source(case.source, source_name=case.source_name)
    preflight_status = "accepted" if preflight.accepted else "rejected"
    parser_outcome = str(diagnostic_result["outcome"])
    if preflight.accepted and parser_outcome == "accepted":
        bridge_stage = "accepted_pipeline"
    elif preflight.accepted:
        bridge_stage = "parser_semantic_reject"
    else:
        bridge_stage = "preflight_reject"
    return {
        "bridge_stage": bridge_stage,
        "case_id": case.case_id,
        "expectation": case.expectation,
        "operation_families": list(preflight.operation_families),
        "parser_diagnostic_outcome": parser_outcome,
        "parser_rejection_reason": diagnostic_result["rejection_reason"],
        "preflight_rejected_features": list(preflight.rejected_features),
        "preflight_status": preflight_status,
        "source_digest": diagnostic_result["source_digest"],
        "source_name": case.source_name,
    }


def _assert_preflight_bridge_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("source-to-intent research preflight bridge case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_STAGES:
        raise ValueError("source-to-intent research preflight bridge case id drift")
    if case["bridge_stage"] != _EXPECTED_CASE_STAGES[case_id]:
        raise ValueError("source-to-intent research preflight bridge stage drift")
    if case["operation_families"] != _EXPECTED_OPERATION_FAMILIES[case_id]:
        raise ValueError("source-to-intent research preflight bridge family drift")
    if case["preflight_rejected_features"] != _EXPECTED_PREFLIGHT_REJECTIONS[case_id]:
        raise ValueError("source-to-intent research preflight bridge rejection drift")
    source_digest = case["source_digest"]
    if not isinstance(source_digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(
        source_digest
    ):
        raise ValueError("source-to-intent research preflight bridge digest drift")
    if case["bridge_stage"] == "accepted_pipeline":
        if case["preflight_status"] != "accepted":
            raise ValueError("source-to-intent research preflight bridge status drift")
        if case["parser_diagnostic_outcome"] != "accepted":
            raise ValueError("source-to-intent research preflight bridge outcome drift")
        if case["parser_rejection_reason"] != "":
            raise ValueError("source-to-intent research preflight bridge reason drift")
    else:
        if case["parser_diagnostic_outcome"] != "rejected":
            raise ValueError("source-to-intent research preflight bridge outcome drift")
        if not isinstance(case["parser_rejection_reason"], str) or not case[
            "parser_rejection_reason"
        ]:
            raise ValueError("source-to-intent research preflight bridge reason drift")
    if case["bridge_stage"] == "preflight_reject" and case["preflight_status"] != "rejected":
        raise ValueError("source-to-intent research preflight bridge preflight drift")
    if (
        case["bridge_stage"] == "parser_semantic_reject"
        and case["preflight_status"] != "accepted"
    ):
        raise ValueError("source-to-intent research preflight bridge preflight drift")
    return case_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research preflight bridge {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "source-to-intent research preflight bridge report is not JSON data"
        ) from exc
    for fragment in SOURCE_TO_INTENT_RESEARCH_PREFLIGHT_BRIDGE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research preflight bridge report contains "
                "forbidden source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
