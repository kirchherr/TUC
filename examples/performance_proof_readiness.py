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
    BENCHMARK_METHODOLOGY_ARTIFACT_STATUS,
    BENCHMARK_METHODOLOGY_CLAIM_STATUS,
    BENCHMARK_METHODOLOGY_REPORT_SCHEMA_VERSION,
    LEAKY_ABSTRACTION_ARTIFACT_STATUS,
    LEAKY_ABSTRACTION_DEFAULT_ISSUES,
    LEAKY_ABSTRACTION_PERFORMANCE_CLAIM_STATUS,
    LEAKY_ABSTRACTION_REPORT_SCHEMA_VERSION,
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
    TOOLCHAIN_ENVIRONMENT_ARTIFACT_STATUS,
    TOOLCHAIN_ENVIRONMENT_CLAIM_STATUS,
    TOOLCHAIN_ENVIRONMENT_REPORT_SCHEMA_VERSION,
    BenchmarkMethodology,
    LeakyAbstractionFact,
    PerformanceProofReadinessEvidence,
    ToolchainComponent,
    ToolchainEnvironmentReport,
    benchmark_methodology_report_to_dict,
    build_benchmark_methodology_report,
    build_leaky_abstraction_report,
    build_performance_proof_readiness_report,
    build_toolchain_environment_report,
    dump_performance_proof_readiness_report,
    leaky_abstraction_report_to_dict,
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


def build_blocked_performance_proof_evidence() -> (
    tuple[PerformanceProofReadinessEvidence, ...]
):
    """Return the current intentionally blocked performance-proof evidence set."""

    return (
        PerformanceProofReadinessEvidence(
            evidence_id="workload_scope",
            present=_has_kernel_ingress_workload_scope_evidence(),
        ),
        PerformanceProofReadinessEvidence(
            evidence_id="planner_overhead_report",
            present=_has_kernel_ingress_planner_overhead_evidence(),
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
            evidence_id="benchmark_methodology",
            present=_has_kernel_ingress_benchmark_methodology_evidence(),
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
        "blocked-native-performance-proof-proposal",
        build_blocked_performance_proof_evidence(),
    )
    print(dump_performance_proof_readiness_report(report), end="")


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
    scope_ids = tuple(str(scope["scope_id"]) for scope in scopes if isinstance(scope, dict))
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
