# Runtime Allocation Admission

Runtime Allocation Admission v0 is the data-only admission check between Runtime
Allocation Request Manifest and any future allocator behavior.

It records bounded admission decisions derived from allocation requests and
memory-budget usage:

- request ID
- source allocation slot ID
- memory domain
- budget ID
- reserved bytes
- per-domain reserved and max-reserved bytes
- admission status
- handle policy

Schema:

```text
schemas/runtime_allocation_admission_report.v0.schema.json
```

Golden output:

```text
tests/golden/runtime_allocation_admission/current_report.json
```

Example:

```text
examples/runtime_allocation_admission.py
```

## Contract

The report is accepted only when:

- the source Request Manifest passes
- the source Memory Budget passes
- the Request Manifest budget digest matches the Memory Budget allocation digest
- every request has exactly one admission decision
- every admission stays under a `within_budget` memory-domain usage
- every admission uses the `no_runtime_handles` policy

The report emits:

```text
runtime_allocation_admission.data_only.v0
```

## Security Boundary

This is not an allocator. It does not allocate memory, expose pointers, create
runtime handles, discover plugins, import backend modules, load dynamic
libraries, spawn subprocesses, access devices, touch the network, execute
generated artifacts, run JIT code, read host paths, read environment variables,
or load raw benchmark output.

The report exists so future allocator behavior must first be justified by a
schema-versioned, digest-bound admission decision.

## Review Meaning

A passing report proves that the current allocation requests can be admitted by
the current memory-budget evidence without creating runtime handles or device
access. It does not prove that a real allocator exists, that device memory was
reserved, or that native memory behavior is optimal.
