# RFC 0220: Backend Plugin Resource Budget

Status: Accepted

## Context

RFC 0217 introduced Backend Plugin Lifecycle Policy as the blocking policy for
future executable backend plugin work. RFC 0218 accepted a data-only sandbox
model. RFC 0219 accepted digest-bound artifact provenance.

At this RFC step, the next missing lifecycle requirement was resource-budget
evidence. Without a budget boundary, future plugin proposals could describe
artifacts without
reviewed limits for CPU time, memory, output, artifact size, cache entries, and
diagnostics. That creates a resource-exhaustion risk before any real sandbox or
executor exists.

## Decision

Add Backend Plugin Resource Budget v0 with:

- report model `src/tuc/backends/resource_budget.py`;
- schema `schemas/backend_plugin_resource_budget_report.v0.schema.json`;
- example `examples/backend_plugin_resource_budget.py`;
- golden `tests/golden/backend_plugin_resource_budget/current_report.json`;
- tests `tests/test_backend_plugin_resource_budget.py`;
- resource budget contract `backend_plugin_resource_budget.data_only.v0`.

The model records accepted static bounds only:

```text
execution_permission = not_granted
execution_allowed = false
```

Each budget record must bind to a sandbox model contract, artifact provenance
contract, content digest, CPU budget, memory budget, and IO-like budget fields
for output, artifact size, cache entries, and diagnostics.

Backend Plugin Lifecycle Policy now treats `resource_budget` as satisfied by
this accepted resource budget contract. The policy remains execution-blocking
even after RFC 0222 accepts maintainer approval evidence.

## Security Boundary

The resource budget report is data-only. It does not scan directories, discover
plugins, import modules, load dynamic libraries, execute generated artifacts,
access devices, spawn subprocesses, touch the network, inspect environment
variables, read host paths, load benchmark artifacts, read artifact bytes, or
collect raw timing samples.

It records stable identifiers, `sha256:` digests, and positive integer limits
only. It does not record Python module names, entry points, commands, device
identifiers, source code, generated artifact contents, native library paths,
secrets, URLs, or raw benchmark output.

## Consequences

TUC now has a concrete resource-budget evidence layer for future executable
backend artifacts without opening a compiler execution surface.

Future plugin proposals still need an explicit implementation RFC before any
plugin discovery, artifact execution, native plugin ABI, dynamic-library loading,
device access, subprocess execution, network access, or JIT execution can be
enabled.
