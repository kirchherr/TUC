"""Run the CI-facing Runtime Evidence Gate."""

from hashlib import sha256

from examples.runtime_backend_equivalence import build_backend_equivalence_report
from examples.runtime_execution_receipt import (
    build_execution_receipt_evidence_reports,
    build_execution_receipt_report,
)
from examples.runtime_hs_ir_plan_alignment import build_alignment_report
from examples.runtime_input_manifest import build_input_manifest_report
from examples.runtime_layout_conversion_evidence import (
    build_current_runtime_layout_conversion_evidence_report,
)
from examples.runtime_layout_conversion_gate_readiness import (
    build_current_runtime_layout_conversion_gate_readiness_report,
)
from examples.runtime_layout_conversion_trace_index import (
    build_current_runtime_layout_conversion_trace_index_report,
)
from examples.runtime_memory_planning_gate import (
    build_gate_report as build_memory_planning_gate_report,
)
from examples.runtime_mixed_backend_equivalence import (
    build_mixed_backend_equivalence_report,
)
from examples.runtime_mixed_tensor_store_evidence import (
    build_mixed_tensor_store_evidence_report,
)
from examples.runtime_output_contract import build_output_contract_report
from examples.runtime_output_manifest import build_output_manifest_report
from examples.runtime_planning_explanation import (
    build_backend_equivalence_runtime_planning_explanation_report,
    build_mixed_backend_equivalence_runtime_planning_explanation_report,
)
from examples.runtime_public_output_bundle import build_public_output_bundle
from examples.runtime_reference_correctness import build_reference_correctness_report
from examples.runtime_tensor_store_evidence import build_tensor_store_evidence_report
from examples.runtime_transfer_trace_index import (
    build_current_runtime_transfer_trace_index_report,
)
from examples.runtime_vector_backend_equivalence import (
    build_vector_backend_equivalence_report,
)
from examples.source_intent_runtime_returns import run_evidence as run_runtime_returns
from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT,
    RuntimeBackendEquivalencePortfolioPolicyError,
    RuntimeBackendEquivalencePortfolioPolicyReport,
    RuntimeBackendEquivalencePortfolioReport,
    RuntimeBackendEquivalencePortfolioSlice,
    RuntimeBackendEquivalenceReport,
    RuntimeBackendEquivalenceRun,
    RuntimeEvidenceGateMatrixBinding,
    RuntimeEvidenceGateMatrixCoverageReport,
    RuntimeEvidenceGraph,
    RuntimeEvidenceMatrixReport,
    RuntimeExecutionEvidenceBundleReport,
    RuntimeExecutionOutputClosureReport,
    RuntimeExecutionReceiptReport,
    RuntimeExecutorConformanceReport,
    RuntimeHsIrPlanAlignmentReport,
    RuntimeInputManifestReport,
    RuntimeOutputContractReport,
    RuntimeOutputManifestReport,
    RuntimePlanningExplanationReport,
    RuntimePublicOutputBundle,
    RuntimeReferenceCorrectnessReport,
    RuntimeTensorStoreEvidenceReport,
    SourceIntentRuntimeReturnsReport,
    assert_runtime_backend_equivalence_portfolio_matches_policy,
    build_current_runtime_evidence_matrix_report,
    build_default_runtime_backend_equivalence_portfolio_policy_report,
    build_runtime_backend_equivalence_portfolio_report,
    build_runtime_evidence_gate_matrix_coverage_report,
    build_runtime_execution_evidence_bundle_report,
    build_runtime_execution_output_closure_report,
    run_runtime_executor_conformance,
)
from tuc.runtime.backend_equivalence import dump_runtime_backend_equivalence_report
from tuc.runtime.backend_equivalence_layout_binding import (
    RuntimeBackendEquivalenceLayoutBindingReport,
    assert_runtime_backend_equivalence_layout_binding,
    build_runtime_backend_equivalence_layout_binding_report,
)
from tuc.runtime.layout_conversion_digest_binding import (
    RuntimeLayoutConversionDigestBindingReport,
    assert_runtime_layout_conversion_digest_binding,
    build_runtime_layout_conversion_digest_binding_report,
)
from tuc.runtime.layout_conversion_evidence import (
    RuntimeLayoutConversionEvidenceReport,
    assert_runtime_layout_conversion_evidence,
    dump_runtime_layout_conversion_evidence_report,
)
from tuc.runtime.layout_conversion_gate_promotion_policy import (
    RuntimeLayoutConversionGatePromotionPolicyReport,
    assert_runtime_layout_conversion_gate_promotion_policy,
    build_runtime_layout_conversion_gate_promotion_policy_report,
)
from tuc.runtime.layout_conversion_gate_readiness import (
    RuntimeLayoutConversionGateReadinessReport,
    assert_runtime_layout_conversion_gate_readiness,
)
from tuc.runtime.layout_conversion_trace_index import (
    RuntimeLayoutConversionTraceIndexReport,
    assert_runtime_layout_conversion_trace_index,
    dump_runtime_layout_conversion_trace_index_report,
)
from tuc.runtime.layout_conversion_trace_replay_verifier import (
    RuntimeLayoutConversionTraceReplayVerifierReport,
    assert_runtime_layout_conversion_trace_replay_verifier,
    build_runtime_layout_conversion_trace_replay_verifier_report,
    dump_runtime_layout_conversion_trace_replay_verifier_report,
)
from tuc.runtime.transfer_trace_index import (
    RuntimeTransferTraceIndexReport,
    assert_runtime_transfer_trace_index,
)

SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID = "source_intent_return_mlp"
SOURCE_INTENT_RUNTIME_RETURNS_SOURCE_BOUNDARY = "source_intent_metadata"
SOURCE_INTENT_RUNTIME_RETURNS_REQUIRED_MATRIX_ARTIFACTS = (
    "source_intent_return_semantics",
    "source_intent_runtime_returns",
)
RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_ID = "runtime_evidence_gate_matrix_coverage"
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY = "runtime_backend_equivalence"
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY = "backend_equivalence"
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS = ("backend_equivalence",)
RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID = "runtime_backend_equivalence"
RUNTIME_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID = "runtime_backend_equivalence_systolic"
RUNTIME_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID = (
    "runtime_planning_explanation_systolic"
)
RUNTIME_TRANSFER_TRACE_INDEX_MATRIX_ARTIFACT_ID = "runtime_transfer_trace_index_systolic"
RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_REQUIRED_ARTIFACTS = (
    "backend_equivalence",
    "runtime_planning_explanation",
    "runtime_transfer_trace_index",
)
RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_ARTIFACT_IDS = (
    RUNTIME_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
    RUNTIME_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID,
    RUNTIME_TRANSFER_TRACE_INDEX_MATRIX_ARTIFACT_ID,
)
RUNTIME_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = "reference_cpu"
RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = "systolic_sim"
RUNTIME_BACKEND_EQUIVALENCE_BASELINE_BACKENDS = ("reference-cpu", "reference-cpu")
RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS = ("systolic-sim", "reference-cpu")
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_GRAPH_ID = "runtime_vector_backend_equivalence"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID = "runtime_backend_equivalence_vector"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = "reference_cpu"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = "vector_sim"
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_BACKENDS = (
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
)
RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS = (
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID = "runtime_mixed_backend_equivalence"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID = "runtime_backend_equivalence_mixed"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID = (
    "runtime_planning_explanation_mixed"
)
RUNTIME_HS_IR_PLAN_ALIGNMENT_MATRIX_ARTIFACT_ID = "runtime_hs_ir_plan_alignment_mixed"
RUNTIME_LAYOUT_CONVERSION_EVIDENCE_MATRIX_ARTIFACT_ID = "runtime_layout_conversion_evidence_mixed"
RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_MATRIX_ARTIFACT_ID = (
    "runtime_layout_conversion_trace_index_mixed"
)
RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_MATRIX_ARTIFACT_ID = (
    "runtime_layout_conversion_trace_replay_verifier_mixed"
)
RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MATRIX_ARTIFACT_ID = (
    "runtime_backend_equivalence_layout_binding_mixed"
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS = (
    "backend_equivalence",
    "runtime_planning_explanation",
    "runtime_hs_ir_plan_alignment",
    "runtime_layout_conversion_evidence",
    "runtime_layout_conversion_trace_index",
    "runtime_layout_conversion_trace_replay_verifier",
    "runtime_backend_equivalence_layout_binding",
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS = (
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
    RUNTIME_MIXED_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID,
    RUNTIME_HS_IR_PLAN_ALIGNMENT_MATRIX_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_EVIDENCE_MATRIX_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_MATRIX_ARTIFACT_ID,
    RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_MATRIX_ARTIFACT_ID,
    RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MATRIX_ARTIFACT_ID,
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_RUN_ID = "reference_cpu"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID = "mixed_accelerators"
RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_BACKENDS = (
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
)
RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS = (
    "systolic-sim",
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID = "runtime_backend_equivalence_portfolio"
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_BACKEND_FAMILIES = (
    "systolic-sim",
    "vector-sim",
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_GRAPH_FAMILY = "backend_equivalence_portfolio"
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_REQUIRED_ARTIFACTS = (
    "backend_equivalence_portfolio",
    "backend_equivalence_portfolio_policy",
)
RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_ARTIFACT_IDS = (
    "runtime_backend_equivalence_portfolio",
    "runtime_backend_equivalence_portfolio_policy",
)
RUNTIME_MEMORY_PLANNING_GRAPH_ID = "runtime_memory_planning"
RUNTIME_MEMORY_PLANNING_MATRIX_GRAPH_FAMILY = "runtime_memory_planning"
RUNTIME_MEMORY_PLANNING_MATRIX_SOURCE_BOUNDARY = "runtime_memory_planning"
RUNTIME_MEMORY_PLANNING_MATRIX_REQUIRED_ARTIFACTS = (
    "runtime_buffer_lifetime",
    "runtime_allocation_plan",
    "runtime_memory_budget",
    "runtime_allocation_request_manifest",
    "runtime_allocation_admission",
    "runtime_allocation_receipt",
    "runtime_allocation_reconciliation",
)
RUNTIME_MEMORY_PLANNING_MATRIX_ARTIFACT_IDS = (
    "runtime_buffer_lifetime_current",
    "runtime_allocation_plan_current",
    "runtime_memory_budget_current",
    "runtime_allocation_request_manifest_current",
    "runtime_allocation_admission_current",
    "runtime_allocation_receipt_current",
    "runtime_allocation_reconciliation_current",
)


class RuntimeEvidenceGateError(AssertionError):
    """Raised when required runtime evidence is incomplete."""


def build_gate_matrix_bindings() -> tuple[RuntimeEvidenceGateMatrixBinding, ...]:
    """Return Matrix bindings that Runtime Evidence Gate requires exactly."""

    return (
        RuntimeEvidenceGateMatrixBinding(
            binding_id="runtime_backend_equivalence_matrix",
            graph_id=RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID,
            graph_family=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY,
            source_boundary=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY,
            required_artifact_kinds=(
                RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_REQUIRED_ARTIFACTS
            ),
            artifact_ids=RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_ARTIFACT_IDS,
        ),
        RuntimeEvidenceGateMatrixBinding(
            binding_id="runtime_vector_backend_equivalence_matrix",
            graph_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_GRAPH_ID,
            graph_family=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY,
            source_boundary=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY,
            required_artifact_kinds=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS,
            artifact_ids=(RUNTIME_VECTOR_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,),
        ),
        RuntimeEvidenceGateMatrixBinding(
            binding_id="runtime_mixed_backend_equivalence_matrix",
            graph_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID,
            graph_family=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY,
            source_boundary=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY,
            required_artifact_kinds=(RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS),
            artifact_ids=RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS,
        ),
        RuntimeEvidenceGateMatrixBinding(
            binding_id="runtime_backend_equivalence_portfolio_matrix",
            graph_id=RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID,
            graph_family=RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_GRAPH_FAMILY,
            source_boundary=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY,
            required_artifact_kinds=(
                RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_REQUIRED_ARTIFACTS
            ),
            artifact_ids=RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_ARTIFACT_IDS,
        ),
        RuntimeEvidenceGateMatrixBinding(
            binding_id="runtime_memory_planning_matrix",
            graph_id=RUNTIME_MEMORY_PLANNING_GRAPH_ID,
            graph_family=RUNTIME_MEMORY_PLANNING_MATRIX_GRAPH_FAMILY,
            source_boundary=RUNTIME_MEMORY_PLANNING_MATRIX_SOURCE_BOUNDARY,
            required_artifact_kinds=RUNTIME_MEMORY_PLANNING_MATRIX_REQUIRED_ARTIFACTS,
            artifact_ids=RUNTIME_MEMORY_PLANNING_MATRIX_ARTIFACT_IDS,
        ),
    )


def build_gate_matrix_coverage_report(
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
) -> RuntimeEvidenceGateMatrixCoverageReport:
    """Return a data-only audit of Matrix bindings used by this gate."""

    matrix = (
        build_current_runtime_evidence_matrix_report() if matrix_report is None else matrix_report
    )
    return build_runtime_evidence_gate_matrix_coverage_report(
        RUNTIME_EVIDENCE_GATE_MATRIX_COVERAGE_ID,
        matrix,
        build_gate_matrix_bindings(),
    )


def build_gate_report(
    *,
    matrix_report: RuntimeEvidenceMatrixReport | None = None,
    conformance_report: RuntimeExecutorConformanceReport | None = None,
    backend_equivalence_report: RuntimeBackendEquivalenceReport | None = None,
    runtime_planning_explanation_report: (RuntimePlanningExplanationReport | None) = None,
    runtime_transfer_trace_index_report: RuntimeTransferTraceIndexReport | None = None,
    vector_backend_equivalence_report: (RuntimeBackendEquivalenceReport | None) = None,
    mixed_backend_equivalence_report: RuntimeBackendEquivalenceReport | None = None,
    mixed_runtime_planning_explanation_report: (RuntimePlanningExplanationReport | None) = None,
    runtime_hs_ir_plan_alignment_report: RuntimeHsIrPlanAlignmentReport | None = None,
    runtime_layout_conversion_evidence_report: (
        RuntimeLayoutConversionEvidenceReport | None
    ) = None,
    runtime_layout_conversion_trace_index_report: (
        RuntimeLayoutConversionTraceIndexReport | None
    ) = None,
    runtime_layout_conversion_trace_replay_verifier_report: (
        RuntimeLayoutConversionTraceReplayVerifierReport | None
    ) = None,
    runtime_backend_equivalence_layout_binding_report: (
        RuntimeBackendEquivalenceLayoutBindingReport | None
    ) = None,
    mixed_tensor_store_report: RuntimeTensorStoreEvidenceReport | None = None,
    runtime_layout_conversion_digest_binding_report: (
        RuntimeLayoutConversionDigestBindingReport | None
    ) = None,
    runtime_layout_conversion_gate_readiness_report: (
        RuntimeLayoutConversionGateReadinessReport | None
    ) = None,
    runtime_layout_conversion_gate_promotion_policy_report: (
        RuntimeLayoutConversionGatePromotionPolicyReport | None
    ) = None,
    backend_equivalence_portfolio_report: (RuntimeBackendEquivalencePortfolioReport | None) = None,
    backend_equivalence_portfolio_policy_report: (
        RuntimeBackendEquivalencePortfolioPolicyReport | None
    ) = None,
    execution_evidence_bundle_report: (RuntimeExecutionEvidenceBundleReport | None) = None,
    execution_receipt_report: RuntimeExecutionReceiptReport | None = None,
    input_manifest_report: RuntimeInputManifestReport | None = None,
    execution_output_closure_report: (RuntimeExecutionOutputClosureReport | None) = None,
    output_contract_report: RuntimeOutputContractReport | None = None,
    output_manifest_report: RuntimeOutputManifestReport | None = None,
    public_output_bundle: RuntimePublicOutputBundle | None = None,
    reference_correctness_report: RuntimeReferenceCorrectnessReport | None = None,
    source_intent_runtime_returns_report: (SourceIntentRuntimeReturnsReport | None) = None,
    memory_planning_gate_text: str | None = None,
    tensor_store_report: RuntimeTensorStoreEvidenceReport | None = None,
) -> str:
    """Return the stable CI-facing runtime evidence gate report."""

    matrix = (
        build_current_runtime_evidence_matrix_report() if matrix_report is None else matrix_report
    )
    gate_matrix_coverage = build_gate_matrix_coverage_report(matrix)
    conformance = (
        run_runtime_executor_conformance() if conformance_report is None else conformance_report
    )
    backend_equivalence = (
        build_backend_equivalence_report()
        if backend_equivalence_report is None
        else backend_equivalence_report
    )
    runtime_planning_explanation = (
        build_backend_equivalence_runtime_planning_explanation_report()
        if runtime_planning_explanation_report is None
        else runtime_planning_explanation_report
    )
    runtime_transfer_trace_index = (
        build_current_runtime_transfer_trace_index_report()
        if runtime_transfer_trace_index_report is None
        else runtime_transfer_trace_index_report
    )
    vector_backend_equivalence = (
        build_vector_backend_equivalence_report()
        if vector_backend_equivalence_report is None
        else vector_backend_equivalence_report
    )
    mixed_backend_equivalence = (
        build_mixed_backend_equivalence_report()
        if mixed_backend_equivalence_report is None
        else mixed_backend_equivalence_report
    )
    mixed_runtime_planning_explanation = (
        build_mixed_backend_equivalence_runtime_planning_explanation_report()
        if mixed_runtime_planning_explanation_report is None
        else mixed_runtime_planning_explanation_report
    )
    runtime_hs_ir_plan_alignment = (
        build_alignment_report()
        if runtime_hs_ir_plan_alignment_report is None
        else runtime_hs_ir_plan_alignment_report
    )
    runtime_layout_conversion_evidence = (
        build_current_runtime_layout_conversion_evidence_report()
        if runtime_layout_conversion_evidence_report is None
        else runtime_layout_conversion_evidence_report
    )
    runtime_layout_conversion_trace_index = (
        build_current_runtime_layout_conversion_trace_index_report()
        if runtime_layout_conversion_trace_index_report is None
        else runtime_layout_conversion_trace_index_report
    )
    runtime_layout_conversion_trace_replay_verifier = (
        runtime_layout_conversion_trace_replay_verifier_report
    )
    runtime_backend_equivalence_layout_binding = runtime_backend_equivalence_layout_binding_report
    mixed_tensor_store = (
        build_mixed_tensor_store_evidence_report()
        if mixed_tensor_store_report is None
        else mixed_tensor_store_report
    )
    runtime_layout_conversion_digest_binding = (
        build_runtime_layout_conversion_digest_binding_report(
            runtime_layout_conversion_evidence,
            runtime_hs_ir_plan_alignment,
            mixed_tensor_store,
        )
        if runtime_layout_conversion_digest_binding_report is None
        else runtime_layout_conversion_digest_binding_report
    )
    runtime_layout_conversion_gate_readiness = (
        build_current_runtime_layout_conversion_gate_readiness_report(
            source_evidence=runtime_layout_conversion_evidence,
            matrix_report=matrix,
            digest_binding_report=runtime_layout_conversion_digest_binding,
        )
        if runtime_layout_conversion_gate_readiness_report is None
        else runtime_layout_conversion_gate_readiness_report
    )
    runtime_layout_conversion_gate_promotion_policy = (
        build_runtime_layout_conversion_gate_promotion_policy_report(
            runtime_layout_conversion_gate_readiness,
        )
        if runtime_layout_conversion_gate_promotion_policy_report is None
        else runtime_layout_conversion_gate_promotion_policy_report
    )
    backend_equivalence_portfolio = (
        build_runtime_backend_equivalence_portfolio_report(
            RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID,
            (
                backend_equivalence,
                vector_backend_equivalence,
                mixed_backend_equivalence,
            ),
        )
        if backend_equivalence_portfolio_report is None
        else backend_equivalence_portfolio_report
    )
    backend_equivalence_portfolio_policy = (
        build_default_runtime_backend_equivalence_portfolio_policy_report()
        if backend_equivalence_portfolio_policy_report is None
        else backend_equivalence_portfolio_policy_report
    )
    tensor_store = (
        build_tensor_store_evidence_report() if tensor_store_report is None else tensor_store_report
    )
    input_manifest = (
        build_input_manifest_report() if input_manifest_report is None else input_manifest_report
    )
    output_manifest = (
        build_output_manifest_report() if output_manifest_report is None else output_manifest_report
    )
    output_contract = (
        build_output_contract_report() if output_contract_report is None else output_contract_report
    )
    public_bundle = (
        build_public_output_bundle() if public_output_bundle is None else public_output_bundle
    )
    reference_correctness = (
        build_reference_correctness_report()
        if reference_correctness_report is None
        else reference_correctness_report
    )
    execution_receipt_evidence = build_execution_receipt_evidence_reports()
    execution_output_contract = execution_receipt_evidence.output_contract
    execution_public_bundle = execution_receipt_evidence.public_output_bundle
    execution_receipt = (
        build_execution_receipt_report()
        if execution_receipt_report is None
        else execution_receipt_report
    )
    execution_evidence_bundle = (
        build_runtime_execution_evidence_bundle_report(
            tensor_store,
            input_manifest,
            output_manifest,
            execution_output_contract,
            execution_public_bundle,
            reference_correctness,
            execution_receipt,
        )
        if execution_evidence_bundle_report is None
        else execution_evidence_bundle_report
    )
    execution_output_closure = (
        build_runtime_execution_output_closure_report(
            execution_output_contract,
            execution_public_bundle,
            execution_receipt,
            execution_evidence_bundle,
        )
        if execution_output_closure_report is None
        else execution_output_closure_report
    )
    source_intent_runtime_returns = (
        run_runtime_returns().runtime_returns
        if source_intent_runtime_returns_report is None
        else source_intent_runtime_returns_report
    )
    memory_planning_gate = (
        build_memory_planning_gate_report()
        if memory_planning_gate_text is None
        else memory_planning_gate_text
    )
    _assert_matrix_complete(matrix)
    _assert_conformance_passed(conformance)
    _assert_backend_equivalence_passed(
        backend_equivalence,
        graph_id=RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID,
        baseline_run_id=RUNTIME_BACKEND_EQUIVALENCE_BASELINE_RUN_ID,
        candidate_run_id=RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
        baseline_backends=RUNTIME_BACKEND_EQUIVALENCE_BASELINE_BACKENDS,
        candidate_backends=RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS,
        label="runtime backend equivalence",
    )
    _assert_backend_equivalence_matrix_covered(
        matrix,
        backend_equivalence,
        artifact_id=RUNTIME_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
        required_artifact_kinds=(RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_REQUIRED_ARTIFACTS),
        label="runtime backend equivalence",
    )
    _assert_runtime_planning_explanation_passed(runtime_planning_explanation)
    _assert_runtime_planning_explanation_bound(
        runtime_planning_explanation,
        backend_equivalence,
    )
    _assert_runtime_planning_explanation_matrix_covered(
        matrix,
        runtime_planning_explanation,
    )
    _assert_runtime_transfer_trace_index_passed(runtime_transfer_trace_index)
    _assert_runtime_transfer_trace_index_bound(
        runtime_transfer_trace_index,
        runtime_planning_explanation,
        backend_equivalence,
    )
    _assert_runtime_transfer_trace_index_matrix_covered(
        matrix,
        runtime_transfer_trace_index,
    )
    _assert_backend_equivalence_passed(
        vector_backend_equivalence,
        graph_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_GRAPH_ID,
        baseline_run_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_RUN_ID,
        candidate_run_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
        baseline_backends=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_BASELINE_BACKENDS,
        candidate_backends=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS,
        label="runtime vector backend equivalence",
    )
    _assert_backend_equivalence_matrix_covered(
        matrix,
        vector_backend_equivalence,
        artifact_id=RUNTIME_VECTOR_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
        label="runtime vector backend equivalence",
    )
    _assert_backend_equivalence_passed(
        mixed_backend_equivalence,
        graph_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID,
        baseline_run_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_RUN_ID,
        candidate_run_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
        baseline_backends=RUNTIME_MIXED_BACKEND_EQUIVALENCE_BASELINE_BACKENDS,
        candidate_backends=RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_BACKENDS,
        label="runtime mixed backend equivalence",
    )
    _assert_backend_equivalence_matrix_covered(
        matrix,
        mixed_backend_equivalence,
        artifact_id=RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID,
        required_artifact_kinds=(RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS),
        label="runtime mixed backend equivalence",
    )
    _assert_runtime_planning_explanation_passed(mixed_runtime_planning_explanation)
    _assert_mixed_runtime_planning_explanation_bound(
        mixed_runtime_planning_explanation,
        mixed_backend_equivalence,
    )
    _assert_mixed_runtime_planning_explanation_matrix_covered(
        matrix,
        mixed_runtime_planning_explanation,
    )
    _assert_runtime_hs_ir_plan_alignment_passed(runtime_hs_ir_plan_alignment)
    _assert_runtime_hs_ir_plan_alignment_bound(
        runtime_hs_ir_plan_alignment,
        mixed_backend_equivalence,
    )
    _assert_runtime_hs_ir_plan_alignment_matrix_covered(
        matrix,
        runtime_hs_ir_plan_alignment,
    )
    _assert_runtime_layout_conversion_evidence_passed(
        runtime_layout_conversion_evidence,
    )
    _assert_runtime_layout_conversion_evidence_bound(
        runtime_layout_conversion_evidence,
        mixed_backend_equivalence,
        mixed_runtime_planning_explanation,
        runtime_hs_ir_plan_alignment,
    )
    _assert_runtime_layout_conversion_evidence_matrix_covered(
        matrix,
        runtime_layout_conversion_evidence,
    )
    _assert_runtime_layout_conversion_trace_index_passed(
        runtime_layout_conversion_trace_index,
    )
    _assert_runtime_layout_conversion_trace_index_bound(
        runtime_layout_conversion_trace_index,
        runtime_layout_conversion_evidence,
        mixed_backend_equivalence,
    )
    _assert_runtime_layout_conversion_trace_index_matrix_covered(
        matrix,
        runtime_layout_conversion_trace_index,
    )
    if runtime_layout_conversion_trace_replay_verifier is None:
        runtime_layout_conversion_trace_replay_verifier = (
            build_runtime_layout_conversion_trace_replay_verifier_report(
                dump_runtime_layout_conversion_evidence_report(runtime_layout_conversion_evidence),
                dump_runtime_layout_conversion_trace_index_report(
                    runtime_layout_conversion_trace_index
                ),
            )
        )
    _assert_runtime_layout_conversion_trace_replay_verifier_passed(
        runtime_layout_conversion_trace_replay_verifier,
    )
    _assert_runtime_layout_conversion_trace_replay_verifier_bound(
        runtime_layout_conversion_trace_replay_verifier,
        runtime_layout_conversion_evidence,
        runtime_layout_conversion_trace_index,
    )
    _assert_runtime_layout_conversion_trace_replay_verifier_matrix_covered(
        matrix,
        runtime_layout_conversion_trace_replay_verifier,
    )
    if runtime_backend_equivalence_layout_binding is None:
        runtime_backend_equivalence_layout_binding = (
            build_runtime_backend_equivalence_layout_binding_report(
                dump_runtime_backend_equivalence_report(mixed_backend_equivalence),
                dump_runtime_layout_conversion_trace_replay_verifier_report(
                    runtime_layout_conversion_trace_replay_verifier
                ),
            )
        )
    _assert_runtime_backend_equivalence_layout_binding_passed(
        runtime_backend_equivalence_layout_binding,
    )
    _assert_runtime_backend_equivalence_layout_binding_bound(
        runtime_backend_equivalence_layout_binding,
        mixed_backend_equivalence,
        runtime_layout_conversion_trace_replay_verifier,
    )
    _assert_runtime_backend_equivalence_layout_binding_matrix_covered(
        matrix,
        runtime_backend_equivalence_layout_binding,
    )
    _assert_mixed_tensor_store_passed(mixed_tensor_store)
    _assert_runtime_layout_conversion_digest_binding_passed(
        runtime_layout_conversion_digest_binding,
    )
    _assert_runtime_layout_conversion_digest_binding_bound(
        runtime_layout_conversion_digest_binding,
        runtime_layout_conversion_evidence,
        runtime_hs_ir_plan_alignment,
        mixed_tensor_store,
    )
    _assert_runtime_layout_conversion_gate_readiness_passed(
        runtime_layout_conversion_gate_readiness,
    )
    _assert_runtime_layout_conversion_promotion_policy_bound(
        runtime_layout_conversion_gate_promotion_policy,
        runtime_layout_conversion_gate_readiness,
        runtime_layout_conversion_digest_binding,
    )
    _assert_backend_equivalence_portfolio_passed(
        backend_equivalence_portfolio,
        (
            backend_equivalence,
            vector_backend_equivalence,
            mixed_backend_equivalence,
        ),
    )
    _assert_backend_equivalence_portfolio_matrix_covered(
        matrix,
        backend_equivalence_portfolio,
    )
    _assert_backend_equivalence_portfolio_policy_bound(
        backend_equivalence_portfolio_policy,
        backend_equivalence_portfolio,
    )
    _assert_gate_matrix_coverage_passed(gate_matrix_coverage)
    _assert_runtime_memory_planning_gate_passed(memory_planning_gate)
    _assert_runtime_memory_planning_matrix_covered(matrix)
    _assert_tensor_store_evidence_passed(tensor_store)
    _assert_input_manifest_passed(input_manifest)
    _assert_output_manifest_passed(output_manifest)
    _assert_output_contract_passed(output_contract)
    _assert_public_output_bundle_passed(public_bundle, output_contract)
    _assert_reference_correctness_passed(reference_correctness)
    _assert_execution_receipt_passed(execution_receipt)
    _assert_execution_receipt_matches_gate_reports(
        execution_receipt,
        tensor_store,
        input_manifest,
        output_manifest,
        execution_output_contract,
        execution_public_bundle,
        reference_correctness,
    )
    _assert_execution_evidence_bundle_passed(execution_evidence_bundle)
    _assert_execution_evidence_bundle_matches_gate_reports(
        execution_evidence_bundle,
        tensor_store,
        input_manifest,
        output_manifest,
        execution_output_contract,
        execution_public_bundle,
        reference_correctness,
        execution_receipt,
    )
    _assert_execution_output_closure_passed(execution_output_closure)
    _assert_execution_output_closure_matches_gate_reports(
        execution_output_closure,
        execution_output_contract,
        execution_public_bundle,
        execution_receipt,
        execution_evidence_bundle,
    )
    _assert_source_intent_runtime_returns_passed(source_intent_runtime_returns)
    _assert_source_intent_runtime_returns_matrix_covered(
        matrix,
        source_intent_runtime_returns,
    )
    return _render_gate_report(
        matrix,
        conformance,
        backend_equivalence,
        runtime_planning_explanation,
        runtime_transfer_trace_index,
        vector_backend_equivalence,
        mixed_backend_equivalence,
        mixed_runtime_planning_explanation,
        runtime_hs_ir_plan_alignment,
        runtime_layout_conversion_evidence,
        runtime_layout_conversion_trace_index,
        runtime_layout_conversion_trace_replay_verifier,
        runtime_backend_equivalence_layout_binding,
        runtime_layout_conversion_digest_binding,
        runtime_layout_conversion_gate_readiness,
        runtime_layout_conversion_gate_promotion_policy,
        backend_equivalence_portfolio,
        backend_equivalence_portfolio_policy,
        gate_matrix_coverage,
        memory_planning_gate,
        tensor_store,
        input_manifest,
        output_manifest,
        output_contract,
        public_bundle,
        reference_correctness,
        execution_receipt,
        execution_evidence_bundle,
        execution_output_closure,
        source_intent_runtime_returns,
    )


def main() -> None:
    print(build_gate_report(), end="")


def _assert_matrix_complete(report: RuntimeEvidenceMatrixReport) -> None:
    if not report.runtime_evidence_matrix_complete:
        issues = ",".join(report.issues)
        raise RuntimeEvidenceGateError(f"runtime evidence matrix incomplete: {issues}")


def _assert_conformance_passed(report: RuntimeExecutorConformanceReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.executor_name}:{issue.case_name}:{issue.message}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime executor conformance failed: {issues}")


def _assert_backend_equivalence_passed(
    report: RuntimeBackendEquivalenceReport,
    *,
    graph_id: str,
    baseline_run_id: str,
    candidate_run_id: str,
    baseline_backends: tuple[str, ...],
    candidate_backends: tuple[str, ...],
    label: str,
) -> None:
    if not isinstance(report, RuntimeBackendEquivalenceReport):
        raise RuntimeEvidenceGateError(f"{label} failed: not a report object")
    if report.issues:
        issues = ",".join(f"{issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"{label} failed: {issues}")
    if report.graph_name != graph_id:
        raise RuntimeEvidenceGateError(f"{label} binding failed: graph_name_mismatch")
    if report.baseline_run_id != baseline_run_id:
        raise RuntimeEvidenceGateError(f"{label} binding failed: baseline_run_id_mismatch")
    if report.candidate_run_id != candidate_run_id:
        raise RuntimeEvidenceGateError(f"{label} binding failed: candidate_run_id_mismatch")
    runs = {run.run_id: run for run in report.runs}
    baseline = runs.get(baseline_run_id)
    candidate = runs.get(candidate_run_id)
    if baseline is None or candidate is None:
        raise RuntimeEvidenceGateError(f"{label} binding failed: missing_expected_run")
    if baseline.planned_backend_sequence != baseline_backends:
        raise RuntimeEvidenceGateError(f"{label} binding failed: baseline_backends_mismatch")
    if candidate.planned_backend_sequence != candidate_backends:
        raise RuntimeEvidenceGateError(f"{label} binding failed: candidate_backends_mismatch")
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(f"{label} binding failed: raw_value_policy_mismatch")
    if any(comparison.comparison_status != "matched" for comparison in report.comparisons):
        raise RuntimeEvidenceGateError(f"{label} binding failed: comparison_not_matched")


def _assert_backend_equivalence_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeBackendEquivalenceReport,
    *,
    artifact_id: str,
    required_artifact_kinds: tuple[str, ...] = (
        RUNTIME_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    ),
    label: str,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(f"{label} matrix coverage failed: graph missing")
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(f"{label} matrix coverage failed: graph_family_mismatch")
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(f"{label} matrix coverage failed: source_boundary_mismatch")
    if graph.required_artifact_kinds != required_artifact_kinds:
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            f"{label} matrix coverage failed: runtime evidence incomplete"
        )
    missing_artifacts = tuple(
        artifact_kind
        for artifact_kind in required_artifact_kinds
        if artifact_kind not in graph.present_artifact_kinds
    )
    if missing_artifacts:
        missing = ",".join(missing_artifacts)
        raise RuntimeEvidenceGateError(f"{label} matrix coverage failed: missing {missing}")
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind == "backend_equivalence"
    )
    if artifact_ids != (artifact_id,):
        raise RuntimeEvidenceGateError(f"{label} matrix coverage failed: artifact_id_mismatch")


def _assert_runtime_planning_explanation_passed(
    report: RuntimePlanningExplanationReport,
) -> None:
    if not isinstance(report, RuntimePlanningExplanationReport):
        raise RuntimeEvidenceGateError("runtime planning explanation failed: not a report object")
    if not report.passed:
        issues = ",".join(f"{issue.operation_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime planning explanation failed: {issues}")


def _assert_runtime_planning_explanation_bound(
    report: RuntimePlanningExplanationReport,
    backend_equivalence: RuntimeBackendEquivalenceReport,
) -> None:
    if report.graph_name != RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation binding failed: graph_name_mismatch"
        )
    runs = {run.run_id: run for run in backend_equivalence.runs}
    candidate = runs.get(RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID)
    if candidate is None:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation binding failed: missing_candidate_run"
        )
    if report.backend_sequence != candidate.planned_backend_sequence:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation binding failed: backend_sequence_mismatch"
        )
    if report.operation_count != len(candidate.planned_backend_sequence):
        raise RuntimeEvidenceGateError(
            "runtime planning explanation binding failed: operation_count_mismatch"
        )
    if report.candidate_score_mode != "recorded" or report.candidate_score_count < 1:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation binding failed: candidate_scores_missing"
        )
    if "fallback" not in report.selection_kinds or report.fallback_count != 1:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation binding failed: fallback_not_explained"
        )


