# Native Baseline Comparison Report

Native Baseline Comparison Report is a diagnostic artifact for reviewing whether
future benchmark evidence has an explicit comparison between a TUC baseline
artifact and a native benchmark artifact.

It does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, inspect host hardware, access devices, execute
backend artifacts, run subprocesses, or claim native performance parity.

## Contract

- Report schema: `schemas/native_baseline_comparison_report.v0.schema.json`
- Report schema version: `tuc.native_baseline_comparison_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_native_baseline_comparison_report(proposal_name, comparisons=())`
- Dump API: `dump_native_baseline_comparison_report(report)`
- Example: `examples/native_baseline_comparison_report.py`
- Tests: `tests/test_native_baseline_comparison_report.py`
- Schema tests: `tests/test_native_baseline_comparison_schema.py`

The report is not a native performance proof. It records explicit comparison
metadata that future benchmark artifacts can reference.

## Comparison Fields

Each comparison entry is data-only and bounded:

- `comparison_id`: stable comparison identifier
- `workload_scope_id`: workload scope being compared
- `baseline_artifact_id`: TUC or reference baseline benchmark artifact ID
- `native_artifact_id`: native benchmark artifact ID
- `comparison_metric_id`: metric identifier, such as median execution time
- `summary_policy_id`: summary policy identifier, such as median/IQR
- `result_status`: `not_measured`, `reported_not_validated`, or `validated_by_ci`
- `comparison_digest`: `not_supplied` or a `sha256:` digest

The report intentionally accepts identifiers, validation status, and digest
status, not raw timing samples, raw native output, benchmark report contents,
host paths, command lines, environment variables, device identifiers, backend
binaries, generated code, or native source contents.

## Security Boundary

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not read or validate benchmark report contents. It is a bounded
review surface for comparison metadata only.

`native_baseline_comparison_ready` means only that at least one bounded
comparison entry is present, every comparison is `validated_by_ci`, and every
comparison supplies a digest. Native performance claims remain blocked in v0.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- fixed vendor performance percentages
- raw benchmark result ingestion
- benchmark artifact loading during proof review
- device access or native benchmark execution
- treating comparison metadata as benchmark proof
- executable backend benchmarking without a dedicated security RFC
