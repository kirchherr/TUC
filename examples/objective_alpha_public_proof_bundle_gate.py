"""Emit the Objective Alpha public proof bundle gate report."""

from __future__ import annotations

from examples.objective_alpha_public_proof_bundle import build_bundle
from tuc.objective_alpha import (
    ObjectiveAlphaPublicProofBundleGateReport,
    build_objective_alpha_public_proof_bundle_gate_report,
    dump_objective_alpha_public_proof_bundle_gate_report,
)


def build_report_object() -> ObjectiveAlphaPublicProofBundleGateReport:
    """Return the current public proof bundle gate report."""

    return build_objective_alpha_public_proof_bundle_gate_report(build_bundle())


def build_report() -> str:
    """Return the stable serialized public proof bundle gate report."""

    return dump_objective_alpha_public_proof_bundle_gate_report(build_report_object())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()