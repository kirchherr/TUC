# RFC 0063: Performance Proof Boundary

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Alpha / Delta / Epsilon

## Summary

TUC adds a formal performance proof boundary covering two known limits of the
universal-compute claim:

- leaky abstraction risk
- runtime planner overhead

This RFC does not add native benchmarks, performance parity claims, executable
CUDA/HIP backends, device access, generated-artifact execution, benchmark
artifact ingestion, cache execution, dynamic libraries, subprocess execution,
or hardware-specific HAC-IR semantics.

## Motivation

Objective Alpha currently proves correctness and inspectability, not native
performance. That is intentional, but reviewers need a precise line between:

- the claim TUC can safely make today
- the performance claims TUC must not make yet

Two risks matter most:

1. A hardware-independent abstraction can become too slow if the last
   hardware-specific optimization details cannot be expressed outside HAC-IR.
2. A runtime planner can dominate runtime for small or fast workloads if
   planning overhead is not separately measured and amortized.

## Decision

Add [Performance Proof Boundary](../docs/PERFORMANCE_PROOF_BOUNDARY.md).
Future native performance proposals must also pass the
[Performance Proof Readiness Report](../docs/PERFORMANCE_PROOF_READINESS.md).

The current proof claim remains:

```text
Compute intent can remain hardware-independent, flow through capability-driven
runtime planning, and produce correct deterministic results.
```

TUC does not currently claim native performance parity, 100 percent native
performance, or a fixed percentage of CUDA, HIP, vendor-library, or
hand-optimized kernel performance.

## Leaky Abstraction Gate

Before TUC may claim native performance parity, a future proposal must include:

- scoped workload family and tensor shapes
- reproducible native baseline
- versioned toolchain and environment
- backend capability data used by TUC
- HS-IR/backend-specific choices used by TUC
- list of hardware-specific facts needed for performance
- proof those facts do not enter HAC-IR semantics
- benchmark provenance
- correctness comparison against deterministic reference semantics
- performance comparison against native baseline
- explanation for every missing native optimization

If a performance-critical hardware detail can only be represented by changing
HAC-IR semantics, the performance parity claim fails.

## Planner Overhead Gate

Before TUC may claim runtime planning is beneficial for a workload class, a
future proposal must report:

- graph construction time
- frontend intake time
- lowering time
- runtime planning time
- backend selection time
- artifact generation time, if any
- execution time
- cache hit and cache miss behavior, if caching exists
- break-even workload size
- small-workload case where planning overhead may dominate

Planner overhead must not be hidden inside execution timing.

## Security Boundary

Performance evidence must not introduce executable backend code, device access,
generated artifacts, dynamic libraries, subprocesses, plugin discovery, or cache
execution without a dedicated security RFC, threat model, resource budgets, and
sandboxing plan.

Benchmark outputs, transfer-cost profiles, latency estimates, cache behavior,
and measured hardware data must not become HAC-IR semantics.

The readiness report does not run benchmarks.
The readiness report does not access devices.
The readiness report does not execute backend artifacts.
The readiness report does not claim native performance parity.
It must not include raw benchmark output.

## Consequences

- TUC can discuss performance honestly without weakening the current proof.
- Correctness proof artifacts remain valid without implying native speed.
- Future performance work gets explicit acceptance criteria.
- Leaky abstraction and planner overhead become reviewable gates.

## Rejected Alternatives

1. Ignore performance until real hardware exists.

   Rejected because the abstraction proof can be misunderstood as a performance
   proof unless the boundary is explicit.

2. Claim "near native" performance with no threshold.

   Rejected because broad performance claims must be scoped, measured,
   reproducible, and compared against a native baseline.

3. Add hardware-specific optimization knobs directly to HAC-IR.

   Rejected because this would undermine the hardware-independent interface.

4. Hide planning time inside execution time.

   Rejected because planner overhead is one of the main limits of the proof.