def _assert_runtime_planning_explanation_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimePlanningExplanationReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation matrix coverage failed: source_boundary_mismatch"
        )
    if (
        graph.required_artifact_kinds
        != RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_REQUIRED_ARTIFACTS
    ):
        raise RuntimeEvidenceGateError(
            "runtime planning explanation matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime planning explanation matrix coverage failed: runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind == "runtime_planning_explanation"
    )
    if artifact_ids != (RUNTIME_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID,):
        raise RuntimeEvidenceGateError(
            "runtime planning explanation matrix coverage failed: artifact_id_mismatch"
        )


def _assert_runtime_transfer_trace_index_passed(
    report: RuntimeTransferTraceIndexReport,
) -> None:
    try:
        assert_runtime_transfer_trace_index(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(f"runtime transfer trace index failed: {exc}") from exc
    if report.graph_name != RUNTIME_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: graph_name_mismatch"
        )
    if report.transfer_count < 1 or report.trace_step_count < 1:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: records_missing"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: raw_value_policy_mismatch"
        )
    if report.execution_policy != "does_not_execute_transfers":
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: execution_policy_mismatch"
        )
    if report.trace_materialization_policy != "transfer_not_materialized_as_runtime_step":
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: trace_materialization_policy_mismatch"
        )
    if report.cost_claim_status != "planning_estimate_not_measurement":
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: cost_claim_status_mismatch"
        )
    if report.residency_claim_status != "not_physical_residency_evidence":
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: residency_claim_status_mismatch"
        )


