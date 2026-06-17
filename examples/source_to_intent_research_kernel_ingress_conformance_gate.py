"""Run CI-facing Source-To-Intent Research Kernel Ingress Conformance Gate."""

from __future__ import annotations

try:
    from examples.source_to_intent_research_kernel_ingress import (
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
        REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
        REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
        REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
        REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE,
    )

from tuc.frontend import (
    SOURCE_INTENT_SCHEMA_VERSION,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceIntentFrontendConformanceCase,
    SourceIntentFrontendConformanceReport,
    SourceToIntentResearchKernelIngressResult,
    ingest_triton_module_source_to_source_intent,
    run_source_intent_frontend_conformance,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_conformance_gate.ci.v0"
)
DEFAULT_FRONTEND_NAME = "source-to-intent-research-kernel-ingress"
REQUIRED_ACCEPTED_CASES = (
    "research_kernel_ingress_matmul_elementwise",
    "research_kernel_ingress_softmax_reduction",
    "research_kernel_ingress_matmul_reduction",
)
REQUIRED_REJECTED_CASES = (
    "reject_kernel_ingress_backend_hint_escape",
    "reject_kernel_ingress_source_text_escape",
)
REQUIRED_KERNEL_INGRESS_SOURCE_NAMES = (
    "research_matmul_elementwise",
    "research_softmax_reduction",
    "research_matmul_reduction",
)
REQUIRED_KERNEL_NAMES = (
    "matmul_elementwise",
    "softmax_reduction",
    "matmul_reduction",
)


class SourceToIntentResearchKernelIngressConformanceGateError(AssertionError):
    """Raised when kernel ingress conformance evidence is incomplete."""


def build_source_to_intent_research_kernel_ingress_results() -> (
    tuple[SourceToIntentResearchKernelIngressResult, ...]
):
    """Return accepted explicit kernel ingress results for conformance."""

    return (
        ingest_triton_module_source_to_source_intent(
            REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
            source_name="research_matmul_elementwise",
            kernel_name="matmul_elementwise",
            tensor_shapes={
                "a": (4, 8),
                "b": (8, 2),
                "y": (4, 2),
            },
        ),
        ingest_triton_module_source_to_source_intent(
            REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE,
            source_name="research_softmax_reduction",
            kernel_name="softmax_reduction",
            tensor_shapes={
                "x": (4, 8),
                "y": (4,),
            },
        ),
        ingest_triton_module_source_to_source_intent(
            REALISTIC_MATMUL_REDUCTION_MODULE_SOURCE,
            source_name="research_matmul_reduction",
            kernel_name="matmul_reduction",
            tensor_shapes={
                "a": (4, 8),
                "b": (8, 2),
                "y": (4,),
            },
        ),
    )


def build_source_to_intent_research_kernel_ingress_conformance_cases(
    ingress_results: tuple[SourceToIntentResearchKernelIngressResult, ...] | None = None,
) -> tuple[SourceIntentFrontendConformanceCase, ...]:
    """Return conformance cases bound to explicit kernel ingress output."""

    results = (
        build_source_to_intent_research_kernel_ingress_results()
        if ingress_results is None
        else ingress_results
    )
    _assert_kernel_ingress_results(results)
    return (
        SourceIntentFrontendConformanceCase(
            name="research_kernel_ingress_matmul_elementwise",
            payload=results[0].parser_result.source_intent_payload,
            should_accept=True,
        ),
        SourceIntentFrontendConformanceCase(
            name="research_kernel_ingress_softmax_reduction",
            payload=results[1].parser_result.source_intent_payload,
            should_accept=True,
        ),
        SourceIntentFrontendConformanceCase(
            name="research_kernel_ingress_matmul_reduction",
            payload=results[2].parser_result.source_intent_payload,
            should_accept=True,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_kernel_ingress_backend_hint_escape",
            payload={
                "name": "bad_kernel_ingress_payload",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "tensors": [{"name": "a", "shape": [1]}],
                "operations": [
                    {
                        "family": "elementwise",
                        "hints": {"backend": "gpu"},
                        "inputs": ["a"],
                        "name": "bad",
                        "outputs": ["a"],
                    }
                ],
            },
            should_accept=False,
        ),
        SourceIntentFrontendConformanceCase(
            name="reject_kernel_ingress_source_text_escape",
            payload={
                "name": "bad_kernel_ingress_payload",
                "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
                "python_source": "@triton.jit\ndef kernel(): pass",
                "tensors": [],
                "operations": [],
            },
            should_accept=False,
        ),
    )


