# RFC 0061: Source-To-Intent Parser Gate

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC defines the gate that must be satisfied before any future Triton-like
source parser may create `source_intent.v0` plain data or a
`SourceIntentModule`.

This RFC does not implement a parser, source ingestion, source-file loading,
preflight-to-intent conversion, Python module imports, decorator evaluation,
`@triton.jit` execution, metadata construction from source, `ComputeGraph`
construction from source, lowering, runtime planning, backend selection, plugin
discovery, generated-artifact execution, or device access.

## Motivation

TUC now has Source Intent IR, schema-versioned Source Intent Intake, Source
Intent Metadata Conversion, Source Intent Frontend Conformance, and a report
schema for frontend conformance evidence.

The next risk is premature source parsing. A half-semantic parser would enlarge
the attack surface and could bypass the hardware-independent interface that TUC
is trying to prove.

This RFC keeps source parsing blocked while defining the evidence required
before it can become implementation work.

## Decision

Add [Source-To-Intent Parser Gate](../docs/SOURCE_TO_INTENT_PARSER_GATE.md).

Any future parser must follow this path:

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

## Required Evidence

Parser implementation work remains blocked until a follow-up parser RFC adds:

- parser threat model update
- hard parser resource budgets
- accepted and rejected source corpus
- fuzz or property-test corpus for arbitrary source bytes
- deterministic parser report golden
- emitted `source_intent.v0` plain-data golden
- Source Intent Intake report golden
- Source Intent Metadata Conversion report golden
- metadata intake report golden
- HAC-IR golden
- runtime-plan golden
- compiler decision-report golden
- HAC-IR neutrality review checklist result
- Source Intent Frontend Conformance report for emitted plain data

## Security Boundary

The gate keeps source text and preflight reports disconnected from compiler
artifacts until Source Intent Intake succeeds.

The future parser must not import user modules, must not evaluate decorators,
must not execute `@triton.jit`, and must not produce `ComputeGraph`.

The future parser must not read host files after the caller provides the source
buffer, discover plugins or backends, access devices, touch the network, run
subprocesses, load dynamic libraries, execute generated artifacts, or depend on
environment variables.

The parser report must not contain raw source text, raw payloads, host paths,
environment data, generated artifacts, plugin entrypoints, device handles, or
backend artifacts.

## Corpus Requirements

Accepted semantic seeds must cover:

- matmul
- elementwise
- reduction
- softmax with explicit axis semantics
- neutral hints already accepted by Source Intent IR
- tensor shape and dtype declarations that map to `source_intent.v0`

Rejected seeds must cover:

- imports
- arbitrary decorators
- decorator calls
- defaults and annotations that require evaluation
- `exec`, `eval`, `compile`, `open`, `__import__`
- reflection helpers
- subprocess, network, dynamic-library, environment, host-path, device, backend,
  and plugin surfaces
- unsupported `tl.*` calls
- ambiguous softmax axis intent
- hardware-specific hints such as `prefer_analog_linear`
- reserved `tuc.*` leakage
- resource exhaustion cases
- malformed or invalid Unicode input

## Consequences

- TUC gets a clear path toward real frontend integration without adding a parser
  yet.
- Source Intent remains the required hardware-independent boundary.
- Future parser work must arrive with security evidence, conformance evidence,
  and golden review artifacts before it can affect compiler behavior.

## Rejected Alternatives

1. Let source parsers emit metadata directly.

   Rejected because it would bypass Source Intent Intake and weaken the
   canonical source-intent boundary.

2. Let source parsers emit `ComputeGraph` directly.

   Rejected because it would bypass metadata intake, Source Intent review, and
   frontend conformance evidence.

3. Start with a partial parser and add security later.

   Rejected because source text is attacker-controlled input and parser
   behavior must be bounded before source can influence compiler artifacts.

4. Reuse Triton preflight reports as Source Intent input.

   Rejected because preflight reports are diagnostic evidence, not semantic
   source-intent payloads.