def _assert_runtime_transfer_trace_index_bound(
    trace_index: RuntimeTransferTraceIndexReport,
    planning_explanation: RuntimePlanningExplanationReport,
    backend_equivalence: RuntimeBackendEquivalenceReport,
) -> None:
    if trace_index.graph_name != planning_explanation.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: planning_graph_mismatch"
        )
    if trace_index.graph_name != backend_equivalence.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: equivalence_graph_mismatch"
        )
    if trace_index.transfer_count != planning_explanation.transfer_edge_count:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: transfer_count_mismatch"
        )
    if trace_index.total_planned_bytes != planning_explanation.total_transfer_bytes:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: transfer_bytes_mismatch"
        )
    candidate_run = _runtime_backend_equivalence_run(
        backend_equivalence,
        RUNTIME_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
    )
    if trace_index.trace_step_count != candidate_run.trace_step_count:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index binding failed: trace_step_count_mismatch"
        )
    if trace_index.transfer_count == 1 and len(candidate_run.planned_backend_sequence) == 2:
        record = trace_index.records[0]
        transfer_backend_pair = (
            record.producer_planned_backend,
            record.consumer_planned_backend,
        )
        if transfer_backend_pair != candidate_run.planned_backend_sequence:
            raise RuntimeEvidenceGateError(
                "runtime transfer trace index binding failed: transfer_backend_mismatch"
            )


def _assert_runtime_transfer_trace_index_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeTransferTraceIndexReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index matrix coverage failed: source_boundary_mismatch"
        )
    if (
        graph.required_artifact_kinds
        != RUNTIME_BACKEND_EQUIVALENCE_SYSTOLIC_MATRIX_REQUIRED_ARTIFACTS
    ):
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index matrix coverage failed: runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind == "runtime_transfer_trace_index"
    )
    if artifact_ids != (RUNTIME_TRANSFER_TRACE_INDEX_MATRIX_ARTIFACT_ID,):
        raise RuntimeEvidenceGateError(
            "runtime transfer trace index matrix coverage failed: artifact_id_mismatch"
        )


def _assert_mixed_runtime_planning_explanation_bound(
    report: RuntimePlanningExplanationReport,
    mixed_equivalence: RuntimeBackendEquivalenceReport,
) -> None:
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: graph_name_mismatch"
        )
    runs = {run.run_id: run for run in mixed_equivalence.runs}
    candidate = runs.get(RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID)
    if candidate is None:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: missing_candidate_run"
        )
    if report.backend_sequence != candidate.planned_backend_sequence:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: backend_sequence_mismatch"
        )
    if report.operation_count != len(candidate.planned_backend_sequence):
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: operation_count_mismatch"
        )
    if report.candidate_score_mode != "recorded" or report.candidate_score_count < 1:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: candidate_scores_missing"
        )
    if "fallback" in report.selection_kinds or report.fallback_count != 0:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: fallback_unexpected"
        )
    if report.selection_kinds != ("preferred_for",):
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: selection_kinds_mismatch"
        )
    if report.layout_conversion_count < 1 or report.total_data_movement_bytes < 1:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation binding failed: movement_not_explained"
        )


def _assert_mixed_runtime_planning_explanation_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimePlanningExplanationReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation matrix coverage failed: source_boundary_mismatch"
        )
    if graph.required_artifact_kinds != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation matrix coverage failed: runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind == "runtime_planning_explanation"
    )
    if artifact_ids != (RUNTIME_MIXED_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID,):
        raise RuntimeEvidenceGateError(
            "runtime mixed planning explanation matrix coverage failed: artifact_id_mismatch"
        )


def _assert_runtime_hs_ir_plan_alignment_passed(
    report: RuntimeHsIrPlanAlignmentReport,
) -> None:
    if not isinstance(report, RuntimeHsIrPlanAlignmentReport):
        raise RuntimeEvidenceGateError("runtime HS-IR plan alignment failed: not a report object")
    if not report.passed:
        issues = ",".join(f"{issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime HS-IR plan alignment failed: {issues}")
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: raw_value_policy_mismatch"
        )


def _assert_runtime_hs_ir_plan_alignment_bound(
    report: RuntimeHsIrPlanAlignmentReport,
    mixed_equivalence: RuntimeBackendEquivalenceReport,
) -> None:
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: graph_name_mismatch"
        )
    if (
        report.partition_plan_graph_name != report.graph_name
        or report.execution_trace_graph_name != report.graph_name
    ):
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: graph_binding_mismatch"
        )
    runs = {run.run_id: run for run in mixed_equivalence.runs}
    candidate = runs.get(RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID)
    if candidate is None:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: missing_candidate_run"
        )
    if report.partition_backend_sequence != candidate.planned_backend_sequence:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: backend_sequence_mismatch"
        )
    if report.hs_ir_backend_sequence != report.partition_backend_sequence:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: hs_ir_plan_mismatch"
        )
    if report.execution_trace_backend_sequence != report.partition_backend_sequence:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: trace_plan_mismatch"
        )
    if report.step_count != len(candidate.planned_backend_sequence):
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment binding failed: step_count_mismatch"
        )


def _assert_runtime_hs_ir_plan_alignment_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeHsIrPlanAlignmentReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment matrix coverage failed: source_boundary_mismatch"
        )
    if graph.required_artifact_kinds != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment matrix coverage failed: runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime HS-IR plan alignment matrix coverage failed: artifact_id_mismatch"
        )


def _assert_runtime_layout_conversion_evidence_passed(
    report: RuntimeLayoutConversionEvidenceReport,
) -> None:
    try:
        assert_runtime_layout_conversion_evidence(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(f"runtime layout conversion evidence failed: {exc}") from exc
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: graph_name_mismatch"
        )
    if len(report.conversions) < 1 or report.total_planned_bytes < 1:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: conversions_missing"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: raw_value_policy_mismatch"
        )
    if report.execution_policy != "does_not_execute_conversions":
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: execution_policy_mismatch"
        )


def _assert_runtime_layout_conversion_evidence_bound(
    report: RuntimeLayoutConversionEvidenceReport,
    mixed_equivalence: RuntimeBackendEquivalenceReport,
    mixed_planning: RuntimePlanningExplanationReport,
    hs_ir_alignment: RuntimeHsIrPlanAlignmentReport,
) -> None:
    if report.graph_name != mixed_equivalence.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: equivalence_graph_mismatch"
        )
    if report.graph_name != mixed_planning.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: planning_graph_mismatch"
        )
    if report.graph_name != hs_ir_alignment.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: hs_ir_graph_mismatch"
        )
    if len(report.conversions) != mixed_planning.layout_conversion_count:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: planning_count_mismatch"
        )
    if report.total_planned_bytes != mixed_planning.total_layout_conversion_bytes:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: planning_bytes_mismatch"
        )
    if len(report.conversions) != hs_ir_alignment.partition_layout_conversion_count:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: hs_ir_count_mismatch"
        )
    if report.total_planned_bytes != hs_ir_alignment.partition_total_layout_conversion_bytes:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence binding failed: hs_ir_bytes_mismatch"
        )


def _assert_runtime_layout_conversion_evidence_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeLayoutConversionEvidenceReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence matrix coverage failed: source_boundary_mismatch"
        )
    if graph.required_artifact_kinds != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence matrix coverage failed: runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion evidence matrix coverage failed: artifact_id_mismatch"
        )


def _assert_runtime_layout_conversion_trace_index_passed(
    report: RuntimeLayoutConversionTraceIndexReport,
) -> None:
    try:
        assert_runtime_layout_conversion_trace_index(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime layout conversion trace index failed: {exc}"
        ) from exc
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: graph_name_mismatch"
        )
    if report.conversion_count < 1 or report.trace_step_count < 1:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: records_missing"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: raw_value_policy_mismatch"
        )
    if report.execution_policy != "does_not_execute_conversions":
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: execution_policy_mismatch"
        )
    if report.trace_materialization_policy != ("conversion_not_materialized_as_runtime_step"):
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: "
            "trace_materialization_policy_mismatch"
        )


def _assert_runtime_layout_conversion_trace_index_bound(
    trace_index: RuntimeLayoutConversionTraceIndexReport,
    layout_conversion: RuntimeLayoutConversionEvidenceReport,
    mixed_equivalence: RuntimeBackendEquivalenceReport,
) -> None:
    if trace_index.graph_name != layout_conversion.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: layout_conversion_graph_mismatch"
        )
    if trace_index.graph_name != mixed_equivalence.graph_name:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: equivalence_graph_mismatch"
        )
    if trace_index.conversion_count != len(layout_conversion.conversions):
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: conversion_count_mismatch"
        )
    if trace_index.source_partition_plan_digest != layout_conversion.source_partition_plan_digest:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: partition_plan_digest_mismatch"
        )
    expected_evidence_digest = _digest_text(
        dump_runtime_layout_conversion_evidence_report(layout_conversion)
    )
    if trace_index.source_layout_conversion_evidence_digest != expected_evidence_digest:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: source_evidence_digest_mismatch"
        )
    candidate_run = _runtime_backend_equivalence_run(
        mixed_equivalence,
        RUNTIME_MIXED_BACKEND_EQUIVALENCE_CANDIDATE_RUN_ID,
    )
    if trace_index.trace_step_count != candidate_run.trace_step_count:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index binding failed: trace_step_count_mismatch"
        )


def _assert_runtime_layout_conversion_trace_index_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeLayoutConversionTraceIndexReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index matrix coverage failed: source_boundary_mismatch"
        )
    if graph.required_artifact_kinds != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index matrix coverage failed: "
            "required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index matrix coverage failed: "
            "runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace index matrix coverage failed: artifact_id_mismatch"
        )


def _assert_runtime_layout_conversion_trace_replay_verifier_passed(
    report: RuntimeLayoutConversionTraceReplayVerifierReport,
) -> None:
    try:
        assert_runtime_layout_conversion_trace_replay_verifier(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime layout conversion trace replay verifier failed: {exc}"
        ) from exc
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace replay verifier failed: graph_name_mismatch"
        )
    if report.check_count != 6:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace replay verifier failed: check_count_mismatch"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace replay verifier failed: raw_value_policy_mismatch"
        )


def _assert_runtime_layout_conversion_trace_replay_verifier_bound(
    replay: RuntimeLayoutConversionTraceReplayVerifierReport,
    layout_conversion: RuntimeLayoutConversionEvidenceReport,
    trace_index: RuntimeLayoutConversionTraceIndexReport,
) -> None:
    expected = {
        "graph_name": layout_conversion.graph_name,
        "layout_conversion_evidence_report_digest": _digest_text(
            dump_runtime_layout_conversion_evidence_report(layout_conversion)
        ),
        "layout_conversion_trace_index_report_digest": _digest_text(
            dump_runtime_layout_conversion_trace_index_report(trace_index)
        ),
        "source_partition_plan_digest": layout_conversion.source_partition_plan_digest,
        "source_layout_conversion_evidence_digest": (
            trace_index.source_layout_conversion_evidence_digest
        ),
        "conversion_metadata_digest": layout_conversion.conversion_metadata_digest,
        "trace_index_conversion_metadata_digest": (layout_conversion.conversion_metadata_digest),
        "raw_value_policy": "omitted_by_policy",
    }
    for field_name, expected_value in expected.items():
        if getattr(replay, field_name) != expected_value:
            raise RuntimeEvidenceGateError(
                "runtime layout conversion trace replay verifier binding failed: "
                f"{field_name}_mismatch"
            )


