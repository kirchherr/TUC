# Performance Proof Boundary

TUC's current Objective Alpha proof is a correctness and inspectability proof.
It is not a native performance parity claim.

This boundary exists because a hardware-independent interface can fail in two
ways even when it is mathematically correct:

- the abstraction can leak when hardware-specific optimization details become
  necessary for competitive performance
- runtime planning can cost more time than execution for small or fast workloads

TUC does not currently claim native performance parity, 100 percent native
performance, or a fixed percentage of CUDA, HIP, vendor-library, or
hand-optimized kernel performance.

## Current Claim

The current proof claim is:

```text
Compute intent can remain hardware-independent, flow through capability-driven
runtime planning, and produce correct deterministic results.
```

The current proof claim is not:

```text
TUC matches native vendor performance.
```

## Leaky Abstraction Gate

Before TUC may claim native performance parity, a proposal must show where
hardware-specific details live without contaminating HAC-IR.

The proposal must include:

- explicit workload family and tensor-shape scope
- native baseline implementation and versioned toolchain
- backend capability data used by TUC
- HS-IR/backend-specific choices used by TUC
- which hardware-specific facts are required for performance
- proof that those facts do not enter HAC-IR semantics
- benchmark provenance and reproducibility instructions
- correctness comparison against deterministic reference semantics
- performance comparison against the native baseline
- explanation for every abstraction leak or missing native optimization

Hardware-specific cache behavior, occupancy tuning, launch configuration,
tiling, memory-bank layout, warp/wavefront behavior, vendor intrinsics, and
similar details belong in backend contracts, HS-IR, runtime plans, backend
implementations, or benchmark evidence, not HAC-IR.

If a workload requires a hardware-specific optimization that cannot be expressed
without changing HAC-IR semantics, the performance parity claim fails.

The current [Leaky Abstraction Report](LEAKY_ABSTRACTION_REPORT.md) defines the
diagnostic report contract at
`schemas/leaky_abstraction_report.v0.schema.json`. It checks the current
HAC-IR hardware-leakage guard and records where performance-specific facts must
live outside HAC-IR.

## Workload Scope Gate

Before TUC may claim performance for a workload class, a proposal must define
the workload family and problem-size bounds as review data.

The proposal must include:

- operation family
- shape profile identifier
- dtype policy identifier
- minimum problem size
- maximum problem size
- correctness reference identifier

The current [Workload Scope Report](WORKLOAD_SCOPE_REPORT.md) defines the
diagnostic report contract at
`schemas/workload_scope_report.v0.schema.json`. It records workload boundaries,
but it does not run benchmarks, store tensors, load artifacts, or prove native
performance.

Workload scope reports must not include tensors, host paths, command lines,
environment variables, raw benchmark output, raw timing samples, backend
binaries, generated code, device identifiers, dynamic-library paths, or native
source contents.

## Benchmark Methodology Gate

Before benchmark output can count as future performance-proof evidence, a
proposal must define how measurements are taken and summarized.

The proposal must include:

- measurement clock
- warmup iteration policy
- measurement iteration policy
- statistical summary policy
- runner isolation level
- outlier policy
- reproducibility policy

The current
[Benchmark Methodology Report](BENCHMARK_METHODOLOGY_REPORT.md) defines the
diagnostic report contract at
`schemas/benchmark_methodology_report.v0.schema.json`. It records benchmark
policy choices, but it does not run benchmarks, store timing samples, load
artifacts, or prove native performance.

Benchmark methodology reports must not include host paths, command lines,
environment variables, raw benchmark output, raw timing samples, backend
binaries, generated code, device identifiers, dynamic-library paths, or native
source contents.

## Toolchain Environment Gate

Before benchmark output can be reproduced, a proposal must identify the
versioned toolchain environment used for measurement.

The proposal must include:

- runtime component identifiers
- package or compiler component identifiers
- version identifiers
- provenance identifiers
- digest status for relevant components

The current
[Toolchain Environment Report](TOOLCHAIN_ENVIRONMENT_REPORT.md) defines the
diagnostic report contract at
`schemas/toolchain_environment_report.v0.schema.json`. It records toolchain
component metadata, but it does not inspect the host, read environment
variables, run discovery commands, access devices, or prove native performance.

Toolchain environment reports must not include host paths, command lines,
environment variables, secrets, package-manager output, hardware serials,
device identifiers, dynamic-library paths, backend binaries, generated code, or
native source contents.

## Planner Overhead Gate

