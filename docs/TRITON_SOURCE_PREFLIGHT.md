# Triton Source Preflight

TUC includes an execution-free Triton source preflight gate.

This is not a Triton source parser, not a `@triton.jit` handler, and not an
ingestion path into `ComputeGraph`, TLIR, HAC-IR, HS-IR, runtime plans, or
backend decisions. It is a bounded source-intake preflight that parses caller-
provided source text as syntax data and returns deterministic review evidence.

It is not an ingestion path into `ComputeGraph`.

## Contract

- Contract: `triton_source_preflight.execution_free.v0`
- API: `preflight_triton_source(source, source_name="triton_source")`
- Output: `TritonSourcePreflightReport`
- Golden: `tests/golden/frontend/triton_source_preflight.txt`

The report includes:

- accepted/rejected status
- source byte and line counts
- AST node and depth counts
- identifier and literal counts
- operation-family hints inferred from allowed `tl.*` syntax
- blocked execution surfaces
- rejected feature IDs
- bounded diagnostics

## Execution-Free Boundary

The preflight gate must not:

- import user modules
- evaluate decorators
- execute `@triton.jit`
- compile Python bytecode
- inspect Python function objects
- execute generated artifacts
- access devices
- touch the network
- read host files
- discover plugins or backends
- produce a `ComputeGraph`

Plain gate language: it must not import user modules, must not evaluate
decorators, must not execute `@triton.jit`, and must not produce a
`ComputeGraph`.

The preflight must not produce a `ComputeGraph`.
The preflight must not evaluate decorators.
Decorator calls such as `@triton.jit(...)` are rejected.

The only accepted decorator syntax is `@triton.jit` as data. Decorator calls
such as `@triton.jit(...)` are rejected because they would require evaluating
arguments or defaults.

## Current Syntax Rules

The v0 preflight is intentionally narrow.

Accepted as syntax data:

- one `def` kernel function
- `@triton.jit` decorator syntax
- selected `tl.*` calls used as reviewable operation-family hints
- simple expression syntax

Rejected:

- imports
- arbitrary decorators
- decorator calls
- default values
- annotations
- `exec`, `eval`, `compile`, `open`, `__import__`
- reflection helpers such as `getattr`, `globals`, `locals`, and `vars`
- subprocess, network, dynamic-library, environment, and host-path surfaces
- unsupported `tl.*` calls
- `tuc.*` references or literals that could smuggle hardware-specific details
  into HAC-IR

## Relationship To Source Parsing

The preflight is the first implementation step under
[Triton Source Threat Model](TRITON_SOURCE_THREAT_MODEL.md). It satisfies the
first parser gate by making source limits, negative tests, and deterministic
diagnostics executable.

It does not satisfy the whole source-ingestion gate. A future source parser
still needs a canonical source-intent IR, metadata conversion, fuzz corpus,
source-intake goldens, HAC-IR goldens, runtime-plan goldens, compiler decision
goldens, and a separate security review before any direct source can affect the
compiler pipeline.
