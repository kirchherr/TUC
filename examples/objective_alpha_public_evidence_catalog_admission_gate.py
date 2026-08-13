"""Emit the Objective Alpha public evidence catalog admission gate report."""

from __future__ import annotations

from examples.objective_alpha_public_evidence_catalog import (
    build_report_object as build_public_evidence_catalog_report_object,
)
from tuc.objective_alpha import (
    ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport,
    build_objective_alpha_public_evidence_catalog_admission_gate_report,
    dump_objective_alpha_public_evidence_catalog_admission_gate_report,
)


def build_report_object() -> ObjectiveAlphaPublicEvidenceCatalogAdmissionGateReport:
    """Return the current public evidence catalog admission gate report."""

    return build_objective_alpha_public_evidence_catalog_admission_gate_report(
        build_public_evidence_catalog_report_object()
    )


def build_report() -> str:
    """Return the stable serialized public evidence catalog admission gate report."""

    return dump_objective_alpha_public_evidence_catalog_admission_gate_report(build_report_object())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
