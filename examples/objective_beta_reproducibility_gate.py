"""Replay Objective Beta evidence from fixed repository artifacts only."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from examples.objective_beta_reproducibility_capsule import (
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID,
    OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY,
    ObjectiveBetaReproducibilityCapsuleError,
    assert_objective_beta_reproducibility_capsule_report_contract,
)
from examples.objective_beta_research_claim import (
    OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS,
    OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS,
)

OBJECTIVE_BETA_REPRODUCIBILITY_GATE_SCHEMA_VERSION = (
    "tuc.objective_beta_reproducibility_gate_report.v0"
)
OBJECTIVE_BETA_REPRODUCIBILITY_GATE_CONTRACT = (
    "objective_beta.reproducibility_gate.offline_replay.v0"
)
OBJECTIVE_BETA_REPRODUCIBILITY_GATE_ID = "objective_beta_reproducibility_gate"
OBJECTIVE_BETA_REPRODUCIBILITY_GATE_STATUS = "PASS"
OBJECTIVE_BETA_REPRODUCIBILITY_GATE_FORBIDDEN_EXECUTION_SURFACES = (
    "source_execution",
    "compiler_execution",
    "runtime_execution",
    "backend_execution",
    "plugin_loading",
    "dynamic_import",
    "subprocess_execution",
    "network_access",
    "device_access",
    "generated_artifact_execution",
)

_HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_CAPSULE_GOLDEN_PATH = Path(
    "tests/golden/proofs/objective_beta_reproducibility_capsule.json"
)
_TOP_LEVEL_KEYS = frozenset(
    {
        "blocked_claims",
        "capsule_digest",
        "capsule_id",
        "capsule_metadata_digest",
        "claim_digest",
        "claim_gate_digest",
        "claim_link_verified",
        "evidence_links_verified",
        "external_approval_required",
        "forbidden_execution_surfaces",
        "gate_contract",
        "gate_id",
        "gate_passed",
        "gate_status",
        "issues",
        "native_performance_claim",
        "replay_policy",
        "schema_version",
        "source_free",
        "source_ingestion_admitted",
        "vendor_replacement_claim",
        "verified_artifact_count",
        "verified_artifact_ids",
    }
)


class ObjectiveBetaReproducibilityGateError(AssertionError):
    """Raised when offline Objective Beta replay cannot be verified."""


@lru_cache(maxsize=1)
def build_report() -> str:
    """Return the stable Objective Beta reproducibility gate report."""

    capsule_text = _read_fixed_text(_CAPSULE_GOLDEN_PATH)
    report = build_objective_beta_reproducibility_gate_report(capsule_text)
    assert_objective_beta_reproducibility_gate_report_contract(report)
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> None:
    print(build_report(), end="")


def build_objective_beta_reproducibility_gate_report(
    capsule_text: str,
    *,
    artifact_texts: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Verify a capsule against allowlisted repository evidence without execution."""

    _assert_text_is_source_free(capsule_text)
    capsule = _json_object(capsule_text, "capsule")
    try:
        assert_objective_beta_reproducibility_capsule_report_contract(capsule)
    except ObjectiveBetaReproducibilityCapsuleError as exc:
        raise ObjectiveBetaReproducibilityGateError("capsule contract invalid") from exc

    fixed_artifacts = (
        dict(artifact_texts)
        if artifact_texts is not None
        else {
            artifact_id: _read_fixed_text(relative_path)
            for artifact_id, relative_path in (
                OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ARTIFACT_PATHS.items()
            )
        }
    )
    _verify_allowlisted_artifacts(capsule, fixed_artifacts)
    claim = _json_object(fixed_artifacts["objective_beta_research_claim"], "claim")
    claim_gate = _json_object(
        fixed_artifacts["objective_beta_research_claim_gate"], "claim gate"
    )
    _verify_claim_links(capsule, claim, claim_gate, fixed_artifacts)

    report: dict[str, object] = {
        "blocked_claims": list(OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS),
        "capsule_digest": _digest(capsule_text),
        "capsule_id": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID,
        "capsule_metadata_digest": str(capsule["capsule_metadata_digest"]),
        "claim_digest": str(capsule["claim_digest"]),
        "claim_gate_digest": str(capsule["claim_gate_digest"]),
        "claim_link_verified": True,
        "evidence_links_verified": True,
        "external_approval_required": True,
        "forbidden_execution_surfaces": list(
            OBJECTIVE_BETA_REPRODUCIBILITY_GATE_FORBIDDEN_EXECUTION_SURFACES
        ),
        "gate_contract": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_CONTRACT,
        "gate_id": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_ID,
        "gate_passed": True,
        "gate_status": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_STATUS,
        "issues": [],
        "native_performance_claim": False,
        "replay_policy": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY,
        "schema_version": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_SCHEMA_VERSION,
        "source_free": True,
        "source_ingestion_admitted": False,
        "vendor_replacement_claim": False,
        "verified_artifact_count": len(OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS),
        "verified_artifact_ids": list(
            OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS
        ),
    }
    assert_objective_beta_reproducibility_gate_report_contract(report)
    return report


