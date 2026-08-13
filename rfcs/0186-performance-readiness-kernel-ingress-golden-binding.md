# RFC 0186: Performance Readiness Kernel Ingress Golden Binding

- Status: accepted-for-prototype
- Created: 2026-06-18
- Phase: Alpha / Delta / Epsilon

## Summary

Bind Performance Proof Readiness to deterministic Kernel Ingress golden
evidence for:

- `correctness_goldens`
- `runtime_plan_goldens`
- `compiler_decision_report_goldens`

This RFC does not run benchmarks, execute backend artifacts, access devices,
load dynamic libraries, discover plugins, publish raw timing samples, or claim
native performance parity.

## Motivation

The Kernel Ingress proof path already emits source-free digests for reference
correctness, runtime plans, and compiler decision reports. Those artifacts are
golden-tested and represent practical review evidence for the current research
slice.

Performance Proof Readiness should not leave those evidence IDs missing when
the accepted Kernel Ingress report already proves they exist and are
reproducible.

## Decision

Update `examples/performance_proof_readiness.py` so the current blocked
readiness proposal marks these evidence IDs present only when:

1. the generated Kernel Ingress report passes its contract;
2. the generated report exactly matches
   `tests/golden/frontend/source_to_intent_research_kernel_ingress.json`;
3. every accepted Kernel Ingress case exposes the expected SHA-256 digest field:
   `reference_correctness_digest`, `runtime_plan_digest`, or
   `compiler_decision_digest`.

The readiness report remains a boolean checklist. It does not embed the
digests, raw source, raw tensor values, benchmark output, or timing samples.

## Evidence

- `examples/performance_proof_readiness.py`
- `tests/test_performance_proof_readiness.py`
- `tests/golden/proofs/performance_proof_readiness_report.json`
- `docs/PERFORMANCE_PROOF_READINESS.md`

## Security Boundary

The golden binding reads only repository-controlled golden evidence. It must
not read host paths supplied by users, import arbitrary source, evaluate
decorators, execute `@triton.jit`, run subprocesses, load plugins, or authorize
native backend execution.

The evidence remains review-only. Native performance claims stay blocked until
all required Performance Proof Readiness evidence IDs are present.

## Consequences

- Existing practical Runtime and compiler decision evidence now counts toward
  readiness without expanding the parser or adding execution surfaces.
- Kernel Ingress golden drift now prevents those readiness IDs from being
  marked present.
- Performance readiness remains blocked by the remaining governance,
  benchmark, native-baseline, leaky-abstraction, break-even, and executable
  backend security evidence.

