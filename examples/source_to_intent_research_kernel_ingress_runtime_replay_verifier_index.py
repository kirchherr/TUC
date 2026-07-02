"""Index Runtime Evidence Replay Verifier reports for Kernel Ingress cases."""

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
    from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT,
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        build_report as build_runtime_evidence_bundle_index_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_runtime_matrix_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_output_closure_index import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX_CONTRACT,
        assert_kernel_ingress_runtime_output_closure_index_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_output_closure_index import (
        build_report as build_runtime_output_closure_index_report,
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
    from source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT,
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        build_report as build_runtime_evidence_bundle_index_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_runtime_matrix_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_output_closure_index import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX_CONTRACT,
        assert_kernel_ingress_runtime_output_closure_index_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_output_closure_index import (
        build_report as build_runtime_output_closure_index_report,
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
    MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECKS,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION,
    RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS,
    RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
    RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    assert_runtime_evidence_replay_verifier,
    assert_runtime_execution_evidence_bundle,
    assert_runtime_execution_output_closure,
    build_runtime_evidence_replay_verifier_report,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_output_closure_report,
    build_runtime_execution_receipt_report,
    build_runtime_input_manifest_report,
    build_runtime_output_contract_report,
    build_runtime_output_manifest_report,
    build_runtime_public_output_bundle,
    build_runtime_reference_correctness_report,
    build_runtime_tensor_store_evidence_report,
    dump_runtime_evidence_replay_verifier_report,
    dump_runtime_execution_evidence_bundle_report,
    dump_runtime_execution_output_closure_report,
    execute_graph,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_runtime_replay_verifier_index_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_CONTRACT = (
    "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index.review.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_ARTIFACT_POLICY = (
    "digest_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_SOURCE_BOUNDARY = (
    "kernel_ingress_runtime_to_replay_verifier_index"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_FORBIDDEN_FRAGMENTS = (
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
        "input_policy",
        "output_closure_contract",
        "output_closure_index_contract",
        "output_closure_index_digest",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "reexecution_policy",
        "replay_required_inputs",
        "replay_verifier_contract",
        "replay_verifier_index_contract",
        "replay_verifier_replay_mode",
        "replay_verifier_schema_version",
        "runtime_evidence_bundle_contract",
        "runtime_evidence_bundle_index_contract",
        "runtime_evidence_bundle_index_digest",
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
        "graph_name",
        "kernel_name",
        "operation_path",
        "output_closure_metadata_digest",
        "output_closure_report_digest",
        "output_contract_metadata_digest",
        "passed",
        "public_output_bundle_digest",
        "raw_value_policy",
        "replay_check_count",
        "replay_contract",
        "replay_metadata_digest",
        "replay_mode",
        "replay_report_digest",
        "status",
        "step_count",
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
    "research_module_softmax_elementwise": {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "graph_name": "research_softmax_elementwise",
        "kernel_name": "softmax_elementwise",
        "operation_path": ["softmax", "elementwise"],
        "step_count": 2,
        "terminal_outputs": ["activated"],
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
    "output_closure_metadata_digest",
    "output_closure_report_digest",
    "output_contract_metadata_digest",
    "public_output_bundle_digest",
    "replay_metadata_digest",
    "replay_report_digest",
)


def build_kernel_ingress_runtime_replay_verifier_index_report() -> dict[str, object]:
    """Return source-free digest bindings for Kernel Ingress replay verification."""

    runtime_matrix_text = build_runtime_matrix_report()
    runtime_matrix = json.loads(runtime_matrix_text)
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    runtime_step_trace_text = build_runtime_step_trace_report()
    runtime_step_trace = json.loads(runtime_step_trace_text)
    assert_kernel_ingress_runtime_step_trace_report_contract(runtime_step_trace)
    runtime_evidence_bundle_index_text = build_runtime_evidence_bundle_index_report()
    runtime_evidence_bundle_index = json.loads(runtime_evidence_bundle_index_text)
    assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(
        runtime_evidence_bundle_index
    )
    runtime_output_closure_index_text = build_runtime_output_closure_index_report()
    runtime_output_closure_index = json.loads(runtime_output_closure_index_text)
    assert_kernel_ingress_runtime_output_closure_index_report_contract(
        runtime_output_closure_index
    )
    cases = [
        _build_case(
            case_id,
            source_name,
            kernel_name,
            module_source,
            _case_by_id(runtime_matrix, case_id),
            _case_by_id(runtime_step_trace, case_id),
            _case_by_id(runtime_evidence_bundle_index, case_id),
            _case_by_id(runtime_output_closure_index, case_id),
        )
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
    ]
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(cases),
        "cases": cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY,
        "output_closure_contract": RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT,
        "output_closure_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX_CONTRACT
        ),
        "output_closure_index_digest": _digest(runtime_output_closure_index_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "reexecution_policy": RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY,
        "replay_required_inputs": list(RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS),
        "replay_verifier_contract": RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT,
        "replay_verifier_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_CONTRACT
        ),
        "replay_verifier_replay_mode": RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE,
        "replay_verifier_schema_version": (
            RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
        ),
        "runtime_evidence_bundle_contract": RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
        "runtime_evidence_bundle_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT
        ),
        "runtime_evidence_bundle_index_digest": _digest(
            runtime_evidence_bundle_index_text
        ),
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "runtime_step_trace_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
        ),
        "runtime_step_trace_digest": _digest(runtime_step_trace_text),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    assert_kernel_ingress_runtime_replay_verifier_index_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Kernel Ingress replay verifier index."""

    return json.dumps(
        build_kernel_ingress_runtime_replay_verifier_index_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_runtime_replay_verifier_index_report_contract(
    report: object,
) -> None:
    """Fail closed unless the Kernel Ingress replay verifier index matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress runtime replay verifier index must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(_EXPECTED_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": RUNTIME_EVIDENCE_REPLAY_VERIFIER_INPUT_POLICY,
        "output_closure_contract": RUNTIME_EXECUTION_OUTPUT_CLOSURE_CONTRACT,
        "output_closure_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX_CONTRACT
        ),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "reexecution_policy": RUNTIME_EVIDENCE_REPLAY_VERIFIER_REEXECUTION_POLICY,
        "replay_required_inputs": list(RUNTIME_EVIDENCE_REPLAY_VERIFIER_REQUIRED_INPUTS),
        "replay_verifier_contract": RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT,
        "replay_verifier_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_CONTRACT
        ),
        "replay_verifier_replay_mode": RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE,
        "replay_verifier_schema_version": (
            RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPORT_SCHEMA_VERSION
        ),
        "runtime_evidence_bundle_contract": RUNTIME_EXECUTION_EVIDENCE_BUNDLE_CONTRACT,
        "runtime_evidence_bundle_index_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX_CONTRACT
        ),
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_step_trace_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress runtime replay verifier index {key} drift")
    for key in (
        "output_closure_index_digest",
        "runtime_evidence_bundle_index_digest",
        "runtime_matrix_digest",
        "runtime_step_trace_digest",
    ):
        _assert_digest(report[key])
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime replay verifier index cases drift")
    observed_case_ids = []
    for case in cases:
        observed_case_ids.append(_assert_case_contract(case))
    if tuple(observed_case_ids) != tuple(_EXPECTED_CASES):
        raise ValueError("kernel ingress runtime replay verifier index case order drift")
    _assert_report_is_source_free(report)


