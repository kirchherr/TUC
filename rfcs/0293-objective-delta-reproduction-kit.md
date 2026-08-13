# RFC 0293: Objective Delta Reproduction Kit

Status: Accepted

## Summary

Publish Objective Delta as a deterministic, data-only ZIP artifact and add an
installed public replay command that emits a closed digest-bound receipt.
Build, replay, compare, attest, checksum, and upload the kit in the existing
release workflow while keeping independent reproduction as an unfulfilled
external-evidence claim.

## Motivation

Objective Delta proves the complete bounded portable-compute path through a
built wheel and a copied external consumer. That validates the installed API,
but reproducing the experiment still requires a repository checkout and
knowledge of several fixture paths. A researcher should receive one immutable
artifact, one wheel, and one command.

The artifact must not become a source archive, plugin package, generic ZIP
extractor, or executable bundle. Release CI reproducing its own proof must also
not be mislabeled as independent validation.

## Decision

Add:

- `tuc.portable_compute_reproduction`;
- installed command `tuc-reproduce-portable-compute`;
- deterministic builder
  `scripts/build_portable_compute_reproduction_kit.py`;
- installed-wheel isolation verifier
  `scripts/verify_external_portable_compute_reproduction.py`;
- closed kit-manifest and reproduction-receipt schemas;
- deterministic manifest and receipt goldens; and
- release construction, installed replay, receipt comparison, attestation,
  checksum, and upload steps.

The kit contains only a manifest, the exact Objective Delta Source Intent, the
two exact data-only backend packages, and the exact expected metadata report.
The verifier does not extract the archive. It reads only an exact allowlist
after checking central-directory and Unix file metadata.

## Archive Contract

Version zero requires:

- exact five-member count and canonical member order;
- flat ASCII names from a fixed allowlist;
- no duplicates, directories, encryption, compression, ZIP64, comments or
  extra fields;
- fixed 1980 ZIP timestamps;
- Unix regular-file type, mode `0644`, and no executable bits;
- per-member, aggregate-expanded, archive and JSON resource limits; and
- manifest-bound SHA-256 and byte length for every payload.

The strict metadata contract makes the release kit deterministic and sharply
reduces parser and archive ambiguity.

## Replay Contract

After archive validation, TUC writes only the three fixed input JSON payloads
to a private temporary directory and invokes the existing bounded portable
compute API. The observed report must equal the expected report byte for byte
and satisfy the portable-compute report assertion independently.

The receipt is deterministic and metadata-only. It binds kit and manifest
digests, expected and observed report digests, package identities, trusted
executor sequence, fallback and layout conversion counts, reference
correctness, backend equivalence, and all blocked claim flags.

`independent_reproduction_claim` is always `false` in v0. Independent evidence
requires separate provenance and maintainer admission rather than a caller-
controlled command-line switch.

## Security Invariants

- No archive member is executed, imported, dynamically loaded or extracted.
- No package discovery, entry point, subprocess, native artifact, device,
  network, environment capture or external runtime handle is admitted.
- Archive and JSON parsing are bounded before semantic execution.
- Duplicate names and duplicate JSON keys fail closed.
- Output construction refuses pre-existing paths and writes only one explicit
  ZIP chosen by the trusted builder caller.
- The public replay CLI emits a fixed source-free rejection.
- Source payloads and runtime tensor values do not enter the receipt.
- The external package plan and trusted in-repository projection remain
  separate proof identities.
- The release job keeps existing least-privilege permissions and adds no action
  or dependency.

## Release Decision

The existing release job:

1. builds the kit from reviewed Objective Delta payloads;
2. installs the freshly built wheel in a clean virtual environment;
3. invokes the installed replay command;
4. compares its receipt with the repository golden;
5. requests GitHub OIDC provenance attestations for kit and receipt;
6. includes both in `SHA256SUMS`; and
7. uploads both in the release artifact bundle.

PyPI publishing remains limited to wheel and source distribution.

## Alternatives Rejected

### Ship a repository snapshot

This is broad, mutable, and unnecessarily exposes examples, tests and source
to the reproduction boundary.

### Put a Python replay script in the ZIP

That creates executable archive content and a second code-distribution path.
Replay belongs to the reviewed installed wheel.

### Extract the ZIP before validation

This creates path traversal, overwrite, symlink and filesystem ambiguity. The
verifier reads exact members directly and projects fixed payloads itself.

### Claim independent reproduction from release CI

The producer rerunning its own experiment is valuable release evidence but is
not independent scientific validation.

### Extend Objective Beta's capsule

Beta intentionally performs metadata-only offline replay without compiler or
runtime execution. Delta needs a live installed semantic replay and therefore
remains a separate contract.

## Consequences

TUC releases can carry a compact, attestable experiment that a third party can
replay without a repository checkout. TUC still needs a real external
reproducer and reviewed external provenance before claiming independent
reproduction or adoption. Arbitrary source, backend code, native hardware,
performance parity, and reproducible Python distributions remain open proof
classes.
