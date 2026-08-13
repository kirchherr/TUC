# RFC 0291: Objective Gamma External Integration

Status: Accepted

## Summary

Promote the existing data-only Backend Integration Package v0 from an
in-repository example to an installed public contract. Add the stable
`tuc.integration` module, the `tuc-backend-verify` console script, a standalone
consumer, and CI/release verification against a built wheel outside the source
tree.

## Motivation

The existing package proof showed that TUC core can validate external
capability data and select the declared backend. It still depended on internal
module paths, an editable project installation, and repository-owned examples.
That is Level 3 validation, but it leaves the Level 4 integration question
partially open: can a backend author use the distributed product boundary?

The answer must be obtained without opening package discovery or executable
plugin surfaces.

## Decision

Add:

- public module `tuc.integration`;
- console entry point `tuc-backend-verify`;
- standalone consumer `integration/objective_gamma`;
- installed-wheel verifier `scripts/verify_external_backend_consumer.py`; and
- a built-wheel integration test in the standard suite already required by CI
  and release verification.

The public API loads, evaluates, asserts, serializes, and emits the existing
Backend Integration Package report. It does not introduce a second schema or
change package semantics.

The verifier creates a temporary environment, force-installs the built wheel,
copies the consumer outside the repository, strips import-path overrides, runs
Python in isolated mode, proves the installed TUC module is outside the source
root, and compares API and CLI output to one byte-stable expected report.

## Security Invariants

- The package remains pure bounded data and contains no executable backend.
- No discovery, package import, entry point loading, device access, network
  access, or runtime execution is added to package evaluation.
- The verifier accepts only explicit regular non-symlink paths and rejects
  symlinks or oversized trees within the copied consumer.
- The executable consumer fixture has an exact file allowlist and pinned source
  digest; the runner is not a general external Python execution facility.
- TUC must resolve from the installed wheel, never from the source root.
- The external consumer imports no TUC internal module.
- CLI rejection output is fixed and cannot disclose untrusted paths, payloads,
  secrets, or parser diagnostics.
- Runtime dependencies come from the already installed hash-locked CI
  environment; the wheel installation uses `--no-deps`.
- A PASS remains capability-and-planning evidence only and grants no execution
  permission.

## Verification

- `tests/test_public_backend_integration.py`
- `tests/test_backend_integration_package.py`
- `tests/test_release_artifacts.py`
- `.github/workflows/ci.yml`
- `.github/workflows/release-artifacts.yml`

## Alternatives Rejected

### Import internal backend modules

This would expose implementation layout as the vendor contract and make
refactoring needlessly breaking.

### Test only the editable checkout

That cannot detect missing wheel modules, missing console entry points, or
accidental dependence on repository import paths.

### Enable executable plugin discovery

That would answer a different and substantially riskier question involving
untrusted code, dependency isolation, native artifacts, and runtime authority.

### Add another evidence schema

The existing deterministic package report already carries the semantic result.
The missing proof is distribution and consumption, so executable CI is the
appropriate verification layer.

## Consequences

TUC now has bounded Level 4 evidence that another backend author can consume
its capability-and-planning interface from a built distribution. Executable
backend admission, native hardware support, performance, publication, and
independent organizational adoption remain open proof classes.
