# RFC 0094: Manifest Claim Review

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Gamma

## Summary

Add a schema-versioned Manifest Claim Review report for backend capability
manifests and add negative fixtures for overreaching specialized accelerator
claims.

## Motivation

The backend capability loader already rejects malformed manifests and unknown
fields. That is necessary but not sufficient: a manifest can be syntactically
valid while still making claims that would weaken TUC's architecture, such as a
specialized accelerator claiming every operation family or a noisy backend
declaring approximation support without an explicit error-budget boundary.

TUC needs a review artifact that makes those claims visible and fail-closed
before they influence public proof narratives.

## Decision

Add:

- [Manifest Claim Review](../docs/MANIFEST_CLAIM_REVIEW.md)
- `schemas/manifest_claim_review_report.v0.schema.json`
- `examples/manifest_claim_review.py`
- negative fixtures under `examples/manifests/review/`
- golden report at
  `tests/golden/backend_claim_review/manifest_claim_review_report.json`
- focused tests in `tests/test_manifest_claim_review.py`

The report accepts explicit manifest paths, loads each through the bounded
backend capability manifest loader, applies claim-shape rules, and records
whether the observed review status matches the expected status for that case.

## Security Model

Manifest Claim Review is data-only. It does not scan directories, discover
plugins, import modules, instantiate backend objects, spawn subprocesses, load
dynamic libraries, access devices, touch the network, execute generated
artifacts, run JIT code, parse source text, or authorize runtime execution.

Reports contain bounded identifiers, issue codes, operation families, memory
domains, layouts, and blocked execution surfaces. They do not contain raw
exception strings, host paths, source text, command lines, device identifiers,
environment variables, benchmark output, generated code, or backend artifact
contents.

## Consequences

- Specialized accelerator manifests now have a second review layer after schema
  loading.
- TUC can publish negative examples that are expected to be blocked without
  making the overall report fail.
- Overbroad hardware self-description is visible as review evidence before it
  can become a planning or proof narrative.
- The loader remains stable; claim policy lives in a separate review contract.

## References

- [Manifest Claim Review](../docs/MANIFEST_CLAIM_REVIEW.md)
- [Backend Capability Schema](../docs/BACKEND_CAPABILITY_SCHEMA.md)
- [Backend API v0.1](../docs/BACKEND_API.md)
- `schemas/manifest_claim_review_report.v0.schema.json`
- `examples/manifest_claim_review.py`
