"""Deterministic proof-report metadata for TUC validation artifacts."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass

from tuc.ir.dialect import (
    HAC_IR_DIALECT_VERSION,
    HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES,
    validate_hac_module_contract,
)
from tuc.ir.modules import IRModule, IRStage
from tuc.runtime import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    Assignment,
    PartitionPlan,
)

PROOF_REPORT_SCHEMA_VERSION = "proof-report.v0"
PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.performance_proof_readiness_report.v0"
)
PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION = "tuc.performance_proof_rfc_report.v0"
PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS = "diagnostic_only"
PERFORMANCE_PROOF_RFC_CLAIM_STATUS = "blocked"
PERFORMANCE_PROOF_RFC_STATUSES = (
    "draft",
    "reviewed_not_accepted",
    "accepted_by_maintainers",
)
PERFORMANCE_PROOF_RFC_DEFAULT_ISSUES = (
    "performance_proof_rfcs_not_supplied",
    "native_performance_claim_blocked",
)
PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION = (
    "tuc.performance_claim_threshold_policy_report.v0"
)
PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS = "diagnostic_only"
PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS = "blocked"
PERFORMANCE_CLAIM_THRESHOLD_POLICY_KINDS = (
    "ratio_to_native_at_least",
    "overhead_over_native_at_most",
)
PERFORMANCE_CLAIM_THRESHOLD_POLICY_STATUSES = (
    "draft",
    "reviewed_not_accepted",
    "accepted_by_maintainers",
)
PERFORMANCE_CLAIM_THRESHOLD_POLICY_DEFAULT_ISSUES = (
    "performance_claim_threshold_policies_not_supplied",
    "native_performance_claim_blocked",
)
PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION = (
    "tuc.performance_acceptance_criteria_report.v0"
)
PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS = "diagnostic_only"
PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS = "blocked"
PERFORMANCE_ACCEPTANCE_CRITERIA_STATUSES = (
    "draft",
    "reviewed_not_accepted",
    "accepted_by_maintainers",
)
PERFORMANCE_ACCEPTANCE_CRITERIA_DEFAULT_ISSUES = (
    "performance_acceptance_criteria_not_supplied",
    "native_performance_claim_blocked",
)
PERFORMANCE_PROOF_BOUNDARY_CONTRACT = "performance_proof_boundary.blocking.v0"
PERFORMANCE_PROOF_REQUIRED_EVIDENCE = (
    "performance_proof_rfc",
    "performance_claim_threshold_policy",
    "performance_acceptance_criteria",
    "benchmark_methodology",
    "native_baseline_provenance",
    "versioned_toolchain_environment",
    "workload_scope",
    "correctness_goldens",
    "native_baseline_comparison",
    "leaky_abstraction_report",
    "planner_overhead_report",
    "break_even_workload_size",
    "runtime_plan_goldens",
    "compiler_decision_report_goldens",
    "benchmark_report_schema",
    "benchmark_report_artifacts",
    "executable_backend_security_review",
)
PERFORMANCE_PROOF_BLOCKED_CLAIMS = (
    "native_performance_parity",
    "hundred_percent_native_performance",
    "fixed_vendor_performance_percentage",
    "near_native_without_threshold",
    "planner_overhead_hidden_in_execution_time",
    "transfer_estimates_as_measured_hardware_performance",
    "hardware_specific_hac_ir_knobs",
)
LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION = "tuc.leaky_abstraction_report.v0"
LEAKY_ABSTRACTION_ARTIFACT_STATUS = "diagnostic_only"
LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS = "blocked"
LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES = (
    "backend_capability",
    "hs_ir",
    "runtime_plan",
    "compiler_decision_report",
    "backend_implementation",
    "benchmark_artifact",
    "security_rfc",
)
LEAKY_ABSTRACTION_DEFAULT_ISSUES = (
    "native_baseline_not_supplied",
    "native_performance_claim_blocked",
)
NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION = (
    "tuc.native_baseline_provenance_report.v0"
)
NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS = "diagnostic_only"
NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS = "blocked"
NATIVE_BASELINE_IMPLEMENTATION_KINDS = (
    "vendor_library",
    "vendor_sample",
    "hand_optimized_kernel",
    "framework_compiler",
)
NATIVE_BASELINE_REPRODUCIBILITY_STATUSES = (
    "not_reproduced",
    "documented_not_executed",
    "reproduced_outside_tuc",
    "reproduced_by_ci",
)
NATIVE_BASELINE_DEFAULT_ISSUES = (
    "native_baselines_not_supplied",
    "native_baseline_comparison_not_supplied",
    "native_performance_claim_blocked",
)
NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION = (
    "tuc.native_baseline_comparison_report.v0"
)
NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS = "diagnostic_only"
NATIVE_BASELINE_COMPARISON_CLAIM_STATUS = "blocked"
NATIVE_BASELINE_COMPARISON_RESULT_STATUSES = (
    "not_measured",
    "reported_not_validated",
    "validated_by_ci",
)
NATIVE_BASELINE_COMPARISON_DEFAULT_ISSUES = (
    "native_baseline_comparisons_not_supplied",
    "native_performance_claim_blocked",
)
BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION = (
    "tuc.benchmark_artifact_manifest_report.v0"
)
BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS = "diagnostic_only"
BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS = "blocked"
BENCHMARK_ARTIFACT_KINDS = (
    "baseline_benchmark_report",
    "native_benchmark_report",
    "native_baseline_comparison_report",
)
BENCHMARK_ARTIFACT_REQUIRED_KINDS = BENCHMARK_ARTIFACT_KINDS
BENCHMARK_ARTIFACT_STORAGE_SCOPES = (
    "repository_golden",
    "ci_artifact",
    "release_artifact",
    "review_attachment",
)
BENCHMARK_ARTIFACT_MANIFEST_DEFAULT_ISSUES = (
    "benchmark_artifacts_not_supplied",
    "native_performance_claim_blocked",
)
WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION = "tuc.workload_scope_report.v0"
WORKLOAD_SCOPE_ARTIFACT_STATUS = "diagnostic_only"
WORKLOAD_SCOPE_CLAIM_STATUS = "blocked"
WORKLOAD_OPERATION_FAMILIES = (
    "matmul",
    "elementwise",
    "reduction",
    "softmax",
)
WORKLOAD_SCOPE_DEFAULT_ISSUES = (
    "workload_scopes_not_supplied",
    "native_performance_claim_blocked",
)
WORKLOAD_SCOPE_MAX_PROBLEM_SIZE = 1_000_000_000_000
BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION = "tuc.benchmark_methodology_report.v0"
BENCHMARK_METHODOLOGY_ARTIFACT_STATUS = "diagnostic_only"
BENCHMARK_METHODOLOGY_CLAIM_STATUS = "blocked"
BENCHMARK_METHODOLOGY_CLOCKS = (
    "monotonic_ns",
    "device_event_timer",
    "external_profiler",
)
BENCHMARK_METHODOLOGY_STATISTIC_POLICIES = (
    "min_median_mean",
    "median_iqr",
    "confidence_interval",
)
BENCHMARK_METHODOLOGY_ISOLATION_LEVELS = (
    "none",
    "process_isolated",
    "dedicated_runner",
    "ci_controlled",
)
BENCHMARK_METHODOLOGY_DEFAULT_ISSUES = (
    "benchmark_methodology_not_supplied",
    "native_performance_claim_blocked",
)
BENCHMARK_METHODOLOGY_MAX_ITERATIONS = 1_000_000
TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION = (
    "tuc.toolchain_environment_report.v0"
)
TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS = "diagnostic_only"
TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS = "blocked"
TOOLCHAIN_COMPONENT_KINDS = (
    "python_runtime",
    "python_package",
    "native_compiler",
    "device_runtime",
    "device_driver",
    "container_image",
    "operating_system",
)
TOOLCHAIN_ENVIRONMENT_DEFAULT_ISSUES = (
    "toolchain_environment_not_supplied",
    "native_performance_claim_blocked",
)
BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION = (
    "tuc.break_even_workload_size_report.v0"
)
BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS = "diagnostic_only"
BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS = "blocked"
BREAK_EVEN_WORKLOAD_SIZE_STATUSES = (
    "not_established",
    "estimated_not_validated",
    "validated_by_ci",
)
BREAK_EVEN_WORKLOAD_SIZE_DEFAULT_ISSUES = (
    "break_even_workloads_not_supplied",
    "native_performance_claim_blocked",
)
EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION = (
    "tuc.executable_backend_security_review_report.v0"
)
EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS = "diagnostic_only"
EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS = "blocked"
EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES = (
    "backend_artifact_execution",
    "cache_access",
    "device_access",
    "dynamic_library_loading",
    "generated_code_execution",
    "native_code_execution",
    "network_access",
    "plugin_discovery",
    "subprocess_execution",
)
EXECUTABLE_BACKEND_SECURITY_REVIEW_STATUSES = (
    "not_reviewed",
    "reviewed_not_approved",
    "approved_by_maintainers",
)
EXECUTABLE_BACKEND_SECURITY_REVIEW_DEFAULT_ISSUES = (
    "executable_backend_security_reviews_not_supplied",
    "native_performance_claim_blocked",
)
RUNTIME_EVIDENCE_MATRIX_REPORT_SCHEMA_VERSION = (
    "tuc.runtime_evidence_matrix_report.v0"
)
RUNTIME_EVIDENCE_MATRIX_CONTRACT = "runtime_evidence_matrix.data_only.v0"
RUNTIME_EVIDENCE_MATRIX_ARTIFACT_STATUS = "review_evidence"
RUNTIME_EVIDENCE_MATRIX_SOURCE_BOUNDARIES = (
    "typed_compute_graph",
    "triton_metadata",
    "source_intent_metadata",
    "runtime_backend_equivalence",
)
RUNTIME_EVIDENCE_ARTIFACT_KINDS = (
    "proof_report_golden",
    "frontend_intake_golden",
    "source_intent_return_semantics",
    "source_intent_runtime_returns",
    "hac_ir_golden",
    "runtime_plan_golden",
    "compiler_decision_golden",
    "execution_readiness_golden",
    "execution_trace_golden",
    "tensor_store_evidence",
    "input_manifest",
    "output_contract",
    "public_output_bundle",
    "reference_correctness",
    "execution_receipt",
    "backend_equivalence",
    "backend_equivalence_portfolio",
    "backend_equivalence_portfolio_policy",
)
RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS = (
    "hac_ir_golden",
    "runtime_plan_golden",
    "compiler_decision_golden",
    "execution_readiness_golden",
    "execution_trace_golden",
    "tensor_store_evidence",
    "input_manifest",
    "output_contract",
    "public_output_bundle",
    "reference_correctness",
    "execution_receipt",
)
MAX_PROOF_METADATA_STRING_BYTES = 128
MAX_PROOF_BACKENDS = 16
MAX_RUNTIME_EVIDENCE_MATRIX_REPORT_BYTES = 64 * 1024
MAX_RUNTIME_EVIDENCE_MATRIX_FIELD_BYTES = 512
MAX_RUNTIME_EVIDENCE_GRAPHS = 64
MAX_RUNTIME_EVIDENCE_ARTIFACTS_PER_GRAPH = 32
MAX_PERFORMANCE_PROOF_READINESS_REPORT_BYTES = 64 * 1024
MAX_PERFORMANCE_PROOF_READINESS_FIELD_BYTES = 512
MAX_PERFORMANCE_PROOF_READINESS_ISSUES = 128
MAX_PERFORMANCE_PROOF_RFC_REPORT_BYTES = 64 * 1024
MAX_PERFORMANCE_PROOF_RFC_FIELD_BYTES = 512
MAX_PERFORMANCE_PROOF_RFCS = 128
MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_BYTES = 64 * 1024
MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICY_FIELD_BYTES = 512
MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICIES = 128
MAX_PERFORMANCE_CLAIM_THRESHOLD_BASIS_POINTS = 100_000
MAX_PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_BYTES = 64 * 1024
MAX_PERFORMANCE_ACCEPTANCE_CRITERIA_FIELD_BYTES = 512
MAX_PERFORMANCE_ACCEPTANCE_CRITERIA = 128
MAX_LEAKY_ABSTRACTION_REPORT_BYTES = 64 * 1024
MAX_LEAKY_ABSTRACTION_FIELD_BYTES = 512
MAX_LEAKY_ABSTRACTION_FACTS = 128
MAX_NATIVE_BASELINE_REPORT_BYTES = 64 * 1024
MAX_NATIVE_BASELINE_FIELD_BYTES = 512
MAX_NATIVE_BASELINES = 64
MAX_NATIVE_BASELINE_COMPARISON_REPORT_BYTES = 64 * 1024
MAX_NATIVE_BASELINE_COMPARISON_FIELD_BYTES = 512
MAX_NATIVE_BASELINE_COMPARISONS = 128
MAX_BENCHMARK_ARTIFACT_MANIFEST_REPORT_BYTES = 64 * 1024
MAX_BENCHMARK_ARTIFACT_FIELD_BYTES = 512
MAX_BENCHMARK_ARTIFACTS = 128
MAX_WORKLOAD_SCOPE_REPORT_BYTES = 64 * 1024
MAX_WORKLOAD_SCOPE_FIELD_BYTES = 512
MAX_WORKLOAD_SCOPES = 128
MAX_BENCHMARK_METHODOLOGY_REPORT_BYTES = 64 * 1024
MAX_BENCHMARK_METHODOLOGY_FIELD_BYTES = 512
MAX_BENCHMARK_METHODOLOGIES = 128
MAX_TOOLCHAIN_ENVIRONMENT_REPORT_BYTES = 64 * 1024
MAX_TOOLCHAIN_ENVIRONMENT_FIELD_BYTES = 512
MAX_TOOLCHAIN_COMPONENTS = 128
MAX_BREAK_EVEN_WORKLOAD_SIZE_REPORT_BYTES = 64 * 1024
MAX_BREAK_EVEN_WORKLOAD_SIZE_FIELD_BYTES = 512
MAX_BREAK_EVEN_WORKLOADS = 128
MAX_BREAK_EVEN_WORKLOAD_SIZE = WORKLOAD_SCOPE_MAX_PROBLEM_SIZE
MAX_EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_BYTES = 64 * 1024
MAX_EXECUTABLE_BACKEND_SECURITY_REVIEW_FIELD_BYTES = 512
MAX_EXECUTABLE_BACKEND_SECURITY_REVIEWS = 128

_PROOF_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_BACKEND_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_SHA256_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ProofReportMetadata:
    """Stable metadata printed in proof reports before compiler artifacts."""

    proof_id: str
    proof_version: str
    graph_family: str
    backend_set: tuple[str, ...]
    report_schema: str = PROOF_REPORT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _validate_proof_identifier(self.report_schema, "report_schema")
        _validate_proof_identifier(self.proof_id, "proof_id")
        _validate_proof_identifier(self.proof_version, "proof_version")
        _validate_proof_identifier(self.graph_family, "graph_family")
        normalized_backends = _normalize_backend_set(self.backend_set)
        object.__setattr__(self, "backend_set", normalized_backends)

    def render_lines(self) -> tuple[str, ...]:
        """Return deterministic text lines for proof report rendering."""

        return (
            f"report_schema: {self.report_schema}",
            f"proof_id: {self.proof_id}",
            f"proof_version: {self.proof_version}",
            f"graph_family: {self.graph_family}",
            f"backend_set: {', '.join(self.backend_set)}",
        )


@dataclass(frozen=True)
class RuntimeEvidenceArtifact:
    """One explicit data-only artifact reference in the runtime evidence matrix."""

    artifact_kind: str
    artifact_id: str


@dataclass(frozen=True)
class RuntimeEvidenceGraph:
    """Evidence inventory for one proof or frontend-originated graph."""

    graph_id: str
    graph_family: str
    source_boundary: str
    artifacts: tuple[RuntimeEvidenceArtifact, ...]
    required_artifact_kinds: tuple[str, ...] = RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS

    @property
    def present_artifact_kinds(self) -> frozenset[str]:
        return frozenset(artifact.artifact_kind for artifact in self.artifacts)

    @property
    def missing_required_artifact_kinds(self) -> tuple[str, ...]:
        present = self.present_artifact_kinds
        return tuple(
            artifact_kind
            for artifact_kind in self.required_artifact_kinds
            if artifact_kind not in present
        )

    @property
    def runtime_evidence_complete(self) -> bool:
        return not self.missing_required_artifact_kinds


@dataclass(frozen=True)
class RuntimeEvidenceMatrixReport:
    """Deterministic inventory of proof/runtime evidence across graph fixtures."""

    matrix_id: str
    graphs: tuple[RuntimeEvidenceGraph, ...]
    issues: tuple[str, ...]
    blocked_execution_surfaces: tuple[str, ...] = (
        RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    )
    evidence_contract: str = RUNTIME_EVIDENCE_MATRIX_CONTRACT

    @property
    def runtime_evidence_matrix_complete(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class PerformanceProofReadinessEvidence:
    """One explicit evidence flag for native performance proof readiness."""

    evidence_id: str
    present: bool


@dataclass(frozen=True)
class PerformanceProofReadinessIssue:
    """One missing or invalid performance-proof evidence item."""

    evidence_id: str
    message: str


@dataclass(frozen=True)
class PerformanceProofReadinessReport:
    """Review report for future native performance proof claims."""

    proposal_name: str
    boundary_contract: str
    checked_evidence: tuple[PerformanceProofReadinessEvidence, ...]
    blocked_claims: tuple[str, ...]
    issues: tuple[PerformanceProofReadinessIssue, ...]

    @property
    def ready(self) -> bool:
        return not self.issues


class PerformanceProofReadinessError(AssertionError):
    """Raised when a performance proof proposal is not ready."""


@dataclass(frozen=True)
class PerformanceProofRFC:
    """One bounded RFC entry for a future native performance claim."""

    rfc_id: str
    workload_scope_id: str
    claim_threshold_policy_id: str
    acceptance_criteria_id: str
    evidence_bundle_id: str
    security_review_id: str
    rfc_status: str = "draft"
    rfc_digest: str = "not_supplied"


@dataclass(frozen=True)
class PerformanceProofRFCReport:
    """Diagnostic report for performance-proof RFC review."""

    proposal_name: str
    rfcs: tuple[PerformanceProofRFC, ...]
    issues: tuple[str, ...]

    @property
    def performance_proof_rfc_ready(self) -> bool:
        rfc_issues = tuple(
            issue for issue in self.issues if issue.startswith("performance_proof_rfc")
        )
        return bool(self.rfcs) and not rfc_issues


@dataclass(frozen=True)
class PerformanceClaimThresholdPolicy:
    """One bounded threshold policy for a future native performance claim."""

    policy_id: str
    workload_scope_id: str
    comparison_metric_id: str
    summary_policy_id: str
    threshold_kind: str
    threshold_basis_points: int
    policy_status: str = "draft"
    policy_digest: str = "not_supplied"


@dataclass(frozen=True)
class PerformanceClaimThresholdPolicyReport:
    """Diagnostic report for future performance claim threshold policies."""

    proposal_name: str
    policies: tuple[PerformanceClaimThresholdPolicy, ...]
    issues: tuple[str, ...]

    @property
    def performance_claim_threshold_policy_ready(self) -> bool:
        threshold_issues = tuple(
            issue
            for issue in self.issues
            if issue.startswith(
                (
                    "performance_claim_threshold_policy",
                    "performance_claim_threshold_policies",
                )
            )
        )
        return bool(self.policies) and not threshold_issues


@dataclass(frozen=True)
class PerformanceAcceptanceCriteria:
    """One bounded acceptance-criteria entry for a future performance claim."""

    criteria_id: str
    workload_scope_id: str
    threshold_policy_id: str
    correctness_evidence_id: str
    benchmark_methodology_id: str
    native_baseline_comparison_id: str
    planner_overhead_report_id: str
    break_even_workload_size_id: str
    leaky_abstraction_report_id: str
    executable_security_review_id: str
    criteria_status: str = "draft"
    criteria_digest: str = "not_supplied"


@dataclass(frozen=True)
class PerformanceAcceptanceCriteriaReport:
    """Diagnostic report for future performance acceptance criteria."""

    proposal_name: str
    criteria: tuple[PerformanceAcceptanceCriteria, ...]
    issues: tuple[str, ...]

    @property
    def performance_acceptance_criteria_ready(self) -> bool:
        criteria_issues = tuple(
            issue
            for issue in self.issues
            if issue.startswith("performance_acceptance_criteria")
        )
        return bool(self.criteria) and not criteria_issues


@dataclass(frozen=True)
class LeakyAbstractionFact:
    """One performance fact and its correct home outside HAC-IR."""

    fact_id: str
    correct_home: str
    required_for_performance: bool
    enters_hac_ir: bool = False


@dataclass(frozen=True)
class LeakyAbstractionLeak:
    """One forbidden hardware-specific fact detected in HAC-IR."""

    operation_name: str
    attribute_name: str
    reason: str


@dataclass(frozen=True)
class LeakyAbstractionReport:
    """Diagnostic report for HAC-IR leaky-abstraction review."""

    graph_name: str
    hac_ir_contract_valid: bool
    checked_forbidden_attributes: tuple[str, ...]
    detected_leaks: tuple[LeakyAbstractionLeak, ...]
    performance_facts: tuple[LeakyAbstractionFact, ...]
    issues: tuple[str, ...]

    @property
    def hac_ir_leak_detected(self) -> bool:
        return bool(self.detected_leaks) or any(
            fact.enters_hac_ir for fact in self.performance_facts
        )


@dataclass(frozen=True)
class NativeBaselineProvenance:
    """One data-only native baseline provenance entry."""

    baseline_id: str
    workload_scope_id: str
    implementation_kind: str
    target_platform_id: str
    source_provenance_id: str
    toolchain_id: str
    reproducibility_status: str
    artifact_digest_status: str = "not_supplied"


@dataclass(frozen=True)
class NativeBaselineProvenanceReport:
    """Diagnostic report for native baseline provenance review."""

    proposal_name: str
    baselines: tuple[NativeBaselineProvenance, ...]
    issues: tuple[str, ...]

    @property
    def native_baseline_ready(self) -> bool:
        return bool(self.baselines) and not self.issues


@dataclass(frozen=True)
class NativeBaselineComparison:
    """One data-only native baseline comparison artifact reference."""

    comparison_id: str
    workload_scope_id: str
    baseline_artifact_id: str
    native_artifact_id: str
    comparison_metric_id: str
    summary_policy_id: str
    result_status: str = "not_measured"
    comparison_digest: str = "not_supplied"


@dataclass(frozen=True)
class NativeBaselineComparisonReport:
    """Diagnostic report for native baseline comparison review."""

    proposal_name: str
    comparisons: tuple[NativeBaselineComparison, ...]
    issues: tuple[str, ...]

    @property
    def native_baseline_comparison_ready(self) -> bool:
        comparison_issues = tuple(
            issue
            for issue in self.issues
            if issue.startswith("native_baseline_comparison")
        )
        return bool(self.comparisons) and not comparison_issues


@dataclass(frozen=True)
class BenchmarkArtifactReference:
    """One data-only benchmark artifact manifest entry."""

    artifact_id: str
    artifact_kind: str
    schema_version: str
    artifact_digest: str = "not_supplied"
    storage_scope: str = "review_attachment"


@dataclass(frozen=True)
class BenchmarkArtifactManifestReport:
    """Diagnostic report for benchmark artifact review."""

    proposal_name: str
    artifacts: tuple[BenchmarkArtifactReference, ...]
    issues: tuple[str, ...]

    @property
    def benchmark_artifact_manifest_complete(self) -> bool:
        benchmark_issues = tuple(
            issue for issue in self.issues if issue.startswith("benchmark_artifact")
        )
        return bool(self.artifacts) and not benchmark_issues


@dataclass(frozen=True)
class WorkloadScope:
    """One bounded workload scope for future performance claims."""

    scope_id: str
    operation_family: str
    shape_profile_id: str
    dtype_policy_id: str
    problem_size_min: int
    problem_size_max: int
    correctness_reference_id: str


@dataclass(frozen=True)
class WorkloadScopeReport:
    """Diagnostic report for workload-scope review."""

    proposal_name: str
    scopes: tuple[WorkloadScope, ...]
    issues: tuple[str, ...]

    @property
    def workload_scope_ready(self) -> bool:
        workload_issues = tuple(
            issue for issue in self.issues if issue.startswith("workload_scope")
        )
        return bool(self.scopes) and not workload_issues


@dataclass(frozen=True)
class BenchmarkMethodology:
    """One bounded benchmark methodology policy entry."""

    methodology_id: str
    workload_scope_id: str
    measurement_clock: str
    warmup_iterations: int
    measurement_iterations: int
    statistic_policy: str
    isolation_level: str
    outlier_policy_id: str
    reproducibility_policy_id: str


@dataclass(frozen=True)
class BenchmarkMethodologyReport:
    """Diagnostic report for benchmark methodology review."""

    proposal_name: str
    methodologies: tuple[BenchmarkMethodology, ...]
    issues: tuple[str, ...]

    @property
    def benchmark_methodology_ready(self) -> bool:
        methodology_issues = tuple(
            issue for issue in self.issues if issue.startswith("benchmark_methodology")
        )
        return bool(self.methodologies) and not methodology_issues


@dataclass(frozen=True)
class ToolchainComponent:
    """One bounded toolchain environment component entry."""

    component_id: str
    component_kind: str
    version_id: str
    provenance_id: str
    component_digest: str = "not_supplied"


@dataclass(frozen=True)
class ToolchainEnvironmentReport:
    """Diagnostic report for versioned toolchain environment review."""

    proposal_name: str
    components: tuple[ToolchainComponent, ...]
    issues: tuple[str, ...]

    @property
    def toolchain_environment_ready(self) -> bool:
        toolchain_issues = tuple(
            issue for issue in self.issues if issue.startswith("toolchain")
        )
        return bool(self.components) and not toolchain_issues


@dataclass(frozen=True)
class BreakEvenWorkloadSize:
    """One bounded break-even workload-size evidence entry."""

    break_even_id: str
    workload_scope_id: str
    planner_overhead_report_id: str
    execution_metric_id: str
    amortization_policy_id: str
    break_even_status: str = "not_established"
    break_even_problem_size: int | None = None
    evidence_digest: str = "not_supplied"


@dataclass(frozen=True)
class BreakEvenWorkloadSizeReport:
    """Diagnostic report for future break-even workload-size review."""

    proposal_name: str
    workloads: tuple[BreakEvenWorkloadSize, ...]
    issues: tuple[str, ...]

    @property
    def break_even_workload_size_ready(self) -> bool:
        break_even_issues = tuple(
            issue for issue in self.issues if issue.startswith("break_even")
        )
        return bool(self.workloads) and not break_even_issues


@dataclass(frozen=True)
class ExecutableBackendSecurityReview:
    """One data-only executable backend security review entry."""

    review_id: str
    reviewed_surface: str
    threat_model_id: str
    sandbox_model_id: str
    resource_budget_id: str
    provenance_id: str
    review_status: str = "not_reviewed"
    fuzzing_evidence_id: str = "not_supplied"
    review_digest: str = "not_supplied"


@dataclass(frozen=True)
class ExecutableBackendSecurityReviewReport:
    """Diagnostic report for executable backend security review."""

    proposal_name: str
    reviews: tuple[ExecutableBackendSecurityReview, ...]
    issues: tuple[str, ...]

    @property
    def executable_backend_security_review_ready(self) -> bool:
        security_issues = tuple(
            issue
            for issue in self.issues
            if issue.startswith("executable_backend_security")
        )
        return bool(self.reviews) and not security_issues


def proof_metadata_from_partition_plan(
    *,
    proof_id: str,
    proof_version: str,
    graph_family: str,
    partition_plan: PartitionPlan,
) -> ProofReportMetadata:
    """Build proof metadata from an already validated partition plan."""

    return ProofReportMetadata(
        proof_id=proof_id,
        proof_version=proof_version,
        graph_family=graph_family,
        backend_set=_backend_set_from_assignments(partition_plan.assignments),
    )


def build_runtime_evidence_matrix_report(
    matrix_id: str,
    graphs: Iterable[RuntimeEvidenceGraph] = (),
) -> RuntimeEvidenceMatrixReport:
    """Build a bounded data-only matrix of existing runtime proof evidence."""

    _validate_runtime_evidence_text(matrix_id, "matrix_id")
    normalized_graphs = _normalize_runtime_evidence_graphs(graphs)
    return RuntimeEvidenceMatrixReport(
        matrix_id=matrix_id,
        graphs=normalized_graphs,
        issues=_runtime_evidence_matrix_issues(normalized_graphs),
    )


def build_current_runtime_evidence_matrix_report() -> RuntimeEvidenceMatrixReport:
    """Return the curated current runtime evidence matrix used by CI gates."""

    return build_runtime_evidence_matrix_report(
        "runtime_evidence_matrix_v0",
        (
            RuntimeEvidenceGraph(
                graph_id="proof_of_abstraction",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    _runtime_evidence_artifact(
                        "proof_report_golden",
                        "proof_of_abstraction_report",
                    ),
                    _runtime_evidence_artifact(
                        "hac_ir_golden",
                        "proof_of_abstraction_hac_ir",
                    ),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "proof_of_abstraction_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "proof_of_abstraction_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "proof_of_abstraction_readiness",
                    ),
                    _runtime_evidence_artifact(
                        "execution_trace_golden",
                        "proof_of_abstraction_trace",
                    ),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "proof_of_abstraction_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "proof_of_abstraction_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "proof_of_abstraction_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "proof_of_abstraction_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "proof_of_abstraction_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "proof_of_abstraction_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_reduction",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    _runtime_evidence_artifact(
                        "proof_report_golden",
                        "proof_of_reduction_report",
                    ),
                    _runtime_evidence_artifact("hac_ir_golden", "proof_of_reduction_hac_ir"),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "proof_of_reduction_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "proof_of_reduction_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "proof_of_reduction_readiness",
                    ),
                    _runtime_evidence_artifact(
                        "execution_trace_golden",
                        "proof_of_reduction_trace",
                    ),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "proof_of_reduction_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "proof_of_reduction_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "proof_of_reduction_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "proof_of_reduction_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "proof_of_reduction_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "proof_of_reduction_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_softmax",
                graph_family="objective_alpha",
                source_boundary="typed_compute_graph",
                artifacts=(
                    _runtime_evidence_artifact("proof_report_golden", "proof_of_softmax_report"),
                    _runtime_evidence_artifact("hac_ir_golden", "proof_of_softmax_hac_ir"),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "proof_of_softmax_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "proof_of_softmax_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "proof_of_softmax_readiness",
                    ),
                    _runtime_evidence_artifact("execution_trace_golden", "proof_of_softmax_trace"),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "proof_of_softmax_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "proof_of_softmax_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "proof_of_softmax_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "proof_of_softmax_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "proof_of_softmax_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "proof_of_softmax_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_execution",
                graph_family="objective_alpha_execution",
                source_boundary="typed_compute_graph",
                artifacts=(
                    _runtime_evidence_artifact(
                        "proof_report_golden",
                        "proof_of_execution_report",
                    ),
                    _runtime_evidence_artifact("hac_ir_golden", "proof_of_execution_hac_ir"),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "proof_of_execution_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "proof_of_execution_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "proof_of_execution_readiness",
                    ),
                    _runtime_evidence_artifact(
                        "execution_trace_golden",
                        "proof_of_execution_trace",
                    ),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "proof_of_execution_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "proof_of_execution_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "proof_of_execution_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "proof_of_execution_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "proof_of_execution_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "proof_of_execution_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="proof_of_systolic_execution",
                graph_family="systolic_execution",
                source_boundary="typed_compute_graph",
                artifacts=(
                    _runtime_evidence_artifact(
                        "proof_report_golden",
                        "proof_of_systolic_execution_report",
                    ),
                    _runtime_evidence_artifact(
                        "hac_ir_golden",
                        "proof_of_systolic_execution_hac_ir",
                    ),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "proof_of_systolic_execution_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "proof_of_systolic_execution_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "proof_of_systolic_execution_readiness",
                    ),
                    _runtime_evidence_artifact(
                        "execution_trace_golden",
                        "proof_of_systolic_execution_trace",
                    ),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "proof_of_systolic_execution_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "proof_of_systolic_execution_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "proof_of_systolic_execution_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "proof_of_systolic_execution_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "proof_of_systolic_execution_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "proof_of_systolic_execution_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="triton_metadata_mvp_families",
                graph_family="triton_metadata_mvp",
                source_boundary="triton_metadata",
                artifacts=(
                    _runtime_evidence_artifact(
                        "frontend_intake_golden",
                        "triton_metadata_mvp_families_intake",
                    ),
                    _runtime_evidence_artifact(
                        "hac_ir_golden",
                        "triton_metadata_mvp_families_hac_ir",
                    ),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "triton_metadata_mvp_families_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "triton_metadata_mvp_families_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "triton_metadata_mvp_families_readiness",
                    ),
                    _runtime_evidence_artifact(
                        "execution_trace_golden",
                        "triton_metadata_mvp_families_trace",
                    ),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "triton_metadata_mvp_families_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "triton_metadata_mvp_families_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "triton_metadata_mvp_families_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "triton_metadata_mvp_families_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "triton_metadata_mvp_families_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "triton_metadata_mvp_families_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="source_intent_return_mlp",
                graph_family="source_intent_runtime_returns",
                source_boundary="source_intent_metadata",
                artifacts=(
                    _runtime_evidence_artifact(
                        "frontend_intake_golden",
                        "source_intent_return_mlp_intake",
                    ),
                    _runtime_evidence_artifact(
                        "source_intent_return_semantics",
                        "source_intent_return_mlp_return_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "source_intent_runtime_returns",
                        "source_intent_return_mlp_runtime_returns",
                    ),
                    _runtime_evidence_artifact(
                        "hac_ir_golden",
                        "source_intent_return_mlp_hac_ir",
                    ),
                    _runtime_evidence_artifact(
                        "runtime_plan_golden",
                        "source_intent_return_mlp_runtime_plan",
                    ),
                    _runtime_evidence_artifact(
                        "compiler_decision_golden",
                        "source_intent_return_mlp_compiler_decision",
                    ),
                    _runtime_evidence_artifact(
                        "execution_readiness_golden",
                        "source_intent_return_mlp_readiness",
                    ),
                    _runtime_evidence_artifact(
                        "execution_trace_golden",
                        "source_intent_return_mlp_trace",
                    ),
                    _runtime_evidence_artifact(
                        "tensor_store_evidence",
                        "source_intent_return_mlp_tensor_store_evidence",
                    ),
                    _runtime_evidence_artifact(
                        "input_manifest",
                        "source_intent_return_mlp_input_manifest",
                    ),
                    _runtime_evidence_artifact(
                        "output_contract",
                        "source_intent_return_mlp_output_contract",
                    ),
                    _runtime_evidence_artifact(
                        "public_output_bundle",
                        "source_intent_return_mlp_public_output_bundle",
                    ),
                    _runtime_evidence_artifact(
                        "reference_correctness",
                        "source_intent_return_mlp_reference_semantics",
                    ),
                    _runtime_evidence_artifact(
                        "execution_receipt",
                        "source_intent_return_mlp_execution_receipt",
                    ),
                ),
            ),
            RuntimeEvidenceGraph(
                graph_id="runtime_backend_equivalence",
                graph_family="backend_equivalence",
                source_boundary="runtime_backend_equivalence",
                artifacts=(
                    _runtime_evidence_artifact(
                        "backend_equivalence",
                        "runtime_backend_equivalence_systolic",
                    ),
                ),
                required_artifact_kinds=("backend_equivalence",),
            ),
            RuntimeEvidenceGraph(
                graph_id="runtime_vector_backend_equivalence",
                graph_family="backend_equivalence",
                source_boundary="runtime_backend_equivalence",
                artifacts=(
                    _runtime_evidence_artifact(
                        "backend_equivalence",
                        "runtime_backend_equivalence_vector",
                    ),
                ),
                required_artifact_kinds=("backend_equivalence",),
            ),
            RuntimeEvidenceGraph(
                graph_id="runtime_mixed_backend_equivalence",
                graph_family="backend_equivalence",
                source_boundary="runtime_backend_equivalence",
                artifacts=(
                    _runtime_evidence_artifact(
                        "backend_equivalence",
                        "runtime_backend_equivalence_mixed",
                    ),
                ),
                required_artifact_kinds=("backend_equivalence",),
            ),
            RuntimeEvidenceGraph(
                graph_id="runtime_backend_equivalence_portfolio",
                graph_family="backend_equivalence_portfolio",
                source_boundary="runtime_backend_equivalence",
                artifacts=(
                    _runtime_evidence_artifact(
                        "backend_equivalence_portfolio",
                        "runtime_backend_equivalence_portfolio",
                    ),
                    _runtime_evidence_artifact(
                        "backend_equivalence_portfolio_policy",
                        "runtime_backend_equivalence_portfolio_policy",
                    ),
                ),
                required_artifact_kinds=(
                    "backend_equivalence_portfolio",
                    "backend_equivalence_portfolio_policy",
                ),
            ),
        ),
    )


def build_performance_proof_readiness_report(
    proposal_name: str,
    evidence: Iterable[PerformanceProofReadinessEvidence],
) -> PerformanceProofReadinessReport:
    """Build a bounded report for future performance-proof readiness."""

    _validate_performance_report_text(proposal_name, "proposal_name")
    evidence_by_id = _normalize_performance_evidence(evidence)
    checked_evidence = tuple(
        PerformanceProofReadinessEvidence(
            evidence_id=evidence_id,
            present=evidence_by_id.get(evidence_id, False),
        )
        for evidence_id in PERFORMANCE_PROOF_REQUIRED_EVIDENCE
    )
    issues = tuple(
        PerformanceProofReadinessIssue(
            evidence_id=item.evidence_id,
            message="required performance proof boundary evidence is missing",
        )
        for item in checked_evidence
        if not item.present
    )
    return PerformanceProofReadinessReport(
        proposal_name=proposal_name,
        boundary_contract=PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        checked_evidence=checked_evidence,
        blocked_claims=PERFORMANCE_PROOF_BLOCKED_CLAIMS,
        issues=issues,
    )


def build_performance_proof_rfc_report(
    proposal_name: str,
    rfcs: Iterable[PerformanceProofRFC] = (),
) -> PerformanceProofRFCReport:
    """Build a bounded data-only report for performance-proof RFC review."""

    _validate_performance_proof_rfc_text(proposal_name, "proposal_name")
    normalized_rfcs = _normalize_performance_proof_rfcs(rfcs)
    issues = list(PERFORMANCE_PROOF_RFC_DEFAULT_ISSUES)
    if normalized_rfcs:
        issues.remove("performance_proof_rfcs_not_supplied")
    if any(
        rfc.rfc_status != "accepted_by_maintainers" for rfc in normalized_rfcs
    ):
        issues.append("performance_proof_rfc_not_accepted")
    if any(
        "not_supplied"
        in {
            rfc.claim_threshold_policy_id,
            rfc.acceptance_criteria_id,
            rfc.evidence_bundle_id,
            rfc.security_review_id,
        }
        for rfc in normalized_rfcs
    ):
        issues.append("performance_proof_rfc_evidence_not_supplied")
    if any(rfc.rfc_digest == "not_supplied" for rfc in normalized_rfcs):
        issues.append("performance_proof_rfc_digest_not_supplied")

    return PerformanceProofRFCReport(
        proposal_name=proposal_name,
        rfcs=normalized_rfcs,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_performance_claim_threshold_policy_report(
    proposal_name: str,
    policies: Iterable[PerformanceClaimThresholdPolicy] = (),
) -> PerformanceClaimThresholdPolicyReport:
    """Build a bounded data-only report for performance threshold review."""

    _validate_performance_claim_threshold_policy_text(
        proposal_name,
        "proposal_name",
    )
    normalized_policies = _normalize_performance_claim_threshold_policies(policies)
    issues = list(PERFORMANCE_CLAIM_THRESHOLD_POLICY_DEFAULT_ISSUES)
    if normalized_policies:
        issues.remove("performance_claim_threshold_policies_not_supplied")
    if any(
        policy.policy_status != "accepted_by_maintainers"
        for policy in normalized_policies
    ):
        issues.append("performance_claim_threshold_policy_not_accepted")
    if any(policy.policy_digest == "not_supplied" for policy in normalized_policies):
        issues.append("performance_claim_threshold_policy_digest_not_supplied")

    return PerformanceClaimThresholdPolicyReport(
        proposal_name=proposal_name,
        policies=normalized_policies,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_performance_acceptance_criteria_report(
    proposal_name: str,
    criteria: Iterable[PerformanceAcceptanceCriteria] = (),
) -> PerformanceAcceptanceCriteriaReport:
    """Build a bounded data-only report for performance acceptance criteria."""

    _validate_performance_acceptance_criteria_text(proposal_name, "proposal_name")
    normalized_criteria = _normalize_performance_acceptance_criteria(criteria)
    issues = list(PERFORMANCE_ACCEPTANCE_CRITERIA_DEFAULT_ISSUES)
    if normalized_criteria:
        issues.remove("performance_acceptance_criteria_not_supplied")
    if any(
        item.criteria_status != "accepted_by_maintainers"
        for item in normalized_criteria
    ):
        issues.append("performance_acceptance_criteria_not_accepted")
    if any(
        "not_supplied"
        in {
            item.workload_scope_id,
            item.threshold_policy_id,
            item.correctness_evidence_id,
            item.benchmark_methodology_id,
            item.native_baseline_comparison_id,
            item.planner_overhead_report_id,
            item.break_even_workload_size_id,
            item.leaky_abstraction_report_id,
            item.executable_security_review_id,
        }
        for item in normalized_criteria
    ):
        issues.append("performance_acceptance_criteria_evidence_not_supplied")
    if any(item.criteria_digest == "not_supplied" for item in normalized_criteria):
        issues.append("performance_acceptance_criteria_digest_not_supplied")

    return PerformanceAcceptanceCriteriaReport(
        proposal_name=proposal_name,
        criteria=normalized_criteria,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_leaky_abstraction_report(
    hac_ir: IRModule,
    performance_facts: Iterable[LeakyAbstractionFact] = (),
) -> LeakyAbstractionReport:
    """Build a bounded diagnostic report for HAC-IR abstraction leakage."""

    if not isinstance(hac_ir, IRModule):
        raise TypeError("leaky abstraction report requires an IRModule")
    if hac_ir.stage is not IRStage.HAC_IR:
        raise ValueError("leaky abstraction report requires a HAC-IR module")
    if hac_ir.metadata.get("dialect_version") != HAC_IR_DIALECT_VERSION:
        raise ValueError("leaky abstraction report requires HAC-IR dialect version")

    normalized_facts = _normalize_leaky_abstraction_facts(performance_facts)
    detected_leaks = _detect_hac_ir_hardware_leaks(hac_ir)
    issues = list(LEAKY_ABSTRACTION_DEFAULT_ISSUES)
    if not normalized_facts:
        issues.insert(0, "performance_facts_not_supplied")
    if detected_leaks:
        issues.append("forbidden_hardware_fact_entered_hac_ir")
    if any(fact.enters_hac_ir for fact in normalized_facts):
        issues.append("performance_fact_entered_hac_ir")

    hac_ir_contract_valid = False
    if not detected_leaks:
        try:
            validate_hac_module_contract(hac_ir)
        except (TypeError, ValueError):
            issues.append("hac_ir_contract_invalid")
        else:
            hac_ir_contract_valid = True

    return LeakyAbstractionReport(
        graph_name=hac_ir.graph.name,
        hac_ir_contract_valid=hac_ir_contract_valid,
        checked_forbidden_attributes=tuple(sorted(HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES)),
        detected_leaks=detected_leaks,
        performance_facts=normalized_facts,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_native_baseline_provenance_report(
    proposal_name: str,
    baselines: Iterable[NativeBaselineProvenance] = (),
) -> NativeBaselineProvenanceReport:
    """Build a bounded data-only native baseline provenance report."""

    _validate_native_baseline_text(proposal_name, "proposal_name")
    normalized_baselines = _normalize_native_baselines(baselines)
    issues = list(NATIVE_BASELINE_DEFAULT_ISSUES)
    if normalized_baselines:
        issues.remove("native_baselines_not_supplied")
        if all(
            baseline.reproducibility_status == "reproduced_by_ci"
            for baseline in normalized_baselines
        ):
            issues = [
                issue
                for issue in issues
                if issue != "native_baseline_comparison_not_supplied"
            ]
        else:
            issues.append("native_baseline_not_reproduced_by_ci")
        if any(
            baseline.artifact_digest_status != "supplied"
            for baseline in normalized_baselines
        ):
            issues.append("native_baseline_artifact_digest_not_supplied")

    return NativeBaselineProvenanceReport(
        proposal_name=proposal_name,
        baselines=normalized_baselines,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_native_baseline_comparison_report(
    proposal_name: str,
    comparisons: Iterable[NativeBaselineComparison] = (),
) -> NativeBaselineComparisonReport:
    """Build a bounded data-only native baseline comparison report."""

    _validate_native_baseline_comparison_text(proposal_name, "proposal_name")
    normalized_comparisons = _normalize_native_baseline_comparisons(comparisons)
    issues = list(NATIVE_BASELINE_COMPARISON_DEFAULT_ISSUES)
    if normalized_comparisons:
        issues.remove("native_baseline_comparisons_not_supplied")
    if any(
        comparison.result_status != "validated_by_ci"
        for comparison in normalized_comparisons
    ):
        issues.append("native_baseline_comparison_not_validated_by_ci")
    if any(
        comparison.comparison_digest == "not_supplied"
        for comparison in normalized_comparisons
    ):
        issues.append("native_baseline_comparison_digest_not_supplied")

    return NativeBaselineComparisonReport(
        proposal_name=proposal_name,
        comparisons=normalized_comparisons,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_benchmark_artifact_manifest_report(
    proposal_name: str,
    artifacts: Iterable[BenchmarkArtifactReference] = (),
) -> BenchmarkArtifactManifestReport:
    """Build a bounded data-only benchmark artifact manifest report."""

    _validate_benchmark_artifact_text(proposal_name, "proposal_name")
    normalized_artifacts = _normalize_benchmark_artifacts(artifacts)
    issues = list(BENCHMARK_ARTIFACT_MANIFEST_DEFAULT_ISSUES)
    supplied_kinds = {artifact.artifact_kind for artifact in normalized_artifacts}
    if normalized_artifacts:
        issues.remove("benchmark_artifacts_not_supplied")
    for required_kind in BENCHMARK_ARTIFACT_REQUIRED_KINDS:
        if required_kind not in supplied_kinds:
            issues.append(f"benchmark_artifact_missing_{required_kind}")
    if any(
        artifact.artifact_digest == "not_supplied"
        for artifact in normalized_artifacts
    ):
        issues.append("benchmark_artifact_digest_not_supplied")

    return BenchmarkArtifactManifestReport(
        proposal_name=proposal_name,
        artifacts=normalized_artifacts,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_workload_scope_report(
    proposal_name: str,
    scopes: Iterable[WorkloadScope] = (),
) -> WorkloadScopeReport:
    """Build a bounded data-only workload scope report."""

    _validate_workload_scope_text(proposal_name, "proposal_name")
    normalized_scopes = _normalize_workload_scopes(scopes)
    issues = list(WORKLOAD_SCOPE_DEFAULT_ISSUES)
    if normalized_scopes:
        issues.remove("workload_scopes_not_supplied")

    return WorkloadScopeReport(
        proposal_name=proposal_name,
        scopes=normalized_scopes,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_benchmark_methodology_report(
    proposal_name: str,
    methodologies: Iterable[BenchmarkMethodology] = (),
) -> BenchmarkMethodologyReport:
    """Build a bounded data-only benchmark methodology report."""

    _validate_benchmark_methodology_text(proposal_name, "proposal_name")
    normalized_methodologies = _normalize_benchmark_methodologies(methodologies)
    issues = list(BENCHMARK_METHODOLOGY_DEFAULT_ISSUES)
    if normalized_methodologies:
        issues.remove("benchmark_methodology_not_supplied")

    return BenchmarkMethodologyReport(
        proposal_name=proposal_name,
        methodologies=normalized_methodologies,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_toolchain_environment_report(
    proposal_name: str,
    components: Iterable[ToolchainComponent] = (),
) -> ToolchainEnvironmentReport:
    """Build a bounded data-only toolchain environment report."""

    _validate_toolchain_environment_text(proposal_name, "proposal_name")
    normalized_components = _normalize_toolchain_components(components)
    issues = list(TOOLCHAIN_ENVIRONMENT_DEFAULT_ISSUES)
    if normalized_components:
        issues.remove("toolchain_environment_not_supplied")
    if any(
        component.component_digest == "not_supplied"
        for component in normalized_components
    ):
        issues.append("toolchain_component_digest_not_supplied")

    return ToolchainEnvironmentReport(
        proposal_name=proposal_name,
        components=normalized_components,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_break_even_workload_size_report(
    proposal_name: str,
    workloads: Iterable[BreakEvenWorkloadSize] = (),
) -> BreakEvenWorkloadSizeReport:
    """Build a bounded data-only break-even workload-size report."""

    _validate_break_even_workload_text(proposal_name, "proposal_name")
    normalized_workloads = _normalize_break_even_workloads(workloads)
    issues = list(BREAK_EVEN_WORKLOAD_SIZE_DEFAULT_ISSUES)
    if normalized_workloads:
        issues.remove("break_even_workloads_not_supplied")
    if any(
        workload.break_even_status != "validated_by_ci"
        for workload in normalized_workloads
    ):
        issues.append("break_even_workload_not_validated_by_ci")
    if any(
        workload.break_even_problem_size is None for workload in normalized_workloads
    ):
        issues.append("break_even_workload_size_not_supplied")
    if any(workload.evidence_digest == "not_supplied" for workload in normalized_workloads):
        issues.append("break_even_workload_digest_not_supplied")

    return BreakEvenWorkloadSizeReport(
        proposal_name=proposal_name,
        workloads=normalized_workloads,
        issues=tuple(dict.fromkeys(issues)),
    )


def build_executable_backend_security_review_report(
    proposal_name: str,
    reviews: Iterable[ExecutableBackendSecurityReview] = (),
) -> ExecutableBackendSecurityReviewReport:
    """Build a bounded data-only executable backend security review report."""

    _validate_executable_backend_security_text(proposal_name, "proposal_name")
    normalized_reviews = _normalize_executable_backend_security_reviews(reviews)
    issues = list(EXECUTABLE_BACKEND_SECURITY_REVIEW_DEFAULT_ISSUES)
    if normalized_reviews:
        issues.remove("executable_backend_security_reviews_not_supplied")
    if any(
        review.review_status != "approved_by_maintainers"
        for review in normalized_reviews
    ):
        issues.append("executable_backend_security_review_not_approved")
    if any(
        "not_supplied"
        in {
            review.threat_model_id,
            review.sandbox_model_id,
            review.resource_budget_id,
            review.provenance_id,
            review.fuzzing_evidence_id,
        }
        for review in normalized_reviews
    ):
        issues.append("executable_backend_security_review_evidence_not_supplied")
    if any(review.review_digest == "not_supplied" for review in normalized_reviews):
        issues.append("executable_backend_security_review_digest_not_supplied")

    return ExecutableBackendSecurityReviewReport(
        proposal_name=proposal_name,
        reviews=normalized_reviews,
        issues=tuple(dict.fromkeys(issues)),
    )


def assert_performance_proof_readiness(
    proposal_name: str,
    evidence: Iterable[PerformanceProofReadinessEvidence],
) -> PerformanceProofReadinessReport:
    """Raise unless a performance proof proposal satisfies every evidence item."""

    report = build_performance_proof_readiness_report(proposal_name, evidence)
    if report.issues:
        lines = [f"performance proof proposal {proposal_name!r} is blocked:"]
        lines.extend(f"- {issue.evidence_id}: {issue.message}" for issue in report.issues)
        raise PerformanceProofReadinessError("\n".join(lines))
    return report


def runtime_evidence_matrix_report_to_dict(
    report: RuntimeEvidenceMatrixReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible runtime evidence matrix."""

    _validate_runtime_evidence_matrix_report(report)
    graphs = _normalize_runtime_evidence_graphs(report.graphs)
    return {
        "artifact_status": RUNTIME_EVIDENCE_MATRIX_ARTIFACT_STATUS,
        "blocked_execution_surfaces": list(report.blocked_execution_surfaces),
        "evidence_contract": report.evidence_contract,
        "graph_count": len(graphs),
        "graphs": [
            {
                "artifacts": [
                    {
                        "artifact_id": artifact.artifact_id,
                        "artifact_kind": artifact.artifact_kind,
                        "artifact_status": "present",
                    }
                    for artifact in graph.artifacts
                ],
                "graph_family": graph.graph_family,
                "graph_id": graph.graph_id,
                "missing_required_artifact_kinds": list(
                    graph.missing_required_artifact_kinds
                ),
                "required_artifact_kinds": list(graph.required_artifact_kinds),
                "runtime_evidence_complete": graph.runtime_evidence_complete,
                "source_boundary": graph.source_boundary,
            }
            for graph in graphs
        ],
        "issues": list(report.issues),
        "matrix_id": report.matrix_id,
        "required_artifact_kinds": list(RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS),
        "runtime_evidence_matrix_complete": report.runtime_evidence_matrix_complete,
        "schema_version": RUNTIME_EVIDENCE_MATRIX_REPORT_SCHEMA_VERSION,
    }


