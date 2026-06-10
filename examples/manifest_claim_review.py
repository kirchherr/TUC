"""Emit backend capability manifest claim-review evidence."""

from pathlib import Path

from tuc import (
    ManifestClaimReviewInput,
    build_manifest_claim_review_report,
    dump_manifest_claim_review_report,
)

MANIFEST_ROOT = Path(__file__).with_name("manifests")
REVIEW_ROOT = MANIFEST_ROOT / "review"


def build_current_manifest_claim_review_inputs() -> tuple[ManifestClaimReviewInput, ...]:
    """Return explicit manifest cases for the current claim-review suite."""

    return (
        ManifestClaimReviewInput(
            manifest_id="systolic_sim_backend",
            path=MANIFEST_ROOT / "systolic_sim_backend.json",
            expected_review_status="accepted",
        ),
        ManifestClaimReviewInput(
            manifest_id="invalid_executable_surface_backend",
            path=REVIEW_ROOT / "invalid_executable_surface_backend.json",
            expected_review_status="blocked",
        ),
        ManifestClaimReviewInput(
            manifest_id="invalid_noise_without_error_budget_backend",
            path=REVIEW_ROOT / "invalid_noise_without_error_budget_backend.json",
            expected_review_status="blocked",
        ),
        ManifestClaimReviewInput(
            manifest_id="invalid_overbroad_accelerator_backend",
            path=REVIEW_ROOT / "invalid_overbroad_accelerator_backend.json",
            expected_review_status="blocked",
        ),
    )


def main() -> None:
    report = build_manifest_claim_review_report(
        build_current_manifest_claim_review_inputs()
    )
    print(dump_manifest_claim_review_report(report), end="")


if __name__ == "__main__":
    main()
