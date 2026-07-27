"""Run the CI-facing Objective Alpha research claim gate."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256

from examples.objective_alpha_research_claim import (
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_REQUIRED_INVARIANTS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS,
    OBJECTIVE_ALPHA_RESEARCH_CLAIM_SUPPORTED_CLAIMS,
    assert_objective_alpha_research_claim_report_contract,
)
from examples.objective_alpha_research_claim import (
    build_report as build_research_claim_report,
)

OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION = (
    "tuc.objective_alpha_research_claim_gate_report.v0"
)
OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_CONTRACT = "objective_alpha.research_claim_gate.ci.v0"
OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_ID = "objective_alpha_research_claim_gate"
OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS = "PASS"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ObjectiveAlphaResearchClaimGateError(AssertionError):
    """Raised when the Objective Alpha research claim gate fails."""


@lru_cache(maxsize=1)
def build_gate_report(*, claim_text: str | None = None) -> str:
    """Return stable CI-facing binding for the Objective Alpha claim."""

    expected_claim_text = build_research_claim_report()
    bound_claim_text = expected_claim_text if claim_text is None else claim_text
    claim = _assert_claim_bound(bound_claim_text)
    if _digest(bound_claim_text) != _digest(expected_claim_text):
        raise ObjectiveAlphaResearchClaimGateError(
            "objective alpha claim gate failed: claim digest drift"
        )
    report = _render_gate_report(bound_claim_text, claim)
    assert_objective_alpha_research_claim_gate_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_gate_report(), end="")


def assert_objective_alpha_research_claim_gate_report_contract(report: object) -> None:
    """Fail closed unless the Objective Alpha claim gate report matches v0."""

    if not isinstance(report, Mapping):
        raise ObjectiveAlphaResearchClaimGateError("claim gate report must be an object")
    expected = {
        "schema_version": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION,
        "gate_contract": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_CONTRACT,
        "gate_id": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_ID,
        "gate_passed": True,
        "gate_status": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS,
        "claim_contract": OBJECTIVE_ALPHA_RESEARCH_CLAIM_CONTRACT,
        "claim_id": OBJECTIVE_ALPHA_RESEARCH_CLAIM_ID,
        "claim_status": OBJECTIVE_ALPHA_RESEARCH_CLAIM_STATUS,
        "claim_scope": OBJECTIVE_ALPHA_RESEARCH_CLAIM_SCOPE,
        "artifact_policy": OBJECTIVE_ALPHA_RESEARCH_CLAIM_ARTIFACT_POLICY,
        "evidence_count": len(OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS),
        "public_bundle_entry_count": 16,
        "catalog_entry_count": 6,
        "public_evidence_entry_count": 22,
        "backend_equivalence_passed": True,
        "reference_correctness_passed": True,
        "native_performance_claim": False,
        "broad_source_parser_claim": False,
        "vendor_replacement_claim": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ObjectiveAlphaResearchClaimGateError(f"claim gate {key} mismatch")
    _assert_string_sequence(
        report.get("evidence_ids"),
        OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS,
        "evidence_ids",
    )
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
    for field_name in ("claim_digest", "claim_metadata_digest"):
        digest = report.get(field_name)
        if not isinstance(digest, str) or not _DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveAlphaResearchClaimGateError(f"claim gate {field_name} invalid")
    if report.get("issues") != []:
        raise ObjectiveAlphaResearchClaimGateError("claim gate issues must be empty")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_claim_bound(claim_text: str) -> Mapping[str, object]:
    if not isinstance(claim_text, str):
        raise ObjectiveAlphaResearchClaimGateError("claim gate input must be text")
    _assert_text_is_source_free(claim_text)
    try:
        claim = json.loads(claim_text)
    except json.JSONDecodeError as exc:
        raise ObjectiveAlphaResearchClaimGateError("claim gate input must be JSON") from exc
    try:
        assert_objective_alpha_research_claim_report_contract(claim)
    except AssertionError as exc:
        raise ObjectiveAlphaResearchClaimGateError(
            "claim gate input failed claim contract"
        ) from exc
    if not isinstance(claim, Mapping):
        raise ObjectiveAlphaResearchClaimGateError("claim gate input must be object")
    return claim


def _render_gate_report(claim_text: str, claim: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_REPORT_SCHEMA_VERSION,
        "gate_contract": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_CONTRACT,
        "gate_id": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_ID,
        "gate_passed": True,
        "gate_status": OBJECTIVE_ALPHA_RESEARCH_CLAIM_GATE_STATUS_PASS,
        "claim_contract": str(claim["claim_contract"]),
        "claim_id": str(claim["claim_id"]),
        "claim_status": str(claim["claim_status"]),
        "claim_scope": str(claim["claim_scope"]),
        "artifact_policy": str(claim["artifact_policy"]),
        "claim_digest": _digest(claim_text),
        "claim_metadata_digest": str(claim["claim_metadata_digest"]),
        "evidence_count": int(claim["evidence_count"]),
        "evidence_ids": _claim_evidence_ids(claim["evidence"]),
        "supported_claims": _string_list(claim["supported_claims"]),
        "blocked_claims": _string_list(claim["blocked_claims"]),
        "required_invariants": _string_list(claim["required_invariants"]),
        "public_bundle_entry_count": int(claim["public_bundle_entry_count"]),
        "catalog_entry_count": int(claim["catalog_entry_count"]),
        "public_evidence_entry_count": int(claim["public_evidence_entry_count"]),
        "backend_equivalence_passed": bool(claim["backend_equivalence_passed"]),
        "reference_correctness_passed": bool(claim["reference_correctness_passed"]),
        "native_performance_claim": bool(claim["native_performance_claim"]),
        "broad_source_parser_claim": bool(claim["broad_source_parser_claim"]),
        "vendor_replacement_claim": bool(claim["vendor_replacement_claim"]),
        "issues": [],
    }


def _claim_evidence_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveAlphaResearchClaimGateError("claim gate evidence must be list")
    evidence_ids: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ObjectiveAlphaResearchClaimGateError("claim gate evidence item invalid")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str):
            raise ObjectiveAlphaResearchClaimGateError("claim gate artifact id missing")
        evidence_ids.append(artifact_id)
    if tuple(evidence_ids) != OBJECTIVE_ALPHA_RESEARCH_CLAIM_EVIDENCE_IDS:
        raise ObjectiveAlphaResearchClaimGateError("claim gate evidence id drift")
    return evidence_ids


def _assert_string_sequence(value: object, expected: tuple[str, ...], field_name: str) -> None:
    if tuple(_string_list(value)) != expected:
        raise ObjectiveAlphaResearchClaimGateError(f"claim gate {field_name} changed")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ObjectiveAlphaResearchClaimGateError("claim gate expected string list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ObjectiveAlphaResearchClaimGateError("claim gate string list item invalid")
        result.append(item)
    return result


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _assert_text_is_source_free(text: str) -> None:
    lowered = text.lower()
    for fragment in OBJECTIVE_ALPHA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS:
        if fragment in lowered:
            raise ObjectiveAlphaResearchClaimGateError(
                f"objective alpha claim gate contains forbidden fragment: {fragment}"
            )


if __name__ == "__main__":
    main()
