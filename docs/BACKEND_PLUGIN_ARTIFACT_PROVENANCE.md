# Backend Plugin Artifact Provenance

Backend Plugin Artifact Provenance v0 is the data-only provenance contract for
future executable backend plugin artifacts.

It records bounded identifiers and digest bindings only. It does not read,
load, inspect, import, or execute artifact contents, and it does not grant
execution permission.

## Contract

- Report schema:
  `schemas/backend_plugin_artifact_provenance_report.v0.schema.json`
- Report schema version:
  `tuc.backend_plugin_artifact_provenance_report.v0`
- Provenance contract:
  `backend_plugin_artifact_provenance.data_only.v0`
- Provenance policy:
  `artifact_provenance.digest_bound.reviewed.no_execution.v0`
- Example:
  `examples/backend_plugin_artifact_provenance.py`
- Golden:
  `tests/golden/backend_plugin_artifact_provenance/current_report.json`
- Tests:
  `tests/test_backend_plugin_artifact_provenance.py`
- RFC:
  [RFC 0219](../rfcs/0219-backend-plugin-artifact-provenance.md)

## Current Decision

The artifact provenance model is accepted as data-only evidence:

- `provenance_status: accepted_data_only_provenance`
- `execution_permission: not_granted`
- `execution_allowed: false`
- `provenance_ready: true`

This satisfies the `artifact_provenance` requirement in
[Backend Plugin Lifecycle Policy](BACKEND_PLUGIN_LIFECYCLE_POLICY.md), but it
does not make plugins executable. Resource-budget evidence, fuzzing or
negative-test evidence, and maintainer approval still remain required before
plugin enablement can be proposed.

## Required Bindings

Each artifact provenance record must bind:

- sandbox model contract
- content digest
- source scope
- build recipe
- review record

The current record is bound to
`backend_plugin_sandbox_model.data_only.v0` and a `sha256:` digest. Storage
scope is recorded as a stable label such as `repository_evidence`, not as a host
path or URL.

## Security Boundary

The report is data-only. It does not scan directories, resolve entry points,
import modules, load dynamic libraries, execute generated artifacts, access
devices, spawn subprocesses, read host paths, inspect environment variables,
touch the network, or load benchmark artifacts.

The schema is fail-closed with `additionalProperties: false` on every object.
It records only bounded identifiers and digests, and omits source text, module
names, host paths, command lines, device identifiers, dynamic-library paths,
generated artifact contents, secrets, raw benchmark output, and artifact bytes.

## Review Meaning

A passing artifact provenance report means TUC has accepted a digest-bound,
reviewed metadata record for a future backend artifact.

It does not mean TUC has an executable plugin ABI, sandbox implementation,
resource budget, fuzz evidence, maintainer approval, or permission to execute
backend artifacts. Those require separate accepted evidence and changes to the
lifecycle policy.