def performance_proof_readiness_report_to_dict(
    report: PerformanceProofReadinessReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible performance readiness report."""

    _validate_performance_readiness_report(report)
    return {
        "blocked_claims": list(report.blocked_claims),
        "boundary_contract": report.boundary_contract,
        "checked_evidence": [
            {
                "evidence_id": item.evidence_id,
                "present": item.present,
            }
            for item in report.checked_evidence
        ],
        "issues": [
            {
                "evidence_id": issue.evidence_id,
                "message": issue.message,
            }
            for issue in report.issues
        ],
        "proposal_name": report.proposal_name,
        "ready": report.ready,
        "schema_version": PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION,
    }


def performance_proof_rfc_report_to_dict(
    report: PerformanceProofRFCReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible performance RFC report."""

    _validate_performance_proof_rfc_report(report)
    return {
        "artifact_status": PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": PERFORMANCE_PROOF_RFC_CLAIM_STATUS,
        "performance_proof_rfc_ready": report.performance_proof_rfc_ready,
        "proposal_name": report.proposal_name,
        "rfcs": [
            {
                "acceptance_criteria_id": rfc.acceptance_criteria_id,
                "claim_threshold_policy_id": rfc.claim_threshold_policy_id,
                "evidence_bundle_id": rfc.evidence_bundle_id,
                "rfc_digest": rfc.rfc_digest,
                "rfc_id": rfc.rfc_id,
                "rfc_status": rfc.rfc_status,
                "security_review_id": rfc.security_review_id,
                "workload_scope_id": rfc.workload_scope_id,
            }
            for rfc in report.rfcs
        ],
        "schema_version": PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION,
    }


def performance_claim_threshold_policy_report_to_dict(
    report: PerformanceClaimThresholdPolicyReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible threshold policy report."""

    _validate_performance_claim_threshold_policy_report(report)
    return {
        "artifact_status": PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS,
        "performance_claim_threshold_policy_ready": (
            report.performance_claim_threshold_policy_ready
        ),
        "policies": [
            {
                "comparison_metric_id": policy.comparison_metric_id,
                "policy_digest": policy.policy_digest,
                "policy_id": policy.policy_id,
                "policy_status": policy.policy_status,
                "summary_policy_id": policy.summary_policy_id,
                "threshold_basis_points": policy.threshold_basis_points,
                "threshold_kind": policy.threshold_kind,
                "workload_scope_id": policy.workload_scope_id,
            }
            for policy in report.policies
        ],
        "proposal_name": report.proposal_name,
        "schema_version": PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION,
    }


def performance_acceptance_criteria_report_to_dict(
    report: PerformanceAcceptanceCriteriaReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible acceptance criteria report."""

    _validate_performance_acceptance_criteria_report(report)
    return {
        "artifact_status": PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "criteria": [
            {
                "benchmark_methodology_id": item.benchmark_methodology_id,
                "break_even_workload_size_id": item.break_even_workload_size_id,
                "correctness_evidence_id": item.correctness_evidence_id,
                "criteria_digest": item.criteria_digest,
                "criteria_id": item.criteria_id,
                "criteria_status": item.criteria_status,
                "executable_security_review_id": (
                    item.executable_security_review_id
                ),
                "leaky_abstraction_report_id": item.leaky_abstraction_report_id,
                "native_baseline_comparison_id": (
                    item.native_baseline_comparison_id
                ),
                "planner_overhead_report_id": item.planner_overhead_report_id,
                "threshold_policy_id": item.threshold_policy_id,
                "workload_scope_id": item.workload_scope_id,
            }
            for item in report.criteria
        ],
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_acceptance_criteria_ready": (
            report.performance_acceptance_criteria_ready
        ),
        "performance_claim_status": PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION,
    }


def leaky_abstraction_report_to_dict(
    report: LeakyAbstractionReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible leaky-abstraction report."""

    _validate_leaky_abstraction_report(report)
    return {
        "allowed_fact_homes": list(LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES),
        "artifact_status": LEAKY_ABSTRACTION_ARTIFACT_STATUS,
        "checked_forbidden_attributes": list(report.checked_forbidden_attributes),
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "detected_leaks": [
            {
                "attribute_name": leak.attribute_name,
                "operation_name": leak.operation_name,
                "reason": leak.reason,
            }
            for leak in report.detected_leaks
        ],
        "graph_name": report.graph_name,
        "hac_ir_contract_valid": report.hac_ir_contract_valid,
        "hac_ir_leak_detected": report.hac_ir_leak_detected,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS,
        "performance_facts": [
            {
                "correct_home": fact.correct_home,
                "enters_hac_ir": fact.enters_hac_ir,
                "fact_id": fact.fact_id,
                "required_for_performance": fact.required_for_performance,
            }
            for fact in report.performance_facts
        ],
        "schema_version": LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION,
    }


def native_baseline_provenance_report_to_dict(
    report: NativeBaselineProvenanceReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible native baseline report."""

    _validate_native_baseline_report(report)
    return {
        "artifact_status": NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS,
        "baselines": [
            {
                "artifact_digest_status": baseline.artifact_digest_status,
                "baseline_id": baseline.baseline_id,
                "implementation_kind": baseline.implementation_kind,
                "reproducibility_status": baseline.reproducibility_status,
                "source_provenance_id": baseline.source_provenance_id,
                "target_platform_id": baseline.target_platform_id,
                "toolchain_id": baseline.toolchain_id,
                "workload_scope_id": baseline.workload_scope_id,
            }
            for baseline in report.baselines
        ],
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "native_baseline_ready": report.native_baseline_ready,
        "native_performance_claim": False,
        "performance_claim_status": NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION,
    }


def native_baseline_comparison_report_to_dict(
    report: NativeBaselineComparisonReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible native comparison report."""

    _validate_native_baseline_comparison_report(report)
    return {
        "artifact_status": NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "comparisons": [
            {
                "baseline_artifact_id": comparison.baseline_artifact_id,
                "comparison_digest": comparison.comparison_digest,
                "comparison_id": comparison.comparison_id,
                "comparison_metric_id": comparison.comparison_metric_id,
                "native_artifact_id": comparison.native_artifact_id,
                "result_status": comparison.result_status,
                "summary_policy_id": comparison.summary_policy_id,
                "workload_scope_id": comparison.workload_scope_id,
            }
            for comparison in report.comparisons
        ],
        "issues": list(report.issues),
        "native_baseline_comparison_ready": (
            report.native_baseline_comparison_ready
        ),
        "native_performance_claim": False,
        "performance_claim_status": NATIVE_BASELINE_COMPARISON_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION,
    }


def benchmark_artifact_manifest_report_to_dict(
    report: BenchmarkArtifactManifestReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible benchmark artifact manifest."""

    _validate_benchmark_artifact_manifest_report(report)
    return {
        "artifact_status": BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS,
        "artifacts": [
            {
                "artifact_digest": artifact.artifact_digest,
                "artifact_id": artifact.artifact_id,
                "artifact_kind": artifact.artifact_kind,
                "schema_version": artifact.schema_version,
                "storage_scope": artifact.storage_scope,
            }
            for artifact in report.artifacts
        ],
        "benchmark_artifact_manifest_complete": (
            report.benchmark_artifact_manifest_complete
        ),
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "required_artifact_kinds": list(BENCHMARK_ARTIFACT_REQUIRED_KINDS),
        "schema_version": BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION,
    }


def workload_scope_report_to_dict(report: WorkloadScopeReport) -> dict[str, object]:
    """Return a deterministic JSON-compatible workload scope report."""

    _validate_workload_scope_report(report)
    return {
        "artifact_status": WORKLOAD_SCOPE_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": WORKLOAD_SCOPE_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION,
        "scopes": [
            {
                "correctness_reference_id": scope.correctness_reference_id,
                "dtype_policy_id": scope.dtype_policy_id,
                "operation_family": scope.operation_family,
                "problem_size_max": scope.problem_size_max,
                "problem_size_min": scope.problem_size_min,
                "scope_id": scope.scope_id,
                "shape_profile_id": scope.shape_profile_id,
            }
            for scope in report.scopes
        ],
        "workload_scope_ready": report.workload_scope_ready,
    }


def benchmark_methodology_report_to_dict(
    report: BenchmarkMethodologyReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible benchmark methodology report."""

    _validate_benchmark_methodology_report(report)
    return {
        "artifact_status": BENCHMARK_METHODOLOGY_ARTIFACT_STATUS,
        "benchmark_methodology_ready": report.benchmark_methodology_ready,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "methodologies": [
            {
                "isolation_level": methodology.isolation_level,
                "measurement_clock": methodology.measurement_clock,
                "measurement_iterations": methodology.measurement_iterations,
                "methodology_id": methodology.methodology_id,
                "outlier_policy_id": methodology.outlier_policy_id,
                "reproducibility_policy_id": (
                    methodology.reproducibility_policy_id
                ),
                "statistic_policy": methodology.statistic_policy,
                "warmup_iterations": methodology.warmup_iterations,
                "workload_scope_id": methodology.workload_scope_id,
            }
            for methodology in report.methodologies
        ],
        "native_performance_claim": False,
        "performance_claim_status": BENCHMARK_METHODOLOGY_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION,
    }


def toolchain_environment_report_to_dict(
    report: ToolchainEnvironmentReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible toolchain environment report."""

    _validate_toolchain_environment_report(report)
    return {
        "artifact_status": TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "components": [
            {
                "component_digest": component.component_digest,
                "component_id": component.component_id,
                "component_kind": component.component_kind,
                "provenance_id": component.provenance_id,
                "version_id": component.version_id,
            }
            for component in report.components
        ],
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION,
        "toolchain_environment_ready": report.toolchain_environment_ready,
    }


def break_even_workload_size_report_to_dict(
    report: BreakEvenWorkloadSizeReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible break-even workload report."""

    _validate_break_even_workload_report(report)
    return {
        "artifact_status": BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS,
        "break_even_workload_size_ready": report.break_even_workload_size_ready,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "schema_version": BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION,
        "workloads": [
            {
                "amortization_policy_id": workload.amortization_policy_id,
                "break_even_id": workload.break_even_id,
                "break_even_problem_size": workload.break_even_problem_size,
                "break_even_status": workload.break_even_status,
                "evidence_digest": workload.evidence_digest,
                "execution_metric_id": workload.execution_metric_id,
                "planner_overhead_report_id": (
                    workload.planner_overhead_report_id
                ),
                "workload_scope_id": workload.workload_scope_id,
            }
            for workload in report.workloads
        ],
    }


def executable_backend_security_review_report_to_dict(
    report: ExecutableBackendSecurityReviewReport,
) -> dict[str, object]:
    """Return a deterministic JSON-compatible backend security report."""

    _validate_executable_backend_security_review_report(report)
    return {
        "artifact_status": EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "executable_backend_security_review_ready": (
            report.executable_backend_security_review_ready
        ),
        "issues": list(report.issues),
        "native_performance_claim": False,
        "performance_claim_status": EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS,
        "proposal_name": report.proposal_name,
        "reviews": [
            {
                "fuzzing_evidence_id": review.fuzzing_evidence_id,
                "provenance_id": review.provenance_id,
                "resource_budget_id": review.resource_budget_id,
                "review_digest": review.review_digest,
                "review_id": review.review_id,
                "review_status": review.review_status,
                "reviewed_surface": review.reviewed_surface,
                "sandbox_model_id": review.sandbox_model_id,
                "threat_model_id": review.threat_model_id,
            }
            for review in report.reviews
        ],
        "schema_version": (
            EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION
        ),
    }


def dump_performance_proof_readiness_report(
    report: PerformanceProofReadinessReport,
) -> str:
    """Render a stable review artifact for performance-proof readiness."""

    text = json.dumps(
        performance_proof_readiness_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_PERFORMANCE_PROOF_READINESS_REPORT_BYTES:
        raise ValueError("performance proof readiness report exceeds byte limit")
    return text + "\n"


def dump_runtime_evidence_matrix_report(
    report: RuntimeEvidenceMatrixReport,
) -> str:
    """Render a stable review artifact for runtime evidence coverage."""

    text = json.dumps(
        runtime_evidence_matrix_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_RUNTIME_EVIDENCE_MATRIX_REPORT_BYTES:
        raise ValueError("runtime evidence matrix report exceeds byte limit")
    return text + "\n"


def dump_performance_proof_rfc_report(report: PerformanceProofRFCReport) -> str:
    """Render a stable diagnostic performance-proof RFC report."""

    text = json.dumps(
        performance_proof_rfc_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_PERFORMANCE_PROOF_RFC_REPORT_BYTES:
        raise ValueError("performance proof RFC report exceeds byte limit")
    return text + "\n"


def dump_performance_claim_threshold_policy_report(
    report: PerformanceClaimThresholdPolicyReport,
) -> str:
    """Render a stable diagnostic performance threshold policy report."""

    text = json.dumps(
        performance_claim_threshold_policy_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_BYTES
    ):
        raise ValueError("performance claim threshold policy report exceeds byte limit")
    return text + "\n"


def dump_performance_acceptance_criteria_report(
    report: PerformanceAcceptanceCriteriaReport,
) -> str:
    """Render a stable diagnostic performance acceptance criteria report."""

    text = json.dumps(
        performance_acceptance_criteria_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_BYTES:
        raise ValueError("performance acceptance criteria report exceeds byte limit")
    return text + "\n"


def dump_leaky_abstraction_report(report: LeakyAbstractionReport) -> str:
    """Render a stable diagnostic leaky-abstraction report."""

    text = json.dumps(leaky_abstraction_report_to_dict(report), indent=2, sort_keys=True)
    if len(text.encode("utf-8")) > MAX_LEAKY_ABSTRACTION_REPORT_BYTES:
        raise ValueError("leaky abstraction report exceeds byte limit")
    return text + "\n"


def dump_native_baseline_provenance_report(
    report: NativeBaselineProvenanceReport,
) -> str:
    """Render a stable diagnostic native baseline provenance report."""

    text = json.dumps(
        native_baseline_provenance_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_NATIVE_BASELINE_REPORT_BYTES:
        raise ValueError("native baseline provenance report exceeds byte limit")
    return text + "\n"


def dump_native_baseline_comparison_report(
    report: NativeBaselineComparisonReport,
) -> str:
    """Render a stable diagnostic native baseline comparison report."""

    text = json.dumps(
        native_baseline_comparison_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_NATIVE_BASELINE_COMPARISON_REPORT_BYTES:
        raise ValueError("native baseline comparison report exceeds byte limit")
    return text + "\n"


def dump_benchmark_artifact_manifest_report(
    report: BenchmarkArtifactManifestReport,
) -> str:
    """Render a stable diagnostic benchmark artifact manifest report."""

    text = json.dumps(
        benchmark_artifact_manifest_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BENCHMARK_ARTIFACT_MANIFEST_REPORT_BYTES:
        raise ValueError("benchmark artifact manifest report exceeds byte limit")
    return text + "\n"


def dump_workload_scope_report(report: WorkloadScopeReport) -> str:
    """Render a stable diagnostic workload scope report."""

    text = json.dumps(workload_scope_report_to_dict(report), indent=2, sort_keys=True)
    if len(text.encode("utf-8")) > MAX_WORKLOAD_SCOPE_REPORT_BYTES:
        raise ValueError("workload scope report exceeds byte limit")
    return text + "\n"


def dump_benchmark_methodology_report(report: BenchmarkMethodologyReport) -> str:
    """Render a stable diagnostic benchmark methodology report."""

    text = json.dumps(
        benchmark_methodology_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BENCHMARK_METHODOLOGY_REPORT_BYTES:
        raise ValueError("benchmark methodology report exceeds byte limit")
    return text + "\n"


def dump_toolchain_environment_report(report: ToolchainEnvironmentReport) -> str:
    """Render a stable diagnostic toolchain environment report."""

    text = json.dumps(
        toolchain_environment_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_TOOLCHAIN_ENVIRONMENT_REPORT_BYTES:
        raise ValueError("toolchain environment report exceeds byte limit")
    return text + "\n"


def dump_break_even_workload_size_report(
    report: BreakEvenWorkloadSizeReport,
) -> str:
    """Render a stable diagnostic break-even workload-size report."""

    text = json.dumps(
        break_even_workload_size_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if len(text.encode("utf-8")) > MAX_BREAK_EVEN_WORKLOAD_SIZE_REPORT_BYTES:
        raise ValueError("break-even workload-size report exceeds byte limit")
    return text + "\n"


def dump_executable_backend_security_review_report(
    report: ExecutableBackendSecurityReviewReport,
) -> str:
    """Render a stable diagnostic executable backend security report."""

    text = json.dumps(
        executable_backend_security_review_report_to_dict(report),
        indent=2,
        sort_keys=True,
    )
    if (
        len(text.encode("utf-8"))
        > MAX_EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_BYTES
    ):
        raise ValueError("executable backend security report exceeds byte limit")
    return text + "\n"


def _runtime_evidence_artifact(
    artifact_kind: str,
    artifact_id: str,
) -> RuntimeEvidenceArtifact:
    return RuntimeEvidenceArtifact(
        artifact_kind=artifact_kind,
        artifact_id=artifact_id,
    )


def _backend_set_from_assignments(
    assignments: Iterable[Assignment],
) -> tuple[str, ...]:
    return tuple(sorted({assignment.backend_name for assignment in assignments}))


def _normalize_backend_set(backends: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(backends, tuple):
        raise TypeError("backend_set must be a tuple")
    if not backends:
        raise ValueError("backend_set must not be empty")
    if len(backends) > MAX_PROOF_BACKENDS:
        raise ValueError("backend_set exceeds proof metadata backend limit")
    if len(set(backends)) != len(backends):
        raise ValueError("backend_set must not contain duplicate names")

    normalized: list[str] = []
    for backend in backends:
        if not isinstance(backend, str) or not _BACKEND_NAME_RE.fullmatch(backend):
            raise ValueError("backend_set entries must be safe backend identifiers")
        _validate_string_budget(backend, "backend_set entry")
        normalized.append(backend)
    return tuple(sorted(normalized))


def _normalize_runtime_evidence_graphs(
    graphs: Iterable[RuntimeEvidenceGraph],
) -> tuple[RuntimeEvidenceGraph, ...]:
    normalized = tuple(graphs)
    if len(normalized) > MAX_RUNTIME_EVIDENCE_GRAPHS:
        raise ValueError("runtime evidence graph count exceeds limit")
    seen: set[str] = set()
    checked: list[RuntimeEvidenceGraph] = []
    for graph in normalized:
        if not isinstance(graph, RuntimeEvidenceGraph):
            raise TypeError("runtime evidence graphs must be RuntimeEvidenceGraph")
        _validate_runtime_evidence_text(graph.graph_id, "graph_id")
        _validate_runtime_evidence_text(graph.graph_family, "graph_family")
        if graph.source_boundary not in RUNTIME_EVIDENCE_MATRIX_SOURCE_BOUNDARIES:
            raise ValueError("unsupported runtime evidence source boundary")
        if graph.graph_id in seen:
            raise ValueError("duplicate runtime evidence graph id")
        seen.add(graph.graph_id)
        checked.append(
            RuntimeEvidenceGraph(
                graph_id=graph.graph_id,
                graph_family=graph.graph_family,
                source_boundary=graph.source_boundary,
                artifacts=_normalize_runtime_evidence_artifacts(graph.artifacts),
                required_artifact_kinds=(
                    _normalize_runtime_evidence_required_artifact_kinds(
                        graph.required_artifact_kinds
                    )
                ),
            )
        )
    return tuple(checked)


def _normalize_runtime_evidence_required_artifact_kinds(
    artifact_kinds: Iterable[str],
) -> tuple[str, ...]:
    normalized = tuple(artifact_kinds)
    if not normalized:
        raise ValueError("runtime evidence required artifact kinds must not be empty")
    seen: set[str] = set()
    for artifact_kind in normalized:
        if artifact_kind not in RUNTIME_EVIDENCE_ARTIFACT_KINDS:
            raise ValueError("unsupported runtime evidence required artifact kind")
        if artifact_kind in seen:
            raise ValueError("duplicate runtime evidence required artifact kind")
        seen.add(artifact_kind)
    return normalized


def _normalize_runtime_evidence_artifacts(
    artifacts: Iterable[RuntimeEvidenceArtifact],
) -> tuple[RuntimeEvidenceArtifact, ...]:
    normalized = tuple(artifacts)
    if len(normalized) > MAX_RUNTIME_EVIDENCE_ARTIFACTS_PER_GRAPH:
        raise ValueError("runtime evidence artifact count exceeds limit")
    seen: set[str] = set()
    for artifact in normalized:
        if not isinstance(artifact, RuntimeEvidenceArtifact):
            raise TypeError(
                "runtime evidence artifacts must be RuntimeEvidenceArtifact"
            )
        if artifact.artifact_kind not in RUNTIME_EVIDENCE_ARTIFACT_KINDS:
            raise ValueError("unsupported runtime evidence artifact kind")
        _validate_runtime_evidence_text(artifact.artifact_id, "artifact_id")
        if artifact.artifact_kind in seen:
            raise ValueError("duplicate runtime evidence artifact kind")
        seen.add(artifact.artifact_kind)
    return tuple(
        sorted(
            normalized,
            key=lambda artifact: RUNTIME_EVIDENCE_ARTIFACT_KINDS.index(
                artifact.artifact_kind
            ),
        )
    )


def _runtime_evidence_matrix_issues(
    graphs: tuple[RuntimeEvidenceGraph, ...],
) -> tuple[str, ...]:
    issues: list[str] = []
    if not graphs:
        issues.append("runtime_evidence_graphs_not_supplied")
    for graph in graphs:
        issues.extend(
            f"{graph.graph_id}.missing_{artifact_kind}"
            for artifact_kind in graph.missing_required_artifact_kinds
        )
    return tuple(issues)


def _normalize_native_baselines(
    baselines: Iterable[NativeBaselineProvenance],
) -> tuple[NativeBaselineProvenance, ...]:
    normalized = tuple(baselines)
    if len(normalized) > MAX_NATIVE_BASELINES:
        raise ValueError("native baseline count exceeds limit")
    seen: set[str] = set()
    for baseline in normalized:
        if not isinstance(baseline, NativeBaselineProvenance):
            raise TypeError("native baselines must be NativeBaselineProvenance")
        _validate_native_baseline_text(baseline.baseline_id, "baseline_id")
        _validate_native_baseline_text(
            baseline.workload_scope_id,
            "workload_scope_id",
        )
        _validate_native_baseline_text(
            baseline.target_platform_id,
            "target_platform_id",
        )
        _validate_native_baseline_text(
            baseline.source_provenance_id,
            "source_provenance_id",
        )
        _validate_native_baseline_text(baseline.toolchain_id, "toolchain_id")
        if baseline.baseline_id in seen:
            raise ValueError("duplicate native baseline id")
        if baseline.implementation_kind not in NATIVE_BASELINE_IMPLEMENTATION_KINDS:
            raise ValueError("unsupported native baseline implementation kind")
        if (
            baseline.reproducibility_status
            not in NATIVE_BASELINE_REPRODUCIBILITY_STATUSES
        ):
            raise ValueError("unsupported native baseline reproducibility status")
        if baseline.artifact_digest_status not in {"not_supplied", "supplied"}:
            raise ValueError("unsupported native baseline artifact digest status")
        seen.add(baseline.baseline_id)
    return normalized


def _normalize_native_baseline_comparisons(
    comparisons: Iterable[NativeBaselineComparison],
) -> tuple[NativeBaselineComparison, ...]:
    normalized = tuple(comparisons)
    if len(normalized) > MAX_NATIVE_BASELINE_COMPARISONS:
        raise ValueError("native baseline comparison count exceeds limit")
    seen: set[str] = set()
    for comparison in normalized:
        if not isinstance(comparison, NativeBaselineComparison):
            raise TypeError(
                "native baseline comparisons must be NativeBaselineComparison"
            )
        _validate_native_baseline_comparison_text(
            comparison.comparison_id,
            "comparison_id",
        )
        _validate_native_baseline_comparison_text(
            comparison.workload_scope_id,
            "workload_scope_id",
        )
        _validate_native_baseline_comparison_text(
            comparison.baseline_artifact_id,
            "baseline_artifact_id",
        )
        _validate_native_baseline_comparison_text(
            comparison.native_artifact_id,
            "native_artifact_id",
        )
        _validate_native_baseline_comparison_text(
            comparison.comparison_metric_id,
            "comparison_metric_id",
        )
        _validate_native_baseline_comparison_text(
            comparison.summary_policy_id,
            "summary_policy_id",
        )
        if comparison.comparison_id in seen:
            raise ValueError("duplicate native baseline comparison id")
        if comparison.result_status not in NATIVE_BASELINE_COMPARISON_RESULT_STATUSES:
            raise ValueError("unsupported native baseline comparison result status")
        _validate_native_baseline_comparison_digest(comparison.comparison_digest)
        seen.add(comparison.comparison_id)
    return normalized


def _normalize_benchmark_artifacts(
    artifacts: Iterable[BenchmarkArtifactReference],
) -> tuple[BenchmarkArtifactReference, ...]:
    normalized = tuple(artifacts)
    if len(normalized) > MAX_BENCHMARK_ARTIFACTS:
        raise ValueError("benchmark artifact count exceeds limit")
    seen: set[str] = set()
    for artifact in normalized:
        if not isinstance(artifact, BenchmarkArtifactReference):
            raise TypeError("benchmark artifacts must be BenchmarkArtifactReference")
        _validate_benchmark_artifact_text(artifact.artifact_id, "artifact_id")
        _validate_benchmark_artifact_text(artifact.schema_version, "schema_version")
        if artifact.artifact_id in seen:
            raise ValueError("duplicate benchmark artifact id")
        if artifact.artifact_kind not in BENCHMARK_ARTIFACT_KINDS:
            raise ValueError("unsupported benchmark artifact kind")
        if artifact.storage_scope not in BENCHMARK_ARTIFACT_STORAGE_SCOPES:
            raise ValueError("unsupported benchmark artifact storage scope")
        _validate_benchmark_artifact_digest(artifact.artifact_digest)
        seen.add(artifact.artifact_id)
    return normalized


def _normalize_workload_scopes(
    scopes: Iterable[WorkloadScope],
) -> tuple[WorkloadScope, ...]:
    normalized = tuple(scopes)
    if len(normalized) > MAX_WORKLOAD_SCOPES:
        raise ValueError("workload scope count exceeds limit")
    seen: set[str] = set()
    for scope in normalized:
        if not isinstance(scope, WorkloadScope):
            raise TypeError("workload scopes must be WorkloadScope")
        _validate_workload_scope_text(scope.scope_id, "scope_id")
        _validate_workload_scope_text(scope.shape_profile_id, "shape_profile_id")
        _validate_workload_scope_text(scope.dtype_policy_id, "dtype_policy_id")
        _validate_workload_scope_text(
            scope.correctness_reference_id,
            "correctness_reference_id",
        )
        if scope.scope_id in seen:
            raise ValueError("duplicate workload scope id")
        if scope.operation_family not in WORKLOAD_OPERATION_FAMILIES:
            raise ValueError("unsupported workload operation family")
        _validate_workload_problem_size(scope.problem_size_min, "problem_size_min")
        _validate_workload_problem_size(scope.problem_size_max, "problem_size_max")
        if scope.problem_size_min > scope.problem_size_max:
            raise ValueError("workload problem size min must not exceed max")
        seen.add(scope.scope_id)
    return normalized


def _normalize_benchmark_methodologies(
    methodologies: Iterable[BenchmarkMethodology],
) -> tuple[BenchmarkMethodology, ...]:
    normalized = tuple(methodologies)
    if len(normalized) > MAX_BENCHMARK_METHODOLOGIES:
        raise ValueError("benchmark methodology count exceeds limit")
    seen: set[str] = set()
    for methodology in normalized:
        if not isinstance(methodology, BenchmarkMethodology):
            raise TypeError("benchmark methodologies must be BenchmarkMethodology")
        _validate_benchmark_methodology_text(
            methodology.methodology_id,
            "methodology_id",
        )
        _validate_benchmark_methodology_text(
            methodology.workload_scope_id,
            "workload_scope_id",
        )
        _validate_benchmark_methodology_text(
            methodology.outlier_policy_id,
            "outlier_policy_id",
        )
        _validate_benchmark_methodology_text(
            methodology.reproducibility_policy_id,
            "reproducibility_policy_id",
        )
        if methodology.methodology_id in seen:
            raise ValueError("duplicate benchmark methodology id")
        if methodology.measurement_clock not in BENCHMARK_METHODOLOGY_CLOCKS:
            raise ValueError("unsupported benchmark methodology measurement clock")
        if (
            methodology.statistic_policy
            not in BENCHMARK_METHODOLOGY_STATISTIC_POLICIES
        ):
            raise ValueError("unsupported benchmark methodology statistic policy")
        if methodology.isolation_level not in BENCHMARK_METHODOLOGY_ISOLATION_LEVELS:
            raise ValueError("unsupported benchmark methodology isolation level")
        _validate_benchmark_iteration_count(
            methodology.warmup_iterations,
            "warmup_iterations",
            minimum=0,
        )
        _validate_benchmark_iteration_count(
            methodology.measurement_iterations,
            "measurement_iterations",
            minimum=1,
        )
        seen.add(methodology.methodology_id)
    return normalized


def _normalize_toolchain_components(
    components: Iterable[ToolchainComponent],
) -> tuple[ToolchainComponent, ...]:
    normalized = tuple(components)
    if len(normalized) > MAX_TOOLCHAIN_COMPONENTS:
        raise ValueError("toolchain component count exceeds limit")
    seen: set[str] = set()
    for component in normalized:
        if not isinstance(component, ToolchainComponent):
            raise TypeError("toolchain components must be ToolchainComponent")
        _validate_toolchain_environment_text(component.component_id, "component_id")
        _validate_toolchain_environment_text(component.version_id, "version_id")
        _validate_toolchain_environment_text(component.provenance_id, "provenance_id")
        if component.component_id in seen:
            raise ValueError("duplicate toolchain component id")
        if component.component_kind not in TOOLCHAIN_COMPONENT_KINDS:
            raise ValueError("unsupported toolchain component kind")
        _validate_toolchain_component_digest(component.component_digest)
        seen.add(component.component_id)
    return normalized


def _normalize_break_even_workloads(
    workloads: Iterable[BreakEvenWorkloadSize],
) -> tuple[BreakEvenWorkloadSize, ...]:
    normalized = tuple(workloads)
    if len(normalized) > MAX_BREAK_EVEN_WORKLOADS:
        raise ValueError("break-even workload count exceeds limit")
    seen: set[str] = set()
    for workload in normalized:
        if not isinstance(workload, BreakEvenWorkloadSize):
            raise TypeError("break-even workloads must be BreakEvenWorkloadSize")
        _validate_break_even_workload_text(workload.break_even_id, "break_even_id")
        _validate_break_even_workload_text(
            workload.workload_scope_id,
            "workload_scope_id",
        )
        _validate_break_even_workload_text(
            workload.planner_overhead_report_id,
            "planner_overhead_report_id",
        )
        _validate_break_even_workload_text(
            workload.execution_metric_id,
            "execution_metric_id",
        )
        _validate_break_even_workload_text(
            workload.amortization_policy_id,
            "amortization_policy_id",
        )
        if workload.break_even_id in seen:
            raise ValueError("duplicate break-even workload id")
        if workload.break_even_status not in BREAK_EVEN_WORKLOAD_SIZE_STATUSES:
            raise ValueError("unsupported break-even workload status")
        _validate_break_even_problem_size(
            workload.break_even_problem_size,
            workload.break_even_status,
        )
        _validate_break_even_workload_digest(workload.evidence_digest)
        seen.add(workload.break_even_id)
    return normalized


def _normalize_executable_backend_security_reviews(
    reviews: Iterable[ExecutableBackendSecurityReview],
) -> tuple[ExecutableBackendSecurityReview, ...]:
    normalized = tuple(reviews)
    if len(normalized) > MAX_EXECUTABLE_BACKEND_SECURITY_REVIEWS:
        raise ValueError("executable backend security review count exceeds limit")
    seen: set[str] = set()
    for review in normalized:
        if not isinstance(review, ExecutableBackendSecurityReview):
            raise TypeError(
                "executable backend security reviews must be "
                "ExecutableBackendSecurityReview"
            )
        _validate_executable_backend_security_text(review.review_id, "review_id")
        _validate_executable_backend_security_text(
            review.threat_model_id,
            "threat_model_id",
        )
        _validate_executable_backend_security_text(
            review.sandbox_model_id,
            "sandbox_model_id",
        )
        _validate_executable_backend_security_text(
            review.resource_budget_id,
            "resource_budget_id",
        )
        _validate_executable_backend_security_text(
            review.provenance_id,
            "provenance_id",
        )
        _validate_executable_backend_security_text(
            review.fuzzing_evidence_id,
            "fuzzing_evidence_id",
        )
        if review.review_id in seen:
            raise ValueError("duplicate executable backend security review id")
        if review.reviewed_surface not in EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES:
            raise ValueError("unsupported executable backend security surface")
        if review.review_status not in EXECUTABLE_BACKEND_SECURITY_REVIEW_STATUSES:
            raise ValueError("unsupported executable backend security review status")
        _validate_executable_backend_security_digest(review.review_digest)
        seen.add(review.review_id)
    return normalized


def _normalize_performance_proof_rfcs(
    rfcs: Iterable[PerformanceProofRFC],
) -> tuple[PerformanceProofRFC, ...]:
    normalized = tuple(rfcs)
    if len(normalized) > MAX_PERFORMANCE_PROOF_RFCS:
        raise ValueError("performance proof RFC count exceeds limit")
    seen: set[str] = set()
    for rfc in normalized:
        if not isinstance(rfc, PerformanceProofRFC):
            raise TypeError("performance proof RFCs must be PerformanceProofRFC")
        _validate_performance_proof_rfc_text(rfc.rfc_id, "rfc_id")
        _validate_performance_proof_rfc_text(
            rfc.workload_scope_id,
            "workload_scope_id",
        )
        _validate_performance_proof_rfc_text(
            rfc.claim_threshold_policy_id,
            "claim_threshold_policy_id",
        )
        _validate_performance_proof_rfc_text(
            rfc.acceptance_criteria_id,
            "acceptance_criteria_id",
        )
        _validate_performance_proof_rfc_text(
            rfc.evidence_bundle_id,
            "evidence_bundle_id",
        )
        _validate_performance_proof_rfc_text(
            rfc.security_review_id,
            "security_review_id",
        )
        if rfc.rfc_id in seen:
            raise ValueError("duplicate performance proof RFC id")
        if rfc.rfc_status not in PERFORMANCE_PROOF_RFC_STATUSES:
            raise ValueError("unsupported performance proof RFC status")
        _validate_performance_proof_rfc_digest(rfc.rfc_digest)
        seen.add(rfc.rfc_id)
    return normalized


def _normalize_performance_claim_threshold_policies(
    policies: Iterable[PerformanceClaimThresholdPolicy],
) -> tuple[PerformanceClaimThresholdPolicy, ...]:
    normalized = tuple(policies)
    if len(normalized) > MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICIES:
        raise ValueError("performance claim threshold policy count exceeds limit")
    seen: set[str] = set()
    for policy in normalized:
        if not isinstance(policy, PerformanceClaimThresholdPolicy):
            raise TypeError(
                "performance claim threshold policies must be "
                "PerformanceClaimThresholdPolicy"
            )
        _validate_performance_claim_threshold_policy_text(
            policy.policy_id,
            "policy_id",
        )
        _validate_performance_claim_threshold_policy_text(
            policy.workload_scope_id,
            "workload_scope_id",
        )
        _validate_performance_claim_threshold_policy_text(
            policy.comparison_metric_id,
            "comparison_metric_id",
        )
        _validate_performance_claim_threshold_policy_text(
            policy.summary_policy_id,
            "summary_policy_id",
        )
        if policy.policy_id in seen:
            raise ValueError("duplicate performance claim threshold policy id")
        if policy.threshold_kind not in PERFORMANCE_CLAIM_THRESHOLD_POLICY_KINDS:
            raise ValueError("unsupported performance claim threshold kind")
        if policy.policy_status not in PERFORMANCE_CLAIM_THRESHOLD_POLICY_STATUSES:
            raise ValueError("unsupported performance claim threshold policy status")
        _validate_performance_claim_threshold_basis_points(
            policy.threshold_basis_points
        )
        _validate_performance_claim_threshold_policy_digest(policy.policy_digest)
        seen.add(policy.policy_id)
    return normalized


def _normalize_performance_acceptance_criteria(
    criteria: Iterable[PerformanceAcceptanceCriteria],
) -> tuple[PerformanceAcceptanceCriteria, ...]:
    normalized = tuple(criteria)
    if len(normalized) > MAX_PERFORMANCE_ACCEPTANCE_CRITERIA:
        raise ValueError("performance acceptance criteria count exceeds limit")
    seen: set[str] = set()
    for item in normalized:
        if not isinstance(item, PerformanceAcceptanceCriteria):
            raise TypeError(
                "performance acceptance criteria must be "
                "PerformanceAcceptanceCriteria"
            )
        _validate_performance_acceptance_criteria_text(
            item.criteria_id,
            "criteria_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.workload_scope_id,
            "workload_scope_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.threshold_policy_id,
            "threshold_policy_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.correctness_evidence_id,
            "correctness_evidence_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.benchmark_methodology_id,
            "benchmark_methodology_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.native_baseline_comparison_id,
            "native_baseline_comparison_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.planner_overhead_report_id,
            "planner_overhead_report_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.break_even_workload_size_id,
            "break_even_workload_size_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.leaky_abstraction_report_id,
            "leaky_abstraction_report_id",
        )
        _validate_performance_acceptance_criteria_text(
            item.executable_security_review_id,
            "executable_security_review_id",
        )
        if item.criteria_id in seen:
            raise ValueError("duplicate performance acceptance criteria id")
        if item.criteria_status not in PERFORMANCE_ACCEPTANCE_CRITERIA_STATUSES:
            raise ValueError("unsupported performance acceptance criteria status")
        _validate_performance_acceptance_criteria_digest(item.criteria_digest)
        seen.add(item.criteria_id)
    return normalized


def _normalize_performance_evidence(
    evidence: Iterable[PerformanceProofReadinessEvidence],
) -> dict[str, bool]:
    evidence_by_id: dict[str, bool] = {}
    allowed_ids = frozenset(PERFORMANCE_PROOF_REQUIRED_EVIDENCE)
    for item in tuple(evidence):
        if not isinstance(item, PerformanceProofReadinessEvidence):
            raise TypeError(
                "performance proof readiness evidence must be "
                "PerformanceProofReadinessEvidence"
            )
        _validate_performance_report_text(item.evidence_id, "evidence_id")
        if item.evidence_id not in allowed_ids:
            raise ValueError(f"unsupported performance proof evidence id: {item.evidence_id}")
        if item.evidence_id in evidence_by_id:
            raise ValueError(f"duplicate performance proof evidence id: {item.evidence_id}")
        if type(item.present) is not bool:
            raise TypeError("performance proof evidence present must be bool")
        evidence_by_id[item.evidence_id] = item.present
    return evidence_by_id


def _normalize_leaky_abstraction_facts(
    performance_facts: Iterable[LeakyAbstractionFact],
) -> tuple[LeakyAbstractionFact, ...]:
    facts = tuple(performance_facts)
    if len(facts) > MAX_LEAKY_ABSTRACTION_FACTS:
        raise ValueError("leaky abstraction fact count exceeds limit")
    seen: set[str] = set()
    normalized: list[LeakyAbstractionFact] = []
    for fact in facts:
        if not isinstance(fact, LeakyAbstractionFact):
            raise TypeError("leaky abstraction facts must be LeakyAbstractionFact")
        _validate_leaky_abstraction_text(fact.fact_id, "fact_id")
        if fact.fact_id in seen:
            raise ValueError("duplicate leaky abstraction fact id")
        if fact.correct_home not in LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES:
            raise ValueError("unsupported leaky abstraction fact home")
        if type(fact.required_for_performance) is not bool:
            raise TypeError("required_for_performance must be bool")
        if type(fact.enters_hac_ir) is not bool:
            raise TypeError("enters_hac_ir must be bool")
        seen.add(fact.fact_id)
        normalized.append(fact)
    return tuple(normalized)


def _detect_hac_ir_hardware_leaks(hac_ir: IRModule) -> tuple[LeakyAbstractionLeak, ...]:
    leaks: list[LeakyAbstractionLeak] = []
    for operation in hac_ir.graph.operations:
        for attribute_name in operation.attributes:
            reason = HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES.get(attribute_name)
            if reason is not None:
                leaks.append(
                    LeakyAbstractionLeak(
                        operation_name=operation.name,
                        attribute_name=attribute_name,
                        reason=reason,
                    )
                )
    return tuple(leaks)


def _validate_performance_readiness_report(
    report: PerformanceProofReadinessReport,
) -> None:
    if not isinstance(report, PerformanceProofReadinessReport):
        raise TypeError("performance proof readiness report must be report object")
    _validate_performance_report_text(report.proposal_name, "proposal_name")
    if report.boundary_contract != PERFORMANCE_PROOF_BOUNDARY_CONTRACT:
        raise ValueError(
            "performance proof readiness boundary contract must be "
            f"{PERFORMANCE_PROOF_BOUNDARY_CONTRACT!r}"
        )
    expected_evidence = PERFORMANCE_PROOF_REQUIRED_EVIDENCE
    if tuple(item.evidence_id for item in report.checked_evidence) != expected_evidence:
        raise ValueError("performance proof readiness evidence order must match boundary")
    for item in report.checked_evidence:
        if not isinstance(item, PerformanceProofReadinessEvidence):
            raise TypeError("performance proof checked evidence must be evidence objects")
        if type(item.present) is not bool:
            raise TypeError("performance proof checked evidence present must be bool")
    if tuple(report.blocked_claims) != PERFORMANCE_PROOF_BLOCKED_CLAIMS:
        raise ValueError("performance proof blocked claims must match boundary")
    if len(report.issues) > MAX_PERFORMANCE_PROOF_READINESS_ISSUES:
        raise ValueError("performance proof readiness report exceeds issue limit")
    for issue in report.issues:
        if not isinstance(issue, PerformanceProofReadinessIssue):
            raise TypeError("performance proof readiness issues must be issue objects")
        _validate_performance_report_text(issue.evidence_id, "issue evidence_id")
        _validate_performance_report_text(issue.message, "issue message")


def _validate_performance_proof_rfc_report(
    report: PerformanceProofRFCReport,
) -> None:
    if not isinstance(report, PerformanceProofRFCReport):
        raise TypeError("performance proof RFC report must be report object")
    _validate_performance_proof_rfc_text(report.proposal_name, "proposal_name")
    _normalize_performance_proof_rfcs(report.rfcs)
    for issue in report.issues:
        _validate_performance_proof_rfc_text(issue, "issue")


def _validate_performance_claim_threshold_policy_report(
    report: PerformanceClaimThresholdPolicyReport,
) -> None:
    if not isinstance(report, PerformanceClaimThresholdPolicyReport):
        raise TypeError("performance claim threshold policy report must be report object")
    _validate_performance_claim_threshold_policy_text(
        report.proposal_name,
        "proposal_name",
    )
    _normalize_performance_claim_threshold_policies(report.policies)
    for issue in report.issues:
        _validate_performance_claim_threshold_policy_text(issue, "issue")


def _validate_performance_acceptance_criteria_report(
    report: PerformanceAcceptanceCriteriaReport,
) -> None:
    if not isinstance(report, PerformanceAcceptanceCriteriaReport):
        raise TypeError("performance acceptance criteria report must be report object")
    _validate_performance_acceptance_criteria_text(
        report.proposal_name,
        "proposal_name",
    )
    _normalize_performance_acceptance_criteria(report.criteria)
    for issue in report.issues:
        _validate_performance_acceptance_criteria_text(issue, "issue")


def _validate_native_baseline_report(
    report: NativeBaselineProvenanceReport,
) -> None:
    if not isinstance(report, NativeBaselineProvenanceReport):
        raise TypeError("native baseline report must be report object")
    _validate_native_baseline_text(report.proposal_name, "proposal_name")
    _normalize_native_baselines(report.baselines)
    for issue in report.issues:
        _validate_native_baseline_text(issue, "issue")
    if report.native_baseline_ready:
        raise ValueError("native baseline provenance v0 must remain claim-blocked")


def _validate_native_baseline_comparison_report(
    report: NativeBaselineComparisonReport,
) -> None:
    if not isinstance(report, NativeBaselineComparisonReport):
        raise TypeError("native baseline comparison report must be report object")
    _validate_native_baseline_comparison_text(report.proposal_name, "proposal_name")
    _normalize_native_baseline_comparisons(report.comparisons)
    for issue in report.issues:
        _validate_native_baseline_comparison_text(issue, "issue")


def _validate_benchmark_artifact_manifest_report(
    report: BenchmarkArtifactManifestReport,
) -> None:
    if not isinstance(report, BenchmarkArtifactManifestReport):
        raise TypeError("benchmark artifact manifest report must be report object")
    _validate_benchmark_artifact_text(report.proposal_name, "proposal_name")
    _normalize_benchmark_artifacts(report.artifacts)
    for issue in report.issues:
        _validate_benchmark_artifact_text(issue, "issue")


def _validate_workload_scope_report(report: WorkloadScopeReport) -> None:
    if not isinstance(report, WorkloadScopeReport):
        raise TypeError("workload scope report must be report object")
    _validate_workload_scope_text(report.proposal_name, "proposal_name")
    _normalize_workload_scopes(report.scopes)
    for issue in report.issues:
        _validate_workload_scope_text(issue, "issue")


def _validate_benchmark_methodology_report(
    report: BenchmarkMethodologyReport,
) -> None:
    if not isinstance(report, BenchmarkMethodologyReport):
        raise TypeError("benchmark methodology report must be report object")
    _validate_benchmark_methodology_text(report.proposal_name, "proposal_name")
    _normalize_benchmark_methodologies(report.methodologies)
    for issue in report.issues:
        _validate_benchmark_methodology_text(issue, "issue")


def _validate_toolchain_environment_report(
    report: ToolchainEnvironmentReport,
) -> None:
    if not isinstance(report, ToolchainEnvironmentReport):
        raise TypeError("toolchain environment report must be report object")
    _validate_toolchain_environment_text(report.proposal_name, "proposal_name")
    _normalize_toolchain_components(report.components)
    for issue in report.issues:
        _validate_toolchain_environment_text(issue, "issue")


def _validate_break_even_workload_report(
    report: BreakEvenWorkloadSizeReport,
) -> None:
    if not isinstance(report, BreakEvenWorkloadSizeReport):
        raise TypeError("break-even workload-size report must be report object")
    _validate_break_even_workload_text(report.proposal_name, "proposal_name")
    _normalize_break_even_workloads(report.workloads)
    for issue in report.issues:
        _validate_break_even_workload_text(issue, "issue")


def _validate_executable_backend_security_review_report(
    report: ExecutableBackendSecurityReviewReport,
) -> None:
    if not isinstance(report, ExecutableBackendSecurityReviewReport):
        raise TypeError("executable backend security report must be report object")
    _validate_executable_backend_security_text(report.proposal_name, "proposal_name")
    _normalize_executable_backend_security_reviews(report.reviews)
    for issue in report.issues:
        _validate_executable_backend_security_text(issue, "issue")


def _validate_leaky_abstraction_report(report: LeakyAbstractionReport) -> None:
    if not isinstance(report, LeakyAbstractionReport):
        raise TypeError("leaky abstraction report must be report object")
    _validate_leaky_abstraction_text(report.graph_name, "graph_name")
    if type(report.hac_ir_contract_valid) is not bool:
        raise TypeError("hac_ir_contract_valid must be bool")
    if tuple(report.checked_forbidden_attributes) != tuple(
        sorted(HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES)
    ):
        raise ValueError("checked forbidden attributes must match HAC-IR guard")
    for leak in report.detected_leaks:
        if not isinstance(leak, LeakyAbstractionLeak):
            raise TypeError("detected leaks must be LeakyAbstractionLeak")
        _validate_leaky_abstraction_text(leak.operation_name, "leak operation_name")
        _validate_leaky_abstraction_text(leak.attribute_name, "leak attribute_name")
        _validate_leaky_abstraction_text(leak.reason, "leak reason")
    _normalize_leaky_abstraction_facts(report.performance_facts)
    for issue in report.issues:
        _validate_leaky_abstraction_text(issue, "issue")
    if report.detected_leaks and report.hac_ir_contract_valid:
        raise ValueError("leaky abstraction report cannot validate leaked HAC-IR")


def _validate_runtime_evidence_matrix_report(
    report: RuntimeEvidenceMatrixReport,
) -> None:
    if not isinstance(report, RuntimeEvidenceMatrixReport):
        raise TypeError("runtime evidence matrix report must be report object")
    _validate_runtime_evidence_text(report.matrix_id, "matrix_id")
    if report.evidence_contract != RUNTIME_EVIDENCE_MATRIX_CONTRACT:
        raise ValueError("runtime evidence matrix contract mismatch")
    if (
        tuple(report.blocked_execution_surfaces)
        != RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
    ):
        raise ValueError("runtime evidence matrix blocked surfaces mismatch")
    graphs = _normalize_runtime_evidence_graphs(report.graphs)
    expected_issues = _runtime_evidence_matrix_issues(graphs)
    if tuple(report.issues) != expected_issues:
        raise ValueError("runtime evidence matrix issues must be derived")
    for issue in report.issues:
        _validate_runtime_evidence_text(issue, "runtime evidence issue")


def _validate_proof_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe proof identifier")
    _validate_string_budget(value, label)


def _validate_string_budget(value: str, label: str) -> None:
    if len(value.encode("utf-8")) > MAX_PROOF_METADATA_STRING_BYTES:
        raise ValueError(f"{label} exceeds proof metadata string limit")


def _validate_runtime_evidence_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe runtime evidence identifier")
    if value in {
        "backend_artifact",
        "callable",
        "command",
        "device_id",
        "dynamic_library",
        "env",
        "environment",
        "executable",
        "file_path",
        "generated_code",
        "host_path",
        "import_module",
        "jit_function",
        "module",
        "network",
        "plugin_entrypoint",
        "python_module",
        "python_source",
        "raw_benchmark_output",
        "raw_timing_samples",
        "subprocess",
        "url",
    }:
        raise ValueError(f"{label} names a forbidden execution surface")
    if len(value.encode("utf-8")) > MAX_RUNTIME_EVIDENCE_MATRIX_FIELD_BYTES:
        raise ValueError(f"{label} exceeds runtime evidence field limit")


def _validate_performance_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_PERFORMANCE_PROOF_READINESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds performance proof readiness field limit")


def _validate_performance_proof_rfc_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe performance proof RFC identifier")
    if len(value.encode("utf-8")) > MAX_PERFORMANCE_PROOF_RFC_FIELD_BYTES:
        raise ValueError(f"{label} exceeds performance proof RFC field limit")


def _validate_performance_proof_rfc_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("rfc_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("rfc_digest must be not_supplied or sha256 digest")


def _validate_performance_claim_threshold_policy_text(
    value: str,
    label: str,
) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe performance claim threshold policy identifier"
        )
    if len(value.encode("utf-8")) > MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICY_FIELD_BYTES:
        raise ValueError(f"{label} exceeds performance claim threshold policy limit")


def _validate_performance_claim_threshold_basis_points(value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("threshold_basis_points must be an integer")
    if value < 1 or value > MAX_PERFORMANCE_CLAIM_THRESHOLD_BASIS_POINTS:
        raise ValueError("threshold_basis_points exceeds limit")


def _validate_performance_claim_threshold_policy_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("policy_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("policy_digest must be not_supplied or sha256 digest")


def _validate_performance_acceptance_criteria_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe performance acceptance criteria identifier"
        )
    if len(value.encode("utf-8")) > MAX_PERFORMANCE_ACCEPTANCE_CRITERIA_FIELD_BYTES:
        raise ValueError(f"{label} exceeds performance acceptance criteria limit")


def _validate_performance_acceptance_criteria_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("criteria_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("criteria_digest must be not_supplied or sha256 digest")


def _validate_native_baseline_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe native baseline identifier")
    if len(value.encode("utf-8")) > MAX_NATIVE_BASELINE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds native baseline field limit")


def _validate_native_baseline_comparison_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe native baseline comparison identifier"
        )
    if len(value.encode("utf-8")) > MAX_NATIVE_BASELINE_COMPARISON_FIELD_BYTES:
        raise ValueError(f"{label} exceeds native baseline comparison field limit")


def _validate_native_baseline_comparison_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("comparison_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("comparison_digest must be not_supplied or sha256 digest")


def _validate_benchmark_artifact_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe benchmark artifact identifier")
    if len(value.encode("utf-8")) > MAX_BENCHMARK_ARTIFACT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds benchmark artifact field limit")


def _validate_benchmark_artifact_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("artifact_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("artifact_digest must be not_supplied or sha256 digest")


def _validate_workload_scope_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe workload scope identifier")
    if len(value.encode("utf-8")) > MAX_WORKLOAD_SCOPE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds workload scope field limit")


def _validate_workload_problem_size(value: int, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if value < 1 or value > WORKLOAD_SCOPE_MAX_PROBLEM_SIZE:
        raise ValueError(f"{label} exceeds workload scope problem size limit")


def _validate_benchmark_methodology_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe benchmark methodology identifier")
    if len(value.encode("utf-8")) > MAX_BENCHMARK_METHODOLOGY_FIELD_BYTES:
        raise ValueError(f"{label} exceeds benchmark methodology field limit")


def _validate_benchmark_iteration_count(
    value: int,
    label: str,
    *,
    minimum: int,
) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if value < minimum or value > BENCHMARK_METHODOLOGY_MAX_ITERATIONS:
        raise ValueError(f"{label} exceeds benchmark methodology iteration limit")


def _validate_toolchain_environment_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe toolchain environment identifier")
    if len(value.encode("utf-8")) > MAX_TOOLCHAIN_ENVIRONMENT_FIELD_BYTES:
        raise ValueError(f"{label} exceeds toolchain environment field limit")


def _validate_toolchain_component_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("component_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("component_digest must be not_supplied or sha256 digest")


def _validate_break_even_workload_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe break-even workload identifier")
    if len(value.encode("utf-8")) > MAX_BREAK_EVEN_WORKLOAD_SIZE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds break-even workload field limit")


def _validate_break_even_problem_size(
    value: int | None,
    break_even_status: str,
) -> None:
    if break_even_status == "not_established":
        if value is not None:
            raise ValueError("not_established break-even workload must not supply size")
        return
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("break_even_problem_size must be an integer")
    if value < 1 or value > MAX_BREAK_EVEN_WORKLOAD_SIZE:
        raise ValueError("break_even_problem_size exceeds limit")


def _validate_break_even_workload_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("evidence_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("evidence_digest must be not_supplied or sha256 digest")


def _validate_executable_backend_security_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(
            f"{label} must be a safe executable backend security identifier"
        )
    if len(value.encode("utf-8")) > MAX_EXECUTABLE_BACKEND_SECURITY_REVIEW_FIELD_BYTES:
        raise ValueError(f"{label} exceeds executable backend security field limit")


def _validate_executable_backend_security_digest(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("review_digest must be a string")
    if value == "not_supplied":
        return
    if not _SHA256_DIGEST_RE.fullmatch(value):
        raise ValueError("review_digest must be not_supplied or sha256 digest")


def _validate_leaky_abstraction_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_LEAKY_ABSTRACTION_FIELD_BYTES:
        raise ValueError(f"{label} exceeds leaky abstraction field limit")


__all__ = [
    "BENCHMARK_ARTIFACT_KINDS",
    "BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS",
    "BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS",
    "BENCHMARK_ARTIFACT_MANIFEST_DEFAULT_ISSUES",
    "BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION",
    "BENCHMARK_ARTIFACT_REQUIRED_KINDS",
    "BENCHMARK_ARTIFACT_STORAGE_SCOPES",
    "BenchmarkArtifactManifestReport",
    "BenchmarkArtifactReference",
    "BENCHMARK_METHODOLOGY_ARTIFACT_STATUS",
    "BENCHMARK_METHODOLOGY_CLAIM_STATUS",
    "BENCHMARK_METHODOLOGY_CLOCKS",
    "BENCHMARK_METHODOLOGY_DEFAULT_ISSUES",
    "BENCHMARK_METHODOLOGY_ISOLATION_LEVELS",
    "BENCHMARK_METHODOLOGY_MAX_ITERATIONS",
    "BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION",
    "BENCHMARK_METHODOLOGY_STATISTIC_POLICIES",
    "BenchmarkMethodology",
    "BenchmarkMethodologyReport",
    "BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS",
    "BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS",
    "BREAK_EVEN_WORKLOAD_SIZE_DEFAULT_ISSUES",
    "BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION",
    "BREAK_EVEN_WORKLOAD_SIZE_STATUSES",
    "BreakEvenWorkloadSize",
    "BreakEvenWorkloadSizeReport",
    "EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS",
    "EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS",
    "EXECUTABLE_BACKEND_SECURITY_REVIEW_DEFAULT_ISSUES",
    "EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION",
    "EXECUTABLE_BACKEND_SECURITY_REVIEW_STATUSES",
    "EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES",
    "ExecutableBackendSecurityReview",
    "ExecutableBackendSecurityReviewReport",
    "MAX_PERFORMANCE_ACCEPTANCE_CRITERIA",
    "MAX_PERFORMANCE_ACCEPTANCE_CRITERIA_FIELD_BYTES",
    "MAX_PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_BYTES",
    "MAX_PERFORMANCE_CLAIM_THRESHOLD_BASIS_POINTS",
    "MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICIES",
    "MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICY_FIELD_BYTES",
    "MAX_PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_BYTES",
    "MAX_RUNTIME_EVIDENCE_ARTIFACTS_PER_GRAPH",
    "MAX_RUNTIME_EVIDENCE_GRAPHS",
    "MAX_RUNTIME_EVIDENCE_MATRIX_FIELD_BYTES",
    "MAX_RUNTIME_EVIDENCE_MATRIX_REPORT_BYTES",
    "LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES",
    "LEAKY_ABSTRACTION_ARTIFACT_STATUS",
    "LEAKY_ABSTRACTION_DEFAULT_ISSUES",
    "LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS",
    "LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION",
    "LeakyAbstractionFact",
    "LeakyAbstractionLeak",
    "LeakyAbstractionReport",
    "MAX_PERFORMANCE_PROOF_READINESS_ISSUES",
    "MAX_PERFORMANCE_PROOF_RFC_FIELD_BYTES",
    "MAX_PERFORMANCE_PROOF_RFC_REPORT_BYTES",
    "MAX_PERFORMANCE_PROOF_RFCS",
    "NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS",
    "NATIVE_BASELINE_COMPARISON_CLAIM_STATUS",
    "NATIVE_BASELINE_COMPARISON_DEFAULT_ISSUES",
    "NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION",
    "NATIVE_BASELINE_COMPARISON_RESULT_STATUSES",
    "NATIVE_BASELINE_DEFAULT_ISSUES",
    "NATIVE_BASELINE_IMPLEMENTATION_KINDS",
    "NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS",
    "NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS",
    "NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION",
    "NATIVE_BASELINE_REPRODUCIBILITY_STATUSES",
    "NativeBaselineComparison",
    "NativeBaselineComparisonReport",
    "NativeBaselineProvenance",
    "NativeBaselineProvenanceReport",
    "PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS",
    "PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS",
    "PERFORMANCE_ACCEPTANCE_CRITERIA_DEFAULT_ISSUES",
    "PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION",
    "PERFORMANCE_ACCEPTANCE_CRITERIA_STATUSES",
    "TOOLCHAIN_COMPONENT_KINDS",
    "TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS",
    "TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS",
    "TOOLCHAIN_ENVIRONMENT_DEFAULT_ISSUES",
    "TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION",
    "ToolchainComponent",
    "ToolchainEnvironmentReport",
    "WORKLOAD_OPERATION_FAMILIES",
    "WORKLOAD_SCOPE_ARTIFACT_STATUS",
    "WORKLOAD_SCOPE_CLAIM_STATUS",
    "WORKLOAD_SCOPE_DEFAULT_ISSUES",
    "WORKLOAD_SCOPE_MAX_PROBLEM_SIZE",
    "WORKLOAD_SCOPE_REPORT_SCHEMA_VERSION",
    "WorkloadScope",
    "WorkloadScopeReport",
    "MAX_PROOF_BACKENDS",
    "MAX_PROOF_METADATA_STRING_BYTES",
    "PERFORMANCE_PROOF_BLOCKED_CLAIMS",
    "PERFORMANCE_PROOF_BOUNDARY_CONTRACT",
    "PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS",
    "PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS",
    "PERFORMANCE_CLAIM_THRESHOLD_POLICY_DEFAULT_ISSUES",
    "PERFORMANCE_CLAIM_THRESHOLD_POLICY_KINDS",
    "PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION",
    "PERFORMANCE_CLAIM_THRESHOLD_POLICY_STATUSES",
    "PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION",
    "PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS",
    "PERFORMANCE_PROOF_RFC_CLAIM_STATUS",
    "PERFORMANCE_PROOF_RFC_DEFAULT_ISSUES",
    "PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION",
    "PERFORMANCE_PROOF_RFC_STATUSES",
    "PERFORMANCE_PROOF_REQUIRED_EVIDENCE",
    "PerformanceClaimThresholdPolicy",
    "PerformanceClaimThresholdPolicyReport",
    "PerformanceAcceptanceCriteria",
    "PerformanceAcceptanceCriteriaReport",
    "PerformanceProofReadinessError",
    "PerformanceProofReadinessEvidence",
    "PerformanceProofReadinessIssue",
    "PerformanceProofReadinessReport",
    "PerformanceProofRFC",
    "PerformanceProofRFCReport",
    "PROOF_REPORT_SCHEMA_VERSION",
    "ProofReportMetadata",
    "RUNTIME_EVIDENCE_ARTIFACT_KINDS",
    "RUNTIME_EVIDENCE_MATRIX_ARTIFACT_STATUS",
    "RUNTIME_EVIDENCE_MATRIX_CONTRACT",
    "RUNTIME_EVIDENCE_MATRIX_REPORT_SCHEMA_VERSION",
    "RUNTIME_EVIDENCE_MATRIX_SOURCE_BOUNDARIES",
    "RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KINDS",
    "RuntimeEvidenceArtifact",
    "RuntimeEvidenceGraph",
    "RuntimeEvidenceMatrixReport",
    "assert_performance_proof_readiness",
    "benchmark_artifact_manifest_report_to_dict",
    "benchmark_methodology_report_to_dict",
    "break_even_workload_size_report_to_dict",
    "build_performance_acceptance_criteria_report",
    "build_toolchain_environment_report",
    "build_benchmark_artifact_manifest_report",
    "build_benchmark_methodology_report",
    "build_break_even_workload_size_report",
    "build_executable_backend_security_review_report",
    "build_performance_claim_threshold_policy_report",
    "build_leaky_abstraction_report",
    "build_native_baseline_comparison_report",
    "build_native_baseline_provenance_report",
    "build_performance_proof_readiness_report",
    "build_performance_proof_rfc_report",
    "build_current_runtime_evidence_matrix_report",
    "build_runtime_evidence_matrix_report",
    "build_workload_scope_report",
    "dump_benchmark_artifact_manifest_report",
    "dump_benchmark_methodology_report",
    "dump_break_even_workload_size_report",
    "dump_performance_acceptance_criteria_report",
    "dump_executable_backend_security_review_report",
    "dump_performance_claim_threshold_policy_report",
    "dump_toolchain_environment_report",
    "dump_leaky_abstraction_report",
    "dump_native_baseline_comparison_report",
    "dump_native_baseline_provenance_report",
    "dump_performance_proof_readiness_report",
    "dump_performance_proof_rfc_report",
    "dump_runtime_evidence_matrix_report",
    "dump_workload_scope_report",
    "leaky_abstraction_report_to_dict",
    "native_baseline_comparison_report_to_dict",
    "native_baseline_provenance_report_to_dict",
    "performance_acceptance_criteria_report_to_dict",
    "performance_claim_threshold_policy_report_to_dict",
    "performance_proof_readiness_report_to_dict",
    "performance_proof_rfc_report_to_dict",
    "proof_metadata_from_partition_plan",
    "runtime_evidence_matrix_report_to_dict",
    "executable_backend_security_review_report_to_dict",
    "toolchain_environment_report_to_dict",
    "workload_scope_report_to_dict",
]
