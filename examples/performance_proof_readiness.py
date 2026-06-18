"""Emit performance-proof readiness evidence for review."""

from __future__ import annotations

import json
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
    PERFORMANCE_PROOF_BOUNDARY_CONTRACT,
    PerformanceProofReadinessEvidence,
    build_performance_proof_readiness_report,
    dump_performance_proof_readiness_report,
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
    )


def main() -> None:
    report = build_performance_proof_readiness_report(
        "blocked-native-performance-proof-proposal",
        build_blocked_performance_proof_evidence(),
    )
    print(dump_performance_proof_readiness_report(report), end="")


def _has_kernel_ingress_workload_scope_evidence() -> bool:
    report_text = build_kernel_ingress_workload_scope_report()
    report = json.loads(report_text)
    assert_kernel_ingress_workload_scope_report_contract(report)
    if report["workload_scope_ready"] is not True:
        raise ValueError("kernel ingress workload scope evidence is not ready")
    return True


def _has_kernel_ingress_planner_overhead_evidence() -> bool:
    ingress = ingest_triton_module_source_to_source_intent(
        REALISTIC_MVP_PIPELINE_MODULE_SOURCE,
        source_name=_KERNEL_INGRESS_MVP_SOURCE_NAME,
        kernel_name=_KERNEL_INGRESS_MVP_KERNEL_NAME,
        tensor_shapes=_KERNEL_INGRESS_MVP_TENSOR_SHAPES,
    )
    module = source_intent_from_mapping(ingress.parser_result.source_intent_payload)
    metadata = source_intent_to_triton_metadata(module)
    graph = metadata.to_compute_graph()
    measurement = measure_pipeline_planner_overhead(
        graph,
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


if __name__ == "__main__":
    main()
