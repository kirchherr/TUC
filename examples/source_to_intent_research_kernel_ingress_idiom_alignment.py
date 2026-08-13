"""Bind Kernel Ingress results to covered Triton idiom scope."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress import (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from examples.source_to_intent_research_kernel_ingress_conformance_gate import (
        REQUIRED_KERNEL_INGRESS_SOURCE_NAMES,
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE_CONTRACT,
        build_source_to_intent_research_kernel_ingress_results,
    )
    from examples.source_to_intent_research_kernel_ingress_conformance_gate import (
        build_gate_report as build_kernel_ingress_conformance_gate_report,
    )
    from examples.triton_idiom_coverage_report import (
        build_report as build_triton_idiom_coverage_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from source_to_intent_research_kernel_ingress_conformance_gate import (  # type: ignore[no-redef]
        REQUIRED_KERNEL_INGRESS_SOURCE_NAMES,
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE_CONTRACT,
        build_source_to_intent_research_kernel_ingress_results,
    )
    from source_to_intent_research_kernel_ingress_conformance_gate import (
        build_gate_report as build_kernel_ingress_conformance_gate_report,
    )
    from triton_idiom_coverage_report import (  # type: ignore[no-redef]
        build_report as build_triton_idiom_coverage_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES,
    TRITON_IDIOM_COVERAGE_CONTRACT,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION = (
    "tuc.source_to_intent_research_kernel_ingress_idiom_alignment_report.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_CONTRACT = (
    "source_to_intent_research_kernel_ingress_idiom_alignment.scope.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_ARTIFACT_POLICY = (
    "metadata_only_values_omitted"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_INPUT_POLICY = (
    "accepted_kernel_ingress_results_only"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_COVERAGE_POLICY = (
    "kernel_ingress_operation_families_must_match_covered_idioms"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_SOURCE_BOUNDARY = (
    "kernel_ingress_to_source_intent.v0_plain_data"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    "python_source",
    "raw_source",
    "raw_tensor_value",
    "source_intent_payload",
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_source_count",
        "alignment_contract",
        "artifact_policy",
        "blocked_execution_surfaces",
        "cases",
        "coverage_contract",
        "coverage_policy",
        "coverage_report_digest",
        "covered_operation_families",
        "default_parser_status",
        "direct_general_triton_source_ingestion",
        "frontend_ingress_contract",
        "input_policy",
        "kernel_ingress_contract",
        "kernel_ingress_digest",
        "kernel_ingress_conformance_gate_contract",
        "kernel_ingress_conformance_gate_digest",
        "kernel_names",
        "parser_status",
        "schema_version",
        "source_boundary",
        "source_names",
        "status",
        "unsupported_operation_families",
    }
)
_CASE_KEYS = frozenset(
    {"case_id", "kernel_name", "matched_idioms", "operation_families", "status"}
)
_EXPECTED_COVERED_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)
_EXPECTED_CASE_SUMMARIES = {
    "research_matmul_elementwise": {
        "kernel_name": "matmul_elementwise",
        "matched_idioms": [
            "metadata_elementwise_activation",
            "metadata_matmul_projection",
        ],
        "operation_families": ["elementwise", "matmul"],
    },
    "research_softmax_reduction": {
        "kernel_name": "softmax_reduction",
        "matched_idioms": ["metadata_reduction_axis", "metadata_softmax_axis"],
        "operation_families": ["reduction", "softmax"],
    },
    "research_matmul_reduction": {
        "kernel_name": "matmul_reduction",
        "matched_idioms": ["metadata_matmul_projection", "metadata_reduction_axis"],
        "operation_families": ["matmul", "reduction"],
    },
    "research_softmax_elementwise": {
        "kernel_name": "softmax_elementwise",
        "matched_idioms": [
            "metadata_elementwise_activation",
            "metadata_softmax_axis",
        ],
        "operation_families": ["elementwise", "softmax"],
    },
    "research_mvp_pipeline": {
        "kernel_name": "mvp_pipeline",
        "matched_idioms": [
            "metadata_elementwise_activation",
            "metadata_matmul_projection",
            "metadata_reduction_axis",
            "metadata_softmax_axis",
        ],
        "operation_families": ["elementwise", "matmul", "reduction", "softmax"],
    },
}


def build_kernel_ingress_idiom_alignment_report() -> dict[str, object]:
    """Return metadata-only evidence that Kernel Ingress stays in covered idioms."""

    coverage_text = build_triton_idiom_coverage_report()
    coverage_report = json.loads(coverage_text)
    kernel_ingress_text = build_kernel_ingress_report()
    conformance_text = build_kernel_ingress_conformance_gate_report()
    ingress_results = build_source_to_intent_research_kernel_ingress_results()
    coverage_by_family = _coverage_by_family(coverage_report)
    cases = [
        _build_case(
            result.report.source_name,
            result.report.kernel_name,
            result.report.operation_families,
            coverage_by_family,
        )
        for result in ingress_results
    ]
    covered_operation_families = sorted(coverage_by_family)
    unsupported = sorted(
        family
        for case in cases
        for family in case["operation_families"]
        if family not in covered_operation_families
    )
    report: dict[str, object] = {
        "accepted_source_count": len(cases),
        "alignment_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_CONTRACT
        ),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_ARTIFACT_POLICY
        ),
        "blocked_execution_surfaces": list(
            TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES
        ),
        "cases": cases,
        "coverage_contract": TRITON_IDIOM_COVERAGE_CONTRACT,
        "coverage_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_COVERAGE_POLICY
        ),
        "coverage_report_digest": _digest(coverage_text),
        "covered_operation_families": covered_operation_families,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "direct_general_triton_source_ingestion": False,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_INPUT_POLICY
        ),
        "kernel_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "kernel_ingress_digest": _digest(kernel_ingress_text),
        "kernel_ingress_conformance_gate_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE_CONTRACT
        ),
        "kernel_ingress_conformance_gate_digest": _digest(conformance_text),
        "kernel_names": [result.report.kernel_name for result in ingress_results],
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_SOURCE_BOUNDARY
        ),
        "source_names": [result.report.source_name for result in ingress_results],
        "status": "PASS" if not unsupported else "FAIL",
        "unsupported_operation_families": unsupported,
    }
    assert_kernel_ingress_idiom_alignment_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for Kernel Ingress idiom alignment."""

    return (
        json.dumps(
            build_kernel_ingress_idiom_alignment_report(),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def main() -> None:
    print(build_report(), end="")


def assert_kernel_ingress_idiom_alignment_report_contract(report: object) -> None:
    """Fail closed unless the Kernel Ingress idiom alignment report is valid."""

    if not isinstance(report, Mapping):
        raise ValueError("kernel ingress idiom alignment report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "alignment_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_CONTRACT
        ),
        "artifact_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_ARTIFACT_POLICY
        ),
        "coverage_contract": TRITON_IDIOM_COVERAGE_CONTRACT,
        "coverage_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_COVERAGE_POLICY
        ),
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "direct_general_triton_source_ingestion": False,
        "frontend_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "input_policy": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_INPUT_POLICY
        ),
        "kernel_ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_E2E_CONTRACT,
        "kernel_ingress_conformance_gate_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE_CONTRACT
        ),
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "schema_version": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_SOURCE_BOUNDARY
        ),
        "source_names": list(REQUIRED_KERNEL_INGRESS_SOURCE_NAMES),
        "status": "PASS",
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"kernel ingress idiom alignment {key} contract drift")
    if report["blocked_execution_surfaces"] != list(
        TRITON_IDIOM_COVERAGE_BLOCKED_EXECUTION_SURFACES
    ):
        raise ValueError("kernel ingress idiom alignment execution surface drift")
    if (
        tuple(report["covered_operation_families"])
        != _EXPECTED_COVERED_OPERATION_FAMILIES
    ):
        raise ValueError("kernel ingress idiom alignment coverage drift")
    if report["unsupported_operation_families"] != []:
        raise ValueError("kernel ingress idiom alignment unsupported scope")
    for key in (
        "coverage_report_digest",
        "kernel_ingress_digest",
        "kernel_ingress_conformance_gate_digest",
    ):
        value = report[key]
        if not isinstance(value, str) or not _SHA256_DIGEST_PATTERN.fullmatch(value):
            raise ValueError("kernel ingress idiom alignment digest drift")
    cases = report["cases"]
    if not isinstance(cases, list):
        raise ValueError("kernel ingress idiom alignment cases drift")
    if report["accepted_source_count"] != len(cases):
        raise ValueError("kernel ingress idiom alignment count drift")
    case_ids = []
    kernel_names = []
    for case in cases:
        case_id, kernel_name = _assert_case_contract(case)
        case_ids.append(case_id)
        kernel_names.append(kernel_name)
    if tuple(case_ids) != REQUIRED_KERNEL_INGRESS_SOURCE_NAMES:
        raise ValueError("kernel ingress idiom alignment case order drift")
    if report["kernel_names"] != kernel_names:
        raise ValueError("kernel ingress idiom alignment kernel name drift")
    _assert_report_is_metadata_only(report)


