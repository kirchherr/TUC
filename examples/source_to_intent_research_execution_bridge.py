"""Execute accepted Source-to-Intent research parser output through normal gates."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

import numpy as np
from numpy.typing import NDArray

try:
    from examples.source_to_intent_research_parser_conformance_gate import (
        REQUIRED_PARSER_SOURCE_NAMES,
        build_source_to_intent_research_parser_results,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_parser_conformance_gate import (  # type: ignore[no-redef]
        REQUIRED_PARSER_SOURCE_NAMES,
        build_source_to_intent_research_parser_results,
    )

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchParseResult,
    build_source_intent_metadata_report,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
    source_to_intent_research_parse_report_to_dict,
)
from tuc.ir import IRStage
from tuc.reference import (
    reference_elementwise,
    reference_matmul,
    reference_reduction_sum,
    reference_softmax,
)
from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    build_runtime_reference_correctness_report,
    dump_runtime_reference_correctness_report,
    execute_graph,
    runtime_execution_readiness_report,
)

SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_execution_bridge_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT = (
    "source_to_intent_research_execution_bridge.explicit.v0"
)
SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_INPUT_POLICY = (
    "accepted_research_parser_results_only"
)
SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_SOURCE_BOUNDARY = (
    "source_intent.v0_plain_data_reintake"
)
SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_RAW_VALUE_POLICY = "omitted_by_policy"
SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_FORBIDDEN_FRAGMENTS = (
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
        "artifact_policy",
        "blocked_compiler_shortcuts",
        "blocked_execution_surfaces",
        "bridge_contract",
        "case_count",
        "cases",
        "default_parser_status",
        "input_policy",
        "parser_output_policy",
        "parser_sources",
        "parser_status",
        "raw_value_policy",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "case_id",
        "comparison_metadata_digest",
        "compiler_decision_digest",
        "execution_trace_digest",
        "hac_ir_digest",
        "metadata_intake_digest",
        "metadata_report_digest",
        "operation_count",
        "operation_families",
        "parser_report_digest",
        "plain_data_digest",
        "raw_value_policy",
        "readiness_digest",
        "reference_correctness_digest",
        "runtime_plan_digest",
        "terminal_outputs",
        "trace_step_count",
    }
)
_DIGEST_KEYS = (
    "comparison_metadata_digest",
    "compiler_decision_digest",
    "execution_trace_digest",
    "hac_ir_digest",
    "metadata_intake_digest",
    "metadata_report_digest",
    "parser_report_digest",
    "plain_data_digest",
    "readiness_digest",
    "reference_correctness_digest",
    "runtime_plan_digest",
)
_EXPECTED_CASE_SUMMARIES = {
    "research_matmul_elementwise": {
        "operation_families": ["elementwise", "matmul"],
        "terminal_outputs": ["activated"],
    },
    "research_softmax_reduction": {
        "operation_families": ["reduction", "softmax"],
        "terminal_outputs": ["row_sum"],
    },
}
_ALLOWED_BRIDGE_BACKENDS = frozenset({"linear-sim", "reference-cpu", "vector-sim"})

FloatArray = NDArray[np.float64]


def build_execution_bridge_report() -> dict[str, object]:
    """Return metadata-only execution evidence for accepted research parser output."""

    results = build_source_to_intent_research_parser_results()
    _assert_parser_results(results)
    cases = tuple(_build_case(result) for result in results)
    report: dict[str, object] = {
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_ARTIFACT_POLICY,
        "blocked_compiler_shortcuts": list(
            SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "bridge_contract": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
        "case_count": len(cases),
        "cases": list(cases),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_INPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_sources": list(REQUIRED_PARSER_SOURCE_NAMES),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_RAW_VALUE_POLICY,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    assert_execution_bridge_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the execution bridge."""

    return json.dumps(build_execution_bridge_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_execution_bridge_report_contract(report: object) -> None:
    """Fail closed unless the execution bridge report matches the v0 proof contract."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research execution bridge report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_ARTIFACT_POLICY,
        "bridge_contract": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_CONTRACT,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_INPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_RAW_VALUE_POLICY,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(
                "source-to-intent research execution bridge "
                f"{key} contract drift"
            )
    if report["blocked_compiler_shortcuts"] != list(
        SOURCE_TO_INTENT_RESEARCH_PARSER_BLOCKED_COMPILER_OUTPUTS
    ):
        raise ValueError(
            "source-to-intent research execution bridge compiler shortcut drift"
        )
    if report["blocked_execution_surfaces"] != list(
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    ):
        raise ValueError(
            "source-to-intent research execution bridge execution surface drift"
        )
    if report["parser_sources"] != list(REQUIRED_PARSER_SOURCE_NAMES):
        raise ValueError("source-to-intent research execution bridge source drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("source-to-intent research execution bridge cases drift")
    if report["case_count"] != len(cases) or len(cases) != len(REQUIRED_PARSER_SOURCE_NAMES):
        raise ValueError("source-to-intent research execution bridge case count drift")
    case_ids = []
    for case in cases:
        case_ids.append(_assert_execution_bridge_case_contract(case))
    if tuple(case_ids) != REQUIRED_PARSER_SOURCE_NAMES:
        raise ValueError("source-to-intent research execution bridge case order drift")
    _assert_report_is_metadata_only(report)


def _build_case(result: SourceToIntentResearchParseResult) -> dict[str, object]:
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
    inputs = _inputs_for(result.report.source_name)
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    references = _references_for(result.report.source_name, inputs)
    correctness = build_runtime_reference_correctness_report(
        compiled.hac_ir.graph,
        execution,
        references,
    )
    if not correctness.passed:
        raise AssertionError("source-to-intent research execution bridge failed")

    parser_report = source_to_intent_research_parse_report_to_dict(result.report)
    source_intent_payload = _canonical_json(result.source_intent_payload)
    return {
        "backend_sequence": [
            assignment.backend_name for assignment in compiled.partition_plan.assignments
        ],
        "case_id": result.report.source_name,
        "comparison_metadata_digest": correctness.comparison_metadata_digest,
        "compiler_decision_digest": _digest(compiled.dump_decision_report()),
        "execution_trace_digest": _digest(execution.trace.dump()),
        "hac_ir_digest": _digest(compiled.dump(IRStage.HAC_IR)),
        "metadata_intake_digest": _digest(metadata.intake_report().dump()),
        "metadata_report_digest": _digest(
            build_source_intent_metadata_report(module).dump()
        ),
        "operation_count": len(module.operations),
        "operation_families": list(result.report.operation_families),
        "parser_report_digest": _digest(_canonical_json(parser_report)),
        "raw_value_policy": correctness.raw_value_policy,
        "readiness_digest": _digest(readiness.dump()),
        "reference_correctness_digest": _digest(
            dump_runtime_reference_correctness_report(correctness)
        ),
        "runtime_plan_digest": _digest(compiled.dump_runtime_plan()),
        "plain_data_digest": _digest(source_intent_payload),
        "terminal_outputs": sorted(references),
        "trace_step_count": len(execution.trace.steps),
    }


def _assert_parser_results(
    results: tuple[SourceToIntentResearchParseResult, ...],
) -> None:
    if type(results) is not tuple:
        raise TypeError("source-to-intent research execution bridge results must be tuple")
    source_names = tuple(result.report.source_name for result in results)
    if source_names != REQUIRED_PARSER_SOURCE_NAMES:
        raise ValueError("source-to-intent research execution bridge source drift")
    for result in results:
        if result.report.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise ValueError("source-to-intent research execution parser status drift")
        if (
            result.report.default_parser_status
            != SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
        ):
            raise ValueError("source-to-intent research execution default status drift")
        if result.report.output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise ValueError("source-to-intent research execution output policy drift")


def _assert_execution_bridge_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("source-to-intent research execution bridge case must be object")
    _assert_exact_keys("execution bridge case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_SUMMARIES:
        raise ValueError("source-to-intent research execution bridge case id drift")
    expected = _EXPECTED_CASE_SUMMARIES[case_id]
    if case["operation_count"] != 2:
        raise ValueError("source-to-intent research execution bridge operation drift")
    if case["trace_step_count"] != 2:
        raise ValueError("source-to-intent research execution bridge trace drift")
    if case["raw_value_policy"] != SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_RAW_VALUE_POLICY:
        raise ValueError("source-to-intent research execution bridge raw value drift")
    if case["operation_families"] != expected["operation_families"]:
        raise ValueError("source-to-intent research execution bridge family drift")
    if case["terminal_outputs"] != expected["terminal_outputs"]:
        raise ValueError("source-to-intent research execution bridge output drift")
    backend_sequence = case["backend_sequence"]
    if (
        not isinstance(backend_sequence, list)
        or len(backend_sequence) < 2
        or any(backend not in _ALLOWED_BRIDGE_BACKENDS for backend in backend_sequence)
    ):
        raise ValueError("source-to-intent research execution bridge backend drift")
    for key in _DIGEST_KEYS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError(
                "source-to-intent research execution bridge digest drift"
            )
    return case_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research execution bridge {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = _canonical_json(report)
    except TypeError as exc:
        raise ValueError(
            "source-to-intent research execution bridge report is not JSON data"
        ) from exc
    for fragment in SOURCE_TO_INTENT_RESEARCH_EXECUTION_BRIDGE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research execution bridge report contains "
                "forbidden source or value material"
            )


def _inputs_for(source_name: str) -> dict[str, FloatArray]:
    if source_name == "research_matmul_elementwise":
        return {
            "a": np.array(
                [
                    [1.0, -2.0, 0.5, 3.0, 0.0, 1.5, -1.0, 2.0],
                    [0.0, 1.0, -1.0, 2.0, 3.0, -0.5, 1.5, -2.0],
                    [2.0, 0.5, 1.0, -1.5, 0.5, 2.5, -3.0, 1.0],
                    [-1.0, 2.0, 0.0, 1.0, -2.0, 1.0, 0.5, 3.0],
                ],
                dtype=np.float64,
            ),
            "b": np.array(
                [
                    [1.0, -1.0],
                    [2.0, 0.5],
                    [-1.0, 3.0],
                    [0.5, -2.0],
                    [1.5, 1.0],
                    [-0.5, 0.25],
                    [2.5, -1.5],
                    [0.0, 2.0],
                ],
                dtype=np.float64,
            ),
        }
    if source_name == "research_softmax_reduction":
        return {
            "x": np.array(
                [
                    [-3.0, -1.0, 0.0, 2.0, 1.0, 0.5, -0.5, 3.0],
                    [1.5, -2.5, 0.25, 0.75, -1.25, 2.25, -0.75, 1.0],
                    [0.0, 0.5, 1.0, 1.5, 2.0, -0.5, -1.0, -1.5],
                    [3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0, 0.5],
                ],
                dtype=np.float64,
            )
        }
    raise ValueError("unsupported source-to-intent research execution source")


def _references_for(
    source_name: str,
    inputs: dict[str, FloatArray],
) -> dict[str, FloatArray]:
    if source_name == "research_matmul_elementwise":
        projection = reference_matmul(inputs["a"], inputs["b"])
        return {"activated": reference_elementwise(projection)}
    if source_name == "research_softmax_reduction":
        normalized = reference_softmax(inputs["x"], axis=1)
        return {"row_sum": reference_reduction_sum(normalized, axis=1)}
    raise ValueError("unsupported source-to-intent research execution source")


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
