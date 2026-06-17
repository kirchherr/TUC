"""Run realistic Triton module-source ingress through controlled runtime proof."""

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
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        _inputs_for,
        _references_for,
    )

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    build_source_intent_metadata_report,
    dump_source_to_intent_research_kernel_ingress_report,
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.ir import IRStage
from tuc.runtime import (
    build_runtime_reference_correctness_report,
    dump_runtime_reference_correctness_report,
    execute_graph,
    runtime_execution_readiness_report,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_e2e_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT = (
    "source_to_intent_research_kernel_ingress.e2e.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_SOURCE_BOUNDARY = (
    "triton_module_source_buffer_to_runtime_via_research_kernel_ingress"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    "python_source",
    "raw_source_text",
    "raw_tensor_value",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE = """import triton
import triton.language as tl

@triton.jit
def matmul_elementwise(a, b, y):
    projection = tl.dot(a, b)
    activated = tl.where(projection > 0.0, projection, 0.0)
    tl.store(y, activated)
"""

REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE = """import triton
import triton.language as tl

@triton.jit
def softmax_reduction(x, y):
    normalized = tl.softmax(x, axis=1)
    row_sum = tl.sum(normalized, axis=1)
    tl.store(y, row_sum)
"""

REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE = """import triton
import triton.language as tl

@triton.jit
def matmul_reduction(a, b, y):
    projection = tl.dot(a, b)
    column_sum = tl.sum(projection, axis=1)
    tl.store(y, column_sum)
"""

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "blocked_claims",
        "case_count",
        "cases",
        "default_parser_status",
        "e2e_contract",
        "frontend_ingress_contract",
        "input_policy",
        "output_policy",
        "parser_output_policy",
        "parser_status",
        "raw_source_policy",
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
        "compiler_decision_digest",
        "execution_trace_digest",
        "extracted_kernel_digest",
        "hac_ir_digest",
        "ingress_report_digest",
        "kernel_name",
        "metadata_intake_digest",
        "metadata_report_digest",
        "module_digest",
        "operation_families",
        "parser_report_digest",
        "plain_data_digest",
        "readiness_digest",
        "reference_correctness_digest",
        "runtime_plan_digest",
        "source_intent_digest",
        "terminal_outputs",
        "trace_step_count",
    }
)
_DIGEST_KEYS = (
    "compiler_decision_digest",
    "execution_trace_digest",
    "extracted_kernel_digest",
    "hac_ir_digest",
    "ingress_report_digest",
    "metadata_intake_digest",
    "metadata_report_digest",
    "module_digest",
    "parser_report_digest",
    "plain_data_digest",
    "readiness_digest",
    "reference_correctness_digest",
    "runtime_plan_digest",
    "source_intent_digest",
)
_MODULE_CASES = (
    (
        "research_module_matmul_elementwise",
        "research_matmul_elementwise",
        "matmul_elementwise",
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
    ),
    (
        "research_module_softmax_reduction",
        "research_softmax_reduction",
        "softmax_reduction",
        REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE,
    ),
    (
        "research_module_matmul_reduction",
        "research_matmul_reduction",
        "matmul_reduction",
        REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
    ),
)
_EXPECTED_CASE_SUMMARIES = {
    "research_module_matmul_elementwise": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "operation_families": ["elementwise", "matmul"],
        "terminal_outputs": ["activated"],
    },
    "research_module_softmax_reduction": {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "operation_families": ["reduction", "softmax"],
        "terminal_outputs": ["row_sum"],
    },
    "research_module_matmul_reduction": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "operation_families": ["matmul", "reduction"],
        "terminal_outputs": ["column_sum"],
    },
}


