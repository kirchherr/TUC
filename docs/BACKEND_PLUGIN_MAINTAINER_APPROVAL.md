# Backend Plugin Maintainer Approval

Backend Plugin Maintainer Approval v0 is the data-only approval contract for
closing the current backend plugin lifecycle evidence gate.

It records that the maintainers accept the existing lifecycle evidence chain as
complete enough for future enablement proposals. It does not discover plugins,
execute artifacts, load dynamic libraries, grant device access, or enable a
native plugin ABI.

## Contract

- Report schema:
  `schemas/backend_plugin_maintainer_approval_report.v0.schema.json`
- Report schema version:
  `tuc.backend_plugin_maintainer_approval_report.v0`
- Approval contract:
  `backend_plugin_maintainer_approval.data_only.v0`
- Approval policy:
  `maintainer_approval.review_record.no_execution.v0`
- Example:
  `examples/backend_plugin_maintainer_approval.py`
- Golden:
  `tests/golden/backend_plugin_maintainer_approval/current_report.json`
- Tests:
  `tests/test_backend_plugin_maintainer_approval.py`
- RFC:
  [RFC 0222](../rfcs/0222-backend-plugin-maintainer-approval.md)

## Current Decision

The maintainer approval model is accepted as data-only evidence:

- `approval_status: accepted_data_only_approval`
- `approval_decision: approved_for_proposal_gate`
- `execution_permission: not_granted`
- `execution_allowed: false`
- `approval_ready: true`

This satisfies the `maintainer_approval` requirement in
[Backend Plugin Lifecycle Policy](BACKEND_PLUGIN_LIFECYCLE_POLICY.md). The
lifecycle report can now become complete while plugin discovery, generated
artifact execution, and native plugin ABI loading remain disabled.

## Required Bindings

Each approval record must bind:

- sandbox model evidence
- artifact provenance evidence
- resource budget evidence
- fuzz/negative-test evidence
- the current blocked execution surfaces
- a requirement that any executable backend change still needs its own
  implementation RFC

The current approval record uses stable IDs only:

- `approval_id: backend_plugin_lifecycle_maintainer_approval`
- `review_record_id: rfc_0222_backend_plugin_maintainer_approval`
- `maintainer_group_id: tuc_maintainers`

## Security Boundary

The report is data-only. It does not scan repositories, call GitHub APIs, read
local approval files, inspect environment variables, resolve maintainer
identities, import modules, execute plugins, load artifacts, touch devices,
spawn subprocesses, or access the network.

The schema is fail-closed with `additionalProperties: false` on every object.
It records only bounded identifiers and omits names, email addresses, tokens,
URLs, source text, module names, host paths, command lines, device identifiers,
dynamic-library paths, generated artifact contents, secrets, raw benchmark
output, raw fuzz corpus inputs, and artifact bytes.

## Review Meaning

A passing maintainer approval report means TUC has accepted the data-only
lifecycle evidence chain as complete for future enablement proposals.

It does not mean TUC has an executable plugin implementation, a sandbox
implementation, runtime enforcement, external plugin discovery, artifact
execution, native performance claims, or permission to execute backend
artifacts. Those require separate implementation RFCs and explicit lifecycle
policy changes.
