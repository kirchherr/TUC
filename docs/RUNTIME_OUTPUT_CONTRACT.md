# Runtime Output Contract

Runtime Output Contract v0 is a schema-versioned, data-only review artifact for
binding public output names to terminal graph tensor names.

## Contract

- Report schema: `schemas/runtime_output_contract_report.v0.schema.json`
- Report schema version: `tuc.runtime_output_contract_report.v0`
- Output contract: `runtime_output_contract.data_only.v0`
- Output manifest contract: `runtime_output_manifest.data_only.v0`
- Executor contract: `runtime_executor.trusted_backend.v0`
- Alias policy: `explicit_output_aliases`
- Terminal output policy: `graph_terminal_outputs`
- Raw value policy: `omitted_by_policy`

## What It Proves

The report separates graph-internal terminal tensors from public output names:

- every terminal graph output can be explicitly bound to a public alias
- public aliases point only to terminal graph outputs
- duplicate tensor bindings are reported
- unbound terminal outputs are reported
- resolved public outputs preserve tensor shape, dtype, producer kind, and
  producer id from Runtime Output Manifest evidence
- raw tensor values are omitted by policy

The deterministic example is:

```bash
python examples/runtime_output_contract.py
```

Golden evidence:

```text
tests/golden/runtime_output_contract/current_report.json
```

The follow-on runtime value boundary is documented in
[Runtime Public Output Bundle](RUNTIME_PUBLIC_OUTPUT_BUNDLE.md) and emits
metadata-only evidence at
`schemas/runtime_public_output_bundle_report.v0.schema.json`.

Frontend-originated public return aliases are connected through
[Source Intent Runtime Returns](SOURCE_INTENT_RUNTIME_RETURNS.md), with
schema-versioned evidence at
`schemas/source_intent_runtime_returns_report.v0.schema.json`.

The current fixture uses the multi-output runtime graph:

```text
tests/golden/runtime_multi_output_evidence/current_report.json
```

## Security Boundary

Runtime Output Contract is metadata only. It does not serialize tensor values,
hash tensor contents, expose host paths, name device identifiers, reference
generated code, load artifacts, discover plugins, run JIT code, spawn
subprocesses, or touch the network.

The contract accepts aliases as a plain in-memory mapping from public name to
terminal tensor name. It rejects subclassed mappings and validates every name
as a bounded safe identifier.

## Current Limitations

- The contract is named-output only; it does not define positional tuple return
  semantics.
- Public output aliases must bind terminal graph tensors exactly; aliases to
  intermediates remain invalid.
- The contract records output metadata, not values.
- The contract is part of Runtime Evidence Gate, but v0 still uses the fixed
  multi-output fixture while broader user API return semantics stabilize.
