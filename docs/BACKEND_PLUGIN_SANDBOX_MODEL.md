# Backend Plugin Sandbox Model

Backend Plugin Sandbox Model v0 is the data-only sandbox contract for future
external executable backend plugins.

It does not implement sandbox execution and does not grant execution permission.
It defines the controls that must exist before TUC may consider plugin
discovery, generated artifact execution, dynamic library loading, device
access, or native plugin ABI work.

## Contract

- Report schema:
  `schemas/backend_plugin_sandbox_model_report.v0.schema.json`
- Report schema version:
  `tuc.backend_plugin_sandbox_model_report.v0`
- Sandbox contract:
  `backend_plugin_sandbox_model.data_only.v0`
- Example:
  `examples/backend_plugin_sandbox_model.py`
- Golden:
  `tests/golden/backend_plugin_sandbox_model/current_report.json`
- Tests:
  `tests/test_backend_plugin_sandbox_model.py`
- RFC:
  [RFC 0218](../rfcs/0218-backend-plugin-sandbox-model.md)

## Current Decision

The sandbox model is accepted as a data-only model:

- `sandbox_model_status: accepted_data_only_model`
- `execution_permission: not_granted`
- `execution_allowed: false`
- `isolation_strategy: separate_worker_process_or_container_required`
- `model_ready: true`

This satisfies the `sandbox_model` requirement in
[Backend Plugin Lifecycle Policy](BACKEND_PLUGIN_LIFECYCLE_POLICY.md), but it
does not make plugins executable. Artifact provenance, resource-budget evidence,
fuzz/negative-test evidence, and maintainer approval now exist as separate
data-only lifecycle evidence; executable plugin behavior still requires a
separate implementation RFC and explicit policy change.

## Required Controls

The model requires:

- explicit opt-in enablement
- capability manifest pre-review
- content-digest artifact binding
- no compile-time plugin execution
- host path access denial
- environment secret access denial
- network access denial
- device access denied by default
- dynamic library loading denied by default
- bounded resource budgets
- content-addressed cache scoping
- metadata-only diagnostics

## Security Boundary

The report is data-only. It does not scan directories, resolve entry points,
import modules, load dynamic libraries, execute generated artifacts, access
devices, spawn subprocesses, read host paths, inspect environment variables,
touch the network, or load benchmark artifacts.

The schema is fail-closed with `additionalProperties: false` on every object.
It records only bounded identifiers and omits source text, module names, host
paths, command lines, device identifiers, dynamic-library paths, generated
artifact contents, secrets, and raw benchmark output.

## Review Meaning

A passing sandbox model means TUC has an accepted control model for future
executable backend plugin proposals.

It does not mean TUC has a sandbox implementation, an executable plugin ABI,
runtime enforcement, or permission to execute backend
artifacts. Those require explicit implementation evidence and changes to the lifecycle policy.
