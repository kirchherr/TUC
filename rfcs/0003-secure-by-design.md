# RFC 0003: Secure By Design Baseline

## Status

Accepted for project policy

## Summary

Adopt secure-by-design as a core TUC engineering constraint. Treat compiler
inputs, IR, backend metadata, runtime plans, caches, and CI inputs as untrusted.

## Motivation

TUC aims to compile and execute workloads across heterogeneous hardware. That
creates many attack surfaces: parsers, lowering passes, plugins, generated
artifacts, runtime plans, and device access. Security must be built into the
architecture before those surfaces become large.

## Goals

- Define trust boundaries.
- Prevent arbitrary code execution during parse, validation, and backend
  discovery.
- Require validation before lowering.
- Require resource limits on accepted inputs.
- Keep backend and fallback decisions inspectable.
- Add negative tests for unsafe inputs.
- Align project process with CISA Secure by Design and NIST SSDF.

## Non-Goals

- Full formal verification.
- Complete sandbox implementation in this RFC.
- Production vulnerability program before first public release.

## Policy

- New compiler input formats require validation and malformed-input tests.
- New backend APIs must separate declarative capability checks from executable
  backend code.
- Native parser or lowering code requires fuzzing and sanitizer plans before it
  is accepted.
- CI must default to least privilege.
- Any approximate lowering must be controlled by explicit error budgets.

## Testing

Security-sensitive changes should include:

- rejection tests,
- resource-limit tests,
- deterministic diagnostics tests,
- fuzz targets when parsing serialized data or native code is involved.

## Open Questions

- What sandbox technology should TUC use for executable backend plugins?
- What serialized IR format should be accepted first?
- What is the first fuzz target once native MLIR work begins?
