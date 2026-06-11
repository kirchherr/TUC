"""Run the CI-facing Backend Author Evidence Gate."""

try:
    from examples.backend_author_readiness import (
        build_external_vector_backend_author_readiness,
    )
    from examples.manifest_claim_review import build_current_manifest_claim_review_inputs
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from backend_author_readiness import build_external_vector_backend_author_readiness
    from manifest_claim_review import build_current_manifest_claim_review_inputs

from tuc import (
    RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES,
    BackendAuthorReadinessReport,
    ManifestClaimReviewReport,
    build_manifest_claim_review_report,
)


class BackendAuthorEvidenceGateError(AssertionError):
    """Raised when backend author evidence is incomplete."""


def build_gate_report(
    *,
    manifest_claim_report: ManifestClaimReviewReport | None = None,
    readiness_report: BackendAuthorReadinessReport | None = None,
) -> str:
    """Return the stable CI-facing backend author evidence gate report."""

    manifest_claim = (
        build_manifest_claim_review_report(build_current_manifest_claim_review_inputs())
        if manifest_claim_report is None
        else manifest_claim_report
    )
    readiness = (
        build_external_vector_backend_author_readiness()
        if readiness_report is None
        else readiness_report
    )
    _assert_manifest_claim_review_passed(manifest_claim)
    _assert_backend_author_ready(readiness)
    return _render_gate_report(manifest_claim, readiness)


def main() -> None:
    print(build_gate_report(), end="")


def _assert_manifest_claim_review_passed(report: ManifestClaimReviewReport) -> None:
    if not report.passed:
        issues = ",".join(
            f"{issue.manifest_id}:{issue.issue_code}" for issue in report.report_issues
        )
        raise BackendAuthorEvidenceGateError(
            f"manifest claim review incomplete: {issues}"
        )


def _assert_backend_author_ready(report: BackendAuthorReadinessReport) -> None:
    if not report.ready:
        issues = ",".join(
            f"{issue.check_name}:{issue.issue_code}" for issue in report.issues
        )
        raise BackendAuthorEvidenceGateError(
            f"backend author readiness incomplete: {issues}"
        )


def _render_gate_report(
    manifest_claim: ManifestClaimReviewReport,
    readiness: BackendAuthorReadinessReport,
) -> str:
    lines = ["backend_author.evidence_gate @backend_author_evidence_gate_v0 {"]
    lines.append('  manifest_claim_review = "passed"')
    lines.append(f'  manifest_claim_review_cases = "{len(manifest_claim.cases)}"')
    lines.append('  backend_author_readiness = "ready"')
    lines.append(f'  backend_author_readiness_checks = "{len(readiness.checks)}"')
    lines.append(
        "  blocked_execution_surfaces = "
        f'"{",".join(RUNTIME_EXECUTOR_BLOCKED_EXECUTION_SURFACES)}"'
    )
    lines.append('  status = "PASS"')
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
