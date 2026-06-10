# Performance Proof Readiness Report

Performance Proof Readiness is a deterministic review report for future native
performance proof proposals.

It does not run benchmarks, ingest benchmark artifacts, access devices, inspect
host hardware, execute backend artifacts, execute generated code, discover
plugins, load dynamic libraries, run subprocesses, or claim native performance
parity.

The readiness report does not access devices.
The readiness report does not execute backend artifacts.
The readiness report does not claim native performance parity.

## Contract

- Boundary contract: `performance_proof_boundary.blocking.v0`
- Report schema version: `tuc.performance_proof_readiness_report.v0`
- Evidence type: `PerformanceProofReadinessEvidence`
- API: `build_performance_proof_readiness_report(proposal_name, evidence)`
- Assertion API: `assert_performance_proof_readiness(proposal_name, evidence)`
- Dump API: `dump_performance_proof_readiness_report(report)`
- Required evidence IDs: `PERFORMANCE_PROOF_REQUIRED_EVIDENCE`
- Blocked claims: `PERFORMANCE_PROOF_BLOCKED_CLAIMS`
- Example: `examples/performance_proof_readiness.py`
- Golden: `tests/golden/proofs/performance_proof_readiness_report.json`
- Tests: `tests/test_performance_proof_readiness.py`

The report is ready only when every required evidence ID is present.

## Required Evidence

The readiness report tracks:

- performance proof RFC
- benchmark methodology
- native baseline provenance
- versioned toolchain environment
- workload scope
- correctness goldens
- native baseline comparison
- leaky-abstraction report
- planner-overhead report
- break-even workload-size report
- runtime-plan goldens
- compiler decision-report goldens
- benchmark report schema
- benchmark report artifacts
- executable backend security review

Missing evidence keeps native performance claims blocked.

The current diagnostic CPU baseline report schema is
`schemas/baseline_benchmark_report.v0.schema.json`. It can satisfy only the
existence of a bounded report schema for the baseline harness. It does not
satisfy native baseline comparison, planner-overhead report,
leaky-abstraction report, benchmark report artifacts, or executable backend
security review.

The current diagnostic workload scope report schema is
`schemas/workload_scope_report.v0.schema.json`. It can satisfy only the
existence of a bounded workload-scope contract. It does not satisfy benchmark
methodology, native baseline comparison, benchmark artifacts, execution timing,
or native performance parity.

The current diagnostic benchmark methodology report schema is
`schemas/benchmark_methodology_report.v0.schema.json`. It can satisfy only the
existence of a bounded benchmark methodology contract. It does not run
benchmarks, load benchmark artifacts, validate raw native output, or prove
native performance parity.

The current diagnostic toolchain environment report schema is
`schemas/toolchain_environment_report.v0.schema.json`. It can satisfy only the
existence of a bounded versioned toolchain environment contract. It does not
inspect the host, read environment variables, run discovery commands, access
devices, or prove native performance parity.

The current diagnostic planner-overhead report schema is
`schemas/planner_overhead_report.v0.schema.json`. It can satisfy only the
existence of a bounded planner phase-separation report. It does not satisfy
break-even workload-size evidence, execution timing evidence, native baseline
comparison, or native performance parity.

The current diagnostic break-even workload-size report schema is
`schemas/break_even_workload_size_report.v0.schema.json`. It can satisfy only
the existence of a bounded break-even workload-size metadata contract. It does
not run benchmarks, load benchmark artifacts, ingest raw timing samples, or
prove native performance parity.

The current diagnostic leaky-abstraction report schema is
`schemas/leaky_abstraction_report.v0.schema.json`. It can satisfy only the
existence of a bounded HAC-IR boundary review report. It does not satisfy
native baseline comparison, benchmark artifacts, or native performance parity.

The current diagnostic native baseline provenance report schema is
`schemas/native_baseline_provenance_report.v0.schema.json`. It can satisfy only
the existence of a bounded native baseline provenance contract. It does not
satisfy native baseline comparison, benchmark report artifacts, execution
timing, or native performance parity.

The current diagnostic native baseline comparison report schema is
`schemas/native_baseline_comparison_report.v0.schema.json`. It can satisfy only
the existence of a bounded native comparison metadata contract. It does not
load benchmark artifacts, parse raw benchmark output, store timing samples, or
prove native performance parity.

