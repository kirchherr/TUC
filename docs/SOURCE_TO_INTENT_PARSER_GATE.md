# Source-To-Intent Parser Gate

TUC still does not implement source text to Source Intent IR.

This gate defines what must exist before any future Triton-like source parser
may create `source_intent.v0` plain data or a `SourceIntentModule`.

## Status

Source-to-intent parsing is blocked.

The only implemented frontend paths remain:

- Triton source preflight as diagnostic syntax review only
- Source Intent Intake from already decoded plain data
- Source Intent Metadata Conversion from an already constructed
  `SourceIntentModule`
- Source Intent Frontend Conformance for external plain-data frontend authors

No source text or preflight report may produce Source Intent IR today.

## Required Future Path

Any future parser must use this path:

```text
caller-provided source buffer
    ->
bounded source syntax data
    ->
source_intent.v0 plain data
    ->
Source Intent Intake
    ->
SourceIntentModule
    ->
Source Intent Metadata Conversion
    ->
schema-versioned metadata
    ->
ComputeGraph
```

A future parser must not produce metadata, `ComputeGraph`, TLIR, HAC-IR, HS-IR,
runtime plans, backend decisions, or backend artifacts directly.

## Non-Negotiable Blocks

The parser gate must block any implementation that:

- imports user modules
- evaluates decorators
- executes `@triton.jit`
- compiles Python bytecode
- inspects Python function objects
- reads host files after the caller provides the source buffer
- discovers plugins or backends
- accesses devices
- touches the network
- runs subprocesses
- loads dynamic libraries
- emits generated artifacts
- uses environment-variable-dependent behavior
- writes caches or artifacts without a separate cache threat model
- smuggles backend, vendor, device, plugin, launch, path, memory-domain, or
  placement details into Source Intent IR or HAC-IR

Plain gate language: a source-to-intent parser must not import user modules, must not evaluate decorators, must not execute `@triton.jit`, and must not produce `ComputeGraph`.

## Required Parser Budgets

A parser RFC must define hard limits for:

- source bytes
- decoded source characters
- line count
- AST nodes
- AST depth
- identifier count and identifier byte length
- literal count and literal byte length
- tensor count, rank, and dimensions
- operation count
- operation arity
- diagnostic count and diagnostic byte length
- parser report byte length
- fuzz input size
- cache entry size and count, if a cache is proposed

All budget failures must fail closed with bounded diagnostics.

## Required Corpus

A parser proposal must add a source-to-intent corpus before source text can
influence compiler artifacts.

Accepted semantic seeds must cover:

- matmul intent
- elementwise intent
- reduction intent
- softmax intent with explicit axis semantics
- neutral hints that already exist in Source Intent IR
- tensor shape and dtype declarations that map to `source_intent.v0`

Rejected seeds must cover:

- imports and `from ... import ...`
- arbitrary decorators
- decorator calls such as `@triton.jit(...)`
- defaults, annotations, and constructs that require evaluation
- `exec`, `eval`, `compile`, `open`, `__import__`
- reflection helpers such as `getattr`, `globals`, `locals`, and `vars`
- subprocess, network, dynamic-library, environment, and host-path surfaces
- device and backend references
- path traversal strings
- unsupported `tl.*` calls
- unsupported operation families
- ambiguous softmax axis intent
- hardware-specific hints such as `prefer_analog_linear`
- reserved `tuc.*` leakage
- oversized source
- excessive AST depth or node count
- excessive emitted tensor or operation count
- excessive diagnostic output
- malformed or invalid Unicode input

## Required Evidence

A parser proposal must include all of these review artifacts:

- dedicated source-to-intent parser RFC
- parser threat model update
- parser budget table
- accepted and rejected source corpus
- property tests or fuzz corpus for arbitrary source bytes
- deterministic source-to-intent parser report golden
- emitted `source_intent.v0` plain-data golden
- Source Intent Intake report golden
- Source Intent Metadata Conversion report golden
- metadata intake report golden
- HAC-IR golden
- runtime-plan golden
- compiler decision-report golden
- HAC-IR neutrality review checklist result
- Source Intent Frontend Conformance report for emitted plain data

The parser report must not contain raw source text, raw payloads, host paths,
environment data, generated artifacts, plugin entrypoints, device handles, or
backend artifacts.

## Review Checklist

Maintainers must reject parser work unless every answer is yes:

1. Does the parser accept only caller-provided source buffers?
2. Does it parse into bounded data, not behavior?
3. Are source text and preflight reports still disconnected from compiler
   artifacts until Source Intent Intake succeeds?
4. Does every emitted payload pass `source_intent_from_mapping(data)`?
5. Does every emitted payload pass Source Intent Frontend Conformance?
6. Are rejected source cases fail-closed with bounded diagnostics?
7. Are operation-family mappings deterministic and golden-tested?
8. Is softmax axis intent explicit?
9. Are hardware, backend, vendor, device, plugin, memory-domain, placement,
   path, environment, and artifact details blocked?
10. Are HAC-IR, runtime-plan, and compiler decision-report goldens present?
11. Are fuzz or property tests part of CI?
12. Is any proposed cache covered by a separate cache threat model?
13. Is any native parser code covered by ASan/UBSan and ownership rules?

## Still Blocked

These remain blocked after this gate:

- implementing a source parser
- accepting source text as compiler input
- converting preflight reports into Source Intent IR
- loading source files by path
- importing frontend packages
- executing Triton, Python, generated code, or backend artifacts
- source-to-metadata or source-to-ComputeGraph shortcuts

The gate exists so TUC can move toward real frontend integration without
turning source parsing into an execution surface.
