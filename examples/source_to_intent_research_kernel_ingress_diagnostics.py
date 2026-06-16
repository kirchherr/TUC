"""Emit source-free diagnostics for Source-To-Intent Research Kernel Ingress."""

from __future__ import annotations

from examples.source_to_intent_research_kernel_ingress import (
    REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
    REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE,
)
from tuc.frontend import (
    SourceToIntentResearchKernelIngressDiagnosticCase,
    build_source_to_intent_research_kernel_ingress_diagnostics_report,
    dump_source_to_intent_research_kernel_ingress_diagnostics_report,
)

REJECT_UNSUPPORTED_IMPORT_MODULE_SOURCE = (
    REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace("import triton", "import os")
)
REJECT_IMPORT_FROM_MODULE_SOURCE = REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE.replace(
    "import triton.language as tl",
    "from triton import language as tl",
)
REJECT_MULTIPLE_KERNEL_FUNCTIONS_MODULE_SOURCE = (
    REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE
    + "\n@triton.jit\n"
    "def extra_kernel(a, y):\n"
    "    tl.store(y, a)\n"
)
REJECT_TOP_LEVEL_SIDE_EFFECT_MODULE_SOURCE = (
    REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE
    + "\nSIDE_EFFECT = open('secret.txt')\n"
)
REJECT_KERNEL_NAME_MISMATCH_MODULE_SOURCE = (
    "# kernel-name mismatch fixture\n" + REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE
)


def build_source_to_intent_research_kernel_ingress_diagnostic_cases() -> (
    tuple[SourceToIntentResearchKernelIngressDiagnosticCase, ...]
):
    """Return accepted and rejected kernel ingress diagnostic cases."""

    matmul_shapes = {"a": (4, 8), "b": (8, 2), "y": (4, 2)}
    softmax_shapes = {"x": (4, 8), "y": (4,)}
    return (
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="accepted_module_matmul_elementwise",
            expectation="accepted",
            module_source=REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
            source_name="research_matmul_elementwise",
            kernel_name="matmul_elementwise",
            tensor_shapes=matmul_shapes,
        ),
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="accepted_module_softmax_reduction",
            expectation="accepted",
            module_source=REALISTIC_SOFTMAX_REDUCTION_MODULE_SOURCE,
            source_name="research_softmax_reduction",
            kernel_name="softmax_reduction",
            tensor_shapes=softmax_shapes,
        ),
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="reject_unsupported_import",
            expectation="rejected",
            module_source=REJECT_UNSUPPORTED_IMPORT_MODULE_SOURCE,
            source_name="reject_unsupported_import",
            kernel_name="matmul_elementwise",
            tensor_shapes=matmul_shapes,
            expected_rejection_reason="unsupported_import",
        ),
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="reject_import_from_statement",
            expectation="rejected",
            module_source=REJECT_IMPORT_FROM_MODULE_SOURCE,
            source_name="reject_import_from_statement",
            kernel_name="matmul_elementwise",
            tensor_shapes=matmul_shapes,
            expected_rejection_reason="import_from_statement",
        ),
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="reject_multiple_kernel_functions",
            expectation="rejected",
            module_source=REJECT_MULTIPLE_KERNEL_FUNCTIONS_MODULE_SOURCE,
            source_name="reject_multiple_kernel_functions",
            kernel_name="matmul_elementwise",
            tensor_shapes=matmul_shapes,
            expected_rejection_reason="multiple_kernel_functions",
        ),
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="reject_top_level_side_effect",
            expectation="rejected",
            module_source=REJECT_TOP_LEVEL_SIDE_EFFECT_MODULE_SOURCE,
            source_name="reject_top_level_side_effect",
            kernel_name="matmul_elementwise",
            tensor_shapes=matmul_shapes,
            expected_rejection_reason="top_level_side_effect",
        ),
        SourceToIntentResearchKernelIngressDiagnosticCase(
            case_id="reject_kernel_name_mismatch",
            expectation="rejected",
            module_source=REJECT_KERNEL_NAME_MISMATCH_MODULE_SOURCE,
            source_name="reject_kernel_name_mismatch",
            kernel_name="not_the_kernel",
            tensor_shapes=matmul_shapes,
            expected_rejection_reason="kernel_name_mismatch",
        ),
    )


def build_report() -> str:
    """Return stable kernel ingress diagnostics evidence."""

    return dump_source_to_intent_research_kernel_ingress_diagnostics_report(
        build_source_to_intent_research_kernel_ingress_diagnostics_report(
            build_source_to_intent_research_kernel_ingress_diagnostic_cases()
        )
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
