# RFC 0022: Release Governance Hardening

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC hardens release governance by pinning release workflow actions to reviewed
commit SHAs, adding a test that rejects unpinned release actions, and defining
the required GitHub tag-ruleset and PyPI Trusted Publishing policy.

## Motivation

Release workflows are a compiler supply-chain boundary. Even if the compiler
code is correct, a mutable action tag, forged release tag, or long-lived
publishing secret can compromise downstream users.

## Decision

Pin release workflow actions to reviewed SHAs:

- `actions/checkout` at `v6.0.2`
- `actions/setup-python` at `v6.2.0`
- `actions/attest` at `v4.1.0`
- `actions/upload-artifact` at `v7.0.1`

Add a test to ensure `.github/workflows/release-artifacts.yml` does not use
mutable `actions/*@v...` refs.

Add `docs/RELEASE_GOVERNANCE.md` covering:

- `v*` release tag ruleset.
- Maintainer-only tag creation.
- Blocked tag updates and deletions.
- GitHub `pypi` environment with required reviewers.
- PyPI Trusted Publishing through OIDC instead of stored tokens.

## Security Model

The repo-level controls prevent accidental drift in the workflow itself. GitHub
admin controls are still required for tag creation and publishing approval.

No publishing secrets are introduced.

## Limitations

- GitHub rulesets and environments cannot be activated from this repository
  change alone.
- PyPI Trusted Publishing must be configured by a PyPI project administrator.
- SHA pinning requires deliberate periodic updates.

## Follow-Up

1. Apply the `v*` tag ruleset in GitHub.
2. Create the `pypi` GitHub environment once publishing is planned.
3. Add a publishing workflow only after maintainer approval policy is active.
4. Add CODEOWNERS and maintainer teams before requiring owner review.
