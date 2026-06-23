"""Index standard runtime evidence bundles for Kernel Ingress research cases."""

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
    from examples.source_to_intent_research_kernel_ingress import (
        _MODULE_CASES,
        _tensor_shapes_for,
        ingest_triton_module_source_to_source_intent,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_runtime_matrix_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT,
        assert_kernel_ingress_runtime_step_trace_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
        build_report as build_runtime_step_trace_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        _inputs_for,
        _references_for,
    )
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        _MODULE_CASES,
        _tensor_shapes_for,
        ingest_triton_module_source_to_source_intent,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_runtime_matrix_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_step_trace import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT,
        assert_kernel_ingress_runtime_step_trace_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_step_trace import (
        build_report as build_runtime_step_trace_report,
    )

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.runtime import (
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    assert_runtime_execution_evidence_bundle,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_receipt_report,
    build_runtime_input_manifest_report,
    build_runtime_output_contract_report,
    build_runtime_output_manifest_report,
    build_runtime_public_output_bundle,
    build_runtime_reference_correctness_report,
    build_runtime_tensor_store_evidence_report,
    dump_runtime_execution_evidence_bundle_report,
    dump_runtime_reference_correctness_report,
    execute_graph,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT = (
    "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index.review.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_ARTIFACT_POLICY = (
    "digest_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_SOURCE_BOUNDARY = (
    "kernel_ingress_runtime_to_standard_execution_evidence_bundle_index"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
    "raw_source_text",
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
    "tensor_value",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "blocked_execution_surfaces",
        "case_count",
        "cases",
        "default_parser_status",
        "executor_contract",
        "frontend_ingress_contract",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "runtime_evidence_bundle_contract",
        "runtime_evidence_bundle_index_contract",
        "runtime_evidence_sections",
        "runtime_matrix_contract",
        "runtime_matrix_digest",
        "runtime_step_trace_contract",
        "runtime_step_trace_digest",
        "schema_version",
        "source_boundary",
        "status",
        "trusted_executor_registry",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "bundle_metadata_digest",
        "bundle_report_digest",
        "case_id",
        "execution_receipt_digest",
        "execution_receipt_link_count",
        "execution_trace_digest",
        "graph_name",
        "input_count",
        "input_manifest_digest",
        "kernel_name",
        "operation_path",
        "output_count",
        "output_manifest_digest",
        "passed",
        "raw_value_policy",
        "reference_comparison_count",
        "reference_correctness_digest",
        "runtime_plan_digest",
        "standard_bundle_sections",
        "status",
        "step_count",
        "tensor_store_digest",
        "tensor_store_record_count",
        "terminal_outputs",
    }
)
_EXPECTED_CASES = {
    "research_module_matmul_elementwise": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "graph_name": "research_matmul_elementwise",
        "kernel_name": "matmul_elementwise",
        "operation_path": ["matmul", "elementwise"],
        "step_count": 2,
        "terminal_outputs": ["activated"],
    },
    "research_module_softmax_reduction": {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "graph_name": "research_softmax_reduction",
        "kernel_name": "softmax_reduction",
        "operation_path": ["softmax", "reduction"],
        "step_count": 2,
        "terminal_outputs": ["row_sum"],
    },
    "research_module_matmul_reduction": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "graph_name": "research_matmul_reduction",
        "kernel_name": "matmul_reduction",
        "operation_path": ["matmul", "reduction"],
        "step_count": 2,
        "terminal_outputs": ["column_sum"],
    },
    "research_module_mvp_pipeline": {
        "backend_sequence": ["linear-sim", "vector-sim", "vector-sim", "vector-sim"],
        "graph_name": "research_mvp_pipeline",
        "kernel_name": "mvp_pipeline",
        "operation_path": ["matmul", "softmax", "reduction", "elementwise"],
        "step_count": 4,
        "terminal_outputs": ["stable"],
    },
}
_DIGEST_KEYS = (
    "bundle_metadata_digest",
    "bundle_report_digest",
    "execution_receipt_digest",
    "execution_trace_digest",
    "input_manifest_digest",
    "output_manifest_digest",
    "reference_correctness_digest",
    "runtime_plan_digest",
    "tensor_store_digest",
)


