"""Emit source-free runtime step traces for Kernel Ingress research cases."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_execution_bridge import _inputs_for
    from examples.source_to_intent_research_kernel_ingress import (
        _MODULE_CASES,
        _tensor_shapes_for,
        ingest_triton_module_source_to_source_intent,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_runtime_matrix_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_execution_bridge import _inputs_for  # type: ignore[no-redef]
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        _MODULE_CASES,
        _tensor_shapes_for,
        ingest_triton_module_source_to_source_intent,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_runtime_matrix_report,
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
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    execute_graph,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_runtime_step_trace_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_runtime_step_trace.execution.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_SOURCE_BOUNDARY = (
    "kernel_ingress_runtime_execution_trace_metadata"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
    "raw_source_text",
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
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
        "kernel_ingress_digest",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "runtime_matrix_contract",
        "runtime_matrix_digest",
        "runtime_step_trace_contract",
        "schema_version",
        "source_boundary",
        "status",
        "trusted_executor_registry",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "case_id",
        "execution_trace_digest",
        "kernel_name",
        "operation_path",
        "runtime_plan_digest",
        "status",
        "step_count",
        "steps",
        "terminal_outputs",
    }
)
_STEP_KEYS = frozenset(
    {
        "executor_backend",
        "input_tensors",
        "operation_kind",
        "operation_name",
        "output_dtypes",
        "output_shapes",
        "output_tensors",
        "planned_backend",
        "status",
        "step_index",
    }
)
_EXPECTED_CASES = {
    "research_module_matmul_elementwise": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "kernel_name": "matmul_elementwise",
        "operation_path": ["matmul", "elementwise"],
        "step_names": ["projection", "activated"],
        "terminal_outputs": ["activated"],
    },
    "research_module_softmax_reduction": {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "kernel_name": "softmax_reduction",
        "operation_path": ["softmax", "reduction"],
        "step_names": ["normalized", "row_sum"],
        "terminal_outputs": ["row_sum"],
    },
    "research_module_matmul_reduction": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "kernel_name": "matmul_reduction",
        "operation_path": ["matmul", "reduction"],
        "step_names": ["projection", "column_sum"],
        "terminal_outputs": ["column_sum"],
    },
    "research_module_mvp_pipeline": {
        "backend_sequence": ["linear-sim", "vector-sim", "vector-sim", "vector-sim"],
        "kernel_name": "mvp_pipeline",
        "operation_path": ["matmul", "softmax", "reduction", "elementwise"],
        "step_names": ["projection", "normalized", "row_sum", "stable"],
        "terminal_outputs": ["stable"],
    },
}


def build_kernel_ingress_runtime_step_trace_report() -> dict[str, object]:
    """Return source-free runtime step traces for accepted Kernel Ingress cases."""

    kernel_ingress_text = build_kernel_ingress_report()
    kernel_ingress = json.loads(kernel_ingress_text)
    runtime_matrix_text = build_runtime_matrix_report()
    runtime_matrix = json.loads(runtime_matrix_text)
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    cases = [
        _build_case_trace(
            case_id,
            source_name,
            kernel_name,
            module_source,
            _case_by_id(kernel_ingress, case_id),
            _case_by_id(runtime_matrix, case_id),
        )
        for case_id, source_name, kernel_name, module_source in _MODULE_CASES
    ]
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(cases),
        "cases": cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "runtime_step_trace_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    assert_kernel_ingress_runtime_step_trace_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress runtime step traces."""

    return json.dumps(
        build_kernel_ingress_runtime_step_trace_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_runtime_step_trace_report_contract(
    report: object,
) -> None:
    """Fail closed unless the runtime step trace report matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress runtime step trace report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "case_count": len(_EXPECTED_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_step_trace_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_CONTRACT
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress runtime step trace {key} drift")
    for key in ("kernel_ingress_digest", "runtime_matrix_digest"):
        value = report[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress runtime step trace digest drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime step trace cases drift")
    observed_case_ids = []
    for case in cases:
        observed_case_ids.append(_assert_case_contract(case))
    if tuple(observed_case_ids) != tuple(_EXPECTED_CASES):
        raise ValueError("kernel ingress runtime step trace case order drift")
    _assert_report_is_source_free(report)


def _build_case_trace(
    case_id: str,
    source_name: str,
    kernel_name: str,
    module_source: str,
    ingress_case: Mapping[object, object],
    matrix_case: Mapping[object, object],
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
    execution = execute_graph(
        compiled.hac_ir.graph,
        compiled.partition_plan,
        _inputs_for(source_name),
    )
    steps = [_step_to_dict(index, step) for index, step in enumerate(execution.trace.steps)]
    operation_path = [str(step["operation_kind"]) for step in steps]
    backend_sequence = [str(step["planned_backend"]) for step in steps]
    trace_digest = _digest(execution.trace.dump())
    runtime_plan_digest = _digest(compiled.dump_runtime_plan())
    if trace_digest != ingress_case["execution_trace_digest"]:
        raise ValueError("kernel ingress runtime step trace execution digest drift")
    if runtime_plan_digest != ingress_case["runtime_plan_digest"]:
        raise ValueError("kernel ingress runtime step trace runtime plan digest drift")
    if trace_digest != matrix_case["execution_trace_digest"]:
        raise ValueError("kernel ingress runtime step trace matrix trace drift")
    if runtime_plan_digest != matrix_case["runtime_plan_digest"]:
        raise ValueError("kernel ingress runtime step trace matrix plan drift")
    return {
        "backend_sequence": backend_sequence,
        "case_id": case_id,
        "execution_trace_digest": trace_digest,
        "kernel_name": kernel_name,
        "operation_path": operation_path,
        "runtime_plan_digest": runtime_plan_digest,
        "status": "traced",
        "step_count": len(steps),
        "steps": steps,
        "terminal_outputs": list(matrix_case["terminal_outputs"]),
    }


def _step_to_dict(index: int, step: object) -> dict[str, object]:
    return {
        "executor_backend": str(step.executor_backend),
        "input_tensors": list(step.input_tensors),
        "operation_kind": step.operation_kind.value,
        "operation_name": str(step.operation_name),
        "output_dtypes": list(step.output_dtypes),
        "output_shapes": [list(shape) for shape in step.output_shapes],
        "output_tensors": list(step.output_tensors),
        "planned_backend": str(step.planned_backend),
        "status": str(step.status),
        "step_index": index,
    }


def _case_by_id(report: Mapping[object, object], case_id: str) -> Mapping[object, object]:
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime step trace source cases drift")
    matches = [
        case
        for case in cases
        if isinstance(case, Mapping) and case.get("case_id") == case_id
    ]
    if len(matches) != 1:
        raise ValueError("kernel ingress runtime step trace source case drift")
    return matches[0]


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress runtime step trace case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASES:
        raise ValueError("kernel ingress runtime step trace case id drift")
    expected = _EXPECTED_CASES[case_id]
    for key in ("backend_sequence", "kernel_name", "operation_path", "terminal_outputs"):
        if case[key] != expected[key]:
            raise ValueError(f"kernel ingress runtime step trace {key} drift")
    if case["step_count"] != len(expected["step_names"]):
        raise ValueError("kernel ingress runtime step trace step count drift")
    if case["status"] != "traced":
        raise ValueError("kernel ingress runtime step trace case status drift")
    for key in ("execution_trace_digest", "runtime_plan_digest"):
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress runtime step trace digest drift")
    steps = case["steps"]
    if not isinstance(steps, list):
        raise ValueError("kernel ingress runtime step trace steps drift")
    observed_step_names = []
    for index, step in enumerate(steps):
        observed_step_names.append(_assert_step_contract(index, step))
    if observed_step_names != expected["step_names"]:
        raise ValueError("kernel ingress runtime step trace operation name drift")
    return case_id


def _assert_step_contract(index: int, step: object) -> str:
    if not isinstance(step, Mapping):
        raise ValueError("kernel ingress runtime step trace step must be object")
    _assert_exact_keys("step", step, _STEP_KEYS)
    if step["step_index"] != index:
        raise ValueError("kernel ingress runtime step trace step index drift")
    if step["planned_backend"] != step["executor_backend"]:
        raise ValueError("kernel ingress runtime step trace backend mismatch")
    if step["status"] != "executed":
        raise ValueError("kernel ingress runtime step trace step status drift")
    for key in (
        "executor_backend",
        "operation_kind",
        "operation_name",
        "planned_backend",
        "status",
    ):
        if not isinstance(step[key], str):
            raise ValueError(f"kernel ingress runtime step trace {key} drift")
    for key in ("input_tensors", "output_dtypes", "output_shapes", "output_tensors"):
        if not isinstance(step[key], list):
            raise ValueError(f"kernel ingress runtime step trace {key} drift")
    return str(step["operation_name"])


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress runtime step trace {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("kernel ingress runtime step trace report is not JSON") from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress runtime step trace contains forbidden source or value"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
