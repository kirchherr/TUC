"""Prove isolated research source ingestion through trusted package execution."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256

try:
    from examples.source_intent_backend_package_portfolio import (
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

from tuc.frontend import (
    ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT,
    ISOLATED_SOURCE_INGESTION_BLOCKED_EXECUTION_SURFACES,
    ISOLATED_SOURCE_INGESTION_CONTRACT,
    ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS,
    ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS,
    ISOLATED_SOURCE_INGESTION_STATUS,
    ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL,
    ingest_isolated_triton_module_source,
    isolated_source_ingestion_report_to_dict,
)

ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_SCHEMA_VERSION = (
    "tuc.isolated_source_ingestion_research_proof_report.v0"
)
ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CONTRACT = (
    "isolated_source_ingestion_research_proof.e2e.v0"
)
ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CLAIM = (
    "bounded_source_reaches_equivalent_trusted_package_execution_through_fixed_worker"
)
ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_STATUS = "PASS"
ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_ARTIFACT_POLICY = (
    "metadata_digest_only_source_and_values_omitted"
)
ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_BLOCKED_CLAIMS = (
    "general_triton_parser",
    "kernel_network_isolation",
    "native_backend_execution",
    "native_performance_parity",
    "production_source_ingestion",
    "production_source_sandbox",
)
_SOURCE_NAME = "research_matmul_elementwise"
_KERNEL_NAME = "matmul_elementwise"
_TENSOR_SHAPES = {"a": (4, 8), "b": (8, 2), "y": (4, 2)}
_ARTIFACT_IDS = (
    "source_intent_module",
    "source_intent_metadata",
    "hac_ir",
    "external_systolic_integration",
    "external_vector_integration",
    "package_portfolio_execution",
    "public_output_contract",
    "public_output_bundle",
    "reference_correctness",
    "backend_equivalence",
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "admission_effect",
        "artifact_digests",
        "artifact_policy",
        "backend_equivalence_passed",
        "blocked_claims",
        "direct_source_ingestion",
        "enforced_controls",
        "equivalence_comparison_metadata_digest",
        "explicit_non_claims",
        "external_package_code_executed",
        "filesystem_namespace_isolation",
        "fixed_worker_process_executed",
        "issues",
        "kernel_name",
        "kernel_network_isolation",
        "operation_families",
        "package_backend_sequence",
        "package_ids",
        "production_source_ingestion",
        "proof_claim",
        "proof_contract",
        "proof_status",
        "public_output_bundle_metadata_digest",
        "public_output_names",
        "raw_source_serialized",
        "raw_tensor_values_serialized",
        "reference_correctness_passed",
        "report_digest",
        "research_source_to_intent_plain_data",
        "schema_version",
        "source_intent_digest",
        "source_intent_payload_serialized",
        "source_name",
        "source_text_executed",
        "trusted_executor_sequence",
        "user_selected_subprocess_executed",
        "worker_contract",
        "worker_protocol",
        "worker_report_digest",
        "worker_status",
    }
)
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"command":',
    '"file_path":',
    '"host_path":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"source_intent_payload":',
    '"source_text":',
    '"tensor_values":',
)


def build_isolated_source_ingestion_research_proof_report() -> dict[str, object]:
    """Run the fixed worker and complete the no-fallback vertical proof."""

    isolated = ingest_isolated_triton_module_source(
        REALISTIC_MATMUL_ELEMENTWISE_MODULE_SOURCE,
        source_name=_SOURCE_NAME,
        kernel_name=_KERNEL_NAME,
        tensor_shapes=_TENSOR_SHAPES,
    )
    inputs = _inputs_for(_SOURCE_NAME)
    evidence = run_module_evidence(
        isolated.module,
        inputs,
        _references_for(_SOURCE_NAME, inputs),
    )
    artifact_texts = artifact_texts_for_evidence(evidence)
    worker_report = isolated_source_ingestion_report_to_dict(isolated.report)
    report: dict[str, object] = {
        "admission_effect": ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT,
        "artifact_digests": [
            {"artifact_id": artifact_id, "digest": _digest_text(artifact_texts[artifact_id])}
            for artifact_id in _ARTIFACT_IDS
        ],
        "artifact_policy": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_ARTIFACT_POLICY,
        "backend_equivalence_passed": evidence.backend_equivalence.passed,
        "blocked_claims": list(
            ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_BLOCKED_CLAIMS
        ),
        "direct_source_ingestion": False,
        "enforced_controls": list(ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS),
        "equivalence_comparison_metadata_digest": (
            evidence.backend_equivalence.comparison_metadata_digest
        ),
        "explicit_non_claims": list(ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS),
        "external_package_code_executed": False,
        "filesystem_namespace_isolation": False,
        "fixed_worker_process_executed": True,
        "issues": [],
        "kernel_name": isolated.report.kernel_name,
        "kernel_network_isolation": False,
        "operation_families": list(isolated.report.operation_families),
        "package_backend_sequence": list(
            evidence.portfolio_report.source_backend_sequence
        ),
        "package_ids": [package.package_id for package in evidence.packages],
        "production_source_ingestion": False,
        "proof_claim": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CLAIM,
        "proof_contract": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CONTRACT,
        "proof_status": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_STATUS,
        "public_output_bundle_metadata_digest": (
            evidence.public_output_bundle.bundle_metadata_digest
        ),
        "public_output_names": list(evidence.public_output_bundle.public_output_names),
        "raw_source_serialized": False,
        "raw_tensor_values_serialized": False,
        "reference_correctness_passed": evidence.reference_correctness.passed,
        "research_source_to_intent_plain_data": True,
        "schema_version": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_SCHEMA_VERSION,
        "source_intent_digest": isolated.report.source_intent_digest,
        "source_intent_payload_serialized": False,
        "source_name": isolated.report.source_name,
        "source_text_executed": False,
        "trusted_executor_sequence": list(
            evidence.portfolio_report.projected_backend_sequence
        ),
        "user_selected_subprocess_executed": False,
        "worker_contract": ISOLATED_SOURCE_INGESTION_CONTRACT,
        "worker_protocol": ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL,
        "worker_report_digest": _digest_payload(worker_report),
        "worker_status": ISOLATED_SOURCE_INGESTION_STATUS,
    }
    report["report_digest"] = _digest_payload(report)
    return assert_isolated_source_ingestion_research_proof_report(report)


def assert_isolated_source_ingestion_research_proof_report(
    report: object,
) -> dict[str, object]:
    """Fail closed on claim, evidence, isolation, or serialization drift."""

    if type(report) is not dict:
        raise TypeError("isolated source ingestion proof report must be plain object")
    typed = dict(cast_mapping(report))
    if frozenset(typed) != _TOP_LEVEL_KEYS:
        raise ValueError("isolated source ingestion proof key drift")
    expected: dict[str, object] = {
        "admission_effect": ISOLATED_SOURCE_INGESTION_ADMISSION_EFFECT,
        "artifact_policy": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_ARTIFACT_POLICY,
        "backend_equivalence_passed": True,
        "blocked_claims": list(
            ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_BLOCKED_CLAIMS
        ),
        "direct_source_ingestion": False,
        "enforced_controls": list(ISOLATED_SOURCE_INGESTION_ENFORCED_CONTROLS),
        "explicit_non_claims": list(ISOLATED_SOURCE_INGESTION_EXPLICIT_NON_CLAIMS),
        "external_package_code_executed": False,
        "filesystem_namespace_isolation": False,
        "fixed_worker_process_executed": True,
        "issues": [],
        "kernel_name": _KERNEL_NAME,
        "kernel_network_isolation": False,
        "operation_families": ["elementwise", "matmul"],
        "package_backend_sequence": ["external-systolic", "external-vector"],
        "package_ids": [
            "external-systolic-reference-package",
            "external-vector-reference-package",
        ],
        "production_source_ingestion": False,
        "proof_claim": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CLAIM,
        "proof_contract": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_CONTRACT,
        "proof_status": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_STATUS,
        "public_output_names": ["y"],
        "raw_source_serialized": False,
        "raw_tensor_values_serialized": False,
        "reference_correctness_passed": True,
        "research_source_to_intent_plain_data": True,
        "schema_version": ISOLATED_SOURCE_INGESTION_RESEARCH_PROOF_SCHEMA_VERSION,
        "source_intent_payload_serialized": False,
        "source_name": _SOURCE_NAME,
        "source_text_executed": False,
        "trusted_executor_sequence": ["systolic-sim", "vector-sim"],
        "user_selected_subprocess_executed": False,
        "worker_contract": ISOLATED_SOURCE_INGESTION_CONTRACT,
        "worker_protocol": ISOLATED_SOURCE_INGESTION_WORKER_PROTOCOL,
        "worker_status": ISOLATED_SOURCE_INGESTION_STATUS,
    }
    for key, expected_value in expected.items():
        if typed[key] != expected_value:
            raise ValueError(f"isolated source ingestion proof {key} drift")
    for key in (
        "equivalence_comparison_metadata_digest",
        "public_output_bundle_metadata_digest",
        "report_digest",
        "source_intent_digest",
        "worker_report_digest",
    ):
        _assert_digest(typed[key], key)
    artifacts = typed["artifact_digests"]
    if type(artifacts) is not list or len(artifacts) != len(_ARTIFACT_IDS):
        raise ValueError("isolated source ingestion proof artifact count drift")
    for artifact, expected_id in zip(artifacts, _ARTIFACT_IDS, strict=True):
        if type(artifact) is not dict or set(artifact) != {"artifact_id", "digest"}:
            raise ValueError("isolated source ingestion proof artifact shape drift")
        if artifact["artifact_id"] != expected_id:
            raise ValueError("isolated source ingestion proof artifact order drift")
        _assert_digest(artifact["digest"], "artifact digest")
    without_digest = dict(typed)
    del without_digest["report_digest"]
    if typed["report_digest"] != _digest_payload(without_digest):
        raise ValueError("isolated source ingestion proof report digest drift")
    encoded = _canonical_json(typed).lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in encoded:
            raise ValueError("isolated source ingestion proof leaks source or values")
    if list(ISOLATED_SOURCE_INGESTION_BLOCKED_EXECUTION_SURFACES) == []:
        raise ValueError("isolated source ingestion proof blocked surfaces missing")
    return typed


def build_report() -> str:
    """Return deterministic metadata-only JSON evidence."""

    return json.dumps(
        build_isolated_source_ingestion_research_proof_report(),
        indent=2,
        sort_keys=True,
    ) + "\n"


def cast_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("isolated source ingestion proof must be mapping")
    return value


def _assert_digest(value: object, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ValueError(f"isolated source ingestion proof {label} invalid")


def _digest_payload(payload: object) -> str:
    return _digest_text(_canonical_json(payload))


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
