# Runtime Execution Receipt

Runtime Execution Receipt v0 is a deterministic, data-only receipt that links
one trusted runtime execution to its runtime evidence reports.

It answers one narrow question:

```text
Did the accepted runtime execution produce a complete metadata-only evidence
chain for inputs, internal records, terminal outputs, and reference correctness?
```

## Contract

- Report schema: `schemas/runtime_execution_receipt_report.v0.schema.json`
- Report schema version: `tuc.runtime_execution_receipt_report.v0`
- Receipt contract: `runtime_execution_receipt.data_only.v0`
- Linkage policy: `metadata_digest_linkage`
- Raw value policy: `omitted_by_policy`
- Artifact status: `review_evidence`

## Linked Evidence

The receipt requires these evidence kinds:

- `tensor_store_evidence`
- `input_manifest`
- `output_manifest`
- `reference_correctness`

Each link records:

- evidence kind
- graph name
- evidence contract
- metadata digest
- item count
- pass/fail status
- raw value policy

The receipt also records operation-level trace metadata: operation name, kind,
planned backend, executor backend, input tensor names, output tensor names,
output shapes, and status.

## Evidence

Run:

```bash
python examples/runtime_execution_receipt.py
```

Golden evidence:

```text
tests/golden/runtime_execution_receipt/proof_of_execution.json
```

## Security Boundary

The receipt does not serialize tensor values, reference values, source text,
Python modules, commands, file paths, host paths, backend artifacts, generated
code, raw benchmark output, device identifiers, URLs, environment variables, or
plugin entry points.

It does not discover plugins, access devices, spawn subprocesses, run JIT code,
load dynamic libraries, touch the network, execute generated artifacts, or load
artifact files from matrix identifiers.

## Review Meaning

A passing Runtime Execution Receipt proves that one trusted runtime execution
has a complete linked evidence chain with matching graph names, expected
contracts, passing evidence reports, non-empty item counts, and raw values
omitted by policy.

It is not a performance claim, a native backend authorization, a cryptographic
attestation, or a tensor-content hash.
