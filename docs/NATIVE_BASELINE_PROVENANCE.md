# Native Baseline Provenance Report

Native Baseline Provenance Report is a diagnostic artifact for reviewing which
native implementation is proposed as the comparison baseline for a future
performance proof.

It does not run benchmarks, execute backend artifacts, access devices, inspect
host hardware, discover plugins, load dynamic libraries, run subprocesses,
store raw benchmark output, store native code, or claim native performance
parity.

## Contract

- Report schema: `schemas/native_baseline_provenance_report.v0.schema.json`
- Report schema version: `tuc.native_baseline_provenance_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_native_baseline_provenance_report(proposal_name, baselines=())`
- Dump API: `dump_native_baseline_provenance_report(report)`
- Example: `examples/native_baseline_provenance.py`
- Tests: `tests/test_native_baseline_provenance_report.py`
- Schema tests: `tests/test_native_baseline_provenance_schema.py`

The report is not a native performance proof. It records provenance metadata
needed before maintainers can decide whether future benchmark comparisons are
meaningful.

## Baseline Fields

Each baseline entry is data-only and bounded:

- `baseline_id`: stable identifier for the native baseline candidate
- `workload_scope_id`: workload or shape-family scope for the comparison
- `implementation_kind`: `vendor_library`, `vendor_sample`,
  `hand_optimized_kernel`, or `framework_compiler`
- `target_platform_id`: stable target-platform identifier
- `source_provenance_id`: stable identifier for source provenance, not a path
- `toolchain_id`: stable toolchain identifier
- `reproducibility_status`: one of `not_reproduced`,
  `documented_not_executed`, `reproduced_outside_tuc`, or `reproduced_by_ci`
- `artifact_digest_status`: `not_supplied` or `supplied`

The report intentionally accepts identifiers, not host paths, command lines,
environment variables, raw output, backend binaries, or device details.

## Security Boundary

The report must not include raw benchmark output, raw timing samples, host
paths, environment variables, hardware serials, device identifiers, generated
artifacts, plugin entrypoints, backend binaries, dynamic-library paths, cache
paths, native code, shell commands, or backend artifact contents.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not execute backend code and does not load benchmark artifacts.
It is a provenance review surface only.

## Current Status

The current report can identify candidate native baselines and keep the
performance proof blocked until reproducible native comparison evidence exists.

`native_baseline_ready` is always false in v0. A future RFC may define a richer
native benchmark artifact and comparison contract, but this report does not.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- native baseline comparison evidence
- benchmark artifact evidence
- raw benchmark result ingestion
- executable backend benchmarking without a dedicated security RFC
- device access, generated-artifact execution, dynamic-library loading, or
  subprocess execution as part of proof review
