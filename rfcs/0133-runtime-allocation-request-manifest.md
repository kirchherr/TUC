# RFC 0133: Runtime Allocation Request Manifest

## Status

Accepted.

## Context

Runtime Allocation Plan v0 defines allocation slots and Runtime Memory Budget v0
checks those slots against explicit memory-domain budgets. A future allocator
will need an admission surface before it can safely request memory from pools or
devices.

Adding allocator behavior directly would be premature: it would introduce
runtime handles, device state, and possible backend execution surfaces before
TUC has a reviewed allocator security model.

## Decision

Introduce Runtime Allocation Request Manifest v0 as a bounded, data-only report
derived from Runtime Allocation Plan and Runtime Memory Budget evidence.

The manifest records one request per allocation slot and includes:

- request ID
- source slot ID
- memory domain
- layout
- dtype
- shape
- reserved bytes
- tensor names
- allocation kind
- request status
- handle policy

The report is schema-versioned at:

```text
schemas/runtime_allocation_request_manifest_report.v0.schema.json
```

The deterministic golden is:

```text
tests/golden/runtime_allocation_request_manifest/current_report.json
```

The example entry point is:

```text
examples/runtime_allocation_request_manifest.py
```

## Security Boundary

The manifest does not allocate memory, expose runtime handles, discover
plugins, import backend modules, load dynamic libraries, spawn subprocesses,
access devices, touch the network, execute generated artifacts, run JIT code,
read host paths, read environment variables, or load raw benchmark output.

All text fields remain bounded and reject known execution-surface names,
including `runtime_handle`.

## Gate Integration

Runtime Memory Planning Gate now verifies that the Allocation Request Manifest
passes and is bound to the same Allocation Plan and Memory Budget evaluated by
the gate invocation.

## Consequences

Future allocator work has a stable admission contract before any memory handle
or device interaction is introduced.

Real allocator behavior remains blocked until a separate allocator RFC defines
ownership, lifetime, sandboxing, provenance, diagnostics, and fuzzing
requirements.
