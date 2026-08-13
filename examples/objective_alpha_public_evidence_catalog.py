"""Emit the Objective Alpha public evidence catalog report."""

from __future__ import annotations

from pathlib import Path

from examples.first_real_triton_kernel_path import (
    build_report as build_first_real_triton_kernel_path_report,
)
from examples.objective_alpha_evidence_extension_policy import (
    build_report_object as build_extension_policy_report_object,
)
from examples.oci_source_worker_release_provenance_readiness import (
    build_report as build_oci_source_worker_release_provenance_readiness_report,
)
from examples.real_triton_first_slice_evidence_portfolio import (
    build_report as build_real_triton_first_slice_evidence_portfolio_report,
)
from examples.runtime_backend_equivalence_portfolio import (
    build_backend_equivalence_portfolio_report,
)
from examples.source_intent_mixed_runtime_public_proof_bundle import (
    build_report as build_source_intent_mixed_runtime_public_proof_bundle_report,
)
from examples.source_to_intent_research_capability_claim_gate import (
    build_gate_report as build_capability_claim_gate_report,
)
from examples.source_to_intent_research_kernel_ingress_proof_bundle import (
    build_report as build_kernel_ingress_proof_bundle_report,
)
from tuc.objective_alpha import (
    ObjectiveAlphaPublicEvidenceCatalogReport,
    build_objective_alpha_public_evidence_catalog_report,
    dump_objective_alpha_public_evidence_catalog_report,
)

_OCI_SOURCE_INGESTION_RESEARCH_PROOF_GOLDEN = Path(
    "tests/golden/frontend/oci_source_ingestion_research_proof_report.json"
)


def build_report_object() -> ObjectiveAlphaPublicEvidenceCatalogReport:
    """Return the current Objective Alpha public evidence catalog report."""

    return build_objective_alpha_public_evidence_catalog_report(
        build_extension_policy_report_object(),
        build_backend_equivalence_portfolio_report(),
        build_kernel_ingress_proof_bundle_report(),
        build_source_intent_mixed_runtime_public_proof_bundle_report(),
        build_capability_claim_gate_report(),
        build_first_real_triton_kernel_path_report(),
        build_real_triton_first_slice_evidence_portfolio_report(),
        _OCI_SOURCE_INGESTION_RESEARCH_PROOF_GOLDEN.read_text(encoding="utf-8"),
        build_oci_source_worker_release_provenance_readiness_report(),
    )


def build_report() -> str:
    """Return the stable serialized public evidence catalog report."""

    return dump_objective_alpha_public_evidence_catalog_report(build_report_object())


def main() -> None:
    print(build_report(), end="")


if __name__ == "__main__":
    main()