def _build_case(
    source_name: str,
    kernel_name: str,
    operation_families: tuple[str, ...],
    coverage_by_family: Mapping[str, str],
) -> dict[str, object]:
    families = sorted(operation_families)
    matched_idioms = sorted(coverage_by_family[family] for family in families)
    return {
        "case_id": source_name,
        "kernel_name": kernel_name,
        "matched_idioms": matched_idioms,
        "operation_families": families,
        "status": "covered",
    }


def _coverage_by_family(coverage_report: Mapping[str, object]) -> dict[str, str]:
    if coverage_report.get("coverage_contract") != TRITON_IDIOM_COVERAGE_CONTRACT:
        raise ValueError("kernel ingress idiom alignment coverage drift")
    if coverage_report.get("triton_idiom_coverage_ready") is not True:
        raise ValueError("kernel ingress idiom alignment coverage not ready")
    coverages = coverage_report.get("coverages")
    if not isinstance(coverages, list):
        raise ValueError("kernel ingress idiom alignment coverage missing")
    by_family: dict[str, str] = {}
    for coverage in coverages:
        if not isinstance(coverage, Mapping):
            raise ValueError("kernel ingress idiom alignment coverage invalid")
        family = coverage.get("operation_family")
        idiom_id = coverage.get("idiom_id")
        status = coverage.get("coverage_status")
        if not isinstance(family, str) or not isinstance(idiom_id, str):
            raise ValueError("kernel ingress idiom alignment coverage invalid")
        if status != "metadata_golden_covered":
            raise ValueError("kernel ingress idiom alignment coverage invalid")
        by_family[family] = idiom_id
    return by_family


def _assert_case_contract(case: object) -> tuple[str, str]:
    if not isinstance(case, Mapping):
        raise ValueError("kernel ingress idiom alignment case must be object")
    _assert_exact_keys("case", case, _CASE_KEYS)
    case_id = case["case_id"]
    if not isinstance(case_id, str) or case_id not in _EXPECTED_CASE_SUMMARIES:
        raise ValueError("kernel ingress idiom alignment case id drift")
    expected = _EXPECTED_CASE_SUMMARIES[case_id]
    if case["kernel_name"] != expected["kernel_name"]:
        raise ValueError("kernel ingress idiom alignment kernel drift")
    if case["operation_families"] != expected["operation_families"]:
        raise ValueError("kernel ingress idiom alignment family drift")
    if case["matched_idioms"] != expected["matched_idioms"]:
        raise ValueError("kernel ingress idiom alignment idiom drift")
    if case["status"] != "covered":
        raise ValueError("kernel ingress idiom alignment case status drift")
    return case_id, expected["kernel_name"]


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"kernel ingress idiom alignment {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("kernel ingress idiom alignment report is not JSON data") from exc
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_IDIOM_ALIGNMENT_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise ValueError(
                "kernel ingress idiom alignment report contains forbidden "
                "source or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
