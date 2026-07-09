"""Emit the project-level TUC research-scope claim gate report."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path

from examples.objective_alpha_research_claim_gate import (
    assert_objective_alpha_research_claim_gate_report_contract,
)
from examples.source_ingestion_admission_gate import (
    assert_source_ingestion_admission_gate_report_contract,
)
from examples.source_ingestion_maintainer_approval_artifact import (
    assert_source_ingestion_maintainer_approval_artifact_report_contract,
)
from examples.source_to_intent_research_capability_claim_gate import (
    SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT,
    assert_capability_claim_gate_report_contract,
)
from tuc.proof import PERFORMANCE_PROOF_INTERPRETATION_CLAIM_STATUS
from tuc.research_scope_claim_gate import (
    ResearchScopeEvidenceBinding,
    build_research_scope_claim_gate_report,
    dump_research_scope_claim_gate_report,
)

_SOURCE_TO_INTENT_CAPABILITY_GATE_ID = (
    "source_to_intent_research_capability_claim_gate"
)
_PERFORMANCE_PROOF_INTERPRETATION_ID = "performance_proof_interpretation"
_OBJECTIVE_ALPHA_GATE_GOLDEN = Path(
    "tests/golden/proofs/objective_alpha_research_claim_gate.json"
)
_SOURCE_TO_INTENT_CAPABILITY_GATE_GOLDEN = Path(
    "tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt"
)
_PERFORMANCE_PROOF_INTERPRETATION_GOLDEN = Path(
    "tests/golden/proofs/performance_proof_interpretation_report.json"
)
_SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_GOLDEN = Path(
    "tests/golden/frontend/source_ingestion_maintainer_approval_artifact_report.json"
)
_SOURCE_INGESTION_ADMISSION_GATE_GOLDEN = Path(
    "tests/golden/frontend/source_ingestion_admission_gate_report.json"
)


def build_current_research_scope_claim_gate_report_text() -> str:
    """Return stable JSON for the current research-scope claim gate."""

    report = build_research_scope_claim_gate_report(
        (
            _objective_alpha_research_claim_gate_binding(),
            _source_to_intent_research_capability_claim_gate_binding(),
            _performance_proof_interpretation_binding(),
            _source_ingestion_maintainer_approval_artifact_binding(),
            _source_ingestion_admission_gate_binding(),
        )
    )
    return dump_research_scope_claim_gate_report(report)


def main() -> None:
    print(build_current_research_scope_claim_gate_report_text(), end="")


def _objective_alpha_research_claim_gate_binding() -> ResearchScopeEvidenceBinding:
    text = _OBJECTIVE_ALPHA_GATE_GOLDEN.read_text(encoding="utf-8")
    payload = _load_json_object(text, "objective alpha research claim gate")
    assert_objective_alpha_research_claim_gate_report_contract(payload)
    return ResearchScopeEvidenceBinding(
        evidence_id=str(payload["gate_id"]),
        contract=str(payload["gate_contract"]),
        status=str(payload["gate_status"]),
        digest=_digest_text(text),
    )


def _source_to_intent_research_capability_claim_gate_binding() -> (
    ResearchScopeEvidenceBinding
):
    text = _SOURCE_TO_INTENT_CAPABILITY_GATE_GOLDEN.read_text(encoding="utf-8")
    assert_capability_claim_gate_report_contract(text)
    return ResearchScopeEvidenceBinding(
        evidence_id=_SOURCE_TO_INTENT_CAPABILITY_GATE_ID,
        contract=SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT,
        status="PASS",
        digest=_digest_text(text),
    )


def _performance_proof_interpretation_binding() -> ResearchScopeEvidenceBinding:
    text = _PERFORMANCE_PROOF_INTERPRETATION_GOLDEN.read_text(encoding="utf-8")
    payload = _load_json_object(text, "performance proof interpretation")
    if payload["performance_claim_status"] != PERFORMANCE_PROOF_INTERPRETATION_CLAIM_STATUS:
        raise AssertionError("performance proof interpretation claim status drift")
    if payload["native_performance_claim"] is not False:
        raise AssertionError("performance proof interpretation must block native claims")
    if payload["performance_proof_interpretation_ready"] is not False:
        raise AssertionError("current interpretation must remain blocked")
    return ResearchScopeEvidenceBinding(
        evidence_id=_PERFORMANCE_PROOF_INTERPRETATION_ID,
        contract=str(payload["claim_boundary"]),
        status=str(payload["performance_claim_status"]),
        digest=_digest_text(text),
    )


def _source_ingestion_maintainer_approval_artifact_binding() -> (
    ResearchScopeEvidenceBinding
):
    text = _SOURCE_INGESTION_MAINTAINER_APPROVAL_ARTIFACT_GOLDEN.read_text(
        encoding="utf-8"
    )
    payload = _load_json_object(text, "source ingestion maintainer approval artifact")
    assert_source_ingestion_maintainer_approval_artifact_report_contract(payload)
    if payload["approval_artifact_present"] is not False:
        raise AssertionError("source ingestion approval artifact must remain absent")
    if payload["approval_status"] != "not_approved":
        raise AssertionError("source ingestion approval artifact must not approve")
    if payload["source_ingestion_admission_ready"] is not False:
        raise AssertionError("source ingestion approval artifact must block admission")
    return ResearchScopeEvidenceBinding(
        evidence_id=str(payload["evidence_id"]),
        contract=str(payload["contract"]),
        status=str(payload["status"]),
        digest=_digest_text(text),
    )


def _source_ingestion_admission_gate_binding() -> ResearchScopeEvidenceBinding:
    text = _SOURCE_INGESTION_ADMISSION_GATE_GOLDEN.read_text(encoding="utf-8")
    payload = _load_json_object(text, "source ingestion admission gate")
    assert_source_ingestion_admission_gate_report_contract(payload)
    if payload["admitted"] is not False:
        raise AssertionError("source ingestion admission gate must remain blocked")
    return ResearchScopeEvidenceBinding(
        evidence_id=str(payload["gate_id"]),
        contract=str(payload["gate_contract"]),
        status=str(payload["gate_status"]),
        digest=_digest_text(text),
    )


def _load_json_object(text: str, label: str) -> Mapping[str, object]:
    value = json.loads(text)
    if not isinstance(value, Mapping):
        raise AssertionError(f"{label} must emit a JSON object")
    return value


def _digest_text(text: str) -> str:
    return f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"


if __name__ == "__main__":
    main()