"""Bind Source Intent plain data to mixed-runtime public proof evidence."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

import numpy as np
from numpy.typing import NDArray

from tuc import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    RUNTIME_EXECUTOR_CONTRACT,
    RUNTIME_OUTPUT_CONTRACT,
    RUNTIME_OUTPUT_MANIFEST_CONTRACT,
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_METADATA_CONTRACT,
    SOURCE_INTENT_SCHEMA_VERSION,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    CompilationResult,
    ComputeGraph,
    RuntimeBackendEquivalenceReport,
    RuntimeExecutionReadinessReport,
    RuntimeExecutionResult,
    RuntimeOutputContractReport,
    RuntimeOutputManifestReport,
    RuntimePublicOutputBundle,
    RuntimeReferenceCorrectnessReport,
    SourceIntentModule,
    SystolicArraySimulatorBackend,
    VectorSimulatorBackend,
    assert_runtime_backend_equivalence,
    assert_runtime_output_contract,
    assert_runtime_output_manifest,
    assert_runtime_public_output_bundle,
    assert_runtime_reference_correctness,
    build_runtime_backend_equivalence_report,
    build_runtime_output_contract_report,
    build_runtime_output_manifest_report,
    build_runtime_public_output_bundle,
    build_runtime_reference_correctness_report,
    build_source_intent_metadata_report,
    compile_graph,
    dump_runtime_backend_equivalence_report,
    dump_runtime_output_contract_report,
    dump_runtime_output_manifest_report,
    dump_runtime_public_output_bundle_report,
    dump_runtime_reference_correctness_report,
    execute_graph,
    runtime_backend_equivalence_report_to_dict,
    runtime_execution_readiness_report,
    source_intent_from_mapping,
    source_intent_return_aliases,
    source_intent_to_triton_metadata,
)
from tuc.report_output import emit_public_json_report

FloatArray = NDArray[np.float64]

SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION = (
    "tuc.source_intent_mixed_runtime_public_proof_bundle_report.v0"
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT = (
    "source_intent_mixed_runtime_public_proof_bundle.e2e.v0"
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_ARTIFACT_POLICY = (
    "digest_only_values_omitted"
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_SOURCE_BOUNDARY = (
    "source_intent_plain_data_to_mixed_runtime_public_outputs"
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CLAIM = (
    "source_intent_preserves_public_outputs_across_mixed_backend_placements"
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BASELINE_RUN_ID = "reference_cpu"
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CANDIDATE_RUN_ID = (
    "source_intent_mixed_accelerators"
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BLOCKED_CLAIMS = (
    "general_source_parser",
    "real_triton_source_ingestion",
    "native_backend_execution",
    "native_performance_claim",
    "runtime_handle_serialization",
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REVIEW_CLAIMS = (
    "source_intent_plain_data_bound",
    "metadata_conversion_bound",
    "mixed_backend_placement_bound",
    "trusted_runtime_execution_bound",
    "public_output_bundle_bound",
    "reference_correctness_passed",
    "backend_equivalence_passed",
    "values_omitted",
)
SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"command":',
    '"device_id":',
    '"file_path":',
    '"generated_code":',
    '"host_path":',
    '"python_source":',
    '"raw_output_value":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"source_intent_payload":',
    '"source_text":',
    '"tensor_value":',
    '"tensor_values":',
    '"value":',
    '"values":',
    "tl.dot",
    "tl.store",
)

_SHA256_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_count",
        "artifact_policy",
        "artifacts",
        "backend_equivalence_contract",
        "backend_equivalence_passed",
        "baseline_backend_sequence",
        "baseline_run_id",
        "blocked_claims",
        "blocked_execution_surfaces",
        "bundle_contract",
        "candidate_backend_sequence",
        "candidate_run_id",
        "comparison_count",
        "equivalence_claim",
        "executor_contract",
        "graph_name",
        "metadata_contract",
        "module_name",
        "operation_families",
        "output_contract",
        "output_manifest_contract",
        "public_output_bundle_contract",
        "public_output_bundle_passed",
        "public_output_names",
        "raw_value_policy",
        "reference_correctness_contract",
        "reference_correctness_passed",
        "review_claims",
        "schema_version",
        "source_boundary",
        "source_intent_contract",
        "status",
        "terminal_outputs",
        "trusted_executor_registry",
        "trusted_runtime_backends",
    }
)
_ARTIFACT_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "status"}
)
_REQUIRED_ARTIFACTS = (
    ("source_intent_module", "text_dump", SOURCE_INTENT_IR_CONTRACT),
    ("source_intent_metadata", "text_report", SOURCE_INTENT_METADATA_CONTRACT),
    (
        "candidate_execution_readiness",
        "text_report",
        RUNTIME_EXECUTOR_CONTRACT,
    ),
    ("candidate_execution_trace", "text_trace", RUNTIME_EXECUTOR_CONTRACT),
    ("candidate_output_manifest", "json_report", RUNTIME_OUTPUT_MANIFEST_CONTRACT),
    ("candidate_output_contract", "json_report", RUNTIME_OUTPUT_CONTRACT),
    (
        "candidate_public_output_bundle",
        "json_report",
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    ),
    (
        "candidate_reference_correctness",
        "json_report",
        RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    ),
    (
        "runtime_backend_equivalence",
        "json_report",
        RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    ),
)
_EXPECTED_OPERATION_FAMILIES = ("matmul", "softmax", "reduction", "elementwise")
_EXPECTED_BASELINE_BACKEND_SEQUENCE = (
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
)
_EXPECTED_CANDIDATE_BACKEND_SEQUENCE = (
    "systolic-sim",
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
_EXPECTED_TRUSTED_RUNTIME_BACKENDS = (
    "reference-cpu",
    "systolic-sim",
    "vector-sim",
)


@dataclass(frozen=True)
class SourceIntentMixedRuntimePublicProofEvidence:
    """Concrete runtime evidence for the Source Intent mixed-placement proof."""

    module: SourceIntentModule
    graph: ComputeGraph
    baseline: CompilationResult
    candidate: CompilationResult
    candidate_readiness: RuntimeExecutionReadinessReport
    baseline_execution: RuntimeExecutionResult
    candidate_execution: RuntimeExecutionResult
    output_manifest: RuntimeOutputManifestReport
    output_contract: RuntimeOutputContractReport
    public_output_bundle: RuntimePublicOutputBundle
    reference_correctness: RuntimeReferenceCorrectnessReport
    backend_equivalence: RuntimeBackendEquivalenceReport


def build_source_intent_mixed_runtime_public_data() -> dict[str, object]:
    """Return JSON-like Source Intent data for the mixed-runtime proof."""

    return {
        "name": "source_intent_mixed_runtime_public_proof",
        "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
        "tensors": [
            {"name": "lhs", "shape": [2, 3]},
            {"name": "rhs", "shape": [3, 3]},
            {"name": "projection", "shape": [2, 3]},
            {"name": "normalized", "shape": [2, 3]},
            {"name": "row_sum", "shape": [2]},
            {"name": "activated", "shape": [2]},
        ],
        "operations": [
            {
                "name": "projection",
                "family": "matmul",
                "inputs": ["lhs", "rhs"],
                "outputs": ["projection"],
                "hints": {
                    "max_error_budget": 0.0,
                    "prefer_linear_accelerator": True,
                },
            },
            {
                "name": "normalize",
                "family": "softmax",
                "inputs": ["projection"],
                "outputs": ["normalized"],
                "attributes": {"axis": 1},
            },
            {
                "name": "sum_rows",
                "family": "reduction",
                "inputs": ["normalized"],
                "outputs": ["row_sum"],
                "attributes": {"axis": 1},
            },
            {
                "name": "stabilize",
                "family": "elementwise",
                "inputs": ["row_sum"],
                "outputs": ["activated"],
            },
        ],
        "returns": [
            {
                "public_name": "api_activated",
                "tensor_name": "activated",
                "required": True,
            }
        ],
    }


def runtime_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs for the proof graph."""

    return {
        "lhs": np.array(
            [[1.0, 2.0, -1.0], [0.5, -1.5, 3.0]],
            dtype=np.float64,
        ),
        "rhs": np.array(
            [[0.25, 1.0, -0.5], [2.0, -1.0, 0.75], [-1.5, 0.5, 1.25]],
            dtype=np.float64,
        ),
    }


