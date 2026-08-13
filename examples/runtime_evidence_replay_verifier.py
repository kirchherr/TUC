"""Emit Runtime Evidence Replay Verifier Report v0."""

from examples.runtime_execution_evidence_bundle import (
    build_execution_evidence_bundle_report,
)
from examples.runtime_execution_output_closure import (
    build_execution_output_closure_report,
)
from tuc.runtime.evidence_replay_verifier import (
    RuntimeEvidenceReplayVerifierReport,
    build_runtime_evidence_replay_verifier_report,
    dump_runtime_evidence_replay_verifier_report,
)
from tuc.runtime.execution_evidence_bundle import (
    dump_runtime_execution_evidence_bundle_report,
)
from tuc.runtime.execution_output_closure import (
    dump_runtime_execution_output_closure_report,
)


def build_evidence_replay_verifier_report() -> RuntimeEvidenceReplayVerifierReport:
    """Return the current proof-of-execution replay verifier report."""

    evidence_bundle_text = dump_runtime_execution_evidence_bundle_report(
        build_execution_evidence_bundle_report()
    )
    output_closure_text = dump_runtime_execution_output_closure_report(
        build_execution_output_closure_report()
    )
    return build_runtime_evidence_replay_verifier_report(
        evidence_bundle_text,
        output_closure_text,
    )


def build_report() -> str:
    """Return stable serialized Runtime Evidence Replay Verifier evidence."""

    return dump_runtime_evidence_replay_verifier_report(
        build_evidence_replay_verifier_report()
    )


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
