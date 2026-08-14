# Objective Delta Reproduction Kit

The Objective Delta Reproduction Kit turns TUC's installed portable-compute
proof into a bounded release artifact that another researcher can replay with
one installed command.

## Research Question

Can TUC package the complete fixed Objective Delta experiment as immutable
plain data, reproduce it through an installed wheel without repository imports,
and emit a deterministic receipt that can later be reviewed as external
evidence?

For release-side construction and replay, the answer is **PASS**. Independent
organizational reproduction remains pending until a third party returns a
receipt produced in its own environment.

## Artifact Set

The release workflow builds and uploads:

```text
tuc-objective-delta-reproduction-kit-v0.zip
tuc-objective-delta-reproduction-receipt.v0.json
```

The ZIP contains exactly five stored, regular, non-executable members:

```text
manifest.json
source_intent.v0.json
external_systolic.v0.json
external_vector.v0.json
expected_report.json
```

`manifest.json` binds every payload path, role, media type, byte length, and
SHA-256 digest. It also binds the portable-compute proof contract, public API,
archive policy, blocked claims, and the absence of executable content.

## Reproduction

After installing the matching TUC wheel and obtaining the release kit:

```bash
tuc-reproduce-portable-compute \
  tuc-objective-delta-reproduction-kit-v0.zip \
  > objective-delta-reproduction-receipt.json
```

The command:

1. validates the archive path, size, central-directory cardinality and order;
2. rejects duplicate, encrypted, compressed, executable, non-regular, extra,
   oversized, reordered, or metadata-drifted members;
3. parses the bounded manifest and verifies every payload digest and size;
4. validates the embedded expected proof report;
5. projects only the three fixed input JSON files into an internal temporary
   directory without extracting the archive;
6. runs the existing `tuc.portable_compute` proof through trusted prototype
   executors;
7. requires the observed report to equal the embedded expected report byte for
   byte; and
8. emits a closed metadata-only reproduction receipt.

The receipt binds the kit, manifest, expected report, observed report, package
identities, trusted executor sequence, correctness, backend equivalence,
fallback count, and layout-conversion count.

## Deterministic Construction

Repository and release builds use:

```bash
python scripts/build_portable_compute_reproduction_kit.py \
  --consumer integration/objective_delta \
  --output dist/tuc-objective-delta-reproduction-kit-v0.zip
```

The builder uses an exact member order, the ZIP epoch timestamp, stored members,
empty comments and extras, Unix regular-file metadata, mode `0644`, canonical
JSON, and no ZIP64. Repeated builds from the same audited payload bytes must be
byte-identical. The v0 golden digest is recorded in
`tests/test_portable_compute_reproduction.py`.

## Release Binding

`.github/workflows/release-artifacts.yml` builds the kit after the Python
distributions, creates a clean virtual environment, installs the wheel, runs
the installed reproduction CLI, and compares the receipt byte for byte with
the reviewed golden. GitHub OIDC artifact attestations cover both kit and
receipt before `SHA256SUMS` is written.

Consumers should verify checksums and GitHub attestations before replay. These
controls bind an artifact to TUC's release workflow; they do not make the
maintainer-run receipt independent evidence.

## Security Boundary

- The archive is data-only and contains no Python, shared library, command,
  plugin entry point, generated code, device path, runtime handle, or source
  text.
- The verifier never calls `extract`, imports archive members, loads native
  libraries, accesses devices or networks, or executes subprocesses.
- ZIP members are read only after bounded central-directory validation.
- Public CLI rejection is a fixed source-free error that omits paths and
  archive content.
- Runtime tensors remain internal and are not serialized.
- Package source-plan identity remains separate from the fixed trusted
  `systolic-sim -> vector-sim` projection.
- The kit cannot grant package execution permission or expand accepted Source
  Intent.

## Relation To Objective Beta

Objective Beta's Reproducibility Capsule replays repository Golden Evidence
without compiler or runtime execution. The Objective Delta kit answers a
different question: it packages one bounded live semantic experiment and
re-executes it through an installed wheel. Both remain useful and neither
subsumes the other.

## Claim Boundary

This work proves deterministic kit construction, installed release-side replay,
and a portable receipt format. It does not prove:

- that an independent person or organization has reproduced the result;
- arbitrary Source Intent, source parsing, graphs, shapes, inputs or packages;
- external package code, plugins, native backends or physical devices;
- wheel or source-distribution byte reproducibility;
- native performance parity; or
- Level 5 adoption.

An external reproduction claim requires a separately reviewed receipt and
provenance from a party outside the TUC release workflow.

Decision: `rfcs/0293-objective-delta-reproduction-kit.md`.
