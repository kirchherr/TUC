# RFC 0025: Backend Capability Registry

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 2

## Summary

TUC adds an explicit backend capability registry that collects trusted
`BackendCapability` objects or schema-versioned backend capability manifests and
exposes only pure capability data to compiler/runtime planning.

## Motivation

Phase 2 needs a clearer platform boundary for backend authors without
accidentally creating an executable plugin surface. The existing manifest loader
is secure and data-only, but callers still have to manage capability lists by
hand. A small immutable registry gives TUC a stable place to enforce uniqueness,
resource limits, and backend-name hygiene before partitioning.

## Decision

Add:

- `tuc.backends.registry.BackendRegistry`
- `BackendRegistration`
- `BackendRegistryError`
- `docs/BACKEND_REGISTRY.md`
- `examples/backend_registry.py`
- Registry tests for explicit manifest loading, duplicate names, directory
  non-scanning, unsafe names, excessive backend counts, and pure-data filtering.

The registry accepts:

- Explicit manifest paths through `from_manifest_paths`.
- Trusted in-process capability objects through `from_capabilities`.

It returns:

- Backend names.
- Registration records.
- Capability tuples for partitioning.
- Pure-data operation support queries.

## Security Model

The registry is not auto-discovery and not a plugin ABI.

It does not:

- Search directories.
- Import Python modules.
- Spawn subprocesses.
- Load dynamic libraries.
- Open devices.
- Store backend objects.
- Execute backend lowering or artifacts.

Manifest paths are explicit. Manifest parsing remains bounded,
schema-versioned, duplicate-key rejecting, and unknown-field rejecting through
`tuc.manifests`.

Registry validation adds:

- Maximum backend count.
- Unique backend names.
- Bounded backend-name byte size.
- Alphanumeric backend-name prefixes.
- Path-separator-free source labels for diagnostics.

## Consequences

- Runtime partitioning can consume a reviewed registry instead of ad hoc lists.
- Backend authoring stays capability-first.
- TUC gets a concrete Phase 2 extension point without granting executable
  plugin privileges.
- Future plugin lifecycle work has a safe data boundary to build from.

## Follow-Up

1. Define a plugin lifecycle RFC before any backend package discovery.
2. Define sandboxed artifact execution before generated backend outputs can run.
3. Add organization-backed maintainer/code-owner groups before broad external
   contribution.
4. Connect registry diagnostics to richer compiler decision reports.
