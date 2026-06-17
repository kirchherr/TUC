"""Emit policy evidence for Kernel Ingress runtime matrix coverage."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT,
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_runtime_coverage_policy_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT = (
    "source_to_intent_research_kernel_ingress_runtime_coverage_policy.review.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ID = (
    "source_to_intent_research_kernel_ingress_runtime_coverage_policy"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ARTIFACT_POLICY = (
    "metadata_only_source_free"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_SOURCE_BOUNDARY = (
    "triton_module_source_buffer_to_runtime_via_research_kernel_ingress"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_TRACE_POLICY = (
    "exact_current_trace_count_until_runtime_model_expands"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"module_source":',
    "python_source",
    '"raw_source":',
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
        "case_requirements",
        "default_parser_status",
        "frontend_ingress_contract",
        "observed_backend_sequences",
        "observed_case_count",
        "observed_operation_families",
        "observed_terminal_outputs",
        "parser_status",
        "policy_contract",
        "policy_id",
        "raw_source_policy",
        "raw_value_policy",
        "required_backend_sequences",
        "required_case_count",
        "required_digest_fields",
        "required_operation_families",
        "required_terminal_outputs",
        "required_trace_step_count_per_case",
        "runtime_matrix_contract",
        "runtime_matrix_digest",
        "schema_version",
        "source_boundary",
        "status",
        "trace_step_policy",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "case_id",
        "kernel_name",
        "operation_families",
        "status",
        "terminal_outputs",
        "trace_step_count",
    }
)
_REQUIRED_CASES = (
    {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "case_id": "research_module_matmul_elementwise",
        "kernel_name": "matmul_elementwise",
        "operation_families": ["elementwise", "matmul"],
        "status": "covered",
        "terminal_outputs": ["activated"],
        "trace_step_count": 2,
    },
    {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "case_id": "research_module_softmax_reduction",
        "kernel_name": "softmax_reduction",
        "operation_families": ["reduction", "softmax"],
        "status": "covered",
        "terminal_outputs": ["row_sum"],
        "trace_step_count": 2,
    },
)
_REQUIRED_BACKEND_SEQUENCES = (
    "linear-sim->vector-sim",
    "vector-sim->vector-sim",
)
_REQUIRED_OPERATION_FAMILIES = ("elementwise", "matmul", "reduction", "softmax")
_REQUIRED_TERMINAL_OUTPUTS = ("activated", "row_sum")
_REQUIRED_DIGEST_FIELDS = (
    "runtime_plan_digest",
    "execution_trace_digest",
    "reference_correctness_digest",
)


def build_kernel_ingress_runtime_coverage_policy_report() -> dict[str, object]:
    """Return source-free policy evidence for Kernel Ingress runtime coverage."""

    runtime_matrix_text = build_kernel_ingress_runtime_matrix_report()
    runtime_matrix = json.loads(runtime_matrix_text)
    assert_kernel_ingress_runtime_matrix_report_contract(runtime_matrix)
    case_requirements = _case_requirements(runtime_matrix)
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ARTIFACT_POLICY
        ),
        "case_requirements": case_requirements,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "observed_backend_sequences": list(runtime_matrix["backend_sequences"]),
        "observed_case_count": runtime_matrix["case_count"],
        "observed_operation_families": list(runtime_matrix["covered_operation_families"]),
        "observed_terminal_outputs": _observed_terminal_outputs(runtime_matrix),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "policy_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
        ),
        "policy_id": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ID,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "required_backend_sequences": list(_REQUIRED_BACKEND_SEQUENCES),
        "required_case_count": len(_REQUIRED_CASES),
        "required_digest_fields": list(_REQUIRED_DIGEST_FIELDS),
        "required_operation_families": list(_REQUIRED_OPERATION_FAMILIES),
        "required_terminal_outputs": list(_REQUIRED_TERMINAL_OUTPUTS),
        "required_trace_step_count_per_case": 2,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trace_step_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_TRACE_POLICY
        ),
    }
    assert_kernel_ingress_runtime_coverage_policy_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the runtime coverage policy."""

    return json.dumps(
        build_kernel_ingress_runtime_coverage_policy_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_runtime_coverage_policy_report_contract(
    report: object,
) -> None:
    """Fail closed unless the runtime coverage policy report matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress runtime coverage policy report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    runtime_matrix_text = build_kernel_ingress_runtime_matrix_report()
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ARTIFACT_POLICY
        ),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "observed_backend_sequences": list(_REQUIRED_BACKEND_SEQUENCES),
        "observed_case_count": len(_REQUIRED_CASES),
        "observed_operation_families": list(_REQUIRED_OPERATION_FAMILIES),
        "observed_terminal_outputs": list(_REQUIRED_TERMINAL_OUTPUTS),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "policy_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_CONTRACT
        ),
        "policy_id": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_ID,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "required_backend_sequences": list(_REQUIRED_BACKEND_SEQUENCES),
        "required_case_count": len(_REQUIRED_CASES),
        "required_digest_fields": list(_REQUIRED_DIGEST_FIELDS),
        "required_operation_families": list(_REQUIRED_OPERATION_FAMILIES),
        "required_terminal_outputs": list(_REQUIRED_TERMINAL_OUTPUTS),
        "required_trace_step_count_per_case": 2,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "runtime_matrix_digest": _digest(runtime_matrix_text),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_SOURCE_BOUNDARY
        ),
        "status": "PASS",
        "trace_step_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_TRACE_POLICY
        ),
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress runtime coverage policy {key} drift")
    cases = report["case_requirements"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime coverage policy cases drift")
    for index, case in enumerate(cases):
        _assert_case_requirement(index, case)
    _assert_report_is_source_free(report)


def _case_requirements(runtime_matrix: Mapping[object, object]) -> list[dict[str, object]]:
    cases = runtime_matrix["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime coverage policy matrix case drift")
    requirements = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress runtime coverage policy matrix case drift")
        _assert_case_has_runtime_digests(case)
        requirements.append(
            {
                "backend_sequence": list(_list_value(case, "backend_sequence")),
                "case_id": str(case["case_id"]),
                "kernel_name": str(case["kernel_name"]),
                "operation_families": list(_list_value(case, "operation_families")),
                "status": "covered",
                "terminal_outputs": list(_list_value(case, "terminal_outputs")),
                "trace_step_count": int(case["trace_step_count"]),
            }
        )
    return requirements


def _assert_case_requirement(index: int, case: object) -> None:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress runtime coverage policy case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    expected = _REQUIRED_CASES[index]
    for key, expected_value in expected.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress runtime coverage policy {key} drift")


def _assert_case_has_runtime_digests(case: Mapping[object, object]) -> None:
    for key in _REQUIRED_DIGEST_FIELDS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress runtime coverage policy digest drift")


def _observed_terminal_outputs(runtime_matrix: Mapping[object, object]) -> list[str]:
    cases = runtime_matrix["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime coverage policy matrix case drift")
    outputs = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress runtime coverage policy matrix case drift")
        for output in _list_value(case, "terminal_outputs"):
            outputs.append(str(output))
    return outputs


def _list_value(case: Mapping[object, object], key: str) -> list[object]:
    value = case[key]
    if not isinstance(value, list):
        raise ValueError(f"kernel ingress runtime coverage policy {key} drift")
    return value


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress runtime coverage policy {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "kernel ingress runtime coverage policy report is not JSON data"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_COVERAGE_POLICY_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress runtime coverage policy contains forbidden "
                "source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