def _assert_runtime_layout_conversion_trace_replay_verifier_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeLayoutConversionTraceReplayVerifierReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace replay verifier matrix coverage failed: graph missing"
        )
    if graph.required_artifact_kinds != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace replay verifier matrix coverage failed: "
            "required_artifacts_mismatch"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion trace replay verifier matrix coverage failed: "
            "artifact_id_mismatch"
        )


def _assert_runtime_backend_equivalence_layout_binding_passed(
    report: RuntimeBackendEquivalenceLayoutBindingReport,
) -> None:
    try:
        assert_runtime_backend_equivalence_layout_binding(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime backend equivalence layout binding failed: {exc}"
        ) from exc
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding failed: graph_name_mismatch"
        )
    if report.check_count != 8:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding failed: check_count_mismatch"
        )
    if report.candidate_backend_count < 2:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding failed: candidate_not_mixed"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding failed: raw_value_policy_mismatch"
        )


def _assert_runtime_backend_equivalence_layout_binding_bound(
    binding: RuntimeBackendEquivalenceLayoutBindingReport,
    mixed_equivalence: RuntimeBackendEquivalenceReport,
    replay: RuntimeLayoutConversionTraceReplayVerifierReport,
) -> None:
    expected = {
        "graph_name": mixed_equivalence.graph_name,
        "baseline_run_id": mixed_equivalence.baseline_run_id,
        "candidate_run_id": mixed_equivalence.candidate_run_id,
        "backend_equivalence_report_digest": _digest_text(
            dump_runtime_backend_equivalence_report(mixed_equivalence)
        ),
        "layout_trace_replay_report_digest": _digest_text(
            dump_runtime_layout_conversion_trace_replay_verifier_report(replay)
        ),
        "backend_equivalence_comparison_metadata_digest": (
            mixed_equivalence.comparison_metadata_digest
        ),
        "layout_trace_replay_metadata_digest": replay.replay_metadata_digest,
        "layout_replay_check_count": replay.check_count,
        "raw_value_policy": "omitted_by_policy",
    }
    for field_name, expected_value in expected.items():
        if getattr(binding, field_name) != expected_value:
            raise RuntimeEvidenceGateError(
                f"runtime backend equivalence layout binding failed: {field_name}_mismatch"
            )


def _assert_runtime_backend_equivalence_layout_binding_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeBackendEquivalenceLayoutBindingReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.graph_name)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding matrix coverage failed: graph missing"
        )
    if graph.required_artifact_kinds != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding matrix coverage failed: "
            "required_artifacts_mismatch"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence layout binding matrix coverage failed: "
            "artifact_id_mismatch"
        )


def _assert_mixed_tensor_store_passed(
    report: RuntimeTensorStoreEvidenceReport,
) -> None:
    if not isinstance(report, RuntimeTensorStoreEvidenceReport):
        raise RuntimeEvidenceGateError(
            "runtime mixed tensor store evidence failed: not a report object"
        )
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime mixed tensor store evidence binding failed: graph_name_mismatch"
        )
    if report.issues:
        issues = ",".join(f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime mixed tensor store evidence failed: {issues}")
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime mixed tensor store evidence binding failed: raw_value_policy_mismatch"
        )


def _assert_runtime_layout_conversion_digest_binding_passed(
    report: RuntimeLayoutConversionDigestBindingReport,
) -> None:
    try:
        assert_runtime_layout_conversion_digest_binding(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime layout conversion digest binding failed: {exc}"
        ) from exc
    if report.graph_name != RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion digest binding failed: graph_name_mismatch"
        )
    if report.source_layout_conversion_count < 1 or len(report.bindings) < 1:
        raise RuntimeEvidenceGateError(
            "runtime layout conversion digest binding failed: bindings_missing"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime layout conversion digest binding failed: raw_value_policy_mismatch"
        )


def _assert_runtime_layout_conversion_digest_binding_bound(
    binding: RuntimeLayoutConversionDigestBindingReport,
    layout_conversion: RuntimeLayoutConversionEvidenceReport,
    hs_ir_alignment: RuntimeHsIrPlanAlignmentReport,
    mixed_tensor_store: RuntimeTensorStoreEvidenceReport,
) -> None:
    expected = {
        "graph_name": layout_conversion.graph_name,
        "source_hs_ir_graph_name": hs_ir_alignment.graph_name,
        "source_tensor_store_graph_name": mixed_tensor_store.graph_name,
        "source_layout_conversion_passed": layout_conversion.passed,
        "source_layout_conversion_issue_count": len(layout_conversion.issues),
        "source_layout_conversion_count": len(layout_conversion.conversions),
        "source_layout_conversion_total_planned_bytes": (layout_conversion.total_planned_bytes),
        "source_layout_conversion_metadata_digest": (layout_conversion.conversion_metadata_digest),
        "source_partition_plan_digest": layout_conversion.source_partition_plan_digest,
        "source_hs_ir_alignment_passed": hs_ir_alignment.passed,
        "source_hs_ir_issue_count": len(hs_ir_alignment.issues),
        "source_hs_ir_step_count": hs_ir_alignment.step_count,
        "source_hs_ir_layout_conversion_count": (hs_ir_alignment.partition_layout_conversion_count),
        "source_hs_ir_total_layout_conversion_bytes": (
            hs_ir_alignment.partition_total_layout_conversion_bytes
        ),
        "source_hs_ir_alignment_metadata_digest": (hs_ir_alignment.alignment_metadata_digest),
        "source_tensor_store_passed": mixed_tensor_store.passed,
        "source_tensor_store_issue_count": len(mixed_tensor_store.issues),
        "source_tensor_store_record_count": len(mixed_tensor_store.records),
        "source_tensor_store_record_metadata_digest": (mixed_tensor_store.record_metadata_digest),
    }
    for field_name, expected_value in expected.items():
        if getattr(binding, field_name) != expected_value:
            raise RuntimeEvidenceGateError(
                f"runtime layout conversion digest binding failed: {field_name}_mismatch"
            )


def _assert_runtime_layout_conversion_gate_readiness_passed(
    report: RuntimeLayoutConversionGateReadinessReport,
) -> None:
    try:
        assert_runtime_layout_conversion_gate_readiness(report)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime layout conversion gate readiness failed: {exc}"
        ) from exc


def _assert_runtime_layout_conversion_promotion_policy_bound(
    policy: RuntimeLayoutConversionGatePromotionPolicyReport,
    readiness: RuntimeLayoutConversionGateReadinessReport,
    digest_binding: RuntimeLayoutConversionDigestBindingReport,
) -> None:
    try:
        assert_runtime_layout_conversion_gate_promotion_policy(policy)
    except (AssertionError, TypeError, ValueError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime layout conversion promotion policy failed: {exc}"
        ) from exc
    expected = {
        "target_graph_id": RUNTIME_MIXED_BACKEND_EQUIVALENCE_GRAPH_ID,
        "target_artifact_kind": "runtime_layout_conversion_evidence",
        "target_artifact_id": RUNTIME_LAYOUT_CONVERSION_EVIDENCE_MATRIX_ARTIFACT_ID,
        "source_readiness_ready": readiness.ready,
        "source_readiness_status": readiness.readiness_status,
        "source_readiness_metadata_digest": readiness.readiness_metadata_digest,
        "source_readiness_target_gate_status": readiness.target_gate_status,
        "source_digest_binding_artifact_id": digest_binding.artifact_id,
        "required_gate_change": ("add_layout_conversion_evidence_to_mixed_graph_required_kinds"),
        "raw_value_policy": "omitted_by_policy",
    }
    for field_name, expected_value in expected.items():
        if getattr(policy, field_name) != expected_value:
            raise RuntimeEvidenceGateError(
                f"runtime layout conversion promotion policy failed: {field_name}_mismatch"
            )


def _assert_backend_equivalence_portfolio_passed(
    report: RuntimeBackendEquivalencePortfolioReport,
    expected_reports: tuple[RuntimeBackendEquivalenceReport, ...],
) -> None:
    if not isinstance(report, RuntimeBackendEquivalencePortfolioReport):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio failed: not a report object"
        )
    if report.issues:
        issues = ",".join(f"{issue.slice_id}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime backend equivalence portfolio failed: {issues}")
    if report.portfolio_id != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_ID:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: portfolio_id_mismatch"
        )
    if report.slice_count != len(expected_reports):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: slice_count_mismatch"
        )
    if report.candidate_backend_families != (
        RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_BACKEND_FAMILIES
    ):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: backend_family_mismatch"
        )
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: raw_value_policy_mismatch"
        )
    expected_slice_ids = tuple(expected_report.graph_name for expected_report in expected_reports)
    actual_slice_ids = tuple(slice_.slice_id for slice_ in report.slices)
    if actual_slice_ids != expected_slice_ids:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: slice_id_mismatch"
        )
    for slice_, expected_report in zip(
        report.slices,
        expected_reports,
        strict=True,
    ):
        _assert_backend_equivalence_portfolio_slice_bound(slice_, expected_report)


def _assert_backend_equivalence_portfolio_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: RuntimeBackendEquivalencePortfolioReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, report.portfolio_id)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_BACKEND_EQUIVALENCE_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio matrix coverage failed: source_boundary_mismatch"
        )
    if (
        graph.required_artifact_kinds
        != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_REQUIRED_ARTIFACTS
    ):
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio matrix coverage failed: "
            "required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio matrix coverage failed: "
            "runtime evidence incomplete"
        )
    missing_artifacts = tuple(
        artifact_kind
        for artifact_kind in RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_REQUIRED_ARTIFACTS
        if artifact_kind not in graph.present_artifact_kinds
    )
    if missing_artifacts:
        missing = ",".join(missing_artifacts)
        raise RuntimeEvidenceGateError(
            f"runtime backend equivalence portfolio matrix coverage failed: missing {missing}"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio matrix coverage failed: artifact_id_mismatch"
        )


def _assert_backend_equivalence_portfolio_policy_bound(
    policy: RuntimeBackendEquivalencePortfolioPolicyReport,
    portfolio: RuntimeBackendEquivalencePortfolioReport,
) -> None:
    try:
        assert_runtime_backend_equivalence_portfolio_matches_policy(
            policy,
            portfolio,
        )
    except (RuntimeBackendEquivalencePortfolioPolicyError, TypeError) as exc:
        raise RuntimeEvidenceGateError(
            f"runtime backend equivalence portfolio policy failed: {exc}"
        ) from exc


def _assert_gate_matrix_coverage_passed(
    report: RuntimeEvidenceGateMatrixCoverageReport,
) -> None:
    if not report.coverage_passed:
        issues = ",".join(report.issues)
        raise RuntimeEvidenceGateError(f"runtime evidence gate matrix coverage failed: {issues}")


def _assert_backend_equivalence_portfolio_slice_bound(
    slice_: RuntimeBackendEquivalencePortfolioSlice,
    expected_report: RuntimeBackendEquivalenceReport,
) -> None:
    runs = {run.run_id: run for run in expected_report.runs}
    baseline = runs.get(expected_report.baseline_run_id)
    candidate = runs.get(expected_report.candidate_run_id)
    if baseline is None or candidate is None:
        raise RuntimeEvidenceGateError(
            "runtime backend equivalence portfolio binding failed: missing_expected_run"
        )
    expected = {
        "slice_id": expected_report.graph_name,
        "graph_name": expected_report.graph_name,
        "baseline_run_id": expected_report.baseline_run_id,
        "candidate_run_id": expected_report.candidate_run_id,
        "baseline_backend_sequence": baseline.planned_backend_sequence,
        "candidate_backend_sequence": candidate.planned_backend_sequence,
        "comparison_count": len(expected_report.comparisons),
        "comparison_metadata_digest": expected_report.comparison_metadata_digest,
        "passed": expected_report.passed,
        "raw_value_policy": expected_report.raw_value_policy,
    }
    actual = {
        "slice_id": slice_.slice_id,
        "graph_name": slice_.graph_name,
        "baseline_run_id": slice_.baseline_run_id,
        "candidate_run_id": slice_.candidate_run_id,
        "baseline_backend_sequence": slice_.baseline_backend_sequence,
        "candidate_backend_sequence": slice_.candidate_backend_sequence,
        "comparison_count": slice_.comparison_count,
        "comparison_metadata_digest": slice_.comparison_metadata_digest,
        "passed": slice_.passed,
        "raw_value_policy": slice_.raw_value_policy,
    }
    for field_name, expected_value in expected.items():
        if actual[field_name] != expected_value:
            raise RuntimeEvidenceGateError(
                "runtime backend equivalence portfolio binding failed: "
                f"{expected_report.graph_name}:{field_name}_mismatch"
            )


