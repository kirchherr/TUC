# Leaky Abstraction Report

Leaky Abstraction Report is a diagnostic artifact for reviewing whether
hardware-specific performance facts stay outside HAC-IR.

It does not run benchmarks, execute backend artifacts, access devices, discover
plugins, load dynamic libraries, inspect host hardware, store raw benchmark
output, or claim native performance parity.

## Contract

- Report schema: `schemas/leaky_abstraction_report.v0.schema.json`
- Report schema version: `tuc.leaky_abstraction_report.v0`
- Artifact status: `diagnostic_only`
- Claim boundary: `performance_proof_boundary.blocking.v0`
- Performance claim status: `blocked`
- API: `build_leaky_abstraction_report(hac_ir, performance_facts=())`
- Dump API: `dump_leaky_abstraction_report(report)`
- Example: `examples/leaky_abstraction_report.py`
- Tests: `tests/test_leaky_abstraction_report.py`
- Schema tests: `tests/test_leaky_abstraction_report_schema.py`

The report is not a native performance proof. It is a HAC-IR boundary review
artifact.

## Boundary Rule

HAC-IR may carry hardware-independent compute intent, deterministic compiler
facts, and abstract planning constraints.

Hardware-specific performance facts must stay in one of these homes:

- `backend_capability`
- `hs_ir`
- `runtime_plan`
- `compiler_decision_report`
- `backend_implementation`
- `benchmark_artifact`
- `security_rfc`

The report checks the existing executable guard
`HAC_IR_FORBIDDEN_HARDWARE_ATTRIBUTES` and reports any forbidden attribute that
entered HAC-IR.

## Security Boundary

The report must not include raw benchmark output, host paths, hardware serials,
device identifiers, plugin entrypoints, backend artifacts, generated code,
dynamic-library paths, cache paths, environment variables, or native
performance parity fields.

The schema is fail-closed with `additionalProperties: false` on every object.

The report does not execute backend code and does not load benchmark artifacts.

## Current Status

The current report can show that the compiled HAC-IR module preserves the
known hardware-neutrality guard. It still keeps native performance claims
blocked because native baseline provenance, benchmark artifacts, and full
performance evidence are not present.

## Still Blocked

These remain blocked after this report exists:

- native performance parity claims
- 100 percent native performance claims
- near-native claims without thresholds
- adding hardware-specific performance knobs to HAC-IR
- treating backend implementation details as HAC-IR semantics
- using diagnostic boundary review as benchmark evidence
- executable backend benchmarking without a dedicated security RFC
