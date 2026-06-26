"""Emit the Objective Alpha evidence extension policy report."""

from __future__ import annotations

from examples.objective_alpha_public_proof_bundle_gate import (
    build_report_object as build_public_bundle_gate_report_object,
)
from tuc.objective_alpha import (
    ObjectiveAlphaEvidenceExtensionPolicyReport,
    build_objective_alpha_evidence_extension_policy_report,
    dump_objective_alpha_evidence_extension_policy_report,
)


def build_report_object() -> ObjectiveAlphaEvidenceExtensionPolicyReport:
    """Return the current Objective Alpha evidence extension policy report."""

    return build_objective_alpha_evidence_extension_policy_report(
        build_public_bundle_gate_report_object()
    )


def build_report() -> str:
    """Return the stable serialized extension policy report."""

    return dump_objective_alpha_evidence_extension_policy_report(build_report_object())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
