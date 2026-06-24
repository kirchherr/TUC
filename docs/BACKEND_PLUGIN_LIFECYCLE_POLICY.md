# Backend Plugin Lifecycle Policy

Backend Plugin Lifecycle Policy v0 is the current blocking policy for any
future external executable backend plugin surface.

It exists because TUC's backend model is intentionally capability-first:
hardware and backend authors may describe capabilities as bounded data, but
TUC must not discover, import, load, or execute third-party backend code until
a separate lifecycle and sandboxing proof exists.

## Contract

- Report schema:
  `schemas/backend_plugin_lifecycle_policy_report.v0.schema.json`
- Report schema version:
  `tuc.backend_plugin_lifecycle_policy_report.v0`
- Policy contract:
  `backend_plugin_lifecycle_policy.blocking.v0`
- Example:
  `examples/backend_plugin_lifecycle_policy.py`
- Golden:
  `tests/golden/backend_plugin_lifecycle_policy/current_report.json`
- Tests:
  `tests/test_backend_plugin_lifecycle_policy.py`
- RFC:
  [RFC 0217](../rfcs/0217-backend-plugin-lifecycle-policy.md)

## Current Decision

The policy is accepted and enforced as a blocking policy:

- `plugin_discovery_enabled: false`
- `artifact_execution_enabled: false`
- `native_plugin_abi_enabled: false`
- `execution_status: external_plugins_blocked`
- `sandbox_model_status: accepted_data_only_model`
- `ready_to_enable_plugins: true`

This is not a rejection of future plugin work. It is the security boundary that
keeps future plugin work from becoming an accidental compiler attack surface.

## Required Before Plugins

The policy currently records nine requirements:

- `capability_manifest_claim_review`: satisfied
- `backend_author_evidence_gate`: satisfied
- `trusted_executor_contract`: satisfied
- `plugin_lifecycle_rfc`: satisfied
- `sandbox_model`: satisfied
- `artifact_provenance`: satisfied
- `resource_budget`: satisfied
- `fuzz_negative_tests`: satisfied
- `maintainer_approval`: satisfied

Even though the data-only lifecycle evidence gate is now complete, TUC must
continue to reject executable plugin behavior until a separate implementation
RFC explicitly changes the policy:

- backend plugin discovery
- generated artifact execution
- native plugin ABI loading
- dynamic-library loading
- device access
- subprocess execution
- network access
- JIT execution

## Security Boundary

The report is data-only. It does not scan directories, read package metadata,
resolve entry points, import Python modules, open dynamic libraries, execute
generated artifacts, access devices, spawn subprocesses, read host paths, read
environment variables, touch the network, or load benchmark artifacts.

The schema is fail-closed with `additionalProperties: false` on every object
and avoids host paths, module names, commands, device identifiers, source text,
artifact contents, and raw benchmark output.

## Review Meaning

A passing policy report means the current repository is still protecting TUC's
compiler boundary from executable backend plugin surfaces.

It does not approve any plugin implementation. A future plugin implementation
proposal must still bind to this complete evidence chain, add concrete sandbox
enforcement, and change the lifecycle policy through a separate implementation
RFC before it can enable discovery or execution.
