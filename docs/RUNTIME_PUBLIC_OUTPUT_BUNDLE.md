# Runtime Public Output Bundle

Runtime Public Output Bundle v0 is the first runtime API boundary that resolves
public output names to internal read-only runtime values.

It builds on Runtime Output Contract v0:

```text
RuntimeExecutionResult + RuntimeOutputContractReport
    -> RuntimePublicOutputBundle
    -> metadata-only Runtime Public Output Bundle report
```

## Contract

- Report schema: `schemas/runtime_public_output_bundle_report.v0.schema.json`
- Report schema version: `tuc.runtime_public_output_bundle_report.v0`
- Bundle contract: `runtime_public_output_bundle.readonly_values.v0`
- Value contract: `runtime_public_output_value.readonly_numpy.v0`
- Output contract: `runtime_output_contract.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Raw value policy: `omitted_by_policy`

## What It Proves

The bundle proves the practical handoff from runtime execution to future user
API return semantics:

- public output names are resolved only from a passing Runtime Output Contract
- each public name maps to one terminal tensor record
- each resolved output is copied into a read-only NumPy array
- shape, dtype, producer kind, producer id, value role, and backing tensor name
  remain inspectable
- serialized evidence contains only metadata and raw-value omission policy

The deterministic example is:

```bash
python examples/runtime_public_output_bundle.py
```

Golden evidence:

```text
tests/golden/runtime_public_output_bundle/current_report.json
```

## Security Boundary

`RuntimePublicOutputBundle` may hold actual in-memory tensor values because it is
the runtime return surface. The schema-versioned report deliberately does not
serialize those values, hash tensor contents, expose host paths, name devices,
reference generated code, discover plugins, run JIT code, spawn subprocesses, or
touch the network.

Bundle construction fails closed when the output contract did not pass, when the
execution graph name does not match the contract graph name, when public names
or tensor names are unsafe, or when values are not copied into read-only arrays.

## Current Limitations

- Positional tuple return semantics are still out of scope.
- The bundle currently targets NumPy `float64` Runtime Executor values.
- This evidence is required by Runtime Evidence Gate and Runtime Evidence
  Matrix as `public_output_bundle`.
- Public API ergonomics are intentionally deferred until Source Intent return
  semantics stabilize.
