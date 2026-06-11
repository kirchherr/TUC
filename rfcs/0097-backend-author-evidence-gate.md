# RFC 0097: Backend Author Evidence Gate

- Status: accepted-for-prototype
- Created: 2026-06-10
- Phase: Gamma

## Summary

Add a CI-facing Backend Author Evidence Gate that composes Manifest Claim Review
and Backend Author Readiness.

## Motivation

Backend author onboarding now has deterministic evidence artifacts, but CI
needs a single smoke gate equivalent to the Runtime Evidence Gate. The gate
should fail when manifest claim review or backend author readiness drifts.

## Decision

Add:

- [Backend Author Evidence Gate](../docs/BACKEND_AUTHOR_EVIDENCE_GATE.md)
- `examples/backend_author_evidence_gate.py`
- golden output at
  `tests/golden/backend_author_readiness/backend_author_evidence_gate.txt`
- focused tests in `tests/test_backend_author_evidence_gate.py`
- a read-only CI workflow step running
  `python examples/backend_author_evidence_gate.py`

## Security Model

The gate is a pure evidence check. It does not add plugin discovery, directory
scanning, dynamic imports of backend modules, dynamic-library loading,
subprocess execution beyond the CI Python process, device access, network
access, JIT execution, generated-artifact execution, secrets, write tokens, or
publishing permissions.

The existing CI workflow already sets `permissions: contents: read`; this gate
does not require broader permissions.

## Consequences

- Backend author evidence is now visible in CI as a dedicated gate.
- Manifest Claim Review and Backend Author Readiness drift will fail fast.
- External backend onboarding gains a practical integration check without
  becoming a plugin system.

## References

- [Backend Author Readiness](../docs/BACKEND_AUTHOR_READINESS.md)
- [Manifest Claim Review](../docs/MANIFEST_CLAIM_REVIEW.md)
- `.github/workflows/ci.yml`
- `examples/backend_author_evidence_gate.py`
