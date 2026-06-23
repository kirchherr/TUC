# Runtime Allocation Receipt

Runtime Allocation Receipt v0 is the data-only allocator dry-run evidence after
Runtime Allocation Admission and before any real allocator behavior.

It records deterministic receipt entries derived from admitted allocation
requests:

- receipt ID
- request ID
- source allocation slot ID
- memory domain
- budget ID
- reserved bytes
- deterministic per-domain dry-run offset
- per-domain reserved and max-reserved bytes
- dry-run allocation status
- handle policy

Schema:

```text
schemas/runtime_allocation_receipt_report.v0.schema.json
```

Golden output:

```text
tests/golden/runtime_allocation_receipt/current_report.json
```

Example:

```text
examples/runtime_allocation_receipt.py
```

## Contract

The report is accepted only when:

- the source Allocation Admission passes
- the source Allocation Admission metadata digest is bound into the receipt
- every admitted request has exactly one dry-run receipt
- receipt bytes equal total admitted bytes
- each receipt stays within the admitted domain budget
- every receipt uses the `no_runtime_handles` policy
- every receipt uses `dry_run_only` allocation mode

The report emits:

```text
runtime_allocation_receipt.data_only.v0
```

## Security Boundary

This is not an allocator and not an execution authorization. It does not allocate
memory, expose pointers, expose runtime handles, discover plugins, import
backend modules, load dynamic libraries, spawn subprocesses, access devices,
touch the network, execute generated artifacts, run JIT code, read host paths,
read environment variables, or load raw benchmark output.

The deterministic offset is only review metadata inside a dry-run ledger. It is
not a host address, device address, pointer, or allocation handle.

## Review Meaning

A passing report proves that admitted allocation requests can be transformed
into stable, bounded, handle-free dry-run allocation receipts. It does not prove
that a real allocator exists, that device memory was reserved, or that native
memory behavior is optimal.