def _assert_runtime_memory_planning_gate_passed(report: str) -> None:
    if not isinstance(report, str):
        raise RuntimeEvidenceGateError("runtime memory planning gate failed: not a text report")
    required_lines = (
        "runtime.memory_planning_gate @runtime_memory_planning_gate_v0 {",
        '  buffer_lifetime = "passed"',
        '  allocation_plan = "passed"',
        '  allocation_lifetime_binding = "verified"',
        '  memory_budget = "passed"',
        '  memory_budget_allocation_binding = "verified"',
        '  allocation_request_manifest = "passed"',
        '  allocation_request_manifest_binding = "verified"',
        '  allocation_request_handle_policy = "no_runtime_handles"',
        '  allocation_admission = "passed"',
        '  allocation_admission_binding = "verified"',
        '  allocation_receipt = "passed"',
        '  allocation_receipt_binding = "verified"',
        f'  blocked_execution_surfaces = "{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"',
        '  status = "PASS"',
    )
    for line in required_lines:
        if line not in report:
            raise RuntimeEvidenceGateError(
                "runtime memory planning gate failed: required_line_missing"
            )
    if not report.rstrip().endswith('status = "PASS"\n}'):
        raise RuntimeEvidenceGateError("runtime memory planning gate failed: status_not_pass")
    for forbidden in (
        "raw_tensor_value",
        "tensor_value",
        "runtime_handle =",
        "device_id",
        "command_line",
        "plugin_entrypoint",
        "python_source",
    ):
        if forbidden in report:
            raise RuntimeEvidenceGateError(
                "runtime memory planning gate failed: forbidden_surface_leaked"
            )


def _assert_runtime_memory_planning_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
) -> None:
    graph = _find_runtime_evidence_graph(matrix, RUNTIME_MEMORY_PLANNING_GRAPH_ID)
    if graph is None:
        raise RuntimeEvidenceGateError(
            "runtime memory planning matrix coverage failed: graph missing"
        )
    if graph.graph_family != RUNTIME_MEMORY_PLANNING_MATRIX_GRAPH_FAMILY:
        raise RuntimeEvidenceGateError(
            "runtime memory planning matrix coverage failed: graph_family_mismatch"
        )
    if graph.source_boundary != RUNTIME_MEMORY_PLANNING_MATRIX_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "runtime memory planning matrix coverage failed: source_boundary_mismatch"
        )
    if graph.required_artifact_kinds != RUNTIME_MEMORY_PLANNING_MATRIX_REQUIRED_ARTIFACTS:
        raise RuntimeEvidenceGateError(
            "runtime memory planning matrix coverage failed: required_artifacts_mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "runtime memory planning matrix coverage failed: runtime evidence incomplete"
        )
    artifact_ids = tuple(
        artifact.artifact_id
        for artifact in graph.artifacts
        if artifact.artifact_kind in RUNTIME_MEMORY_PLANNING_MATRIX_REQUIRED_ARTIFACTS
    )
    if artifact_ids != RUNTIME_MEMORY_PLANNING_MATRIX_ARTIFACT_IDS:
        raise RuntimeEvidenceGateError(
            "runtime memory planning matrix coverage failed: artifact_id_mismatch"
        )


def _assert_tensor_store_evidence_passed(
    report: RuntimeTensorStoreEvidenceReport,
) -> None:
    if report.issues:
        issues = ",".join(f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime tensor store evidence failed: {issues}")


def _assert_input_manifest_passed(report: RuntimeInputManifestReport) -> None:
    if report.issues:
        issues = ",".join(f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime input manifest failed: {issues}")


def _assert_output_manifest_passed(report: RuntimeOutputManifestReport) -> None:
    if report.issues:
        issues = ",".join(f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime output manifest failed: {issues}")


def _assert_output_contract_passed(report: RuntimeOutputContractReport) -> None:
    if report.issues:
        issues = ",".join(
            f"{issue.public_name}:{issue.tensor_name}:{issue.issue_code}" for issue in report.issues
        )
        raise RuntimeEvidenceGateError(f"runtime output contract failed: {issues}")


def _assert_public_output_bundle_passed(
    bundle: RuntimePublicOutputBundle,
    output_contract: RuntimeOutputContractReport,
) -> None:
    if not isinstance(bundle, RuntimePublicOutputBundle):
        raise RuntimeEvidenceGateError("runtime public output bundle failed: not a bundle object")
    expected_public_names = tuple(output.public_name for output in output_contract.public_outputs)
    expected_tensor_names = tuple(output.tensor_name for output in output_contract.public_outputs)
    if bundle.graph_name != output_contract.graph_name:
        raise RuntimeEvidenceGateError("runtime public output bundle failed: graph name mismatch")
    if bundle.output_contract != output_contract.output_contract:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: output contract mismatch"
        )
    if bundle.raw_value_policy != output_contract.raw_value_policy:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: raw value policy mismatch"
        )
    if bundle.public_output_names != expected_public_names:
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: public output name mismatch"
        )
    if bundle.tensor_names != expected_tensor_names:
        raise RuntimeEvidenceGateError("runtime public output bundle failed: tensor name mismatch")
    if any(not output.readonly for output in bundle.outputs):
        raise RuntimeEvidenceGateError(
            "runtime public output bundle failed: output value is mutable"
        )


def _assert_reference_correctness_passed(
    report: RuntimeReferenceCorrectnessReport,
) -> None:
    if report.issues:
        issues = ",".join(f"{issue.tensor_name}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime reference correctness failed: {issues}")


def _assert_execution_receipt_passed(report: RuntimeExecutionReceiptReport) -> None:
    if report.issues:
        issues = ",".join(f"{issue.evidence_kind}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime execution receipt failed: {issues}")


def _assert_execution_receipt_matches_gate_reports(
    receipt: RuntimeExecutionReceiptReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    reference_correctness: RuntimeReferenceCorrectnessReport,
) -> None:
    links = {link.evidence_kind: link for link in receipt.evidence_links}
    expected_links = {
        "tensor_store_evidence": {
            "evidence_contract": tensor_store.evidence_contract,
            "graph_name": tensor_store.graph_name,
            "item_count": len(tensor_store.records),
            "metadata_digest": tensor_store.record_metadata_digest,
            "passed": tensor_store.passed,
            "raw_value_policy": tensor_store.raw_value_policy,
        },
        "input_manifest": {
            "evidence_contract": input_manifest.manifest_contract,
            "graph_name": input_manifest.graph_name,
            "item_count": len(input_manifest.inputs),
            "metadata_digest": input_manifest.input_metadata_digest,
            "passed": input_manifest.passed,
            "raw_value_policy": input_manifest.raw_value_policy,
        },
        "output_manifest": {
            "evidence_contract": output_manifest.manifest_contract,
            "graph_name": output_manifest.graph_name,
            "item_count": len(output_manifest.outputs),
            "metadata_digest": output_manifest.output_metadata_digest,
            "passed": output_manifest.passed,
            "raw_value_policy": output_manifest.raw_value_policy,
        },
        "output_contract": {
            "evidence_contract": output_contract.output_contract,
            "graph_name": output_contract.graph_name,
            "item_count": len(output_contract.public_outputs),
            "metadata_digest": output_contract.contract_metadata_digest,
            "passed": output_contract.passed,
            "raw_value_policy": output_contract.raw_value_policy,
        },
        "public_output_bundle": {
            "evidence_contract": public_output_bundle.bundle_contract,
            "graph_name": public_output_bundle.graph_name,
            "item_count": len(public_output_bundle.outputs),
            "metadata_digest": public_output_bundle.bundle_metadata_digest,
            "passed": public_output_bundle.passed,
            "raw_value_policy": public_output_bundle.raw_value_policy,
        },
        "reference_correctness": {
            "evidence_contract": reference_correctness.correctness_contract,
            "graph_name": reference_correctness.graph_name,
            "item_count": len(reference_correctness.comparisons),
            "metadata_digest": reference_correctness.comparison_metadata_digest,
            "passed": reference_correctness.passed,
            "raw_value_policy": reference_correctness.raw_value_policy,
        },
    }

    for evidence_kind, expected in expected_links.items():
        link = links.get(evidence_kind)
        if link is None:
            raise RuntimeEvidenceGateError(
                f"runtime execution receipt binding failed: {evidence_kind}:missing_link"
            )
        actual = {
            "evidence_contract": link.evidence_contract,
            "graph_name": link.graph_name,
            "item_count": link.item_count,
            "metadata_digest": link.metadata_digest,
            "passed": link.passed,
            "raw_value_policy": link.raw_value_policy,
        }
        for field_name, expected_value in expected.items():
            if actual[field_name] != expected_value:
                raise RuntimeEvidenceGateError(
                    "runtime execution receipt binding failed: "
                    f"{evidence_kind}:{field_name}_mismatch"
                )


def _assert_execution_evidence_bundle_passed(
    report: RuntimeExecutionEvidenceBundleReport,
) -> None:
    if not isinstance(report, RuntimeExecutionEvidenceBundleReport):
        raise RuntimeEvidenceGateError(
            "runtime execution evidence bundle failed: not a report object"
        )
    if report.issues:
        issues = ",".join(f"{issue.section}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime execution evidence bundle failed: {issues}")


def _assert_execution_evidence_bundle_matches_gate_reports(
    bundle: RuntimeExecutionEvidenceBundleReport,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    reference_correctness: RuntimeReferenceCorrectnessReport,
    execution_receipt: RuntimeExecutionReceiptReport,
) -> None:
    expected = {
        "tensor_store_evidence": {
            "contract": tensor_store.evidence_contract,
            "graph_name": tensor_store.graph_name,
            "item_count": len(tensor_store.records),
            "metadata_digest": tensor_store.record_metadata_digest,
            "passed": tensor_store.passed,
            "raw_value_policy": tensor_store.raw_value_policy,
        },
        "input_manifest": {
            "contract": input_manifest.manifest_contract,
            "graph_name": input_manifest.graph_name,
            "item_count": len(input_manifest.inputs),
            "metadata_digest": input_manifest.input_metadata_digest,
            "passed": input_manifest.passed,
            "raw_value_policy": input_manifest.raw_value_policy,
        },
        "output_manifest": {
            "contract": output_manifest.manifest_contract,
            "graph_name": output_manifest.graph_name,
            "item_count": len(output_manifest.outputs),
            "metadata_digest": output_manifest.output_metadata_digest,
            "passed": output_manifest.passed,
            "raw_value_policy": output_manifest.raw_value_policy,
        },
        "output_contract": {
            "contract": output_contract.output_contract,
            "graph_name": output_contract.graph_name,
            "item_count": len(output_contract.public_outputs),
            "metadata_digest": output_contract.contract_metadata_digest,
            "passed": output_contract.passed,
            "raw_value_policy": output_contract.raw_value_policy,
        },
        "public_output_bundle": {
            "contract": public_output_bundle.bundle_contract,
            "graph_name": public_output_bundle.graph_name,
            "item_count": len(public_output_bundle.outputs),
            "metadata_digest": public_output_bundle.bundle_metadata_digest,
            "passed": public_output_bundle.passed,
            "raw_value_policy": public_output_bundle.raw_value_policy,
        },
        "reference_correctness": {
            "contract": reference_correctness.correctness_contract,
            "graph_name": reference_correctness.graph_name,
            "item_count": len(reference_correctness.comparisons),
            "metadata_digest": reference_correctness.comparison_metadata_digest,
            "passed": reference_correctness.passed,
            "raw_value_policy": reference_correctness.raw_value_policy,
        },
        "execution_receipt": {
            "contract": execution_receipt.receipt_contract,
            "graph_name": execution_receipt.graph_name,
            "item_count": len(execution_receipt.evidence_links),
            "metadata_digest": execution_receipt.receipt_metadata_digest,
            "passed": execution_receipt.passed,
            "raw_value_policy": execution_receipt.raw_value_policy,
        },
    }
    actual = {
        "tensor_store_evidence": {
            "contract": bundle.tensor_store_report.evidence_contract,
            "graph_name": bundle.tensor_store_report.graph_name,
            "item_count": len(bundle.tensor_store_report.records),
            "metadata_digest": bundle.tensor_store_report.record_metadata_digest,
            "passed": bundle.tensor_store_report.passed,
            "raw_value_policy": bundle.tensor_store_report.raw_value_policy,
        },
        "input_manifest": {
            "contract": bundle.input_manifest_report.manifest_contract,
            "graph_name": bundle.input_manifest_report.graph_name,
            "item_count": len(bundle.input_manifest_report.inputs),
            "metadata_digest": bundle.input_manifest_report.input_metadata_digest,
            "passed": bundle.input_manifest_report.passed,
            "raw_value_policy": bundle.input_manifest_report.raw_value_policy,
        },
        "output_manifest": {
            "contract": bundle.output_manifest_report.manifest_contract,
            "graph_name": bundle.output_manifest_report.graph_name,
            "item_count": len(bundle.output_manifest_report.outputs),
            "metadata_digest": bundle.output_manifest_report.output_metadata_digest,
            "passed": bundle.output_manifest_report.passed,
            "raw_value_policy": bundle.output_manifest_report.raw_value_policy,
        },
        "output_contract": {
            "contract": bundle.output_contract_report.output_contract,
            "graph_name": bundle.output_contract_report.graph_name,
            "item_count": len(bundle.output_contract_report.public_outputs),
            "metadata_digest": bundle.output_contract_report.contract_metadata_digest,
            "passed": bundle.output_contract_report.passed,
            "raw_value_policy": bundle.output_contract_report.raw_value_policy,
        },
        "public_output_bundle": {
            "contract": bundle.public_output_bundle.bundle_contract,
            "graph_name": bundle.public_output_bundle.graph_name,
            "item_count": len(bundle.public_output_bundle.outputs),
            "metadata_digest": bundle.public_output_bundle.bundle_metadata_digest,
            "passed": bundle.public_output_bundle.passed,
            "raw_value_policy": bundle.public_output_bundle.raw_value_policy,
        },
        "reference_correctness": {
            "contract": bundle.reference_correctness_report.correctness_contract,
            "graph_name": bundle.reference_correctness_report.graph_name,
            "item_count": len(bundle.reference_correctness_report.comparisons),
            "metadata_digest": (bundle.reference_correctness_report.comparison_metadata_digest),
            "passed": bundle.reference_correctness_report.passed,
            "raw_value_policy": bundle.reference_correctness_report.raw_value_policy,
        },
        "execution_receipt": {
            "contract": bundle.execution_receipt_report.receipt_contract,
            "graph_name": bundle.execution_receipt_report.graph_name,
            "item_count": len(bundle.execution_receipt_report.evidence_links),
            "metadata_digest": (bundle.execution_receipt_report.receipt_metadata_digest),
            "passed": bundle.execution_receipt_report.passed,
            "raw_value_policy": bundle.execution_receipt_report.raw_value_policy,
        },
    }

    for section, expected_fields in expected.items():
        actual_fields = actual[section]
        for field_name, expected_value in expected_fields.items():
            if actual_fields[field_name] != expected_value:
                raise RuntimeEvidenceGateError(
                    "runtime execution evidence bundle binding failed: "
                    f"{section}:{field_name}_mismatch"
                )


