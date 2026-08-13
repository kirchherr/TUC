"""Prove Kernel Ingress cases preserve outputs across backend placements."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

from tuc.report_output import emit_public_json_report

try:
    from examples.source_to_intent_research_execution_bridge import (
        _inputs_for,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        _MODULE_CASES,
        _tensor_shapes_for,
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_execution_bridge import _inputs_for  # type: ignore[no-redef]
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        _MODULE_CASES,
        _tensor_shapes_for,
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )

from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.compiler import compile_graph
from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)
from tuc.runtime import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    assert_runtime_backend_equivalence,
    build_runtime_backend_equivalence_report,
    dump_runtime_backend_equivalence_report,
    execute_graph,
    runtime_backend_equivalence_report_to_dict,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_backend_equivalence_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_backend_equivalence.portability.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SOURCE_BOUNDARY = (
    "kernel_ingress_source_intent_to_reference_cpu_and_trusted_simulators"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CLAIM = (
    "same_source_intent_preserves_public_outputs_across_backend_placements"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = (
    "reference_cpu"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = (
    "capability_selected_simulators"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_FORBIDDEN_FRAGMENTS = (
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
        "baseline_backend_sequences",
        "blocked_execution_surfaces",
        "case_count",
        "cases",
        "candidate_backend_sequences",
        "comparison_count",
        "default_parser_status",
        "equivalence_claim",
        "equivalence_contract",
        "executor_contract",
        "frontend_ingress_contract",
        "kernel_ingress_backend_equivalence_contract",
        "kernel_ingress_digest",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "schema_version",
        "source_boundary",
        "status",
        "trusted_executor_registry",
        "trusted_runtime_backends",
    }
)
_CASE_KEYS = frozenset(
    {
        "baseline_backend_sequence",
        "baseline_run_id",
        "baseline_trace_step_count",
        "candidate_backend_sequence",
        "candidate_run_id",
        "candidate_trace_step_count",
        "case_id",
        "comparison_count",
        "comparison_metadata_digest",
        "equivalence_report_digest",
        "graph_name",
        "kernel_name",
        "operation_families",
        "passed",
        "raw_value_policy",
        "run_count",
        "status",
        "terminal_outputs",
    }
)
_DIGEST_KEYS = (
    "comparison_metadata_digest",
    "equivalence_report_digest",
)
_EXPECTED_CASES = {
    "research_module_matmul_elementwise": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["linear-sim", "vector-sim"],
        "graph_name": "research_matmul_elementwise",
        "kernel_name": "matmul_elementwise",
        "operation_families": ["elementwise", "matmul"],
        "terminal_outputs": ["activated"],
        "trace_step_count": 2,
    },
    "research_module_softmax_reduction": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["vector-sim", "vector-sim"],
        "graph_name": "research_softmax_reduction",
        "kernel_name": "softmax_reduction",
        "operation_families": ["reduction", "softmax"],
        "terminal_outputs": ["row_sum"],
        "trace_step_count": 2,
    },
    "research_module_matmul_reduction": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["linear-sim", "vector-sim"],
        "graph_name": "research_matmul_reduction",
        "kernel_name": "matmul_reduction",
        "operation_families": ["matmul", "reduction"],
        "terminal_outputs": ["column_sum"],
        "trace_step_count": 2,
    },
    "research_module_softmax_elementwise": {
        "baseline_backend_sequence": ["reference-cpu", "reference-cpu"],
        "candidate_backend_sequence": ["vector-sim", "vector-sim"],
        "graph_name": "research_softmax_elementwise",
        "kernel_name": "softmax_elementwise",
        "operation_families": ["elementwise", "softmax"],
        "terminal_outputs": ["activated"],
        "trace_step_count": 2,
    },
    "research_module_mvp_pipeline": {
        "baseline_backend_sequence": [
            "reference-cpu",
            "reference-cpu",
            "reference-cpu",
            "reference-cpu",
        ],
        "candidate_backend_sequence": [
            "linear-sim",
            "vector-sim",
            "vector-sim",
            "vector-sim",
        ],
        "graph_name": "research_mvp_pipeline",
        "kernel_name": "mvp_pipeline",
        "operation_families": ["elementwise", "matmul", "reduction", "softmax"],
        "terminal_outputs": ["stable"],
        "trace_step_count": 4,
    },
}


def build_kernel_ingress_backend_equivalence_report() -> dict[str, object]:
    """Return source-free backend equivalence evidence for Kernel Ingress cases."""

    kernel_ingress_text = build_kernel_ingress_report()
    kernel_ingress = json.loads(kernel_ingress_text)
    assert_kernel_ingress_report_contract(kernel_ingress)
    cases = [
        _build_case(case_id, source_name, kernel_name, module_source)
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
    ]
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_ARTIFACT_POLICY
        ),
        "baseline_backend_sequences": _unique_sequences(
            cases,
            "baseline_backend_sequence",
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(cases),
        "cases": cases,
        "candidate_backend_sequences": _unique_sequences(
            cases,
            "candidate_backend_sequence",
        ),
        "comparison_count": sum(_int_value(case, "comparison_count") for case in cases),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "equivalence_claim": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CLAIM
        ),
        "equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_backend_equivalence_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
        ),
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_runtime_backends": [
            "linear-sim",
            "reference-cpu",
            "vector-sim",
        ],
    }
    assert_kernel_ingress_backend_equivalence_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress backend equivalence."""

    return json.dumps(
        build_kernel_ingress_backend_equivalence_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    emit_public_json_report(build_report())


def assert_kernel_ingress_backend_equivalence_report_contract(
    report: object,
) -> None:
    """Fail closed unless Kernel Ingress backend equivalence matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress backend equivalence report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    kernel_ingress_text = build_kernel_ingress_report()
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_ARTIFACT_POLICY
        ),
        "baseline_backend_sequences": [
            "reference-cpu->reference-cpu",
            "reference-cpu->reference-cpu->reference-cpu->reference-cpu",
        ],
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(_EXPECTED_CASES),
        "candidate_backend_sequences": [
            "linear-sim->vector-sim",
            "vector-sim->vector-sim",
            "linear-sim->vector-sim->vector-sim->vector-sim",
        ],
        "comparison_count": len(_EXPECTED_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "equivalence_claim": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CLAIM
        ),
        "equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_backend_equivalence_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CONTRACT
        ),
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_runtime_backends": [
            "linear-sim",
            "reference-cpu",
            "vector-sim",
        ],
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress backend equivalence {key} drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress backend equivalence cases drift")
    observed_case_ids = []
    for case in cases:
        observed_case_ids.append(_assert_case_contract(case))
    if tuple(observed_case_ids) != tuple(_EXPECTED_CASES):
        raise ValueError("kernel ingress backend equivalence case order drift")
    _assert_report_is_source_free(report)


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
    baseline = compile_graph(graph, [])
    candidate = compile_graph(
        graph,
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    inputs = _inputs_for(source_name)
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    equivalence = assert_runtime_backend_equivalence(
        build_runtime_backend_equivalence_report(
            graph,
            baseline.partition_plan,
            baseline_execution,
            candidate.partition_plan,
            candidate_execution,
            baseline_run_id=(
                SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_BASELINE_RUN_ID
            ),
            candidate_run_id=(
                SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID
            ),
        )
    )
    equivalence_text = dump_runtime_backend_equivalence_report(equivalence)
    equivalence_report = runtime_backend_equivalence_report_to_dict(equivalence)
    return {
        "baseline_backend_sequence": _run_sequence(equivalence_report, 0),
        "baseline_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_BASELINE_RUN_ID
        ),
        "baseline_trace_step_count": _run_step_count(equivalence_report, 0),
        "candidate_backend_sequence": _run_sequence(equivalence_report, 1),
        "candidate_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID
        ),
        "candidate_trace_step_count": _run_step_count(equivalence_report, 1),
        "case_id": case_id,
        "comparison_count": int(equivalence_report["comparison_count"]),
        "comparison_metadata_digest": str(
            equivalence_report["comparison_metadata_digest"]
        ),
        "equivalence_report_digest": _digest(equivalence_text),
        "graph_name": str(equivalence_report["graph_name"]),
        "kernel_name": kernel_name,
        "operation_families": list(ingress.report.operation_families),
        "passed": bool(equivalence_report["passed"]),
        "raw_value_policy": str(equivalence_report["raw_value_policy"]),
        "run_count": int(equivalence_report["run_count"]),
        "status": "backend_equivalence_bound",
        "terminal_outputs": _comparison_outputs(equivalence_report),
    }


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress backend equivalence case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASES:
        raise ValueError("kernel ingress backend equivalence case id drift")
    expected = _EXPECTED_CASES[case_id]
    for key in (
        "baseline_backend_sequence",
        "candidate_backend_sequence",
        "graph_name",
        "kernel_name",
        "operation_families",
        "terminal_outputs",
    ):
        if case[key] != expected[key]:
            raise ValueError(f"kernel ingress backend equivalence {key} drift")
    expected_values = {
        "baseline_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_BASELINE_RUN_ID
        ),
        "baseline_trace_step_count": expected["trace_step_count"],
        "candidate_run_id": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID
        ),
        "candidate_trace_step_count": expected["trace_step_count"],
        "comparison_count": 1,
        "passed": True,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "run_count": 2,
        "status": "backend_equivalence_bound",
    }
    for key, expected_value in expected_values.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress backend equivalence {key} drift")
    for key in _DIGEST_KEYS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress backend equivalence digest drift")
    return case_id


def _run_sequence(report: Mapping[str, object], index: int) -> list[str]:
    runs = report["runs"]
    if not isinstance(runs, list) or not isinstance(runs[index], Mapping):
        raise ValueError("kernel ingress backend equivalence run drift")
    sequence = runs[index]["planned_backend_sequence"]
    if not isinstance(sequence, list):
        raise ValueError("kernel ingress backend equivalence run sequence drift")
    return [str(item) for item in sequence]


def _run_step_count(report: Mapping[str, object], index: int) -> int:
    runs = report["runs"]
    if not isinstance(runs, list) or not isinstance(runs[index], Mapping):
        raise ValueError("kernel ingress backend equivalence run drift")
    return int(runs[index]["trace_step_count"])


def _comparison_outputs(report: Mapping[str, object]) -> list[str]:
    comparisons = report["comparisons"]
    if not isinstance(comparisons, list):
        raise ValueError("kernel ingress backend equivalence comparison drift")
    outputs: list[str] = []
    for comparison in comparisons:
        if not isinstance(comparison, Mapping):
            raise ValueError("kernel ingress backend equivalence comparison drift")
        if comparison["comparison_status"] != "matched":
            raise ValueError("kernel ingress backend equivalence comparison failed")
        outputs.append(str(comparison["tensor_name"]))
    return outputs


def _unique_sequences(cases: list[dict[str, object]], key: str) -> list[str]:
    observed: list[str] = []
    for case in cases:
        sequence = case[key]
        if not isinstance(sequence, list):
            raise ValueError("kernel ingress backend equivalence sequence drift")
        rendered = "->".join(str(item) for item in sequence)
        if rendered not in observed:
            observed.append(rendered)
    return observed


def _int_value(payload: Mapping[str, object], key: str) -> int:
    value = payload[key]
    if not isinstance(value, int):
        raise ValueError("kernel ingress backend equivalence count drift")
    return value


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress backend equivalence {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("kernel ingress backend equivalence report is not JSON") from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress backend equivalence contains forbidden source "
                "or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
