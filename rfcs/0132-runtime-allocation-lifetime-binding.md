# RFC 0132: Runtime Allocation Lifetime Binding

## Status

Accepted.

## Context

Runtime Buffer Lifetime v0 derives conservative produced tensor lifetimes and
reuse candidates. Runtime Allocation Plan v0 derives tensor-to-slot bindings
from that lifetime report.

Runtime Memory Planning Gate already checks Allocation Plan and Memory Budget
evidence, and now binds Memory Budget to the Allocation Plan by metadata
digest. The upstream link still needs the same protection: an Allocation Plan
can otherwise be internally valid while being stale relative to the lifetime
report evaluated by the gate.

## Decision

Runtime Buffer Lifetime reports expose `lifetime_metadata_digest`, a
deterministic digest over lifetime metadata.

Runtime Allocation Plan reports record `source_lifetime_metadata_digest` from
the Buffer Lifetime report used to build the allocation plan.

Runtime Memory Planning Gate now verifies:

- Buffer Lifetime evidence passes
- Allocation Plan source lifetime contract, schema, issue count, graph name,
  operation count, and metadata digest match the Buffer Lifetime report
  evaluated by the same gate invocation
- Memory Budget remains bound to the Allocation Plan by allocation metadata
  digest

## Security Boundary

The digest is metadata-only. It does not include tensor values, host paths,
device identifiers, benchmark output, executable artifacts, command lines,
environment variables, or plugin entry points.

The binding check does not allocate memory, query devices, import plugins, load
dynamic libraries, spawn subprocesses, run JIT code, execute generated
artifacts, or access the network.

## Consequences

Runtime Memory Planning Gate now rejects stale or forged Allocation Plan
evidence when it does not bind to the current Buffer Lifetime report.

The gate output includes:

```text
allocation_lifetime_binding = "verified"
```
