"""Run accepted research source buffers through the controlled runtime path."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_execution_bridge import (
        _inputs_for,
        _references_for,
    )
    from examples.source_to_intent_research_parser import (
        MATMUL_ELEMENTWISE_SOURCE,
        SOFTMAX_REDUCTION_SOURCE,
    )
    from examples.source_to_intent_research_parser_conformance_gate import (
        REQUIRED_PARSER_SOURCE_NAMES,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        _inputs_for,
        _references_for,
    )
    from source_to_intent_research_parser import (  # type: ignore[no-redef]
        MATMUL_ELEMENTWISE_SOURCE,
        SOFTMAX_REDUCTION_SOURCE,
    )
    from source_to_intent_research_parser_conformance_gate import (  # type: ignore[no-redef]
        REQUIRED_PARSER_SOURCE_NAMES,
    )

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    build_source_intent_metadata_report,
    parse_triton_source_to_source_intent,
    preflight_triton_source,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
    source_to_intent_research_parse_report_to_dict,
)
from tuc.ir import IRStage
from tuc.runtime import (
    build_runtime_reference_correctness_report,
    dump_runtime_reference_correctness_report,
    execute_graph,
    runtime_execution_readiness_report,
)

SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_source_runtime_smoke_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_CONTRACT = (
    "source_to_intent_research_source_runtime_smoke.e2e.v0"
)
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_INPUT_POLICY = (
    "accepted_research_source_buffers_only"
)
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_SOURCE_BOUNDARY = (
    "caller_provided_source_buffer_to_runtime_via_research_parser"
)
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_RAW_SOURCE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_RAW_VALUE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_BLOCKED_CLAIMS = (
    "general_triton_source_ingestion",
    "native_performance_claim",
    "production_parser",
)
SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_FORBIDDEN_FRAGMENTS = (
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
        "artifact_policy",
        "blocked_claims",
        "case_count",
        "cases",
        "default_parser_status",
        "input_policy",
        "parser_output_policy",
        "parser_sources",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "schema_version",
        "smoke_contract",
        "source_boundary",
        "status",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "case_id",
        "compiler_decision_digest",
        "execution_trace_digest",
        "hac_ir_digest",
        "metadata_intake_digest",
        "metadata_report_digest",
        "operation_families",
        "parser_report_digest",
        "plain_data_digest",
        "preflight_digest",
        "preflight_status",
        "readiness_digest",
        "reference_correctness_digest",
        "runtime_plan_digest",
        "source_digest",
        "terminal_outputs",
        "trace_step_count",
    }
)
_DIGEST_KEYS = (
    "compiler_decision_digest",
    "execution_trace_digest",
    "hac_ir_digest",
    "metadata_intake_digest",
    "metadata_report_digest",
    "parser_report_digest",
    "plain_data_digest",
    "preflight_digest",
    "readiness_digest",
    "reference_correctness_digest",
    "runtime_plan_digest",
    "source_digest",
)
_SOURCE_CASES = (
    ("research_matmul_elementwise", MATMUL_ELEMENTWISE_SOURCE),
    ("research_softmax_reduction", SOFTMAX_REDUCTION_SOURCE),
)
_EXPECTED_CASE_SUMMARIES = {
    "research_matmul_elementwise": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "operation_families": ["elementwise", "matmul"],
        "terminal_outputs": ["activated"],
    },
    "research_softmax_reduction": {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "operation_families": ["reduction", "softmax"],
        "terminal_outputs": ["row_sum"],
    },
}


def build_source_runtime_smoke_report() -> dict[str, object]:
    """Return metadata-only evidence for source-buffer to runtime execution."""

    cases = [_build_case(source_name, source) for source_name, source in _SOURCE_CASES]
    report: dict[str, object] = {
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_BLOCKED_CLAIMS),
        "case_count": len(cases),
        "cases": cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_INPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_sources": list(REQUIRED_PARSER_SOURCE_NAMES),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_REPORT_SCHEMA_VERSION
        ),
        "smoke_contract": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_CONTRACT,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    assert_source_runtime_smoke_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the source-runtime smoke path."""

    return json.dumps(build_source_runtime_smoke_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_source_runtime_smoke_report_contract(report: object) -> None:
    """Fail closed unless the source-runtime smoke report matches the v0 contract."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research source runtime smoke report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_BLOCKED_CLAIMS),
        "case_count": len(_SOURCE_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_INPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_sources": list(REQUIRED_PARSER_SOURCE_NAMES),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_RAW_VALUE_POLICY,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_REPORT_SCHEMA_VERSION,
        "smoke_contract": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_CONTRACT,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(
                "source-to-intent research source runtime smoke "
                f"{key} contract drift"
            )
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("source-to-intent research source runtime smoke cases drift")
    case_ids = []
    for case in cases:
        case_ids.append(_assert_source_runtime_smoke_case_contract(case))
    if tuple(case_ids) != REQUIRED_PARSER_SOURCE_NAMES:
        raise ValueError("source-to-intent research source runtime smoke case order drift")
    _assert_report_is_metadata_only(report)


def _build_case(source_name: str, source: str) -> dict[str, object]:
    preflight = preflight_triton_source(source, source_name=source_name)
    if not preflight.accepted:
        raise AssertionError("source-to-intent research source runtime preflight failed")
    result = parse_triton_source_to_source_intent(
        source,
        source_name=source_name,
        tensor_shapes=_tensor_shapes_for(source_name),
    )
    module = source_intent_from_mapping(result.source_intent_payload)
    metadata = source_intent_to_triton_metadata(module)
    graph = metadata.to_compute_graph()
    compiled = compile_graph(
        graph,
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    readiness = runtime_execution_readiness_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
    )
    inputs = _inputs_for(source_name)
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    references = _references_for(source_name, inputs)
    correctness = build_runtime_reference_correctness_report(
        compiled.hac_ir.graph,
        execution,
        references,
    )
    if not correctness.passed:
        raise AssertionError("source-to-intent research source runtime smoke failed")
    source_bytes = source.encode("utf-8")
    parser_report = source_to_intent_research_parse_report_to_dict(result.report)
    source_intent_payload = _canonical_json(result.source_intent_payload)
    return {
        "backend_sequence": [
            assignment.backend_name for assignment in compiled.partition_plan.assignments
        ],
        "case_id": source_name,
        "compiler_decision_digest": _digest(compiled.dump_decision_report()),
        "execution_trace_digest": _digest(execution.trace.dump()),
        "hac_ir_digest": _digest(compiled.dump(IRStage.HAC_IR)),
        "metadata_intake_digest": _digest(metadata.intake_report().dump()),
        "metadata_report_digest": _digest(build_source_intent_metadata_report(module).dump()),
        "operation_families": list(result.report.operation_families),
        "parser_report_digest": _digest(_canonical_json(parser_report)),
        "plain_data_digest": _digest(source_intent_payload),
        "preflight_digest": _digest(preflight.dump()),
        "preflight_status": "accepted",
        "readiness_digest": _digest(readiness.dump()),
        "reference_correctness_digest": _digest(
            dump_runtime_reference_correctness_report(correctness)
        ),
        "runtime_plan_digest": _digest(compiled.dump_runtime_plan()),
        "source_digest": f"sha256:{sha256(source_bytes).hexdigest()}",
        "terminal_outputs": sorted(references),
        "trace_step_count": len(execution.trace.steps),
    }


def _tensor_shapes_for(source_name: str) -> dict[str, tuple[int, ...]]:
    if source_name == "research_matmul_elementwise":
        return {"a": (4, 8), "b": (8, 2), "y": (4, 2)}
    if source_name == "research_softmax_reduction":
        return {"x": (4, 8), "y": (4,)}
    raise ValueError("unsupported source-to-intent research smoke source")


def _assert_source_runtime_smoke_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("source-to-intent research source runtime smoke case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_SUMMARIES:
        raise ValueError("source-to-intent research source runtime smoke case id drift")
    expected = _EXPECTED_CASE_SUMMARIES[case_id]
    if case["backend_sequence"] != expected["backend_sequence"]:
        raise ValueError("source-to-intent research source runtime smoke backend drift")
    if case["operation_families"] != expected["operation_families"]:
        raise ValueError("source-to-intent research source runtime smoke family drift")
    if case["terminal_outputs"] != expected["terminal_outputs"]:
        raise ValueError("source-to-intent research source runtime smoke output drift")
    if case["preflight_status"] != "accepted":
        raise ValueError("source-to-intent research source runtime smoke preflight drift")
    if case["trace_step_count"] != 2:
        raise ValueError("source-to-intent research source runtime smoke trace drift")
    for key in _DIGEST_KEYS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("source-to-intent research source runtime smoke digest drift")
    return case_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research source runtime smoke {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = _canonical_json(report)
    except TypeError as exc:
        raise ValueError(
            "source-to-intent research source runtime smoke report is not JSON data"
        ) from exc
    for fragment in SOURCE_TO_INTENT_RESEARCH_SOURCE_RUNTIME_SMOKE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research source runtime smoke report contains "
                "forbidden source or value material"
            )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