def build_kernel_ingress_report() -> dict[str, object]:
    """Return metadata-only evidence for module-source to runtime execution."""

    cases = [
        _build_case(case_id, source_name, kernel_name, module_source)
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
    ]
    report: dict[str, object] = {
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS),
        "case_count": len(cases),
        "cases": cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "e2e_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
        "output_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    assert_kernel_ingress_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the kernel-ingress runtime path."""

    return json.dumps(build_kernel_ingress_report(), indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_report_contract(report: object) -> None:
    """Fail closed unless the kernel-ingress e2e report matches the contract."""

    if not isinstance(report, Mapping):
        raise ValueError("source-to-intent research kernel ingress report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_ARTIFACT_POLICY,
        "blocked_claims": list(SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS),
        "case_count": len(_MODULE_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "e2e_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
        "output_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
        "parser_output_policy": SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_REPORT_SCHEMA_VERSION,
        "source_boundary": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_SOURCE_BOUNDARY,
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"source-to-intent research kernel ingress {key} drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("source-to-intent research kernel ingress cases drift")
    case_ids = []
    for case in cases:
        case_ids.append(_assert_case_contract(case))
    if tuple(case_ids) != tuple(case[0] for case in _MODULE_CASES):
        raise ValueError("source-to-intent research kernel ingress case order drift")
    _assert_report_is_metadata_only(report)


def _build_case(
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
        raise AssertionError("source-to-intent research kernel ingress failed")
    ingress_report_text = dump_source_to_intent_research_kernel_ingress_report(
        ingress.report
    )
    plain_data_text = _canonical_json(ingress.parser_result.source_intent_payload)
    return {
        "backend_sequence": [
            assignment.backend_name for assignment in compiled.partition_plan.assignments
        ],
        "case_id": case_id,
        "compiler_decision_digest": _digest(compiled.dump_decision_report()),
        "execution_trace_digest": _digest(execution.trace.dump()),
        "extracted_kernel_digest": ingress.report.extracted_kernel_digest,
        "hac_ir_digest": _digest(compiled.dump(IRStage.HAC_IR)),
        "ingress_report_digest": _digest(ingress_report_text),
        "kernel_name": kernel_name,
        "metadata_intake_digest": _digest(metadata.intake_report().dump()),
        "metadata_report_digest": _digest(build_source_intent_metadata_report(module).dump()),
        "module_digest": ingress.report.module_digest,
        "operation_families": list(ingress.report.operation_families),
        "parser_report_digest": ingress.report.parser_report_digest,
        "plain_data_digest": _digest(plain_data_text),
        "readiness_digest": _digest(readiness.dump()),
        "reference_correctness_digest": _digest(
            dump_runtime_reference_correctness_report(correctness)
        ),
        "runtime_plan_digest": _digest(compiled.dump_runtime_plan()),
        "source_intent_digest": ingress.report.source_intent_digest,
        "terminal_outputs": sorted(references),
        "trace_step_count": len(execution.trace.steps),
    }


def _tensor_shapes_for(source_name: str) -> dict[str, tuple[int, ...]]:
    if source_name == "research_matmul_elementwise":
        return {"a": (4, 8), "b": (8, 2), "y": (4, 2)}
    if source_name == "research_softmax_reduction":
        return {"x": (4, 8), "y": (4,)}
    if source_name == "research_matmul_reduction":
        return {"a": (4, 8), "b": (8, 2), "y": (4,)}
    raise ValueError("unsupported source-to-intent research kernel ingress source")


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("source-to-intent research kernel ingress case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_SUMMARIES:
        raise ValueError("source-to-intent research kernel ingress case id drift")
    expected = _EXPECTED_CASE_SUMMARIES[case_id]
    if case["backend_sequence"] != expected["backend_sequence"]:
        raise ValueError("source-to-intent research kernel ingress backend drift")
    if case["operation_families"] != expected["operation_families"]:
        raise ValueError("source-to-intent research kernel ingress family drift")
    if case["terminal_outputs"] != expected["terminal_outputs"]:
        raise ValueError("source-to-intent research kernel ingress output drift")
    if case["trace_step_count"] != 2:
        raise ValueError("source-to-intent research kernel ingress trace drift")
    if not isinstance(case["kernel_name"], str):
        raise ValueError("source-to-intent research kernel ingress kernel drift")
    for key in _DIGEST_KEYS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("source-to-intent research kernel ingress digest drift")
    return case_id


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source-to-intent research kernel ingress {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = _canonical_json(report)
    except TypeError as exc:
        raise ValueError("source-to-intent research kernel ingress report is not JSON") from exc
    for fragment in SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source-to-intent research kernel ingress report contains "
                "forbidden source or value material"
            )


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
