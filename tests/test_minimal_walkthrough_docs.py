from __future__ import annotations

from pathlib import Path


def test_minimal_tuc_walkthrough_is_bounded_and_reviewable() -> None:
    text = Path("docs/MINIMAL_TUC_WALKTHROUGH.md").read_text(encoding="utf-8")

    for expected in (
        "hardware-independent compute intent",
        "Runtime Tensor Store",
        "Output Contract and Public Output Bundle",
        "Runtime Replay Verifier",
        "Backend Equivalence",
        "Transfer and Layout Trace Evidence",
        "Runtime Layout Conversion Trace Index",
        "blocked -> row_major",
        "runtime_layout_conversion_trace_replay_verifier",
        "runtime_backend_equivalence_layout_binding",
        "python examples/proof_of_execution.py",
        "python examples/runtime_evidence_gate.py",
        "python examples/source_to_intent_research_kernel_ingress_evidence_gate.py",
        "reference-cpu",
        "linear-sim",
        "vector-sim",
        "What This Proves",
        "What This Does Not Prove",
        "does not prove native",
        "does not approve arbitrary source-code parsing",
        "does not authorize plugin discovery",
        "secure compiler boundary",
    ):
        assert expected in text


def test_backend_equivalence_proof_type_has_clear_boundaries() -> None:
    text = Path("docs/PROOF_OF_BACKEND_EQUIVALENCE.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "Proof of Backend Equivalence is a TUC proof type",
        "reference-cpu",
        "capability-selected",
        "linear-sim",
        "vector-sim",
        "no single simulator is the proof center",
        "Required Evidence",
        "Current Artifacts",
        "What It Proves",
        "What It Does Not Prove",
        "does not prove native device execution",
        "does not prove native performance parity",
        "data-only",
        "must not serialize",
        "trusted in-process",
        "Runtime Executor boundary",
        "Reviewer Checklist",
        "the report is not bound by the relevant evidence gate",
    ):
        assert expected in text


def test_layout_conversion_evidence_rfc_blocks_implicit_conversions() -> None:
    text = Path("rfcs/0212-runtime-layout-conversion-evidence.md").read_text(
        encoding="utf-8"
    )

    for expected in (
        "Runtime Layout Conversion Evidence",
        "This RFC does not implement layout conversion",
        "explicit planned layout transitions",
        "HAC-IR as compute intent",
        "PartitionPlan",
        "RuntimeLayoutConversionEvidence",
        "conversion_records",
        "from_layout",
        "to_layout",
        "planned_bytes",
        "Backend-local hidden conversions do not count as evidence",
        "planned logical layout, not physical residency",
        "must not contain tensor values",
        "negative tests for unknown layouts",
        "Runtime Evidence Gate binding to exact artifact IDs",
    ):
        assert expected in text


