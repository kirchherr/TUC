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

## Required Future Evidence

Any future performance proof must add:

- dedicated performance proof RFC
- benchmark methodology document
- native baseline provenance
- benchmark report schema
- deterministic benchmark fixtures or stored report artifacts
- correctness goldens for every benchmarked workload
- runtime-plan and compiler decision-report goldens
- explicit planner-overhead report
- explicit leaky-abstraction report
- security review for any executable backend, device access, generated artifact,
  cache, subprocess, dynamic library, or native code used by benchmarking

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
2. Is the native baseline reproducible?
3. Is mathematical correctness still proven independently?
4. Are planner overhead and execution time reported separately?
5. Is the break-even workload size reported?
6. Are cache effects explicit rather than hidden?
7. Are abstraction leaks listed and assigned to capabilities, HS-IR, runtime
   plans, backend contracts, or backend implementation?
8. Is HAC-IR still hardware-neutral?
9. Are runtime plans and compiler decisions golden-tested?
10. Is benchmark provenance versioned?
11. Are any executable backend or device surfaces threat-modeled?
12. Does the claim avoid broad wording such as "near native" unless the
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
