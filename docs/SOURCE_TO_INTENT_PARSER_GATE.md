# Source-To-Intent Parser Gate

TUC still does not implement source text to Source Intent IR.

This gate defines what must exist before any future Triton-like source parser
may create `source_intent.v0` plain data or a `SourceIntentModule`.

## Status

Source-to-intent parsing is blocked.

TUC treats the first parser as a research proof obligation, not a claim that the
project replaces CUDA, ROCm, XLA, TVM, or production vendor compilers. The
parser may become acceptable only when it proves a narrow, bounded path from a
caller-provided source buffer to `source_intent.v0` plain data.

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

The current corpus inventory is documented in
[Source-To-Intent Corpus Evidence](SOURCE_TO_INTENT_CORPUS.md). It provides
accepted and rejected source-buffer fixtures but does not implement parsing.

The current fuzz/property obligation inventory is documented in
[Source-To-Intent Property Corpus](SOURCE_TO_INTENT_PROPERTY_CORPUS.md). It
defines parser properties but does not run parser logic or emit Source Intent
IR.

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
- Source Intent Frontend Conformance Gate output proving merge-facing
  conformance and public-return coverage
- Source-To-Intent Readiness report with every required evidence ID present

The parser report must not contain raw source text, raw payloads, host paths,
environment data, generated artifacts, plugin entrypoints, device handles, or
backend artifacts.

[Source-To-Intent Readiness Report](SOURCE_TO_INTENT_READINESS.md) defines the
deterministic report that keeps parser proposals blocked until all required
evidence is present.

[Source-To-Intent Research Readiness](SOURCE_TO_INTENT_RESEARCH_READINESS.md)
records the current complete proposal-evidence set while parser implementation
remains blocked.

[Source-To-Intent Parser Report](SOURCE_TO_INTENT_PARSER_REPORT.md) defines the
proposal-only parser report golden. It keeps `parser_enabled = false` and does
not implement source parsing.

[Source-To-Intent Parser Block Gate](SOURCE_TO_INTENT_PARSER_BLOCK_GATE.md)
turns the current blocked parser state into CI-facing merge evidence through
`examples/source_to_intent_parser_block_gate.py`.

## Review Checklist

Maintainers must reject parser work unless every answer is yes:

1. Does the parser accept only caller-provided source buffers?
2. Does it parse into bounded data, not behavior?
3. Are source text and preflight reports still disconnected from compiler
   artifacts until Source Intent Intake succeeds?
4. Does every emitted payload pass `source_intent_from_mapping(data)`?
5. Does every emitted payload pass Source Intent Frontend Conformance?
6. Does Source Intent Frontend Conformance Gate pass?
7. Does the Source-To-Intent Readiness report pass?
8. Are rejected source cases fail-closed with bounded diagnostics?
9. Are operation-family mappings deterministic and golden-tested?
10. Is softmax axis intent explicit?
11. Are hardware, backend, vendor, device, plugin, memory-domain, placement,
   path, environment, and artifact details blocked?
12. Are HAC-IR, runtime-plan, and compiler decision-report goldens present?
13. Are fuzz or property tests part of CI?
14. Is any proposed cache covered by a separate cache threat model?
15. Is any native parser code covered by ASan/UBSan and ownership rules?

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