Before TUC may claim runtime planning is beneficial for a workload class, a
proposal must measure planning overhead separately from execution time.

The proposal must include:

- graph construction time
- frontend intake time
- lowering time
- runtime planning time
- backend selection time
- artifact generation time, if any
- execution time
- cache hit and cache miss behavior, if caching exists
- break-even workload size where planning overhead is amortized
- small-workload result where planning overhead may dominate

If planning time is greater than execution time for a target workload and no
accepted amortization or caching contract exists, TUC must report that workload
as planner-overhead dominated.

Planner overhead must not be hidden inside execution time.

The current [Planner Overhead Report](PLANNER_OVERHEAD_REPORT.md) defines the
diagnostic report contract at
`schemas/planner_overhead_report.v0.schema.json`. It separates compiler and
runtime-planning phases from execution time, but execution time and break-even
workload size remain explicitly not measured.

## Break-Even Workload Size Gate

Before TUC may claim that planning overhead is amortized for a workload class,
a proposal must identify the scoped break-even workload size as bounded review
data.

The proposal must include:

- workload scope identifier
- planner-overhead report identifier
- execution metric identifier
- amortization policy identifier
- break-even validation status
- break-even problem size
- evidence digest status

The current
[Break-Even Workload Size Report](BREAK_EVEN_WORKLOAD_SIZE_REPORT.md) defines
the diagnostic report contract at
`schemas/break_even_workload_size_report.v0.schema.json`. It records only
break-even metadata, validation status, bounded problem size, and digest status.
It does not run benchmarks, load benchmark artifacts, parse raw benchmark
output, store raw timing samples, or prove native performance.

Break-even workload-size reports must not include host paths, command lines,
environment variables, raw timing samples, raw native output, backend binaries,
generated code, device identifiers, dynamic-library paths, or benchmark report
contents.

## Native Baseline Provenance Gate

Before TUC may compare against a native implementation, a proposal must identify
the native baseline as bounded review data.

The proposal must include:

- workload scope
- baseline implementation kind
- target platform identifier
- source provenance identifier
- toolchain identifier
- reproducibility status
- artifact digest status

The current [Native Baseline Provenance Report](NATIVE_BASELINE_PROVENANCE.md)
defines the diagnostic report contract at
`schemas/native_baseline_provenance_report.v0.schema.json`. It records native
baseline candidate provenance, but it does not run benchmarks, access devices,
load artifacts, or prove native performance.

Native baseline provenance must not include host paths, command lines,
environment variables, raw benchmark output, backend binaries, generated code,
device identifiers, dynamic-library paths, or native source contents.

## Native Baseline Comparison Gate

Before TUC may interpret native benchmark data as comparison evidence, a
proposal must identify the bounded comparison between TUC baseline artifacts and
native benchmark artifacts.

The proposal must include:

- workload scope identifier
- baseline benchmark artifact identifier
- native benchmark artifact identifier
- comparison metric identifier
- summary policy identifier
- validation status
- comparison digest status

The current
[Native Baseline Comparison Report](NATIVE_BASELINE_COMPARISON_REPORT.md)
defines the diagnostic report contract at
`schemas/native_baseline_comparison_report.v0.schema.json`. It records only
comparison metadata, validation status, and digest status. It does not load
benchmark artifacts, parse raw benchmark output, store raw timing samples, or
prove native performance.

Native baseline comparison reports must not include host paths, URLs, command
lines, environment variables, raw timing samples, raw native output, backend
binaries, generated code, device identifiers, dynamic-library paths, or native
source contents.

## Benchmark Artifact Manifest Gate

Before benchmark report artifacts can count as future performance-proof
evidence, a proposal must list those artifacts through a bounded manifest.

The proposal must include:

- baseline benchmark report artifact reference
- native benchmark report artifact reference
- native baseline comparison report artifact reference
- schema version for each artifact
- SHA-256 digest status for each artifact
- storage scope for each artifact

The current
[Benchmark Artifact Manifest Report](BENCHMARK_ARTIFACT_MANIFEST.md) defines
the diagnostic report contract at
`schemas/benchmark_artifact_manifest_report.v0.schema.json`. It records only
artifact identifiers, kinds, schema versions, digests, and storage scopes. It
does not load benchmark artifacts, store raw benchmark output, or accept native
performance claims.

Benchmark artifact manifests must not include host paths, URLs, command lines,
environment variables, raw timing samples, raw native output, backend binaries,
generated code, device identifiers, dynamic-library paths, or native source
contents.

