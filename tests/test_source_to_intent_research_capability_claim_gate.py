from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from examples.source_to_intent_research_capability_claim import (
    SOURCE_TO_INTENT_RESEARCH_CAPABILITY_REQUIRED_EVIDENCE_IDS,
)
from examples.source_to_intent_research_capability_claim import (
    build_report as build_capability_claim_report,
)
from examples.source_to_intent_research_capability_claim_gate import (
    SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT,
    SourceToIntentResearchCapabilityClaimGateError,
    assert_capability_claim_gate_report_contract,
    build_gate_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_capability_claim_gate.txt"
)


def test_source_to_intent_research_capability_claim_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == GOLDEN_PATH.read_text(encoding="utf-8")
    assert (
        f'gate_contract = "{SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE_CONTRACT}"'
        in report
    )
    assert 'capability_claim = "passed"' in report
    assert 'claim_id = "bounded_universal_compute_research_slice"' in report
    assert 'claim_status = "supported_for_current_research_scope"' in report
    assert 'backend_equivalence_case_count = "5"' in report
    assert 'backend_equivalence_shape_profile_case_count = "10"' in report
    assert 'baseline_runtime_backend = "reference-cpu"' in report
    assert 'combined_pipeline = "matmul->softmax->reduction->elementwise"' in report
    assert 'trusted_runtime_backends = "linear-sim,vector-sim"' in report
    assert 'evidence_count = "13"' in report
    assert (
        'evidence_ids = "'
        + ",".join(SOURCE_TO_INTENT_RESEARCH_CAPABILITY_REQUIRED_EVIDENCE_IDS)
        + '"'
        in report
    )
    assert 'status = "PASS"' in report


def test_source_to_intent_research_capability_claim_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_capability_claim_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert "sha256:" in completed.stdout
    assert "native_performance_claim" in completed.stdout
    assert "vendor_compiler_replacement" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_source_to_intent_research_capability_claim_gate_rejects_status_drift() -> None:
    claim = json.loads(build_capability_claim_report())
    claim["status"] = "WARN"

    with pytest.raises(
        SourceToIntentResearchCapabilityClaimGateError,
        match="claim report binding missing",
    ):
        build_gate_report(capability_claim_text=json.dumps(claim, sort_keys=True))


def test_source_to_intent_research_capability_claim_gate_rejects_digest_drift() -> None:
    claim = json.loads(build_capability_claim_report())
    evidence = claim["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0]["digest"] = "sha256:" + "1" * 64

    with pytest.raises(
        SourceToIntentResearchCapabilityClaimGateError,
        match="claim digest drift",
    ):
        build_gate_report(capability_claim_text=json.dumps(claim, sort_keys=True) + "\n")


def test_source_to_intent_research_capability_claim_gate_rejects_claim_expansion() -> None:
    claim = json.loads(build_capability_claim_report())
    claim["blocked_claims"] = [
        item
        for item in claim["blocked_claims"]
        if item != "vendor_compiler_replacement"
    ]

    with pytest.raises(
        SourceToIntentResearchCapabilityClaimGateError,
        match="claim report binding missing",
    ):
        build_gate_report(capability_claim_text=json.dumps(claim, sort_keys=True) + "\n")


def test_source_to_intent_research_capability_claim_gate_rejects_source_leakage() -> None:
    with pytest.raises(
        SourceToIntentResearchCapabilityClaimGateError,
        match="forbidden source fragment",
    ):
        build_gate_report(capability_claim_text=build_capability_claim_report() + "tl.dot")


def test_source_to_intent_research_capability_claim_gate_contract_rejects_drift() -> None:
    with pytest.raises(
        SourceToIntentResearchCapabilityClaimGateError,
        match="required binding missing",
    ):
        assert_capability_claim_gate_report_contract('status = "PASS"\n')


def test_capability_claim_gate_contract_rejects_evidence_id_drift() -> None:
    report = build_gate_report().replace(
        "source_to_intent_research_evidence_gate",
        "source_to_intent_research_missing_gate",
    )

    with pytest.raises(
        SourceToIntentResearchCapabilityClaimGateError,
        match="required binding missing",
    ):
        assert_capability_claim_gate_report_contract(report)


def test_source_to_intent_research_capability_claim_gate_is_documented_and_in_ci() -> None:
    gate_path = "examples/source_to_intent_research_capability_claim_gate.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_GATE.md"),
        Path("rfcs/0179-source-to-intent-research-capability-claim-gate.md"),
        Path("rfcs/0239-source-to-intent-capability-claim-gate-evidence-id-binding.md"),
    ):
        assert gate_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("rfcs/0179-source-to-intent-research-capability-claim-gate.md"),
        Path("rfcs/0239-source-to-intent-capability-claim-gate-evidence-id-binding.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")
