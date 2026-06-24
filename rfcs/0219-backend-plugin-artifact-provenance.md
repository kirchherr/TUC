# RFC 0219: Backend Plugin Artifact Provenance

Status: Accepted

## Context

RFC 0217 introduced Backend Plugin Lifecycle Policy as the blocking policy for
future executable backend plugin work. RFC 0218 accepted a data-only sandbox
model, but executable artifact provenance was still missing.

Without a provenance boundary, a future plugin proposal could blur the line
between a named backend artifact and permission to load or execute that artifact.
TUC needs the opposite: digest-bound metadata that strengthens review evidence
while keeping execution blocked.

## Decision

Add Backend Plugin Artifact Provenance v0 with:

- report model `src/tuc/backends/artifact_provenance.py`;
- schema `schemas/backend_plugin_artifact_provenance_report.v0.schema.json`;
- example `examples/backend_plugin_artifact_provenance.py`;
- golden `tests/golden/backend_plugin_artifact_provenance/current_report.json`;
- tests `tests/test_backend_plugin_artifact_provenance.py`;
- provenance contract `backend_plugin_artifact_provenance.data_only.v0`.

The model records that provenance is accepted only as digest-bound metadata:

```text
execution_permission = not_granted
execution_allowed = false
```

Each artifact record must bind to a sandbox model contract, content digest,
source scope, build recipe, and review record. Storage scope is a stable label,
not a host path, package URL, import path, or executable entry point.

Backend Plugin Lifecycle Policy now treats `artifact_provenance` as satisfied
by this accepted provenance contract. The policy remains execution-blocking
after resource-budget evidence is accepted by RFC 0220, fuzz/negative-test
evidence is accepted by RFC 0221, and maintainer approval evidence is accepted
by RFC 0222.

## Security Boundary

The provenance report is data-only. It does not scan directories, discover
plugins, import modules, load dynamic libraries, execute generated artifacts,
access devices, spawn subprocesses, touch the network, inspect environment
variables, read host paths, load benchmark artifacts, or read artifact bytes.

It records stable identifiers and `sha256:` digests only. It does not record
Python module names, entry points, commands, device identifiers, source code,
generated artifact contents, native library paths, secrets, URLs, or raw
benchmark output.

## Consequences

TUC now has a concrete provenance requirement for future executable backend
artifacts without opening a compiler execution surface.

Future plugin proposals still need an explicit implementation RFC before any
plugin discovery, artifact execution, native plugin ABI, dynamic-library
loading, device access, subprocess execution, network access, or JIT execution
can be enabled.
