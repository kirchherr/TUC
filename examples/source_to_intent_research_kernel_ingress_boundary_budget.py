"""Emit source-free boundary budget evidence for Kernel Ingress."""

from __future__ import annotations

import json
from collections.abc import Mapping

try:
    from examples.source_to_intent_research_kernel_ingress_conformance_gate import (
        build_source_to_intent_research_kernel_ingress_results,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress_conformance_gate import (  # type: ignore[no-redef]
        build_source_to_intent_research_kernel_ingress_results,
    )

from tuc.frontend import (
    MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASES,
    MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_MODULE_BYTES,
    MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_BYTES,
    MAX_TRITON_SOURCE_AST_DEPTH,
    MAX_TRITON_SOURCE_AST_NODES,
    MAX_TRITON_SOURCE_BYTES,
    MAX_TRITON_SOURCE_LINES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceToIntentResearchKernelIngressError,
    SourceToIntentResearchKernelIngressReport,
    ingest_triton_module_source_to_source_intent,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_boundary_budget_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT = (
    "source_to_intent_research_kernel_ingress_boundary_budget.security.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_POLICY = (
    "fail_closed_before_extraction_or_lowering"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_SOURCE_BOUNDARY = (
    "triton_module_source_buffer_as_untrusted_data"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    "python_source",
    '"module_source":',
    '"raw_source":',
    "raw_tensor_value",
    "secret.txt",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_case_count",
        "accepted_observations",
        "artifact_policy",
        "blocked_compiler_outputs",
        "blocked_execution_surfaces",
        "boundary_contract",
        "budget_policy",
        "budget_rejection_case_count",
        "budget_rejection_cases",
        "default_parser_status",
        "diagnostics_budget_limits",
        "diagnostics_contract",
        "frontend_ingress_contract",
        "ingress_budget_limits",
        "input_policy",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_OBSERVATION_KEYS = frozenset(
    {
        "case_id",
        "import_count",
        "kernel_name",
        "module_ast_depth",
        "module_ast_node_count",
        "module_bytes",
        "module_line_count",
        "operation_families",
        "source_name",
        "status",
        "top_level_function_count",
    }
)
_REJECTION_KEYS = frozenset(
    {"case_id", "limit", "observed", "reason_fragment", "status"}
)
_EXPECTED_SOURCE_NAMES = (
    "research_matmul_elementwise",
    "research_softmax_reduction",
    "research_matmul_reduction",
    "research_softmax_elementwise",
    "research_mvp_pipeline",
)
_EXPECTED_KERNEL_NAMES = (
    "matmul_elementwise",
    "softmax_reduction",
    "matmul_reduction",
    "softmax_elementwise",
    "mvp_pipeline",
)
_EXPECTED_REJECTION_CASES = {
    "module_byte_budget": {
        "limit": MAX_TRITON_SOURCE_BYTES,
        "observed": MAX_TRITON_SOURCE_BYTES + 1,
        "reason_fragment": "module source byte budget exceeded",
    },
    "module_line_budget": {
        "limit": MAX_TRITON_SOURCE_LINES,
        "observed": MAX_TRITON_SOURCE_LINES + 1,
        "reason_fragment": "module source line budget exceeded",
    },
}


def build_kernel_ingress_boundary_budget_report() -> dict[str, object]:
    """Return source-free budget evidence for Kernel Ingress."""

    accepted_results = build_source_to_intent_research_kernel_ingress_results()
    accepted_observations = [
        _build_observation(result.report) for result in accepted_results
    ]
    rejection_cases = [
        _build_budget_rejection_case(
            "module_byte_budget",
            "x" * (MAX_TRITON_SOURCE_BYTES + 1),
        ),
        _build_budget_rejection_case(
            "module_line_budget",
            "\n".join("x" for _ in range(MAX_TRITON_SOURCE_LINES + 1)),
        ),
    ]
    report: dict[str, object] = {
        "accepted_case_count": len(accepted_observations),
        "accepted_observations": accepted_observations,
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_ARTIFACT_POLICY
        ),
        "blocked_compiler_outputs": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ),
        "blocked_execution_surfaces": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ),
        "boundary_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT
        ),
        "budget_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_POLICY
        ),
        "budget_rejection_case_count": len(rejection_cases),
        "budget_rejection_cases": rejection_cases,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_budget_limits": {
            "case_count": MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASES,
            "module_bytes": (
                MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_MODULE_BYTES
            ),
            "report_bytes": (
                MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_BYTES
            ),
        },
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "ingress_budget_limits": {
            "module_ast_depth": MAX_TRITON_SOURCE_AST_DEPTH,
            "module_ast_nodes": MAX_TRITON_SOURCE_AST_NODES,
            "module_bytes": MAX_TRITON_SOURCE_BYTES,
            "module_lines": MAX_TRITON_SOURCE_LINES,
        },
        "input_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    assert_kernel_ingress_boundary_budget_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress boundary budgets."""

    return json.dumps(
        build_kernel_ingress_boundary_budget_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_boundary_budget_report_contract(report: object) -> None:
    """Fail closed unless the boundary budget report matches the v0 contract."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress boundary budget report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "accepted_case_count": len(_EXPECTED_SOURCE_NAMES),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_ARTIFACT_POLICY
        ),
        "blocked_compiler_outputs": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ),
        "blocked_execution_surfaces": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ),
        "boundary_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT
        ),
        "budget_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_POLICY
        ),
        "budget_rejection_case_count": len(_EXPECTED_REJECTION_CASES),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_budget_limits": {
            "case_count": MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CASES,
            "module_bytes": (
                MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_MODULE_BYTES
            ),
            "report_bytes": (
                MAX_SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_BYTES
            ),
        },
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "ingress_budget_limits": {
            "module_ast_depth": MAX_TRITON_SOURCE_AST_DEPTH,
            "module_ast_nodes": MAX_TRITON_SOURCE_AST_NODES,
            "module_bytes": MAX_TRITON_SOURCE_BYTES,
            "module_lines": MAX_TRITON_SOURCE_LINES,
        },
        "input_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress boundary budget {key} drift")
    _assert_observations(report["accepted_observations"])
    _assert_rejection_cases(report["budget_rejection_cases"])
    _assert_report_is_source_free(report)


def _build_observation(
    report: SourceToIntentResearchKernelIngressReport,
) -> dict[str, object]:
    source_name = report.source_name
    kernel_name = report.kernel_name
    return {
        "case_id": f"accepted_{source_name}",
        "import_count": report.import_count,
        "kernel_name": kernel_name,
        "module_ast_depth": report.module_ast_depth,
        "module_ast_node_count": report.module_ast_node_count,
        "module_bytes": report.module_bytes,
        "module_line_count": report.module_line_count,
        "operation_families": list(report.operation_families),
        "source_name": source_name,
        "status": "within_budget",
        "top_level_function_count": report.top_level_function_count,
    }


def _build_budget_rejection_case(case_id: str, module_source: str) -> dict[str, object]:
    expected = _EXPECTED_REJECTION_CASES[case_id]
    try:
        ingest_triton_module_source_to_source_intent(
            module_source,
            source_name="budget_rejection_case",
            kernel_name="budget_kernel",
            tensor_shapes={"x": (1,)},
        )
    except SourceToIntentResearchKernelIngressError as exc:
        if expected["reason_fragment"] not in str(exc):
            raise ValueError(
                "kernel ingress boundary budget rejection reason drift"
            ) from exc
    else:
        raise ValueError("kernel ingress boundary budget rejection unexpectedly passed")
    return {
        "case_id": case_id,
        "limit": expected["limit"],
        "observed": expected["observed"],
        "reason_fragment": expected["reason_fragment"],
        "status": "rejected",
    }


def _assert_observations(value: object) -> None:
    if not isinstance(value, list) or len(value) != len(_EXPECTED_SOURCE_NAMES):
        raise ValueError("kernel ingress boundary budget observations drift")
    for index, observation in enumerate(value):
        if not isinstance(observation, Mapping):
            raise ValueError("kernel ingress boundary budget observation must be object")
        _assert_exact_keys("observation", observation, _OBSERVATION_KEYS)
        if observation["source_name"] != _EXPECTED_SOURCE_NAMES[index]:
            raise ValueError("kernel ingress boundary budget source drift")
        if observation["kernel_name"] != _EXPECTED_KERNEL_NAMES[index]:
            raise ValueError("kernel ingress boundary budget kernel drift")
        if observation["case_id"] != f"accepted_{_EXPECTED_SOURCE_NAMES[index]}":
            raise ValueError("kernel ingress boundary budget case drift")
        if observation["status"] != "within_budget":
            raise ValueError("kernel ingress boundary budget observation status drift")
        if observation["import_count"] != 2:
            raise ValueError("kernel ingress boundary budget import drift")
        if observation["top_level_function_count"] != 1:
            raise ValueError("kernel ingress boundary budget function drift")
        _assert_bounded(
            observation["module_bytes"],
            MAX_TRITON_SOURCE_BYTES,
            "module bytes",
        )
        _assert_bounded(
            observation["module_line_count"],
            MAX_TRITON_SOURCE_LINES,
            "module lines",
        )
        _assert_bounded(
            observation["module_ast_node_count"],
            MAX_TRITON_SOURCE_AST_NODES,
            "module ast nodes",
        )
        _assert_bounded(
            observation["module_ast_depth"],
            MAX_TRITON_SOURCE_AST_DEPTH,
            "module ast depth",
        )


def _assert_rejection_cases(value: object) -> None:
    if not isinstance(value, list) or len(value) != len(_EXPECTED_REJECTION_CASES):
        raise ValueError("kernel ingress boundary budget rejection case drift")
    for case in value:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress boundary budget rejection must be object")
        _assert_exact_keys("rejection", case, _REJECTION_KEYS)
        case_id = case["case_id"]
        if not isinstance(case_id, str) or case_id not in _EXPECTED_REJECTION_CASES:
            raise ValueError("kernel ingress boundary budget rejection id drift")
        expected = _EXPECTED_REJECTION_CASES[case_id]
        for key, expected_value in expected.items():
            if case[key] != expected_value:
                raise ValueError(
                    f"kernel ingress boundary budget rejection {key} drift"
                )
        if case["status"] != "rejected":
            raise ValueError("kernel ingress boundary budget rejection status drift")


def _assert_bounded(value: object, limit: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"kernel ingress boundary budget invalid {label}")
    if value > limit:
        raise ValueError(f"kernel ingress boundary budget exceeded {label}")


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress boundary budget {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "kernel ingress boundary budget report is not JSON data"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress boundary budget contains forbidden source or "
                "value material"
            )


if __name__ == "__main__":
    main()