def _build_case(
    case_id: str,
    source_name: str,
    kernel_name: str,
    module_source: str,
    matrix_case: Mapping[object, object],
    step_trace_case: Mapping[object, object],
    evidence_bundle_case: Mapping[object, object],
    output_closure_case: Mapping[object, object],
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
        {
            f"public_{output.tensor_name}": output.tensor_name
            for output in output_manifest.outputs
        },
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
    closure = assert_runtime_execution_output_closure(
        build_runtime_execution_output_closure_report(
            output_contract,
            public_output_bundle,
            receipt,
            bundle,
        )
    )
    bundle_text = dump_runtime_execution_evidence_bundle_report(bundle)
    closure_text = dump_runtime_execution_output_closure_report(closure)
    replay = assert_runtime_evidence_replay_verifier(
        build_runtime_evidence_replay_verifier_report(bundle_text, closure_text)
    )
    replay_text = dump_runtime_evidence_replay_verifier_report(replay)
    _assert_bound_digest(
        _digest(compiled.dump_runtime_plan()),
        matrix_case["runtime_plan_digest"],
        step_trace_case["runtime_plan_digest"],
    )
    _assert_bound_digest(
        _digest(execution.trace.dump()),
        matrix_case["execution_trace_digest"],
        step_trace_case["execution_trace_digest"],
    )
    _assert_bound_digest(
        bundle.bundle_metadata_digest,
        evidence_bundle_case["bundle_metadata_digest"],
        output_closure_case["bundle_metadata_digest"],
    )
    _assert_bound_digest(
        replay.evidence_bundle_report_digest,
        evidence_bundle_case["bundle_report_digest"],
        output_closure_case["bundle_report_digest"],
    )
    _assert_bound_digest(
        receipt.receipt_metadata_digest,
        evidence_bundle_case["execution_receipt_digest"],
        output_closure_case["execution_receipt_digest"],
    )
    _assert_bound_digest(
        closure.closure_metadata_digest,
        output_closure_case["output_closure_metadata_digest"],
        replay.output_closure_metadata_digest,
    )
    _assert_bound_digest(
        replay.output_closure_report_digest,
        output_closure_case["output_closure_report_digest"],
        _digest(closure_text),
    )
    _assert_bound_digest(
        output_contract.contract_metadata_digest,
        output_closure_case["source_output_contract_digest"],
        replay.output_contract_metadata_digest,
    )
    _assert_bound_digest(
        public_output_bundle.bundle_metadata_digest,
        output_closure_case["public_output_bundle_digest"],
        replay.public_output_bundle_metadata_digest,
    )
    return {
        "backend_sequence": list(step_trace_case["backend_sequence"]),
        "bundle_metadata_digest": replay.evidence_bundle_metadata_digest,
        "bundle_report_digest": replay.evidence_bundle_report_digest,
        "case_id": case_id,
        "execution_receipt_digest": replay.execution_receipt_metadata_digest,
        "graph_name": replay.graph_name,
        "kernel_name": kernel_name,
        "operation_path": list(step_trace_case["operation_path"]),
        "output_closure_metadata_digest": replay.output_closure_metadata_digest,
        "output_closure_report_digest": replay.output_closure_report_digest,
        "output_contract_metadata_digest": replay.output_contract_metadata_digest,
        "passed": replay.passed,
        "public_output_bundle_digest": replay.public_output_bundle_metadata_digest,
        "raw_value_policy": replay.raw_value_policy,
        "replay_check_count": replay.check_count,
        "replay_contract": replay.replay_contract,
        "replay_metadata_digest": replay.replay_metadata_digest,
        "replay_mode": replay.replay_mode,
        "replay_report_digest": _digest(replay_text),
        "status": "runtime_replay_verifier_bound",
        "step_count": len(execution.trace.steps),
        "terminal_outputs": list(step_trace_case["terminal_outputs"]),
    }


def _case_by_id(report: Mapping[object, object], case_id: str) -> Mapping[object, object]:
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime replay verifier source cases drift")
    matches = [
        case
        for case in cases
        if isinstance(case, Mapping) and case.get("case_id") == case_id
    ]
    if len(matches) != 1:
        raise ValueError("kernel ingress runtime replay verifier source case drift")
    return matches[0]


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress runtime replay verifier case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASES:
        raise ValueError("kernel ingress runtime replay verifier case id drift")
    expected = _EXPECTED_CASES[case_id]
    for key, expected_value in expected.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress runtime replay verifier {key} drift")
    expected_counts = {
        "passed": True,
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "replay_check_count": MAX_RUNTIME_EVIDENCE_REPLAY_VERIFIER_CHECKS,
        "replay_contract": RUNTIME_EVIDENCE_REPLAY_VERIFIER_CONTRACT,
        "replay_mode": RUNTIME_EVIDENCE_REPLAY_VERIFIER_REPLAY_MODE,
        "status": "runtime_replay_verifier_bound",
    }
    for key, expected_value in expected_counts.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress runtime replay verifier {key} drift")
    for key in _DIGEST_KEYS:
        _assert_digest(case[key])
    return case_id


def _assert_bound_digest(actual: str, first_value: object, second_value: object) -> None:
    if actual != first_value or actual != second_value:
        raise ValueError("kernel ingress runtime replay verifier digest binding drift")


def _assert_digest(value: object) -> None:
    if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
        raise ValueError("kernel ingress runtime replay verifier digest drift")


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress runtime replay verifier {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "kernel ingress runtime replay verifier report is not JSON"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress runtime replay verifier contains forbidden material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
