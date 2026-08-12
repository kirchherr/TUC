"""Emit the digest-only Objective Beta reproducibility capsule."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from examples.objective_beta_research_claim import (
    OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
    assert_objective_beta_research_claim_report_contract,
)
from examples.objective_beta_research_claim_gate import (
    OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID,
    assert_objective_beta_research_claim_gate_report_contract,
)

OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION = (
    "tuc.objective_beta_reproducibility_capsule_report.v0"
)
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_CONTRACT = (
    "objective_beta.reproducibility_capsule.digest_manifest.v0"
)
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID = "objective_beta_reproducibility_capsule"
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_STATUS = "reproducible_from_repository_goldens"
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_POLICY = (
    "allowlisted_repository_goldens_digest_only_source_free"
)
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY = (
    "no_source_compiler_runtime_or_backend_execution"
)
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_SPECS = (
    ("objective_alpha_research_claim_gate", "predecessor_claim_gate"),
    (
        "source_to_intent_research_kernel_ingress_proof_bundle",
        "kernel_ingress_proof",
    ),
    ("first_real_triton_kernel_path", "bounded_kernel_path"),
    ("real_triton_first_slice_evidence_portfolio", "first_slice_portfolio"),
    (
        "real_triton_first_slice_admission_readiness_gate",
        "fail_closed_admission_readiness",
    ),
    (
        "real_triton_first_slice_maintainer_approval_request",
        "external_review_request",
    ),
    ("research_scope_claim_gate", "research_scope_boundary"),
    ("oci_source_ingestion_research_proof", "kernel_isolation_proof"),
    (
        "oci_source_worker_release_provenance_readiness",
        "release_provenance_readiness",
    ),
    ("objective_beta_research_claim", "research_claim"),
    ("objective_beta_research_claim_gate", "research_claim_gate"),
)
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS = tuple(
    artifact_id
    for artifact_id, _role in OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_SPECS
)
OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS = {
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
    "objective_beta_research_claim": Path(
        "tests/golden/proofs/objective_beta_research_claim.json"
    ),
    "objective_beta_research_claim_gate": Path(
        "tests/golden/proofs/objective_beta_research_claim_gate.json"
    ),
}

_HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_TOP_LEVEL_KEYS = frozenset(
    {
        "artifact_policy",
        "blocked_claims",
        "capsule_contract",
        "capsule_id",
        "capsule_metadata_digest",
        "capsule_status",
        "claim_digest",
        "claim_gate_digest",
        "claim_gate_id",
        "claim_id",
        "claim_metadata_digest",
        "evidence",
        "evidence_count",
        "external_approval_required",
        "native_performance_claim",
        "replay_policy",
        "schema_version",
        "source_ingestion_admitted",
        "vendor_replacement_claim",
    }
)
_EVIDENCE_KEYS = frozenset(
    {"artifact_id", "content_type", "digest", "role", "source_free"}
)


class ObjectiveBetaReproducibilityCapsuleError(AssertionError):
    """Raised when the Objective Beta capsule cannot be reproduced safely."""


@lru_cache(maxsize=1)
def build_report() -> str:
    """Return the stable serialized Objective Beta reproducibility capsule."""

    report = build_objective_beta_reproducibility_capsule_report()
    assert_objective_beta_reproducibility_capsule_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


@lru_cache(maxsize=1)
def build_objective_beta_reproducibility_capsule_report() -> dict[str, object]:
    """Build a fixed, source-free manifest over Objective Beta evidence."""

    artifact_texts = _read_allowlisted_artifact_texts()
    artifact_payloads = {
        artifact_id: _json_object(text, artifact_id)
        for artifact_id, text in artifact_texts.items()
    }
    claim = artifact_payloads["objective_beta_research_claim"]
    claim_gate = artifact_payloads["objective_beta_research_claim_gate"]
    assert_objective_beta_research_claim_report_contract(claim)
    assert_objective_beta_research_claim_gate_report_contract(claim_gate)
    _assert_claim_chain(artifact_texts, claim, claim_gate)

    evidence = [
        {
            "artifact_id": artifact_id,
            "content_type": "application/json",
            "digest": _digest(artifact_texts[artifact_id]),
            "role": role,
            "source_free": True,
        }
        for artifact_id, role in OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_SPECS
    ]
    report: dict[str, object] = {
        "artifact_policy": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_POLICY,
        "blocked_claims": list(OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS),
        "capsule_contract": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_CONTRACT,
        "capsule_id": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID,
        "capsule_status": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_STATUS,
        "claim_digest": _digest(artifact_texts["objective_beta_research_claim"]),
        "claim_gate_digest": _digest(
            artifact_texts["objective_beta_research_claim_gate"]
        ),
        "claim_gate_id": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID,
        "claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
        "claim_metadata_digest": str(claim["claim_metadata_digest"]),
        "evidence": evidence,
        "evidence_count": len(evidence),
        "external_approval_required": True,
        "native_performance_claim": False,
        "replay_policy": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY,
        "schema_version": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION,
        "source_ingestion_admitted": False,
        "vendor_replacement_claim": False,
    }
    report["capsule_metadata_digest"] = _capsule_metadata_digest(report)
    return report


def assert_objective_beta_reproducibility_capsule_report_contract(
    report: object,
) -> None:
    """Fail closed unless a capsule matches the exact Objective Beta v0 contract."""

    if not isinstance(report, Mapping):
        raise ObjectiveBetaReproducibilityCapsuleError("capsule report must be an object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise ObjectiveBetaReproducibilityCapsuleError("capsule report keys changed")
    expected = {
        "artifact_policy": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_POLICY,
        "capsule_contract": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_CONTRACT,
        "capsule_id": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID,
        "capsule_status": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_STATUS,
        "claim_gate_id": OBJECTIVE_BETA_RESEARCH_CLAIM_GATE_ID,
        "claim_id": OBJECTIVE_BETA_RESEARCH_CLAIM_ID,
        "evidence_count": len(OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS),
        "external_approval_required": True,
        "native_performance_claim": False,
        "replay_policy": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY,
        "schema_version": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION,
        "source_ingestion_admitted": False,
        "vendor_replacement_claim": False,
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ObjectiveBetaReproducibilityCapsuleError(f"capsule {key} mismatch")
    if tuple(_string_list(report.get("blocked_claims"), "blocked_claims")) != (
        OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS
    ):
        raise ObjectiveBetaReproducibilityCapsuleError("capsule blocked_claims mismatch")
    _assert_evidence(report.get("evidence"))
    for field_name in (
        "capsule_metadata_digest",
        "claim_digest",
        "claim_gate_digest",
        "claim_metadata_digest",
    ):
        digest = report.get(field_name)
        if not isinstance(digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveBetaReproducibilityCapsuleError(
                f"capsule {field_name} invalid"
            )
    if report["capsule_metadata_digest"] != _capsule_metadata_digest(report):
        raise ObjectiveBetaReproducibilityCapsuleError("capsule metadata digest drift")
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _assert_claim_chain(
    artifact_texts: Mapping[str, str],
    claim: Mapping[str, object],
    claim_gate: Mapping[str, object],
) -> None:
    claim_digest = _digest(artifact_texts["objective_beta_research_claim"])
    if claim_gate.get("claim_digest") != claim_digest:
        raise ObjectiveBetaReproducibilityCapsuleError("claim gate digest binding mismatch")
    evidence = claim.get("evidence")
    if not isinstance(evidence, list):
        raise ObjectiveBetaReproducibilityCapsuleError("claim evidence missing")
    expected_dependency_ids = OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS
    observed_ids: list[str] = []
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ObjectiveBetaReproducibilityCapsuleError("claim evidence item invalid")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or artifact_id not in artifact_texts:
            raise ObjectiveBetaReproducibilityCapsuleError("claim evidence id invalid")
        observed_ids.append(artifact_id)
        if item.get("digest") != _digest(artifact_texts[artifact_id]):
            raise ObjectiveBetaReproducibilityCapsuleError(
                f"claim evidence digest mismatch: {artifact_id}"
            )
    if tuple(observed_ids) != expected_dependency_ids:
        raise ObjectiveBetaReproducibilityCapsuleError("claim evidence order mismatch")


def _read_allowlisted_artifact_texts() -> dict[str, str]:
    if set(OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS) != set(
        OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS
    ):
        raise ObjectiveBetaReproducibilityCapsuleError("capsule allowlist mismatch")
    return {
        artifact_id: _read_artifact_text(relative_path)
        for artifact_id, relative_path in (
            OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS.items()
        )
    }


def _read_artifact_text(relative_path: Path) -> str:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ObjectiveBetaReproducibilityCapsuleError("capsule artifact path invalid")
    try:
        text = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ObjectiveBetaReproducibilityCapsuleError(
            "capsule allowlisted artifact read failed"
        ) from exc
    _assert_text_is_source_free(text)
    return text


def _json_object(text: str, artifact_id: str) -> Mapping[str, object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ObjectiveBetaReproducibilityCapsuleError(
            f"capsule artifact is not valid JSON: {artifact_id}"
        ) from exc
    if not isinstance(value, Mapping):
        raise ObjectiveBetaReproducibilityCapsuleError(
            f"capsule artifact must be object: {artifact_id}"
        )
    return value


def _assert_evidence(value: object) -> None:
    if not isinstance(value, list):
        raise ObjectiveBetaReproducibilityCapsuleError("capsule evidence must be list")
    observed: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise ObjectiveBetaReproducibilityCapsuleError("capsule evidence item invalid")
        artifact_id = item.get("artifact_id")
        role = item.get("role")
        if not isinstance(artifact_id, str) or not isinstance(role, str):
            raise ObjectiveBetaReproducibilityCapsuleError(
                "capsule evidence identity invalid"
            )
        observed.append((artifact_id, role))
        if item.get("content_type") != "application/json":
            raise ObjectiveBetaReproducibilityCapsuleError(
                "capsule evidence content_type mismatch"
            )
        if item.get("source_free") is not True:
            raise ObjectiveBetaReproducibilityCapsuleError(
                "capsule evidence source_free mismatch"
            )
        digest = item.get("digest")
        if not isinstance(digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveBetaReproducibilityCapsuleError(
                "capsule evidence digest invalid"
            )
    if tuple(observed) != OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_SPECS:
        raise ObjectiveBetaReproducibilityCapsuleError("capsule evidence order mismatch")


def _capsule_metadata_digest(report: Mapping[str, object]) -> str:
    payload = {key: value for key, value in report.items() if key != "capsule_metadata_digest"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _digest(canonical)


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ObjectiveBetaReproducibilityCapsuleError(
            f"capsule {field_name} must be string list"
        )
    return value


def _assert_text_is_source_free(text: str) -> None:
    for fragment in OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ObjectiveBetaReproducibilityCapsuleError(
                "capsule contains forbidden source or runtime fragment"
            )


if __name__ == "__main__":
    main()
