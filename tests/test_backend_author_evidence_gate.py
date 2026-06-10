from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from examples.backend_author_evidence_gate import (
    BackendAuthorEvidenceGateError,
    build_gate_report,
)
from examples.manifest_claim_review import build_current_manifest_claim_review_inputs
from tuc import (
    BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS,
    BackendAuthorReadinessCheck,
    ManifestClaimReviewInput,
    build_backend_author_readiness_report,
    build_manifest_claim_review_report,
)

_GOLDEN = Path("tests/golden/backend_author_readiness/backend_author_evidence_gate.txt")


def test_backend_author_evidence_gate_matches_golden() -> None:
    report = build_gate_report()

    assert report == _GOLDEN.read_text(encoding="utf-8")
    assert 'manifest_claim_review = "passed"' in report
    assert 'backend_author_readiness = "ready"' in report
    assert report.rstrip().endswith('status = "PASS"\n}')


def test_backend_author_evidence_gate_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/backend_author_evidence_gate.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == _GOLDEN.read_text(encoding="utf-8")


def test_backend_author_evidence_gate_rejects_failed_manifest_review() -> None:
    inputs = (
        *build_current_manifest_claim_review_inputs(),
        ManifestClaimReviewInput(
            manifest_id="systolic_expected_blocked",
            path=Path("examples/manifests/systolic_sim_backend.json"),
            expected_review_status="blocked",
        ),
    )
    manifest_claim = build_manifest_claim_review_report(inputs)

    with pytest.raises(BackendAuthorEvidenceGateError, match="manifest claim review"):
        build_gate_report(manifest_claim_report=manifest_claim)


def test_backend_author_evidence_gate_rejects_failed_author_readiness() -> None:
    readiness = build_backend_author_readiness_report(
        backend_name="candidate",
        manifest_id="candidate_manifest",
        checks=tuple(
            BackendAuthorReadinessCheck(
                check_name=check_name,
                status="failed" if check_name == "backend_conformance" else "passed",
                evidence_id=f"{check_name}_evidence",
                detail="test_detail",
            )
            for check_name in BACKEND_AUTHOR_READINESS_REQUIRED_CHECKS
        ),
    )

    with pytest.raises(BackendAuthorEvidenceGateError, match="backend author readiness"):
        build_gate_report(readiness_report=readiness)
