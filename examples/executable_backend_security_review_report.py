"""Emit a diagnostic executable backend security review report."""

from tuc import (
    ExecutableBackendSecurityReview,
    build_executable_backend_security_review_report,
    dump_executable_backend_security_review_report,
)


def main() -> None:
    report = build_executable_backend_security_review_report(
        "phase1_backend_security_candidate",
        reviews=(
            ExecutableBackendSecurityReview(
                review_id="cuda_artifact_execution_review",
                reviewed_surface="backend_artifact_execution",
                threat_model_id="backend_execution_threat_model",
                sandbox_model_id="not_supplied",
                resource_budget_id="backend_execution_budget",
                provenance_id="security_rfc_0075",
                review_status="reviewed_not_approved",
            ),
        ),
    )
    print(dump_executable_backend_security_review_report(report), end="")


if __name__ == "__main__":
    main()
