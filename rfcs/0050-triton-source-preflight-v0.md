# RFC 0050: Triton Source Preflight v0

- Status: accepted-for-prototype
- Created: 2026-06-09
- Phase: Epsilon

## Summary

TUC adds an execution-free Triton source preflight gate.

This RFC does not add direct Triton source ingestion. It adds a bounded source
syntax preflight that accepts caller-provided source text, parses it as data,
rejects known execution surfaces, and emits a deterministic
`TritonSourcePreflightReport`.

The boundary is a bounded source syntax preflight, not a compiler ingestion
path.

## Motivation

RFC 0049 blocks direct Triton source ingestion until source-parser gates exist:
resource budgets, negative tests, deterministic diagnostics, fuzzing, and
HAC-IR neutrality review. The first useful implementation step is to make those
pre-parser gates executable without connecting source text to lowering.

## Decision

Add `tuc.frontend.triton_source` with:

- `TRITON_SOURCE_PREFLIGHT_CONTRACT`
- source byte and line budgets
- AST node and depth budgets
- identifier and literal budgets
- bounded diagnostics
- `TritonSourcePreflightReport`
- `preflight_triton_source`

The preflight may parse source text into bounded syntax data. It must not import
user modules, must not evaluate decorators, must not execute `@triton.jit`, must
not inspect Python function objects, and must not produce a `ComputeGraph`.

Plain gate language: it must not import user modules, must not evaluate
decorators, must not execute `@triton.jit`, and must not produce a
`ComputeGraph`.

The preflight must not produce a `ComputeGraph`.

## Accepted Scope

The v0 preflight accepts only narrow syntax evidence:

- one kernel function
- `@triton.jit` decorator syntax as data
- selected `tl.*` calls as operation-family hints
- simple expressions

The preflight rejects imports, arbitrary decorators, decorator calls, defaults,
annotations, dangerous builtins, reflection helpers, subprocess/network/device/
dynamic-library surfaces, unsupported `tl.*` calls, path-like strings, and
`tuc.*` HAC-IR neutrality leakage.

## Evidence

The implementation adds:

- unit tests for accepted bounded syntax
- negative tests for parser threat-model surfaces
- oversized-source and AST-depth rejection tests
- a deterministic golden source preflight report
- documentation in `docs/TRITON_SOURCE_PREFLIGHT.md`

## Consequences

- Phase Epsilon can move closer to real Triton intent without opening a Python
  execution surface.
- Source parser work now has an executable preflight boundary.
- Metadata intake remains the only source of `ComputeGraph` values from
  Triton-like frontend data.

## Rejected Alternatives

1. Convert preflight output directly into metadata.

   Rejected because source-intent IR and semantic mapping need a separate RFC,
   fuzz corpus, goldens, and review.

2. Accept Python function objects for preflight.

   Rejected because function objects imply imports, globals, closures,
   decorators, bytecode, and environment-dependent behavior.

3. Allow decorator calls as syntax data.

   Rejected because decorator arguments and defaults can hide evaluation
   surfaces and semantic drift.
