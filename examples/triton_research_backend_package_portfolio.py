"""Prove bounded Triton research source through an external package portfolio."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256

try:
    from examples.source_intent_backend_package_portfolio import (
        EXPECTED_PACKAGE_DIGESTS,
        SourceIntentBackendPackagePortfolioEvidence,
        artifact_texts_for_evidence,
        run_module_evidence,
    )
    from examples.source_to_intent_research_execution_bridge import (
        _inputs_for,
        _references_for,
    )
    from examples.source_to_intent_research_kernel_ingress import (
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from source_intent_backend_package_portfolio import (  # type: ignore[no-redef]
        EXPECTED_PACKAGE_DIGESTS,
        SourceIntentBackendPackagePortfolioEvidence,
        artifact_texts_for_evidence,
        run_module_evidence,
    )
    from source_to_intent_research_execution_bridge import (  # type: ignore[no-redef]
        _inputs_for,
        _references_for,
    )
    from source_to_intent_research_kernel_ingress import (  # type: ignore[no-redef]
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
    )

from tuc.backends.integration_package import BACKEND_INTEGRATION_PACKAGE_CONTRACT
from tuc.frontend import (
    SOURCE_INTENT_IR_CONTRACT,
    SOURCE_INTENT_METADATA_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
    SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
    SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
    SourceIntentModule,
    SourceToIntentResearchKernelIngressResult,
    dump_source_to_intent_research_kernel_ingress_report,
    ingest_triton_module_source_to_source_intent,
    source_intent_from_mapping,
    source_to_intent_research_parse_report_to_dict,
)
from tuc.ir.dialect import HAC_IR_DIALECT_VERSION
from tuc.runtime.backend_equivalence import RUNTIME_BACKEND_EQUIVALENCE_CONTRACT
from tuc.runtime.backend_package_execution import (
    BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
)
from tuc.runtime.backend_package_execution_portfolio import (
    BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
)
from tuc.runtime.executor import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
)
from tuc.runtime.output_contract import RUNTIME_OUTPUT_CONTRACT
from tuc.runtime.public_output_bundle import RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT
from tuc.runtime.reference_correctness import RUNTIME_REFERENCE_CORRECTNESS_CONTRACT

TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_SCHEMA_VERSION = (
    "tuc.triton_research_backend_package_portfolio_report.v0"
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_CONTRACT = (
    "triton_research_backend_package_portfolio.e2e.v0"
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_CLAIM = (
    "bounded_triton_research_source_reaches_no_fallback_external_package_execution"
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_SOURCE_BOUNDARY = (
    "bounded_triton_module_text_to_external_package_portfolio_research_only"
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_ARTIFACT_POLICY = (
    "digest_only_source_payloads_and_values_omitted"
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_CLAIMS = (
    "general_triton_source_ingestion",
    "production_parser",
    "production_source_ingestion_admission",
    "external_package_code_execution",
    "native_backend_execution",
    "physical_device_residency",
    "native_performance_parity",
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_EXECUTION_SURFACES = tuple(
    sorted(
        {
            *SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BLOCKED_EXECUTION_SURFACES,
            *RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
        }
    )
)
TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"backend_artifact":',
    '"command":',
    '"device_id":',
    '"generated_code":',
    '"host_path":',
    '"plugin_entrypoint":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    '"tensor_values":',
    "tl.dot",
    "tl.store",
)

SOURCE_NAME = "research_matmul_elementwise"
KERNEL_NAME = "matmul_elementwise"
TENSOR_SHAPES = {"a": (4, 8), "b": (8, 2), "y": (4, 2)}

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_count",
        "artifact_policy",
        "artifacts",
        "execution",
        "frontend",
        "packages",
        "planning",
        "proof_claim",
        "proof_contract",
        "proof_status",
        "schema_version",
        "security",
        "source",
    }
)
_ARTIFACT_KEYS = frozenset(
    {"artifact_id", "artifact_kind", "contract", "digest", "status"}
)
_REQUIRED_ARTIFACTS = (
    (
        "kernel_ingress",
        "json_report",
        SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
    ),
    ("research_parser", "json_report", SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT),
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
class TritonResearchBackendPackagePortfolioEvidence:
    """Internal typed evidence retained while constructing the public report."""

    ingress: SourceToIntentResearchKernelIngressResult
    module: SourceIntentModule
    portfolio: SourceIntentBackendPackagePortfolioEvidence


def run_evidence() -> TritonResearchBackendPackagePortfolioEvidence:
    """Run the bounded module source through the fixed package portfolio."""

    ingress = ingest_triton_module_source_to_source_intent(
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
        source_name=SOURCE_NAME,
        kernel_name=KERNEL_NAME,
        tensor_shapes=TENSOR_SHAPES,
    )
    module = source_intent_from_mapping(ingress.parser_result.source_intent_payload)
    inputs = _inputs_for(SOURCE_NAME)
    references = _references_for(SOURCE_NAME, inputs)
    portfolio = run_module_evidence(module, inputs, references)
    return TritonResearchBackendPackagePortfolioEvidence(
        ingress=ingress,
        module=module,
        portfolio=portfolio,
    )


def build_triton_research_backend_package_portfolio_report() -> dict[str, object]:
    """Return metadata-only evidence for the joined research source path."""

    evidence = run_evidence()
    ingress_report = evidence.ingress.report
    portfolio = evidence.portfolio
    portfolio_report = portfolio.portfolio_report
    texts = _artifact_texts(evidence)
    artifacts = [
        {
            "artifact_id": artifact_id,
            "artifact_kind": artifact_kind,
            "contract": contract,
            "digest": _digest(texts[artifact_id]),
            "status": "accepted",
        }
        for artifact_id, artifact_kind, contract in _REQUIRED_ARTIFACTS
    ]
    report: dict[str, object] = {
        "artifact_count": len(artifacts),
        "artifact_policy": (
            TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_ARTIFACT_POLICY
        ),
        "artifacts": artifacts,
        "execution": {
            "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
            "backend_equivalence_passed": portfolio.backend_equivalence.passed,
            "equivalence_comparison_metadata_digest": (
                portfolio.backend_equivalence.comparison_metadata_digest
            ),
            "physical_device_execution": False,
            "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
            "public_output_names": list(
                portfolio.public_output_bundle.public_output_names
            ),
            "raw_tensor_values_serialized": False,
            "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
            "reference_correctness_passed": portfolio.reference_correctness.passed,
            "terminal_output_names": list(
                portfolio.public_output_bundle.tensor_names
            ),
            "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
        },
        "frontend": {
            "default_parser_status": ingress_report.default_parser_status,
            "ingress_contract": ingress_report.ingress_contract,
            "operation_families": list(ingress_report.operation_families),
            "parser_contract": SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
            "parser_status": ingress_report.parser_status,
            "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
            "source_intent_digest": ingress_report.source_intent_digest,
            "source_intent_payload_serialized": False,
        },
        "packages": {
            "external_package_code_executed": False,
            "external_plugin_execution": False,
            "integration_contract": BACKEND_INTEGRATION_PACKAGE_CONTRACT,
            "package_digests": [
                package.package_digest for package in portfolio.packages
            ],
            "package_ids": [package.package_id for package in portfolio.packages],
        },
        "planning": {
            "fallback_assignment_count": (
                portfolio_report.fallback_assignment_count
            ),
            "hac_ir_contract": HAC_IR_DIALECT_VERSION,
            "layout_conversion_count": len(portfolio_report.layout_conversions),
            "package_admission_contract": (
                BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT
            ),
            "package_backend_sequence": list(
                portfolio_report.source_backend_sequence
            ),
            "portfolio_contract": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
            "trusted_executor_sequence": list(
                portfolio_report.projected_backend_sequence
            ),
        },
        "proof_claim": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_CLAIM,
        "proof_contract": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_CONTRACT,
        "proof_status": "PASS",
        "schema_version": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_SCHEMA_VERSION,
        "security": {
            "blocked_claims": list(
                TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_CLAIMS
            ),
            "blocked_execution_surfaces": list(
                TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_EXECUTION_SURFACES
            ),
            "production_source_ingestion_admitted": False,
        },
        "source": {
            "decorator_evaluated": False,
            "extracted_kernel_digest": ingress_report.extracted_kernel_digest,
            "import_count": ingress_report.import_count,
            "jit_executed": False,
            "kernel_name": ingress_report.kernel_name,
            "module_ast_depth": ingress_report.module_ast_depth,
            "module_ast_node_count": ingress_report.module_ast_node_count,
            "module_bytes": ingress_report.module_bytes,
            "module_digest": ingress_report.module_digest,
            "module_imports_executed": False,
            "module_line_count": ingress_report.module_line_count,
            "source_boundary": (
                TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_SOURCE_BOUNDARY
            ),
            "source_name": ingress_report.source_name,
            "source_text_executed": False,
            "source_text_serialized": False,
        },
    }
    assert_triton_research_backend_package_portfolio_report(report)
    return report


def assert_triton_research_backend_package_portfolio_report(
    report: object,
) -> dict[str, object]:
    """Fail closed unless the report matches the accepted research slice."""

    if not isinstance(report, dict):
        raise TypeError("Triton research package portfolio report must be plain object")
    if frozenset(report) != _TOP_LEVEL_KEYS:
        raise ValueError("Triton research package portfolio top-level drift")
    expected_top_level = {
        "artifact_count": len(_REQUIRED_ARTIFACTS),
        "artifact_policy": (
            TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_ARTIFACT_POLICY
        ),
        "proof_claim": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_CLAIM,
        "proof_contract": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_CONTRACT,
        "proof_status": "PASS",
        "schema_version": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_SCHEMA_VERSION,
    }
    for key, expected in expected_top_level.items():
        if report[key] != expected:
            raise ValueError(f"Triton research package portfolio {key} drift")
    _assert_source(report["source"])
    _assert_frontend(report["frontend"])
    _assert_packages(report["packages"])
    _assert_planning(report["planning"])
    _assert_execution(report["execution"])
    _assert_security(report["security"])
    artifacts = report["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) != len(_REQUIRED_ARTIFACTS):
        raise ValueError("Triton research package portfolio artifact count drift")
    for artifact, expected in zip(artifacts, _REQUIRED_ARTIFACTS, strict=True):
        _assert_artifact(artifact, expected)
    encoded = _canonical_json(report)
    for fragment in TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_FORBIDDEN_FRAGMENTS:
        if fragment in encoded:
            raise ValueError(
                "Triton research package portfolio contains forbidden material"
            )
    return report


def build_report() -> str:
    """Return stable JSON for the bounded Triton research proof."""

    return json.dumps(
        build_triton_research_backend_package_portfolio_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def main() -> None:
    print(build_report(), end="")


def _artifact_texts(
    evidence: TritonResearchBackendPackagePortfolioEvidence,
) -> dict[str, str]:
    parser_report = source_to_intent_research_parse_report_to_dict(
        evidence.ingress.parser_result.report
    )
    return {
        "kernel_ingress": dump_source_to_intent_research_kernel_ingress_report(
            evidence.ingress.report
        ),
        "research_parser": json.dumps(
            parser_report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        **artifact_texts_for_evidence(evidence.portfolio),
    }


def _assert_source(value: object) -> None:
    expected = {
        "decorator_evaluated": False,
        "extracted_kernel_digest": (
            "sha256:ad113b078fe24fcd871fbfb3f95b03e6192dbad3e607bbb737a9e09aa92f9bad"
        ),
        "import_count": 2,
        "jit_executed": False,
        "kernel_name": KERNEL_NAME,
        "module_ast_depth": 7,
        "module_ast_node_count": 52,
        "module_bytes": 206,
        "module_digest": (
            "sha256:eb599f41b7abee29e06c0842db8ba43fc8e8b710f668532a767c31fd81d7f7a0"
        ),
        "module_imports_executed": False,
        "module_line_count": 8,
        "source_boundary": TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_SOURCE_BOUNDARY,
        "source_name": SOURCE_NAME,
        "source_text_executed": False,
        "source_text_serialized": False,
    }
    _assert_exact_object("source", value, expected)


def _assert_frontend(value: object) -> None:
    expected = {
        "default_parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_DEFAULT_STATUS,
        "ingress_contract": SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_CONTRACT,
        "operation_families": ["elementwise", "matmul"],
        "parser_contract": SOURCE_TO_INTENT_RESEARCH_PARSER_CONTRACT,
        "parser_status": SOURCE_TO_INTENT_RESEARCH_PARSER_STATUS,
        "source_intent_contract": SOURCE_INTENT_IR_CONTRACT,
        "source_intent_digest": (
            "sha256:20b83d9aebaf4b231ccb37c55171faef3ce258efb6fb0d8df422108fe1a7bb4f"
        ),
        "source_intent_payload_serialized": False,
    }
    _assert_exact_object("frontend", value, expected)


def _assert_packages(value: object) -> None:
    expected = {
        "external_package_code_executed": False,
        "external_plugin_execution": False,
        "integration_contract": BACKEND_INTEGRATION_PACKAGE_CONTRACT,
        "package_digests": list(EXPECTED_PACKAGE_DIGESTS),
        "package_ids": [
            "external-systolic-reference-package",
            "external-vector-reference-package",
        ],
    }
    _assert_exact_object("packages", value, expected)


def _assert_planning(value: object) -> None:
    expected = {
        "fallback_assignment_count": 0,
        "hac_ir_contract": HAC_IR_DIALECT_VERSION,
        "layout_conversion_count": 1,
        "package_admission_contract": BACKEND_PACKAGE_EXECUTION_ADMISSION_CONTRACT,
        "package_backend_sequence": ["external-systolic", "external-vector"],
        "portfolio_contract": BACKEND_PACKAGE_EXECUTION_PORTFOLIO_CONTRACT,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
    }
    _assert_exact_object("planning", value, expected)


def _assert_execution(value: object) -> None:
    if not isinstance(value, dict):
        raise TypeError("Triton research package portfolio execution must be object")
    expected = {
        "backend_equivalence_contract": RUNTIME_BACKEND_EQUIVALENCE_CONTRACT,
        "backend_equivalence_passed": True,
        "physical_device_execution": False,
        "public_output_bundle_contract": RUNTIME_PUBLIC_OUTPUT_BUNDLE_CONTRACT,
        "public_output_names": ["y"],
        "raw_tensor_values_serialized": False,
        "reference_correctness_contract": RUNTIME_REFERENCE_CORRECTNESS_CONTRACT,
        "reference_correctness_passed": True,
        "terminal_output_names": ["activated"],
        "trusted_executor_registry": TRUSTED_RUNTIME_EXECUTOR_REGISTRY,
    }
    if frozenset(value) != frozenset(
        {*expected, "equivalence_comparison_metadata_digest"}
    ):
        raise ValueError("Triton research package portfolio execution key drift")
    for key, expected_value in expected.items():
        if value[key] != expected_value:
            raise ValueError(
                f"Triton research package portfolio execution {key} drift"
            )
    _assert_digest(value["equivalence_comparison_metadata_digest"])


def _assert_security(value: object) -> None:
    expected = {
        "blocked_claims": list(
            TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_CLAIMS
        ),
        "blocked_execution_surfaces": list(
            TRITON_RESEARCH_BACKEND_PACKAGE_PORTFOLIO_BLOCKED_EXECUTION_SURFACES
        ),
        "production_source_ingestion_admitted": False,
    }
    _assert_exact_object("security", value, expected)


def _assert_exact_object(
    label: str,
    value: object,
    expected: Mapping[str, object],
) -> None:
    if not isinstance(value, dict) or value != expected:
        raise ValueError(f"Triton research package portfolio {label} drift")


def _assert_artifact(
    artifact: object,
    expected: tuple[str, str, str],
) -> None:
    if not isinstance(artifact, Mapping) or frozenset(artifact) != _ARTIFACT_KEYS:
        raise ValueError("Triton research package portfolio artifact shape drift")
    artifact_id, artifact_kind, contract = expected
    if artifact["artifact_id"] != artifact_id:
        raise ValueError("Triton research package portfolio artifact id drift")
    if artifact["artifact_kind"] != artifact_kind:
        raise ValueError("Triton research package portfolio artifact kind drift")
    if artifact["contract"] != contract or artifact["status"] != "accepted":
        raise ValueError("Triton research package portfolio artifact contract drift")
    _assert_digest(artifact["digest"])


def _assert_digest(value: object) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError("Triton research package portfolio digest drift")


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Triton research package portfolio must be JSON data") from exc


def _digest(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()
