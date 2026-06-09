# RFC 0053: Canonical Source Intent IR v0

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds a canonical Source Intent IR data model.

This RFC does not add source parsing, metadata conversion, `ComputeGraph`
construction, TLIR lowering, HAC-IR lowering, runtime planning, backend
selection, plugin discovery, or code execution.

The new contract is:

```text
source_intent_ir.canonical.v0
```

## Motivation

The Triton source preflight gate is intentionally diagnostic. The next risk is
accidentally turning preflight into a half-semantic parser that can influence
compiler artifacts before the source-ingestion threat model is satisfied.

Canonical Source Intent IR creates a named intermediate contract between
bounded syntax data and schema-versioned metadata while keeping all conversion
arrows blocked.

## Decision

Add `tuc.frontend.source_intent` with:

- `SOURCE_INTENT_IR_CONTRACT`
- `SourceIntentTensor`
- `SourceIntentOperation`
- `SourceIntentModule`
- bounded tensor and operation counts
- bounded tensor rank, dimensions, and operation arity
- neutral operation families only
- neutral hints only
- deterministic dump support

The implementation intentionally provides no `to_metadata`, no
`to_compute_graph`, and no lowering path.

The implementation intentionally provides no `to_compute_graph`.

## Accepted Scope

Source Intent IR v0 may represent:

- tensor identity, shape, and dtype
- operation families: `matmul`, `elementwise`, `reduction`, `softmax`
- symbolic input and output tensor references
- neutral hints: `prefer_linear_accelerator`, `prefer_sparsity`,
  `robust_to_noise`, and `max_error_budget`

## Rejected Scope

Source Intent IR v0 rejects:

- hardware family names as operation families
- `prefer_analog_linear`
- reserved `tuc.*` keys
- backend names
- vendor names
- device names
- memory-domain or placement keys
- plugin entrypoints
- Python source, function objects, bytecode, generated artifacts, commands,
  dynamic libraries, file paths, URLs, subprocess, network, or environment keys

## Evidence

The implementation adds:

- deterministic Source Intent IR golden dump
- unit tests for valid module construction
- negative tests for hardware-specific families
- negative tests for execution-surface and hardware-specific hint keys
- tests proving the object has no metadata or `ComputeGraph` conversion exit
- documentation in `docs/SOURCE_INTENT_IR.md`

## Consequences

- The project can discuss future source parsing without weakening the current
  execution-free boundary.
- Preflight remains diagnostic only.
- Schema-versioned metadata remains the accepted bridge into compiler
  ingestion.
- Metadata intake remains the only source-connected compiler-ingestion path.
- Future conversion from Source Intent IR to metadata requires its own RFC,
  corpus, goldens, HAC-IR neutrality review, runtime-plan goldens, and compiler
  decision-report goldens.

## Rejected Alternatives

1. Convert preflight reports directly into Source Intent IR.

   Rejected because preflight reports are review diagnostics, not semantic
   source-intent artifacts.

2. Convert Source Intent IR directly into `ComputeGraph`.

   Rejected because schema-versioned metadata remains the accepted bridge into
   compiler ingestion until a separate security review accepts otherwise.

3. Keep `prefer_analog_linear` as a source-intent hint.

   Rejected because source intent must not privilege one hardware class.
