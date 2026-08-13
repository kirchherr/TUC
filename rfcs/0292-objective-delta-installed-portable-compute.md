# RFC 0292: Objective Delta Installed Portable Compute

Status: Accepted

## Summary

Add a narrow installed public proof that composes bounded Source Intent, two
external data-only backend packages, capability planning, an explicit layout
conversion, fixed trusted heterogeneous execution, independent reference
correctness, and backend equivalence into one digest-only PASS report.

## Motivation

Objective Gamma proves that an external consumer can validate and plan a
backend package through a built TUC wheel. The execution portfolios prove that
external package identities can be projected to trusted prototype executors
and compared against reference semantics. Those proofs are individually
strong, but they leave a distribution-level question open: does the complete
portable-compute path work through a stable installed interface outside the
repository?

Objective Delta answers that question without admitting external executable
code or broadening TUC into a plugin loader.

## Decision

Add:

- public module `tuc.portable_compute`;
- console entry point `tuc-prove-portable-compute`;
- closed report schema `tuc.portable_compute_proof_report.v0`;
- standalone consumer `integration/objective_delta`;
- installed-wheel verifier
  `scripts/verify_external_portable_compute_consumer.py`; and
- built-wheel integration coverage in `tests/test_portable_compute.py`.

The v0 contract admits exactly one reviewed Source Intent shape and exactly the
two reviewed external backend package identities. Package order is
canonicalized. Planning must produce `external-systolic -> external-vector`
without fallback and with one `blocked -> row_major` layout conversion.

Execution uses only the existing fixed trusted projection to
`systolic-sim -> vector-sim`. The proof requires independent reference
correctness and equivalence against `reference-cpu`. Its public report contains
metadata and digests, never source payloads or raw tensor values.

## Security Invariants

- All public inputs are explicit regular non-symlink files with bounded byte
  size and exact JSON structure.
- Backend package identity and content digest are both pinned before planning.
- No package discovery, dynamic import, executable entry point, external
  subprocess mapping, native code, generated artifact, device, or network
  access is admitted.
- The source plan and trusted projection remain separately visible in evidence.
- Internal proof inputs are fixed and are never accepted from the external
  consumer or serialized into the report.
- The copied consumer has an exact file allowlist and pinned Python source
  digest; the verifier is not a general external code runner.
- The installed module must resolve outside the repository source tree.
- CLI rejection output is fixed and source-free.
- Correctness and backend equivalence are mandatory; no execution-only PASS is
  possible.
- Native and performance claims remain explicitly blocked.

## Verification

- `tests/test_portable_compute.py`
- `tests/test_public_backend_integration.py`
- `tests/test_source_intent_backend_package_portfolio.py`
- `tests/test_backend_package_execution_portfolio.py`
- `.github/workflows/ci.yml`
- `.github/workflows/release-artifacts.yml`

## Alternatives Rejected

### Reuse an in-repository example as the public API

Examples are not a stable distribution contract and can accidentally depend on
source-tree imports.

### Execute implementations supplied by backend packages

This would introduce an untrusted-code and native-artifact security problem
that Objective Delta neither needs nor claims to solve.

### Accept arbitrary Source Intent or runtime tensors

That would expand parser, shape, memory, and denial-of-service surfaces before
the fixed end-to-end hypothesis is proven. Version zero remains deliberately
bounded.

### Report only final output equality

That would hide source-plan identity, trusted projection, fallback, placement,
layout conversion, and execution evidence. The proof instead binds these
surfaces through a closed digest-only report.

## Consequences

TUC now has Level 4 installed integration evidence for one complete portable
compute slice: neutral intent plus external capability data can drive trusted
heterogeneous execution and preserve reference semantics through a built
distribution. General source admission, executable backend isolation, native
hardware, performance parity, package publication, and third-party adoption
remain open research and adoption milestones.
