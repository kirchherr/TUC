# Branch Protection Policy

This policy defines the required protection settings for TUC's default branch.
It is intentionally strict because TUC is a compiler project and every merge can
change the trust boundary for source parsing, IR validation, backend selection,
runtime planning, or supply-chain automation.

## Protected Branch

Protect:

```text
main
```

If the repository default branch is renamed, apply the same policy to the new
default branch before deleting or unprotecting `main`.

## Required Pull Request Rules

Enable:

- Require a pull request before merging.
- Require at least 1 approving review.
- Dismiss stale pull request approvals when new commits are pushed.
- Require review from Code Owners.
- Require conversation resolution before merging.
- Require linear history.
- Include administrators or prevent bypassing the ruleset.

Do not enable direct pushes to `main`.

## Required Status Checks

Enable strict required status checks, including the branch-up-to-date setting.

Require these pull-request checks:

```text
python
CodeQL
Dependency Review
```

`python` is the main CI job. It runs linting, typing, unit tests, current
examples, the Runtime Evidence Gate, and a baseline benchmark smoke test.

`CodeQL` and `Dependency Review` are security workflow jobs. `OpenSSF Scorecard`
runs on push and schedule, but not on pull requests, so it should not be a
required PR check until the workflow is changed to provide a PR-safe check.

## Force Push And Deletion Rules

Disable:

- Allow force pushes.
- Allow deletions.

These should stay disabled even for administrators unless the repository is
under explicit recovery procedures.

## Optional Rules For Later

Consider enabling these once contributor tooling is ready:

- Require signed commits.
- Require merge queue.
- Restrict pushes to named maintainer teams.

These are not required in v0 because the repository does not yet define
release signing or maintainer teams.

## GitHub UI Setup

Recommended setup through GitHub rulesets:

1. Open repository settings.
2. Open `Rules` and then `Rulesets`.
3. Create a branch ruleset.
4. Target branch name pattern: `main`.
5. Enable pull request, status check, linear history, force-push, and deletion
   rules as listed above.
6. Add required checks only after the checks have appeared at least once on a
   pull request.
7. Set enforcement to active.

Branch protection rules can also be used when rulesets are unavailable. The
settings should match this document.

## API Automation Note

This repository currently does not store a GitHub API token, and the local
environment does not include the GitHub CLI. Once an admin token or GitHub CLI
session is available, this policy can be applied through GitHub's branch
protection or repository ruleset API.

Do not commit repository admin tokens, personal access tokens, or deploy keys to
automate this.

## Review Cadence

Review this policy whenever:

- A workflow name or job name changes.
- Native compiler code is added.
- Release automation is added.
- CODEOWNERS or maintainer teams are introduced.
- The default branch is renamed.
