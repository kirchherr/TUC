"""Prove Source Intent through a no-fallback external package portfolio."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from tuc.backends.integration_package import (
    BACKEND_INTEGRATION_PACKAGE_CONTRACT,
    BackendIntegrationPackage,
    BackendIntegrationPackageReport,
    assert_backend_integration_package,
    dump_backend_integration_package_report,
    evaluate_backend_integration_package,
    load_backend_integration_package,
)
from tuc.compiler import CompilationResult, compile_graph
from tuc.frontend.source_intent import (
    SOURCE_INTENT_IR_CONTRACT,
    SourceIntentModule,
)
from tuc.frontend.source_intent_intake import (
    SOURCE_INTENT_SCHEMA_VERSION,
    source_intent_from_mapping,
)
from tuc.frontend.source_intent_metadata import (
    SOURCE_INTENT_METADATA_CONTRACT,
    SourceIntentMetadataReport,
    build_source_intent_metadata_report,
    source_intent_to_triton_metadata,
)
from tuc.frontend.source_intent_returns import source_intent_return_aliases
from tuc.ir.dialect import HAC_IR_DIALECT_VERSION
from tuc.ir.modules import IRStage
from tuc.runtime.backend_equivalence import (
    RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    RuntimeBackendEquivalenceReport,
    assert_runtime_backend_equivalence,
    build_runtime_backend_equivalence_report,
    dump_runtime_backend_equivalence_report,
)
from tuc.runtime.backend_package_execution import (
    BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
    build_backend_package_execution_admission_report,
)
from tuc.runtime.backend_package_execution_portfolio import (
    BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
    AdmittedBackendPackagePortfolioExecution,
    BackendPackageExecutionPortfolioReport,
    build_backend_package_execution_portfolio_admission,
    build_backend_package_execution_portfolio_report,
    dump_backend_package_execution_portfolio_report,
    execute_backend_package_execution_portfolio,
)
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    execute_graph,
)
from tuc.runtime.output_contract import (
    RUNTIME_OUTPUT_CONTRACT,
    RuntimeOutputContractReport,
    assert_runtime_output_contract,
    build_runtime_output_contract_report,
    dump_runtime_output_contract_report,
)
from tuc.runtime.public_output_bundle import (
    RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    RuntimePublicOutputBundle,
    assert_runtime_public_output_bundle,
    build_runtime_public_output_bundle,
    dump_runtime_public_output_bundle_report,
)
from tuc.runtime.reference_correctness import (
    RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    RuntimeReferenceCorrectnessReport,
    assert_runtime_reference_correctness,
    build_runtime_reference_correctness_report,
    dump_runtime_reference_correctness_report,
)

SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_SCHEMA_VERSION = (
    "tuc.source_intent_backend_package_portfolio_report.v0"
)
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_CONTRACT = (
    "source_intent_backend_package_portfolio.e2e.v0"
)
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_CLAIM = (
    "source_intent_reaches_no_fallback_external_package_execution_with_equivalent_outputs"
)
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_SOURCE_BOUNDARY = (
    "source_intent_plain_data_to_external_package_portfolio"
)
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_ARTIFACT_POLICY = (
    "digest_only_source_and_values_omitted"
)
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_STATUS = "PASS"
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_RAW_VALUE_POLICY = "omitted_by_policy"
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_CLAIMS = (
    "source_text_execution",
    "general_source_parser",
    "external_package_code_execution",
    "native_backend_execution",
    "physical_device_residency",
    "native_performance_parity",
)
SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_FORBIDDEN_FRAGMENTS = (
    '"backend_artifact":',
    '"command":',
    '"device_id":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"python_source":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    '"tensor_values":',
)

PACKAGE_DIRECTORY = Path(__file__).with_name("backend_packages")
SYSTOLIC_PACKAGE_PATH = PACKAGE_DIRECTORY / "external_systolic.v0.json"
VECTOR_PACKAGE_PATH = PACKAGE_DIRECTORY / "external_vector.v0.json"
EXPECTED_PACKAGE_DIGESTS = (
    "sha256:806813974dfde16b46f694566d751b18780d5e43d8455467bf4e5d7ea38b452c",
    "sha256:bf4bf333025a176f20ad927c249747f6ce923e14f224f4cd94ed769d893288ee",
)

FloatArray = NDArray[np.float64]

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_count",
        "artifact_policy",
        "artifacts",
        "backend_equivalence_contract",
        "backend_equivalence_passed",
        "backend_integration_contract",
        "blocked_claims",
        "blocked_execution_surfaces",
        "equivalence_comparison_metadata_digest",
        "external_package_code_executed",
        "external_plugin_execution",
        "fallback_assignment_count",
        "graph_name",
        "hac_ir_contract",
        "layout_conversion_count",
        "metadata_contract",
        "module_name",
        "operation_families",
        "output_contract",
        "package_admission_contract",
        "package_backend_sequence",
        "package_digests",
        "package_ids",
        "physical_device_execution",
        "portfolio_contract",
        "proof_claim",
        "proof_contract",
        "proof_status",
        "public_output_bundle_contract",
        "public_output_names",
        "raw_tensor_value_policy",
        "raw_tensor_values_serialized",
        "reference_correctness_contract",
        "reference_correctness_passed",
        "schema_version",
        "source_boundary",
        "source_intent_contract",
        "source_intent_payload_serialized",
        "source_text_executed",
        "terminal_output_names",
        "trusted_executor_registry",
        "trusted_executor_sequence",
    }
)
_ARTIFACT_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "status"}
)
_REQUIRED_ARTIFACTS = (
    ("source_intent_module", "text_dump", SOURCE_INTENT_IR_CONTRACT),
    ("source_intent_metadata", "text_report", SOURCE_INTENT_METADATA_CONTRACT),
    ("hac_ir", "text_dump", HAC_IR_DIALECT_VERSION),
    (
        "external_systolic_integration",
        "json_report",
        BACKEND_INTEGRATION_PACKAGE_CONTRACT,
    ),
    (
        "external_vector_integration",
        "json_report",
        BACKEND_INTEGRATION_PACKAGE_CONTRACT,
    ),
    (
        "package_portfolio_execution",
        "json_report",
        BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
    ),
    ("public_output_contract", "json_report", RUNTIME_OUTPUT_CONTRACT),
    (
        "public_output_bundle",
        "json_report",
        RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
    ),
    (
        "reference_correctness",
        "json_report",
        RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
    ),
    (
        "backend_equivalence",
        "json_report",
        RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
    ),
)


@dataclass(frozen=True)
class SourceIntentBackendPackagePortfolioEvidence:
    """Internal typed evidence retained while constructing the public proof."""

    module: SourceIntentModule
    metadata_report: SourceIntentMetadataReport
    compilation: CompilationResult
    packages: tuple[BackendIntegrationPackage, ...]
    integration_reports: tuple[BackendIntegrationPackageReport, ...]
    candidate: AdmittedBackendPackagePortfolioExecution
    portfolio_report: BackendPackageExecutionPortfolioReport
    output_contract: RuntimeOutputContractReport
    public_output_bundle: RuntimePublicOutputBundle
    reference_correctness: RuntimeReferenceCorrectnessReport
    backend_equivalence: RuntimeBackendEquivalenceReport


def build_source_intent_data() -> dict[str, object]:
    """Return bounded source-free compute intent for the vertical proof."""

    return {
        "name": "source_intent_backend_package_portfolio",
        "schema_version": SOURCE_INTENT_SCHEMA_VERSION,
        "tensors": [
            {"name": "lhs", "shape": [2, 2], "dtype": "float64"},
            {"name": "rhs", "shape": [2, 2], "dtype": "float64"},
            {"name": "projection", "shape": [2, 2], "dtype": "float64"},
            {"name": "activated", "shape": [2, 2], "dtype": "float64"},
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
                "name": "activation",
                "family": "elementwise",
                "inputs": ["projection"],
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


def proof_inputs() -> dict[str, FloatArray]:
    """Return deterministic finite inputs shared by all executions."""

    return {
        "lhs": np.array([[1.0, -2.0], [0.5, 3.0]], dtype=np.float64),
        "rhs": np.array([[2.0, 1.0], [-1.0, 0.25]], dtype=np.float64),
    }


def reference_outputs(inputs: dict[str, FloatArray]) -> dict[str, FloatArray]:
    """Return independent terminal semantics for the identity activation."""

    return {"activated": inputs["lhs"] @ inputs["rhs"]}


def run_evidence() -> SourceIntentBackendPackagePortfolioEvidence:
    """Run the complete execution-free-intake to trusted-runtime proof."""

    module = source_intent_from_mapping(build_source_intent_data())
    metadata_report = build_source_intent_metadata_report(module)
    graph = source_intent_to_triton_metadata(module).to_compute_graph()
    packages = tuple(
        load_backend_integration_package(path)
        for path in (SYSTOLIC_PACKAGE_PATH, VECTOR_PACKAGE_PATH)
    )
    integration_reports = tuple(
        evaluate_backend_integration_package(package) for package in packages
    )
    for integration_report in integration_reports:
        assert_backend_integration_package(integration_report)
    admissions = tuple(
        build_backend_package_execution_admission_report(report)
        for report in integration_reports
    )
    portfolio = build_backend_package_execution_portfolio_admission(admissions)
    compilation = compile_graph(
        graph,
        tuple(package.capability for package in packages),
    )
    inputs = proof_inputs()
    candidate = execute_backend_package_execution_portfolio(
        compilation.hac_ir.graph,
        compilation.partition_plan,
        inputs,
        portfolio,
    )
    baseline = compile_graph(graph, ())
    baseline_execution = execute_graph(
        baseline.hac_ir.graph,
        baseline.partition_plan,
        inputs,
    )
    backend_equivalence = assert_runtime_backend_equivalence(
        build_runtime_backend_equivalence_report(
            graph,
            baseline.partition_plan,
            baseline_execution,
            candidate.projected_partition_plan,
            candidate.execution,
            baseline_run_id="reference_cpu",
            candidate_run_id="source_intent_package_portfolio",
        )
    )
    portfolio_report = build_backend_package_execution_portfolio_report(
        graph,
        candidate,
        backend_equivalence,
    )
    output_contract = assert_runtime_output_contract(
        build_runtime_output_contract_report(
            graph,
            candidate.execution,
            source_intent_return_aliases(module),
        )
    )
    public_output_bundle = assert_runtime_public_output_bundle(
        build_runtime_public_output_bundle(candidate.execution, output_contract)
    )
    reference_correctness = assert_runtime_reference_correctness(
        build_runtime_reference_correctness_report(
            graph,
            candidate.execution,
            reference_outputs(inputs),
        )
    )
    return SourceIntentBackendPackagePortfolioEvidence(
        module=module,
        metadata_report=metadata_report,
        compilation=compilation,
        packages=packages,
        integration_reports=integration_reports,
        candidate=candidate,
        portfolio_report=portfolio_report,
        output_contract=output_contract,
        public_output_bundle=public_output_bundle,
        reference_correctness=reference_correctness,
        backend_equivalence=backend_equivalence,
    )


def build_source_intent_backend_package_portfolio_report() -> dict[str, object]:
    """Return digest-only evidence for the complete vertical proof."""

    evidence = run_evidence()
    artifact_texts = _artifact_texts(evidence)
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
    portfolio = evidence.portfolio_report
    report: dict[str, object] = {
        "artifact_count": len(artifacts),
        "artifact_policy": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_ARTIFACT_POLICY,
        "artifacts": artifacts,
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_passed": evidence.backend_equivalence.passed,
        "backend_integration_contract": BACKEND_INTEGRATION_PACKAGE_CONTRACT,
        "blocked_claims": list(
            SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_CLAIMS
        ),
        "blocked_execution_surfaces": list(
            RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ),
        "equivalence_comparison_metadata_digest": (
            evidence.backend_equivalence.comparison_metadata_digest
        ),
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "fallback_assignment_count": portfolio.fallback_assignment_count,
        "graph_name": evidence.compilation.hac_ir.graph.name,
        "hac_ir_contract": HAC_IR_DIALECT_VERSION,
        "layout_conversion_count": len(portfolio.layout_conversions),
        "metadata_contract": SOURCE_INTENT_METADATA_CONTRACT,
        "module_name": evidence.module.name,
        "operation_families": [
            operation.family for operation in evidence.module.operations
        ],
        "output_contract": RUNTIME_OUTPUT_CONTRACT,
        "package_admission_contract": BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
        "package_backend_sequence": list(portfolio.source_backend_sequence),
        "package_digests": [package.package_digest for package in evidence.packages],
        "package_ids": [package.package_id for package in evidence.packages],
        "physical_device_execution": False,
        "portfolio_contract": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
        "proof_claim": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_CLAIM,
        "proof_contract": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_CONTRACT,
        "proof_status": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_STATUS,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_names": list(evidence.public_output_bundle.public_output_names),
        "raw_tensor_value_policy": (
            SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_RAW_VALUE_POLICY
        ),
        "raw_tensor_values_serialized": False,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_passed": evidence.reference_correctness.passed,
        "schema_version": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_SCHEMA_VERSION,
        "source_boundary": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_SOURCE_BOUNDARY,
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "terminal_output_names": list(evidence.public_output_bundle.tensor_names),
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_executor_sequence": list(portfolio.projected_backend_sequence),
    }
    assert_source_intent_backend_package_portfolio_report(report)
    return report


def assert_source_intent_backend_package_portfolio_report(
    report: object,
) -> dict[str, object]:
    """Fail closed unless public evidence matches the accepted proof contract."""

    if not isinstance(report, dict):
        raise TypeError("source intent package portfolio report must be plain object")
    if frozenset(report) != _TOP_LEVEL_KEYS:
        raise ValueError("source intent package portfolio report key drift")
    expected: dict[str, object] = {
        "artifact_count": len(_REQUIRED_ARTIFACTS),
        "artifact_policy": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_ARTIFACT_POLICY,
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_passed": True,
        "backend_integration_contract": BACKEND_INTEGRATION_PACKAGE_CONTRACT,
        "blocked_claims": list(
            SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_CLAIMS
        ),
        "blocked_execution_surfaces": list(
            RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES
        ),
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "fallback_assignment_count": 0,
        "graph_name": "source_intent_backend_package_portfolio",
        "hac_ir_contract": HAC_IR_DIALECT_VERSION,
        "layout_conversion_count": 1,
        "metadata_contract": SOURCE_INTENT_METADATA_CONTRACT,
        "module_name": "source_intent_backend_package_portfolio",
        "operation_families": ["matmul", "elementwise"],
        "output_contract": RUNTIME_OUTPUT_CONTRACT,
        "package_admission_contract": BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
        "package_backend_sequence": ["external-systolic", "external-vector"],
        "package_ids": [
            "external-systolic-reference-package",
            "external-vector-reference-package",
        ],
        "physical_device_execution": False,
        "portfolio_contract": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
        "proof_claim": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_CLAIM,
        "proof_contract": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_CONTRACT,
        "proof_status": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_STATUS,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_names": ["api_activated"],
        "raw_tensor_value_policy": (
            SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_RAW_VALUE_POLICY
        ),
        "raw_tensor_values_serialized": False,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_passed": True,
        "schema_version": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_SCHEMA_VERSION,
        "source_boundary": SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_SOURCE_BOUNDARY,
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "source_intent_payload_serialized": False,
        "source_text_executed": False,
        "terminal_output_names": ["activated"],
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
    }
    for key, value in expected.items():
        if report[key] != value:
            raise ValueError(f"source intent package portfolio {key} drift")
    _assert_digest(report["equivalence_comparison_metadata_digest"])
    package_digests = report["package_digests"]
    if package_digests != list(EXPECTED_PACKAGE_DIGESTS):
        raise ValueError("source intent package portfolio package digest drift")
    artifacts = report["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(_REQUIRED_ARTIFACTS):
        raise ValueError("source intent package portfolio artifact count drift")
    for artifact, expected_artifact in zip(artifacts, _REQUIRED_ARTIFACTS, strict=True):
        _assert_artifact(artifact, expected_artifact)
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"))
    for fragment in SOURCE_INTENT_BACKEND_PACKAGE_PORTFOLIO_FORBIDDEN_FRAGMENTS:
        if fragment in encoded:
            raise ValueError(
                "source intent package portfolio contains forbidden evidence surface"
            )
    return report


def build_report() -> str:
    """Return stable JSON for the Source Intent package portfolio proof."""

    return json.dumps(
        build_source_intent_backend_package_portfolio_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def _artifact_texts(
    evidence: SourceIntentBackendPackagePortfolioEvidence,
) -> dict[str, str]:
    return {
        "source_intent_module": evidence.module.dump(),
        "source_intent_metadata": evidence.metadata_report.dump(),
        "hac_ir": evidence.compilation.dump(IRStage.HAC_IR),
        "external_systolic_integration": dump_backend_integration_package_report(
            evidence.integration_reports[0]
        ),
        "external_vector_integration": dump_backend_integration_package_report(
            evidence.integration_reports[1]
        ),
        "package_portfolio_execution": (
            dump_backend_package_execution_portfolio_report(
                evidence.portfolio_report
            )
        ),
        "public_output_contract": dump_runtime_output_contract_report(
            evidence.output_contract
        ),
        "public_output_bundle": dump_runtime_public_output_bundle_report(
            evidence.public_output_bundle
        ),
        "reference_correctness": dump_runtime_reference_correctness_report(
            evidence.reference_correctness
        ),
        "backend_equivalence": dump_runtime_backend_equivalence_report(
            evidence.backend_equivalence
        ),
    }


def _assert_artifact(
    artifact: object,
    expected: tuple[str, str, str],
) -> None:
    if not isinstance(artifact, Mapping) or frozenset(artifact) != _ARTIFACT_KEYS:
        raise ValueError("source intent package portfolio artifact shape drift")
    artifact_id, artifact_kind, contract = expected
    if artifact["artifact_id"] != artifact_id:
        raise ValueError("source intent package portfolio artifact id drift")
    if artifact["artifact_kind"] != artifact_kind:
        raise ValueError("source intent package portfolio artifact kind drift")
    if artifact["contract"] != contract or artifact["status"] != "accepted":
        raise ValueError("source intent package portfolio artifact contract drift")
    _assert_digest(artifact["digest"])


def _assert_digest(value: object) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError("source intent package portfolio digest drift")


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
