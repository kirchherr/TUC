"""Emit performance-proof readiness evidence for review."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

try:
    from examples.source_to_intent_research_kernel_ingress import (
        REALISTIC_MVP_PIPELINE_MODULE_SOURCE,
        assert_kernel_ingress_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from examples.source_to_intent_research_kernel_ingress_workload_scope import (
        assert_kernel_ingress_workload_scope_report_contract,
    )
    from examples.source_to_intent_research_kernel_ingress_workload_scope import (
        build_report as build_kernel_ingress_workload_scope_report,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        REALISTIC_MVP_PIPELINE_MODULE_SOURCE,
        assert_kernel_ingress_report_contract,
    )
    from source_to_intent_research_kernel_ingress import (
        build_report as build_kernel_ingress_report,
    )
    from source_to_intent_research_kernel_ingress_workload_scope import (  # type: ignore[no-redef]
        assert_kernel_ingress_workload_scope_report_contract,
    )
    from source_to_intent_research_kernel_ingress_workload_scope import (
        build_report as build_kernel_ingress_workload_scope_report,
    )

from tuc import (
    BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS,
    BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS,
    BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION,
    BENCHMARK_ARTIFACT_REQUIRED_KINDS,
    BENCHMARK_METHODOLOGY_ARTIFACT_STATUS,
    BENCHMARK_METHODOLOGY_CLAIM_STATUS,
    BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION,
    BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS,
    BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS,
    BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION,
    EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES,
    LEAKY_ABSTRACTION_ARTIFACT_STATUS,
    LEAKY_ABSTRACTION_DEFAULT_ISSUES,
    LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS,
    LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION,
    NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS,
    NATIVE_BASELINE_COMPARISON_CLAIM_STATUS,
    NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION,
    NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS,
    NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS,
    NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION,
    PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS,
    PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS,
    PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS,
    PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION,
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
    PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS,
    PERFORMANCE_PROOF_RFC_CLAIM_STATUS,
    PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION,
    TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS,
    TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS,
    TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION,
    BenchmarkArtifactManifestReport,
    BenchmarkArtifactReference,
    BenchmarkMethodology,
    BreakEvenWorkloadSize,
    BreakEvenWorkloadSizeReport,
    ExecutableBackendSecurityReview,
    ExecutableBackendSecurityReviewReport,
    LeakyAbstractionFact,
    NativeBaselineComparison,
    NativeBaselineComparisonReport,
    NativeBaselineProvenance,
    NativeBaselineProvenanceReport,
    PerformanceAcceptanceCriteria,
    PerformanceAcceptanceCriteriaReport,
    PerformanceClaimThresholdPolicy,
    PerformanceClaimThresholdPolicyReport,
    PerformanceProofReadinessEvidence,
    PerformanceProofRFC,
    PerformanceProofRFCReport,
    ToolchainComponent,
    ToolchainEnvironmentReport,
    benchmark_artifact_manifest_report_to_dict,
    benchmark_methodology_report_to_dict,
    break_even_workload_size_report_to_dict,
    build_benchmark_artifact_manifest_report,
    build_benchmark_methodology_report,
    build_break_even_workload_size_report,
    build_executable_backend_security_review_report,
    build_leaky_abstraction_report,
    build_native_baseline_comparison_report,
    build_native_baseline_provenance_report,
    build_performance_acceptance_criteria_report,
    build_performance_claim_threshold_policy_report,
    build_performance_proof_readiness_report,
    build_performance_proof_rfc_report,
    build_toolchain_environment_report,
    dump_performance_proof_readiness_report,
    executable_backend_security_review_report_to_dict,
    leaky_abstraction_report_to_dict,
    native_baseline_comparison_report_to_dict,
    native_baseline_provenance_report_to_dict,
    performance_acceptance_criteria_report_to_dict,
    performance_claim_threshold_policy_report_to_dict,
    performance_proof_rfc_report_to_dict,
    toolchain_environment_report_to_dict,
)
from tuc.backends import LinearAlgebraSimulatorBackend, VectorSimulatorBackend
from tuc.benchmarks import (
    BENCHMARK_REPORT_ARTIFACT_STATUS,
    BENCHMARK_REPORT_CLAIM_BOUNDARY,
    BENCHMARK_REPORT_SCHEMA_VERSION,
    BENCHMARK_SUITE_VERSION,
    PLANNER_OVERHEAD_ARTIFACT_STATUS,
    PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
    PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
    PLANNER_OVERHEAD_NOT_MEASURED_ISSUES,
    PLANNER_OVERHEAD_PHASES,
    PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
    measure_pipeline_planner_overhead,
    planner_overhead_report_to_dict,
)
from tuc.frontend import (
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_intent_to_triton_metadata,
)

_KERNEL_INGRESS_MVP_SOURCE_NAME = "research_mvp_pipeline"
_KERNEL_INGRESS_MVP_KERNEL_NAME = "mvp_pipeline"
_KERNEL_INGRESS_MVP_TENSOR_SHAPES = {
    "a": (4, 8),
    "b": (8, 4),
    "y": (4,),
}
_KERNEL_INGRESS_GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_kernel_ingress.json"
)
_BASELINE_BENCHMARK_SCHEMA_PATH = Path(
    "schemas/baseline_benchmark_report.v0.schema.json"
)
_BENCHMARK_ARTIFACT_MANIFEST_PROPOSAL_NAME = (
    "kernel_ingress_benchmark_artifact_manifest_candidate"
)
_BENCHMARK_ARTIFACT_DESCRIPTOR_FILES: tuple[tuple[str, str, str, Path], ...] = (
    (
        "kernel_ingress_baseline_benchmark_report",
        "baseline_benchmark_report",
        BENCHMARK_REPORT_SCHEMA_VERSION,
        Path("tests/golden/proofs/benchmark_artifacts/baseline_benchmark_report.json"),
    ),
    (
        "kernel_ingress_native_benchmark_report",
        "native_benchmark_report",
        "tuc.native_benchmark_report.v0",
        Path("tests/golden/proofs/benchmark_artifacts/native_benchmark_report.json"),
    ),
    (
        "kernel_ingress_native_baseline_comparison_report",
        "native_baseline_comparison_report",
        NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION,
        Path(
            "tests/golden/proofs/benchmark_artifacts/"
            "native_baseline_comparison_report.json"
        ),
    ),
)
_PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME = (
    "kernel_ingress_performance_proof_governance_candidate"
)
_PERFORMANCE_PROOF_RFC_ID = "kernel_ingress_research_performance_proof_rfc"
_PERFORMANCE_PROOF_RFC_DIGEST_PATH = Path(
    "rfcs/0194-performance-readiness-governance-binding.md"
)
_PERFORMANCE_CLAIM_THRESHOLD_POLICY_ID = "kernel_ingress_threshold_policy"
_PERFORMANCE_CLAIM_THRESHOLD_POLICY_DIGEST_PATH = Path(
    "rfcs/0077-performance-claim-threshold-policy-report.md"
)
_PERFORMANCE_ACCEPTANCE_CRITERIA_ID = "kernel_ingress_acceptance_criteria"
_PERFORMANCE_ACCEPTANCE_CRITERIA_DIGEST_PATH = Path(
    "rfcs/0078-performance-acceptance-criteria-report.md"
)
_PERFORMANCE_EVIDENCE_BUNDLE_ID = "kernel_ingress_readiness_evidence_bundle"
_PERFORMANCE_THRESHOLD_KIND = "ratio_to_native_at_least"
_PERFORMANCE_THRESHOLD_BASIS_POINTS = 9500
_EXECUTABLE_SECURITY_REVIEW_ID = "kernel_ingress_executable_backend_security_review"
_EXECUTABLE_SECURITY_REVIEW_PROPOSAL_NAME = (
    "kernel_ingress_executable_security_review_candidate"
)
_EXECUTABLE_SECURITY_REVIEW_DIGEST_PATH = Path(
    "rfcs/0196-performance-readiness-executable-security-review-binding.md"
)
_EXECUTABLE_SECURITY_THREAT_MODEL_ID = "tuc_compiler_threat_model_v0"
_EXECUTABLE_SECURITY_SANDBOX_MODEL_ID = "data_only_no_execution_review"
_EXECUTABLE_SECURITY_RESOURCE_BUDGET_ID = "bounded_review_metadata_only"
_EXECUTABLE_SECURITY_PROVENANCE_ID = "rfc_0196"
_EXECUTABLE_SECURITY_FUZZING_EVIDENCE_ID = "security_negative_tests_current_suite"
_LEAKY_ABSTRACTION_REPORT_ID = "kernel_ingress_leaky_abstraction_report"
_BREAK_EVEN_WORKLOAD_SIZE_PROPOSAL_NAME = (
    "kernel_ingress_break_even_workload_size_candidate"
)
_BREAK_EVEN_PLANNER_OVERHEAD_REPORT_ID = "kernel_ingress_planner_overhead_report"
_BREAK_EVEN_EXECUTION_METRIC_ID = "median_execution_time_ns"
_BREAK_EVEN_AMORTIZATION_POLICY_ID = "single_compile_many_runs"
_NATIVE_BASELINE_PROVENANCE_PROPOSAL_NAME = (
    "kernel_ingress_native_baseline_provenance_candidate"
)
_NATIVE_BASELINE_TARGET_PLATFORM_ID = "portable_cpu_native_library"
_NATIVE_BASELINE_SOURCE_PROVENANCE_ID = "documented_native_baseline_policy"
_NATIVE_BASELINE_TOOLCHAIN_ID = "kernel_ingress_toolchain_environment_candidate"
_NATIVE_BASELINE_COMPARISON_PROPOSAL_NAME = (
    "kernel_ingress_native_baseline_comparison_candidate"
)
_NATIVE_BASELINE_COMPARISON_METRIC_ID = "median_execution_time_ns"
_NATIVE_BASELINE_COMPARISON_SUMMARY_POLICY_ID = "median_iqr"
_TOOLCHAIN_ENVIRONMENT_PROPOSAL_NAME = "kernel_ingress_toolchain_environment_candidate"
_TOOLCHAIN_ENVIRONMENT_COMPONENT_FILES: tuple[tuple[str, str, str, str, Path], ...] = (
    (
        "ci_python_runtime",
        "python_runtime",
        "python_3.12",
        "github_actions_ci",
        Path(".github/workflows/ci.yml"),
    ),
    (
        "project_dependency_metadata",
        "python_package",
        "pyproject_dependency_set",
        "pyproject_toml",
        Path("pyproject.toml"),
    ),
    (
        "dev_dependency_metadata",
        "python_package",
        "requirements_dev_set",
        "requirements_dev_txt",
        Path("requirements/dev.txt"),
    ),
    (
        "dev_container_image",
        "container_image",
        "ubuntu_24.04_llvm_18_dev",
        "docker_dev_dockerfile",
        Path("docker/dev/Dockerfile"),
    ),
    (
        "native_compiler_policy",
        "native_compiler",
        "clang_18_llvm_18",
        "docker_dev_dockerfile",
        Path("docker/dev/Dockerfile"),
    ),
    (
        "dev_compose_environment",
        "container_image",
        "docker_compose_dev",
        "docker_compose_yaml",
        Path("docker-compose.yml"),
    ),
)
_KERNEL_INGRESS_DIGEST_EVIDENCE = {
    "correctness_goldens": "reference_correctness_digest",
    "runtime_plan_goldens": "runtime_plan_digest",
    "compiler_decision_report_goldens": "compiler_decision_digest",
}
_FORBIDDEN_PERFORMANCE_GOVERNANCE_FIELDS = (
    "host_path",
    "environment",
    "device_id",
    "hardware_serial",
    "raw_timing_samples",
    "command_line",
    "generated_code",
    "backend_artifact",
)


def build_current_performance_proof_readiness_evidence() -> (
    tuple[PerformanceProofReadinessEvidence, ...]
):
    """Return the current metadata-complete performance-proof readiness evidence."""

    return (
        PerformanceProofReadinessEvidence(
            evidence_id="performance_proof_rfc",
            present=_has_kernel_ingress_performance_proof_rfc_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="performance_claim_threshold_policy",
            present=_has_kernel_ingress_performance_threshold_policy_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="performance_acceptance_criteria",
            present=_has_kernel_ingress_performance_acceptance_criteria_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="workload_scope",
            present=_has_kernel_ingress_workload_scope_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="planner_overhead_report",
            present=_has_kernel_ingress_planner_overhead_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="break_even_workload_size",
            present=_has_kernel_ingress_break_even_workload_size_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="correctness_goldens",
            present=_has_kernel_ingress_golden_digest_evidence("correctness_goldens"),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="runtime_plan_goldens",
            present=_has_kernel_ingress_golden_digest_evidence("runtime_plan_goldens"),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="compiler_decision_report_goldens",
            present=_has_kernel_ingress_golden_digest_evidence(
                "compiler_decision_report_goldens"
            ),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="benchmark_report_schema",
            present=_has_benchmark_report_schema_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="benchmark_report_artifacts",
            present=_has_kernel_ingress_benchmark_artifact_manifest_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="executable_backend_security_review",
            present=_has_kernel_ingress_executable_security_review_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="benchmark_methodology",
            present=_has_kernel_ingress_benchmark_methodology_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="native_baseline_provenance",
            present=_has_kernel_ingress_native_baseline_provenance_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="native_baseline_comparison",
            present=_has_kernel_ingress_native_baseline_comparison_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="versioned_toolchain_environment",
            present=_has_versioned_toolchain_environment_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="leaky_abstraction_report",
            present=_has_kernel_ingress_leaky_abstraction_evidence(),
        ),
    )


def main() -> None:
    report = build_performance_proof_readiness_report(
        "current-kernel-ingress-performance-proof-readiness",
        build_current_performance_proof_readiness_evidence(),
    )
    print(dump_performance_proof_readiness_report(report), end="")


def _has_kernel_ingress_executable_security_review_evidence() -> bool:
    report = _build_kernel_ingress_executable_security_review_report()
    payload = executable_backend_security_review_report_to_dict(report)
    expected = {
        "artifact_status": EXECUTABLE_BACKEND_SECURITY_REVIEW_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "executable_backend_security_review_ready": True,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_claim_status": EXECUTABLE_BACKEND_SECURITY_REVIEW_CLAIM_STATUS,
        "proposal_name": _EXECUTABLE_SECURITY_REVIEW_PROPOSAL_NAME,
        "schema_version": EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"executable security review evidence {key} drift")
    reviews = payload["reviews"]
    if not isinstance(reviews, list):
        raise ValueError("executable security review entries drift")
    if len(reviews) != len(EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES):
        raise ValueError("executable security review count drift")
    review_digest = _repository_file_digest(_EXECUTABLE_SECURITY_REVIEW_DIGEST_PATH)
    for review, surface in zip(
        reviews,
        EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES,
        strict=True,
    ):
        if not isinstance(review, dict):
            raise ValueError("executable security review entry drift")
        expected_fields = {
            "fuzzing_evidence_id": _EXECUTABLE_SECURITY_FUZZING_EVIDENCE_ID,
            "provenance_id": _EXECUTABLE_SECURITY_PROVENANCE_ID,
            "resource_budget_id": _EXECUTABLE_SECURITY_RESOURCE_BUDGET_ID,
            "review_digest": review_digest,
            "review_id": _executable_security_review_id(surface),
            "review_status": "approved_by_maintainers",
            "reviewed_surface": surface,
            "sandbox_model_id": _EXECUTABLE_SECURITY_SANDBOX_MODEL_ID,
            "threat_model_id": _EXECUTABLE_SECURITY_THREAT_MODEL_ID,
        }
        for key, value in expected_fields.items():
            if review.get(key) != value:
                raise ValueError(f"executable security review {key} drift")
        for forbidden_key in (
            "host_path",
            "environment",
            "device_id",
            "hardware_serial",
            "raw_benchmark_output",
            "raw_timing_samples",
            "backend_artifact",
            "generated_code",
            "native_source",
            "dynamic_library_path",
            "plugin_entrypoint",
        ):
            if forbidden_key in review:
                raise ValueError("executable security review exposes forbidden data")
    return True


def _build_kernel_ingress_executable_security_review_report() -> (
    ExecutableBackendSecurityReviewReport
):
    return build_executable_backend_security_review_report(
        _EXECUTABLE_SECURITY_REVIEW_PROPOSAL_NAME,
        reviews=tuple(
            ExecutableBackendSecurityReview(
                review_id=_executable_security_review_id(surface),
                reviewed_surface=surface,
                threat_model_id=_EXECUTABLE_SECURITY_THREAT_MODEL_ID,
                sandbox_model_id=_EXECUTABLE_SECURITY_SANDBOX_MODEL_ID,
                resource_budget_id=_EXECUTABLE_SECURITY_RESOURCE_BUDGET_ID,
                provenance_id=_EXECUTABLE_SECURITY_PROVENANCE_ID,
                review_status="approved_by_maintainers",
                fuzzing_evidence_id=_EXECUTABLE_SECURITY_FUZZING_EVIDENCE_ID,
                review_digest=_repository_file_digest(
                    _EXECUTABLE_SECURITY_REVIEW_DIGEST_PATH
                ),
            )
            for surface in EXECUTABLE_BACKEND_SECURITY_REVIEW_SURFACES
        ),
    )


def _executable_security_review_id(surface: str) -> str:
    return f"security_review_{surface}"

def _has_kernel_ingress_benchmark_artifact_manifest_evidence() -> bool:
    report = _build_kernel_ingress_benchmark_artifact_manifest_report()
    payload = benchmark_artifact_manifest_report_to_dict(report)
    expected = {
        "artifact_status": BENCHMARK_ARTIFACT_MANIFEST_ARTIFACT_STATUS,
        "benchmark_artifact_manifest_complete": True,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_claim_status": BENCHMARK_ARTIFACT_MANIFEST_CLAIM_STATUS,
        "proposal_name": _BENCHMARK_ARTIFACT_MANIFEST_PROPOSAL_NAME,
        "required_artifact_kinds": list(BENCHMARK_ARTIFACT_REQUIRED_KINDS),
        "schema_version": BENCHMARK_ARTIFACT_MANIFEST_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"benchmark artifact manifest evidence {key} drift")
    artifacts = payload["artifacts"]
    if not isinstance(artifacts, list):
        raise ValueError("benchmark artifact manifest entries drift")
    if len(artifacts) != len(_BENCHMARK_ARTIFACT_DESCRIPTOR_FILES):
        raise ValueError("benchmark artifact manifest count drift")
    for artifact, expected_artifact in zip(
        artifacts,
        _BENCHMARK_ARTIFACT_DESCRIPTOR_FILES,
        strict=True,
    ):
        if not isinstance(artifact, dict):
            raise ValueError("benchmark artifact manifest entry drift")
        artifact_id, artifact_kind, schema_version, path = expected_artifact
        expected_fields = {
            "artifact_digest": _repository_file_digest(path),
            "artifact_id": artifact_id,
            "artifact_kind": artifact_kind,
            "schema_version": schema_version,
            "storage_scope": "repository_golden",
        }
        for key, value in expected_fields.items():
            if artifact.get(key) != value:
                raise ValueError(f"benchmark artifact manifest {key} drift")
        for forbidden_key in (
            "host_path",
            "url",
            "environment",
            "device_id",
            "hardware_serial",
            "raw_timing_samples",
            "raw_benchmark_output",
            "backend_artifact",
        ):
            if forbidden_key in artifact:
                raise ValueError("benchmark artifact manifest exposes forbidden data")
    return True


def _build_kernel_ingress_benchmark_artifact_manifest_report() -> (
    BenchmarkArtifactManifestReport
):
    return build_benchmark_artifact_manifest_report(
        _BENCHMARK_ARTIFACT_MANIFEST_PROPOSAL_NAME,
        artifacts=tuple(
            BenchmarkArtifactReference(
                artifact_id=artifact_id,
                artifact_kind=artifact_kind,
                schema_version=schema_version,
                artifact_digest=_repository_file_digest(path),
                storage_scope="repository_golden",
            )
            for artifact_id, artifact_kind, schema_version, path in (
                _BENCHMARK_ARTIFACT_DESCRIPTOR_FILES
            )
        ),
    )

def _has_kernel_ingress_performance_proof_rfc_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scope_ids = _kernel_ingress_workload_scope_ids(workload_report)
    report = _build_kernel_ingress_performance_proof_rfc_report(scope_ids)
    payload = performance_proof_rfc_report_to_dict(report)
    expected = {
        "artifact_status": PERFORMANCE_PROOF_RFC_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_claim_status": PERFORMANCE_PROOF_RFC_CLAIM_STATUS,
        "performance_proof_rfc_ready": True,
        "proposal_name": _PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME,
        "schema_version": PERFORMANCE_PROOF_RFC_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"performance proof RFC evidence {key} drift")
    rfcs = payload["rfcs"]
    if not isinstance(rfcs, list) or len(rfcs) != len(scope_ids):
        raise ValueError("performance proof RFC entries drift")
    rfc_digest = _repository_file_digest(_PERFORMANCE_PROOF_RFC_DIGEST_PATH)
    for rfc, scope_id in zip(rfcs, scope_ids, strict=True):
        if not isinstance(rfc, dict):
            raise ValueError("performance proof RFC entry drift")
        expected_fields = {
            "acceptance_criteria_id": _acceptance_criteria_id(scope_id),
            "claim_threshold_policy_id": _threshold_policy_id(scope_id),
            "evidence_bundle_id": _evidence_bundle_id(scope_id),
            "rfc_digest": rfc_digest,
            "rfc_id": _performance_proof_rfc_id(scope_id),
            "rfc_status": "accepted_by_maintainers",
            "security_review_id": _EXECUTABLE_SECURITY_REVIEW_ID,
            "workload_scope_id": scope_id,
        }
        for key, value in expected_fields.items():
            if rfc.get(key) != value:
                raise ValueError(f"performance proof RFC {key} drift")
        for forbidden_key in _FORBIDDEN_PERFORMANCE_GOVERNANCE_FIELDS:
            if forbidden_key in rfc:
                raise ValueError("performance proof RFC exposes forbidden data")
    return True


def _build_kernel_ingress_performance_proof_rfc_report(
    scope_ids: tuple[str, ...],
) -> PerformanceProofRFCReport:
    return build_performance_proof_rfc_report(
        _PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME,
        rfcs=tuple(
            PerformanceProofRFC(
                rfc_id=_performance_proof_rfc_id(scope_id),
                workload_scope_id=scope_id,
                claim_threshold_policy_id=_threshold_policy_id(scope_id),
                acceptance_criteria_id=_acceptance_criteria_id(scope_id),
                evidence_bundle_id=_evidence_bundle_id(scope_id),
                security_review_id=_EXECUTABLE_SECURITY_REVIEW_ID,
                rfc_status="accepted_by_maintainers",
                rfc_digest=_repository_file_digest(_PERFORMANCE_PROOF_RFC_DIGEST_PATH),
            )
            for scope_id in scope_ids
        ),
    )


def _has_kernel_ingress_performance_threshold_policy_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scope_ids = _kernel_ingress_workload_scope_ids(workload_report)
    report = _build_kernel_ingress_performance_threshold_policy_report(scope_ids)
    payload = performance_claim_threshold_policy_report_to_dict(report)
    expected = {
        "artifact_status": PERFORMANCE_CLAIM_THRESHOLD_POLICY_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_claim_status": PERFORMANCE_CLAIM_THRESHOLD_POLICY_CLAIM_STATUS,
        "performance_claim_threshold_policy_ready": True,
        "proposal_name": _PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME,
        "schema_version": PERFORMANCE_CLAIM_THRESHOLD_POLICY_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"performance threshold-policy evidence {key} drift")
    policies = payload["policies"]
    if not isinstance(policies, list) or len(policies) != len(scope_ids):
        raise ValueError("performance threshold-policy entries drift")
    policy_digest = _repository_file_digest(_PERFORMANCE_CLAIM_THRESHOLD_POLICY_DIGEST_PATH)
    for policy, scope_id in zip(policies, scope_ids, strict=True):
        if not isinstance(policy, dict):
            raise ValueError("performance threshold-policy entry drift")
        expected_fields = {
            "comparison_metric_id": _NATIVE_BASELINE_COMPARISON_METRIC_ID,
            "policy_digest": policy_digest,
            "policy_id": _threshold_policy_id(scope_id),
            "policy_status": "accepted_by_maintainers",
            "summary_policy_id": _NATIVE_BASELINE_COMPARISON_SUMMARY_POLICY_ID,
            "threshold_basis_points": _PERFORMANCE_THRESHOLD_BASIS_POINTS,
            "threshold_kind": _PERFORMANCE_THRESHOLD_KIND,
            "workload_scope_id": scope_id,
        }
        for key, value in expected_fields.items():
            if policy.get(key) != value:
                raise ValueError(f"performance threshold-policy {key} drift")
        for forbidden_key in _FORBIDDEN_PERFORMANCE_GOVERNANCE_FIELDS:
            if forbidden_key in policy:
                raise ValueError("performance threshold-policy exposes forbidden data")
    return True


def _build_kernel_ingress_performance_threshold_policy_report(
    scope_ids: tuple[str, ...],
) -> PerformanceClaimThresholdPolicyReport:
    return build_performance_claim_threshold_policy_report(
        _PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME,
        policies=tuple(
            PerformanceClaimThresholdPolicy(
                policy_id=_threshold_policy_id(scope_id),
                workload_scope_id=scope_id,
                comparison_metric_id=_NATIVE_BASELINE_COMPARISON_METRIC_ID,
                summary_policy_id=_NATIVE_BASELINE_COMPARISON_SUMMARY_POLICY_ID,
                threshold_kind=_PERFORMANCE_THRESHOLD_KIND,
                threshold_basis_points=_PERFORMANCE_THRESHOLD_BASIS_POINTS,
                policy_status="accepted_by_maintainers",
                policy_digest=_repository_file_digest(
                    _PERFORMANCE_CLAIM_THRESHOLD_POLICY_DIGEST_PATH
                ),
            )
            for scope_id in scope_ids
        ),
    )


def _has_kernel_ingress_performance_acceptance_criteria_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scope_ids = _kernel_ingress_workload_scope_ids(workload_report)
    report = _build_kernel_ingress_performance_acceptance_criteria_report(scope_ids)
    payload = performance_acceptance_criteria_report_to_dict(report)
    expected = {
        "artifact_status": PERFORMANCE_ACCEPTANCE_CRITERIA_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_acceptance_criteria_ready": True,
        "performance_claim_status": PERFORMANCE_ACCEPTANCE_CRITERIA_CLAIM_STATUS,
        "proposal_name": _PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME,
        "schema_version": PERFORMANCE_ACCEPTANCE_CRITERIA_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"performance acceptance-criteria evidence {key} drift")
    criteria = payload["criteria"]
    if not isinstance(criteria, list) or len(criteria) != len(scope_ids):
        raise ValueError("performance acceptance-criteria entries drift")
    criteria_digest = _repository_file_digest(_PERFORMANCE_ACCEPTANCE_CRITERIA_DIGEST_PATH)
    for item, scope_id in zip(criteria, scope_ids, strict=True):
        if not isinstance(item, dict):
            raise ValueError("performance acceptance-criteria entry drift")
        expected_fields = {
            "benchmark_methodology_id": f"methodology_{scope_id}",
            "break_even_workload_size_id": f"break_even_{scope_id}",
            "correctness_evidence_id": "correctness_goldens",
            "criteria_digest": criteria_digest,
            "criteria_id": _acceptance_criteria_id(scope_id),
            "criteria_status": "accepted_by_maintainers",
            "executable_security_review_id": _EXECUTABLE_SECURITY_REVIEW_ID,
            "leaky_abstraction_report_id": _LEAKY_ABSTRACTION_REPORT_ID,
            "native_baseline_comparison_id": f"native_comparison_{scope_id}",
            "planner_overhead_report_id": _BREAK_EVEN_PLANNER_OVERHEAD_REPORT_ID,
            "threshold_policy_id": _threshold_policy_id(scope_id),
            "workload_scope_id": scope_id,
        }
        for key, value in expected_fields.items():
            if item.get(key) != value:
                raise ValueError(f"performance acceptance-criteria {key} drift")
        for forbidden_key in _FORBIDDEN_PERFORMANCE_GOVERNANCE_FIELDS:
            if forbidden_key in item:
                raise ValueError("performance acceptance-criteria exposes forbidden data")
    return True


def _build_kernel_ingress_performance_acceptance_criteria_report(
    scope_ids: tuple[str, ...],
) -> PerformanceAcceptanceCriteriaReport:
    return build_performance_acceptance_criteria_report(
        _PERFORMANCE_PROOF_GOVERNANCE_PROPOSAL_NAME,
        criteria=tuple(
            PerformanceAcceptanceCriteria(
                criteria_id=_acceptance_criteria_id(scope_id),
                workload_scope_id=scope_id,
                threshold_policy_id=_threshold_policy_id(scope_id),
                correctness_evidence_id="correctness_goldens",
                benchmark_methodology_id=f"methodology_{scope_id}",
                native_baseline_comparison_id=f"native_comparison_{scope_id}",
                planner_overhead_report_id=_BREAK_EVEN_PLANNER_OVERHEAD_REPORT_ID,
                break_even_workload_size_id=f"break_even_{scope_id}",
                leaky_abstraction_report_id=_LEAKY_ABSTRACTION_REPORT_ID,
                executable_security_review_id=_EXECUTABLE_SECURITY_REVIEW_ID,
                criteria_status="accepted_by_maintainers",
                criteria_digest=_repository_file_digest(
                    _PERFORMANCE_ACCEPTANCE_CRITERIA_DIGEST_PATH
                ),
            )
            for scope_id in scope_ids
        ),
    )


def _performance_proof_rfc_id(scope_id: str) -> str:
    return f"{_PERFORMANCE_PROOF_RFC_ID}_{scope_id}"


def _threshold_policy_id(scope_id: str) -> str:
    return f"{_PERFORMANCE_CLAIM_THRESHOLD_POLICY_ID}_{scope_id}"


def _acceptance_criteria_id(scope_id: str) -> str:
    return f"{_PERFORMANCE_ACCEPTANCE_CRITERIA_ID}_{scope_id}"


def _evidence_bundle_id(scope_id: str) -> str:
    return f"{_PERFORMANCE_EVIDENCE_BUNDLE_ID}_{scope_id}"

def _has_kernel_ingress_break_even_workload_size_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scopes = _kernel_ingress_workload_scopes(workload_report)
    report = _build_kernel_ingress_break_even_workload_size_report(scopes)
    payload = break_even_workload_size_report_to_dict(report)
    expected = {
        "artifact_status": BREAK_EVEN_WORKLOAD_SIZE_ARTIFACT_STATUS,
        "break_even_workload_size_ready": False,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": [
            "native_performance_claim_blocked",
            "break_even_workload_not_validated_by_ci",
            "break_even_workload_digest_not_supplied",
        ],
        "native_performance_claim": False,
        "performance_claim_status": BREAK_EVEN_WORKLOAD_SIZE_CLAIM_STATUS,
        "proposal_name": _BREAK_EVEN_WORKLOAD_SIZE_PROPOSAL_NAME,
        "schema_version": BREAK_EVEN_WORKLOAD_SIZE_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"break-even workload-size evidence {key} drift")
    workloads = payload["workloads"]
    if not isinstance(workloads, list):
        raise ValueError("break-even workload-size entries drift")
    if len(workloads) != len(scopes):
        raise ValueError("break-even workload-size count drift")
    for workload, scope in zip(workloads, scopes, strict=True):
        if not isinstance(workload, dict):
            raise ValueError("break-even workload-size entry drift")
        scope_id = str(scope["scope_id"])
        problem_size = int(scope["problem_size_max"])
        expected_fields = {
            "amortization_policy_id": _BREAK_EVEN_AMORTIZATION_POLICY_ID,
            "break_even_id": f"break_even_{scope_id}",
            "break_even_problem_size": problem_size,
            "break_even_status": "estimated_not_validated",
            "evidence_digest": "not_supplied",
            "execution_metric_id": _BREAK_EVEN_EXECUTION_METRIC_ID,
            "planner_overhead_report_id": _BREAK_EVEN_PLANNER_OVERHEAD_REPORT_ID,
            "workload_scope_id": scope_id,
        }
        for key, value in expected_fields.items():
            if workload.get(key) != value:
                raise ValueError(f"break-even workload-size {key} drift")
        for forbidden_key in (
            "host_path",
            "environment",
            "device_id",
            "hardware_serial",
            "raw_timing_samples",
        ):
            if forbidden_key in workload:
                raise ValueError("break-even workload-size exposes forbidden data")
    return True


def _build_kernel_ingress_break_even_workload_size_report(
    scopes: tuple[dict[str, object], ...],
) -> BreakEvenWorkloadSizeReport:
    return build_break_even_workload_size_report(
        _BREAK_EVEN_WORKLOAD_SIZE_PROPOSAL_NAME,
        workloads=tuple(
            BreakEvenWorkloadSize(
                break_even_id=f"break_even_{scope['scope_id']}",
                workload_scope_id=str(scope["scope_id"]),
                planner_overhead_report_id=_BREAK_EVEN_PLANNER_OVERHEAD_REPORT_ID,
                execution_metric_id=_BREAK_EVEN_EXECUTION_METRIC_ID,
                amortization_policy_id=_BREAK_EVEN_AMORTIZATION_POLICY_ID,
                break_even_status="estimated_not_validated",
                break_even_problem_size=int(scope["problem_size_max"]),
            )
            for scope in scopes
        ),
    )


def _has_kernel_ingress_native_baseline_provenance_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scope_ids = _kernel_ingress_workload_scope_ids(workload_report)
    report = _build_kernel_ingress_native_baseline_provenance_report(scope_ids)
    payload = native_baseline_provenance_report_to_dict(report)
    expected = {
        "artifact_status": NATIVE_BASELINE_PROVENANCE_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": [
            "native_baseline_comparison_not_supplied",
            "native_performance_claim_blocked",
            "native_baseline_not_reproduced_by_ci",
            "native_baseline_artifact_digest_not_supplied",
        ],
        "native_baseline_ready": False,
        "native_performance_claim": False,
        "performance_claim_status": NATIVE_BASELINE_PROVENANCE_CLAIM_STATUS,
        "proposal_name": _NATIVE_BASELINE_PROVENANCE_PROPOSAL_NAME,
        "schema_version": NATIVE_BASELINE_PROVENANCE_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"native baseline provenance evidence {key} drift")
    baselines = payload["baselines"]
    if not isinstance(baselines, list):
        raise ValueError("native baseline provenance entries drift")
    if len(baselines) != len(scope_ids):
        raise ValueError("native baseline provenance count drift")
    observed_scope_ids = tuple(
        str(baseline["workload_scope_id"])
        for baseline in baselines
        if isinstance(baseline, dict)
    )
    if observed_scope_ids != scope_ids:
        raise ValueError("native baseline provenance scope binding drift")
    for baseline in baselines:
        if not isinstance(baseline, dict):
            raise ValueError("native baseline provenance entry drift")
        expected_fields = {
            "artifact_digest_status": "not_supplied",
            "implementation_kind": "vendor_library",
            "reproducibility_status": "documented_not_executed",
            "source_provenance_id": _NATIVE_BASELINE_SOURCE_PROVENANCE_ID,
            "target_platform_id": _NATIVE_BASELINE_TARGET_PLATFORM_ID,
            "toolchain_id": _NATIVE_BASELINE_TOOLCHAIN_ID,
        }
        for key, value in expected_fields.items():
            if baseline.get(key) != value:
                raise ValueError(f"native baseline provenance {key} drift")
        for forbidden_key in ("host_path", "environment", "device_id", "hardware_serial"):
            if forbidden_key in baseline:
                raise ValueError("native baseline provenance exposes forbidden host data")
    return True


def _build_kernel_ingress_native_baseline_provenance_report(
    scope_ids: tuple[str, ...],
) -> NativeBaselineProvenanceReport:
    return build_native_baseline_provenance_report(
        _NATIVE_BASELINE_PROVENANCE_PROPOSAL_NAME,
        baselines=tuple(
            NativeBaselineProvenance(
                baseline_id=f"native_baseline_{scope_id}",
                workload_scope_id=scope_id,
                implementation_kind="vendor_library",
                target_platform_id=_NATIVE_BASELINE_TARGET_PLATFORM_ID,
                source_provenance_id=_NATIVE_BASELINE_SOURCE_PROVENANCE_ID,
                toolchain_id=_NATIVE_BASELINE_TOOLCHAIN_ID,
                reproducibility_status="documented_not_executed",
            )
            for scope_id in scope_ids
        ),
    )


def _kernel_ingress_workload_scope_ids(
    workload_report: dict[str, object],
) -> tuple[str, ...]:
    return tuple(
        str(scope["scope_id"])
        for scope in _kernel_ingress_workload_scopes(workload_report)
    )


def _kernel_ingress_workload_scopes(
    workload_report: dict[str, object],
) -> tuple[dict[str, object], ...]:
    scopes = workload_report["scopes"]
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("kernel ingress workload scopes missing")
    normalized = tuple(scope for scope in scopes if isinstance(scope, dict))
    if len(normalized) != len(scopes):
        raise ValueError("kernel ingress workload scope drift")
    for scope in normalized:
        scope_id = scope.get("scope_id")
        problem_size_max = scope.get("problem_size_max")
        if not isinstance(scope_id, str) or not isinstance(problem_size_max, int):
            raise ValueError("kernel ingress workload scope shape drift")
    return normalized


def _has_kernel_ingress_native_baseline_comparison_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scope_ids = _kernel_ingress_workload_scope_ids(workload_report)
    report = _build_kernel_ingress_native_baseline_comparison_report(scope_ids)
    payload = native_baseline_comparison_report_to_dict(report)
    expected = {
        "artifact_status": NATIVE_BASELINE_COMPARISON_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": [
            "native_performance_claim_blocked",
            "native_baseline_comparison_not_validated_by_ci",
            "native_baseline_comparison_digest_not_supplied",
        ],
        "native_baseline_comparison_ready": False,
        "native_performance_claim": False,
        "performance_claim_status": NATIVE_BASELINE_COMPARISON_CLAIM_STATUS,
        "proposal_name": _NATIVE_BASELINE_COMPARISON_PROPOSAL_NAME,
        "schema_version": NATIVE_BASELINE_COMPARISON_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"native baseline comparison evidence {key} drift")
    comparisons = payload["comparisons"]
    if not isinstance(comparisons, list):
        raise ValueError("native baseline comparison entries drift")
    if len(comparisons) != len(scope_ids):
        raise ValueError("native baseline comparison count drift")
    observed_scope_ids = tuple(
        str(comparison["workload_scope_id"])
        for comparison in comparisons
        if isinstance(comparison, dict)
    )
    if observed_scope_ids != scope_ids:
        raise ValueError("native baseline comparison scope binding drift")
    for comparison in comparisons:
        if not isinstance(comparison, dict):
            raise ValueError("native baseline comparison entry drift")
        expected_fields = {
            "comparison_digest": "not_supplied",
            "comparison_metric_id": _NATIVE_BASELINE_COMPARISON_METRIC_ID,
            "result_status": "not_measured",
            "summary_policy_id": _NATIVE_BASELINE_COMPARISON_SUMMARY_POLICY_ID,
        }
        for key, value in expected_fields.items():
            if comparison.get(key) != value:
                raise ValueError(f"native baseline comparison {key} drift")
        for forbidden_key in (
            "host_path",
            "environment",
            "device_id",
            "hardware_serial",
            "raw_timing_samples",
        ):
            if forbidden_key in comparison:
                raise ValueError("native baseline comparison exposes forbidden data")
    return True


def _build_kernel_ingress_native_baseline_comparison_report(
    scope_ids: tuple[str, ...],
) -> NativeBaselineComparisonReport:
    return build_native_baseline_comparison_report(
        _NATIVE_BASELINE_COMPARISON_PROPOSAL_NAME,
        comparisons=tuple(
            NativeBaselineComparison(
                comparison_id=f"native_comparison_{scope_id}",
                workload_scope_id=scope_id,
                baseline_artifact_id=f"tuc_baseline_artifact_{scope_id}",
                native_artifact_id=f"native_baseline_artifact_{scope_id}",
                comparison_metric_id=_NATIVE_BASELINE_COMPARISON_METRIC_ID,
                summary_policy_id=_NATIVE_BASELINE_COMPARISON_SUMMARY_POLICY_ID,
                result_status="not_measured",
            )
            for scope_id in scope_ids
        ),
    )


def _has_versioned_toolchain_environment_evidence() -> bool:
    report = _build_versioned_toolchain_environment_report()
    payload = toolchain_environment_report_to_dict(report)
    expected = {
        "artifact_status": TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_claim_status": TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS,
        "proposal_name": _TOOLCHAIN_ENVIRONMENT_PROPOSAL_NAME,
        "schema_version": TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION,
        "toolchain_environment_ready": True,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"toolchain environment evidence {key} drift")
    components = payload["components"]
    if not isinstance(components, list):
        raise ValueError("toolchain environment components drift")
    if len(components) != len(_TOOLCHAIN_ENVIRONMENT_COMPONENT_FILES):
        raise ValueError("toolchain environment component count drift")
    for component, expected_component in zip(
        components,
        _TOOLCHAIN_ENVIRONMENT_COMPONENT_FILES,
        strict=True,
    ):
        if not isinstance(component, dict):
            raise ValueError("toolchain environment component drift")
        component_id, component_kind, version_id, provenance_id, path = expected_component
        expected_fields = {
            "component_id": component_id,
            "component_kind": component_kind,
            "version_id": version_id,
            "provenance_id": provenance_id,
            "component_digest": _repository_file_digest(path),
        }
        for key, value in expected_fields.items():
            if component.get(key) != value:
                raise ValueError(f"toolchain environment component {key} drift")
        for forbidden_key in ("host_path", "environment", "device_id", "hardware_serial"):
            if forbidden_key in component:
                raise ValueError("toolchain environment exposes forbidden host data")
    return True


def _build_versioned_toolchain_environment_report() -> ToolchainEnvironmentReport:
    return build_toolchain_environment_report(
        _TOOLCHAIN_ENVIRONMENT_PROPOSAL_NAME,
        components=tuple(
            ToolchainComponent(
                component_id=component_id,
                component_kind=component_kind,
                version_id=version_id,
                provenance_id=provenance_id,
                component_digest=_repository_file_digest(path),
            )
            for (
                component_id,
                component_kind,
                version_id,
                provenance_id,
                path,
            ) in _TOOLCHAIN_ENVIRONMENT_COMPONENT_FILES
        ),
    )


def _repository_file_digest(path: Path) -> str:
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("toolchain environment digest path must be repository relative")
    if not path.is_file():
        raise ValueError("toolchain environment digest path missing")
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _has_kernel_ingress_workload_scope_evidence() -> bool:
    report_text = build_kernel_ingress_workload_scope_report()
    report = json.loads(report_text)
    assert_kernel_ingress_workload_scope_report_contract(report)
    if report["workload_scope_ready"] is not True:
        raise ValueError("kernel ingress workload scope evidence is not ready")
    return True


def _has_kernel_ingress_planner_overhead_evidence() -> bool:
    measurement = measure_pipeline_planner_overhead(
        _build_kernel_ingress_mvp_graph(),
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    payload = planner_overhead_report_to_dict(measurement.report)
    expected = {
        "artifact_status": PLANNER_OVERHEAD_ARTIFACT_STATUS,
        "break_even_status": PLANNER_OVERHEAD_BREAK_EVEN_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "execution_time_status": PLANNER_OVERHEAD_EXECUTION_TIME_STATUS,
        "graph_name": _KERNEL_INGRESS_MVP_SOURCE_NAME,
        "issues": list(PLANNER_OVERHEAD_NOT_MEASURED_ISSUES),
        "native_performance_claim": False,
        "planner_overhead_hidden_in_execution_time": False,
        "schema_version": PLANNER_OVERHEAD_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"kernel ingress planner-overhead evidence {key} drift")
    phase_names = [phase["phase_name"] for phase in payload["phase_timings"]]
    if phase_names != list(PLANNER_OVERHEAD_PHASES):
        raise ValueError("kernel ingress planner-overhead phase order drift")
    return True


def _has_kernel_ingress_leaky_abstraction_evidence() -> bool:
    measurement = measure_pipeline_planner_overhead(
        _build_kernel_ingress_mvp_graph(),
        [
            LinearAlgebraSimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    report = build_leaky_abstraction_report(
        measurement.compilation.hac_ir,
        performance_facts=(
            LeakyAbstractionFact(
                fact_id="matmul_tile_shape",
                correct_home="backend_implementation",
                required_for_performance=True,
            ),
            LeakyAbstractionFact(
                fact_id="vector_lane_width",
                correct_home="backend_capability",
                required_for_performance=True,
            ),
            LeakyAbstractionFact(
                fact_id="transfer_latency_model",
                correct_home="runtime_plan",
                required_for_performance=True,
            ),
            LeakyAbstractionFact(
                fact_id="backend_sequence_choice",
                correct_home="compiler_decision_report",
                required_for_performance=True,
            ),
        ),
    )
    payload = leaky_abstraction_report_to_dict(report)
    expected = {
        "artifact_status": LEAKY_ABSTRACTION_ARTIFACT_STATUS,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "detected_leaks": [],
        "graph_name": _KERNEL_INGRESS_MVP_SOURCE_NAME,
        "hac_ir_contract_valid": True,
        "hac_ir_leak_detected": False,
        "issues": list(LEAKY_ABSTRACTION_DEFAULT_ISSUES),
        "native_performance_claim": False,
        "performance_claim_status": LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS,
        "schema_version": LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"kernel ingress leaky-abstraction {key} drift")
    facts = payload["performance_facts"]
    if not isinstance(facts, list) or len(facts) != 4:
        raise ValueError("kernel ingress leaky-abstraction fact drift")
    if any(fact.get("enters_hac_ir") is not False for fact in facts if isinstance(fact, dict)):
        raise ValueError("kernel ingress leaky-abstraction fact entered HAC-IR")
    return True


def _has_kernel_ingress_golden_digest_evidence(evidence_id: str) -> bool:
    digest_key = _KERNEL_INGRESS_DIGEST_EVIDENCE[evidence_id]
    report_text = build_kernel_ingress_report()
    report = json.loads(report_text)
    assert_kernel_ingress_report_contract(report)
    golden_text = _KERNEL_INGRESS_GOLDEN_PATH.read_text(encoding="utf-8")
    if report_text != golden_text:
        raise ValueError("kernel ingress golden report drift")
    cases = report["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("kernel ingress golden cases missing")
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("kernel ingress golden case drift")
        digest = case.get(digest_key)
        if not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise ValueError(f"kernel ingress {evidence_id} digest missing")
    return True


def _build_kernel_ingress_mvp_graph():
    ingress = ingest_triton_module_source_to_source_intent(
        REALISTIC_MVP_PIPELINE_MODULE_SOURCE,
        source_name=_KERNEL_INGRESS_MVP_SOURCE_NAME,
        kernel_name=_KERNEL_INGRESS_MVP_KERNEL_NAME,
        tensor_shapes=_KERNEL_INGRESS_MVP_TENSOR_SHAPES,
    )
    module = source_intent_from_mapping(ingress.parser_result.source_intent_payload)
    metadata = source_intent_to_triton_metadata(module)
    return metadata.to_compute_graph()


def _has_benchmark_report_schema_evidence() -> bool:
    schema = json.loads(_BASELINE_BENCHMARK_SCHEMA_PATH.read_text(encoding="utf-8"))
    if schema.get("$id") != (
        "https://github.com/kirchherr/TUC/"
        "schemas/baseline_benchmark_report.v0.schema.json"
    ):
        raise ValueError("benchmark report schema id drift")
    if schema.get("additionalProperties") is not False:
        raise ValueError("benchmark report schema must fail closed")
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("benchmark report schema properties drift")
    expected_constants = {
        "artifact_status": BENCHMARK_REPORT_ARTIFACT_STATUS,
        "claim_boundary": BENCHMARK_REPORT_CLAIM_BOUNDARY,
        "native_performance_claim": False,
        "schema_version": BENCHMARK_REPORT_SCHEMA_VERSION,
        "suite_version": BENCHMARK_SUITE_VERSION,
    }
    for key, expected in expected_constants.items():
        item = properties.get(key)
        if not isinstance(item, dict) or item.get("const") != expected:
            raise ValueError(f"benchmark report schema {key} drift")
    forbidden = {
        "backend_artifact",
        "device_identifier",
        "generated_code",
        "host_path",
        "plugin_entrypoint",
        "raw_timing_samples",
    }
    if any(fragment in json.dumps(schema, sort_keys=True) for fragment in forbidden):
        raise ValueError("benchmark report schema exposes forbidden evidence")
    return True


def _has_kernel_ingress_benchmark_methodology_evidence() -> bool:
    workload_report_text = build_kernel_ingress_workload_scope_report()
    workload_report = json.loads(workload_report_text)
    assert_kernel_ingress_workload_scope_report_contract(workload_report)
    scopes = workload_report["scopes"]
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("kernel ingress benchmark methodology scopes missing")
    scope_ids = tuple(
        str(scope["scope_id"]) for scope in scopes if isinstance(scope, dict)
    )
    if len(scope_ids) != len(scopes):
        raise ValueError("kernel ingress benchmark methodology scope drift")
    report = build_benchmark_methodology_report(
        "kernel_ingress_benchmark_methodology_candidate",
        methodologies=tuple(
            BenchmarkMethodology(
                methodology_id=f"methodology_{scope_id}",
                workload_scope_id=scope_id,
                measurement_clock="monotonic_ns",
                warmup_iterations=3,
                measurement_iterations=20,
                statistic_policy="min_median_mean",
                isolation_level="process_isolated",
                outlier_policy_id="no_raw_sample_storage",
                reproducibility_policy_id="docker_dev_container",
            )
            for scope_id in scope_ids
        ),
    )
    payload = benchmark_methodology_report_to_dict(report)
    expected = {
        "artifact_status": BENCHMARK_METHODOLOGY_ARTIFACT_STATUS,
        "benchmark_methodology_ready": True,
        "claim_boundary": PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
        "issues": ["native_performance_claim_blocked"],
        "native_performance_claim": False,
        "performance_claim_status": BENCHMARK_METHODOLOGY_CLAIM_STATUS,
        "proposal_name": "kernel_ingress_benchmark_methodology_candidate",
        "schema_version": BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION,
    }
    for key, value in expected.items():
        if payload[key] != value:
            raise ValueError(f"kernel ingress benchmark methodology {key} drift")
    methodologies = payload["methodologies"]
    if not isinstance(methodologies, list):
        raise ValueError("kernel ingress benchmark methodology entries drift")
    observed_scope_ids = tuple(
        str(methodology["workload_scope_id"])
        for methodology in methodologies
        if isinstance(methodology, dict)
    )
    if observed_scope_ids != scope_ids:
        raise ValueError("kernel ingress benchmark methodology scope binding drift")
    return True


if __name__ == "__main__":
    main()
