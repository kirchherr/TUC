# RFC 0020: Branch Protection Policy

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1

## Summary

TUC defines a required branch protection policy for `main` and expands the CI
job so the required `python` check covers current examples and the baseline
benchmark smoke test.

## Motivation

TUC has reached the point where compiler and backend boundaries are protected by
tests and documentation. The default branch now needs repository-level controls
so those protections cannot be bypassed by accidental direct pushes, missing
checks, force pushes, or branch deletion.

## Decision

Add `docs/BRANCH_PROTECTION.md` and update CI.

Required `main` protection:

- Pull request required.
- At least 1 approval.
- Stale approvals dismissed on new commits.
- Conversation resolution required.
- Linear history required.
- Administrators included or ruleset bypass disabled.
- Strict required checks:
  - `python`
  - `CodeQL`
  - `Dependency Review`
- Force pushes disabled.
- Branch deletion disabled.

The `python` CI job now also runs:

- `examples/triton_metadata_adapter.py`
- `examples/backend_api_v0.py`
- `scripts/benchmark.py --iterations 1 --warmup 0`

## Security Model

The policy uses GitHub repository controls rather than project conventions
alone. It does not add new secrets or tokens.

`OpenSSF Scorecard` remains scheduled/push-only and is not listed as a required
pull-request status check until the workflow exposes a PR-safe check.

## Current Limitation

This change documents and prepares the policy in the repository. Applying it to
GitHub requires repository admin rights through the GitHub UI, GitHub CLI, or
GitHub API. The current local environment has no `gh` executable and no
available GitHub API token.

## Follow-Up

1. Apply the policy in GitHub repository settings.
2. Add CODEOWNERS and maintainer teams before requiring CODEOWNERS review.
3. Add signed-commit requirements once contributor signing guidance exists.
4. Add merge queue once CI load justifies it.
