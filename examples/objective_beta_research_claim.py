"""Emit the Objective Beta research claim snapshot."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from examples.first_real_triton_kernel_path import (
    assert_first_real_triton_kernel_path_report_contract,
)
from examples.objective_alpha_research_claim_gate import (
    assert_objective_alpha_research_claim_gate_report_contract,
)
from examples.oci_source_ingestion_research_proof import (
    assert_oci_source_ingestion_research_proof_report,
)
from examples.oci_source_worker_release_provenance_readiness import (
    assert_report_contract as assert_oci_release_provenance_readiness_report_contract,
)
from examples.real_triton_first_slice_admission_readiness_gate import (
    assert_real_triton_first_slice_admission_readiness_gate_report_contract,
)
from examples.real_triton_first_slice_evidence_portfolio import (
    assert_real_triton_first_slice_evidence_portfolio_report_contract,
)
from examples.real_triton_first_slice_maintainer_approval_request import (
    assert_real_triton_first_slice_maintainer_approval_request_report_contract,
)
from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
    assert_kernel_ingress_proof_bundle_report_contract,
)
from tuc.report_output import emit_public_json_report

OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION = (
    "tuc.objective_beta_research_claim_report.v0"
)
OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT = (
    "objective_beta.research_claim.digest_snapshot.v0"
)
OBJECTIVE_BETA_RESEARCH_CLAIM_ID = "objective_beta_universal_compute_research_claim"
OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS = "supported_for_objective_beta_research_scope"
OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE = (
    "objective_beta_kernel_ingress_first_slice_review_readiness"
)
OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID = (
    "objective_alpha_universal_compute_research_claim"
)
OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY = "digest_only_source_free"
OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS = (
    "objective_alpha_research_claim_gate",
    "source_to_intent_research_kernel_ingress_proof_bundle",
    "first_real_triton_kernel_path",
    "real_triton_first_slice_evidence_portfolio",
    "real_triton_first_slice_admission_readiness_gate",
    "real_triton_first_slice_maintainer_approval_request",
    "research_scope_claim_gate",
    "oci_source_ingestion_research_proof",
    "oci_source_worker_release_provenance_readiness",
)
OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS = (
    "objective_alpha_research_claim_preserved",
    "realistic_kernel_ingress_research_slice_bound",
    "source_intent_to_runtime_mixed_backend_path_bound",
    "first_real_triton_kernel_path_bound",
    "first_slice_review_readiness_bound",
    "external_approval_request_packaged",
    "research_scope_boundaries_preserved",
    "kernel_isolated_source_ingestion_proof_bound",
    "oci_worker_release_provenance_readiness_bound",
)
OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS = (
    "arbitrary_triton_source_ingestion",
    "production_source_parser",
    "broad_source_code_parsing",
    "source_to_compute_graph_admission",
    "native_backend_execution",
    "native_performance_parity",
    "real_hardware_backend_execution",
    "external_plugin_execution",
    "generated_artifact_execution",
    "vendor_compiler_replacement",
    "cuda_replacement",
    "production_source_sandbox",
    "external_release_attestation_verified",
    "public_registry_worker_image",
)
OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS = (
    "objective_alpha_claim_gate_passed",
    "kernel_ingress_proof_bundle_passed",
    "first_real_kernel_path_passed",
    "first_slice_evidence_portfolio_passed",
    "admission_readiness_fail_closed",
    "maintainer_approval_request_non_approving",
    "research_scope_gate_passed",
    "oci_kernel_isolation_proof_passed",
    "oci_release_provenance_readiness_passed",
    "production_source_sandbox_false",
    "external_attestation_unverified",
    "source_ingestion_admitted_false",
    "external_approval_still_required",
    "native_performance_claim_false",
    "vendor_replacement_claim_false",
    "digest_only_source_free_claim",
)
OBJECTIVE_BETA_RESEARCH_CLAIM_OPERATION_FAMILIES = (
    "elementwise",
    "matmul",
    "reduction",
    "softmax",
)
OBJECTIVE_BETA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS = (
    "reference-cpu",
    "systolic-sim",
    "linear-sim",
    "vector-sim",
)
OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"backend_artifact":',
    '"command":',
    '"device_id":',
    '"generated_code":',
    '"host_path":',
    '"module_source":',
    '"python_source":',
    '"raw_benchmark_output":',
    '"raw_source":',
    '"raw_tensor_value":',
    '"raw_timing_samples":',
    '"runtime_handle":',
    '"source_intent_payload":',
    '"source_text":',
    '"tensor_value":',
    '"tensor_values":',
)

_HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_TOP_LEVEL_KEYS = frozenset(
    {
        "accepted_kernel_count",
        "admission_readiness_status",
        "admission_ready",
        "artifact_policy",
        "blocked_claims",
        "broad_source_parser_claim",
        "claim_contract",
        "claim_id",
        "claim_metadata_digest",
        "claim_passed",
        "claim_scope",
        "claim_status",
        "evidence",
        "evidence_count",
        "external_approval_required",
        "first_real_path_status",
        "first_slice_portfolio_status",
        "kernel_ingress_artifact_count",
        "native_performance_claim",
        "operation_families",
        "predecessor_claim_id",
        "production_compiler_claim",
        "realistic_ingress_case_count",
        "research_scope_gate_status",
        "required_invariants",
        "schema_version",
        "source_ingestion_admitted",
        "supported_claims",
        "surface_opened",
        "trusted_runtime_backends",
        "vendor_replacement_claim",
    }
)
_EVIDENCE_KEYS = frozenset({"artifact_id", "contract", "digest", "source_free", "status"})
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACT_PATHS = {
    "objective_alpha_research_claim_gate": Path(
        "tests/golden/proofs/objective_alpha_research_claim_gate.json"
    ),
    "source_to_intent_research_kernel_ingress_proof_bundle": Path(
        "tests/golden/frontend/source_to_intent_research_kernel_ingress_proof_bundle.json"
    ),
    "first_real_triton_kernel_path": Path(
        "tests/golden/frontend/first_real_triton_kernel_path.json"
    ),
    "real_triton_first_slice_evidence_portfolio": Path(
        "tests/golden/frontend/real_triton_first_slice_evidence_portfolio_report.json"
    ),
    "real_triton_first_slice_admission_readiness_gate": Path(
        "tests/golden/frontend/real_triton_first_slice_admission_readiness_gate_report.json"
    ),
    "real_triton_first_slice_maintainer_approval_request": Path(
        "tests/golden/frontend/real_triton_first_slice_maintainer_approval_request_report.json"
    ),
    "research_scope_claim_gate": Path("tests/golden/proofs/research_scope_claim_gate.json"),
    "oci_source_ingestion_research_proof": Path(
        "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
    ),
    "oci_source_worker_release_provenance_readiness": Path(
        "tests/golden/frontend/oci_source_worker_release_provenance_readiness_report.json"
    ),
}


class ObjectiveBetaResearchClaimError(AssertionError):
    """Raised when the Objective Beta research claim cannot be supported."""


@lru_cache(maxsize=1)
def build_report() -> str:
    """Return a stable serialized Objective Beta research claim snapshot."""

    report = build_objective_beta_research_claim_report()
    assert_objective_beta_research_claim_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    emit_public_json_report(build_report())


@lru_cache(maxsize=1)
def build_objective_beta_research_claim_report() -> dict[str, object]:
    """Build the current digest-only Objective Beta research claim report."""

    artifacts = _build_artifact_texts()
    payloads = {artifact_id: _json_payload(text, artifact_id) for artifact_id, text in artifacts}
    _assert_supporting_payloads(payloads)
    evidence = [
        {
            "artifact_id": artifact_id,
            "contract": _artifact_contract(artifact_id, payloads[artifact_id]),
            "digest": _digest(text),
            "source_free": True,
            "status": _artifact_status(artifact_id, payloads[artifact_id]),
        }
        for artifact_id, text in artifacts
    ]
    kernel_bundle = payloads["source_to_intent_research_kernel_ingress_proof_bundle"]
    report: dict[str, object] = {
        "accepted_kernel_count": len(_string_list(kernel_bundle["accepted_kernel_names"])),
        "admission_readiness_status": str(
            payloads["real_triton_first_slice_admission_readiness_gate"]["gate_status"]
        ),
        "admission_ready": False,
        "artifact_policy": OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY,
        "blocked_claims": list(OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS),
        "broad_source_parser_claim": False,
        "claim_contract": OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT,
        "claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
        "claim_passed": True,
        "claim_scope": OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE,
        "claim_status": OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "external_approval_required": True,
        "first_real_path_status": str(payloads["first_real_triton_kernel_path"]["status"]),
        "first_slice_portfolio_status": str(
            payloads["real_triton_first_slice_evidence_portfolio"]["portfolio_status"]
        ),
        "kernel_ingress_artifact_count": int(kernel_bundle["artifact_count"]),
        "native_performance_claim": False,
        "operation_families": list(OBJECTIVE_BETA_RESEARCH_CLAIM_OPERATION_FAMILIES),
        "predecessor_claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID,
        "production_compiler_claim": False,
        "realistic_ingress_case_count": len(_string_list(kernel_bundle["accepted_source_names"])),
        "research_scope_gate_status": str(payloads["research_scope_claim_gate"]["gate_status"]),
        "required_invariants": list(OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS),
        "schema_version": OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION,
        "source_ingestion_admitted": False,
        "supported_claims": list(OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS),
        "surface_opened": False,
        "trusted_runtime_backends": list(OBJECTIVE_BETA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS),
        "vendor_replacement_claim": False,
    }
    report["claim_metadata_digest"] = _claim_metadata_digest(report)
    return report


def assert_objective_beta_research_claim_report_contract(report: object) -> None:
    """Fail closed unless the Objective Beta research claim report matches v0."""

    if not isinstance(report, Mapping):
        raise ObjectiveBetaResearchClaimError("beta claim report must be an object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise ObjectiveBetaResearchClaimError("beta claim report keys changed")
    expected = {
        "schema_version": OBJECTIVE_BETA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION,
        "claim_contract": OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT,
        "claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
        "claim_status": OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS,
        "claim_scope": OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE,
        "predecessor_claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID,
        "artifact_policy": OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY,
        "claim_passed": True,
        "evidence_count": len(OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS),
        "kernel_ingress_artifact_count": 15,
        "accepted_kernel_count": 5,
        "realistic_ingress_case_count": 5,
        "first_real_path_status": "PASS",
        "first_slice_portfolio_status": "PASS",
        "admission_readiness_status": "blocked_missing_maintainer_security_review_approval",
        "research_scope_gate_status": "PASS",
        "external_approval_required": True,
        "admission_ready": False,
        "source_ingestion_admitted": False,
        "surface_opened": False,
        "native_performance_claim": False,
        "production_compiler_claim": False,
        "broad_source_parser_claim": False,
        "vendor_replacement_claim": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ObjectiveBetaResearchClaimError(f"beta claim report {key} mismatch")
    _assert_string_sequence(
        report.get("supported_claims"),
        OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
        "supported_claims",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    _assert_string_sequence(
        report.get("operation_families"),
        OBJECTIVE_BETA_RESEARCH_CLAIM_OPERATION_FAMILIES,
        "operation_families",
    )
    _assert_string_sequence(
        report.get("trusted_runtime_backends"),
        OBJECTIVE_BETA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS,
        "trusted_runtime_backends",
    )
    _assert_evidence(report.get("evidence"))
    digest = report.get("claim_metadata_digest")
    if not isinstance(digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(digest):
        raise ObjectiveBetaResearchClaimError("beta claim metadata digest invalid")
    if digest != _claim_metadata_digest(report):
        raise ObjectiveBetaResearchClaimError("beta claim metadata digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _build_artifact_texts() -> tuple[tuple[str, str], ...]:
    return tuple(
        (artifact_id, _read_artifact_text(_ARTIFACT_PATHS[artifact_id]))
        for artifact_id in OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS
    )


def _assert_supporting_payloads(payloads: Mapping[str, Mapping[str, object]]) -> None:
    alpha = payloads["objective_alpha_research_claim_gate"]
    kernel = payloads["source_to_intent_research_kernel_ingress_proof_bundle"]
    first_path = payloads["first_real_triton_kernel_path"]
    portfolio = payloads["real_triton_first_slice_evidence_portfolio"]
    readiness = payloads["real_triton_first_slice_admission_readiness_gate"]
    approval_request = payloads["real_triton_first_slice_maintainer_approval_request"]
    scope = payloads["research_scope_claim_gate"]
    oci_proof = payloads["oci_source_ingestion_research_proof"]
    oci_readiness = payloads["oci_source_worker_release_provenance_readiness"]

    assert_objective_alpha_research_claim_gate_report_contract(alpha)
    assert_kernel_ingress_proof_bundle_report_contract(kernel)
    assert_first_real_triton_kernel_path_report_contract(first_path)
    assert_real_triton_first_slice_evidence_portfolio_report_contract(portfolio)
    assert_real_triton_first_slice_admission_readiness_gate_report_contract(readiness)
    assert_real_triton_first_slice_maintainer_approval_request_report_contract(
        approval_request
    )
    assert_oci_source_ingestion_research_proof_report(dict(oci_proof))
    assert_oci_release_provenance_readiness_report_contract(oci_readiness)
    _assert_status(scope, "gate_contract", "research_scope.claim_gate.data_only.v0")
    _assert_status(scope, "gate_status", "PASS")
    _assert_true(alpha, "gate_passed")
    _assert_status(kernel, "status", "PASS")
    _assert_status(first_path, "status", "PASS")
    _assert_status(portfolio, "portfolio_status", "PASS")
    _assert_status(
        readiness,
        "gate_status",
        "blocked_missing_maintainer_security_review_approval",
    )
    _assert_false(readiness, "gate_passed")
    _assert_false(readiness, "admitted")
    _assert_false(readiness, "surface_opened")
    _assert_status(approval_request, "request_status", "ready_for_external_review")
    _assert_status(approval_request, "approval_status", "not_approved")
    _assert_false(approval_request, "approval_request_is_approval")
    _assert_false(approval_request, "admitted")
    _assert_false(approval_request, "surface_opened")
    _assert_true(scope, "gate_passed")
    _assert_false(scope, "source_ingestion_admitted")
    _assert_false(scope, "native_performance_claim")
    _assert_false(scope, "production_compiler_claim")
    _assert_status(oci_proof, "proof_status", "PASS")
    _assert_false(oci_proof, "production_source_ingestion")
    _assert_false(oci_proof, "production_source_sandbox")
    _assert_false(oci_proof, "published_worker_image_provenance")
    _assert_status(oci_readiness, "readiness_status", "PASS")
    _assert_false(oci_readiness, "external_attestation_verified")
    _assert_false(oci_readiness, "production_source_ingestion")
    _assert_false(oci_readiness, "production_source_sandbox")
    _assert_false(oci_readiness, "published_worker_image_provenance")
    _assert_false(oci_readiness, "execution_permission")
    if int(kernel["artifact_count"]) != 15:
        raise ObjectiveBetaResearchClaimError("kernel ingress artifact count mismatch")


def _artifact_contract(artifact_id: str, payload: Mapping[str, object]) -> str:
    contract_keys = {
        "objective_alpha_research_claim_gate": "gate_contract",
        "source_to_intent_research_kernel_ingress_proof_bundle": "bundle_contract",
        "first_real_triton_kernel_path": "path_contract",
        "real_triton_first_slice_evidence_portfolio": "portfolio_contract",
        "real_triton_first_slice_admission_readiness_gate": "gate_contract",
        "real_triton_first_slice_maintainer_approval_request": "request_contract",
        "research_scope_claim_gate": "gate_contract",
        "oci_source_ingestion_research_proof": "proof_contract",
        "oci_source_worker_release_provenance_readiness": "readiness_contract",
    }
    return str(payload[contract_keys[artifact_id]])


def _artifact_status(artifact_id: str, payload: Mapping[str, object]) -> str:
    status_keys = {
        "objective_alpha_research_claim_gate": "gate_status",
        "source_to_intent_research_kernel_ingress_proof_bundle": "status",
        "first_real_triton_kernel_path": "status",
        "real_triton_first_slice_evidence_portfolio": "portfolio_status",
        "real_triton_first_slice_admission_readiness_gate": "gate_status",
        "real_triton_first_slice_maintainer_approval_request": "request_status",
        "research_scope_claim_gate": "gate_status",
        "oci_source_ingestion_research_proof": "proof_status",
        "oci_source_worker_release_provenance_readiness": "readiness_status",
    }
    return str(payload[status_keys[artifact_id]])


def _assert_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise ObjectiveBetaResearchClaimError("beta claim evidence must be list")
    observed_ids: list[str] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise ObjectiveBetaResearchClaimError("beta claim evidence item invalid")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str):
            raise ObjectiveBetaResearchClaimError("beta claim evidence id missing")
        observed_ids.append(artifact_id)
        if item.get("source_free") is not True:
            raise ObjectiveBetaResearchClaimError("beta claim evidence source_free mismatch")
        digest = item.get("digest")
        if not isinstance(digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveBetaResearchClaimError("beta claim evidence digest invalid")
    if tuple(observed_ids) != OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS:
        raise ObjectiveBetaResearchClaimError("beta claim evidence ids mismatch")


def _json_payload(text: str, artifact_id: str) -> Mapping[str, object]:
    _assert_text_is_source_free(text)
    value = json.loads(text)
    if not isinstance(value, Mapping):
        raise ObjectiveBetaResearchClaimError(f"{artifact_id} must be a JSON object")
    return value


def _read_artifact_text(relative_path: Path) -> str:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ObjectiveBetaResearchClaimError("beta claim artifact path invalid")
    try:
        text = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ObjectiveBetaResearchClaimError("beta claim artifact read failed") from exc
    _assert_text_is_source_free(text)
    return text


def _assert_status(payload: Mapping[str, object], key: str, expected: str) -> None:
    if payload.get(key) != expected:
        raise ObjectiveBetaResearchClaimError(f"beta claim {key} mismatch")


def _assert_true(payload: Mapping[str, object], key: str) -> None:
    if payload.get(key) is not True:
        raise ObjectiveBetaResearchClaimError(f"beta claim {key} mismatch")


def _assert_false(payload: Mapping[str, object], key: str) -> None:
    if payload.get(key) is not False:
        raise ObjectiveBetaResearchClaimError(f"beta claim {key} mismatch")


def _assert_string_sequence(value: object, expected: tuple[str, ...], field_name: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise ObjectiveBetaResearchClaimError(f"beta claim {field_name} mismatch")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveBetaResearchClaimError("beta claim expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ObjectiveBetaResearchClaimError("beta claim string list item invalid")
        result.append(item)
    return result


def _digest(text: str) -> str:
    _assert_text_is_source_free(text)
    return sha256(text.encode("utf-8")).hexdigest()


def _claim_metadata_digest(report: Mapping[str, object]) -> str:
    payload = {key: value for key, value in report.items() if key != "claim_metadata_digest"}
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise ObjectiveBetaResearchClaimError(
                f"objective beta claim contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