def assert_objective_beta_reproducibility_gate_report_contract(report: object) -> None:
    """Fail closed unless the offline replay report matches the exact v0 contract."""

    if not isinstance(report, Mapping):
        raise ObjectiveBetaReproducibilityGateError("replay gate report must be object")
    if set(report) != _TOP_LEVEL_KEYS:
        raise ObjectiveBetaReproducibilityGateError("replay gate report keys changed")
    expected = {
        "capsule_id": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_ID,
        "claim_link_verified": True,
        "evidence_links_verified": True,
        "external_approval_required": True,
        "gate_contract": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_CONTRACT,
        "gate_id": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_ID,
        "gate_passed": True,
        "gate_status": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_STATUS,
        "issues": [],
        "native_performance_claim": False,
        "replay_policy": OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_REPLAY_POLICY,
        "schema_version": OBJECTIVE_BETA_REPRODUCIBILITY_GATE_SCHEMA_VERSION,
        "source_free": True,
        "source_ingestion_admitted": False,
        "vendor_replacement_claim": False,
        "verified_artifact_count": len(OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS),
    }
    for key, expected_value in expected.items():
        if report.get(key) != expected_value:
            raise ObjectiveBetaReproducibilityGateError(f"replay gate {key} mismatch")
    if tuple(_string_list(report.get("blocked_claims"), "blocked_claims")) != (
        OBJECTIVE_BETA_RESEARCH_CLAIM_BLOCKED_CLAIMS
    ):
        raise ObjectiveBetaReproducibilityGateError("replay gate blocked_claims mismatch")
    if tuple(
        _string_list(report.get("verified_artifact_ids"), "verified_artifact_ids")
    ) != OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS:
        raise ObjectiveBetaReproducibilityGateError(
            "replay gate verified_artifact_ids mismatch"
        )
    if tuple(
        _string_list(
            report.get("forbidden_execution_surfaces"),
            "forbidden_execution_surfaces",
        )
    ) != OBJECTIVE_BETA_REPRODUCIBILITY_GATE_FORBIDDEN_EXECUTION_SURFACES:
        raise ObjectiveBetaReproducibilityGateError(
            "replay gate forbidden_execution_surfaces mismatch"
        )
    for field_name in (
        "capsule_digest",
        "capsule_metadata_digest",
        "claim_digest",
        "claim_gate_digest",
    ):
        digest = report.get(field_name)
        if not isinstance(digest, str) or not _HEX_DIGEST_PATTERN.fullmatch(digest):
            raise ObjectiveBetaReproducibilityGateError(
                f"replay gate {field_name} invalid"
            )
    _assert_text_is_source_free(json.dumps(report, sort_keys=True))


