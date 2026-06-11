# RFC 0112: Runtime Output Contract v0

- Status: Accepted
- Date: 2026-06-11
- Related:
  - [Runtime Output Contract](../docs/RUNTIME_OUTPUT_CONTRACT.md)
  - [Runtime Output Manifest](../docs/RUNTIME_OUTPUT_MANIFEST.md)
  - [Runtime Multi-Output Evidence Fixture](0111-runtime-multi-output-evidence.md)
  - `schemas/runtime_output_contract_report.v0.schema.json`
  - `examples/runtime_output_contract.py`

## Summary

Add Runtime Output Contract v0 as a schema-versioned, data-only report that
binds public output names to terminal graph tensor names.

## Motivation

Runtime Output Manifest proves which terminal graph tensors were produced.
That is not the same as a future user-facing API return contract. If TUC lets
terminal tensor names implicitly become public output names, graph construction
details can leak into API semantics and future frontend integrations become
harder to review.

TUC needs an explicit boundary where public output names are named, validated,
and checked against terminal graph outputs.

## Decision

Runtime Output Contract v0:

- accepts a plain mapping from public output name to terminal tensor name
- sorts aliases by public name for deterministic evidence
- rejects subclassed mappings
- requires aliases to point to terminal graph outputs
- reports unbound terminal graph outputs
- reports duplicate tensor bindings
- resolves public outputs from Runtime Output Manifest metadata
- serializes only metadata and raw-value omission policy
- keeps positional return semantics out of scope

The report schema is:

```text
schemas/runtime_output_contract_report.v0.schema.json
```

## Non-Goals

- positional tuple return semantics
- tensor-value serialization
- tensor-content hashing
- user-defined output transformation kernels
- native backend correctness claims
- native performance claims
- external executable backend approval
- plugin discovery or artifact loading

## Security Boundary

The contract is metadata-only. It must not include output tensor values,
reference tensor values, tensor hashes, host paths, device identifiers,
generated code, command lines, environment variables, plugin entrypoints,
network locations, raw benchmark samples, JIT artifacts, or native executable
artifacts.

Aliases are bounded safe identifiers. The v0 builder accepts only a plain
`dict[str, str]` so external mapping subclasses cannot smuggle behavior into
contract construction.

## Acceptance Criteria

- A schema-versioned Runtime Output Contract report exists.
- A deterministic example binds public names to the multi-output fixture.
- Golden evidence proves two public outputs without raw tensor values.
- Tests cover missing aliases, non-terminal aliases, duplicate bindings,
  forged issues, forbidden names, raw-value inclusion, schema shape, and
  documentation references.
