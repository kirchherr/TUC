# Runtime Allocation Request Manifest

Runtime Allocation Request Manifest v0 is the data-only request surface between
Runtime Allocation Plan, Runtime Memory Budget, and a future allocator.

It records bounded allocator-admission requests derived from allocation slots:

- request ID
- source allocation slot ID
- memory domain
- layout
- dtype
- shape
- reserved bytes
- tensor names
- allocation kind
- request status
- handle policy

Schema:

```text
schemas/runtime_allocation_request_manifest_report.v0.schema.json
```

Golden output:

```text
tests/golden/runtime_allocation_request_manifest/current_report.json
```

Example:

```text
examples/runtime_allocation_request_manifest.py
```

## Contract

The manifest is accepted only when:

- the source Allocation Plan metadata digest matches the Memory Budget source
  allocation digest
- request IDs and slot IDs are unique
- at least one allocation request exists
- every request is derived from a typed allocation slot
- every request uses the `no_runtime_handles` policy

The manifest emits:

```text
runtime_allocation_request_manifest.data_only.v0
```

## Security Boundary

This is not a memory allocator. It does not allocate memory, expose pointers,
create runtime handles, discover plugins, import backend modules, load dynamic
libraries, spawn subprocesses, access devices, touch the network, execute
generated artifacts, run JIT code, read host paths, read environment variables,
or load raw benchmark output.

The manifest exists so future allocator work starts from a reviewable,
schema-versioned admission contract instead of an implicit runtime side effect.

## Review Meaning

A passing manifest proves that the current allocation slots have a stable,
bounded, metadata-only allocator-request view and that the request view is bound
to the same Allocation Plan and Memory Budget evidence.

It does not prove that a real allocator exists, that a device allocation was
performed, or that native memory behavior is optimal. Those claims require a
separate allocator RFC, sandbox model, provenance evidence, and tests.