def reference_outputs(inputs: dict[str, FloatArray]) -> dict[str, FloatArray]:
    """Return independent reference outputs for the terminal public tensor."""

    projection = inputs["lhs"] @ inputs["rhs"]
    shifted = projection - np.max(projection, axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    normalized = exponentials / np.sum(exponentials, axis=1, keepdims=True)
    row_sum = np.sum(normalized, axis=1)
    activated = row_sum
    return {"activated": activated}


def run_evidence() -> SourceIntentMixedRuntimePublicProofEvidence:
    """Compile, execute, and bind Source Intent to mixed-runtime proof evidence."""

    module = source_intent_from_mapping(
        build_source_intent_mixed_runtime_public_data()
    )
    metadata = source_intent_to_triton_metadata(module)
    graph = metadata.to_compute_graph()
    baseline = compile_graph(graph, [])
    candidate = compile_graph(
        graph,
        [
            SystolicArraySimulatorBackend().capability,
            VectorSimulatorBackend().capability,
        ],
    )
    inputs = runtime_inputs()
    candidate_readiness = runtime_execution_readiness_report(
        candidate.hac_ir.graph,
        candidate.partition_plan,
    )
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    candidate_execution = execute_graph(
        candidate.hac_ir.graph,
        candidate.partition_plan,
        inputs,
    )
    output_manifest = assert_runtime_output_manifest(
        build_runtime_output_manifest_report(
            candidate.hac_ir.graph,
            candidate_execution,
        )
    )
    output_contract = assert_runtime_output_contract(
        build_runtime_output_contract_report(
            candidate.hac_ir.graph,
            candidate_execution,
            source_intent_return_aliases(module),
        )
    )
    public_output_bundle = assert_runtime_public_output_bundle(
        build_runtime_public_output_bundle(candidate_execution, output_contract)
    )
    reference_correctness = assert_runtime_reference_correctness(
        build_runtime_reference_correctness_report(
            candidate.hac_ir.graph,
            candidate_execution,
            reference_outputs(inputs),
        )
    )
    backend_equivalence = assert_runtime_backend_equivalence(
        build_runtime_backend_equivalence_report(
            graph,
            baseline.partition_plan,
            baseline_execution,
            candidate.partition_plan,
            candidate_execution,
            baseline_run_id=(
                SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BASELINE_RUN_ID
            ),
            candidate_run_id=(
                SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CANDIDATE_RUN_ID
            ),
        )
    )
    return SourceIntentMixedRuntimePublicProofEvidence(
        module=module,
        graph=candidate.hac_ir.graph,
        baseline=baseline,
        candidate=candidate,
        candidate_readiness=candidate_readiness,
        baseline_execution=baseline_execution,
        candidate_execution=candidate_execution,
        output_manifest=output_manifest,
        output_contract=output_contract,
        public_output_bundle=public_output_bundle,
        reference_correctness=reference_correctness,
        backend_equivalence=backend_equivalence,
    )


def build_source_intent_mixed_runtime_public_proof_bundle_report() -> dict[str, object]:
    """Return digest-only Source Intent to mixed-runtime public proof evidence."""

    evidence = run_evidence()
    artifact_texts = _build_artifact_texts(evidence)
    _assert_artifact_payloads(evidence, artifact_texts)
    artifacts = [
        {
            "artifact_id": artifact_id,
            "artifact_kind": artifact_kind,
            "contract": contract,
            "digest": _digest(artifact_texts[artifact_id]),
            "status": "accepted",
        }
        for artifact_id, artifact_kind, contract in _REQUIRED_ARTIFACTS
    ]
    equivalence_report = runtime_backend_equivalence_report_to_dict(
        evidence.backend_equivalence
    )
    report: dict[str, object] = {
        "artifact_count": len(artifacts),
        "artifact_policy": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_ARTIFACT_POLICY
        ),
        "artifacts": artifacts,
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_passed": evidence.backend_equivalence.passed,
        "baseline_backend_sequence": list(_run_sequence(equivalence_report, 0)),
        "baseline_run_id": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BASELINE_RUN_ID
        ),
        "blocked_claims": list(
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BLOCKED_CLAIMS
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "bundle_contract": SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT,
        "candidate_backend_sequence": list(_run_sequence(equivalence_report, 1)),
        "candidate_run_id": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CANDIDATE_RUN_ID
        ),
        "comparison_count": int(equivalence_report["comparison_count"]),
        "equivalence_claim": SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CLAIM,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "graph_name": evidence.graph.name,
        "metadata_contract": SOURCE_INTENT_METADATA_CONTRACT,
        "module_name": evidence.module.name,
        "operation_families": [operation.family for operation in evidence.module.operations],
        "output_contract": RUNTIME_OUTPUT_CONTRACT,
        "output_manifest_contract": RUNTIME_OUTPUT_MANIFEST_CONTRACT,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_bundle_passed": evidence.public_output_bundle.passed,
        "public_output_names": list(evidence.public_output_bundle.public_output_names),
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_passed": evidence.reference_correctness.passed,
        "review_claims": list(
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REVIEW_CLAIMS
        ),
        "schema_version": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_SOURCE_BOUNDARY
        ),
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "status": "PASS",
        "terminal_outputs": list(evidence.public_output_bundle.tensor_names),
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_runtime_backends": list(_EXPECTED_TRUSTED_RUNTIME_BACKENDS),
    }
    assert_source_intent_mixed_runtime_public_proof_bundle_report_contract(report)
    return report