def build_gate_report(
    *,
    conformance_report: SourceIntentFrontendConformanceReport | None = None,
    ingress_results: tuple[SourceToIntentResearchKernelIngressResult, ...] | None = None,
) -> str:
    """Return stable CI-facing kernel ingress conformance gate evidence."""

    results = (
        build_source_to_intent_research_kernel_ingress_results()
        if ingress_results is None
        else ingress_results
    )
    _assert_kernel_ingress_results(results)
    report = (
        run_source_intent_frontend_conformance(
            DEFAULT_FRONTEND_NAME,
            build_source_to_intent_research_kernel_ingress_conformance_cases(results),
        )
        if conformance_report is None
        else conformance_report
    )
    _assert_conformance_passed(report)
    _assert_required_cases_covered(report)
    return _render_gate_report(report, results)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_kernel_ingress_results(
    results: tuple[SourceToIntentResearchKernelIngressResult, ...],
) -> None:
    if type(results) is not tuple:
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance failed: ingress results must be a tuple"
        )
    if len(results) != len(REQUIRED_KERNEL_INGRESS_SOURCE_NAMES):
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance failed: ingress result count mismatch"
        )
    source_names = tuple(result.report.source_name for result in results)
    if source_names != REQUIRED_KERNEL_INGRESS_SOURCE_NAMES:
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance failed: ingress source names changed"
        )
    kernel_names = tuple(result.report.kernel_name for result in results)
    if kernel_names != REQUIRED_KERNEL_NAMES:
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance failed: kernel names changed"
        )
    for result in results:
        if not isinstance(result, SourceToIntentResearchKernelIngressResult):
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: not an ingress result"
            )
        report = result.report
        if report.ingress_contract != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT:
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: ingress contract changed"
            )
        if report.input_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY:
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: input policy changed"
            )
        if report.output_policy != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY:
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: output policy changed"
            )
        if report.parser_status != SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS:
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: parser status changed"
            )
        if report.default_parser_status != (
            SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS
        ):
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: default parser status changed"
            )
        if report.parser_output_policy != SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY:
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: parser output policy changed"
            )
        if report.raw_source_policy != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY
        ):
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: raw source policy changed"
            )
        if report.raw_value_policy != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY
        ):
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: raw value policy changed"
            )
        if report.blocked_claims != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_CLAIMS:
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: blocked claims changed"
            )
        if report.blocked_compiler_outputs != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS
        ):
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: blocked compiler outputs changed"
            )
        if report.blocked_execution_surfaces != (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES
        ):
            raise SourceToIntentResearchKernelIngressConformanceGateError(
                "kernel ingress conformance failed: blocked surfaces changed"
            )


def _assert_conformance_passed(
    report: SourceIntentFrontendConformanceReport,
) -> None:
    if not isinstance(report, SourceIntentFrontendConformanceReport):
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance failed: not a conformance report"
        )
    if not report.passed:
        issues = ",".join(
            f"{issue.case_name}:{issue.message}" for issue in report.issues
        )
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            f"kernel ingress conformance failed: {issues}"
        )
    if report.frontend_name != DEFAULT_FRONTEND_NAME:
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance failed: frontend name changed"
        )


def _assert_required_cases_covered(
    report: SourceIntentFrontendConformanceReport,
) -> None:
    checked_cases = frozenset(report.checked_cases)
    missing_cases = tuple(
        case_name
        for case_name in (*REQUIRED_ACCEPTED_CASES, *REQUIRED_REJECTED_CASES)
        if case_name not in checked_cases
    )
    if missing_cases:
        missing = ",".join(missing_cases)
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance coverage failed: "
            f"missing {missing}"
        )
    if report.accepted_case_count != len(REQUIRED_ACCEPTED_CASES):
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance coverage failed: accepted case count changed"
        )
    if report.rejected_case_count != len(REQUIRED_REJECTED_CASES):
        raise SourceToIntentResearchKernelIngressConformanceGateError(
            "kernel ingress conformance coverage failed: rejected case count changed"
        )


def _render_gate_report(
    report: SourceIntentFrontendConformanceReport,
    results: tuple[SourceToIntentResearchKernelIngressResult, ...],
) -> str:
    lines = [
        "source_to_intent.research_kernel_ingress_conformance_gate "
        "@source_to_intent_research_kernel_ingress_conformance_gate_v0 {"
    ]
    lines.append(
        "  gate_contract = "
        f'"{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONFORMANCE_GATE_CONTRACT}"'
    )
    lines.append(
        f'  ingress_contract = "{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT}"'
    )
    lines.append(
        f'  input_policy = "{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_INPUT_POLICY}"'
    )
    lines.append(
        f'  output_policy = "{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_OUTPUT_POLICY}"'
    )
    lines.append(f'  parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS}"')
    lines.append(
        f'  default_parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS}"'
    )
    lines.append(
        f'  parser_output_policy = "{SOURCE_TO_INTENT_RESEARCH_PARSER_OUTPUT_POLICY}"'
    )
    lines.append('  source_intent_frontend_conformance = "passed"')
    lines.append(f'  frontend_name = "{report.frontend_name}"')
    lines.append(
        "  ingress_sources = "
        f'"{",".join(result.report.source_name for result in results)}"'
    )
    lines.append(
        f'  kernel_names = "{",".join(result.report.kernel_name for result in results)}"'
    )
    lines.append(f'  accepted_cases = "{report.accepted_case_count}"')
    lines.append(f'  rejected_cases = "{report.rejected_case_count}"')
    lines.append(f'  checked_cases = "{len(report.checked_cases)}"')
    lines.append(
        f'  required_accepted_cases = "{",".join(REQUIRED_ACCEPTED_CASES)}"'
    )
    lines.append(
        f'  required_rejected_cases = "{",".join(REQUIRED_REJECTED_CASES)}"'
    )
    lines.append(
        "  blocked_compiler_outputs = "
        f'"{",".join(SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_COMPILER_OUTPUTS)}"'
    )
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