## Executable Backend Security Review Gate

Before TUC may use executable backend behavior, generated artifacts, device
access, dynamic libraries, subprocesses, plugin discovery, native code, network
access, or cache access as performance-proof evidence, a proposal must identify
the accepted security review for each executable surface.

The proposal must include:

- reviewed executable surface
- threat model identifier
- sandbox model identifier
- resource budget identifier
- provenance identifier
- fuzzing, sanitizer, property-test, or negative-test evidence identifier
- maintainer approval status
- security review digest status

The current
[Executable Backend Security Review Report](EXECUTABLE_BACKEND_SECURITY_REVIEW_REPORT.md)
defines the diagnostic report contract at
`schemas/executable_backend_security_review_report.v0.schema.json`. It records
only bounded security review metadata. It does not execute backend artifacts,
access devices, load dynamic libraries, run subprocesses, discover plugins, or
prove native performance.

Executable backend security review reports must not include host paths, command
lines, environment variables, raw benchmark output, raw timing samples, backend
artifact contents, generated code, device identifiers, dynamic-library paths, or
native source contents.

## Required Future Evidence

Any future performance proof must add:

- dedicated performance proof RFC
- benchmark methodology document
- explicit benchmark methodology report
- explicit toolchain environment report
- explicit workload scope report
- native baseline provenance
- explicit native baseline comparison report
- benchmark report schema
- deterministic benchmark fixtures or stored report artifacts
- explicit benchmark artifact manifest
- correctness goldens for every benchmarked workload
- runtime-plan and compiler decision-report goldens
- explicit planner-overhead report
- explicit break-even workload-size report
- explicit leaky-abstraction report
- explicit native baseline provenance report
- explicit executable backend security review report

## Performance Proof Readiness Report

Future native performance proposals must pass the
[Performance Proof Readiness Report](PERFORMANCE_PROOF_READINESS.md) before
TUC may make native performance claims.

The readiness report uses boundary contract
`performance_proof_boundary.blocking.v0`, report schema version
`tuc.performance_proof_readiness_report.v0`, API
`build_performance_proof_readiness_report(proposal_name, evidence)`, required
evidence IDs `PERFORMANCE_PROOF_REQUIRED_EVIDENCE`, and golden artifact
`tests/golden/proofs/performance_proof_readiness_report.json`.

Missing evidence keeps native performance claims blocked. Unknown evidence IDs
and duplicate evidence IDs fail closed.

The readiness report does not run benchmarks.
The readiness report does not access devices.
The readiness report does not execute backend artifacts.
The readiness report does not claim native performance parity.
The readiness report must not include raw benchmark output.

## Benchmarking Relationship

The current CPU-first benchmark harness is diagnostic. It is useful for local
drift and future comparisons, but it is not a performance proof.

Baseline benchmark output must not be used as a native performance parity claim
until this boundary is satisfied.

## Review Checklist

Reviewers must reject performance claims unless every answer is yes:

1. Is the claim scoped to a specific workload family and shape range?
2. Is the workload scope report present and bounded?
3. Is the benchmark methodology report present and bounded?
4. Is the toolchain environment report present and bounded?
5. Is the native baseline reproducible?
6. Is the native baseline provenance report present and bounded?
7. Is the native baseline comparison report present and bounded?
8. Is mathematical correctness still proven independently?
9. Are planner overhead and execution time reported separately?
10. Is the break-even workload-size report present and bounded?
11. Are cache effects explicit rather than hidden?
12. Are abstraction leaks listed and assigned to capabilities, HS-IR, runtime
   plans, backend contracts, or backend implementation?
13. Is HAC-IR still hardware-neutral?
14. Are runtime plans and compiler decisions golden-tested?
15. Is benchmark provenance versioned?
16. Is the benchmark artifact manifest present and bounded?
17. Is the executable backend security review report present and bounded?
18. Does the claim avoid broad wording such as "near native" unless the
    threshold is predefined and measured?

## Still Blocked

These remain blocked:

- claiming native performance parity
- claiming 100 percent native performance
- claiming a fixed percentage of vendor-library performance
- hiding planner overhead inside execution timing
- treating transfer-cost estimates as measured hardware performance
- using benchmark output as HAC-IR semantics
- adding hardware-specific performance knobs to HAC-IR
- executing backend artifacts or device code without a dedicated security RFC

The goal is to make performance a future proof, not a premature promise.
