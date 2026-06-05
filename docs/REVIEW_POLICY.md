# Review Policy

TUC uses pull request review, CODEOWNERS, RFCs, and CI checks to protect compiler
correctness, security boundaries, and release integrity.

## Required Repository Setting

The default branch ruleset must enable:

- Require a pull request before merging.
- Require review from Code Owners.
- Require conversation resolution before merging.
- Dismiss stale approvals when new commits are pushed.
- Require the documented status checks from
  [Branch protection policy](BRANCH_PROTECTION.md).

CODEOWNERS only requests and enforces reviews when GitHub branch protection or
rulesets enable Code Owner review.

## Current Owners

The initial owner for all protected areas is:

```text
@kirchherr
```

Future maintainer teams should replace individual ownership where possible, for
example `@tuc-org/tuc-maintainers`, once the repository is moved into an
organization or maintainer teams exist.

## Critical Change Classes

These changes require explicit owner review:

- GitHub Actions, Dependabot, release workflows, branch rules, or publishing.
- Dockerfiles, dependency manifests, package metadata, or build-system changes.
- Parser, frontend metadata, IR model, IR dumps, lowering, or dialect contracts.
- Backend capability schemas, backend conformance, manifests, or simulator
  behavior.
- Runtime partitioning, transfer-cost modeling, runtime plans, or generated
  artifact handling.
- Security baseline, release governance, branch protection, or vulnerability
  handling.
- RFCs that change compatibility, architecture, backend contracts, governance,
  or release policy.

## Review Expectations

Owner review should answer:

- Which trust boundary changed?
- Which invariants are validated before lowering or publishing?
- What resource budget prevents graph, metadata, artifact, or CI abuse?
- Does the change add imports, subprocesses, dynamic libraries, network access,
  generated-code execution, or filesystem writes?
- Are diagnostics bounded and free of secrets or misleading fallbacks?
- Which tests or golden artifacts prove the intended behavior?

## Merge Policy

A maintainer may merge when:

- Required checks pass.
- Required owner review is complete.
- Security-relevant questions are answered in the PR or linked RFC.
- Any temporary exception is documented as follow-up work.

Do not merge by bypassing review except during a documented incident recovery.

## CODEOWNERS Maintenance

CODEOWNERS must be updated when:

- New compiler, runtime, backend, parser, or release directories are added.
- Maintainer teams are introduced.
- GitHub workflow names or release paths change.
- A new externally consumed API or artifact format is introduced.