def build_kernel_ingress_runtime_evidence_bundle_index_report() -> dict[str, object]:
    """Return source-free digest bindings for standard runtime evidence bundles."""

    runtime_matrix_text = build_runtime_matrix_report()
    runtime_matrix = json.loads(runtime_matrix_text)
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    runtime_step_trace_text = build_runtime_step_trace_report()
    runtime_step_trace = json.loads(runtime_step_trace_text)
    assert_kernel_ingress_runtime_step_trace_report_contract(runtime_step_trace)
    cases = [
        _build_case(
            case_id,
            source_name,
            kernel_name,
            module_source,
            _case_by_id(runtime_matrix, case_id),
            _case_by_id(runtime_step_trace, case_id),
        )
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
    ]
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(cases),
        "cases": cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "runtime_evidence_bundle_contract": RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
        "runtime_evidence_bundle_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT
        ),
        "runtime_evidence_sections": list(RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS),
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "runtime_step_trace_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
        ),
        "runtime_step_trace_digest": _digest(runtime_step_trace_text),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Kernel Ingress runtime bundle index."""

    return json.dumps(
        build_kernel_ingress_runtime_evidence_bundle_index_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(
    report: object,
) -> None:
    """Fail closed unless the Kernel Ingress runtime bundle index matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress runtime evidence bundle index must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(_EXPECTED_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "runtime_evidence_bundle_contract": RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
        "runtime_evidence_bundle_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT
        ),
        "runtime_evidence_sections": list(RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS),
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_step_trace_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress runtime evidence bundle index {key} drift")
    for key in ("runtime_matrix_digest", "runtime_step_trace_digest"):
        _assert_digest(report[key])
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime evidence bundle index cases drift")
    observed_case_ids = []
    for case in cases:
        observed_case_ids.append(_assert_case_contract(case))
    if tuple(observed_case_ids) != tuple(_EXPECTED_CASES):
        raise ValueError("kernel ingress runtime evidence bundle index case order drift")
    _assert_report_is_source_free(report)


