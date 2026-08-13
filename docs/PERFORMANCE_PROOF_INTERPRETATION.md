# Performance Proof Interpretation Report

Performance Proof Interpretation is the data-only gate after
[Performance Proof Readiness](PERFORMANCE_PROOF_READINESS.md).

A passing readiness report means the current proof slice has complete review
metadata. It does not mean native performance has been measured, interpreted, or
proven. The interpretation report keeps that boundary explicit.

It does not run benchmarks, ingest raw benchmark output, parse raw timing
samples, access devices, inspect host hardware, execute backend artifacts,
execute generated code, discover plugins, load dynamic libraries, run
subprocesses, or claim native performance parity.

## Contract

- Boundary contract: `performance_proof_boundary.blocking.v0`
- Report schema version: `tuc.performance_proof_interpretation_report.v0`
- Schema: `schemas/performance_proof_interpretation_report.v0.schema.json`
- API: `build_performance_proof_interpretation_report(...)`
- Dump API: `dump_performance_proof_interpretation_report(report)`
- Example: `examples/performance_proof_interpretation.py`
- Golden: `tests/golden/proofs/performance_proof_interpretation_report.json`
- Tests: `tests/test_performance_proof_interpretation.py`

## Meaning

The report records:

- whether Performance Proof Readiness passed;
- how many readiness issues remain;
- which measurement-interpretation artifacts have been accepted;
- whether interpretation metadata is complete;
- the same blocked native-performance claim boundary as readiness.

The current Kernel Ingress report intentionally has
`readiness_ready = true` and `performance_proof_interpretation_ready = false`.
That is the desired state: TUC has complete readiness metadata, but it has not
interpreted accepted measurement artifacts as native performance proof.

## Security Boundary

The report accepts only bounded artifact IDs. It must not contain host paths,
URLs, raw benchmark output, raw timing samples, command lines, environment
variables, device identifiers, hardware serials, backend binaries, generated
code, native source, dynamic-library paths, plugin entrypoints, or execution
permission.

## Still Blocked

These remain blocked after this report exists:

- claiming native performance parity;
- claiming 100 percent native performance;
- claiming a fixed percentage of CUDA, HIP, vendor-library, or hand-optimized
  kernel performance;
- claiming near-native performance without accepted measurement interpretation;
- treating readiness metadata as benchmark evidence;
- treating benchmark artifact inventory as benchmark interpretation;
- hiding planner overhead inside execution timing;
- executing backend artifacts or device code as part of proof review.
