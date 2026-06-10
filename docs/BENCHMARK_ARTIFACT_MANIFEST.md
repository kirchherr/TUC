# Benchmark Artifact Manifest Report

Benchmark Artifact Manifest Report is a diagnostic artifact for reviewing which
benchmark report artifacts a future native performance proposal claims to have.

It does not run benchmarks, load benchmark artifacts, execute backend artifacts,
access devices, inspect host hardware, discover plugins, load dynamic
libraries, run subprocesses, store raw benchmark output, store raw timing
samples, store native code, or claim native performance parity.

## Contract

- Report schema: `schemas/benchmark_artifact_manifest_report.v0.schema.json`
- Report schema version: `tuc.benchmark_artifact_manifest_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_benchmark_artifact_manifest_report(proposal_name, artifacts=())`
- Dump API: `dump_benchmark_artifact_manifest_report(report)`
- Example: `examples/benchmark_artifact_manifest.py`
- Tests: `tests/test_benchmark_artifact_manifest_report.py`
- Schema tests: `tests/test_benchmark_artifact_manifest_schema.py`

The report is not a native performance proof. It is a manifest of bounded
artifact references and digests.

## Required Artifact Kinds

The v0 manifest tracks these benchmark artifact kinds:

- `baseline_benchmark_report`
- `native_benchmark_report`
- `native_baseline_comparison_report`

Each entry contains:

- `artifact_id`: stable identifier for the artifact
- `artifact_kind`: one of the required artifact kinds
- `schema_version`: schema version claimed by the artifact
- `artifact_digest`: `not_supplied` or a `sha256:` digest
- `storage_scope`: `repository_golden`, `ci_artifact`, `release_artifact`, or
  `review_attachment`

The report intentionally accepts identifiers and digests, not host paths,
download URLs, command lines, environment variables, raw output, backend
binaries, or device details.

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, hardware serials, device identifiers, generated
artifacts, plugin entrypoints, backend binaries, dynamic-library paths, cache
paths, native code, shell commands, or backend artifact contents.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not execute backend code and does not load benchmark artifacts.
It is an inventory review surface only.

## Current Status

The current report can show which benchmark artifacts are still missing and
which artifact references lack SHA-256 digests.

`benchmark_artifact_manifest_complete` means only that the manifest contains all
required artifact kinds with digests. It does not mean TUC has accepted a native
performance claim.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- benchmark artifact acceptance as proof
- raw benchmark result ingestion
- native benchmark execution
- executable backend benchmarking without a dedicated security RFC
- device access, generated-artifact execution, dynamic-library loading, or
  subprocess execution as part of proof review