def _verify_allowlisted_artifacts(
    capsule: Mapping[str, object], artifact_texts: Mapping[str, str]
) -> None:
    if set(artifact_texts) != set(OBJECTIVE_BETA_REPRODUCIBILITY_CAPSULE_EVIDENCE_IDS):
        raise ObjectiveBetaReproducibilityGateError("replay artifact allowlist mismatch")
    evidence = capsule.get("evidence")
    if not isinstance(evidence, list):
        raise ObjectiveBetaReproducibilityGateError("replay capsule evidence missing")
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ObjectiveBetaReproducibilityGateError("replay evidence item invalid")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or artifact_id not in artifact_texts:
            raise ObjectiveBetaReproducibilityGateError("replay artifact id invalid")
        text = artifact_texts[artifact_id]
        _assert_text_is_source_free(text)
        _json_object(text, artifact_id)
        if item.get("digest") != _digest(text):
            raise ObjectiveBetaReproducibilityGateError(
                f"replay artifact digest mismatch: {artifact_id}"
            )


def _verify_claim_links(
    capsule: Mapping[str, object],
    claim: Mapping[str, object],
    claim_gate: Mapping[str, object],
    artifact_texts: Mapping[str, str],
) -> None:
    claim_digest = _digest(artifact_texts["objective_beta_research_claim"])
    claim_gate_digest = _digest(artifact_texts["objective_beta_research_claim_gate"])
    if capsule.get("claim_digest") != claim_digest:
        raise ObjectiveBetaReproducibilityGateError("replay capsule claim digest mismatch")
    if capsule.get("claim_gate_digest") != claim_gate_digest:
        raise ObjectiveBetaReproducibilityGateError(
            "replay capsule claim gate digest mismatch"
        )
    if claim_gate.get("claim_digest") != claim_digest:
        raise ObjectiveBetaReproducibilityGateError("replay claim link mismatch")
    if claim.get("claim_metadata_digest") != capsule.get("claim_metadata_digest"):
        raise ObjectiveBetaReproducibilityGateError(
            "replay claim metadata digest mismatch"
        )
    claim_evidence = claim.get("evidence")
    if not isinstance(claim_evidence, list):
        raise ObjectiveBetaReproducibilityGateError("replay claim evidence missing")
    observed_ids: list[str] = []
    for item in claim_evidence:
        if not isinstance(item, Mapping):
            raise ObjectiveBetaReproducibilityGateError("replay claim evidence invalid")
        artifact_id = item.get("artifact_id")
        if not isinstance(artifact_id, str) or artifact_id not in artifact_texts:
            raise ObjectiveBetaReproducibilityGateError("replay claim artifact id invalid")
        observed_ids.append(artifact_id)
        if item.get("digest") != _digest(artifact_texts[artifact_id]):
            raise ObjectiveBetaReproducibilityGateError(
                f"replay claim evidence digest mismatch: {artifact_id}"
            )
    if tuple(observed_ids) != OBJECTIVE_BETA_RESEARCH_CLAIM_EVIDENCE_IDS:
        raise ObjectiveBetaReproducibilityGateError("replay claim evidence order mismatch")
    for payload_name, payload in (("claim", claim), ("claim gate", claim_gate)):
        for key in (
            "source_ingestion_admitted",
            "native_performance_claim",
            "vendor_replacement_claim",
        ):
            if payload.get(key) is not False:
                raise ObjectiveBetaReproducibilityGateError(
                    f"replay {payload_name} {key} mismatch"
                )
        if payload.get("external_approval_required") is not True:
            raise ObjectiveBetaReproducibilityGateError(
                f"replay {payload_name} external approval boundary mismatch"
            )


def _read_fixed_text(relative_path: Path) -> str:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ObjectiveBetaReproducibilityGateError("replay fixed path invalid")
    try:
        text = (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ObjectiveBetaReproducibilityGateError("replay artifact read failed") from exc
    _assert_text_is_source_free(text)
    return text


def _json_object(text: str, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ObjectiveBetaReproducibilityGateError(
            f"replay {label} is not valid JSON"
        ) from exc
    if not isinstance(value, Mapping):
        raise ObjectiveBetaReproducibilityGateError(f"replay {label} must be object")
    return value


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ObjectiveBetaReproducibilityGateError(
            f"replay gate {field_name} must be string list"
        )
    return value


def _assert_text_is_source_free(text: str) -> None:
    for fragment in OBJECTIVE_BETA_RESEARCH_CLAIM_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            raise ObjectiveBetaReproducibilityGateError(
                "replay input contains forbidden source or runtime fragment"
            )


if __name__ == "__main__":
    main()
