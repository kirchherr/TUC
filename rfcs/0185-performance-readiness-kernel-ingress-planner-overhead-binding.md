# RFC 0185: Performance Readiness Kernel Ingress Planner Overhead Binding

- Status: accepted-for-prototype
- Created: 2026-06-18
- Phase: Alpha / Delta / Epsilon

## Summary

Bind Performance Proof Readiness to current Kernel Ingress evidence for two
bounded evidence IDs:

- `workload_scope`
- `planner_overhead_report`

This RFC does not run benchmarks, execute backend artifacts, access devices,
load dynamic libraries, discover plugins, publish raw timing samples, or claim
native performance parity.

## Motivation

Kernel Ingress shape-profile evidence now produces bounded workload scopes.
Planner overhead is also a required native-performance blocker, but readiness
must not mark it present through a hand-written boolean.

The next practical step is to derive the current readiness flags from checked
contracts:

- Kernel Ingress workload scope must pass its contract.
- The accepted Kernel Ingress MVP pipeline graph must produce a bounded
  planner-overhead report.
- Planner overhead must remain separate from execution timing.

## Decision

Update `examples/performance_proof_readiness.py` so
`build_blocked_performance_proof_evidence()` derives current evidence by:

1. building and contract-checking
   `examples/source_to_intent_research_kernel_ingress_workload_scope.py`;
2. constructing the accepted Kernel Ingress MVP pipeline graph through the
   controlled Source-to-Intent research path;
3. building a diagnostic `planner_overhead_report.v0` for that graph;
4. checking that the report keeps execution timing unmeasured, break-even
   evidence not established, and planner overhead outside execution time.

The readiness report may now mark `planner_overhead_report` present, but it
must remain `ready=false` until every required performance-proof evidence ID is
present.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`

## Security Boundary

The readiness report output remains a boolean evidence checklist. It must not
include raw source, raw tensor values, raw benchmark output, raw timing samples,
host paths, environment variables, device identifiers, generated artifacts,
plugin entrypoints, backend binaries, dynamic-library paths, or backend
artifact contents.

The planner-overhead report used for evidence remains diagnostic. It does not
authorize native execution, benchmark ingestion, performance parity claims, or
break-even claims.

## Consequences

- Current readiness evidence is less hand-wavy: two evidence IDs are now tied
  to checked Kernel Ingress artifacts.
- Planner overhead is visible as a separate compiler/planner concern.
- Native performance remains blocked until the remaining evidence IDs are
  satisfied.

