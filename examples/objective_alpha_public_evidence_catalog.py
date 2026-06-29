"""Emit the Objective Alpha public evidence catalog report."""

from __future__ import annotations

from examples.objective_alpha_evidence_extension_policy import (
    build_report_object as build_extension_policy_report_object,
)
from examples.runtime_backend_equivalence_portfolio import (
    build_backend_equivalence_portfolio_report,
)
from tuc.objective_alpha import (
    ObjectiveAlphaPublicEvidenceCatalogReport,
    build_objective_alpha_public_evidence_catalog_report,
    dump_objective_alpha_public_evidence_catalog_report,
)


def build_report_object() -> ObjectiveAlphaPublicEvidenceCatalogReport:
    """Return the current Objective Alpha public evidence catalog report."""

    return build_objective_alpha_public_evidence_catalog_report(
        build_extension_policy_report_object(),
        build_backend_equivalence_portfolio_report(),
    )


def build_report() -> str:
    """Return the stable serialized public evidence catalog report."""

    return dump_objective_alpha_public_evidence_catalog_report(build_report_object())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()
