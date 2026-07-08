"""Emit the current Objective Alpha research claim snapshot."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256

from examples.objective_alpha_evidence_extension_policy import (
    build_report as build_extension_policy_report,
)
from examples.objective_alpha_public_evidence_catalog import (
    build_report as build_public_evidence_catalog_report,
)
from examples.objective_alpha_public_evidence_catalog_admission_gate import (
    build_report as build_public_evidence_catalog_admission_gate_report,
)
from examples.objective_alpha_public_proof_bundle import (
    build_report as build_public_proof_bundle_report,
)
from examples.objective_alpha_public_proof_bundle_gate import (
    build_report as build_public_proof_bundle_gate_report,
)
from examples.source_intent_mixed_runtime_public_proof_bundle import (
    build_report as build_source_intent_mixed_runtime_public_proof_bundle_report,
)

OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION = (
    "tuc.objective_alpha_research_claim_report.v0"
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT = (
    "objective_alpha.research_claim.digest_snapshot.v0"
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID = "objective_alpha_universal_compute_research_claim"
OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS = "supported_for_objective_alpha_research_scope"
OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE = (
    "objective_alpha_public_bundle_catalog_and_mixed_runtime_proof"
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY = "digest_only_source_free"
OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS = (
    "objective_alpha_public_proof_bundle",
    "objective_alpha_public_proof_bundle_gate",
    "objective_alpha_evidence_extension_policy",
    "objective_alpha_public_evidence_catalog",
    "objective_alpha_public_evidence_catalog_admission_gate",
    "source_intent_mixed_runtime_public_proof_bundle",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS = (
    "hardware_independent_compute_intent_current_research_slice",
    "capability_planned_trusted_runtime_execution",
    "mixed_backend_public_semantics_preserved",
    "digest_only_reviewable_public_evidence",
    "rfc_bound_public_evidence_growth",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS = (
    "native_performance_parity",
    "vendor_compiler_replacement",
    "broad_source_code_parsing",
    "arbitrary_third_party_backend_execution",
    "device_access",
    "generated_artifact_execution",
    "production_triton_integration",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS = (
    "public_proof_bundle_full",
    "public_proof_bundle_gate_passed",
    "extension_policy_passed",
    "public_evidence_catalog_passed",
    "public_evidence_catalog_admission_gate_passed",
    "source_intent_mixed_runtime_public_proof_passed",
    "backend_equivalence_passed",
    "reference_correctness_passed",
    "digest_only_source_free_claim",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_OPERATION_FAMILIES = (
    "matmul",
    "softmax",
    "reduction",
    "elementwise",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS = (
    "reference-cpu",
    "systolic-sim",
    "vector-sim",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_BASELINE_BACKEND_SEQUENCE = (
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
    "reference-cpu",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_MIXED_BACKEND_SEQUENCE = (
    "systolic-sim",
    "vector-sim",
    "vector-sim",
    "vector-sim",
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS = (
    "@triton.jit",
    "import triton",
    '"backend_artifact":',
    '"command":',
    '"device_id":',
    '"generated_code":',
    '"host_path":',
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


class ObjectiveAlphaResearchClaimError(AssertionError):
    """Raised when the Objective Alpha research claim cannot be supported."""


@lru_cache(maxsize=1)
def build_report() -> str:
    """Return a stable serialized Objective Alpha research claim snapshot."""

    report = build_objective_alpha_research_claim_report()
    assert_objective_alpha_research_claim_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


@lru_cache(maxsize=1)
def build_objective_alpha_research_claim_report() -> dict[str, object]:
    """Build the current digest-only Objective Alpha research claim report."""

    artifacts = _build_artifact_texts()
    payloads = {artifact_id: _json_payload(text, artifact_id) for artifact_id, text in artifacts}
    _assert_supporting_payloads(payloads)
    evidence = [
        {
            "artifact_id": artifact_id,
            "digest": _digest(text),
            "status": "accepted",
        }
        for artifact_id, text in artifacts
    ]
    report: dict[str, object] = {
        "schema_version": OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION,
        "claim_contract": OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT,
        "claim_id": OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID,
        "claim_status": OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS,
        "claim_scope": OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE,
        "artifact_policy": OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY,
        "claim_passed": True,
        "supported_claims": list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS),
        "blocked_claims": list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS),
        "required_invariants": list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS),
        "evidence": evidence,
        "evidence_count": len(evidence),
        "public_bundle_entry_count": int(
            payloads["objective_alpha_public_proof_bundle"]["entry_count"]
        ),
        "catalog_entry_count": int(
            payloads["objective_alpha_public_evidence_catalog"]["catalog_entry_count"]
        ),
        "public_evidence_entry_count": int(
            payloads["objective_alpha_public_proof_bundle"]["entry_count"]
        )
        + int(payloads["objective_alpha_public_evidence_catalog"]["catalog_entry_count"]),
        "operation_families": list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_OPERATION_FAMILIES),
        "trusted_runtime_backends": list(
            OBJECTIVE_ALPHA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS
        ),
        "baseline_backend_sequence": list(
            OBJECTIVE_ALPHA_RESEARCH_CLAIM_BASELINE_BACKEND_SEQUENCE
        ),
        "mixed_backend_sequence": list(OBJECTIVE_ALPHA_RESEARCH_CLAIM_MIXED_BACKEND_SEQUENCE),
        "backend_equivalence_passed": True,
        "reference_correctness_passed": True,
        "native_performance_claim": False,
        "broad_source_parser_claim": False,
        "vendor_replacement_claim": False,
    }
    report["claim_metadata_digest"] = _claim_metadata_digest(report)
    return report


def assert_objective_alpha_research_claim_report_contract(report: object) -> None:
    """Fail closed unless the Objective Alpha research claim report matches v0."""

    if not isinstance(report, Mapping):
        raise ObjectiveAlphaResearchClaimError("claim report must be an object")
    expected = {
        "schema_version": OBJECTIVE_ALPHA_RESEARCH_CLAIM_REPORT_SCHEMA_VERSION,
        "claim_contract": OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT,
        "claim_id": OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID,
        "claim_status": OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS,
        "claim_scope": OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE,
        "artifact_policy": OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY,
        "claim_passed": True,
        "evidence_count": len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS),
        "public_bundle_entry_count": 16,
        "catalog_entry_count": 5,
        "public_evidence_entry_count": 21,
        "backend_equivalence_passed": True,
        "reference_correctness_passed": True,
        "native_performance_claim": False,
        "broad_source_parser_claim": False,
        "vendor_replacement_claim": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ObjectiveAlphaResearchClaimError(f"claim report {key} mismatch")
    _assert_string_sequence(
        report.get("supported_claims"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
        "supported_claims",
    )
    _assert_string_sequence(
        report.get("blocked_claims"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
        "blocked_claims",
    )
    _assert_string_sequence(
        report.get("required_invariants"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
        "required_invariants",
    )
    _assert_string_sequence(
        report.get("operation_families"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_OPERATION_FAMILIES,
        "operation_families",
    )
    _assert_string_sequence(
        report.get("trusted_runtime_backends"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS,
        "trusted_runtime_backends",
    )
    _assert_string_sequence(
        report.get("baseline_backend_sequence"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_BASELINE_BACKEND_SEQUENCE,
        "baseline_backend_sequence",
    )
    _assert_string_sequence(
        report.get("mixed_backend_sequence"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_MIXED_BACKEND_SEQUENCE,
        "mixed_backend_sequence",
    )
    evidence = report.get("evidence")
    if not isinstance(evidence, list):
        raise ObjectiveAlphaResearchClaimError("claim report evidence must be a list")
    evidence_ids = []
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ObjectiveAlphaResearchClaimError("claim report evidence item invalid")
        artifact_id = item.get("artifact_id")
        digest = item.get("digest")
        status = item.get("status")
        if not isinstance(artifact_id, str):
            raise ObjectiveAlphaResearchClaimError("claim report artifact id missing")
        if not isinstance(digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveAlphaResearchClaimError("claim report digest invalid")
        if status != "accepted":
            raise ObjectiveAlphaResearchClaimError("claim report evidence not accepted")
        evidence_ids.append(artifact_id)
    if tuple(evidence_ids) != OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS:
        raise ObjectiveAlphaResearchClaimError("claim report evidence ids changed")
    metadata_digest = report.get("claim_metadata_digest")
    if not isinstance(metadata_digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(metadata_digest):
        raise ObjectiveAlphaResearchClaimError("claim report metadata digest invalid")
    expected_digest = _claim_metadata_digest(dict(report))
    if metadata_digest != expected_digest:
        raise ObjectiveAlphaResearchClaimError("claim report metadata digest drift")
    _assert_report_is_source_free(report)


def _build_artifact_texts() -> tuple[tuple[str, str], ...]:
    return (
        ("objective_alpha_public_proof_bundle", build_public_proof_bundle_report()),
        ("objective_alpha_public_proof_bundle_gate", build_public_proof_bundle_gate_report()),
        ("objective_alpha_evidence_extension_policy", build_extension_policy_report()),
        ("objective_alpha_public_evidence_catalog", build_public_evidence_catalog_report()),
        (
            "objective_alpha_public_evidence_catalog_admission_gate",
            build_public_evidence_catalog_admission_gate_report(),
        ),
        (
            "source_intent_mixed_runtime_public_proof_bundle",
            build_source_intent_mixed_runtime_public_proof_bundle_report(),
        ),
    )


def _assert_supporting_payloads(payloads: Mapping[str, Mapping[str, object]]) -> None:
    public_bundle = payloads["objective_alpha_public_proof_bundle"]
    if public_bundle.get("entry_count") != 16 or public_bundle.get("entry_capacity") != 16:
        raise ObjectiveAlphaResearchClaimError("public proof bundle is not full")
    if public_bundle.get("native_performance_claim") is not False:
        raise ObjectiveAlphaResearchClaimError("public proof bundle claim expanded")
    if public_bundle.get("broad_source_parser_claim") is not False:
        raise ObjectiveAlphaResearchClaimError("public proof bundle parser claim expanded")
    if public_bundle.get("vendor_replacement_claim") is not False:
        raise ObjectiveAlphaResearchClaimError("public proof bundle vendor claim expanded")

    public_bundle_gate = payloads["objective_alpha_public_proof_bundle_gate"]
    if public_bundle_gate.get("gate_passed") is not True:
        raise ObjectiveAlphaResearchClaimError("public proof bundle gate did not pass")
    if public_bundle_gate.get("entry_count") != 16:
        raise ObjectiveAlphaResearchClaimError("public proof bundle gate entry count drift")

    extension_policy = payloads["objective_alpha_evidence_extension_policy"]
    if extension_policy.get("policy_passed") is not True:
        raise ObjectiveAlphaResearchClaimError("extension policy did not pass")
    if extension_policy.get("stable_entry_count") != 16:
        raise ObjectiveAlphaResearchClaimError("extension policy stable entry count drift")

    catalog = payloads["objective_alpha_public_evidence_catalog"]
    if catalog.get("catalog_passed") is not True:
        raise ObjectiveAlphaResearchClaimError("public evidence catalog did not pass")
    if catalog.get("catalog_entry_count") != 5:
        raise ObjectiveAlphaResearchClaimError("public evidence catalog entry count drift")
    catalog_ids = _mapping_list_values(catalog.get("catalog_entries"), "evidence_id")
    if "source_intent_mixed_runtime_public_proof_bundle" not in catalog_ids:
        raise ObjectiveAlphaResearchClaimError("mixed runtime proof missing from catalog")

    catalog_gate = payloads["objective_alpha_public_evidence_catalog_admission_gate"]
    if catalog_gate.get("gate_passed") is not True:
        raise ObjectiveAlphaResearchClaimError("public evidence catalog gate did not pass")
    if catalog_gate.get("catalog_entry_count") != 5:
        raise ObjectiveAlphaResearchClaimError("public evidence catalog gate entry count drift")

    mixed_proof = payloads["source_intent_mixed_runtime_public_proof_bundle"]
    if mixed_proof.get("status") != "PASS":
        raise ObjectiveAlphaResearchClaimError("mixed runtime proof did not pass")
    if mixed_proof.get("backend_equivalence_passed") is not True:
        raise ObjectiveAlphaResearchClaimError("mixed runtime proof equivalence failed")
    if mixed_proof.get("reference_correctness_passed") is not True:
        raise ObjectiveAlphaResearchClaimError("mixed runtime proof reference failed")
    if tuple(_string_list(mixed_proof.get("operation_families"))) != (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_OPERATION_FAMILIES
    ):
        raise ObjectiveAlphaResearchClaimError("mixed runtime operation families drift")
    if tuple(_string_list(mixed_proof.get("trusted_runtime_backends"))) != (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_TRUSTED_RUNTIME_BACKENDS
    ):
        raise ObjectiveAlphaResearchClaimError("mixed runtime trusted backends drift")
    if tuple(_string_list(mixed_proof.get("baseline_backend_sequence"))) != (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_BASELINE_BACKEND_SEQUENCE
    ):
        raise ObjectiveAlphaResearchClaimError("mixed runtime baseline sequence drift")
    if tuple(_string_list(mixed_proof.get("candidate_backend_sequence"))) != (
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_MIXED_BACKEND_SEQUENCE
    ):
        raise ObjectiveAlphaResearchClaimError("mixed runtime candidate sequence drift")


def _json_payload(text: str, artifact_id: str) -> Mapping[str, object]:
    _assert_text_is_source_free(text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ObjectiveAlphaResearchClaimError(f"{artifact_id} is not JSON") from exc
    if not isinstance(payload, Mapping):
        raise ObjectiveAlphaResearchClaimError(f"{artifact_id} must be an object")
    return payload


def _digest(text: str) -> str:
    _assert_text_is_source_free(text)
    return sha256(text.encode("utf-8")).hexdigest()


def _claim_metadata_digest(report: Mapping[str, object]) -> str:
    payload = dict(report)
    payload.pop("claim_metadata_digest", None)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode("utf-8")).hexdigest()


def _mapping_list_values(value: object, key: str) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveAlphaResearchClaimError("expected list of mappings")
    values: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ObjectiveAlphaResearchClaimError("expected mapping item")
        item_value = item.get(key)
        if not isinstance(item_value, str):
            raise ObjectiveAlphaResearchClaimError("expected string mapping value")
        values.append(item_value)
    return values


def _assert_string_sequence(value: object, expected: tuple[str, ...], field_name: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise ObjectiveAlphaResearchClaimError(f"claim report {field_name} changed")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveAlphaResearchClaimError("expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ObjectiveAlphaResearchClaimError("expected string list item")
        result.append(item)
    return result


def _assert_report_is_source_free(report: Mapping[str, object]) -> None:
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in OBJECTIVE_ALPHA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise ObjectiveAlphaResearchClaimError(
                f"objective alpha research claim contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()