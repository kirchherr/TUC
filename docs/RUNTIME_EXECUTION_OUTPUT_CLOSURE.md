# Runtime Execution Output Closure

Runtime Execution Output Closure v0 is a deterministic, data-only audit report
for the public output boundary of one trusted runtime execution.

It answers one narrow question:

```text
Do Runtime Execution Receipt and Runtime Execution Evidence Bundle bind the same
Output Contract and Runtime Public Output Bundle metadata for this execution?
```

## Contract

- Report schema: `schemas/runtime_execution_output_closure_report.v0.schema.json`
- Report schema version: `tuc.runtime_execution_output_closure_report.v0`
- Closure contract: `runtime_execution_output_closure.data_only.v0`
- Closure policy: `runtime_execution_output_closure.receipt_bundle_public_outputs.v0`
- Closure status: `closed_by_metadata_digest`
- Raw value policy: `omitted_by_policy`

## Checked Evidence

The report checks exactly two public-output evidence kinds:

- `output_contract`
- `public_output_bundle`

For each kind, it compares source, receipt, and bundle contract IDs, metadata
digests, item counts, and row status. It also verifies that the bundle embeds
the same Runtime Execution Receipt digest as the receipt evaluated by the gate.

## Evidence

Run the proof-of-execution closure:

```bash
python examples/runtime_execution_output_closure.py
```

Run the multi-output closure:

```bash
python examples/runtime_multi_output_execution_output_closure.py
```

Golden evidence:

```text
tests/golden/runtime_execution_output_closure/proof_of_execution.json
tests/golden/runtime_execution_output_closure/multi_output_execution.json
```

## Security Boundary

The report is metadata-only. It serializes contracts, graph names, SHA-256
metadata digests, item counts, pass/fail status, and raw-value policy. It does
not serialize tensor values, source text, commands, host paths, generated code,
backend artifacts, device identifiers, URLs, environment variables, or plugin
entry points.

It does not discover plugins, access devices, spawn subprocesses, run JIT code,
load dynamic libraries, touch the network, execute generated artifacts, or read
artifact files from matrix identifiers.

## Review Meaning

A passing Runtime Execution Output Closure proves that a runtime public output
boundary is closed by metadata digest across source public-output evidence,
Runtime Execution Receipt, and Runtime Execution Evidence Bundle. The current
evidence covers both the proof-of-execution fixture and a two-public-output
fixture.

It is not a performance claim, cryptographic attestation, hardware endorsement,
or source parser completeness claim.