def _assert_execution_output_closure_passed(
    report: RuntimeExecutionOutputClosureReport,
) -> None:
    if not isinstance(report, RuntimeExecutionOutputClosureReport):
        raise RuntimeEvidenceGateError(
            "runtime execution output closure failed: not a report object"
        )
    if report.issues:
        issues = ",".join(f"{issue.subject}:{issue.issue_code}" for issue in report.issues)
        raise RuntimeEvidenceGateError(f"runtime execution output closure failed: {issues}")


def _assert_execution_output_closure_matches_gate_reports(
    report: RuntimeExecutionOutputClosureReport,
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    execution_receipt: RuntimeExecutionReceiptReport,
    execution_evidence_bundle: RuntimeExecutionEvidenceBundleReport,
) -> None:
    expected = build_runtime_execution_output_closure_report(
        output_contract,
        public_output_bundle,
        execution_receipt,
        execution_evidence_bundle,
    )
    fields = (
        "graph_name",
        "source_output_contract_metadata_digest",
        "source_public_output_bundle_metadata_digest",
        "source_execution_receipt_metadata_digest",
        "source_execution_evidence_bundle_metadata_digest",
        "source_bundle_execution_receipt_metadata_digest",
        "checks",
        "closure_policy_id",
        "raw_value_policy",
    )
    for field_name in fields:
        if getattr(report, field_name) != getattr(expected, field_name):
            raise RuntimeEvidenceGateError(
                f"runtime execution output closure binding failed: {field_name}_mismatch"
            )


def _assert_source_intent_runtime_returns_passed(
    report: SourceIntentRuntimeReturnsReport,
) -> None:
    if not isinstance(report, SourceIntentRuntimeReturnsReport):
        raise RuntimeEvidenceGateError("source intent runtime returns failed: not a report object")
    if not report.passed:
        raise RuntimeEvidenceGateError("source intent runtime returns failed")
    if report.runtime_returns_contract != SOURCE_INTENT_RUNTIME_RETURNS_CONTRACT:
        raise RuntimeEvidenceGateError("source intent runtime returns failed: contract mismatch")
    if report.raw_value_policy != "omitted_by_policy":
        raise RuntimeEvidenceGateError(
            "source intent runtime returns failed: raw value policy mismatch"
        )


def _assert_source_intent_runtime_returns_matrix_covered(
    matrix: RuntimeEvidenceMatrixReport,
    report: SourceIntentRuntimeReturnsReport,
) -> None:
    graph = _find_runtime_evidence_graph(
        matrix,
        SOURCE_INTENT_RUNTIME_RETURNS_GRAPH_ID,
    )
    if graph is None:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: graph missing"
        )
    if graph.source_boundary != SOURCE_INTENT_RUNTIME_RETURNS_SOURCE_BOUNDARY:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: source boundary mismatch"
        )
    if report.module_name != graph.graph_id or report.graph_name != graph.graph_id:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: report graph mismatch"
        )
    if not graph.runtime_evidence_complete:
        raise RuntimeEvidenceGateError(
            "source intent runtime returns matrix coverage failed: runtime evidence incomplete"
        )
    missing_artifacts = tuple(
        artifact_kind
        for artifact_kind in SOURCE_INTENT_RUNTIME_RETURNS_REQUIRED_MATRIX_ARTIFACTS
        if artifact_kind not in graph.present_artifact_kinds
    )
    if missing_artifacts:
        missing = ",".join(missing_artifacts)
        raise RuntimeEvidenceGateError(
            f"source intent runtime returns matrix coverage failed: missing {missing}"
        )


def _runtime_backend_equivalence_run(
    report: RuntimeBackendEquivalenceReport,
    run_id: str,
) -> RuntimeBackendEquivalenceRun:
    for run in report.runs:
        if run.run_id == run_id:
            return run
    raise RuntimeEvidenceGateError(f"runtime backend equivalence run missing: {run_id}")


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _find_runtime_evidence_graph(
    matrix: RuntimeEvidenceMatrixReport,
    graph_id: str,
) -> RuntimeEvidenceGraph | None:
    for graph in matrix.graphs:
        if graph.graph_id == graph_id:
            return graph
    return None


