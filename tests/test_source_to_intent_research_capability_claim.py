from __future__ import annotations

import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from examples.source_to_intent_research_capability_claim import (
    SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT,
    SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_REPORT_SCHEMA_VERSION,
    assert_research_capability_claim_report_contract,
    build_report,
    build_research_capability_claim_report,
)

GOLDEN_PATH = Path(
    "tests/golden/frontend/source_to_intent_research_capability_claim.json"
)
SCHEMA_PATH = Path(
    "schemas/source_to_intent_research_capability_claim_report.v0.schema.json"
)


@lru_cache(maxsize=1)
def _cached_report_text() -> str:
    return build_report()


def _fresh_report() -> dict[str, object]:
    return json.loads(_cached_report_text())


def test_source_to_intent_research_capability_claim_report_shape() -> None:
    report = _fresh_report()
    assert_research_capability_claim_report_contract(report)

    assert report["schema_version"] == (
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_REPORT_SCHEMA_VERSION
    )
    assert report["claim_contract"] == (
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT
    )
    assert report["status"] == "PASS"
    assert report["claim_id"] == "bounded_universal_compute_research_slice"
    assert report["claim_status"] == "supported_for_current_research_scope"
    assert report["accepted_kernel_count"] == 5
    assert report["runtime_case_count"] == 5
    assert report["backend_equivalence_case_count"] == 5
    assert report["backend_equivalence_shape_profile_case_count"] == 10
    assert report["baseline_runtime_backend"] == "reference-cpu"
    assert report["combined_pipeline_kernel"] == "mvp_pipeline"
    assert report["combined_pipeline_operation_path"] == [
        "matmul",
        "softmax",
        "reduction",
        "elementwise",
    ]
    assert report["trusted_runtime_backends"] == ["linear-sim", "vector-sim"]
    assert report["blocked_claims"] == [
        "arbitrary_backend_execution",
        "general_triton_source_ingestion",
        "hardware_certification",
        "native_performance_claim",
        "production_parser",
        "vendor_compiler_replacement",
    ]
    assert [item["artifact_id"] for item in report["evidence"]] == [
        "source_to_intent_research_proof_bundle",
        "source_to_intent_research_evidence_gate",
        "source_to_intent_research_kernel_ingress_proof_bundle",
        "source_to_intent_research_kernel_ingress_evidence_gate",
        "source_to_intent_research_kernel_ingress_runtime_matrix",
        "source_to_intent_research_kernel_ingress_runtime_step_trace",
        "source_to_intent_research_kernel_ingress_runtime_evidence_bundle_index",
        "source_to_intent_research_kernel_ingress_runtime_output_closure_index",
        "source_to_intent_research_kernel_ingress_runtime_replay_verifier_index",
        "source_to_intent_research_kernel_ingress_backend_equivalence",
        "source_to_intent_research_kernel_ingress_backend_equivalence_shape_profiles",
        "source_to_intent_research_kernel_ingress_runtime_coverage_policy",
        "source_to_intent_research_kernel_ingress_runtime_backend_alignment",
    ]


@pytest.mark.parametrize(
    ("tamper_key", "tamper_value", "error"),
    [
        ("status", "WARN", "status"),
        ("accepted_kernel_count", 3, "accepted_kernel_count"),
        ("blocked_claims", [], "blocked_claims"),
        ("raw_source", "def kernel(): pass", "top-level report"),
    ],
)
def test_source_to_intent_research_capability_claim_rejects_drift(
    tamper_key: str,
    tamper_value: object,
    error: str,
) -> None:
    report = _fresh_report()
    report[tamper_key] = tamper_value

    with pytest.raises(ValueError, match=error):
        assert_research_capability_claim_report_contract(report)


