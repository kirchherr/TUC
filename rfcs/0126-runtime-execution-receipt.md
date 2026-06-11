# RFC 0126: Runtime Execution Receipt

## Status

Accepted.

## Context

TUC now has separate data-only runtime evidence for internal tensor records,
accepted external inputs, terminal outputs, and reference correctness. These
reports are useful independently, but reviewers still need a small artifact that
proves they belong to the same trusted runtime execution.

## Decision

Add Runtime Execution Receipt v0:

- `src/tuc/runtime/execution_receipt.py`
- `examples/runtime_execution_receipt.py`
- `schemas/runtime_execution_receipt_report.v0.schema.json`
- `tests/golden/runtime_execution_receipt/proof_of_execution.json`
- [Runtime Execution Receipt](../docs/RUNTIME_EXECUTION_RECEIPT.md)

The receipt contract is:

```text
runtime_execution_receipt.data_only.v0
```

The schema path is:

```text
schemas/runtime_execution_receipt_report.v0.schema.json
```

Runtime Evidence Gate now requires the receipt after Runtime Reference
Correctness.

## Required Linked Evidence

The receipt links:

- Runtime Tensor Store Evidence
- Runtime Input Manifest
- Runtime Output Manifest
- Runtime Reference Correctness

Each link carries only graph name, contract, metadata digest, item count, pass
status, and raw-value policy. The receipt also records operation-level runtime
trace metadata without tensor values.

## Security Boundary

The receipt is data-only. It does not serialize input tensors, output tensors,
reference tensors, source text, host paths, commands, generated code, backend
artifacts, plugin entry points, device identifiers, URLs, environment
variables, or raw benchmark output.

It does not execute generated artifacts, discover backend plugins, import
dynamic code, load dynamic libraries, access devices, spawn subprocesses, or
touch the network.

## Consequences

The practical runtime proof now has a single metadata-only receipt:

```text
accepted inputs
  -> runtime value records
  -> terminal outputs
  -> reference correctness
  -> execution receipt
```

This improves reviewability without expanding the compiler or runtime attack
surface.