def build_report() -> str:
    """Return stable JSON evidence for the Source Intent mixed-runtime proof."""

    return json.dumps(
        build_source_intent_mixed_runtime_public_proof_bundle_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    emit_public_json_report(build_report())


def assert_source_intent_mixed_runtime_public_proof_bundle_report_contract(
    report: object,
) -> None:
    """Fail closed unless the Source Intent mixed-runtime proof matches v0."""

    if not isinstance(report, Mapping):
        raise ValueError("source intent mixed runtime proof bundle report must be object")
    _assert_exact_keys("top-level report", report, _TOP_LEVEL_KEYS)
    expected_values = {
        "artifact_count": len(_REQUIRED_ARTIFACTS),
        "artifact_policy": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_ARTIFACT_POLICY
        ),
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_passed": True,
        "baseline_backend_sequence": list(_EXPECTED_BASELINE_BACKEND_SEQUENCE),
        "baseline_run_id": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BASELINE_RUN_ID
        ),
        "blocked_claims": list(
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_BLOCKED_CLAIMS
        ),
        "blocked_execution_surfaces": list(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES),
        "bundle_contract": SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CONTRACT,
        "candidate_backend_sequence": list(_EXPECTED_CANDIDATE_BACKEND_SEQUENCE),
        "candidate_run_id": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CANDIDATE_RUN_ID
        ),
        "comparison_count": 1,
        "equivalence_claim": SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_CLAIM,
        "executor_contract": RUNTIME_EXECUTOR_CONTRACT,
        "graph_name": "source_intent_mixed_runtime_public_proof",
        "metadata_contract": SOURCE_INTENT_METADATA_CONTRACT,
        "module_name": "source_intent_mixed_runtime_public_proof",
        "operation_families": list(_EXPECTED_OPERATION_FAMILIES),
        "output_contract": RUNTIME_OUTPUT_CONTRACT,
        "output_manifest_contract": RUNTIME_OUTPUT_MANIFEST_CONTRACT,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_bundle_passed": True,
        "public_output_names": ["api_activated"],
        "raw_value_policy": RUNTIME_TENSOR_STORE_RAW_VALUE_STATUS,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_passed": True,
        "review_claims": list(
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REVIEW_CLAIMS
        ),
        "schema_version": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_REPORT_SCHEMA_VERSION
        ),
        "source_boundary": (
            SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_SOURCE_BOUNDARY
        ),
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "status": "PASS",
        "terminal_outputs": ["activated"],
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_runtime_backends": list(_EXPECTED_TRUSTED_RUNTIME_BACKENDS),
    }
    for key, expected in expected_values.items():
        if report[key] != expected:
            raise ValueError(f"source intent mixed runtime proof bundle {key} drift")
    artifacts = report["artifacts"]
    if not isinstance(artifacts, list):
        raise ValueError("source intent mixed runtime proof bundle artifacts drift")
    observed_ids = []
    for index, artifact in enumerate(artifacts):
        observed_ids.append(_assert_artifact_contract(index, artifact))
    if tuple(observed_ids) != tuple(artifact[0] for artifact in _REQUIRED_ARTIFACTS):
        raise ValueError(
            "source intent mixed runtime proof bundle artifact order drift"
        )
    _assert_report_is_metadata_only(report)


