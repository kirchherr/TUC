"""Emit source-free rejection coverage evidence for Kernel Ingress."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT,
        assert_kernel_ingress_boundary_budget_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
        build_report as build_kernel_ingress_boundary_budget_report,
    )
    from examples.source_to_intent_research_kernel_ingress_diagnostics import (
        build_report as build_kernel_ingress_diagnostics_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress_boundary_budget import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT,
        assert_kernel_ingress_boundary_budget_report_contract,
    )
    from source_to_intent_research_kernel_ingress_boundary_budget import (
        build_report as build_kernel_ingress_boundary_budget_report,
    )
    from source_to_intent_research_kernel_ingress_diagnostics import (
        build_report as build_kernel_ingress_diagnostics_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_rejection_coverage_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_rejection_coverage.security.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_ARTIFACT_POLICY = (
    "metadata_only_source_free"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_POLICY = (
    "all_current_rejections_are_source_free_and_fail_closed"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_SOURCE_BOUNDARY = (
    "triton_module_source_buffer_as_untrusted_data"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_FORBIDDEN_FRAGMENTS = (
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
        "blocked_compiler_outputs",
        "blocked_execution_surfaces",
        "boundary_budget_contract",
        "boundary_budget_digest",
        "budget_rejection_reasons",
        "coverage_contract",
        "coverage_matrix",
        "coverage_policy",
        "covered_rejection_count",
        "default_parser_status",
        "diagnostics_contract",
        "diagnostics_digest",
        "diagnostics_rejection_reasons",
        "frontend_ingress_contract",
        "parser_status",
        "raw_source_policy",
        "raw_value_policy",
        "required_coverage_sources",
        "schema_version",
        "source_boundary",
        "status",
    }
)
_COVERAGE_KEYS = frozenset(
    {"case_id", "coverage_source", "reason_id", "status"}
)
_REQUIRED_COVERAGE_SOURCES = ("diagnostics", "boundary_budget")
_EXPECTED_DIAGNOSTIC_COVERAGE = (
    {
        "case_id": "reject_unsupported_import",
        "coverage_source": "diagnostics",
        "reason_id": "unsupported_import",
        "status": "covered",
    },
    {
        "case_id": "reject_import_from_statement",
        "coverage_source": "diagnostics",
        "reason_id": "import_from_statement",
        "status": "covered",
    },
    {
        "case_id": "reject_import_after_kernel_function",
        "coverage_source": "diagnostics",
        "reason_id": "import_after_kernel_function",
        "status": "covered",
    },
    {
        "case_id": "reject_missing_triton_jit_decorator",
        "coverage_source": "diagnostics",
        "reason_id": "missing_triton_jit_decorator",
        "status": "covered",
    },
    {
        "case_id": "reject_decorator_call",
        "coverage_source": "diagnostics",
        "reason_id": "decorator_call",
        "status": "covered",
    },
    {
        "case_id": "reject_unsupported_decorator",
        "coverage_source": "diagnostics",
        "reason_id": "unsupported_decorator",
        "status": "covered",
    },
    {
        "case_id": "reject_multiple_kernel_functions",
        "coverage_source": "diagnostics",
        "reason_id": "multiple_kernel_functions",
        "status": "covered",
    },
    {
        "case_id": "reject_top_level_side_effect",
        "coverage_source": "diagnostics",
        "reason_id": "top_level_side_effect",
        "status": "covered",
    },
    {
        "case_id": "reject_kernel_name_mismatch",
        "coverage_source": "diagnostics",
        "reason_id": "kernel_name_mismatch",
        "status": "covered",
    },
)
_EXPECTED_BUDGET_COVERAGE = (
    {
        "case_id": "module_byte_budget",
        "coverage_source": "boundary_budget",
        "reason_id": "module_byte_budget",
        "status": "covered",
    },
    {
        "case_id": "module_line_budget",
        "coverage_source": "boundary_budget",
        "reason_id": "module_line_budget",
        "status": "covered",
    },
    {
        "case_id": "module_ast_node_budget",
        "coverage_source": "boundary_budget",
        "reason_id": "module_ast_node_budget",
        "status": "covered",
    },
    {
        "case_id": "module_ast_depth_budget",
        "coverage_source": "boundary_budget",
        "reason_id": "module_ast_depth_budget",
        "status": "covered",
    },
)
_EXPECTED_COVERAGE_MATRIX = _EXPECTED_DIAGNOSTIC_COVERAGE + _EXPECTED_BUDGET_COVERAGE
_EXPECTED_BUDGET_REJECTION_REASONS = tuple(
    item["reason_id"] for item in _EXPECTED_BUDGET_COVERAGE
)


def build_kernel_ingress_rejection_coverage_report() -> dict[str, object]:
    """Return source-free rejection coverage evidence for Kernel Ingress."""

    diagnostics_text = build_kernel_ingress_diagnostics_report()
    boundary_budget_text = build_kernel_ingress_boundary_budget_report()
    diagnostics = json.loads(diagnostics_text)
    boundary_budget = json.loads(boundary_budget_text)
    _assert_kernel_ingress_diagnostics_payload(diagnostics)
    assert_kernel_ingress_boundary_budget_report_contract(boundary_budget)
    coverage_matrix = _build_coverage_matrix(diagnostics, boundary_budget)
    report: dict[str, object] = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_ARTIFACT_POLICY
        ),
        "blocked_compiler_outputs": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ),
        "blocked_execution_surfaces": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ),
        "boundary_budget_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT
        ),
        "boundary_budget_digest": _digest(boundary_budget_text),
        "budget_rejection_reasons": list(_EXPECTED_BUDGET_REJECTION_REASONS),
        "coverage_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_CONTRACT
        ),
        "coverage_matrix": coverage_matrix,
        "coverage_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_POLICY
        ),
        "covered_rejection_count": len(coverage_matrix),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "diagnostics_digest": _digest(diagnostics_text),
        "diagnostics_rejection_reasons": sorted(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
        ),
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "required_coverage_sources": list(_REQUIRED_COVERAGE_SOURCES),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    assert_kernel_ingress_rejection_coverage_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress rejection coverage."""

    return json.dumps(
        build_kernel_ingress_rejection_coverage_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_rejection_coverage_report_contract(
    report: object,
) -> None:
    """Fail closed unless the rejection coverage report matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress rejection coverage report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_ARTIFACT_POLICY
        ),
        "blocked_compiler_outputs": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ),
        "blocked_execution_surfaces": list(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ),
        "boundary_budget_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BOUNDARY_BUDGET_CONTRACT
        ),
        "budget_rejection_reasons": list(_EXPECTED_BUDGET_REJECTION_REASONS),
        "coverage_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_CONTRACT
        ),
        "coverage_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_POLICY
        ),
        "covered_rejection_count": len(_EXPECTED_COVERAGE_MATRIX),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "diagnostics_rejection_reasons": sorted(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
        ),
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "required_coverage_sources": list(_REQUIRED_COVERAGE_SOURCES),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_SOURCE_BOUNDARY
        ),
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress rejection coverage {key} drift")
    for key in ("boundary_budget_digest", "diagnostics_digest"):
        digest = report[key]
        if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
            raise ValueError(f"kernel ingress rejection coverage {key} drift")
    _assert_coverage_matrix(report["coverage_matrix"])
    _assert_report_is_source_free(report)


def _build_coverage_matrix(
    diagnostics: Mapping[str, object],
    boundary_budget: Mapping[str, object],
) -> list[dict[str, object]]:
    diagnostic_entries = []
    cases = diagnostics["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress rejection coverage diagnostics cases drift")
    for case in cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress rejection coverage diagnostic case drift")
        if case["outcome"] == "rejected":
            diagnostic_entries.append(
                {
                    "case_id": case["case_id"],
                    "coverage_source": "diagnostics",
                    "reason_id": case["rejection_reason"],
                    "status": "covered",
                }
            )
    budget_entries = []
    rejection_cases = boundary_budget["budget_rejection_cases"]
    if not isinstance(rejection_cases, list):
        raise ValueError("kernel ingress rejection coverage budget cases drift")
    for case in rejection_cases:
        if not isinstance(case, Mapping):
            raise ValueError("kernel ingress rejection coverage budget case drift")
        budget_entries.append(
            {
                "case_id": case["case_id"],
                "coverage_source": "boundary_budget",
                "reason_id": case["case_id"],
                "status": "covered",
            }
        )
    coverage = diagnostic_entries + budget_entries
    _assert_coverage_matrix(coverage)
    return coverage


def _assert_kernel_ingress_diagnostics_payload(report: object) -> None:
    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress rejection coverage diagnostics must be object")
    expected_values = {
        "accepted_case_count": 5,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "rejected_case_count": len(_EXPECTED_DIAGNOSTIC_COVERAGE),
        "rejection_reasons": sorted(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
        ),
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REPORT_SCHEMA_VERSION
        ),
    }
    for key, expected in expected_values.items():
        if report.get(key) != expected:
            raise ValueError(f"kernel ingress rejection coverage diagnostics {key} drift")


def _assert_coverage_matrix(value: object) -> None:
    if not isinstance(value, list) or len(value) != len(_EXPECTED_COVERAGE_MATRIX):
        raise ValueError("kernel ingress rejection coverage matrix drift")
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError("kernel ingress rejection coverage item must be object")
        _assert_exact_keys("coverage item", item, _COVERAGE_KEYS)
        if item != _EXPECTED_COVERAGE_MATRIX[index]:
            raise ValueError("kernel ingress rejection coverage item drift")
    reason_ids = [item["reason_id"] for item in value]
    if len(reason_ids) != len(set(reason_ids)):
        raise ValueError("kernel ingress rejection coverage reason IDs must be unique")


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress rejection coverage {context} drift")


def _assert_report_is_source_free(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "kernel ingress rejection coverage report is not JSON data"
        ) from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_REJECTION_COVERAGE_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress rejection coverage contains forbidden source or "
                "value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
