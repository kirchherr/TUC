"""Emit a diagnostic performance-proof RFC report."""

from tuc import (
    PerformanceProofRFC,
    build_performance_proof_rfc_report,
    dump_performance_proof_rfc_report,
)


def main() -> None:
    report = build_performance_proof_rfc_report(
        "native_performance_proposal",
        rfcs=(
            PerformanceProofRFC(
                rfc_id="native_matmul64_performance_rfc",
                workload_scope_id="matmul64_scope",
                claim_threshold_policy_id="near_native_threshold_policy",
                acceptance_criteria_id="native_performance_acceptance_criteria",
                evidence_bundle_id="not_supplied",
                security_review_id="backend_execution_security_review",
                rfc_status="reviewed_not_accepted",
            ),
        ),
    )
    print(dump_performance_proof_rfc_report(report), end="")


if __name__ == "__main__":
    main()
