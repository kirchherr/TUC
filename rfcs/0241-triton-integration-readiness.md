# RFC 0241: Triton Integration Readiness

## Status

Accepted.

## Context

The roadmap now points beyond Minimal Walkthrough, Proof Of Backend Equivalence,
and Layout Conversion Evidence toward real Triton integration as the next
credibility milestone.

That milestone is risky if it is treated as permission to execute Triton source,
import Python modules, evaluate decorators, or connect source text directly to
compiler artifacts. TUC needs a review checkpoint that says what is already
ready and what remains missing before broader Triton-facing integration can
advance.

## Decision

Add Triton Integration Readiness v0.

The report is data-only and records:

- satisfied prerequisites from the current safe frontend and runtime proof path;
- missing prerequisites for broader parser syntax and external frontend package
  conformance;
- policy-blocked surfaces for direct Triton source ingestion and Triton JIT
  execution;
- explicit counts and issues showing the current state is not ready.

The report schema is:

```text
schemas/triton_integration_readiness_report.v0.schema.json
```

The canonical example is:

```text
examples/triton_integration_readiness.py
```

## Security Constraints

The report must not:

- parse Triton source;
- import Python modules;
- evaluate decorators;
- execute `@triton.jit`;
- inspect Python function objects;
- access devices;
- discover plugins;
- run subprocesses;
- load dynamic libraries;
- create generated artifacts;
- serialize source text, host paths, command lines, environment variables,
  device identifiers, runtime handles, backend artifacts, raw benchmark output,
  raw timing samples, or executable permissions.

## Consequences

Real Triton integration remains blocked until this readiness report can pass
with all required prerequisites satisfied. This keeps the next roadmap milestone
practical and reviewable without weakening the secure compiler boundary.