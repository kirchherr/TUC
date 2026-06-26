"""Emit the digest-only Objective Alpha public proof bundle."""

from __future__ import annotations

from hashlib import sha256

from examples.proof_of_backend_equivalence import (
    build_report as build_backend_equivalence_proof_report,
)
from examples.proof_of_execution import render_proof_report, run_proof
from examples.research_onboarding_evidence import build_report as build_onboarding_report
from examples.runtime_allocation_reconciliation import (
    build_current_runtime_allocation_reconciliation_report,
)
from examples.runtime_backend_equivalence_layout_binding import (
    build_report as build_backend_equivalence_layout_binding_report,
)
from examples.runtime_backend_equivalence_transfer_binding import (
    build_report as build_backend_equivalence_transfer_binding_report,
)
from examples.runtime_evidence_gate import build_gate_report
from examples.runtime_evidence_matrix import build_report as build_matrix_report
from examples.runtime_execution_output_closure import (
    build_report as build_output_closure_report,
)
from examples.runtime_layout_conversion_trace_replay_verifier import (
    build_report as build_layout_conversion_trace_replay_verifier_report,
)
from examples.runtime_memory_planning_gate import (
    build_gate_report as build_memory_planning_gate_report,
)
from examples.runtime_transfer_trace_replay_verifier import (
    build_report as build_transfer_trace_replay_verifier_report,
)
from tuc import (
    ObjectiveAlphaPublicEvidenceEntry,
    ObjectiveAlphaPublicProofBundle,
    build_objective_alpha_public_proof_bundle,
    dump_objective_alpha_public_proof_bundle,
    dump_runtime_allocation_reconciliation_report,
)


def build_bundle() -> ObjectiveAlphaPublicProofBundle:
    """Build the current Objective Alpha public proof bundle."""

    proof = run_proof()
    if not proof.passed:
        raise RuntimeError("proof_of_execution did not pass")
    proof_output = render_proof_report(proof) + "\n"
    matrix_output = build_matrix_report()
    gate_output = build_gate_report()
    backend_equivalence_proof_output = build_backend_equivalence_proof_report()
    output_closure_output = build_output_closure_report()
    transfer_trace_replay_output = build_transfer_trace_replay_verifier_report()
    backend_equivalence_transfer_binding_output = (
        build_backend_equivalence_transfer_binding_report()
    )
    layout_conversion_trace_replay_output = (
        build_layout_conversion_trace_replay_verifier_report()
    )
    backend_equivalence_layout_binding_output = (
        build_backend_equivalence_layout_binding_report()
    )
    allocation_reconciliation_output = dump_runtime_allocation_reconciliation_report(
        build_current_runtime_allocation_reconciliation_report()
    )
    memory_planning_gate_output = build_memory_planning_gate_report()
    onboarding_output = build_onboarding_report()
    return build_objective_alpha_public_proof_bundle(
        (
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="proof_of_execution",
                entry_point="python examples/proof_of_execution.py",
                artifact_kind="deterministic_proof_output",
                metadata_digest=_digest_text(proof_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_evidence_matrix",
                entry_point="python examples/runtime_evidence_matrix.py",
                artifact_kind="schema_versioned_matrix_report",
                metadata_digest=_digest_text(matrix_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_evidence_gate",
                entry_point="python examples/runtime_evidence_gate.py",
                artifact_kind="deterministic_gate_output",
                metadata_digest=_digest_text(gate_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="proof_of_backend_equivalence",
                entry_point="python examples/proof_of_backend_equivalence.py",
                artifact_kind="schema_versioned_backend_equivalence_proof_report",
                metadata_digest=_digest_text(backend_equivalence_proof_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_execution_output_closure",
                entry_point="python examples/runtime_execution_output_closure.py",
                artifact_kind="schema_versioned_output_closure_report",
                metadata_digest=_digest_text(output_closure_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_transfer_trace_replay_verifier",
                entry_point="python examples/runtime_transfer_trace_replay_verifier.py",
                artifact_kind="schema_versioned_transfer_trace_replay_verifier_report",
                metadata_digest=_digest_text(transfer_trace_replay_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_backend_equivalence_transfer_binding",
                entry_point="python examples/runtime_backend_equivalence_transfer_binding.py",
                artifact_kind="schema_versioned_backend_equivalence_transfer_binding_report",
                metadata_digest=_digest_text(backend_equivalence_transfer_binding_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_layout_conversion_trace_replay_verifier",
                entry_point="python examples/runtime_layout_conversion_trace_replay_verifier.py",
                artifact_kind="schema_versioned_layout_conversion_trace_replay_verifier_report",
                metadata_digest=_digest_text(layout_conversion_trace_replay_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_backend_equivalence_layout_binding",
                entry_point="python examples/runtime_backend_equivalence_layout_binding.py",
                artifact_kind="schema_versioned_backend_equivalence_layout_binding_report",
                metadata_digest=_digest_text(backend_equivalence_layout_binding_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_allocation_reconciliation",
                entry_point="python examples/runtime_allocation_reconciliation.py",
                artifact_kind="schema_versioned_allocation_reconciliation_report",
                metadata_digest=_digest_text(allocation_reconciliation_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="runtime_memory_planning_gate",
                entry_point="python examples/runtime_memory_planning_gate.py",
                artifact_kind="deterministic_memory_planning_gate_output",
                metadata_digest=_digest_text(memory_planning_gate_output),
            ),
            ObjectiveAlphaPublicEvidenceEntry(
                evidence_id="research_onboarding_evidence",
                entry_point="python examples/research_onboarding_evidence.py",
                artifact_kind="schema_versioned_onboarding_report",
                metadata_digest=_digest_text(onboarding_output),
            ),
        )
    )


def build_report() -> str:
    """Return the stable serialized public proof bundle."""

    return dump_objective_alpha_public_proof_bundle(build_bundle())


def main() -> None:
    print(build_report(), end="")


def _digest_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
