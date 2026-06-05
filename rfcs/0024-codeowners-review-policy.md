# RFC 0024: CODEOWNERS Review Policy

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC adds `.github/CODEOWNERS`, a review policy, and tests that ensure
security-critical compiler, runtime, backend, governance, and release paths stay
owned.

## Motivation

TUC now has compiler IR contracts, backend APIs, release workflows, provenance,
and publishing controls. Those boundaries should not be changed through ordinary
review alone. CODEOWNERS gives GitHub a path-aware review signal that can be
enforced by branch protection.

## Decision

Add `.github/CODEOWNERS` with `@kirchherr` as the initial owner.

Explicitly cover:

- GitHub Actions, Dependabot, package metadata, requirements, and Docker.
- Security, branch protection, release, governance, and contribution policy.
- Compiler, frontend, IR, backend, runtime, manifest, and golden fixture paths.
- RFCs and architecture contract documentation.

Add `docs/REVIEW_POLICY.md` describing owner-review expectations and critical
change classes.

Add `tests/test_codeowners_policy.py` to guard the required path set.

## Security Model

CODEOWNERS is not a standalone security boundary. It must be paired with GitHub
branch protection or rulesets that require Code Owner review.

This change prevents accidental removal of review ownership for critical paths
and documents the questions reviewers must answer before approving changes.

## Limitations

- The initial owner is an individual GitHub account because TUC is not yet in an
  organization with maintainer teams.
- GitHub's Code Owner review requirement must be enabled by a repository admin.
- CODEOWNERS cannot express different approval counts for different paths.

## Follow-Up

1. Enable "Require review from Code Owners" on the `main` branch ruleset.
2. Move ownership to maintainer teams when the project has an organization or
   multiple maintainers.
3. Add stronger policy checks if multiple independent approvals become required.
