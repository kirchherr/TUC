# Backend Plugin Resource Budget

Backend Plugin Resource Budget v0 is the data-only budget contract for future
executable backend plugin artifacts.

It records static upper bounds for CPU time, memory, output, artifact size,
cache entries, and diagnostics. It does not measure resource usage, enforce a
sandbox, execute artifacts, or grant execution permission.

## Contract

- Report schema:
  `schemas/backend_plugin_resource_budget_report.v0.schema.json`
- Report schema version:
  `tuc.backend_plugin_resource_budget_report.v0`
- Resource budget contract:
  `backend_plugin_resource_budget.data_only.v0`
- Budget policy:
  `resource_budget.static_bounds.no_execution.v0`
- Example:
  `examples/backend_plugin_resource_budget.py`
- Golden:
  `tests/golden/backend_plugin_resource_budget/current_report.json`
- Tests:
  `tests/test_backend_plugin_resource_budget.py`
- RFC:
  [RFC 0220](../rfcs/0220-backend-plugin-resource-budget.md)

## Current Decision

The resource budget model is accepted as data-only evidence:

- `budget_status: accepted_data_only_budget`
- `execution_permission: not_granted`
- `execution_allowed: false`
- `budget_ready: true`

This satisfies the `resource_budget` requirement in
[Backend Plugin Lifecycle Policy](BACKEND_PLUGIN_LIFECYCLE_POLICY.md), but it
does not make plugins executable. Fuzz/negative-test evidence and maintainer
approval now exist as separate data-only evidence, completing the lifecycle
evidence gate without enabling execution.

## Static Bounds

The current record binds one future artifact to:

- CPU time limit
- memory limit
- output size limit
- artifact size limit
- cache entry limit
- diagnostics size limit

The record also binds to
`backend_plugin_sandbox_model.data_only.v0` and
`backend_plugin_artifact_provenance.data_only.v0`. It repeats the artifact
`sha256:` digest from artifact provenance so reviewers can detect drift without
reading or executing the artifact.

## Security Boundary

The report is data-only. It does not scan directories, resolve entry points,
import modules, load dynamic libraries, execute generated artifacts, access
devices, spawn subprocesses, read host paths, inspect environment variables,
touch the network, load benchmark artifacts, read artifact bytes, or collect
raw timing samples.

The schema is fail-closed with `additionalProperties: false` on every object.
It records only bounded identifiers, digests, and positive integer limits, and
omits source text, module names, host paths, command lines, device identifiers,
dynamic-library paths, generated artifact contents, secrets, raw benchmark
output, URLs, and artifact bytes.

## Review Meaning

A passing resource budget report means TUC has accepted static, reviewable
resource limits for a future backend artifact.

It does not mean TUC has a sandbox implementation, an executable plugin ABI,
runtime enforcement, native performance claims, or
permission to execute backend artifacts. Those require separate accepted
evidence and changes to the lifecycle policy.