def _render_gate_report(
    matrix: RuntimeEvidenceMatrixReport,
    conformance: RuntimeExecutorConformanceReport,
    backend_equivalence: RuntimeBackendEquivalenceReport,
    runtime_planning_explanation: RuntimePlanningExplanationReport,
    runtime_transfer_trace_index: RuntimeTransferTraceIndexReport,
    vector_backend_equivalence: RuntimeBackendEquivalenceReport,
    mixed_backend_equivalence: RuntimeBackendEquivalenceReport,
    mixed_runtime_planning_explanation: RuntimePlanningExplanationReport,
    runtime_hs_ir_plan_alignment: RuntimeHsIrPlanAlignmentReport,
    runtime_layout_conversion_evidence: RuntimeLayoutConversionEvidenceReport,
    runtime_layout_conversion_trace_index: RuntimeLayoutConversionTraceIndexReport,
    runtime_layout_conversion_trace_replay_verifier: (
        RuntimeLayoutConversionTraceReplayVerifierReport
    ),
    runtime_backend_equivalence_layout_binding: (RuntimeBackendEquivalenceLayoutBindingReport),
    runtime_layout_conversion_digest_binding: RuntimeLayoutConversionDigestBindingReport,
    runtime_layout_conversion_gate_readiness: RuntimeLayoutConversionGateReadinessReport,
    runtime_layout_conversion_gate_promotion_policy: (
        RuntimeLayoutConversionGatePromotionPolicyReport
    ),
    backend_equivalence_portfolio: RuntimeBackendEquivalencePortfolioReport,
    backend_equivalence_portfolio_policy: (RuntimeBackendEquivalencePortfolioPolicyReport),
    gate_matrix_coverage: RuntimeEvidenceGateMatrixCoverageReport,
    memory_planning_gate: str,
    tensor_store: RuntimeTensorStoreEvidenceReport,
    input_manifest: RuntimeInputManifestReport,
    output_manifest: RuntimeOutputManifestReport,
    output_contract: RuntimeOutputContractReport,
    public_output_bundle: RuntimePublicOutputBundle,
    reference_correctness: RuntimeReferenceCorrectnessReport,
    execution_receipt: RuntimeExecutionReceiptReport,
    execution_evidence_bundle: RuntimeExecutionEvidenceBundleReport,
    execution_output_closure: RuntimeExecutionOutputClosureReport,
    source_intent_runtime_returns: SourceIntentRuntimeReturnsReport,
) -> str:
    lines = ["runtime.evidence_gate @runtime_evidence_gate_v0 {"]
    lines.append('  runtime_evidence_matrix = "complete"')
    lines.append(f'  runtime_evidence_graphs = "{len(matrix.graphs)}"')
    lines.append('  runtime_evidence_gate_matrix_coverage = "passed"')
    lines.append(
        f'  runtime_evidence_gate_matrix_bindings = "{gate_matrix_coverage.binding_count}"'
    )
    lines.append('  runtime_executor_conformance = "passed"')
    lines.append(f'  runtime_executor_conformance_cases = "{len(conformance.checked_cases)}"')
    lines.append('  runtime_backend_equivalence = "passed"')
    lines.append('  runtime_backend_equivalence_binding = "verified"')
    lines.append('  runtime_backend_equivalence_matrix = "covered"')
    lines.append(
        "  runtime_backend_equivalence_matrix_artifact = "
        f'"{RUNTIME_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(f'  runtime_backend_equivalence_runs = "{len(backend_equivalence.runs)}"')
    lines.append(
        f'  runtime_backend_equivalence_comparisons = "{len(backend_equivalence.comparisons)}"'
    )
    lines.append(
        f'  runtime_backend_equivalence_raw_value_policy = "{backend_equivalence.raw_value_policy}"'
    )
    lines.append('  runtime_planning_explanation = "passed"')
    lines.append('  runtime_planning_explanation_binding = "verified"')
    lines.append('  runtime_planning_explanation_matrix = "covered"')
    lines.append(
        "  runtime_planning_explanation_matrix_artifact = "
        f'"{RUNTIME_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_planning_explanation_backend_sequence = "
        f'"{",".join(runtime_planning_explanation.backend_sequence)}"'
    )
    lines.append(
        "  runtime_planning_explanation_selection_kinds = "
        f'"{",".join(runtime_planning_explanation.selection_kinds)}"'
    )
    lines.append(
        "  runtime_planning_explanation_movement_bytes = "
        f'"{runtime_planning_explanation.total_data_movement_bytes}"'
    )
    lines.append('  runtime_transfer_trace_index = "passed"')
    lines.append('  runtime_transfer_trace_index_binding = "verified"')
    lines.append('  runtime_transfer_trace_index_matrix = "covered"')
    lines.append(
        "  runtime_transfer_trace_index_matrix_artifact = "
        f'"{RUNTIME_TRANSFER_TRACE_INDEX_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_transfer_trace_index_records = "
        f'"{runtime_transfer_trace_index.transfer_count}"'
    )
    lines.append(
        "  runtime_transfer_trace_index_trace_steps = "
        f'"{runtime_transfer_trace_index.trace_step_count}"'
    )
    lines.append(
        "  runtime_transfer_trace_index_planned_bytes = "
        f'"{runtime_transfer_trace_index.total_planned_bytes}"'
    )
    lines.append(
        "  runtime_transfer_trace_index_materialization = "
        f'"{runtime_transfer_trace_index.trace_materialization_policy}"'
    )
    lines.append('  runtime_vector_backend_equivalence = "passed"')
    lines.append('  runtime_vector_backend_equivalence_binding = "verified"')
    lines.append('  runtime_vector_backend_equivalence_matrix = "covered"')
    lines.append(
        "  runtime_vector_backend_equivalence_matrix_artifact = "
        f'"{RUNTIME_VECTOR_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        f'  runtime_vector_backend_equivalence_runs = "{len(vector_backend_equivalence.runs)}"'
    )
    lines.append(
        "  runtime_vector_backend_equivalence_comparisons = "
        f'"{len(vector_backend_equivalence.comparisons)}"'
    )
    lines.append(
        "  runtime_vector_backend_equivalence_raw_value_policy = "
        f'"{vector_backend_equivalence.raw_value_policy}"'
    )
    lines.append('  runtime_mixed_backend_equivalence = "passed"')
    lines.append('  runtime_mixed_backend_equivalence_binding = "verified"')
    lines.append('  runtime_mixed_backend_equivalence_matrix = "covered"')
    lines.append(
        "  runtime_mixed_backend_equivalence_matrix_artifact = "
        f'"{RUNTIME_MIXED_BACKEND_EQUIVALENCE_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        f'  runtime_mixed_backend_equivalence_runs = "{len(mixed_backend_equivalence.runs)}"'
    )
    lines.append(
        "  runtime_mixed_backend_equivalence_comparisons = "
        f'"{len(mixed_backend_equivalence.comparisons)}"'
    )
    lines.append(
        "  runtime_mixed_backend_equivalence_raw_value_policy = "
        f'"{mixed_backend_equivalence.raw_value_policy}"'
    )
    lines.append('  runtime_mixed_planning_explanation = "passed"')
    lines.append('  runtime_mixed_planning_explanation_binding = "verified"')
    lines.append('  runtime_mixed_planning_explanation_matrix = "covered"')
    lines.append(
        "  runtime_mixed_planning_explanation_matrix_artifact = "
        f'"{RUNTIME_MIXED_BACKEND_EQUIVALENCE_PLANNING_EXPLANATION_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_mixed_planning_explanation_backend_sequence = "
        f'"{",".join(mixed_runtime_planning_explanation.backend_sequence)}"'
    )
    lines.append(
        "  runtime_mixed_planning_explanation_selection_kinds = "
        f'"{",".join(mixed_runtime_planning_explanation.selection_kinds)}"'
    )
    lines.append(
        "  runtime_mixed_planning_explanation_movement_bytes = "
        f'"{mixed_runtime_planning_explanation.total_data_movement_bytes}"'
    )
    lines.append('  runtime_hs_ir_plan_alignment = "passed"')
    lines.append('  runtime_hs_ir_plan_alignment_binding = "verified"')
    lines.append('  runtime_hs_ir_plan_alignment_matrix = "covered"')
    lines.append(
        "  runtime_hs_ir_plan_alignment_matrix_artifact = "
        f'"{RUNTIME_HS_IR_PLAN_ALIGNMENT_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        f'  runtime_hs_ir_plan_alignment_steps = "{runtime_hs_ir_plan_alignment.step_count}"'
    )
    lines.append(
        "  runtime_hs_ir_plan_alignment_backend_sequence = "
        f'"{",".join(runtime_hs_ir_plan_alignment.partition_backend_sequence)}"'
    )
    lines.append(
        "  runtime_hs_ir_plan_alignment_raw_value_policy = "
        f'"{runtime_hs_ir_plan_alignment.raw_value_policy}"'
    )
    lines.append('  runtime_layout_conversion_evidence = "passed"')
    lines.append('  runtime_layout_conversion_evidence_binding = "verified"')
    lines.append('  runtime_layout_conversion_evidence_matrix = "covered"')
    lines.append(
        "  runtime_layout_conversion_evidence_matrix_artifact = "
        f'"{RUNTIME_LAYOUT_CONVERSION_EVIDENCE_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_layout_conversion_count = "
        f'"{len(runtime_layout_conversion_evidence.conversions)}"'
    )
    lines.append(
        "  runtime_layout_conversion_planned_bytes = "
        f'"{runtime_layout_conversion_evidence.total_planned_bytes}"'
    )
    lines.append('  runtime_layout_conversion_trace_index = "passed"')
    lines.append('  runtime_layout_conversion_trace_index_binding = "verified"')
    lines.append('  runtime_layout_conversion_trace_index_matrix = "covered"')
    lines.append(
        "  runtime_layout_conversion_trace_index_matrix_artifact = "
        f'"{RUNTIME_LAYOUT_CONVERSION_TRACE_INDEX_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_layout_conversion_trace_index_records = "
        f'"{runtime_layout_conversion_trace_index.conversion_count}"'
    )
    lines.append(
        "  runtime_layout_conversion_trace_index_trace_steps = "
        f'"{runtime_layout_conversion_trace_index.trace_step_count}"'
    )
    lines.append(
        "  runtime_layout_conversion_trace_index_materialization = "
        f'"{runtime_layout_conversion_trace_index.trace_materialization_policy}"'
    )
    lines.append('  runtime_layout_conversion_trace_replay_verifier = "passed"')
    lines.append('  runtime_layout_conversion_trace_replay_binding = "verified"')
    lines.append('  runtime_layout_conversion_trace_replay_matrix = "covered"')
    lines.append(
        "  runtime_layout_conversion_trace_replay_matrix_artifact = "
        f'"{RUNTIME_LAYOUT_CONVERSION_TRACE_REPLAY_VERIFIER_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_layout_conversion_trace_replay_checks = "
        f'"{runtime_layout_conversion_trace_replay_verifier.check_count}"'
    )
    lines.append('  runtime_backend_equivalence_layout_binding = "passed"')
    lines.append('  runtime_backend_equivalence_layout_binding_matrix = "covered"')
    lines.append(
        "  runtime_backend_equivalence_layout_binding_matrix_artifact = "
        f'"{RUNTIME_BACKEND_EQUIVALENCE_LAYOUT_BINDING_MATRIX_ARTIFACT_ID}"'
    )
    lines.append(
        "  runtime_backend_equivalence_layout_binding_checks = "
        f'"{runtime_backend_equivalence_layout_binding.check_count}"'
    )
    lines.append(
        "  runtime_backend_equivalence_layout_binding_candidate_backends = "
        f'"{runtime_backend_equivalence_layout_binding.candidate_backend_count}"'
    )
    lines.append('  runtime_layout_conversion_digest_binding = "passed"')
    lines.append('  runtime_layout_conversion_digest_binding_consistency = "verified"')
    lines.append(
        "  runtime_layout_conversion_digest_binding_rows = "
        f'"{len(runtime_layout_conversion_digest_binding.bindings)}"'
    )
    lines.append('  runtime_layout_conversion_gate_readiness = "ready"')
    lines.append('  runtime_layout_conversion_promotion_policy = "accepted"')
    lines.append(
        "  runtime_layout_conversion_promotion_enforcement_status = "
        f'"{runtime_layout_conversion_gate_promotion_policy.enforcement_status}"'
    )
    lines.append('  runtime_layout_conversion_gate_enforcement = "enabled"')
    lines.append('  runtime_backend_equivalence_portfolio = "passed"')
    lines.append('  runtime_backend_equivalence_portfolio_binding = "verified"')
    lines.append(
        "  runtime_backend_equivalence_portfolio_slices = "
        f'"{backend_equivalence_portfolio.slice_count}"'
    )
    lines.append(
        "  runtime_backend_equivalence_portfolio_backend_families = "
        f'"{",".join(backend_equivalence_portfolio.candidate_backend_families)}"'
    )
    lines.append(
        "  runtime_backend_equivalence_portfolio_raw_value_policy = "
        f'"{backend_equivalence_portfolio.raw_value_policy}"'
    )
    lines.append('  runtime_backend_equivalence_portfolio_matrix = "covered"')
    lines.append(
        "  runtime_backend_equivalence_portfolio_matrix_artifacts = "
        f'"{",".join(RUNTIME_BACKEND_EQUIVALENCE_PORTFOLIO_MATRIX_ARTIFACT_IDS)}"'
    )
    lines.append('  runtime_backend_equivalence_portfolio_policy = "accepted"')
    lines.append('  runtime_backend_equivalence_portfolio_policy_binding = "verified"')
    lines.append(
        "  runtime_backend_equivalence_portfolio_policy_required_slices = "
        f'"{backend_equivalence_portfolio_policy.requirement_count}"'
    )
    lines.append('  runtime_memory_planning_gate = "passed"')
    lines.append('  runtime_memory_planning_matrix = "covered"')
    lines.append(
        "  runtime_memory_planning_matrix_artifacts = "
        f'"{",".join(RUNTIME_MEMORY_PLANNING_MATRIX_ARTIFACT_IDS)}"'
    )
    lines.append(
        f'  runtime_memory_planning_gate_bytes = "{len(memory_planning_gate.encode("utf-8"))}"'
    )
    lines.append('  runtime_tensor_store_evidence = "passed"')
    lines.append(f'  runtime_tensor_store_records = "{len(tensor_store.records)}"')
    lines.append(f'  runtime_tensor_store_raw_value_policy = "{tensor_store.raw_value_policy}"')
    lines.append('  runtime_input_manifest = "passed"')
    lines.append(f'  runtime_input_count = "{len(input_manifest.inputs)}"')
    lines.append(f'  runtime_input_raw_value_policy = "{input_manifest.raw_value_policy}"')
    lines.append('  runtime_output_manifest = "passed"')
    lines.append(f'  runtime_output_count = "{len(output_manifest.outputs)}"')
    lines.append(f'  runtime_output_raw_value_policy = "{output_manifest.raw_value_policy}"')
    lines.append('  runtime_output_contract = "passed"')
    lines.append(f'  runtime_public_output_count = "{len(output_contract.public_outputs)}"')
    lines.append(f'  runtime_output_alias_count = "{len(output_contract.aliases)}"')
    lines.append(
        f'  runtime_output_contract_raw_value_policy = "{output_contract.raw_value_policy}"'
    )
    lines.append('  runtime_public_output_bundle = "passed"')
    lines.append(f'  runtime_public_output_bundle_outputs = "{len(public_output_bundle.outputs)}"')
    lines.append(
        "  runtime_public_output_bundle_raw_value_policy = "
        f'"{public_output_bundle.raw_value_policy}"'
    )
    lines.append('  runtime_reference_correctness = "passed"')
    lines.append(f'  runtime_reference_comparisons = "{len(reference_correctness.comparisons)}"')
    lines.append(
        f'  runtime_reference_raw_value_policy = "{reference_correctness.raw_value_policy}"'
    )
    lines.append('  runtime_execution_receipt = "passed"')
    lines.append('  runtime_execution_receipt_binding = "verified"')
    lines.append(f'  runtime_execution_receipt_links = "{len(execution_receipt.evidence_links)}"')
    lines.append(f'  runtime_execution_receipt_operations = "{len(execution_receipt.operations)}"')
    lines.append(
        f'  runtime_execution_receipt_raw_value_policy = "{execution_receipt.raw_value_policy}"'
    )
    lines.append('  runtime_execution_evidence_bundle = "passed"')
    lines.append('  runtime_execution_evidence_bundle_binding = "verified"')
    lines.append(
        "  runtime_execution_evidence_bundle_sections = "
        f'"{len(execution_evidence_bundle.report_sections)}"'
    )
    lines.append(
        "  runtime_execution_evidence_bundle_raw_value_policy = "
        f'"{execution_evidence_bundle.raw_value_policy}"'
    )
    lines.append('  runtime_execution_output_closure = "passed"')
    lines.append('  runtime_execution_output_closure_binding = "verified"')
    lines.append(
        f'  runtime_execution_output_closure_checks = "{execution_output_closure.check_count}"'
    )
    lines.append(
        "  runtime_execution_output_closure_policy = "
        f'"{execution_output_closure.closure_policy_id}"'
    )
    lines.append(
        "  runtime_execution_output_closure_raw_value_policy = "
        f'"{execution_output_closure.raw_value_policy}"'
    )
    lines.append('  source_intent_runtime_returns_matrix = "covered"')
    lines.append('  source_intent_runtime_returns = "passed"')
    lines.append(
        f'  source_intent_runtime_return_count = "{source_intent_runtime_returns.return_count}"'
    )
    lines.append(
        "  source_intent_runtime_public_output_count = "
        f'"{len(source_intent_runtime_returns.public_output_names)}"'
    )
    lines.append(
        "  source_intent_runtime_returns_raw_value_policy = "
        f'"{source_intent_runtime_returns.raw_value_policy}"'
    )
    lines.append(
        f'  blocked_execution_surfaces = "{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
