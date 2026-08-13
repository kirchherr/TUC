"""Run the CI-facing Objective Beta research claim gate."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256

from examples.objective_beta_research_claim import (
    OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY,
    OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT,
    OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
    OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID,
    OBJECTIVE_BETA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE,
    OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
    assert_objective_beta_research_claim_report_contract,
)
from examples.objective_beta_research_claim import (
    build_report as build_research_claim_report,
)
from tuc.report_output import emit_public_json_report

OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.objective_beta_research_claim_gate_report.v0"
)
OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_CONTRACT = "objective_beta.research_claim_gate.ci.v0"
OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID = "objective_beta_research_claim_gate"
OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS = "PASS"

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ObjectiveBetaResearchClaimGateError(AssertionError):
    """Raised when the Objective Beta research claim gate fails."""


@lru_cache(maxsize=1)
def build_gate_report(*, claim_text: str | None = None) -> str:
    """Return stable CI-facing binding for the Objective Beta claim."""

    expected_claim_text = build_research_claim_report()
    bound_claim_text = expected_claim_text if claim_text is None else claim_text
    claim = _assert_claim_bound(bound_claim_text)
    if _digest(bound_claim_text) != _digest(expected_claim_text):
        raise ObjectiveBetaResearchClaimGateError(
            "objective beta claim gate failed: claim digest drift"
        )
    report = _render_gate_report(bound_claim_text, claim)
    assert_objective_beta_research_claim_gate_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    emit_public_json_report(build_gate_report())


def assert_objective_beta_research_claim_gate_report_contract(report: object) -> None:
    """Fail closed unless the Objective Beta claim gate report matches v0."""

    if not isinstance(report, Mapping):
        raise ObjectiveBetaResearchClaimGateError("beta claim gate report must be object")
    expected = {
        "schema_version": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION,
        "gate_contract": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_CONTRACT,
        "gate_id": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID,
        "gate_passed": True,
        "gate_status": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS,
        "claim_contract": OBJECTIVE_BETA_RESEARCH_CLAIM_CONTRACT,
        "claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
        "claim_status": OBJECTIVE_BETA_RESEARCH_CLAIM_STATUS,
        "claim_scope": OBJECTIVE_BETA_RESEARCH_CLAIM_SCOPE,
        "predecessor_claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_PREDECESSOR_CLAIM_ID,
        "artifact_policy": OBJECTIVE_BETA_RESEARCH_CLAIM_ARTIFACT_POLICY,
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
            raise ObjectiveBetaResearchClaimGateError(f"beta claim gate {key} mismatch")
    _assert_string_sequence(
        report.get("evidence_ids"),
        OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS,
        "evidence_ids",
    )
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
    for field_name in ("claim_digest", "claim_metadata_digest"):
        digest = report.get(field_name)
        if not isinstance(digest, str) or not _DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveBetaResearchClaimGateError(
                f"beta claim gate {field_name} invalid"
            )
    if report.get("issues") != []:
        raise ObjectiveBetaResearchClaimGateError("beta claim gate issues must be empty")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_claim_bound(claim_text: str) -> Mapping[str, object]:
    if not isinstance(claim_text, str):
        raise ObjectiveBetaResearchClaimGateError("beta claim gate input must be text")
    _assert_text_is_source_free(claim_text)
    try:
        claim = json.loads(claim_text)
    except json.JSONDecodeError as exc:
        raise ObjectiveBetaResearchClaimGateError(
            "beta claim gate input must be JSON"
        ) from exc
    try:
        assert_objective_beta_research_claim_report_contract(claim)
    except AssertionError as exc:
        raise ObjectiveBetaResearchClaimGateError(
            "beta claim gate input failed claim contract"
        ) from exc
    if not isinstance(claim, Mapping):
        raise ObjectiveBetaResearchClaimGateError("beta claim gate input must be object")
    return claim


def _render_gate_report(claim_text: str, claim: Mapping[str, object]) -> dict[str, object]:
    return {
        "admission_readiness_status": str(claim["admission_readiness_status"]),
        "admission_ready": bool(claim["admission_ready"]),
        "artifact_policy": str(claim["artifact_policy"]),
        "blocked_claims": _string_list(claim["blocked_claims"]),
        "broad_source_parser_claim": bool(claim["broad_source_parser_claim"]),
        "claim_contract": str(claim["claim_contract"]),
        "claim_digest": _digest(claim_text),
        "claim_id": str(claim["claim_id"]),
        "claim_metadata_digest": str(claim["claim_metadata_digest"]),
        "claim_scope": str(claim["claim_scope"]),
        "claim_status": str(claim["claim_status"]),
        "evidence_count": int(claim["evidence_count"]),
        "evidence_ids": _claim_evidence_ids(claim["evidence"]),
        "external_approval_required": bool(claim["external_approval_required"]),
        "first_real_path_status": str(claim["first_real_path_status"]),
        "first_slice_portfolio_status": str(claim["first_slice_portfolio_status"]),
        "gate_contract": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_CONTRACT,
        "gate_id": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID,
        "gate_passed": True,
        "gate_status": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_STATUS_PASS,
        "issues": [],
        "kernel_ingress_artifact_count": int(claim["kernel_ingress_artifact_count"]),
        "native_performance_claim": bool(claim["native_performance_claim"]),
        "predecessor_claim_id": str(claim["predecessor_claim_id"]),
        "production_compiler_claim": bool(claim["production_compiler_claim"]),
        "accepted_kernel_count": int(claim["accepted_kernel_count"]),
        "realistic_ingress_case_count": int(claim["realistic_ingress_case_count"]),
        "research_scope_gate_status": str(claim["research_scope_gate_status"]),
        "required_invariants": _string_list(claim["required_invariants"]),
        "schema_version": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION,
        "source_ingestion_admitted": bool(claim["source_ingestion_admitted"]),
        "supported_claims": _string_list(claim["supported_claims"]),
        "surface_opened": bool(claim["surface_opened"]),
        "vendor_replacement_claim": bool(claim["vendor_replacement_claim"]),
    }


def _claim_evidence_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveBetaResearchClaimGateError("beta claim gate evidence must be list")
    evidence_ids: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ObjectiveBetaResearchClaimGateError("beta claim gate evidence invalid")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str):
            raise ObjectiveBetaResearchClaimGateError("beta claim gate artifact id missing")
        evidence_ids.append(artifact_id)
    if tuple(evidence_ids) != OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS:
        raise ObjectiveBetaResearchClaimGateError("beta claim gate evidence id drift")
    return evidence_ids


def _assert_string_sequence(value: object, expected: tuple[str, ...], field_name: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise ObjectiveBetaResearchClaimGateError(f"beta claim gate {field_name} changed")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveBetaResearchClaimGateError("beta claim gate expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ObjectiveBetaResearchClaimGateError(
                "beta claim gate string list item invalid"
            )
        result.append(item)
    return result


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise ObjectiveBetaResearchClaimGateError(
                f"objective beta claim gate contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
