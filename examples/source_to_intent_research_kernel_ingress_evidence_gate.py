"""Run the CI-facing Source-To-Intent Research Kernel Ingress Evidence Gate."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_to_intent_research_kernel_ingress import (
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence import (
        assert_kernel_ingress_backend_equivalence_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_backend_equivalence import (
        build_report as build_kernel_ingress_backend_equivalence_report,
    )
    from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
        assert_kernel_ingress_boundary_budget_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_boundary_budget import (
        build_report as build_kernel_ingress_boundary_budget_report,
    )
    from examples.source_to_intent_research_kernel_ingress_conformance_gate import (
        build_gate_report as build_kernel_ingress_conformance_gate_report,
    )
    from examples.source_to_intent_research_kernel_ingress_diagnostics import (
        build_report as build_kernel_ingress_diagnostics_report,
    )
    from examples.source_to_intent_research_kernel_ingress_idiom_alignment import (
        assert_kernel_ingress_idiom_alignment_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_idiom_alignment import (
        build_report as build_kernel_ingress_idiom_alignment_report,
    )
    from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
        assert_kernel_ingress_proof_bundle_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
        build_report as build_kernel_ingress_proof_bundle_report,
    )
    from examples.source_to_intent_research_kernel_ingress_rejection_coverage import (
        assert_kernel_ingress_rejection_coverage_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_rejection_coverage import (
        build_report as build_kernel_ingress_rejection_coverage_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        assert_kernel_ingress_runtime_backend_alignment_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        build_report as build_kernel_ingress_runtime_backend_alignment_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        assert_kernel_ingress_runtime_coverage_policy_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        build_report as build_kernel_ingress_runtime_coverage_policy_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        build_report as build_kernel_ingress_runtime_evidence_bundle_index_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
        assert_kernel_ingress_runtime_step_trace_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_runtime_step_trace import (
        build_report as build_kernel_ingress_runtime_step_trace_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence import (  # type: ignore[no-redef]
        assert_kernel_ingress_backend_equivalence_report_contract,
    )
    from source_to_intent_research_kernel_ingress_backend_equivalence import (
        build_report as build_kernel_ingress_backend_equivalence_report,
    )
    from source_to_intent_research_kernel_ingress_boundary_budget import (  # type: ignore[no-redef]
        assert_kernel_ingress_boundary_budget_report_contract,
    )
    from source_to_intent_research_kernel_ingress_boundary_budget import (
        build_report as build_kernel_ingress_boundary_budget_report,
    )
    from source_to_intent_research_kernel_ingress_conformance_gate import (
        build_gate_report as build_kernel_ingress_conformance_gate_report,
    )
    from source_to_intent_research_kernel_ingress_diagnostics import (
        build_report as build_kernel_ingress_diagnostics_report,
    )
    from source_to_intent_research_kernel_ingress_idiom_alignment import (  # type: ignore[no-redef]
        assert_kernel_ingress_idiom_alignment_report_contract,
    )
    from source_to_intent_research_kernel_ingress_idiom_alignment import (
        build_report as build_kernel_ingress_idiom_alignment_report,
    )
    from source_to_intent_research_kernel_ingress_proof_bundle import (  # type: ignore[no-redef]
        assert_kernel_ingress_proof_bundle_report_contract,
    )
    from source_to_intent_research_kernel_ingress_proof_bundle import (
        build_report as build_kernel_ingress_proof_bundle_report,
    )
    from source_to_intent_research_kernel_ingress_rejection_coverage import (  # type: ignore[no-redef]
        assert_kernel_ingress_rejection_coverage_report_contract,
    )
    from source_to_intent_research_kernel_ingress_rejection_coverage import (
        build_report as build_kernel_ingress_rejection_coverage_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_backend_alignment import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_backend_alignment_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_backend_alignment import (
        build_report as build_kernel_ingress_runtime_backend_alignment_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_coverage_policy import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_coverage_policy_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_coverage_policy import (
        build_report as build_kernel_ingress_runtime_coverage_policy_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index import (
        build_report as build_kernel_ingress_runtime_evidence_bundle_index_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_matrix_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_matrix import (
        build_report as build_kernel_ingress_runtime_matrix_report,
    )
    from source_to_intent_research_kernel_ingress_runtime_step_trace import (  # type: ignore[no-redef]
        assert_kernel_ingress_runtime_step_trace_report_contract,
    )
    from source_to_intent_research_kernel_ingress_runtime_step_trace import (
        build_report as build_kernel_ingress_runtime_step_trace_report,
    )

from tuc.frontend import (
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
)

SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT = (
    "source_to_intent_research_kernel_ingress_evidence_gate.ci.v0"
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_ACCEPTED_SOURCES = (
    "research_matmul_elementwise",
    "research_softmax_reduction",
    "research_matmul_reduction",
    "research_mvp_pipeline",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_ACCEPTED_KERNELS = (
    "matmul_elementwise",
    "softmax_reduction",
    "matmul_reduction",
    "mvp_pipeline",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)
SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_FORBIDDEN_FRAGMENTS = (
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


class SourceToIntentResearchKernelIngressEvidenceGateError(AssertionError):
    """Raised when Kernel Ingress evidence binding is incomplete."""


def build_gate_report(
    *,
    boundary_budget_text: str | None = None,
    conformance_gate_text: str | None = None,
    diagnostics_text: str | None = None,
    idiom_alignment_text: str | None = None,
    kernel_ingress_text: str | None = None,
    proof_bundle_text: str | None = None,
    rejection_coverage_text: str | None = None,
    runtime_backend_alignment_text: str | None = None,
    runtime_backend_equivalence_text: str | None = None,
    runtime_coverage_policy_text: str | None = None,
    runtime_evidence_bundle_index_text: str | None = None,
    runtime_matrix_text: str | None = None,
    runtime_step_trace_text: str | None = None,
) -> str:
    """Return stable CI-facing Kernel Ingress evidence binding."""

    kernel_ingress = (
        build_kernel_ingress_report()
        if kernel_ingress_text is None
        else kernel_ingress_text
    )
    boundary_budget = (
        build_kernel_ingress_boundary_budget_report()
        if boundary_budget_text is None
        else boundary_budget_text
    )
    runtime_matrix = (
        build_kernel_ingress_runtime_matrix_report()
        if runtime_matrix_text is None
        else runtime_matrix_text
    )
    runtime_step_trace = (
        build_kernel_ingress_runtime_step_trace_report()
        if runtime_step_trace_text is None
        else runtime_step_trace_text
    )
    runtime_evidence_bundle_index = (
        build_kernel_ingress_runtime_evidence_bundle_index_report()
        if runtime_evidence_bundle_index_text is None
        else runtime_evidence_bundle_index_text
    )
    runtime_backend_equivalence = (
        build_kernel_ingress_backend_equivalence_report()
        if runtime_backend_equivalence_text is None
        else runtime_backend_equivalence_text
    )
    runtime_coverage_policy = (
        build_kernel_ingress_runtime_coverage_policy_report()
        if runtime_coverage_policy_text is None
        else runtime_coverage_policy_text
    )
    runtime_backend_alignment = (
        build_kernel_ingress_runtime_backend_alignment_report()
        if runtime_backend_alignment_text is None
        else runtime_backend_alignment_text
    )
    rejection_coverage = (
        build_kernel_ingress_rejection_coverage_report()
        if rejection_coverage_text is None
        else rejection_coverage_text
    )
    diagnostics = (
        build_kernel_ingress_diagnostics_report()
        if diagnostics_text is None
        else diagnostics_text
    )
    conformance_gate = (
        build_kernel_ingress_conformance_gate_report()
        if conformance_gate_text is None
        else conformance_gate_text
    )
    idiom_alignment = (
        build_kernel_ingress_idiom_alignment_report()
        if idiom_alignment_text is None
        else idiom_alignment_text
    )
    proof_bundle = (
        build_kernel_ingress_proof_bundle_report()
        if proof_bundle_text is None
        else proof_bundle_text
    )
    _assert_kernel_ingress_bound(kernel_ingress)
    runtime_matrix_report = _assert_runtime_matrix_bound(runtime_matrix)
    runtime_step_trace_report = _assert_runtime_step_trace_bound(runtime_step_trace)
    runtime_evidence_bundle_index_report = _assert_runtime_evidence_bundle_index_bound(
        runtime_evidence_bundle_index
    )
    runtime_backend_equivalence_report = _assert_runtime_backend_equivalence_bound(
        runtime_backend_equivalence
    )
    _assert_runtime_coverage_policy_bound(runtime_coverage_policy)
    runtime_backend_alignment_report = _assert_runtime_backend_alignment_bound(
        runtime_backend_alignment
    )
    _assert_boundary_budget_bound(boundary_budget)
    _assert_rejection_coverage_bound(rejection_coverage)
    _assert_diagnostics_bound(diagnostics)
    _assert_conformance_gate_bound(conformance_gate)
    _assert_idiom_alignment_bound(idiom_alignment)
    _assert_proof_bundle_bound(
        proof_bundle,
        {
            "source_to_intent_research_kernel_ingress": kernel_ingress,
            "source_to_intent_research_kernel_ingress_runtime_matrix": (
                runtime_matrix
            ),
            "source_to_intent_research_kernel_ingress_runtime_step_trace": (
                runtime_step_trace
            ),
            "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index": (
                runtime_evidence_bundle_index
            ),
            "source_to_intent_research_kernel_ingress_backend_equivalence": (
                runtime_backend_equivalence
            ),
            "source_to_intent_research_kernel_ingress_runtime_coverage_policy": (
                runtime_coverage_policy
            ),
            "source_to_intent_research_kernel_ingress_runtime_backend_alignment": (
                runtime_backend_alignment
            ),
            "source_to_intent_research_kernel_ingress_boundary_budget": (
                boundary_budget
            ),
            "source_to_intent_research_kernel_ingress_rejection_coverage": (
                rejection_coverage
            ),
            "source_to_intent_research_kernel_ingress_diagnostics": diagnostics,
            "source_to_intent_research_kernel_ingress_conformance_gate": (
                conformance_gate
            ),
            "source_to_intent_research_kernel_ingress_idiom_alignment": (
                idiom_alignment
            ),
        },
    )
    report = _render_gate_report(
        kernel_ingress,
        runtime_matrix,
        runtime_coverage_policy,
        runtime_backend_alignment,
        runtime_matrix_report,
        runtime_step_trace,
        runtime_step_trace_report,
        runtime_evidence_bundle_index,
        runtime_evidence_bundle_index_report,
        runtime_backend_equivalence,
        runtime_backend_equivalence_report,
        runtime_backend_alignment_report,
        boundary_budget,
        rejection_coverage,
        diagnostics,
        conformance_gate,
        idiom_alignment,
        proof_bundle,
    )
    assert_kernel_ingress_evidence_gate_report_contract(report)
    return report


def main() -> None:
    print(build_gate_report(), end="")


def assert_kernel_ingress_evidence_gate_report_contract(text: object) -> None:
    """Fail closed unless the Kernel Ingress evidence gate text matches v0."""

    if not isinstance(text, str):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: gate output must be text"
        )
    required_fragments = (
        "source_to_intent.kernel_ingress_evidence_gate "
        "@source_to_intent_research_kernel_ingress_evidence_gate_v0 {",
        (
            f'  gate_contract = "'
            f'{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT}"'
        ),
        '  kernel_ingress = "passed"',
        '  runtime_matrix = "passed"',
        '  runtime_step_trace = "passed"',
        '  runtime_evidence_bundle_index = "passed"',
        '  runtime_backend_equivalence = "passed"',
        '  runtime_coverage_policy = "passed"',
        '  runtime_backend_alignment = "passed"',
        '  boundary_budget = "passed"',
        '  rejection_coverage = "passed"',
        '  diagnostics = "passed"',
        '  conformance_gate = "passed"',
        '  idiom_alignment = "passed"',
        '  proof_bundle = "passed"',
        (
            '  accepted_sources = "research_matmul_elementwise,'
            'research_softmax_reduction,research_matmul_reduction,'
            'research_mvp_pipeline"'
        ),
        (
            '  accepted_kernels = "matmul_elementwise,softmax_reduction,'
            'matmul_reduction,mvp_pipeline"'
        ),
        '  covered_operation_families = "elementwise,matmul,reduction,softmax"',
        (
            '  backend_sequences = "linear-sim->vector-sim,'
            'vector-sim->vector-sim,'
            'linear-sim->vector-sim->vector-sim->vector-sim"'
        ),
        '  trusted_executor_registry = "trusted_runtime_executor_registry.v0"',
        '  trusted_runtime_backends = "linear-sim,vector-sim"',
        '  runtime_case_count = "4"',
        '  runtime_step_trace_cases = "4"',
        '  runtime_evidence_bundle_cases = "4"',
        '  runtime_backend_equivalence_cases = "4"',
        '  backend_equivalence_comparisons = "4"',
        (
            '  baseline_backend_sequences = "reference-cpu->reference-cpu,'
            'reference-cpu->reference-cpu->reference-cpu->reference-cpu"'
        ),
        (
            '  runtime_evidence_sections = "tensor_store_evidence,'
            'input_manifest,output_manifest,reference_correctness,'
            'execution_receipt"'
        ),
        (
            '  mvp_pipeline_operation_path = "matmul->softmax'
            '->reduction->elementwise"'
        ),
        (
            '  required_runtime_digest_fields = "runtime_plan_digest,'
            'execution_trace_digest,reference_correctness_digest"'
        ),
        '  covered_rejections = "7"',
        (
            '  diagnostics_rejection_reasons = "import_from_statement,'
            'kernel_name_mismatch,multiple_kernel_functions,'
            'top_level_side_effect,unsupported_import"'
        ),
        '  budget_rejection_reasons = "module_byte_budget,module_line_budget"',
        f'  parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS}"',
        (
            f'  default_parser_status = "'
            f'{SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS}"'
        ),
        '  raw_source_policy = "omitted_by_policy"',
        '  raw_value_policy = "omitted_by_policy"',
        '  status = "PASS"',
        "}",
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise SourceToIntentResearchKernelIngressEvidenceGateError(
                "kernel ingress evidence gate failed: required binding missing"
            )
    for digest_field in (
        "kernel_ingress_digest",
        "runtime_matrix_digest",
        "runtime_step_trace_digest",
        "runtime_evidence_bundle_index_digest",
        "runtime_backend_equivalence_digest",
        "runtime_coverage_policy_digest",
        "runtime_backend_alignment_digest",
        "boundary_budget_digest",
        "rejection_coverage_digest",
        "diagnostics_digest",
        "conformance_gate_digest",
        "idiom_alignment_digest",
        "proof_bundle_digest",
    ):
        if f"  {digest_field} = \"sha256:" not in text:
            raise SourceToIntentResearchKernelIngressEvidenceGateError(
                "kernel ingress evidence gate failed: digest binding missing"
            )
    _assert_gate_text_is_source_free(text)


def _assert_kernel_ingress_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "kernel ingress")
    try:
        assert_kernel_ingress_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: kernel ingress binding missing"
        ) from exc
    if report["frontend_ingress_contract"] != SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: ingress contract drift"
        )
    _assert_gate_text_is_source_free(text)
    return report


def _assert_boundary_budget_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "boundary budget")
    try:
        assert_kernel_ingress_boundary_budget_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: boundary budget binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_runtime_matrix_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "runtime matrix")
    try:
        assert_kernel_ingress_runtime_matrix_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: runtime matrix binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_runtime_step_trace_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "runtime step trace")
    try:
        assert_kernel_ingress_runtime_step_trace_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: runtime step trace binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_runtime_evidence_bundle_index_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "runtime evidence bundle index")
    try:
        assert_kernel_ingress_runtime_evidence_bundle_index_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: "
            "runtime evidence bundle index binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_runtime_backend_equivalence_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "runtime backend equivalence")
    try:
        assert_kernel_ingress_backend_equivalence_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: "
            "runtime backend equivalence binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_runtime_coverage_policy_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "runtime coverage policy")
    try:
        assert_kernel_ingress_runtime_coverage_policy_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: runtime coverage policy binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_runtime_backend_alignment_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "runtime backend alignment")
    try:
        assert_kernel_ingress_runtime_backend_alignment_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: runtime backend alignment binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_rejection_coverage_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "rejection coverage")
    try:
        assert_kernel_ingress_rejection_coverage_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: rejection coverage binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_diagnostics_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "diagnostics")
    expected_values = {
        "accepted_case_count": 4,
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "diagnostics_contract": (
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_CONTRACT
        ),
        "ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "raw_source_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY,
        "raw_value_policy": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY,
        "rejected_case_count": 5,
        "rejection_reasons": sorted(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_DIAGNOSTICS_REJECTION_REASONS
        ),
    }
    for key, expected in expected_values.items():
        if report.get(key) != expected:
            raise SourceToIntentResearchKernelIngressEvidenceGateError(
                "kernel ingress evidence gate failed: diagnostics binding missing"
            )
    _assert_gate_text_is_source_free(text)
    return report


def _assert_conformance_gate_bound(text: str) -> None:
    if not isinstance(text, str):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: conformance gate not text"
        )
    required_fragments = (
        'source_intent_frontend_conformance = "passed"',
        (
            'ingress_sources = "research_matmul_elementwise,'
            'research_softmax_reduction,research_matmul_reduction,'
            'research_mvp_pipeline"'
        ),
        (
            'kernel_names = "matmul_elementwise,softmax_reduction,'
            'matmul_reduction,mvp_pipeline"'
        ),
        'status = "PASS"',
    )
    for fragment in required_fragments:
        if fragment not in text:
            raise SourceToIntentResearchKernelIngressEvidenceGateError(
                "kernel ingress evidence gate failed: conformance gate binding missing"
            )
    _assert_gate_text_is_source_free(text)


def _assert_idiom_alignment_bound(text: str) -> Mapping[str, object]:
    report = _load_json_report(text, "idiom alignment")
    try:
        assert_kernel_ingress_idiom_alignment_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: idiom alignment binding missing"
        ) from exc
    _assert_gate_text_is_source_free(text)
    return report


def _assert_proof_bundle_bound(
    text: str,
    artifact_texts: Mapping[str, str],
) -> Mapping[str, object]:
    report = _load_json_report(text, "proof bundle")
    try:
        assert_kernel_ingress_proof_bundle_report_contract(report)
    except (TypeError, ValueError) as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: proof bundle binding missing"
        ) from exc
    artifacts = report["artifacts"]
    if not isinstance(artifacts, list):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: proof bundle artifacts drift"
        )
    observed_digests = {
        artifact["artifact_id"]: artifact["digest"]
        for artifact in artifacts
        if isinstance(artifact, Mapping)
    }
    for artifact_id, artifact_text in artifact_texts.items():
        if observed_digests.get(artifact_id) != _digest(artifact_text):
            raise SourceToIntentResearchKernelIngressEvidenceGateError(
                "kernel ingress evidence gate failed: proof bundle digest drift"
            )
    _assert_gate_text_is_source_free(text)
    return report


def _render_gate_report(
    kernel_ingress_text: str,
    runtime_matrix_text: str,
    runtime_coverage_policy_text: str,
    runtime_backend_alignment_text: str,
    runtime_matrix_report: Mapping[str, object],
    runtime_step_trace_text: str,
    runtime_step_trace_report: Mapping[str, object],
    runtime_evidence_bundle_index_text: str,
    runtime_evidence_bundle_index_report: Mapping[str, object],
    runtime_backend_equivalence_text: str,
    runtime_backend_equivalence_report: Mapping[str, object],
    runtime_backend_alignment_report: Mapping[str, object],
    boundary_budget_text: str,
    rejection_coverage_text: str,
    diagnostics_text: str,
    conformance_gate_text: str,
    idiom_alignment_text: str,
    proof_bundle_text: str,
) -> str:
    rejection_coverage = json.loads(rejection_coverage_text)
    lines = [
        "source_to_intent.kernel_ingress_evidence_gate "
        "@source_to_intent_research_kernel_ingress_evidence_gate_v0 {"
    ]
    lines.append(
        "  gate_contract = "
        f'"{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_CONTRACT}"'
    )
    lines.append('  kernel_ingress = "passed"')
    lines.append(f'  kernel_ingress_digest = "{_digest(kernel_ingress_text)}"')
    lines.append('  runtime_matrix = "passed"')
    lines.append(f'  runtime_matrix_digest = "{_digest(runtime_matrix_text)}"')
    lines.append('  runtime_step_trace = "passed"')
    lines.append(
        f'  runtime_step_trace_digest = "{_digest(runtime_step_trace_text)}"'
    )
    lines.append('  runtime_evidence_bundle_index = "passed"')
    lines.append(
        "  runtime_evidence_bundle_index_digest = "
        f'"{_digest(runtime_evidence_bundle_index_text)}"'
    )
    lines.append('  runtime_backend_equivalence = "passed"')
    lines.append(
        "  runtime_backend_equivalence_digest = "
        f'"{_digest(runtime_backend_equivalence_text)}"'
    )
    lines.append('  runtime_coverage_policy = "passed"')
    lines.append(
        "  runtime_coverage_policy_digest = "
        f'"{_digest(runtime_coverage_policy_text)}"'
    )
    lines.append('  runtime_backend_alignment = "passed"')
    lines.append(
        "  runtime_backend_alignment_digest = "
        f'"{_digest(runtime_backend_alignment_text)}"'
    )
    lines.append('  boundary_budget = "passed"')
    lines.append(f'  boundary_budget_digest = "{_digest(boundary_budget_text)}"')
    lines.append('  rejection_coverage = "passed"')
    lines.append(
        f'  rejection_coverage_digest = "{_digest(rejection_coverage_text)}"'
    )
    lines.append('  diagnostics = "passed"')
    lines.append(f'  diagnostics_digest = "{_digest(diagnostics_text)}"')
    lines.append('  conformance_gate = "passed"')
    lines.append(f'  conformance_gate_digest = "{_digest(conformance_gate_text)}"')
    lines.append('  idiom_alignment = "passed"')
    lines.append(f'  idiom_alignment_digest = "{_digest(idiom_alignment_text)}"')
    lines.append('  proof_bundle = "passed"')
    lines.append(f'  proof_bundle_digest = "{_digest(proof_bundle_text)}"')
    lines.append(
        '  accepted_sources = "'
        + ",".join(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_ACCEPTED_SOURCES
        )
        + '"'
    )
    lines.append(
        '  accepted_kernels = "'
        + ",".join(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_ACCEPTED_KERNELS
        )
        + '"'
    )
    lines.append(
        '  covered_operation_families = "'
        + ",".join(
            SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_OPERATION_FAMILIES
        )
        + '"'
    )
    lines.append(
        '  backend_sequences = "'
        + ",".join(_string_list(runtime_matrix_report["backend_sequences"]))
        + '"'
    )
    lines.append(
        "  trusted_executor_registry = "
        f'"{runtime_backend_alignment_report["trusted_executor_registry"]}"'
    )
    lines.append(
        '  trusted_runtime_backends = "'
        + ",".join(_string_list(runtime_backend_alignment_report["required_backend_names"]))
        + '"'
    )
    lines.append(f'  runtime_case_count = "{runtime_matrix_report["case_count"]}"')
    lines.append(
        f'  runtime_step_trace_cases = "{runtime_step_trace_report["case_count"]}"'
    )
    lines.append(
        "  runtime_evidence_bundle_cases = "
        f'"{runtime_evidence_bundle_index_report["case_count"]}"'
    )
    lines.append(
        "  runtime_backend_equivalence_cases = "
        f'"{runtime_backend_equivalence_report["case_count"]}"'
    )
    lines.append(
        "  backend_equivalence_comparisons = "
        f'"{runtime_backend_equivalence_report["comparison_count"]}"'
    )
    lines.append(
        '  baseline_backend_sequences = "'
        + ",".join(
            _string_list(runtime_backend_equivalence_report["baseline_backend_sequences"])
        )
        + '"'
    )
    lines.append(
        '  runtime_evidence_sections = "'
        + ",".join(_string_list(runtime_evidence_bundle_index_report["runtime_evidence_sections"]))
        + '"'
    )
    lines.append(
        '  mvp_pipeline_operation_path = "'
        + "->".join(_mvp_pipeline_operation_path(runtime_step_trace_report))
        + '"'
    )
    lines.append(
        '  required_runtime_digest_fields = "runtime_plan_digest,'
        'execution_trace_digest,reference_correctness_digest"'
    )
    lines.append(
        f'  covered_rejections = "{rejection_coverage["covered_rejection_count"]}"'
    )
    lines.append(
        "  diagnostics_rejection_reasons = "
        f'"{",".join(rejection_coverage["diagnostics_rejection_reasons"])}"'
    )
    lines.append(
        "  budget_rejection_reasons = "
        f'"{",".join(rejection_coverage["budget_rejection_reasons"])}"'
    )
    lines.append(f'  parser_status = "{SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS}"')
    lines.append(
        f'  default_parser_status = "'
        f'{SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS}"'
    )
    lines.append(
        f'  raw_source_policy = "'
        f'{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_SOURCE_POLICY}"'
    )
    lines.append(
        f'  raw_value_policy = "'
        f'{SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RAW_VALUE_POLICY}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _load_json_report(text: str, label: str) -> Mapping[str, object]:
    if not isinstance(text, str):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            f"kernel ingress evidence gate failed: {label} not text"
        )
    try:
        report = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            f"kernel ingress evidence gate failed: {label} not JSON"
        ) from exc
    if not isinstance(report, Mapping):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            f"kernel ingress evidence gate failed: {label} report must be object"
        )
    return report


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: runtime matrix binding missing"
        )
    return [str(item) for item in value]


def _mvp_pipeline_operation_path(report: Mapping[str, object]) -> list[str]:
    cases = report["cases"]
    if not isinstance(cases, list):
        raise SourceToIntentResearchKernelIngressEvidenceGateError(
            "kernel ingress evidence gate failed: runtime step trace binding missing"
        )
    for case in cases:
        if isinstance(case, Mapping) and case.get("case_id") == (
            "research_module_mvp_pipeline"
        ):
            operation_path = case.get("operation_path")
            if not isinstance(operation_path, list):
                break
            return [str(item) for item in operation_path]
    raise SourceToIntentResearchKernelIngressEvidenceGateError(
        "kernel ingress evidence gate failed: runtime step trace binding missing"
    )


def _assert_gate_text_is_source_free(text: str) -> None:
    for fragment in (
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE_FORBIDDEN_FRAGMENTS
    ):
        if fragment in text:
            raise SourceToIntentResearchKernelIngressEvidenceGateError(
                "kernel ingress evidence gate failed: "
                "gate output contains forbidden source fragment"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
