"""Emit deterministic planner-overhead portfolio evidence for Kernel Ingress cases."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress import (
        _EXPECTED_CASE_SUMMARIES,
        _MODULE_CASES,
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        _tensor_shapes_for,
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        _EXPECTED_CASE_SUMMARIES,
        _MODULE_CASES,
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        _tensor_shapes_for,
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.benchmarks import (
    PLANNER_OVERHEAD_ARTIFACT_STATUS,
    PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
    PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
    PLANNER_OVERHEAD_NOT_MEASURED_ISSUES,
    PLANNER_OVERHEAD_PHASES,
    PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
    measure_pipeline_planner_overhead,
    planner_overhead_report_to_dict,
)
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.proof import PERFORMANCE_PROOF_BOUNDARY_CONTRACT

PLANNER_OVERHEAD_PORTFOLIO_REPORT_SCHEMA_VERSION = (
    "tuc.planner_overhead_portfolio_report.v0"
)
PLANNER_OVERHEAD_PORTFOLIO_CONTRACT = "planner_overhead_portfolio.kernel_ingress.v0"
PLANNER_OVERHEAD_PORTFOLIO_TIMING_POLICY = (
    "measured_compiler_phase_durations_omitted_for_deterministic_evidence"
)
PLANNER_OVERHEAD_PORTFOLIO_SOURCE_BOUNDARY = (
    "kernel_ingress_compute_graphs_after_source_intent"
)
PLANNER_OVERHEAD_PORTFOLIO_STATUS = "PASS"
PLANNER_OVERHEAD_PORTFOLIO_CASE_STATUS = "planner_overhead_bound"
PLANNER_OVERHEAD_PORTFOLIO_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "duration_ns",
    "import triton",
    "python_source",
    '"raw_source":',
    "raw_source_text",
    "raw_tensor_value",
    "raw_timing_samples",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
    "total_planning_ns",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_UNMEASURED_PHASES = ("graph_construction", "frontend_intake", "execution")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_status",
        "break_even_status",
        "case_count",
        "cases",
        "claim_boundary",
        "covered_operation_families",
        "e2e_contract",
        "execution_time_status",
        "frontend_ingress_contract",
        "kernel_ingress_digest",
        "native_performance_claim",
        "parser_status",
        "planner_overhead_contract",
        "planner_overhead_hidden_in_execution_time",
        "planner_overhead_schema_version",
        "portfolio_contract",
        "raw_source_policy",
        "raw_timing_policy",
        "raw_value_policy",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "break_even_status",
        "case_id",
        "execution_time_status",
        "graph_name",
        "kernel_name",
        "measured_compiler_phase_count",
        "native_performance_claim",
        "operation_families",
        "phase_contract",
        "planner_overhead_hidden_in_execution_time",
        "source_name",
        "status",
        "timing_policy",
        "unmeasured_issues",
        "unmeasured_phase_count",
        "unmeasured_phases",
    }
)


def build_planner_overhead_portfolio_report() -> dict[str, object]:
    """Return source-free planner-overhead portfolio evidence for Kernel Ingress."""

    kernel_ingress_text = build_kernel_ingress_report()
    kernel_ingress = json.loads(kernel_ingress_text)
    assert_kernel_ingress_report_contract(kernel_ingress)

    cases = [
        _build_portfolio_case(case_id, source_name, kernel_name, module_source)
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
    ]
    report: dict[str, object] = {
        "artifact_status": PLANNER_OVERHEAD_ARTIFACT_STATUS,
        "break_even_status": PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
        "case_count": len(cases),
        "cases": cases,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "covered_operation_families": _covered_operation_families(cases),
        "e2e_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "execution_time_status": PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "native_performance_claim": False,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "planner_overhead_contract": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
        "planner_overhead_hidden_in_execution_time": False,
        "planner_overhead_schema_version": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
        "portfolio_contract": PLANNER_OVERHEAD_PORTFOLIO_CONTRACT,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_timing_policy": PLANNER_OVERHEAD_PORTFOLIO_TIMING_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": PLANNER_OVERHEAD_PORTFOLIO_REPORT_SCHEMA_VERSION,
        "source_boundary": PLANNER_OVERHEAD_PORTFOLIO_SOURCE_BOUNDARY,
        "status": PLANNER_OVERHEAD_PORTFOLIO_STATUS,
    }
    assert_planner_overhead_portfolio_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the planner-overhead portfolio."""

    return json.dumps(
        build_planner_overhead_portfolio_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_planner_overhead_portfolio_report_contract(report: object) -> None:
    """Fail closed unless the planner-overhead portfolio report matches contract."""

    if not isinstance(report, Mapping):
        raise ValueError("planner-overhead portfolio report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_status": PLANNER_OVERHEAD_ARTIFACT_STATUS,
        "break_even_status": PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
        "case_count": len(_MODULE_CASES),
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "covered_operation_families": ["elementwise", "matmul", "reduction", "softmax"],
        "e2e_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "execution_time_status": PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "native_performance_claim": False,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "planner_overhead_contract": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
        "planner_overhead_hidden_in_execution_time": False,
        "planner_overhead_schema_version": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
        "portfolio_contract": PLANNER_OVERHEAD_PORTFOLIO_CONTRACT,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_timing_policy": PLANNER_OVERHEAD_PORTFOLIO_TIMING_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": PLANNER_OVERHEAD_PORTFOLIO_REPORT_SCHEMA_VERSION,
        "source_boundary": PLANNER_OVERHEAD_PORTFOLIO_SOURCE_BOUNDARY,
        "status": PLANNER_OVERHEAD_PORTFOLIO_STATUS,
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"planner-overhead portfolio {key} drift")
    digest = report["kernel_ingress_digest"]
    if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("planner-overhead portfolio kernel ingress digest drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("planner-overhead portfolio cases drift")
    case_ids = []
    for case in cases:
        case_ids.append(_assert_case_contract(case))
    if tuple(case_ids) != tuple(case[0] for case in _MODULE_CASES):
        raise ValueError("planner-overhead portfolio case order drift")
    _assert_report_is_metadata_only(report)


def _build_portfolio_case(
    case_id: str,
    source_name: str,
    kernel_name: str,
    module_source: str,
) -> dict[str, object]:
    ingress = ingest_triton_module_source_to_source_intent(
        module_source,
        source_name=source_name,
        kernel_name=kernel_name,
        tensor_shapes=_tensor_shapes_for(source_name),
    )
    module = source_intent_from_mapping(ingress.parser_result.source_intent_payload)
    metadata = source_intent_to_triton_metadata(module)
    measurement = measure_pipeline_planner_overhead(
        metadata.to_compute_graph(),
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    payload = planner_overhead_report_to_dict(measurement.report)
    _assert_planner_payload(case_id, source_name, payload)
    measured_count = sum(
        1 for phase in payload["phase_timings"] if phase["measurement_status"] == "measured"
    )
    backend_sequence = [
        assignment.backend_name
        for assignment in measurement.compilation.partition_plan.assignments
    ]
    return {
        "backend_sequence": backend_sequence,
        "break_even_status": payload["break_even_status"],
        "case_id": case_id,
        "execution_time_status": payload["execution_time_status"],
        "graph_name": payload["graph_name"],
        "kernel_name": kernel_name,
        "measured_compiler_phase_count": measured_count,
        "native_performance_claim": payload["native_performance_claim"],
        "operation_families": list(ingress.report.operation_families),
        "phase_contract": list(PLANNER_OVERHEAD_PHASES),
        "planner_overhead_hidden_in_execution_time": payload[
            "planner_overhead_hidden_in_execution_time"
        ],
        "source_name": source_name,
        "status": PLANNER_OVERHEAD_PORTFOLIO_CASE_STATUS,
        "timing_policy": PLANNER_OVERHEAD_PORTFOLIO_TIMING_POLICY,
        "unmeasured_issues": list(PLANNER_OVERHEAD_NOT_MEASURED_ISSUES),
        "unmeasured_phase_count": len(_UNMEASURED_PHASES),
        "unmeasured_phases": list(_UNMEASURED_PHASES),
    }


def _assert_planner_payload(
    case_id: str,
    source_name: str,
    payload: Mapping[str, object],
) -> None:
    expected = {
        "artifact_status": PLANNER_OVERHEAD_ARTIFACT_STATUS,
        "break_even_status": PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "execution_time_status": PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
        "graph_name": source_name,
        "issues": list(PLANNER_OVERHEAD_NOT_MEASURED_ISSUES),
        "native_performance_claim": False,
        "planner_overhead_hidden_in_execution_time": False,
        "schema_version": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
    }
    for key, expected_value in expected.items():
        if payload[key] != expected_value:
            raise ValueError(f"planner-overhead portfolio {case_id} {key} drift")
    phases = payload["phase_timings"]
    if not isinstance(phases, list):
        raise ValueError("planner-overhead portfolio phase timing drift")
    phase_names = [phase["phase_name"] for phase in phases if isinstance(phase, dict)]
    if phase_names != list(PLANNER_OVERHEAD_PHASES):
        raise ValueError("planner-overhead portfolio phase order drift")
    for phase in phases:
        if not isinstance(phase, dict):
            raise ValueError("planner-overhead portfolio phase shape drift")
        if phase.get("included_in_execution_time") is not False:
            raise ValueError("planner-overhead portfolio hides overhead in execution")
    if not isinstance(payload["total_planning_ns"], int):
        raise ValueError("planner-overhead portfolio planning total drift")


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("planner-overhead portfolio case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_SUMMARIES:
        raise ValueError("planner-overhead portfolio case id drift")
    expected = _EXPECTED_CASE_SUMMARIES[case_id]
    expected_source = dict(_source_names_by_case())[case_id]
    if case["source_name"] != expected_source:
        raise ValueError("planner-overhead portfolio source_name drift")
    if case["graph_name"] != expected_source:
        raise ValueError("planner-overhead portfolio graph_name drift")
    if case["kernel_name"] != dict(_kernel_names_by_case())[case_id]:
        raise ValueError("planner-overhead portfolio kernel_name drift")
    if case["backend_sequence"] != expected["backend_sequence"]:
        raise ValueError("planner-overhead portfolio backend_sequence drift")
    if case["operation_families"] != expected["operation_families"]:
        raise ValueError("planner-overhead portfolio operation_families drift")
    expected_fields = {
        "break_even_status": PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
        "execution_time_status": PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
        "measured_compiler_phase_count": 5,
        "native_performance_claim": False,
        "phase_contract": list(PLANNER_OVERHEAD_PHASES),
        "planner_overhead_hidden_in_execution_time": False,
        "status": PLANNER_OVERHEAD_PORTFOLIO_CASE_STATUS,
        "timing_policy": PLANNER_OVERHEAD_PORTFOLIO_TIMING_POLICY,
        "unmeasured_issues": list(PLANNER_OVERHEAD_NOT_MEASURED_ISSUES),
        "unmeasured_phase_count": len(_UNMEASURED_PHASES),
        "unmeasured_phases": list(_UNMEASURED_PHASES),
    }
    for key, expected_value in expected_fields.items():
        if case[key] != expected_value:
            raise ValueError(f"planner-overhead portfolio {key} drift")
    return case_id


def _source_names_by_case() -> tuple[tuple[str, str], ...]:
    return tuple((case_id, source_name) for case_id, source_name, _, _ in _MODULE_CASES)


def _kernel_names_by_case() -> tuple[tuple[str, str], ...]:
    return tuple((case_id, kernel_name) for case_id, _, kernel_name, _ in _MODULE_CASES)


def _covered_operation_families(cases: list[dict[str, object]]) -> list[str]:
    families = {
        family
        for case in cases
        for family in case["operation_families"]
        if isinstance(family, str)
    }
    return sorted(families)


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"planner-overhead portfolio {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("planner-overhead portfolio report is not JSON") from exc
    for fragment in PLANNER_OVERHEAD_PORTFOLIO_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "planner-overhead portfolio contains forbidden source, value, "
                "or timing material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
