# RFC 0010: Schema-Versioned Backend And Transfer Manifests

- Status: accepted-for-prototype
- Created: 2026-06-05
- Phase: 1 to 2

## Summary

TUC adds explicit JSON manifest loaders for backend capabilities and transfer
cost profiles. The loaders accept only schema-versioned, bounded, repository- or
caller-provided JSON files and return typed `BackendCapability` or
`TransferCostProfile` objects.

## Motivation

Backend authors will eventually need to describe capabilities without modifying
TUC source code. Transfer-cost profiles also need to move from in-memory test
objects toward calibrated data files. Both paths are compiler input boundaries
and must be treated as untrusted.

## Decision

Add `tuc.manifests` with:

- `load_json_manifest(...)`
- `load_backend_capability_manifest(...)`
- `load_transfer_cost_profile_manifest(...)`

The initial schema versions are:

- `tuc.backend_capability.v0`
- `tuc.transfer_cost_profile.v0`

The loader is intentionally explicit. It does not scan directories, import
plugins, execute backend code, resolve entry points, or discover manifests from
environment variables.

## Security Model

Manifest files are untrusted input:

- Files must use the `.json` suffix.
- Symlink paths are rejected.
- File size is bounded.
- JSON must be UTF-8.
- Duplicate JSON object keys are rejected.
- `NaN`, `Infinity`, and `-Infinity` are rejected.
- JSON depth, object key count, list length, string size, integer size, and
  float range are bounded.
- Unknown schema fields are rejected.
- Schema versions must match exactly.

The result is typed data only. Capability and profile validation still happens
before runtime planning or lowering.

## Consequences

- Backend capability files and transfer-cost profile files are now possible
  without increasing plugin attack surface.
- Future backend API documentation can point to stable manifest schema names.
- Schema evolution must be explicit and tested.

## Follow-Up

1. Add formal JSON Schema documents once the v0 fields stabilize.
2. Add backend API v0.1 documentation for external authors.
3. Add manifest fuzz tests before accepting third-party manifest ingestion at
   scale.
4. Add signed or provenance-bound manifest distribution only as part of release
   hardening.
