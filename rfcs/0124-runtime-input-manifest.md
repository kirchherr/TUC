# RFC 0124: Runtime Input Manifest

## Status

Accepted.

## Context

Runtime Tensor Store Evidence shows that accepted input and computed runtime
values are held as internal `RuntimeValueRecord` metadata with raw tensor values
omitted from review artifacts. Runtime Output Manifest then makes terminal
outputs explicit.

The remaining asymmetry was the accepted external input boundary. Inputs were
visible indirectly through the tensor store, but there was no dedicated
metadata-only manifest proving which graph external inputs the runtime accepted
before computation.

## Decision

Add Runtime Input Manifest v0:

- `examples/runtime_input_manifest.py`
- `src/tuc/runtime/input_manifest.py`
- `schemas/runtime_input_manifest_report.v0.schema.json`
- `tests/golden/runtime_input_manifest/proof_of_execution.json`
- [Runtime Input Manifest](../docs/RUNTIME_INPUT_MANIFEST.md)

The manifest contract is:

```text
runtime_input_manifest.data_only.v0
```

The schema path is:

```text
schemas/runtime_input_manifest_report.v0.schema.json
```

Runtime Evidence Gate now requires Runtime Input Manifest evidence between
Runtime Tensor Store Evidence and Runtime Output Manifest evidence.

## Security Boundary

Runtime Input Manifest is data-only. It omits raw tensor values and rejects
fields or identifiers that name source text, commands, file paths, host paths,
backend artifacts, generated code, Python modules, raw benchmark output, raw
tensor values, device identifiers, URLs, environment variables, or plugin entry
points.

It does not add a parser, a plugin system, dynamic import, subprocess execution,
device access, dynamic library loading, network access, JIT execution, or
generated artifact execution.

## Consequences

Runtime evidence now has an explicit metadata-only input boundary:

```text
external graph input -> RuntimeValueRecord -> Runtime Input Manifest
```

This makes future backend and frontend work easier to audit because accepted
runtime inputs are no longer inferred only from broader tensor-store evidence.
