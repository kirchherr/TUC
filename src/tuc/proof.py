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
from tuc.runtime import Assignment, PartitionPlan

PROOF_REPORT_SCHEMA_VERSION = "proof-report.v0"
PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION = (
    "tuc.performance_proof_readiness_report.v0"
)
PERFORMANCE_PROOF_BOUNDARY_CONTRACT = "performance_proof_boundary.blocking.v0"
PERFORMANCE_PROOF_REQUIRED_EVIDENCE = (
    "performance_proof_rfc",
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
MAX_PROOF_METADATA_STRING_BYTES = 128
MAX_PROOF_BACKENDS = 16
MAX_PERFORMANCE_PROOF_READINESS_REPORT_BYTES = 64 * 1024
MAX_PERFORMANCE_PROOF_READINESS_FIELD_BYTES = 512
MAX_PERFORMANCE_PROOF_READINESS_ISSUES = 128
MAX_LEAKY_ABSTRACTION_REPORT_BYTES = 64 * 1024
MAX_LEAKY_ABSTRACTION_FIELD_BYTES = 512
MAX_LEAKY_ABSTRACTION_FACTS = 128
MAX_NATIVE_BASELINE_REPORT_BYTES = 64 * 1024
MAX_NATIVE_BASELINE_FIELD_BYTES = 512
MAX_NATIVE_BASELINES = 64
MAX_BENCHMARK_ARTIFACT_MANIFEST_REPORT_BYTES = 64 * 1024
MAX_BENCHMARK_ARTIFACT_FIELD_BYTES = 512
MAX_BENCHMARK_ARTIFACTS = 128
MAX_WORKLOAD_SCOPE_REPORT_BYTES = 64 * 1024
MAX_WORKLOAD_SCOPE_FIELD_BYTES = 512
MAX_WORKLOAD_SCOPES = 128
MAX_BENCHMARK_METHODOLOGY_REPORT_BYTES = 64 * 1024
MAX_BENCHMARK_METHODOLOGY_FIELD_BYTES = 512
MAX_BENCHMARK_METHODOLOGIES = 128

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


def _validate_proof_identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe proof identifier")
    _validate_string_budget(value, label)


def _validate_string_budget(value: str, label: str) -> None:
    if len(value.encode("utf-8")) > MAX_PROOF_METADATA_STRING_BYTES:
        raise ValueError(f"{label} exceeds proof metadata string limit")


def _validate_performance_report_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    if len(value.encode("utf-8")) > MAX_PERFORMANCE_PROOF_READINESS_FIELD_BYTES:
        raise ValueError(f"{label} exceeds performance proof readiness field limit")


def _validate_native_baseline_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not _PROOF_IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{label} must be a safe native baseline identifier")
    if len(value.encode("utf-8")) > MAX_NATIVE_BASELINE_FIELD_BYTES:
        raise ValueError(f"{label} exceeds native baseline field limit")


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
    "LEAKY_ABSTRACTION_ALLOWED_FACT_HOMES",
    "LEAKY_ABSTRACTION_ARTIFACT_STATUS",
    "LEAKY_ABSTRACTION_DEFAULT_ISSUES",
    "LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS",
    "LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION",
    "LeakyAbstractionFact",
    "LeakyAbstractionLeak",
    "LeakyAbstractionReport",
    "MAX_PERFORMANCE_PROOF_READINESS_ISSUES",
    "NATIVE_BASELINE_DEFAULT_ISSUES",
    "NATIVE_BASELINE_IMPLEMENTATION_KINDS",
    "NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS",
    "NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS",
    "NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION",
    "NATIVE_BASELINE_REPRODUCIBILITY_STATUSES",
    "NativeBaselineProvenance",
    "NativeBaselineProvenanceReport",
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
    "PERFORMANCE_PROOF_READINESS_REPORT_SCHEMA_VERSION",
    "PERFORMANCE_PROOF_REQUIRED_EVIDENCE",
    "PerformanceProofReadinessError",
    "PerformanceProofReadinessEvidence",
    "PerformanceProofReadinessIssue",
    "PerformanceProofReadinessReport",
    "PROOF_REPORT_SCHEMA_VERSION",
    "ProofReportMetadata",
    "assert_performance_proof_readiness",
    "benchmark_artifact_manifest_report_to_dict",
    "benchmark_methodology_report_to_dict",
    "build_benchmark_artifact_manifest_report",
    "build_benchmark_methodology_report",
    "build_leaky_abstraction_report",
    "build_native_baseline_provenance_report",
    "build_performance_proof_readiness_report",
    "build_workload_scope_report",
    "dump_benchmark_artifact_manifest_report",
    "dump_benchmark_methodology_report",
    "dump_leaky_abstraction_report",
    "dump_native_baseline_provenance_report",
    "dump_performance_proof_readiness_report",
    "dump_workload_scope_report",
    "leaky_abstraction_report_to_dict",
    "native_baseline_provenance_report_to_dict",
    "performance_proof_readiness_report_to_dict",
    "proof_metadata_from_partition_plan",
    "workload_scope_report_to_dict",
]
