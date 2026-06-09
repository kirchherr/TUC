# RFC 0049: Triton Source Threat Model

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds a threat model for future Triton source ingestion.

This RFC does not add a source parser. It defines the security gates that must
exist before direct Triton Python source, Python function objects, decorators,
bytecode, or `@triton.jit` handling can be accepted.

## Motivation

TUC can now ingest schema-versioned Triton-like metadata and can prove all MVP
operation families through frontend-originated goldens. The next temptation is
to parse Triton Python source directly.

That would be unsafe without a clear threat model. Python source can carry
imports, decorators, default values, calls, reflection, filesystem references,
device assumptions, and JIT surfaces. TUC must keep frontend ingestion as data,
not behavior.

## Decision

Add [Triton Source Threat Model](../docs/TRITON_SOURCE_THREAT_MODEL.md).

Direct Triton source ingestion remains blocked until a follow-up implementation
includes:

- bounded source parser
- bounded source parsing
- must not import user modules
- must not evaluate decorators
- must not execute `@triton.jit`
- no imports
- no decorator evaluation
- no `@triton.jit` execution
- no Python bytecode compilation
- no Python function-object inspection
- no filesystem reads beyond the caller-provided source buffer
- no subprocesses
- no dynamic libraries
- no device access
- no network access
- no generated-artifact execution
- parser resource budgets
- negative tests
- fuzz corpus or property-test corpus
- deterministic source-intake diagnostics
- frontend intake, HAC-IR, runtime-plan, and decision-report goldens
- HAC-IR neutrality

Plain-language gate: future source work must not import user modules, must not
evaluate decorators, and must not execute @triton.jit.

## Parser Boundary

The parser boundary must accept source text as untrusted data and return either
validated metadata or a validated `ComputeGraph`. It must not return executable
code, backend artifacts, Python callables, device handles, or runtime launch
configuration.

The future architecture is:

```text
source text -> bounded syntax data -> canonical source-intent IR -> schema-versioned metadata
```

Only then may the existing metadata-to-`ComputeGraph` pipeline lower to TLIR and
HAC-IR. Direct Triton source ingestion remains blocked until this architecture
has negative tests, deterministic source-intake diagnostics, parser budgets, and
a fuzz corpus/property-test corpus.

## Consequences

- Phase Epsilon can continue toward real Triton integration without weakening
  secure-by-design guarantees.
- Metadata intake remains the only accepted Triton-like frontend path for now.
- Future source parser work has an explicit merge gate.

## Rejected Alternatives

1. Parse Python function objects instead of source text.

   Rejected because function objects imply imports, bytecode, globals,
   closures, decorators, and environment-dependent behavior.

2. Execute `@triton.jit` and inspect generated artifacts.

   Rejected because JIT execution and generated artifacts need a separate
   sandbox and backend execution threat model.

3. Allow source ingestion with broad fallback diagnostics.

   Rejected because misleading fallback can hide semantic drift or unsupported
   operation families.
