"""Emit runtime evidence inventory for Kernel Ingress research cases."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_runtime_matrix_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT = (
    "source_to_intent_research_kernel_ingress_runtime_matrix.execution.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_SOURCE_BOUNDARY = (
    "triton_module_source_buffer_to_runtime_via_research_kernel_ingress"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_FORBIDDEN_FRAGMENTS = (
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
        "backend_sequences",
        "case_count",
        "cases",
        "covered_operation_families",
        "default_parser_status",
        "e2e_contract",
        "frontend_ingress_contract",
        "kernel_ingress_digest",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "runtime_matrix_contract",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_CASE_KEYS = frozenset(
    {
        "backend_sequence",
        "case_id",
        "execution_trace_digest",
        "kernel_name",
        "operation_families",
        "reference_correctness_digest",
        "runtime_plan_digest",
        "status",
        "terminal_outputs",
        "trace_step_count",
    }
)
_DIGEST_KEYS = (
    "execution_trace_digest",
    "reference_correctness_digest",
    "runtime_plan_digest",
)
_EXPECTED_CASES = {
    "research_module_matmul_elementwise": {
        "backend_sequence": ["linear-sim", "vector-sim"],
        "kernel_name": "matmul_elementwise",
        "operation_families": ["elementwise", "matmul"],
        "terminal_outputs": ["activated"],
    },
    "research_module_softmax_reduction": {
        "backend_sequence": ["vector-sim", "vector-sim"],
        "kernel_name": "softmax_reduction",
        "operation_families": ["reduction", "softmax"],
        "terminal_outputs": ["row_sum"],
    },
}


def build_kernel_ingress_runtime_matrix_report() -> dict[str, object]:
    """Return a source-free runtime evidence matrix for Kernel Ingress cases."""

    kernel_ingress_text = build_kernel_ingress_report()
    kernel_ingress = json.loads(kernel_ingress_text)
    assert_kernel_ingress_report_contract(kernel_ingress)
    cases = [_runtime_case(case) for case in kernel_ingress["cases"]]
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_ARTIFACT_POLICY
        ),
        "backend_sequences": _backend_sequences(cases),
        "case_count": len(cases),
        "cases": cases,
        "covered_operation_families": _covered_operation_families(cases),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "e2e_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    assert_kernel_ingress_runtime_matrix_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Kernel Ingress runtime matrix."""

    return json.dumps(
        build_kernel_ingress_runtime_matrix_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_runtime_matrix_report_contract(report: object) -> None:
    """Fail closed unless the Kernel Ingress runtime matrix matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress runtime matrix report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    kernel_ingress_text = build_kernel_ingress_report()
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_ARTIFACT_POLICY
        ),
        "backend_sequences": ["linear-sim->vector-sim", "vector-sim->vector-sim"],
        "case_count": len(_EXPECTED_CASES),
        "covered_operation_families": [
            "elementwise",
            "matmul",
            "reduction",
            "softmax",
        ],
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "e2e_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "runtime_matrix_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_CONTRACT
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress runtime matrix {key} drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress runtime matrix cases drift")
    observed_case_ids = []
    for case in cases:
        observed_case_ids.append(_assert_case_contract(case))
    if tuple(observed_case_ids) != tuple(_EXPECTED_CASES):
        raise ValueError("kernel ingress runtime matrix case order drift")
    _assert_report_is_source_free(report)


def _runtime_case(case: object) -> dict[str, object]:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress runtime matrix source case drift")
    return {
        "backend_sequence": list(_list_value(case, "backend_sequence")),
        "case_id": str(case["case_id"]),
        "execution_trace_digest": str(case["execution_trace_digest"]),
        "kernel_name": str(case["kernel_name"]),
        "operation_families": list(_list_value(case, "operation_families")),
        "reference_correctness_digest": str(case["reference_correctness_digest"]),
        "runtime_plan_digest": str(case["runtime_plan_digest"]),
        "status": "runtime_bound",
        "terminal_outputs": list(_list_value(case, "terminal_outputs")),
        "trace_step_count": int(case["trace_step_count"]),
    }


def _assert_case_contract(case: object) -> str:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress runtime matrix case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASES:
        raise ValueError("kernel ingress runtime matrix case id drift")
    expected = _EXPECTED_CASES[case_id]
    for key, expected_value in expected.items():
        if case[key] != expected_value:
            raise ValueError(f"kernel ingress runtime matrix {key} drift")
    if case["trace_step_count"] != 2:
        raise ValueError("kernel ingress runtime matrix trace step drift")
    if case["status"] != "runtime_bound":
        raise ValueError("kernel ingress runtime matrix case status drift")
    for key in _DIGEST_KEYS:
        value = case[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress runtime matrix digest drift")
    return case_id


def _list_value(case: Mapping[object, object], key: str) -> list[object]:
    value = case[key]
    if not isinstance(value, list):
        raise ValueError(f"kernel ingress runtime matrix {key} drift")
    return value


def _backend_sequences(cases: list[dict[str, object]]) -> list[str]:
    sequences = []
    for case in cases:
        backend_sequence = case["backend_sequence"]
        if not isinstance(backend_sequence, list):
            raise ValueError("kernel ingress runtime matrix backend sequence drift")
        sequence = "->".join(str(item) for item in backend_sequence)
        if sequence not in sequences:
            sequences.append(sequence)
    return sequences


def _covered_operation_families(cases: list[dict[str, object]]) -> list[str]:
    families = set()
    for case in cases:
        operation_families = case["operation_families"]
        if not isinstance(operation_families, list):
            raise ValueError("kernel ingress runtime matrix operation family drift")
        families.update(str(item) for item in operation_families)
    return sorted(families)


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress runtime matrix {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("kernel ingress runtime matrix report is not JSON data") from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_MATRIX_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress runtime matrix contains forbidden source "
                "or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