The current diagnostic benchmark artifact manifest report schema is
`schemas/benchmark_artifact_manifest_report.v0.schema.json`. It can satisfy only
the existence of a bounded benchmark artifact inventory contract. It does not
load benchmark artifacts, satisfy benchmark result acceptance, validate raw
native output, or prove native performance parity.

The current diagnostic executable backend security review report schema is
`schemas/executable_backend_security_review_report.v0.schema.json`. It can
satisfy only the existence of a bounded executable-surface security review
metadata contract. It does not execute backend artifacts, access devices, load
dynamic libraries, run subprocesses, discover plugins, or approve native
performance parity.

## Blocked Claims

The v0 report explicitly blocks:

- native performance parity
- 100 percent native performance
- fixed vendor performance percentages
- near-native claims without a predefined threshold
- hidden planner overhead inside execution time
- transfer estimates treated as measured hardware performance
- hardware-specific HAC-IR knobs

These blocked claims mirror the
[Performance Proof Boundary](PERFORMANCE_PROOF_BOUNDARY.md).

## Security Boundary

The readiness report accepts only explicit evidence IDs and booleans. It must
not include raw benchmark output, raw timing samples, host paths, environment
variables, hardware serials, device identifiers, generated artifacts, plugin
entrypoints, backend binaries, dynamic-library paths, cache paths, or backend
artifact contents.

The readiness report must not include raw benchmark output.

Unknown evidence IDs and duplicate evidence IDs fail closed.

The report is not a benchmark schema and is not a benchmark result format. A
future benchmark report schema must be reviewed separately before benchmark
artifacts can become proof evidence.

The readiness report is also not a native baseline provenance report. Native
baseline candidates are tracked by
[Native Baseline Provenance Report](NATIVE_BASELINE_PROVENANCE.md), which is
data-only and remains claim-blocked in v0.

The readiness report is not a native baseline comparison report. Native
comparison metadata is tracked by
[Native Baseline Comparison Report](NATIVE_BASELINE_COMPARISON_REPORT.md), which
is data-only and remains separate from raw benchmark values.

The readiness report is not a benchmark artifact manifest. Benchmark report
artifact inventory is tracked by
[Benchmark Artifact Manifest Report](BENCHMARK_ARTIFACT_MANIFEST.md), which is
data-only and remains separate from benchmark result validation.

The readiness report is not a workload scope report. Workload boundaries are
tracked by [Workload Scope Report](WORKLOAD_SCOPE_REPORT.md), which is
data-only and remains separate from benchmark methodology and execution.

The readiness report is not a benchmark methodology report. Measurement policy
is tracked by
[Benchmark Methodology Report](BENCHMARK_METHODOLOGY_REPORT.md), which is
data-only and remains separate from benchmark execution and raw timing samples.

The readiness report is not a toolchain environment report. Versioned toolchain
inventory is tracked by
[Toolchain Environment Report](TOOLCHAIN_ENVIRONMENT_REPORT.md), which is
data-only and remains separate from host discovery.

The readiness report is not a break-even workload-size report. Break-even
metadata is tracked by
[Break-Even Workload Size Report](BREAK_EVEN_WORKLOAD_SIZE_REPORT.md), which is
data-only and remains separate from raw timing samples.

The readiness report is not an executable backend security review report.
Executable-surface security evidence is tracked by
[Executable Backend Security Review Report](EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md),
which is data-only and remains separate from execution permission.

## Evidence

The current golden report intentionally remains blocked:

```text
tests/golden/proofs/performance_proof_readiness_report.json
```

This makes the current roadmap state explicit: TUC has a performance proof
boundary and a readiness report, but no native performance proof proposal has
supplied the required evidence.

## Still Blocked

These remain blocked after this report exists:

- claiming native performance parity
- claiming 100 percent native performance
- claiming a fixed percentage of CUDA, HIP, vendor-library, or hand-optimized
  kernel performance
- claiming near-native performance without a predefined threshold
- hiding planner overhead inside execution timing
- treating transfer-cost estimates as measured hardware performance
- executing backend artifacts or device code as part of proof review
- adding hardware-specific performance knobs to HAC-IR