def _build_case(
    case_id: str,
    source_name: str,
    kernel_name: str,
    module_source: str,
    matrix_case: Mapping[object, object],
    step_trace_case: Mapping[object, object],
) -> dict[str, object]:
    ingress = ingest_triton_module_source_to_source_intent(
        module_source,
        source_name=source_name,
        kernel_name=kernel_name,
        tensor_shapes=_tensor_shapes_for(source_name),
    )
    module = source_intent_from_mapping(ingress.parser_result.source_intent_payload)
    graph = source_intent_to_triton_metadata(module).to_compute_graph()
    compiled = compile_graph(
        graph,
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    inputs = _inputs_for(source_name)
    execution = execute_graph(compiled.hac_ir.graph, compiled.partition_plan, inputs)
    correctness = build_runtime_reference_correctness_report(
        compiled.hac_ir.graph,
        execution,
        _references_for(source_name, inputs),
    )
    tensor_store = build_runtime_tensor_store_evidence_report(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        execution,
    )
    input_manifest = build_runtime_input_manifest_report(
        compiled.hac_ir.graph,
        execution,
    )
    output_manifest = build_runtime_output_manifest_report(
        compiled.hac_ir.graph,
        execution,
    )
    output_contract = build_runtime_output_contract_report(
        compiled.hac_ir.graph,
        execution,
        {f"public_{output.tensor_name}": output.tensor_name for output in output_manifest.outputs},
    )
    public_output_bundle = build_runtime_public_output_bundle(
        execution,
        output_contract,
    )
    receipt = build_runtime_execution_receipt_report(
        execution,
        tensor_store,
        input_manifest,
        output_manifest,
        output_contract,
        public_output_bundle,
        correctness,
    )
    bundle = assert_runtime_execution_evidence_bundle(
        build_runtime_execution_evidence_bundle_report(
            tensor_store,
            input_manifest,
            output_manifest,
            output_contract,
            public_output_bundle,
            correctness,
            receipt,
        )
    )
    runtime_plan_digest = _digest(compiled.dump_runtime_plan())
    execution_trace_digest = _digest(execution.trace.dump())
    reference_correctness_digest = _digest(
        dump_runtime_reference_correctness_report(correctness)
    )
    _assert_bound_digest(
        runtime_plan_digest,
        matrix_case["runtime_plan_digest"],
        step_trace_case["runtime_plan_digest"],
    )
    _assert_bound_digest(
        execution_trace_digest,
        matrix_case["execution_trace_digest"],
        step_trace_case["execution_trace_digest"],
    )
    if reference_correctness_digest != matrix_case["reference_correctness_digest"]:
        raise ValueError("kernel ingress runtime bundle reference digest drift")
    return {
        "backend_sequence": list(step_trace_case["backend_sequence"]),
        "bundle_metadata_digest": bundle.bundle_metadata_digest,
        "bundle_report_digest": _digest(
            dump_runtime_execution_evidence_bundle_report(bundle)
        ),
        "case_id": case_id,
        "execution_receipt_digest": receipt.receipt_metadata_digest,
        "execution_receipt_link_count": len(receipt.evidence_links),
        "execution_trace_digest": execution_trace_digest,
        "graph_name": bundle.graph_name,
        "input_count": len(input_manifest.inputs),
        "input_manifest_digest": input_manifest.input_metadata_digest,
        "kernel_name": kernel_name,
        "operation_path": list(step_trace_case["operation_path"]),
        "output_count": len(output_manifest.outputs),
        "output_manifest_digest": output_manifest.output_metadata_digest,
        "passed": bundle.passed,
        "raw_value_policy": bundle.raw_value_policy,
        "reference_comparison_count": len(correctness.comparisons),
        "reference_correctness_digest": reference_correctness_digest,
        "runtime_plan_digest": runtime_plan_digest,
        "standard_bundle_sections": list(bundle.report_sections),
        "status": "standard_runtime_evidence_bound",
        "step_count": len(execution.trace.steps),
        "tensor_store_digest": tensor_store.record_metadata_digest,
        "tensor_store_record_count": len(tensor_store.records),
        "terminal_outputs": list(step_trace_case["terminal_outputs"]),
    }


def _case_by_id(report: Mapping[object, object], case_id: str) -> Mapping[object, object]:
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime evidence bundle source cases drift")
    matches = [
        case
        for case in cases
        if isinstance(case, Mapping) and case.get("case_id") == case_id
    ]
    if len(matches) != 1:
        raise ValueError("kernel ingress runtime evidence bundle source case drift")
    return matches[0]


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress runtime evidence bundle case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASES:
        raise ValueError("kernel ingress runtime evidence bundle case id drift")
    expected = _EXPECTED_CASES[case_id]
    for key, expected_value in expected.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress runtime evidence bundle {key} drift")
    expected_counts = {
        "execution_receipt_link_count": 6,
        "output_count": 1,
        "passed": True,
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "reference_comparison_count": 1,
        "standard_bundle_sections": list(RUNTIME_EXECUTION_EVIDENCE_BUNDLE_SECTIONS),
        "status": "standard_runtime_evidence_bound",
    }
    for key, expected_value in expected_counts.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress runtime evidence bundle {key} drift")
    if case["input_count"] not in (1, 2):
        raise ValueError("kernel ingress runtime evidence bundle input count drift")
    if case["tensor_store_record_count"] < case["step_count"]:
        raise ValueError("kernel ingress runtime evidence bundle record count drift")
    for key in _DIGEST_KEYS:
        _assert_digest(case[key])
    return case_id


def _assert_bound_digest(actual: str, matrix_value: object, trace_value: object) -> None:
    if actual != matrix_value or actual != trace_value:
        raise ValueError("kernel ingress runtime evidence bundle digest binding drift")


def _assert_digest(value: object) -> None:
    if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
        raise ValueError("kernel ingress runtime evidence bundle digest drift")


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress runtime evidence bundle {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "kernel ingress runtime evidence bundle report is not JSON"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress runtime evidence bundle contains forbidden material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
