# RFC 0151: Source-To-Intent Research Readiness

## Status

Accepted.

## Context

TUC's research claim is not that the project replaces CUDA, ROCm, XLA, TVM, or
production vendor compiler stacks. The claim is narrower: a
hardware-independent compute interface may be possible if source intent,
capability-driven planning, runtime evidence, and performance-boundary claims
remain explicit and reviewable.

The strongest current criticism is also accurate: direct source-to-intent
parsing is still blocked. TUC already has Source Intent IR, Source Intent
Intake, metadata conversion, conformance, preflight, and runtime evidence, but
the real source parser must not be treated as solved.

## Decision

Add a separate research readiness example:

```text
examples/source_to_intent_research_readiness.py
```

with deterministic golden evidence:

```text
tests/golden/frontend/source_to_intent_research_readiness.json
```

The report reuses the existing Source-To-Intent Readiness contract and marks
the current research proposal as still blocked. Existing evidence is recorded as
present, while parser-specific source corpus, parser fuzz/property corpus, and
parser report golden evidence remain missing.

Later RFCs add source corpus, property corpus, and proposal-only parser report
evidence. After RFC 0154, research-readiness evidence is complete while parser
implementation remains disabled.

The default Source-To-Intent Parser Block Gate remains unchanged. It continues
to prove that the ordinary parser path is closed.

## Security Boundary

This change does not add source parsing, source-file loading, Python imports,
decorator evaluation, `@triton.jit` execution, bytecode compilation, frontend
module inspection, plugin discovery, backend discovery, device access, network
access, subprocess execution, generated artifact execution, direct
`ComputeGraph` construction from source, or any source-to-metadata shortcut.

It serializes only bounded evidence IDs, booleans, issue IDs, and blocked
execution-surface labels.

## Consequences

TUC now has a visible research-status artifact for the hardest frontend
problem. The project can move toward a minimal source parser without pretending
that source parsing is complete or accidentally weakening secure-by-design
frontend boundaries.
