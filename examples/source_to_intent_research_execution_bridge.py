"""Execute accepted Source-to-Intent research parser output through normal gates."""

from __future__ import annotations

import json
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

FloatArray = NDArray[np.float64]


def build_execution_bridge_report() -> dict[str, object]:
    """Return metadata-only execution evidence for accepted research parser output."""

    results = build_source_to_intent_research_parser_results()
    _assert_parser_results(results)
    cases = tuple(_build_case(result) for result in results)
    return {
        "artifact_policy": "metadata_only_values_omitted",
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


def build_report() -> str:
    """Return stable JSON evidence for the execution bridge."""

    return json.dumps(build_execution_bridge_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


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