def _build_artifact_texts(
    evidence: SourceIntentMixedRuntimePublicProofEvidence,
) -> dict[str, str]:
    return {
        "source_intent_module": evidence.module.dump(),
        "source_intent_metadata": build_source_intent_metadata_report(
            evidence.module
        ).dump(),
        "candidate_execution_readiness": evidence.candidate_readiness.dump(),
        "candidate_execution_trace": evidence.candidate_execution.trace.dump(),
        "candidate_output_manifest": dump_runtime_output_manifest_report(
            evidence.output_manifest
        ),
        "candidate_output_contract": dump_runtime_output_contract_report(
            evidence.output_contract
        ),
        "candidate_public_output_bundle": dump_runtime_public_output_bundle_report(
            evidence.public_output_bundle
        ),
        "candidate_reference_correctness": dump_runtime_reference_correctness_report(
            evidence.reference_correctness
        ),
        "runtime_backend_equivalence": dump_runtime_backend_equivalence_report(
            evidence.backend_equivalence
        ),
    }


def _assert_artifact_payloads(
    evidence: SourceIntentMixedRuntimePublicProofEvidence,
    artifact_texts: Mapping[str, str],
) -> None:
    if tuple(artifact_texts) != tuple(artifact[0] for artifact in _REQUIRED_ARTIFACTS):
        raise ValueError("source intent mixed runtime proof bundle artifact drift")
    if not evidence.output_manifest.passed:
        raise ValueError("source intent mixed runtime proof bundle output manifest failed")
    if not evidence.output_contract.passed:
        raise ValueError("source intent mixed runtime proof bundle output contract failed")
    if not evidence.public_output_bundle.passed:
        raise ValueError("source intent mixed runtime proof bundle public bundle failed")
    if not evidence.reference_correctness.passed:
        raise ValueError(
            "source intent mixed runtime proof bundle reference correctness failed"
        )
    if not evidence.backend_equivalence.passed:
        raise ValueError(
            "source intent mixed runtime proof bundle backend equivalence failed"
        )
    for artifact_id, _, _ in _REQUIRED_ARTIFACTS:
        text = artifact_texts[artifact_id]
        if not isinstance(text, str) or not text:
            raise ValueError(
                "source intent mixed runtime proof bundle artifact payload drift"
            )
        _assert_text_is_metadata_only(text)