def test_source_to_intent_research_capability_claim_rejects_evidence_drift() -> None:
    report = _fresh_report()
    evidence = report["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0]["digest"] = "sha256:" + "0" * 63

    with pytest.raises(ValueError, match="digest drift"):
        assert_research_capability_claim_report_contract(report)


def test_source_to_intent_research_capability_claim_rejects_source_leakage() -> None:
    report = _fresh_report()
    evidence = report["evidence"]
    assert isinstance(evidence, list)
    assert isinstance(evidence[0], dict)
    evidence[0]["artifact_id"] = "@triton.jit"

    with pytest.raises(ValueError, match="artifact_id drift|forbidden material"):
        assert_research_capability_claim_report_contract(report)


def test_source_to_intent_research_capability_claim_matches_golden() -> None:
    assert _cached_report_text() == GOLDEN_PATH.read_text(encoding="utf-8")


def test_source_to_intent_research_capability_claim_example_runs() -> None:
    completed = subprocess.run(
        [sys.executable, "examples/source_to_intent_research_capability_claim.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == GOLDEN_PATH.read_text(encoding="utf-8")
    assert '"status": "PASS"' in completed.stdout
    assert '"claim_id": "bounded_universal_compute_research_slice"' in completed.stdout
    assert '"baseline_runtime_backend": "reference-cpu"' in completed.stdout
    assert '"combined_pipeline_kernel": "mvp_pipeline"' in completed.stdout
    assert "source_to_intent_research_kernel_ingress_evidence_gate" in completed.stdout
    assert "@triton.jit" not in completed.stdout
    assert "import triton" not in completed.stdout
    assert "tl.dot" not in completed.stdout
    assert "tl.store" not in completed.stdout
    assert "source_intent_payload" not in completed.stdout


def test_source_to_intent_research_capability_claim_schema_declares_contract() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_REPORT_SCHEMA_VERSION
    )
    assert schema["properties"]["claim_contract"]["const"] == (
        SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM_CONTRACT
    )
    assert schema["properties"]["accepted_kernel_count"]["const"] == 5
    assert schema["properties"]["runtime_case_count"]["const"] == 5
    assert schema["properties"]["backend_equivalence_case_count"]["const"] == 5
    assert schema["properties"]["backend_equivalence_shape_profile_case_count"][
        "const"
    ] == 10
    assert schema["properties"]["baseline_runtime_backend"]["const"] == "reference-cpu"
    assert schema["properties"]["evidence_count"]["const"] == 13
    assert schema["$defs"]["evidence"]["additionalProperties"] is False
    assert "blocked_claims" in schema["required"]


def test_source_to_intent_research_capability_claim_is_documented_and_in_ci() -> None:
    example_path = "examples/source_to_intent_research_capability_claim.py"
    doc_path = "SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"

    for path in (
        Path(".github/workflows/ci.yml"),
        Path("README.md"),
        Path("ROADMAP.md"),
        Path("docs/ROADMAP_STATUS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_EVIDENCE_GATE.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_PROOF_BUNDLE.md"),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_STEP_TRACE.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_EVIDENCE_BUNDLE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_OUTPUT_CLOSURE_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_RUNTIME_REPLAY_VERIFIER_INDEX.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE.md"
        ),
        Path(
            "docs/"
            "SOURCE_TO_INTENT_RESEARCH_KERNEL_INGRESS_BACKEND_EQUIVALENCE_SHAPE_PROFILES.md"
        ),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
        Path(
            "rfcs/"
            "0180-source-to-intent-research-kernel-ingress-runtime-step-trace.md"
        ),
        Path(
            "rfcs/"
            "0181-source-to-intent-research-kernel-ingress-runtime-evidence-bundle-index.md"
        ),
        Path(
            "rfcs/"
            "0209-source-to-intent-research-kernel-ingress-runtime-output-closure-index.md"
        ),
        Path(
            "rfcs/"
            "0211-source-to-intent-research-kernel-ingress-runtime-replay-verifier-index.md"
        ),
        Path(
            "rfcs/"
            "0182-source-to-intent-research-kernel-ingress-backend-equivalence.md"
        ),
        Path(
            "rfcs/"
            "0183-source-to-intent-research-kernel-ingress-backend-equivalence-shape-profiles.md"
        ),
    ):
        assert example_path in path.read_text(encoding="utf-8")

    for path in (
        Path("README.md"),
        Path("docs/SOURCE_TO_INTENT_RESEARCH_PROOF_BUNDLE.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
    ):
        assert doc_path in path.read_text(encoding="utf-8")


def test_source_to_intent_research_capability_claim_docs_list_evidence_inputs() -> None:
    report = _fresh_report()
    evidence = report["evidence"]
    assert isinstance(evidence, list)
    evidence_paths = [f"examples/{item['artifact_id']}.py" for item in evidence]

    for path in (
        Path("docs/SOURCE_TO_INTENT_RESEARCH_CAPABILITY_CLAIM.md"),
        Path("rfcs/0178-source-to-intent-research-capability-claim.md"),
    ):
        text = path.read_text(encoding="utf-8")
        for evidence_path in evidence_paths:
            assert evidence_path in text
        assert "Follow-Up Evidence" not in text
