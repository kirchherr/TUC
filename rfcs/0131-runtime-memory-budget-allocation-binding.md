# RFC 0131: Runtime Memory Budget Allocation Binding

## Status

Accepted.

## Context

Runtime Allocation Plan v0 derives planned buffer slots from Runtime Buffer
Lifetime evidence. Runtime Memory Budget v0 derives memory-domain usages from
an allocation plan and checks them against explicit budgets.

Runtime Memory Planning Gate previously checked that the Allocation Plan and
Memory Budget had the same graph name and operation count. That left a review
gap: a stale Memory Budget report could still appear coherent if those fields
matched while its usage data came from a different Allocation Plan.

## Decision

Runtime Allocation Plan reports expose `allocation_metadata_digest`, a
deterministic digest over allocation-plan metadata.

Runtime Memory Budget reports record `source_allocation_metadata_digest` from
the Allocation Plan used to build the budget report.

Runtime Memory Planning Gate verifies that the Memory Budget source allocation
metadata digest matches the Allocation Plan evaluated by the same gate
invocation.

## Security Boundary

The digest is metadata-only. It does not include tensor values, host paths,
device identifiers, benchmark output, executable artifacts, command lines,
environment variables, or plugin entry points.

The binding check does not allocate memory, query devices, import plugins, load
dynamic libraries, spawn subprocesses, run JIT code, execute generated
artifacts, or access the network.

## Consequences

Runtime Memory Planning Gate now rejects stale or forged Memory Budget evidence
when it does not bind to the current Allocation Plan.

The gate output includes:

```text
memory_budget_allocation_binding = "verified"
```