def _assert_artifact_contract(index: int, artifact: object) -> str:
    if not isinstance(artifact, Mapping):
        raise ValueError("source intent mixed runtime proof bundle artifact must be object")
    _assert_exact_keys("artifact", artifact, _ARTIFACT_KEYS)
    expected_id, expected_kind, expected_contract = _REQUIRED_ARTIFACTS[index]
    expected_values = {
        "artifact_id": expected_id,
        "artifact_kind": expected_kind,
        "contract": expected_contract,
        "status": "accepted",
    }
    for key, expected in expected_values.items():
        if artifact[key] != expected:
            raise ValueError(f"source intent mixed runtime proof bundle {key} drift")
    digest = artifact["digest"]
    if not isinstance(digest, str) or not _SHA256_DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("source intent mixed runtime proof bundle digest drift")
    return expected_id


def _run_sequence(report: Mapping[str, object], index: int) -> tuple[str, ...]:
    runs = report["runs"]
    if not isinstance(runs, list) or not isinstance(runs[index], Mapping):
        raise ValueError("source intent mixed runtime proof bundle run drift")
    sequence = runs[index]["planned_backend_sequence"]
    if not isinstance(sequence, list):
        raise ValueError("source intent mixed runtime proof bundle run sequence drift")
    return tuple(str(item) for item in sequence)


def _assert_exact_keys(
    context: str,
    payload: Mapping[object, object],
    expected: frozenset[str],
) -> None:
    if set(payload) != expected:
        raise ValueError(f"source intent mixed runtime proof bundle {context} drift")


def _assert_report_is_metadata_only(report: object) -> None:
    try:
        text = json.dumps(report, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError(
            "source intent mixed runtime proof bundle report is not JSON data"
        ) from exc
    _assert_text_is_metadata_only(text)


def _assert_text_is_metadata_only(text: str) -> None:
    for fragment in SOURCE_INTENT_MIXED_RUNTIME_PUBLIC_PROOF_BUNDLE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ValueError(
                "source intent mixed runtime proof bundle contains forbidden "
                "source, execution, or value material"
            )


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
