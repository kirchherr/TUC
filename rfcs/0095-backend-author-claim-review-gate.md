# RFC 0095: Backend Author Claim Review Gate

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Gamma

## Summary

Make Manifest Claim Review part of the external backend author path before
registry loading, compiler planning, backend conformance, or trusted lowering.

## Motivation

Manifest Claim Review exists as a standalone report, but backend authors need a
single reference path that applies the same gate automatically. Without that
integration, a valid-looking external manifest could be reviewed separately
from the authoring workflow and drift into planning evidence without the
claim-shape checks maintainers expect.

## Decision

Update `examples/external_backend_author_path.py` so it now runs:

1. Manifest Claim Review.
2. Explicit manifest registry loading.
3. Pure-data registry support diagnostics.
4. Compiler planning.
5. Backend conformance.
6. Trusted lowering of only the assigned HAC-IR subgraph.

The author path stops before registry loading if the manifest claim review does
not pass or if the manifest case is not `accepted`.

Add:

- `build_external_backend_claim_review(...)`
- `claim_review` on `ExternalBackendAuthorReport`
- golden evidence at
  `tests/golden/backend_claim_review/external_vector_author_report.json`
- tests proving accepted external manifests pass and blocked manifests stop the
  author path

## Security Model

The gate preserves the existing boundaries:

- explicit manifest paths only
- no directory scanning
- no plugin discovery
- no dynamic import
- no subprocess execution
- no device access
- no dynamic-library loading
- no network access
- no generated-artifact execution

Manifest Claim Review remains policy and evidence. It does not make manifests
executable and does not replace trusted runtime executor contracts.

## Consequences

- Backend author onboarding now applies manifest claim review by default.
- Accepted external manifests carry deterministic claim-review evidence before
  compiler planning.
- Blocked manifests fail early, before registry diagnostics, conformance, or
  lowering.
- The loader remains a bounded parser; authoring policy lives in the review
  gate.

## References

- [Manifest Claim Review](../docs/MANIFEST_CLAIM_REVIEW.md)
- [Backend Author Certification](../docs/BACKEND_AUTHOR_CERTIFICATION.md)
- [Backend API v0.1](../docs/BACKEND_API.md)
- `examples/external_backend_author_path.py`
- `tests/test_external_backend_author_path.py`
