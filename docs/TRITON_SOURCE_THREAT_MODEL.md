# Triton Source Threat Model

TUC has a schema-versioned Triton-like metadata intake path. It does not yet
accept Triton Python source, Python function objects, decorators, bytecode, or
`@triton.jit` execution.

This document defines the required security model before any direct Triton
source ingestion can be implemented.

## Security Position

Direct Triton source ingestion remains blocked until the parser is designed as
a data-only boundary.

The future source path must:

- parse source text into bounded data
- must not import user modules
- must not evaluate decorators
- must not execute `@triton.jit`
- never import user modules
- never evaluate decorators
- never execute `@triton.jit`
- never compile Python bytecode
- never inspect Python function objects
- never execute generated artifacts
- never access devices
- never touch the network
- never read host paths outside an explicitly provided source buffer
- never use environment-variable-dependent behavior

Any proposal that needs one of those surfaces requires a separate security RFC,
sandboxing model, negative tests, and maintainer approval before implementation.

In plain terms: Direct Triton source ingestion remains blocked; a future parser
must not import user modules, must not evaluate decorators, and must not execute
@triton.jit.

## Attacker-Controlled Inputs

A future parser must treat all of these as untrusted:

- source bytes and decoded source text
- comments and string literals
- decorator syntax
- function names, argument names, and local symbols
- annotations and default values
- numeric literals and shape-like constants
- indexing expressions and pointer-like syntax
- operation names inferred from source structure
- source-to-metadata diagnostics
- parser error messages
- cached parser artifacts

## Forbidden During Parsing

The parser must reject or avoid:

- `import` and `from ... import ...`
- `exec`, `eval`, `compile`, `open`, `__import__`, and reflection helpers
- decorator evaluation
- arbitrary call execution
- dynamic attribute access as semantic authority
- filesystem reads after the caller has provided the source buffer
- subprocess execution
- dynamic library loading
- network access
- device discovery or device handles
- generated artifact creation or execution
- fallback behavior that changes mathematical intent

## Resource Budgets

A future source parser must define hard limits before accepting external input:

| Budget | Requirement |
| --- | --- |
| Source bytes | Maximum accepted UTF-8 byte length |
| Lines | Maximum line count |
| AST nodes | Maximum parsed node count |
| AST depth | Maximum nesting depth |
| Symbols | Maximum identifier count and identifier byte length |
| Literals | Maximum literal count and literal size |
| Operations | Maximum emitted operation count |
| Tensors | Maximum emitted tensor count and rank |
| Diagnostics | Maximum diagnostic count and text bytes |
| Cache | Maximum cache entry size and count, if caching exists |

All budget failures must fail closed with bounded diagnostics.

## Parser Output Contract

The only accepted output of a future Triton source parser is validated
Triton-like metadata or a validated `ComputeGraph`.

The accepted architecture is:

```text
source text
    ->
bounded syntax data
    ->
canonical source-intent IR
    ->
schema-versioned metadata
    ->
ComputeGraph
```

Equivalently: source text -> bounded syntax data -> canonical source-intent IR -> schema-versioned metadata.
No stage may execute user-controlled code,
inspect runtime Python objects, discover backends, or attach hardware-specific
placement semantics.

The output must include deterministic evidence equivalent to the current
metadata intake path:

- schema version
- source intake contract version
- blocked execution surfaces
- accepted operation families
- rejected syntax features
- source budget summary
- HAC-IR neutrality review result
- frontend-to-HAC-IR golden artifact
- runtime-plan golden artifact
- compiler decision-report golden artifact

## Required Negative Tests

Before direct source ingestion is accepted, tests must prove rejection of:

- imports
- arbitrary decorators
- decorator calls
- default values that require evaluation
- `exec`, `eval`, and `compile`
- file access attempts
- subprocess attempts
- network attempts
- dynamic library references
- device references
- path traversal strings
- oversized source text
- excessive AST depth
- excessive AST node count
- excessive diagnostic output
- unsupported operation families
- ambiguous softmax axis intent
- hardware-specific `tuc.*` leakage

## Fuzzing And Hardening Gate

Before the source parser accepts untrusted external source, TUC must add:

- parser fuzz target or equivalent fuzz corpus/property-test corpus
- malformed-source seed corpus
- resource-exhaustion seed corpus
- crash-free parser CI check
- deterministic diagnostics checks
- coverage for canonicalization before lowering

If native code is introduced, ASan/UBSan and strict ownership boundaries are
required before merge.

Triton source preflight v0 provides the first fuzz corpus/property-test corpus.
Future source-intent IR work must extend it with semantic mapping seeds before
source text can influence compiler artifacts.

Canonical Source Intent IR v0 now exists only as a data model. It must remain
disconnected from metadata conversion, `ComputeGraph`, TLIR, HAC-IR, HS-IR,
runtime plans, and compiler decision reports until a separate conversion RFC
adds corpus, goldens, and security-review evidence.

## HAC-IR Neutrality Gate

The source parser must preserve HAC-IR neutrality. It may describe compute
intent, tensor relationships, operation families, validation facts, and
developer hints that are already allowed by the frontend metadata contract. It
must not smuggle backend, vendor, device, plugin, launch, generated-artifact,
host-path, environment, or runtime-placement details into HAC-IR.

Any hardware-specific evidence discovered by a future trusted pipeline belongs
in capability data, HS-IR, runtime plans, or compiler decision reports, not in
the source-intent IR or HAC-IR.

## Current Allowed Path

The only Triton-like frontend path accepted by TUC for compiler ingestion is
schema-versioned metadata:

```text
Triton-like metadata
    ->
TritonKernelMetadata
    ->
ComputeGraph
    ->
TLIR
    ->
HAC-IR
```

This keeps Phase Epsilon moving without opening a Python execution surface.

TUC also has an execution-free
[Triton Source Preflight](TRITON_SOURCE_PREFLIGHT.md). It may parse caller-
provided source text as bounded syntax data and emit a deterministic diagnostic
report. It must not produce metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR,
runtime plans, compiler decision reports, or backend assignments.

TUC also has a data-only [Source Intent IR](SOURCE_INTENT_IR.md). It is the
named future boundary between bounded syntax data and schema-versioned metadata,
but no implemented frontend path may produce it from source text yet.
